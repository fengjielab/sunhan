#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成先验可信度补充实验的预试、正式顺序与记录模板。"""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "paper2_sci" / "07_supplement_experiment"

OBJECTS = {
    "banana": {
        "correct_K": 50.0,
        "overstiff_K": 200.0,
        "safe_anchor_K": 50.0,
        "gripper_force": 8.0,
    },
    "mouse": {
        "correct_K": 200.0,
        "overstiff_K": 250.0,
        "safe_anchor_K": 160.0,
        "gripper_force": 20.0,
    },
}
CONDITIONS = {
    "C0": {"prior": "correct", "posterior": "off"},
    "C1": {"prior": "correct", "posterior": "on"},
    "W0": {"prior": "overstiff", "posterior": "off"},
    "W1": {"prior": "overstiff", "posterior": "on"},
}
TREATMENTS = [
    (obj, cond)
    for obj in ("banana", "mouse")
    for cond in ("C0", "C1", "W0", "W1")
]


def williams_rows(n: int) -> list[list[int]]:
    if n % 2:
        raise ValueError("This generator expects an even number of treatments")
    first = [0]
    for i in range(1, n):
        first.append((i + 1) // 2 if i % 2 else n - i // 2)
    return [[(value + row) % n for value in first] for row in range(n)]


def trial_row(participant: str, order: int, obj: str, cond: str,
              participant_group: str) -> dict:
    condition = CONDITIONS[cond]
    prior_K = (
        OBJECTS[obj]["correct_K"]
        if condition["prior"] == "correct"
        else OBJECTS[obj]["overstiff_K"]
    )
    trial_id = f"{participant}_{order:02d}_{obj}_{cond}"
    output_dir = f"data/trust_correction/{participant}"
    command = (
        f"python3 my_test/interactive_teleop.py --mode {cond} "
        f"--actual-object {obj} --subject-id {participant} "
        f"--object-id {obj} --trial-id {trial_id} "
        f"--trajectory-dir {output_dir}"
    )
    return {
        "run_order": order,
        "participant_id": participant,
        "participant_group": participant_group,
        "actual_object": obj,
        "condition_code": cond,
        "prior_condition": condition["prior"],
        "posterior_correction": condition["posterior"],
        "prior_K_N_per_m": prior_K,
        "safe_anchor_K_N_per_m": OBJECTS[obj]["safe_anchor_K"],
        "gripper_force_N": OBJECTS[obj]["gripper_force"],
        "trial_id": trial_id,
        "output_dir": output_dir,
        "launch_command": command,
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    # 预试从低风险正确先验开始；每个错误先验先运行有修正的 W1，再运行 W0。
    pilot_order = [
        ("banana", "C0"), ("banana", "C1"),
        ("mouse", "C0"), ("mouse", "C1"),
        ("banana", "W1"), ("banana", "W0"),
        ("mouse", "W1"), ("mouse", "W0"),
    ]
    pilot = [
        trial_row("PILOT_V2", idx, obj, cond, "non_formal_experimenter_v2")
        for idx, (obj, cond) in enumerate(pilot_order, start=1)
    ]
    write_csv(OUT / "pilot_schedule_8.csv", pilot)

    # 鼠标机制诊断：单一非正式实验人员，4条件×3个平衡重复块。
    # 该数据只用于判断C1过度修正是否可重复，不进入正式统计。
    diagnostic: list[dict] = []
    diagnostic_conditions = ["C0", "C1", "W0", "W1"]
    order = 0
    for block, sequence in enumerate(williams_rows(4)[:3], start=1):
        for within_block_order, condition_index in enumerate(sequence, start=1):
            order += 1
            row = trial_row(
                "MOUSE_DIAG",
                order,
                "mouse",
                diagnostic_conditions[condition_index],
                "non_formal_mouse_diagnostic",
            )
            row["diagnostic_block"] = block
            row["within_block_order"] = within_block_order
            diagnostic.append(row)
    write_csv(OUT / "mouse_diagnostic_schedule_12.csv", diagnostic)

    rows = williams_rows(len(TREATMENTS))
    formal: list[dict] = []
    for number in range(1, 11):
        participant = f"P{number:02d}"
        participant_group = "previous_cohort" if number <= 5 else "new_cohort"
        sequence = rows[number - 1] if number <= 8 else list(
            reversed(rows[number - 9])
        )
        for order, treatment_index in enumerate(sequence, start=1):
            obj, cond = TREATMENTS[treatment_index]
            formal.append(
                trial_row(participant, order, obj, cond, participant_group)
            )
    write_csv(OUT / "formal_schedule_80.csv", formal)

    outcome_fields = [
        "trial_id", "participant_id", "actual_object", "condition_code",
        "scheduled_order", "attempt_number", "started_at", "data_file_stem",
        "task_completed", "grasp_success", "drop_occurred", "visible_damage",
        "collision_occurred", "robot_emergency_stop", "software_safety_stop",
        "raw_vision_class", "raw_vision_correct", "failure_stage",
        "failure_reason", "operator_action", "retest_trial_id",
        "primary_first_attempt", "include_end_to_end_success", "notes",
    ]
    outcome_rows = []
    for row in formal:
        values = {field: "" for field in outcome_fields}
        values.update({
            "trial_id": row["trial_id"],
            "participant_id": row["participant_id"],
            "actual_object": row["actual_object"],
            "condition_code": row["condition_code"],
            "scheduled_order": row["run_order"],
            "attempt_number": 1,
            "primary_first_attempt": 1,
            "include_end_to_end_success": 1,
        })
        outcome_rows.append(values)
    write_csv(OUT / "trial_outcomes_80_template.csv", outcome_rows)

    background_fields = [
        "participant_id", "cohort", "age_years", "sex", "dominant_hand",
        "normal_or_corrected_vision", "robotics_experience_years",
        "teleoperation_experience_level", "weekly_video_game_hours",
        "prior_training_minutes", "completed_old_180_experiment",
        "consent_confirmed", "notes",
    ]
    background = []
    for number in range(1, 11):
        values = {field: "" for field in background_fields}
        values.update({
            "participant_id": f"P{number:02d}",
            "cohort": "previous_cohort" if number <= 5 else "new_cohort",
            "completed_old_180_experiment": 1 if number <= 5 else 0,
        })
        background.append(values)
    write_csv(OUT / "participant_background_10_template.csv", background)

    print(f"Generated schedules and templates in: {OUT}")


if __name__ == "__main__":
    main()
