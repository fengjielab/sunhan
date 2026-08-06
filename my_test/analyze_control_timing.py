#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Summarize per-module timing for instrumented teleoperation CSV files."""

from __future__ import annotations

import argparse
import csv
import math
from collections import Counter
from pathlib import Path


COMPONENTS = {
    "omega_io": "prev_omega_io_s",
    "panda_state": "prev_panda_state_s",
    "haptic_send": "prev_haptic_send_s",
    "impedance_update": "prev_impedance_update_s",
    "panda_command": "prev_panda_command_s",
    "gripper_update": "prev_gripper_update_s",
    "record": "prev_record_s",
    "keyboard_status": "prev_keyboard_status_s",
}


def number(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def percentile(values: list[float], probability: float) -> float:
    values = sorted(value for value in values if math.isfinite(value))
    if not values:
        return math.nan
    position = (len(values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return values[lower]
    fraction = position - lower
    return values[lower] * (1 - fraction) + values[upper] * fraction


def classify_long_cycle(row: dict, threshold_s: float) -> str:
    component_values = {
        name: number(row.get(column)) for name, column in COMPONENTS.items()
    }
    component_values = {
        name: value for name, value in component_values.items()
        if math.isfinite(value)
    }
    sleep_actual = number(row.get("prev_sleep_actual_s"))
    work = number(row.get("prev_loop_work_s"))
    if math.isfinite(sleep_actual) and sleep_actual >= threshold_s:
        return "sleep_or_scheduler"
    if component_values:
        name, value = max(component_values.items(), key=lambda item: item[1])
        if value >= threshold_s:
            return name
    if math.isfinite(work) and work >= threshold_s:
        return "unprofiled_work_or_thread_preemption"
    return "between_cycles_or_unattributed"


def analyze(path: Path, long_threshold_s: float) -> dict:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    required = {"control_dt", "prev_loop_work_s", "prev_sleep_actual_s"}
    missing = required - set(rows[0] if rows else {})
    if missing:
        raise ValueError(f"{path.name}: missing timing columns {sorted(missing)}")

    dt = [number(row.get("control_dt")) for row in rows]
    dt = [value for value in dt if math.isfinite(value) and value > 0]
    long_rows = [
        row for row in rows if number(row.get("control_dt")) >= long_threshold_s
    ]
    causes = Counter(classify_long_cycle(row, long_threshold_s) for row in long_rows)
    first = rows[0]
    return {
        "file": path.name,
        "object": first.get("actual_object", ""),
        "condition": first.get("condition_code", ""),
        "samples": len(dt),
        "median_ms": 1000 * percentile(dt, 0.50),
        "p99_ms": 1000 * percentile(dt, 0.99),
        "over_20ms_pct": 100 * sum(value > 0.020 for value in dt) / len(dt),
        "over_50ms_pct": 100 * sum(value > 0.050 for value in dt) / len(dt),
        "long_cycles": len(long_rows),
        "causes": causes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data_dir", type=Path)
    parser.add_argument("--long-threshold-ms", type=float, default=20.0)
    args = parser.parse_args()
    files = sorted(args.data_dir.resolve().glob("trust_experiment_*.csv"))
    if not files:
        raise SystemExit(f"No trust experiment CSV files in {args.data_dir}")
    threshold_s = args.long_threshold_ms / 1000.0
    for path in files:
        result = analyze(path, threshold_s)
        causes = ", ".join(
            f"{name}={count}" for name, count in result["causes"].most_common()
        ) or "none"
        print(
            f"{result['object']:6} {result['condition']:2} "
            f"median={result['median_ms']:.2f}ms "
            f"p99={result['p99_ms']:.2f}ms "
            f">20ms={result['over_20ms_pct']:.2f}% "
            f">50ms={result['over_50ms_pct']:.2f}% | {causes}"
        )


if __name__ == "__main__":
    main()
