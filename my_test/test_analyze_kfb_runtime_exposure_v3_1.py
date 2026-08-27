import csv
import hashlib
import json
import unittest
from pathlib import Path

import analyze_kfb_runtime_exposure_v3_1 as v31


ROOT = Path(__file__).resolve().parent
BUNDLE = ROOT / "正宫" / "26_runtime_exposure_submission_bundle_v3_1"
ANALYSIS = BUNDLE / "analysis"


def rows(name):
    with (ANALYSIS / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


class RuntimeExposureV31Tests(unittest.TestCase):
    def test_exact_participant_units_and_queue(self):
        cohort = rows("analysis_cohort_manifest.csv")
        human = rows("participant_human_variability.csv")
        self.assertEqual(len(cohort), 300)
        self.assertEqual(len(human), 20)
        self.assertEqual({r["participant_id"] for r in human}, {f"F{i:02d}" for i in range(1, 21)})
        self.assertEqual({r["analysis_unit"] for r in human}, {"participant"})
        self.assertEqual(sum(int(r["completed"]) for r in cohort), 294)
        self.assertEqual(sum(int(r["incomplete"]) for r in cohort), 6)

    def test_human_stressors_and_expected_ranges(self):
        range_rows = {r["stressor"]: r for r in rows("human_variability_range.csv")}
        expected = {
            "approach_duration", "omega_path", "panda_path", "panda_peak_speed",
            "internal_force_impulse", "whole_trial_clamp_rate",
            "outcome_window_clamp_trial_rate", "approach_duration_all_trials",
        }
        self.assertEqual(set(range_rows), expected)
        self.assertAlmostEqual(float(range_rows["omega_path"]["participant_mean_min"]), 0.023673988333101356)
        self.assertAlmostEqual(float(range_rows["omega_path"]["participant_mean_max"]), 0.04642987106651571)
        self.assertAlmostEqual(float(range_rows["panda_path"]["participant_mean_max"]), 0.024442109574783988)
        self.assertAlmostEqual(float(range_rows["panda_peak_speed"]["participant_mean_min"]), 0.026773697681679025)
        self.assertAlmostEqual(float(range_rows["internal_force_impulse"]["participant_mean_max"]), 1.188103191985815)
        self.assertAlmostEqual(float(range_rows["whole_trial_clamp_rate"]["participant_mean_max"]), 0.7857142857142857)

    def test_continuous_associations_are_participant_level_and_deterministic(self):
        association_rows = rows("human_variability_associations.csv")
        self.assertEqual(len(association_rows), 12)
        self.assertEqual({r["participant_count"] for r in association_rows}, {"20"})
        self.assertEqual({r["p_value_computed"] for r in association_rows}, {"0"})
        self.assertNotIn("classification_accuracy", {r["outcome"] for r in association_rows})
        participant_rows = [{k: (float(v) if k not in {"participant_id", "analysis_unit"} else v) for k, v in r.items()} for r in rows("participant_human_variability.csv")]
        first_rows, first_provenance = v31.human_variability_associations(participant_rows)
        expected_rows = [{k: (float(v) if k not in {"stressor", "stressor_unit", "evidence_category", "outcome", "analysis_role"} else v) for k, v in r.items()} for r in association_rows]
        self.assertEqual(first_rows, expected_rows)
        self.assertEqual(first_provenance["seed"], 20260827)
        self.assertEqual(first_provenance["requested_replicates"], 10000)

    def test_worst_participant_margins_are_below_limits(self):
        human = rows("participant_human_variability.csv")
        timing = max(float(r["timing_mae_fraction_of_limit"]) for r in human)
        exposure = max(float(r["exposure_mae_fraction_of_limit"]) for r in human)
        self.assertAlmostEqual(timing, 0.1526000666666731)
        self.assertAlmostEqual(exposure, 0.12605323333332827)
        self.assertLess(timing, 1.0)
        self.assertLess(exposure, 1.0)

    def test_retrospective_diagnostic_is_fixed(self):
        summary = {r["configuration"]: r for r in rows("retrospective_diagnostic_summary.csv")}
        self.assertEqual(set(summary), {"A", "G", "E", "F"})
        self.assertIn("43/45", summary["G"]["key_discrepancy"])
        self.assertIn("3/45", summary["F"]["runtime_evidence"])
        self.assertIn("39 full / 2 partial / 4 zero", summary["E"]["runtime_evidence"])
        self.assertIn("35/7/3", summary["F"]["runtime_evidence"])

    def test_figures_exactly_five_in_three_formats(self):
        figures = ANALYSIS / "figures"
        stems = {
            "fig1_five_layer_framework", "fig2_retrospective_discontinuities",
            "fig3_record_layer_recovery", "fig4_outcome_window_binding",
            "fig5_human_variability_stress_test",
        }
        for extension in ("png", "svg", "pdf"):
            paths = list(figures.glob(f"*.{extension}"))
            self.assertEqual({p.stem for p in paths}, stems)
            self.assertTrue(all(p.stat().st_size > 1000 for p in paths))

    def test_evidence_layers_do_not_merge_command_and_delivery(self):
        layers = {r["layer"]: r for r in rows("evidence_layer_status.csv")}
        self.assertEqual(layers["D_i^phys"]["status"], "NOT_INDEPENDENTLY_OBSERVED")
        commands = rows("record_command_summary.csv")
        self.assertEqual({r["physical_delivery_status"] for r in commands}, {"NOT_INDEPENDENTLY_OBSERVED"})
        self.assertEqual(next(r for r in commands if r["condition"] == "C4")["outcome_window_clamp_trials"], "0")

    def test_bootstrap_artifact_matches_generated_rows(self):
        provenance = json.loads((ANALYSIS / "bootstrap_provenance.json").read_text(encoding="utf-8"))
        self.assertEqual(provenance["seed"], 20260827)
        self.assertEqual(provenance["requested_replicates"], 10000)
        self.assertEqual(provenance["analysis_unit"], "participant")
        digest = hashlib.sha256((ANALYSIS / "human_variability_associations.csv").read_bytes()).hexdigest()
        self.assertEqual(len(digest), 64)


if __name__ == "__main__":
    unittest.main()
