#!/usr/bin/env python3

from __future__ import annotations

import math
import unittest
from pathlib import Path

from analyze_kfb_runtime_exposure_v3 import (
    evidence_layers,
    exact_binomial_ci,
    interval_integral,
    participant_runtime_summary,
    record_command_summary,
)


class RuntimeExposureV3Tests(unittest.TestCase):
    def test_exact_clopper_pearson_for_294_of_294(self):
        low, high = exact_binomial_ci(294, 294)
        self.assertAlmostEqual(low, 0.9875311790067285, places=14)
        self.assertEqual(high, 1.0)

    def test_interval_integral_separates_step_and_continuous_values(self):
        rows = [
            {"t_mono_ns": 0, "flag": 0, "value": 0},
            {"t_mono_ns": 100_000_000, "flag": 1, "value": 1},
            {"t_mono_ns": 200_000_000, "flag": 1, "value": 2},
        ]
        flag_total, flag_coverage = interval_integral(rows, 0.05, 0.20, "flag", 0.11, step=True)
        value_total, value_coverage = interval_integral(rows, 0.05, 0.20, "value", 0.11)
        self.assertAlmostEqual(flag_total, 0.10)
        self.assertAlmostEqual(flag_coverage, 0.15)
        self.assertAlmostEqual(value_total, 0.1875)
        self.assertAlmostEqual(value_coverage, 0.15)

    def test_evidence_layers_never_substitute_command_for_physical_delivery(self):
        layers = {row["layer"]: row for row in evidence_layers()}
        self.assertEqual(layers["D_i^phys"]["status"], "NOT_INDEPENDENTLY_OBSERVED")
        self.assertIn("software_command", layers["R_i^cmd"]["status"].lower())
        self.assertIn("not physical", layers["R_i^cmd"]["claim_boundary"].lower())

    def test_participant_summary_uses_participants_not_trials_as_units(self):
        rows = []
        for participant, durations in (("F01", (1.0, 2.0)), ("F02", (3.0, 5.0))):
            for duration in durations:
                rows.append({
                    "participant_id": participant,
                    "fidelity_evaluable": 1,
                    "classification_correct": 1,
                    "onset_error_s": 0.002,
                    "phi_error": 0.001,
                    "approach_duration_s": duration,
                    "approach_robot_path_m": 0.01,
                    "approach_robot_peak_speed_m_s": 0.02,
                    "excess_force_impulse_Ns": 0.3,
                    "haptic_clamped_any": 0,
                    "haptic_clamped_window_fraction": 0.0,
                })
        summary = participant_runtime_summary(rows)
        self.assertEqual(len(summary), 2)
        self.assertEqual(summary[0]["approach_duration_mean_s"], 1.5)
        self.assertEqual(summary[1]["approach_duration_mean_s"], 4.0)

    def test_real_outputs_preserve_c4_window_binding(self):
        root = Path(__file__).resolve().parent
        analysis = root / "正宫" / "25_runtime_exposure_submission_bundle_v3" / "analysis"
        metrics_path = analysis / "trial_metrics.csv"
        if not metrics_path.is_file():
            self.skipTest("v3 formal outputs not present")
        import analyze_kfb_timing_formal as base

        metrics = base.read_csv(metrics_path)
        command = record_command_summary(metrics)
        c4 = next(row for row in command if row["condition"] == "C4")
        overall = next(row for row in command if row["condition"] == "OVERALL")
        self.assertEqual(c4["any_trial_clamp_trials"], 11)
        self.assertEqual(c4["outcome_window_clamp_trials"], 0)
        self.assertEqual(overall["outcome_window_clamp_trials"], 47)
        self.assertTrue(math.isfinite(overall["command_integral_trial_mean_Ns"]))


if __name__ == "__main__":
    unittest.main()
