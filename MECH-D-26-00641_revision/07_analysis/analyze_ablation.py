"""Build the trial table and fit the prespecified participant-level mixed model."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path


def event_time(events, name):
    for event in events:
        if event.get("event") == name:
            return event.get("system_time")
    return None


def duration(events, start, end):
    a, b = event_time(events, start), event_time(events, end)
    return b - a if a is not None and b is not None and b >= a else None


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def percentile(values, probability):
    values = sorted(value for value in values if value is not None)
    if not values:
        return None
    position = (len(values) - 1) * probability
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return values[lower]
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def raw_metrics(csv_path: Path):
    if not csv_path.is_file():
        return {}
    with csv_path.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    output = {}
    for phase in ("APPROACH", "GRASP", "TRANSPORT", "RELEASE"):
        forces = [number(row.get("F_ext_mag")) for row in rows if row.get("phase") == phase]
        forces = [value for value in forces if value is not None]
        key = phase.lower()
        output[f"{key}_force_peak_N"] = max(forces) if forces else None
        output[f"{key}_force_rms_N"] = (
            math.sqrt(sum(value * value for value in forces) / len(forces)) if forces else None
        )
    dts = [number(row.get("control_dt")) for row in rows]
    queue_ages = [number(row.get("vision_queue_age_ms")) for row in rows
                  if row.get("vision_locked") == "1"]
    output.update({
        "control_dt_median_ms": 1000 * percentile(dts, 0.50) if percentile(dts, 0.50) is not None else None,
        "control_dt_p95_ms": 1000 * percentile(dts, 0.95) if percentile(dts, 0.95) is not None else None,
        "control_dt_p99_ms": 1000 * percentile(dts, 0.99) if percentile(dts, 0.99) is not None else None,
        "control_dt_max_ms": 1000 * max(value for value in dts if value is not None)
        if any(value is not None for value in dts) else None,
        "vision_queue_age_median_ms": percentile(queue_ages, 0.50),
        "vision_queue_age_p95_ms": percentile(queue_ages, 0.95),
        "deadline_miss_rate": sum(int(float(row.get("control_deadline_miss") or 0)) for row in rows) / len(rows),
        "haptic_saturation_rate": sum(int(float(row.get("haptic_saturated") or 0)) for row in rows) / len(rows),
    })
    return output


def read_rows(data_dir: Path, timeout_s: float):
    rows = []
    for path in sorted(data_dir.rglob("*_summary.json")):
        summary = json.loads(path.read_text(encoding="utf-8"))
        experiment = summary.get("experiment", {})
        events = experiment.get("events", [])
        condition = summary.get("mode", {}).get("condition")
        object_id = summary.get("object_id") or experiment.get("object_id")
        detections = [event for event in events if event.get("event") == "vision_detection"]
        false_triggers = [
            event for event in detections
            if str(event.get("detected_class", "")).lower() != str(object_id).lower()
        ]
        success = bool(experiment.get("completed"))
        total = duration(events, "task_start", "task_end")
        penalized = total if success and total is not None else timeout_s
        row = {
            "run_uuid": summary.get("run_uuid"),
            "subject_id": summary.get("subject_id") or experiment.get("subject_id"),
            "session_id": summary.get("session_id"),
            "object_id": object_id,
            "trial_id": summary.get("trial_id") or experiment.get("trial_id"),
            "trial_order": summary.get("trial_order"),
            "repetition": summary.get("repetition"),
            "condition": condition,
            "adaptive_haptics": int(summary.get("mode", {}).get("adaptive_haptics", False)),
            "adaptive_gripper": int(summary.get("mode", {}).get("adaptive_gripper", False)),
            "success": int(success),
            "completion_time_s": total,
            "penalized_time_s": penalized,
            "approach_time_s": duration(events, "task_start", "grasp_start"),
            "grasp_time_s": duration(events, "grasp_start", "grasp_success"),
            "transport_time_s": duration(events, "grasp_success", "release_start"),
            "release_time_s": duration(events, "release_start", "task_end"),
            "force_peak_N": summary.get("external_force", {}).get("F_ext_peak_N"),
            "force_mean_N": summary.get("external_force", {}).get("F_ext_mean_N"),
            "deadline_miss_count": summary.get("timing", {}).get("control_deadline_miss_count"),
            "haptic_saturation_count": summary.get("timing", {}).get("haptic_saturation_count"),
            "vision_queue_age_ms": summary.get("timing", {}).get("vision_queue_age_ms_final"),
            "vision_detection_count": len(detections),
            "vision_false_trigger_count": len(false_triggers),
            "vision_false_trigger_rate": (
                len(false_triggers) / len(detections) if detections else None
            ),
            "vision_no_lock": int(event_time(events, "vision_lock") is None),
            "detection_to_contact_s": duration(events, "vision_detection", "contact_onset"),
            "parameter_start_to_contact_s": duration(
                events, "parameter_transition_start", "contact_onset"
            ),
            "source_summary": str(path.resolve()),
        }
        raw_path = path.with_name(f"{condition}_{summary.get('run_uuid')}.csv")
        row.update(raw_metrics(raw_path))
        rows.append(row)
    return rows


def write_csv(rows, path: Path):
    fields = list(rows[0]) if rows else [
        "run_uuid", "subject_id", "object_id", "condition", "penalized_time_s"
    ]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("data_dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--timeout-s", type=float, default=120.0)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = read_rows(args.data_dir, args.timeout_s)
    write_csv(rows, args.output_dir / "confirmatory_trial_table.csv")
    status = {"n_trials": len(rows), "n_participants": len({r["subject_id"] for r in rows})}
    (args.output_dir / "analysis_status.json").write_text(
        json.dumps(status, indent=2) + "\n", encoding="utf-8"
    )
    if not rows:
        print("No formal summary files found; wrote an empty trial table.")
        return

    import numpy as np
    import pandas as pd
    import statsmodels.formula.api as smf

    frame = pd.DataFrame(rows)
    frame["log_penalized_time"] = np.log(frame["penalized_time_s"].astype(float))
    if frame["subject_id"].nunique() < 4:
        raise SystemExit("At least four participants are required to fit the mixed model")
    model = smf.mixedlm(
        "log_penalized_time ~ adaptive_haptics * adaptive_gripper + "
        "C(object_id) + trial_order + repetition",
        frame,
        groups=frame["subject_id"],
    ).fit(reml=False)
    (args.output_dir / "primary_mixed_model.txt").write_text(
        model.summary().as_text() + "\n", encoding="utf-8"
    )
    participant_means = frame.groupby(
        ["subject_id", "condition"], as_index=False
    ).agg(
        penalized_time_s=("penalized_time_s", "mean"),
        success_rate=("success", "mean"),
    )
    participant_means.to_csv(
        args.output_dir / "participant_condition_means.csv", index=False
    )
    condition_summary = frame.groupby("condition", as_index=False).agg(
        n_trials=("run_uuid", "count"),
        n_participants=("subject_id", "nunique"),
        penalized_time_mean_s=("penalized_time_s", "mean"),
        penalized_time_sd_s=("penalized_time_s", "std"),
        success_rate=("success", "mean"),
    )
    condition_summary.to_csv(args.output_dir / "condition_summary.csv", index=False)
    completed = frame[frame["success"] == 1].copy()
    phase_models = []
    for phase in ("approach_time_s", "grasp_time_s", "transport_time_s", "release_time_s"):
        phase_frame = completed.dropna(subset=[phase])
        if phase_frame["subject_id"].nunique() < 4:
            continue
        phase_frame["log_phase_time"] = np.log(phase_frame[phase].astype(float).clip(lower=1e-6))
        result = smf.mixedlm(
            "log_phase_time ~ adaptive_haptics * adaptive_gripper + "
            "C(object_id) + trial_order + repetition",
            phase_frame,
            groups=phase_frame["subject_id"],
        ).fit(reml=False)
        phase_models.append(f"## {phase}\n\n{result.summary().as_text()}\n")
    (args.output_dir / "phase_mixed_models.txt").write_text(
        "\n".join(phase_models), encoding="utf-8"
    )
    print(f"Analyzed {len(frame)} trials from {frame['subject_id'].nunique()} participants")


if __name__ == "__main__":
    main()
