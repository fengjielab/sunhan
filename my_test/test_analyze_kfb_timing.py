#!/usr/bin/env python3

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from analyze_kfb_timing import (
    _load_manifests,
    _read_csv,
    command_reconstruct,
    command_analyze,
    command_unblind,
    reconstruct_trial,
    trial_metrics,
)
from kfb_timing_protocol import CONDITIONS, config_hash, sha256_file


class AnalysisTests(unittest.TestCase):
    def make_trial(
        self,
        root: Path,
        code: str = "C3",
        *,
        trial_id: str = "P01_M01_01",
        participant_id: str = "P01",
        phase: str = "measured",
        analyzed: bool = True,
        masked_condition: str = "M0000001",
    ) -> tuple[Path, dict]:
        spec = CONDITIONS[code]
        csv_path = root / f"{trial_id}.csv"
        events_path = root / f"{trial_id}_events.json"
        summary_path = root / f"{trial_id}_summary.json"
        manifest_path = root / f"{trial_id}_manifest.json"
        fields = [
            "t_mono_ns", "event", "contact_confirmed", "intervention_state",
            "K_fb_commanded", "omega_x", "omega_y", "omega_z", "omega_valid",
            "F_ext_mag", "force_threshold_on_N", "force_corrected_N", "control_dt",
            "haptic_cmd_norm", "haptic_clamped", "haptic_send_ok", "safety_abort",
        ]
        rows = []
        contact_s = 1.0
        for index in range(0, 521):
            time_s = index * 0.005
            relative = time_s - contact_s
            active = spec.onset_s <= relative < spec.offset_s
            event = "contact_confirmed" if abs(time_s - contact_s) < 1e-9 else ""
            rows.append({
                "t_mono_ns": int(time_s * 1_000_000_000),
                "event": event,
                "contact_confirmed": int(time_s >= contact_s),
                "intervention_state": "intervention" if active else "hold_baseline",
                "K_fb_commanded": 0.7 if active else 0.5,
                "omega_x": 0.001 * time_s,
                "omega_y": 0.0,
                "omega_z": 0.002 * time_s,
                "omega_valid": 1,
                "F_ext_mag": 2.0,
                "force_threshold_on_N": 1.75,
                "force_corrected_N": 1.0,
                "control_dt": 0.005,
                "haptic_cmd_norm": 0.8,
                "haptic_clamped": 0,
                "haptic_send_ok": 1,
                "safety_abort": 0,
            })
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        events_path.write_text(json.dumps({"trial_id": trial_id}), encoding="utf-8")
        summary_path.write_text(json.dumps({"trial_id": trial_id}), encoding="utf-8")
        manifest = {
            "trial_id": trial_id,
            "participant_id": participant_id,
            "masked_condition": masked_condition,
            "protocol_phase": phase,
            "analyzed": analyzed,
            "completed": True,
            "incomplete": False,
            "config_sha256": config_hash(),
            "files": {
                "csv": {"path": csv_path.name, "sha256": sha256_file(csv_path)},
                "events": {"path": events_path.name, "sha256": sha256_file(events_path)},
                "summary": {"path": summary_path.name, "sha256": sha256_file(summary_path)},
            },
        }
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        oracle = {
            "trial_id": trial_id,
            "participant_id": participant_id,
            "phase": phase,
            "analyzed": str(int(analyzed)),
            "masked_condition": masked_condition,
            "true_condition": code,
            "scheduled_onset_s": f"{spec.onset_s:.3f}",
            "scheduled_offset_s": f"{spec.offset_s:.3f}",
            "expected_epsilon_s": f"{spec.expected_epsilon_s:.3f}",
            "expected_phi": f"{spec.expected_phi:.3f}",
            "config_sha256": config_hash(),
        }
        return manifest_path, oracle

    def test_reconstruction_and_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, oracle = self.make_trial(root)
            manifest = _load_manifests(root)[0]
            fidelity = reconstruct_trial(manifest)
            self.assertEqual(fidelity["inferred_condition"], "C3")
            self.assertAlmostEqual(float(fidelity["phi_hat"]), 0.5, delta=0.01)
            metric = trial_metrics(manifest, oracle, fidelity)
            self.assertEqual(metric["technical_valid"], 1)
            self.assertEqual(metric["H_computable"], 1)
            self.assertGreater(metric["post_contact_master_path_length_m"], 0)

    def test_freeze_then_unblind(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, oracle = self.make_trial(root)
            fidelity_path = root / "fidelity.csv"
            oracle_path = root / "oracle.csv"
            output_path = root / "unblinded.csv"
            with oracle_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(oracle))
                writer.writeheader()
                writer.writerow(oracle)
            command_reconstruct(root, fidelity_path)
            self.assertTrue(fidelity_path.with_suffix(".freeze.json").is_file())
            command_unblind(fidelity_path, oracle_path, output_path)
            row = _read_csv(output_path)[0]
            self.assertEqual(row["classification_correct"], "1")
            self.assertAlmostEqual(float(row["onset_error_s"]), 0.0, delta=0.006)
            results_dir = root / "results"
            command_analyze(root, output_path, oracle_path, results_dir)
            report = json.loads(
                (results_dir / "measured_acceptance.json").read_text(encoding="utf-8")
            )
            self.assertFalse(report["overall_pass"])
            self.assertFalse((results_dir / "engineering_acceptance.json").exists())

    def test_full_engineering_acceptance_pipeline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            oracle_rows = []
            for index in range(25):
                code = f"C{index % 5}"
                _, oracle = self.make_trial(
                    root,
                    code,
                    trial_id=f"ENG_E01_{index + 1:02d}",
                    participant_id="ENGINEER",
                    phase="engineering",
                    analyzed=False,
                    masked_condition=f"M{index + 1:07d}",
                )
                oracle_rows.append(oracle)
            oracle_path = root / "oracle.csv"
            with oracle_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(oracle_rows[0]))
                writer.writeheader()
                writer.writerows(oracle_rows)
            fidelity_path = root / "fidelity.csv"
            unblinded_path = root / "fidelity_unblinded.csv"
            results_dir = root / "results"
            command_reconstruct(root, fidelity_path)
            command_unblind(fidelity_path, oracle_path, unblinded_path)
            command_analyze(root, unblinded_path, oracle_path, results_dir)
            report = json.loads(
                (results_dir / "engineering_acceptance.json").read_text(encoding="utf-8")
            )
            self.assertTrue(report["overall_pass"], report["checks"])
            self.assertEqual(report["technical_valid_count"], 25)


if __name__ == "__main__":
    unittest.main()
