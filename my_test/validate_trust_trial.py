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
    "system_time", "control_dt", "F_ext_mag", "K_trans", "force_threshold",
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


def _percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return math.nan
    position = (len(ordered) - 1) * probability
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


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

    control_dt = [
        value for value in (_number(row["control_dt"]) for row in rows)
        if math.isfinite(value) and value > 0.0
    ]
    median_dt = _percentile(control_dt, 0.50)
    p99_dt = _percentile(control_dt, 0.99)
    over_50ms_fraction = (
        sum(value > 0.050 for value in control_dt) / len(control_dt)
        if control_dt else math.nan
    )
    add(
        "control_loop_quality",
        bool(control_dt)
        and median_dt <= 0.0075
        and p99_dt <= 0.020
        and over_50ms_fraction <= 0.001,
        f"median={median_dt:.6f}s, p99={p99_dt:.6f}s, "
        f">50ms={over_50ms_fraction:.3%}",
    )

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
    window_end_event = _event(events, "posterior_window_end")
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

    if correction_expected and window_end_event is not None and contact_event is not None:
        window_latency = _number(window_end_event.get("system_time")) - _number(
            contact_event.get("system_time")
        )
        add(
            "posterior_window_end_timing",
            0.80 <= window_latency <= 0.85,
            f"latency={window_latency:.4f}s",
        )
        end_time = _number(window_end_event.get("system_time"))
        post_rows = [row for row in rows if _number(row["system_time"]) >= end_time]
        post_stiffness = [_number(row["K_trans"]) for row in post_rows]
        post_trust = [_number(row["prior_trust"]) for row in post_rows]
        k_span = (
            max(post_stiffness) - min(post_stiffness) if post_stiffness else math.inf
        )
        trust_span = max(post_trust) - min(post_trust) if post_trust else math.inf
        add(
            "posterior_state_frozen_after_window",
            len(post_rows) >= 2 and k_span <= 1e-6 and trust_span <= 1e-9,
            f"rows={len(post_rows)}, K_span={k_span:.6g}, "
            f"trust_span={trust_span:.6g}",
        )
    elif correction_expected:
        add(
            "posterior_window_end_timing",
            False,
            "missing posterior_window_end event",
        )
        add(
            "posterior_state_frozen_after_window",
            False,
            "cannot verify without posterior_window_end event",
        )
    else:
        add(
            "posterior_window_absent_when_disabled",
            window_end_event is None,
            str(window_end_event),
        )

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
