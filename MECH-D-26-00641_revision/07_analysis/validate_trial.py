"""Validate one schema-v3 raw trial without modifying acquisition files."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path


CONDITION_FLAGS = {
    "I": (1, 0, 0),
    "I_H": (1, 1, 0),
    "I_G": (1, 0, 1),
    "I_H_G": (1, 1, 1),
}
REQUIRED_COLUMNS = {
    "schema_version", "system_time", "operation_time", "phase", "event",
    "mode", "run_uuid", "run_kind", "session_id", "schedule_id",
    "subject_id", "object_id", "trial_id", "trial_order", "repetition",
    "adaptive_impedance", "adaptive_haptics", "adaptive_gripper",
    "K_trans", "K_rot", "damping_ratio", "K_fb", "deadband",
    "gripper_speed", "gripper_force", "vision_class", "vision_confidence",
    "vision_locked", "capture_perf_time_ns", "inference_start_perf_time_ns",
    "inference_end_perf_time_ns", "result_receive_perf_time_ns",
    "vision_queue_age_ms", "parameter_apply_start_perf_time_ns",
    "parameter_apply_end_perf_time_ns", "u_h_base_x", "u_h_base_y",
    "u_h_base_z", "u_g_aperture_N", "u_h_cmd_x", "u_h_cmd_y",
    "u_h_cmd_z", "u_h_cmd_norm_N", "haptic_force_limit_N",
    "haptic_saturated", "control_dt", "control_overrun_s",
    "control_deadline_miss",
}


def number(value, default=math.nan):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def unique(rows, key):
    return {row.get(key, "") for row in rows}


def validate(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
        columns = set(reader.fieldnames or [])

    errors, warnings = [], []
    missing = sorted(REQUIRED_COLUMNS - columns)
    if missing:
        errors.append(f"missing columns: {missing}")
    if len(rows) < 10:
        errors.append(f"too few samples: {len(rows)}")
    if not rows:
        return {"status": "fail", "errors": errors, "warnings": warnings}

    for key in ("schema_version", "mode", "run_uuid", "run_kind", "session_id",
                "schedule_id", "subject_id", "object_id", "trial_id",
                "trial_order", "repetition"):
        values = unique(rows, key)
        if len(values) != 1:
            errors.append(f"metadata changes within trial: {key}={sorted(values)}")

    if unique(rows, "schema_version") != {"3"}:
        errors.append(f"schema is not v3: {sorted(unique(rows, 'schema_version'))}")
    condition = next(iter(unique(rows, "mode")))
    if condition not in CONDITION_FLAGS:
        errors.append(f"unknown condition: {condition}")
    else:
        observed = tuple(int(number(rows[0].get(key), -1)) for key in
                         ("adaptive_impedance", "adaptive_haptics", "adaptive_gripper"))
        if observed != CONDITION_FLAGS[condition]:
            errors.append(f"factor flags {observed} do not match {condition}")

    times = [number(row.get("system_time")) for row in rows]
    if any(not math.isfinite(value) for value in times):
        errors.append("non-finite system_time")
    elif any(later < earlier for earlier, later in zip(times, times[1:])):
        errors.append("system_time is not monotonic")

    locked_rows = [row for row in rows if row.get("vision_locked") == "1"]
    events = "|".join(row.get("event", "") for row in rows)
    for event in ("task_start", "vision_lock"):
        if event not in events:
            errors.append(f"missing required event: {event}")
    if not locked_rows:
        errors.append("no samples after vision lock")
    else:
        timing_fields = (
            "capture_perf_time_ns", "inference_start_perf_time_ns",
            "inference_end_perf_time_ns", "result_receive_perf_time_ns",
            "parameter_apply_start_perf_time_ns",
        )
        for key in timing_fields:
            if number(locked_rows[-1].get(key), 0) <= 0:
                errors.append(f"missing locked-trial timing: {key}")

    force_violations = 0
    for row in rows:
        command = number(row.get("u_h_cmd_norm_N"))
        limit = number(row.get("haptic_force_limit_N"))
        if math.isfinite(command) and math.isfinite(limit) and command > limit + 1e-6:
            force_violations += 1
    if force_violations:
        errors.append(f"{force_violations} haptic commands exceed software limit")

    dts = [number(row.get("control_dt")) for row in rows]
    dts = [value for value in dts if math.isfinite(value)]
    deadline_misses = sum(int(number(row.get("control_deadline_miss"), 0)) for row in rows)
    saturations = sum(int(number(row.get("haptic_saturated"), 0)) for row in rows)
    if "task_end" not in events:
        warnings.append("trial has no successful task_end event")

    report = {
        "status": "pass" if not errors else "fail",
        "file": str(path.resolve()),
        "condition": condition,
        "run_uuid": next(iter(unique(rows, "run_uuid"))),
        "samples": len(rows),
        "errors": errors,
        "warnings": warnings,
        "metrics": {
            "duration_s": times[-1] - times[0] if len(times) > 1 else 0,
            "control_dt_mean_ms": 1000 * sum(dts) / len(dts) if dts else None,
            "control_dt_max_ms": 1000 * max(dts) if dts else None,
            "deadline_miss_count": deadline_misses,
            "deadline_miss_rate": deadline_misses / len(rows),
            "haptic_saturation_count": saturations,
            "haptic_saturation_rate": saturations / len(rows),
        },
    }
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = validate(args.csv)
    output = args.output or args.csv.with_name(args.csv.stem + "_validation.json")
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{report['status'].upper()}: {output}")
    if report["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
