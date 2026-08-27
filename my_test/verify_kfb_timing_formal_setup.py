#!/usr/bin/env python3
"""Verify the frozen 24-participant K_fb formal-study schedule."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path

from kfb_timing_protocol import (
    CONDITIONS,
    DEFAULT_CONFIG,
    config_hash,
    sha256_text_file,
    software_hash,
)


def _read_csv(path: Path) -> list[dict]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schedule-dir", type=Path, required=True)
    parser.add_argument("--start-pose-file", type=Path)
    args = parser.parse_args()

    schedule_dir = args.schedule_dir.resolve()
    metadata = json.loads((schedule_dir / "schedule_metadata.json").read_text(encoding="utf-8"))
    checks: dict[str, bool] = {}
    checks["formal_design"] = metadata.get("schedule_design") == (
        "formal_v1_24_participants_3_blocks_no_training"
    )
    for relative, expected in metadata["file_text_sha256"].items():
        path = schedule_dir / relative
        checks[f"hash:{relative}"] = path.is_file() and sha256_text_file(path) == expected

    current_config_hash = config_hash(DEFAULT_CONFIG)
    source_dir = Path(__file__).resolve().parent
    current_software_hash = software_hash([
        source_dir / "interactive_teleop.py",
        source_dir / "kfb_timing_protocol.py",
        source_dir / "experiment_protocol.py",
    ])
    checks["config_hash"] = metadata["config_sha256"] == current_config_hash
    checks["acquisition_software_hash"] = (
        metadata["acquisition_software_sha256"] == current_software_hash
    )

    run_rows = _read_csv(schedule_dir / "participant_run_sheet.csv")
    oracle = _read_csv(schedule_dir / "private_oracle" / "oracle.csv")
    oracle_by_id = {row["trial_id"]: row for row in oracle}
    participants = metadata["participants"]
    checks["24_participants"] = len(participants) == 24 and len(set(participants)) == 24
    checks["360_formal_trials"] = len(run_rows) == len(oracle) == 360
    checks["formal_only"] = all(
        row["phase"] == "measured" and row["analyzed"] == "1" for row in run_rows + oracle
    )
    checks["unique_trial_ids"] = len({row["trial_id"] for row in oracle}) == 360
    checks["unique_masks"] = len({row["masked_condition"] for row in oracle}) == 360
    checks["run_sheet_blinded"] = all("true_condition" not in row for row in run_rows)

    all_no_adjacent = True
    all_balanced = True
    all_distinct_positions = True
    global_positions: Counter = Counter()
    for participant in participants:
        rows = [row for row in run_rows if row["participant_id"] == participant]
        rows.sort(key=lambda row: (int(row["block"]), int(row["position"])))
        codes = [oracle_by_id[row["trial_id"]]["true_condition"] for row in rows]
        all_no_adjacent &= all(left != right for left, right in zip(codes, codes[1:]))
        counts = Counter(codes)
        all_balanced &= len(rows) == 15 and all(counts[code] == 3 for code in CONDITIONS)
        local_positions: Counter = Counter()
        for row, code in zip(rows, codes):
            position = int(row["position"])
            local_positions[(code, position)] += 1
            global_positions[(code, position)] += 1
        all_distinct_positions &= all(value <= 1 for value in local_positions.values())
        for block in range(1, 4):
            block_codes = [
                oracle_by_id[row["trial_id"]]["true_condition"]
                for row in rows if int(row["block"]) == block
            ]
            all_balanced &= len(block_codes) == 5 and set(block_codes) == set(CONDITIONS)
    checks["each_condition_three_times_per_participant"] = all_balanced
    checks["no_adjacent_repeat"] = all_no_adjacent
    checks["three_distinct_positions_per_condition"] = all_distinct_positions
    checks["study_position_balance"] = all(
        global_positions[(code, position)] in (14, 15)
        for code in CONDITIONS for position in range(1, 6)
    )

    if args.start_pose_file:
        pose = json.loads(args.start_pose_file.read_text(encoding="utf-8"))
        dimensions = pose.get("pad_dimensions_mm", [])
        checks["start_pose_fixed_target"] = bool(pose.get("fixed_target_checked"))
        checks["start_pose_distance"] = math.isclose(
            float(pose.get("pad_distance_m", math.nan)), 0.030, abs_tol=0.002
        )
        checks["pad_dimensions"] = (
            len(dimensions) == 3
            and float(dimensions[0]) >= 60
            and float(dimensions[1]) >= 60
            and float(dimensions[2]) >= 10
        )

    report = {
        "schedule_dir": str(schedule_dir),
        "checks": checks,
        "overall_pass": all(checks.values()),
        "current_config_sha256": current_config_hash,
        "current_acquisition_software_sha256": current_software_hash,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["overall_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
