"""Launch one trial from the locked CSV schedule without retyping metadata."""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from pathlib import Path


def load_row(schedule: Path, subject_id: str, trial_order: int):
    with schedule.open(newline="", encoding="utf-8-sig") as stream:
        matches = [row for row in csv.DictReader(stream)
                   if row["subject_id"] == subject_id
                   and int(row["trial_order"]) == trial_order]
    if len(matches) != 1:
        raise SystemExit(
            f"Expected one schedule row for {subject_id} trial {trial_order}, found {len(matches)}"
        )
    return matches[0]


def group_directory_parts(row):
    """Return object-group and repetition folders for one four-condition block."""
    object_id = str(row["object_id"])
    if not re.fullmatch(r"[A-Za-z0-9_-]+", object_id):
        raise SystemExit(f"Unsafe object_id in schedule: {object_id!r}")
    try:
        object_order = int(row["object_order"])
        repetition = int(row["repetition"])
    except (KeyError, TypeError, ValueError) as error:
        raise SystemExit(f"Invalid grouping fields in schedule row: {error}") from error
    if object_order < 1 or repetition < 1:
        raise SystemExit("object_order and repetition must be positive")
    return f"G{object_order:02d}_{object_id}", f"R{repetition}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--schedule", type=Path, required=True)
    parser.add_argument("--subject-id", required=True)
    parser.add_argument("--trial-order", type=int, required=True)
    parser.add_argument("--run-kind", choices=["pilot", "formal"], required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--yolo-model", type=Path, required=True)
    parser.add_argument("--haptic-force-limit", type=float, default=3.0)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    row = load_row(args.schedule, args.subject_id, args.trial_order)
    group_dir, repetition_dir = group_directory_parts(row)
    output_dir = (
        args.data_root / row["subject_id"] / row["session_id"]
        / group_dir / repetition_dir
    )
    command = [
        sys.executable, str(Path(__file__).with_name("interactive_teleop.py")),
        "--mode", row["condition"], "--run-kind", args.run_kind,
        "--trajectory-dir", str(output_dir),
        "--subject-id", row["subject_id"], "--object-id", row["object_id"],
        "--trial-id", row["trial_id"], "--session-id", row["session_id"],
        "--schedule-id", row["schedule_id"], "--trial-order", row["trial_order"],
        "--repetition", row["repetition"],
        "--haptic-force-limit", str(args.haptic_force_limit),
        "--yolo-model", str(args.yolo_model.resolve()),
    ]
    print("Scheduled row:", row)
    print("Group directory:", output_dir)
    print("Command:", subprocess.list2cmdline(command))
    if not args.execute:
        print("Dry run only; add --execute after checking the object and workspace.")
        return
    output_dir.mkdir(parents=True, exist_ok=True)
    before = set(output_dir.glob("*.csv"))
    subprocess.run(command, check=True)
    new_csv = sorted(set(output_dir.glob("*.csv")) - before)
    if len(new_csv) != 1:
        raise SystemExit(
            f"Expected one new raw CSV after the trial, found {len(new_csv)}: {new_csv}"
        )
    validator = Path(__file__).resolve().parents[3] / "07_analysis" / "validate_trial.py"
    subprocess.run([sys.executable, str(validator), str(new_csv[0])], check=True)
    print(f"Trial and validation complete: {new_csv[0]}")


if __name__ == "__main__":
    main()
