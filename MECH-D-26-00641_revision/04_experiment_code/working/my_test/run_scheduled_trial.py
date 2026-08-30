"""Launch one trial from the locked CSV schedule without retyping metadata."""

from __future__ import annotations

import argparse
import csv
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
    output_dir = args.data_root / row["subject_id"] / row["session_id"]
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
