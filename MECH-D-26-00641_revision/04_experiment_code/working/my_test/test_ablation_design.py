import unittest
import math

from ablation_design import CONDITIONS, FIXED_BASELINE, resolve_parameters
from experiment_protocol import json_safe
from run_scheduled_trial import group_directory_name


PROFILE = {
    "K_trans": 50.0,
    "K_rot": 5.0,
    "damping_ratio": 0.8,
    "K_fb": 0.2,
    "deadband": 0.3,
    "scale": 9.0,
    "gripper_speed": 0.02,
    "gripper_force": 8.0,
}

MEDIUM_PROFILE = {
    "K_trans": 150.0, "K_rot": 10.0, "damping_ratio": 1.0,
    "K_fb": 0.5, "deadband": 0.4, "scale": 3.0,
    "gripper_speed": 0.05, "gripper_force": 20.0,
}


class AblationDesignTests(unittest.TestCase):
    def test_exact_condition_ids(self):
        self.assertEqual(set(CONDITIONS), {"I", "I_H", "I_G", "I_H_G"})

    def test_impedance_is_adaptive_in_all_conditions(self):
        for condition_id in CONDITIONS:
            resolved = resolve_parameters(condition_id, PROFILE)
            self.assertEqual(resolved["K_trans"], PROFILE["K_trans"])
            self.assertEqual(resolved["K_rot"], PROFILE["K_rot"])
            self.assertEqual(resolved["damping_ratio"], PROFILE["damping_ratio"])

    def test_haptic_factor_only_changes_haptic_parameters(self):
        off = resolve_parameters("I", PROFILE)
        on = resolve_parameters("I_H", PROFILE)
        changed = {key for key in off if off[key] != on[key]}
        self.assertEqual(changed, {
            "condition_id", "K_fb", "deadband", "effective_force_threshold_N",
            "adaptive_haptics",
        })
        self.assertEqual(off["K_fb"], FIXED_BASELINE["K_fb"])
        self.assertEqual(off["deadband"], FIXED_BASELINE["deadband"])

    def test_gripper_factor_only_changes_gripper_parameters(self):
        off = resolve_parameters("I", PROFILE)
        on = resolve_parameters("I_G", PROFILE)
        changed = {key for key in off if off[key] != on[key]}
        self.assertEqual(changed, {
            "condition_id", "gripper_speed", "gripper_force", "adaptive_gripper",
        })

    def test_scale_is_never_a_hidden_factor(self):
        for condition_id in CONDITIONS:
            self.assertEqual(resolve_parameters(condition_id, PROFILE)["scale"], 3.0)

    def test_medium_profile_has_real_h_and_g_manipulations(self):
        baseline = resolve_parameters("I", MEDIUM_PROFILE)
        haptic = resolve_parameters("I_H", MEDIUM_PROFILE)
        gripper = resolve_parameters("I_G", MEDIUM_PROFILE)
        self.assertNotEqual(
            (baseline["K_fb"], baseline["deadband"]),
            (haptic["K_fb"], haptic["deadband"]),
        )
        self.assertNotEqual(
            (baseline["gripper_speed"], baseline["gripper_force"]),
            (gripper["gripper_speed"], gripper["gripper_force"]),
        )

    def test_json_safe_replaces_non_finite_values(self):
        cleaned = json_safe({"finite": 1.0, "missing": math.nan})
        self.assertEqual(cleaned, {"finite": 1.0, "missing": None})

    def test_group_directory_keeps_four_conditions_together(self):
        common = {"object_order": "4", "object_id": "banana", "repetition": "1"}
        names = {
            group_directory_name({**common, "condition": condition})
            for condition in CONDITIONS
        }
        self.assertEqual(names, {"G04_banana_R1"})

    def test_group_directory_separates_repetitions(self):
        first = group_directory_name({
            "object_order": "2", "object_id": "cup", "repetition": "1",
        })
        second = group_directory_name({
            "object_order": "2", "object_id": "cup", "repetition": "2",
        })
        self.assertEqual(first, "G02_cup_R1")
        self.assertEqual(second, "G02_cup_R2")


if __name__ == "__main__":
    unittest.main()
