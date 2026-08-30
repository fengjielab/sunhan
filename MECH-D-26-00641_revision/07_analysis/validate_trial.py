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
EXPECTED_OBJECT_LABEL = {
    "apple": "soft", "banana": "soft",
    "bottle": "medium", "cup": "medium",
    "mouse": "hard", "scissors": "hard",
}
WARNING_DEADLINE_MISS_RATE = 0.10
FAIL_DEADLINE_MISS_RATE = 0.25
WARNING_HAPTIC_SATURATION_RATE = 0.05
FAIL_HAPTIC_SATURATION_RATE = 0.20
REQUIRED_COLUMNS = {
    "schema_version", "system_time", "operation_time", "phase", "event",
    "mode", "run_uuid", "run_kind", "session_id", "schedule_id",
    "subject_id", "object_id", "trial_id", "trial_order", "repetition",
    "adaptive_impedance", "adaptive_haptics", "adaptive_gripper",
    "K_trans", "K_rot", "damping_ratio", "K_fb", "deadband",
    "gripper_speed", "gripper_force", "vision_class", "vision_locked_class",
    "vision_label", "vision_confidence", "vision_locked",
    "capture_perf_time_ns", "inference_start_perf_time_ns",
    "inference_end_perf_time_ns", "result_receive_perf_time_ns",
    "vision_queue_age_ms", "parameter_apply_start_perf_time_ns",
    "parameter_apply_end_perf_time_ns", "u_h_base_x", "u_h_base_y",
    "u_h_base_z", "u_g_aperture_N", "u_h_cmd_x", "u_h_cmd_y",
    "u_h_cmd_z", "u_h_cmd_norm_N", "haptic_force_limit_N",
    "haptic_saturated", "control_target_frequency_hz", "control_target_dt_s",
    "control_dt", "control_compute_time_s", "control_overrun_s",
    "control_deadline_miss",
}


def number(value, default=math.nan):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def unique(rows, key):
    return {row.get(key, "") for row in rows}


def percentile(values, fraction):
    values = sorted(values)
    if not values:
        return math.nan
    position = (len(values) - 1) * fraction
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return values[lower]
    weight = position - lower
    return values[lower] * (1 - weight) + values[upper] * weight


def differs(a, b, tolerance=1e-9):
    return math.isfinite(a) and math.isfinite(b) and abs(a - b) > tolerance


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
                "trial_order", "repetition", "control_target_frequency_hz",
                "control_target_dt_s"):
        values = unique(rows, key)
        if len(values) != 1:
            errors.append(f"metadata changes within trial: {key}={sorted(values)}")

    if unique(rows, "schema_version") != {"3"}:
        errors.append(f"schema is not v3: {sorted(unique(rows, 'schema_version'))}")
    condition = next(iter(unique(rows, "mode")))
    run_kind = next(iter(unique(rows, "run_kind")))
    run_uuid = next(iter(unique(rows, "run_uuid")))
    object_id = next(iter(unique(rows, "object_id")))
    if condition not in CONDITION_FLAGS:
        errors.append(f"unknown condition: {condition}")
    else:
        observed = tuple(int(number(rows[0].get(key), -1)) for key in
                         ("adaptive_impedance", "adaptive_haptics", "adaptive_gripper"))
        if observed != CONDITION_FLAGS[condition]:
            errors.append(f"factor flags {observed} do not match {condition}")

    config = None
    config_path = path.with_name(f"run_config_{run_uuid}.json")
    if config_path.is_file():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid run config {config_path.name}: {exc}")
    elif run_kind in ("pilot", "formal"):
        errors.append(f"missing run config: {config_path.name}")

    if config is not None:
        for key in ("run_uuid", "run_kind", "session_id", "schedule_id",
                    "subject_id", "object_id", "trial_id", "trial_order",
                    "repetition", "condition"):
            csv_key = "mode" if key == "condition" else key
            csv_value = next(iter(unique(rows, csv_key)))
            if str(config.get(key, "")) != str(csv_value):
                errors.append(
                    f"run config mismatch: {key}={config.get(key)!r}, "
                    f"CSV={csv_value!r}"
                )
        config_control = config.get("control", {})
        csv_frequency = number(next(iter(unique(rows, "control_target_frequency_hz"))))
        csv_target_dt = number(next(iter(unique(rows, "control_target_dt_s"))))
        if not math.isclose(
                number(config_control.get("target_frequency_hz")),
                csv_frequency, rel_tol=1e-9, abs_tol=1e-12):
            errors.append("run config control frequency does not match CSV")
        if not math.isclose(
                number(config_control.get("target_period_s")),
                csv_target_dt, rel_tol=1e-9, abs_tol=1e-12):
            errors.append("run config control target period does not match CSV")

    times = [number(row.get("system_time")) for row in rows]
    if any(not math.isfinite(value) for value in times):
        errors.append("non-finite system_time")
    elif any(later < earlier for earlier, later in zip(times, times[1:])):
        errors.append("system_time is not monotonic")

    locked_rows = [row for row in rows if row.get("vision_locked") == "1"]
    event_tokens = [
        event for row in rows for event in row.get("event", "").split("|") if event
    ]
    events = "|".join(event_tokens)
    required_events = (
        "force_baseline_ready", "vision_lock", "parameter_transition_end",
        "system_ready", "task_start", "grasp_start", "grasp_success",
        "release_start",
    )
    for event in required_events:
        if event not in events:
            errors.append(f"missing required event: {event}")
    event_order = required_events + (("task_end",) if "task_end" in events else ())
    positions = [event_tokens.index(event) for event in event_order if event in event_tokens]
    if positions != sorted(positions):
        errors.append(f"phase events are out of order: {event_order}")
    if run_kind in ("pilot", "formal") and "task_end" not in events:
        errors.append("pilot/formal trial has no successful task_end event")
    if "task_incomplete" in events:
        errors.append("trial contains task_incomplete")
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

        locked_class = locked_rows[-1].get("vision_locked_class", "")
        locked_label = locked_rows[-1].get("vision_label", "")
        if locked_class != object_id:
            errors.append(
                f"vision locked class {locked_class!r} does not match "
                f"scheduled object {object_id!r}"
            )
        expected_label = EXPECTED_OBJECT_LABEL.get(object_id)
        if expected_label and locked_label != expected_label:
            errors.append(
                f"vision label {locked_label!r} does not match "
                f"{object_id!r} expected label {expected_label!r}"
            )

        if config is not None:
            baseline = config.get("design", {}).get("fixed_baseline", {})
            final = locked_rows[-1]
            for key in ("K_fb", "deadband", "gripper_speed", "gripper_force"):
                if not math.isfinite(number(baseline.get(key))):
                    errors.append(f"run config baseline is missing finite {key}")
            haptic_on = CONDITION_FLAGS.get(condition, (0, 0, 0))[1] == 1
            gripper_on = CONDITION_FLAGS.get(condition, (0, 0, 0))[2] == 1
            haptic_changed = any(differs(
                number(final.get(key)), number(baseline.get(key))
            ) for key in ("K_fb", "deadband"))
            gripper_changed = any(differs(
                number(final.get(key)), number(baseline.get(key))
            ) for key in ("gripper_speed", "gripper_force"))
            if haptic_on != haptic_changed:
                errors.append(
                    f"H manipulation mismatch: enabled={haptic_on}, "
                    f"changed={haptic_changed}"
                )
            if gripper_on != gripper_changed:
                errors.append(
                    f"G manipulation mismatch: enabled={gripper_on}, "
                    f"changed={gripper_changed}"
                )

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
    compute_times = [number(row.get("control_compute_time_s")) for row in rows]
    compute_times = [value for value in compute_times if math.isfinite(value)]
    target_dts = [number(row.get("control_target_dt_s")) for row in rows]
    target_dts = [value for value in target_dts if math.isfinite(value) and value > 0]
    target_dt = target_dts[-1] if target_dts else math.nan
    deadline_misses = sum(int(number(row.get("control_deadline_miss"), 0)) for row in rows)
    saturations = sum(int(number(row.get("haptic_saturated"), 0)) for row in rows)
    deadline_miss_rate = deadline_misses / len(rows)
    saturation_rate = saturations / len(rows)
    dt_p95 = percentile(dts, 0.95)
    compute_p95 = percentile(compute_times, 0.95)

    if not math.isfinite(target_dt):
        errors.append("missing finite positive control target period")
    else:
        recomputed_misses = sum(value > target_dt for value in compute_times)
        if recomputed_misses != deadline_misses:
            errors.append(
                f"deadline flag mismatch: logged={deadline_misses}, "
                f"recomputed={recomputed_misses}"
            )
        if deadline_miss_rate > FAIL_DEADLINE_MISS_RATE:
            errors.append(
                f"control compute deadline miss rate {deadline_miss_rate:.1%} "
                f"exceeds {FAIL_DEADLINE_MISS_RATE:.0%}"
            )
        elif deadline_miss_rate > WARNING_DEADLINE_MISS_RATE:
            warnings.append(
                f"control compute deadline miss rate is {deadline_miss_rate:.1%}"
            )
        if math.isfinite(dt_p95) and dt_p95 > 4 * target_dt:
            errors.append(
                f"control period p95 {1000*dt_p95:.2f} ms exceeds "
                f"4x target period"
            )
        elif math.isfinite(dt_p95) and dt_p95 > 2 * target_dt:
            warnings.append(
                f"control period p95 is {1000*dt_p95:.2f} ms "
                f"(>{2*1000*target_dt:.2f} ms)"
            )

    if saturation_rate > FAIL_HAPTIC_SATURATION_RATE:
        errors.append(
            f"haptic saturation rate {saturation_rate:.1%} exceeds "
            f"{FAIL_HAPTIC_SATURATION_RATE:.0%}"
        )
    elif saturation_rate > WARNING_HAPTIC_SATURATION_RATE:
        warnings.append(f"haptic saturation rate is {saturation_rate:.1%}")

    report = {
        "status": "pass" if not errors else "fail",
        "file": str(path.resolve()),
        "condition": condition,
        "run_uuid": run_uuid,
        "samples": len(rows),
        "errors": errors,
        "warnings": warnings,
        "metrics": {
            "duration_s": times[-1] - times[0] if len(times) > 1 else 0,
            "control_dt_mean_ms": 1000 * sum(dts) / len(dts) if dts else None,
            "control_dt_p95_ms": 1000 * dt_p95 if math.isfinite(dt_p95) else None,
            "control_dt_max_ms": 1000 * max(dts) if dts else None,
            "control_compute_mean_ms": (
                1000 * sum(compute_times) / len(compute_times)
                if compute_times else None
            ),
            "control_compute_p95_ms": (
                1000 * compute_p95 if math.isfinite(compute_p95) else None
            ),
            "control_target_dt_ms": 1000 * target_dt if math.isfinite(target_dt) else None,
            "deadline_miss_count": deadline_misses,
            "deadline_miss_rate": deadline_miss_rate,
            "haptic_saturation_count": saturations,
            "haptic_saturation_rate": saturation_rate,
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
    output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    label = report["status"].upper()
    if report["status"] == "pass" and report["warnings"]:
        label = "PASS WITH WARNINGS"
    print(f"{label}: {output}")
    for warning in report["warnings"]:
        print(f"WARNING: {warning}")
    if report["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
