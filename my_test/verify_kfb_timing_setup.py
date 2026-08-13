#!/usr/bin/env python3
"""Verify frozen K_fb schedule, hashes, balance, and optional start pose."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path

from kfb_timing_protocol import CONDITIONS, DEFAULT_CONFIG, config_hash, sha256_file, software_hash


def read_csv(path: Path) -> list[dict]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schedule-dir", type=Path, required=True)
    parser.add_argument("--start-pose-file", type=Path)
    args = parser.parse_args()

    schedule_dir = args.schedule_dir.resolve()
    metadata_path = schedule_dir / "schedule_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    checks = {}
    for relative, expected_hash in metadata["file_sha256"].items():
        path = schedule_dir / relative
        checks[f"hash:{relative}"] = path.is_file() and sha256_file(path) == expected_hash

    config_path = schedule_dir / "protocol_config_v1.json"
    stored_config = json.loads(config_path.read_text(encoding="utf-8"))
    checks["config_hash"] = (
        metadata["config_sha256"]
        == stored_config["config_sha256"]
        == config_hash(DEFAULT_CONFIG)
    )

    source_dir = Path(__file__).resolve().parent
    current_software_hash = software_hash([
        source_dir / "interactive_teleop.py",
        source_dir / "kfb_timing_protocol.py",
        source_dir / "experiment_protocol.py",
    ])
    checks["acquisition_software_hash"] = (
        metadata["acquisition_software_sha256"] == current_software_hash
    )

    engineering = read_csv(schedule_dir / "engineering_run_sheet.csv")
    participant = read_csv(schedule_dir / "participant_run_sheet.csv")
    oracle = read_csv(schedule_dir / "private_oracle" / "oracle.csv")
    oracle_by_id = {row["trial_id"]: row for row in oracle}
    checks["counts"] = len(engineering) == 25 and len(participant) == 80 and len(oracle) == 105
    checks["unique_trial_ids"] = len({row["trial_id"] for row in oracle}) == 105
    checks["unique_masks"] = len({row["masked_condition"] for row in oracle}) == 105
    checks["run_sheets_blinded"] = all(
        "true_condition" not in row for row in engineering + participant
    )
    all_run_rows = engineering + participant
    block_conditions = {}
    for row in all_run_rows:
        key = (row["participant_id"], row["phase"], row["block"])
        block_conditions.setdefault(key, []).append(
            oracle_by_id[row["trial_id"]]["true_condition"]
        )
    checks["one_each_condition_per_block"] = all(
        len(codes) == 5 and set(codes) == set(CONDITIONS)
        for codes in block_conditions.values()
    )

    no_adjacent_repeat = True
    for participant_id in ("ENGINEER", "P01", "P02", "P03", "P04"):
        rows = [row for row in all_run_rows if row["participant_id"] == participant_id]
        phase_order = {"engineering": 0, "training": 0, "measured": 1}
        rows.sort(key=lambda row: (
            phase_order[row["phase"]], int(row["block"]), int(row["position"])
        ))
        codes = [oracle_by_id[row["trial_id"]]["true_condition"] for row in rows]
        no_adjacent_repeat &= all(left != right for left, right in zip(codes, codes[1:]))
    checks["no_adjacent_repeat"] = no_adjacent_repeat

    measured_position_counts = Counter()
    for participant_id in ("P01", "P02", "P03", "P04"):
        measured = [
            row for row in oracle
            if row["participant_id"] == participant_id and row["phase"] == "measured"
        ]
        counts = Counter(row["true_condition"] for row in measured)
        checks[f"balance:{participant_id}"] = (
            len(measured) == 15 and all(counts[code] == 3 for code in CONDITIONS)
        )
        participant_run_by_id = {
            row["trial_id"]: row for row in participant
            if row["participant_id"] == participant_id and row["phase"] == "measured"
        }
        local_positions = Counter()
        for row in measured:
            position = int(participant_run_by_id[row["trial_id"]]["position"])
            local_positions[(row["true_condition"], position)] += 1
            measured_position_counts[(row["true_condition"], position)] += 1
        checks[f"distinct_positions:{participant_id}"] = all(
            value <= 1 for value in local_positions.values()
        )
    checks["study_position_balance"] = all(
        measured_position_counts[(code, position)] in (2, 3)
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
        "current_config_sha256": config_hash(DEFAULT_CONFIG),
        "current_acquisition_software_sha256": current_software_hash,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["overall_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
