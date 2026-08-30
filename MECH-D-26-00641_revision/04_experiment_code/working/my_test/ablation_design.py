"""Pure, hardware-independent definition of the confirmatory 2x2 ablation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping


SCHEMA_VERSION = 3
FIXED_BASELINE = {
    "K_trans": 150.0,
    "K_rot": 10.0,
    "damping_ratio": 1.0,
    "K_fb": 0.5,
    "deadband": 0.4,
    "scale": 3.0,
    "gripper_speed": 0.05,
    "gripper_force": 15.0,
}


@dataclass(frozen=True)
class AblationCondition:
    condition_id: str
    adaptive_impedance: bool
    adaptive_haptics: bool
    adaptive_gripper: bool


CONDITIONS = {
    "I": AblationCondition("I", True, False, False),
    "I_H": AblationCondition("I_H", True, True, False),
    "I_G": AblationCondition("I_G", True, False, True),
    "I_H_G": AblationCondition("I_H_G", True, True, True),
}


REQUIRED_PROFILE_KEYS = {
    "K_trans",
    "K_rot",
    "damping_ratio",
    "K_fb",
    "deadband",
    "scale",
    "gripper_speed",
    "gripper_force",
}


def resolve_parameters(condition_id: str, profile: Mapping[str, float]) -> dict:
    """Return the applied parameters while changing only the assigned factors."""
    if condition_id not in CONDITIONS:
        raise ValueError(f"Unknown ablation condition: {condition_id}")
    missing = REQUIRED_PROFILE_KEYS.difference(profile)
    if missing:
        raise ValueError(f"Profile is missing keys: {sorted(missing)}")

    condition = CONDITIONS[condition_id]
    resolved = dict(FIXED_BASELINE)
    if condition.adaptive_impedance:
        for key in ("K_trans", "K_rot", "damping_ratio"):
            resolved[key] = float(profile[key])
    if condition.adaptive_haptics:
        for key in ("K_fb", "deadband"):
            resolved[key] = float(profile[key])
    if condition.adaptive_gripper:
        for key in ("gripper_speed", "gripper_force"):
            resolved[key] = float(profile[key])

    resolved["scale"] = float(FIXED_BASELINE["scale"])
    resolved["effective_force_threshold_N"] = (
        resolved["deadband"] / resolved["K_fb"]
        if resolved["K_fb"] > 0
        else float("inf")
    )
    resolved.update(asdict(condition))
    return resolved


def design_manifest() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "fixed_baseline": dict(FIXED_BASELINE),
        "conditions": {key: asdict(value) for key, value in CONDITIONS.items()},
    }
