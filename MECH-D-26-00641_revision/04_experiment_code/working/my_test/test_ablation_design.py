import unittest

from ablation_design import CONDITIONS, FIXED_BASELINE, resolve_parameters


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


if __name__ == "__main__":
    unittest.main()
