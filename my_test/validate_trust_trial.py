#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证单个 C0/C1/W0/W1 试次的条件身份、时序、边界与日志完整性。"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Iterable


REQUIRED_COLUMNS = {
    "system_time", "F_ext_mag", "K_trans", "force_threshold",
    "condition_code", "actual_object", "prior_condition",
    "posterior_correction", "prior_K", "prior_trust",
    "contact_risk_ema", "trust_target_K", "trust_config_hash",
    "raw_vision_class", "raw_vision_label", "raw_vision_confidence",
}


def _number(value: str, default: float = math.nan) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _constant(rows: list[dict], key: str) -> set[str]:
    return {str(row.get(key, "")).strip() for row in rows}


def _find_events_path(csv_path: Path) -> Path:
    candidate = csv_path.with_name(csv_path.stem + "_events.json")
    if not candidate.exists():
        raise FileNotFoundError(f"missing events JSON: {candidate}")
    return candidate


def _load_events(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("events"), list):
        return payload["events"]
    raise ValueError(f"cannot locate event list in {path}")


def _event(events: Iterable[dict], name: str) -> dict | None:
    return next((event for event in events if event.get("event") == name), None)


def validate(csv_path: Path) -> dict:
    with csv_path.open("r", newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("trajectory CSV has no rows")

    checks: list[dict] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    missing = REQUIRED_COLUMNS - set(rows[0])
    add("required_columns", not missing, f"missing={sorted(missing)}")
    if missing:
        return {"file": str(csv_path), "passed": False, "checks": checks}

    condition_values = _constant(rows, "condition_code")
    object_values = _constant(rows, "actual_object")
    hash_values = _constant(rows, "trust_config_hash") - {""}
    add(
        "constant_condition_identity",
        len(condition_values) == len(object_values) == len(hash_values) == 1,
        f"condition={condition_values}, object={object_values}, hash={hash_values}",
    )
    condition = next(iter(condition_values)) if len(condition_values) == 1 else ""
    correction_expected = condition in ("C1", "W1")

    stiffness = [_number(row["K_trans"]) for row in rows]
    trust = [_number(row["prior_trust"]) for row in rows]
    add(
        "stiffness_bounds",
        all(50.0 - 1e-6 <= value <= 200.0 + 1e-6 for value in stiffness),
        f"min={min(stiffness):.3f}, max={max(stiffness):.3f}",
    )
    max_step = max((abs(b - a) for a, b in zip(stiffness, stiffness[1:])), default=0.0)
    add("stiffness_step_limit", max_step <= 20.0 + 1e-6, f"max_step={max_step:.3f}")
    max_trust_increase = max((b - a for a, b in zip(trust, trust[1:])), default=0.0)
    add(
        "trust_monotonic_nonincrease",
        max_trust_increase <= 1e-9,
        f"max_increase={max_trust_increase:.6g}",
    )

    prior_values = {_number(row["prior_K"]) for row in rows}
    prior_K = next(iter(prior_values)) if len(prior_values) == 1 else math.nan
    if not correction_expected:
        max_deviation = max(abs(value - prior_K) for value in stiffness)
        add(
            "no_correction_condition_is_fixed",
            max_deviation <= 1e-6 and all(abs(value - 1.0) <= 1e-9 for value in trust),
            f"max_K_deviation={max_deviation:.6g}, min_trust={min(trust):.6g}",
        )

    events = _load_events(_find_events_path(csv_path))
    prior_event = _event(events, "prior_applied")
    contact_event = _event(events, "contact_onset")
    override_event = _event(events, "posterior_override_start")
    safety_event = _event(events, "safety_stop")
    add("prior_event_present", prior_event is not None, str(prior_event))
    add("contact_event_present", contact_event is not None, str(contact_event))
    if override_event is not None and contact_event is not None:
        latency = _number(override_event.get("system_time")) - _number(
            contact_event.get("system_time")
        )
        add("override_after_contact_delay", latency >= 0.05 - 1e-6, f"latency={latency:.4f}s")
    elif correction_expected:
        add(
            "override_after_contact_delay",
            False,
            "no posterior_override_start event; acceptable only if no risk exceeded the guard",
        )
    else:
        add("override_absent_when_disabled", override_event is None, str(override_event))

    confidences = [_number(row["raw_vision_confidence"]) for row in rows]
    detected = any(math.isfinite(value) for value in confidences)
    add("raw_vision_recorded", detected, "at least one finite confidence required")

    longest_high_force_s = 0.0
    high_force_start = None
    previous_time = None
    for row in rows:
        sample_time = _number(row.get("system_time"))
        force_mag = _number(row.get("F_ext_mag"))
        if force_mag >= 12.0:
            if high_force_start is None:
                high_force_start = sample_time
            previous_time = sample_time
            longest_high_force_s = max(
                longest_high_force_s, previous_time - high_force_start
            )
        else:
            high_force_start = None
            previous_time = None
    add(
        "safety_event_consistency",
        longest_high_force_s < 0.10 - 1e-3 or safety_event is not None,
        f"longest_at_or_above_12N={longest_high_force_s:.4f}s, "
        f"safety_event={safety_event is not None}",
    )

    return {
        "file": str(csv_path),
        "condition_code": condition,
        "passed": all(item["passed"] for item in checks),
        "checks": checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path, help="trust_experiment_*.csv")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()
    report = validate(args.csv.resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        with args.json_out.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
