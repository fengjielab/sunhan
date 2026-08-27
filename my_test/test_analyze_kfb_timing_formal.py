#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from analyze_kfb_timing_formal import (
    acceptance_report,
    build_cohort,
    classify,
    load_oracle,
    load_protocol,
    parse_participants,
    sha256_text,
)


class FormalAnalysisTests(unittest.TestCase):
    def test_participant_range_is_exact(self):
        participants = parse_participants("F01-F20")
        self.assertEqual(len(participants), 20)
        self.assertEqual(participants[0], "F01")
        self.assertEqual(participants[-1], "F20")
        with self.assertRaises(ValueError):
            parse_participants("F20-F01")

    def test_text_hash_normalizes_newlines_and_bom(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            linux = root / "linux.json"
            windows = root / "windows.json"
            linux.write_bytes(b'{\n  "ok": true\n}\n')
            windows.write_bytes(b'\xef\xbb\xbf{\r\n  "ok": true\r\n}\r\n')
            expected = hashlib.sha256(linux.read_bytes()).hexdigest()
            self.assertEqual(sha256_text(linux), expected)
            self.assertEqual(sha256_text(windows), expected)

    def test_classification_uses_frozen_truth(self):
        conditions = {
            "C0": {"onset_s": 0.20, "offset_s": 1.20, "expected_phi": 1.0},
            "C1": {"onset_s": 0.05, "offset_s": 1.20, "expected_phi": 1.0},
            "C2": {"onset_s": 0.50, "offset_s": 1.20, "expected_phi": 0.625},
            "C3": {"onset_s": 0.20, "offset_s": 0.60, "expected_phi": 0.5},
            "C4": {"onset_s": 1.10, "offset_s": 1.30, "expected_phi": 0.0},
        }
        self.assertEqual(classify(0.203, 0.598, 0.501, conditions), "C3")
        self.assertEqual(classify(1.098, 1.302, 0.0, conditions), "C4")

    def test_extra_participant_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "F01").mkdir()
            (root / "F99").mkdir()
            with self.assertRaisesRegex(RuntimeError, "participant directory mismatch"):
                build_cohort(root, ["F01"], {}, "unused")

    def test_clamping_does_not_change_primary_acceptance(self):
        fidelity = [{
            "condition": "OVERALL",
            "classification_accuracy": 1.0,
            "timing_mae_s": 0.003,
            "timing_p95_abs_error_s": 0.005,
            "timing_max_abs_error_s": 0.006,
            "exposure_mae": 0.002,
        }]
        quality = [{
            "condition": "OVERALL",
            "planned_trials": 300,
            "completed_trials": 294,
            "fidelity_evaluable_trials": 294,
            "safety_abort_trials": 6,
            "haptic_clamped_completed_trials": 65,
        }]
        report = acceptance_report(fidelity, quality)
        self.assertTrue(report["overall_primary_pass"])
        self.assertEqual(report["haptic_clamped_completed_trials"], 65)

    def test_real_formal_cohort_contract(self):
        root = Path(__file__).resolve().parent
        data_dir = root / "data" / "kfb_timing_formal_v1" / "participants"
        if not data_dir.is_dir():
            self.skipTest("formal acquisition data not present")
        protocol_path = root / "正宫" / "23_kfb_timing_pilot" / "frozen_schedule_formal_v1" / "protocol_config_v1.json"
        oracle_path = root / "正宫" / "23_kfb_timing_pilot" / "frozen_schedule_formal_v1" / "private_oracle" / "oracle.csv"
        participants = parse_participants("F01-F20")
        protocol = load_protocol(protocol_path)
        oracle = load_oracle(oracle_path, participants, protocol["config_sha256"])
        queue, _ = build_cohort(data_dir, participants, oracle, protocol["config_sha256"])
        self.assertEqual(len(queue), 300)
        self.assertEqual(sum(int(row["completed"]) for row in queue), 294)
        self.assertEqual(sum(row["csv_verification"] == "byte_exact" for row in queue), 300)
        self.assertEqual(sum(row["events_verification"] == "canonical_text_exact" for row in queue), 300)
        self.assertEqual(sum(row["summary_verification"] == "canonical_text_exact" for row in queue), 300)


if __name__ == "__main__":
    unittest.main()
