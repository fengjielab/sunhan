#!/usr/bin/env python3
"""Generate the frozen 24-participant K_fb formal-study schedule."""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter
from pathlib import Path

from generate_kfb_timing_schedule import _choose_measured_blocks, _masked_code
from kfb_timing_protocol import (
    CONDITIONS,
    DEFAULT_CONFIG,
    config_hash,
    sha256_text_file,
    software_hash,
    write_config,
)


SEED = 20260812
PARTICIPANTS = tuple(f"F{number:02d}" for number in range(1, 25))
BLOCKS_PER_PARTICIPANT = 3


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_schedule(seed: int = SEED) -> tuple[list[dict], list[dict]]:
    rng = random.Random(seed)
    used_masks: set[str] = set()
    run_rows: list[dict] = []
    oracle_rows: list[dict] = []
    global_position_counts: Counter = Counter()
    global_transition_counts: Counter = Counter()
    cfg_hash = config_hash(DEFAULT_CONFIG)

    source_dir = Path(__file__).resolve().parent
    acquisition_hash = software_hash([
        source_dir / "interactive_teleop.py",
        source_dir / "kfb_timing_protocol.py",
        source_dir / "experiment_protocol.py",
    ])

    for participant in PARTICIPANTS:
        blocks = _choose_measured_blocks(
            rng,
            None,
            global_position_counts,
            global_transition_counts,
        )
        for block, order in enumerate(blocks, start=1):
            for position, condition_code in enumerate(order, start=1):
                trial_id = f"{participant}_M{block:02d}_{position:02d}"
                mask = _masked_code(rng, used_masks)
                trial_number = (block - 1) * 5 + position
                spec = CONDITIONS[condition_code]
                run_rows.append({
                    "participant_id": participant,
                    "phase": "measured",
                    "analyzed": 1,
                    "trial_number": trial_number,
                    "block": block,
                    "position": position,
                    "trial_id": trial_id,
                    "masked_condition": mask,
                    "break_after": int(position == 5 and block < BLOCKS_PER_PARTICIPANT),
                    "command": f"bash run_kfb_formal_trial.sh {trial_id} {participant}",
                })
                oracle_rows.append({
                    "trial_id": trial_id,
                    "participant_id": participant,
                    "phase": "measured",
                    "analyzed": 1,
                    "masked_condition": mask,
                    "true_condition": condition_code,
                    "scheduled_onset_s": f"{spec.onset_s:.3f}",
                    "scheduled_offset_s": f"{spec.offset_s:.3f}",
                    "expected_epsilon_s": f"{spec.expected_epsilon_s:.3f}",
                    "expected_phi": f"{spec.expected_phi:.3f}",
                    "config_sha256": cfg_hash,
                    "acquisition_software_sha256": acquisition_hash,
                })

    expected = len(PARTICIPANTS) * BLOCKS_PER_PARTICIPANT * len(CONDITIONS)
    if len(run_rows) != expected or len(oracle_rows) != expected:
        raise AssertionError(f"formal schedule must contain {expected} trials")
    return run_rows, oracle_rows


def _command_sheet(rows: list[dict]) -> str:
    lines = [
        "# K_fb正式实验每次运行命令（formal_v1）",
        "",
        "设计：24名参与者；仅正式试验；每人3个区组；每区组五条件各一次；每人15次。",
        "",
        "开始前进入目录：",
        "",
        "```bash",
        "cd ~/sunhan/my_test",
        "```",
        "",
        "每条命令只运行一次。完成后，将同一Trial ID的4个文件一起移动到",
        "`data/kfb_timing_formal_v1/participants/FXX/block_0N/`，不要改文件名。",
        "",
    ]
    for participant in PARTICIPANTS:
        lines.extend([
            f"## {participant}",
            "",
            "| 顺序 | 区组 | 序位 | Trial ID | 匿名码 | 完成 | 最短命令 |",
            "|---:|---:|---:|---|---|:---:|---|",
        ])
        participant_rows = [row for row in rows if row["participant_id"] == participant]
        for row in participant_rows:
            lines.append(
                f"| {row['trial_number']} | {row['block']} | {row['position']} | "
                f"`{row['trial_id']}` | `{row['masked_condition']}` | ☐ | "
                f"`{row['command']}` |"
            )
        lines.append("")
    lines.extend([
        "## 现场规则",
        "",
        "- 每完成5次休息2–3分钟。",
        "- `HOLD`后停止主动推进，保持轻触；不要故意回拉、横向摆动或追踪力值。",
        "- 每次必须生成CSV、events、summary和manifest四个文件。",
        "- 失败记录不得覆盖或删除；补测须使用另行登记的新Trial ID。",
        "- 不得根据力值、轨迹长度或结果方向决定补测。",
        "",
    ])
    return "\n".join(lines)


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

    run_rows, oracle_rows = build_schedule(args.seed)
    run_path = output_dir / "participant_run_sheet.csv"
    oracle_path = private_dir / "oracle.csv"
    config_path = output_dir / "protocol_config_v1.json"
    commands_path = output_dir / "formal_run_commands.md"
    _write_csv(run_path, run_rows, list(run_rows[0]))
    _write_csv(oracle_path, oracle_rows, list(oracle_rows[0]))
    write_config(config_path, DEFAULT_CONFIG)
    commands_path.write_text(_command_sheet(run_rows), encoding="utf-8")

    source_dir = Path(__file__).resolve().parent
    acquisition_hash = software_hash([
        source_dir / "interactive_teleop.py",
        source_dir / "kfb_timing_protocol.py",
        source_dir / "experiment_protocol.py",
    ])
    metadata = {
        "schedule_design": "formal_v1_24_participants_3_blocks_no_training",
        "seed": args.seed,
        "participants": list(PARTICIPANTS),
        "participant_count": len(PARTICIPANTS),
        "blocks_per_participant": BLOCKS_PER_PARTICIPANT,
        "formal_trials_per_participant": BLOCKS_PER_PARTICIPANT * len(CONDITIONS),
        "formal_trials_total": len(run_rows),
        "config_sha256": config_hash(DEFAULT_CONFIG),
        "acquisition_software_sha256": acquisition_hash,
        "text_hash_canonicalization": "UTF-8, optional BOM removed, CRLF/CR normalized to LF",
        "file_text_sha256": {
            "participant_run_sheet.csv": sha256_text_file(run_path),
            "private_oracle/oracle.csv": sha256_text_file(oracle_path),
            "protocol_config_v1.json": sha256_text_file(config_path),
            "formal_run_commands.md": sha256_text_file(commands_path),
        },
    }
    (output_dir / "schedule_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
