#!/usr/bin/env python3
"""Generate frozen engineering and four-participant K_fb pilot schedules."""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import random
from collections import Counter
from pathlib import Path
from typing import Dict, List, Sequence

from kfb_timing_protocol import (
    CONDITIONS,
    DEFAULT_CONFIG,
    config_hash,
    sha256_file,
    software_hash,
    write_config,
)


SEED = 20260812
PARTICIPANTS = ("P01", "P02", "P03", "P04")
CONDITION_CODES = tuple(sorted(CONDITIONS))


def _choose_balanced_blocks(n_blocks: int, rng: random.Random) -> List[Sequence[str]]:
    """Greedily choose permutations with positional and transition balance."""
    permutations = list(itertools.permutations(CONDITION_CODES))
    position_counts = Counter()
    transition_counts = Counter()
    chosen: List[Sequence[str]] = []
    previous_last = None
    for _ in range(n_blocks):
        scored = []
        rng.shuffle(permutations)
        for permutation in permutations:
            if previous_last == permutation[0]:
                continue
            position_penalty = sum(position_counts[(code, pos)] for pos, code in enumerate(permutation))
            transition_penalty = sum(
                transition_counts[(permutation[pos], permutation[pos + 1])]
                for pos in range(len(permutation) - 1)
            )
            start_penalty = sum(1 for row in chosen if row[0] == permutation[0])
            scored.append((position_penalty * 3 + transition_penalty * 2 + start_penalty, permutation))
        if not scored:
            raise RuntimeError("could not generate a constrained condition order")
        best_score = min(item[0] for item in scored)
        best = [item[1] for item in scored if item[0] == best_score]
        selected = rng.choice(best)
        chosen.append(selected)
        previous_last = selected[-1]
        for pos, code in enumerate(selected):
            position_counts[(code, pos)] += 1
        for left, right in zip(selected, selected[1:]):
            transition_counts[(left, right)] += 1
    return chosen


def _choose_measured_blocks(
    rng: random.Random,
    previous_last: str,
    global_position_counts: Counter,
    global_transition_counts: Counter,
) -> List[Sequence[str]]:
    """Choose three blocks with participant-local and study-wide balance."""
    permutations = list(itertools.permutations(CONDITION_CODES))
    local_position_counts = Counter()
    chosen: List[Sequence[str]] = []
    for _ in range(3):
        rng.shuffle(permutations)
        scored = []
        for permutation in permutations:
            if previous_last == permutation[0]:
                continue
            # Place each participant's three repeats of a condition at three
            # distinct serial positions.
            if any(
                local_position_counts[(code, position)]
                for position, code in enumerate(permutation)
            ):
                continue
            position_penalty = sum(
                global_position_counts[(code, position)]
                for position, code in enumerate(permutation)
            )
            transition_penalty = sum(
                global_transition_counts[(left, right)]
                for left, right in zip(permutation, permutation[1:])
            )
            scored.append((position_penalty * 3 + transition_penalty * 2, permutation))
        if not scored:
            raise RuntimeError("could not generate participant-balanced measured blocks")
        best_score = min(item[0] for item in scored)
        selected = rng.choice([item[1] for item in scored if item[0] == best_score])
        chosen.append(selected)
        previous_last = selected[-1]
        for position, code in enumerate(selected):
            local_position_counts[(code, position)] += 1
            global_position_counts[(code, position)] += 1
        for left, right in zip(selected, selected[1:]):
            global_transition_counts[(left, right)] += 1
    return chosen


def _masked_code(rng: random.Random, used: set) -> str:
    while True:
        value = f"M{rng.randrange(16**7):07X}"
        if value not in used:
            used.add(value)
            return value


def build_schedules(seed: int = SEED) -> tuple[List[dict], List[dict]]:
    rng = random.Random(seed)
    used_masks = set()
    run_rows: List[dict] = []
    oracle_rows: List[dict] = []
    engineering_blocks = _choose_balanced_blocks(5, rng)

    def add_trial(
        participant: str,
        phase: str,
        block: int,
        position: int,
        condition_code: str,
        analyzed: bool,
    ) -> None:
        prefix = "ENG" if phase == "engineering" else participant
        phase_tag = {"engineering": "E", "training": "T", "measured": "M"}[phase]
        trial_id = f"{prefix}_{phase_tag}{block:02d}_{position:02d}"
        mask = _masked_code(rng, used_masks)
        spec = CONDITIONS[condition_code]
        trial_number = 1 + sum(
            row["participant_id"] == participant and row["phase"] == phase
            for row in run_rows
        )
        run_rows.append({
            "participant_id": participant,
            "phase": phase,
            "analyzed": int(analyzed),
            "trial_number": trial_number,
            "block": block,
            "position": position,
            "trial_id": trial_id,
            "masked_condition": mask,
            "break_after": int(phase == "measured" and position == 5 and block < 3),
        })
        oracle_rows.append({
            "trial_id": trial_id,
            "participant_id": participant,
            "phase": phase,
            "analyzed": int(analyzed),
            "masked_condition": mask,
            "true_condition": condition_code,
            "scheduled_onset_s": f"{spec.onset_s:.3f}",
            "scheduled_offset_s": f"{spec.offset_s:.3f}",
            "expected_epsilon_s": f"{spec.expected_epsilon_s:.3f}",
            "expected_phi": f"{spec.expected_phi:.3f}",
        })

    for block in range(1, 6):
        order = engineering_blocks[block - 1]
        for position, condition in enumerate(order, start=1):
            add_trial("ENGINEER", "engineering", block, position, condition, False)

    measured_position_counts = Counter()
    measured_transition_counts = Counter()
    for participant in PARTICIPANTS:
        training_order = _choose_balanced_blocks(1, rng)[0]
        for position, condition in enumerate(training_order, start=1):
            add_trial(participant, "training", 1, position, condition, False)
        measured_blocks = _choose_measured_blocks(
            rng,
            training_order[-1],
            measured_position_counts,
            measured_transition_counts,
        )
        for block, order in enumerate(measured_blocks, start=1):
            for position, condition in enumerate(order, start=1):
                add_trial(participant, "measured", block, position, condition, True)

    if len(run_rows) != 105 or len(oracle_rows) != 105:
        raise AssertionError("schedule must contain 25 engineering and 80 participant trials")
    return run_rows, oracle_rows


def _write_csv(path: Path, rows: List[dict], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        parser.error(f"output directory is not empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    private_dir = output_dir / "private_oracle"
    private_dir.mkdir(parents=True, exist_ok=True)

    run_rows, oracle_rows = build_schedules(args.seed)
    source_dir = Path(__file__).resolve().parent
    acquisition_files = [
        source_dir / "interactive_teleop.py",
        source_dir / "kfb_timing_protocol.py",
        source_dir / "experiment_protocol.py",
    ]
    source_hash = software_hash(acquisition_files)
    cfg_hash = config_hash(DEFAULT_CONFIG)
    for row in run_rows:
        row["command_template"] = (
            "python3 my_test/interactive_teleop.py --mode kfb_timing "
            f"--subject-id {row['participant_id']} --trial-id {row['trial_id']} "
            "--kfb-oracle <PRIVATE_ORACLE_PATH> "
            "--kfb-start-pose-file <START_POSE_PATH> "
            "--trajectory-dir <DATA_DIR>"
        )
    for row in oracle_rows:
        row["config_sha256"] = cfg_hash
        row["acquisition_software_sha256"] = source_hash

    engineering = [row for row in run_rows if row["phase"] == "engineering"]
    participant = [row for row in run_rows if row["phase"] != "engineering"]
    run_fields = list(run_rows[0])
    oracle_fields = list(oracle_rows[0])
    engineering_path = output_dir / "engineering_run_sheet.csv"
    participant_path = output_dir / "participant_run_sheet.csv"
    oracle_path = private_dir / "oracle.csv"
    config_path = output_dir / "protocol_config_v1.json"
    _write_csv(engineering_path, engineering, run_fields)
    _write_csv(participant_path, participant, run_fields)
    _write_csv(oracle_path, oracle_rows, oracle_fields)
    write_config(config_path, DEFAULT_CONFIG)

    metadata = {
        "protocol_version": DEFAULT_CONFIG.protocol_version,
        "seed": args.seed,
        "config_sha256": cfg_hash,
        "acquisition_software_sha256": source_hash,
        "engineering_trials": len(engineering),
        "participant_training_trials": sum(row["phase"] == "training" for row in run_rows),
        "participant_measured_trials": sum(row["phase"] == "measured" for row in run_rows),
        "oracle_path": "private_oracle/oracle.csv",
        "file_sha256": {
            "engineering_run_sheet.csv": sha256_file(engineering_path),
            "participant_run_sheet.csv": sha256_file(participant_path),
            "private_oracle/oracle.csv": sha256_file(oracle_path),
            "protocol_config_v1.json": sha256_file(config_path),
        },
    }
    (output_dir / "schedule_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
