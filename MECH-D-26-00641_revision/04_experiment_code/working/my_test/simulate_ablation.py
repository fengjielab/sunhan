"""Hardware-free verification that only the assigned ablation factors change."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ablation_design import CONDITIONS, FIXED_BASELINE, resolve_parameters


PROFILES = {
    "soft": {
        "K_trans": 50.0, "K_rot": 5.0, "damping_ratio": 0.8,
        "K_fb": 0.2, "deadband": 0.3, "scale": 3.0,
        "gripper_speed": 0.02, "gripper_force": 8.0,
    },
    "medium": {
        "K_trans": 150.0, "K_rot": 10.0, "damping_ratio": 1.0,
        "K_fb": 0.5, "deadband": 0.4, "scale": 3.0,
        "gripper_speed": 0.05, "gripper_force": 20.0,
    },
    "hard": {
        "K_trans": 200.0, "K_rot": 13.0, "damping_ratio": 1.2,
        "K_fb": 0.7, "deadband": 0.5, "scale": 3.0,
        "gripper_speed": 0.10, "gripper_force": 20.0,
    },
}


def verify():
    report = {"status": "pass", "fixed_baseline": FIXED_BASELINE, "profiles": {}}
    for profile_name, profile in PROFILES.items():
        resolved = {
            condition_id: resolve_parameters(condition_id, profile)
            for condition_id in CONDITIONS
        }
        for condition_id, values in resolved.items():
            assert values["adaptive_impedance"] is True
            if not values["adaptive_haptics"]:
                assert values["K_fb"] == FIXED_BASELINE["K_fb"]
                assert values["deadband"] == FIXED_BASELINE["deadband"]
            if not values["adaptive_gripper"]:
                assert values["gripper_speed"] == FIXED_BASELINE["gripper_speed"]
                assert values["gripper_force"] == FIXED_BASELINE["gripper_force"]
            assert values["scale"] == FIXED_BASELINE["scale"]
            if values["adaptive_haptics"]:
                assert (
                    values["K_fb"], values["deadband"]
                ) != (
                    FIXED_BASELINE["K_fb"], FIXED_BASELINE["deadband"]
                ), f"{profile_name}/{condition_id} has no H manipulation"
            if values["adaptive_gripper"]:
                assert (
                    values["gripper_speed"], values["gripper_force"]
                ) != (
                    FIXED_BASELINE["gripper_speed"],
                    FIXED_BASELINE["gripper_force"],
                ), f"{profile_name}/{condition_id} has no G manipulation"
        report["profiles"][profile_name] = resolved
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = verify()
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
        print(f"PASS: wrote {args.output}")
    else:
        print(text)


if __name__ == "__main__":
    main()
