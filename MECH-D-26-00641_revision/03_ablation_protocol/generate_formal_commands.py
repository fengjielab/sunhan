"""Generate an auditable text file containing all 384 short formal commands."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
SCHEDULE = HERE / "randomization_schedule.csv"
OUTPUT = HERE / "正式实验384次命令.txt"
CONDITIONS = {"I", "I_H", "I_G", "I_H_G"}


def load_rows():
    with SCHEDULE.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def validate(rows):
    assert len(rows) == 384
    assert {row["subject_id"] for row in rows} == {f"P{i:02d}" for i in range(1, 9)}
    for subject_number in range(1, 9):
        subject = f"P{subject_number:02d}"
        selected = [row for row in rows if row["subject_id"] == subject]
        assert len(selected) == 48
        assert [int(row["trial_order"]) for row in selected] == list(range(1, 49))
        assert Counter(row["condition"] for row in selected) == Counter({key: 12 for key in CONDITIONS})
        assert Counter(row["session_id"] for row in selected) == Counter({
            f"{subject}_S1": 24,
            f"{subject}_S2": 24,
        })
        groups = Counter(
            (row["object_order"], row["object_id"], row["repetition"])
            for row in selected
        )
        assert len(groups) == 12
        assert set(groups.values()) == {4}


def main():
    rows = load_rows()
    validate(rows)
    lines = [
        "MECH-D-26-00641 正式实验384次逐条命令",
        "",
        "运行目录：",
        "/home/mfj/sunhan/MECH-D-26-00641_revision/04_experiment_code/working/my_test",
        "",
        "先执行：",
        "cd /home/mfj/sunhan/MECH-D-26-00641_revision/04_experiment_code/working/my_test",
        "",
        "每条命令都会先显示计划行和保存目录；只有FORMAL_LOCK.md为LOCKED且输入RUN后才连接硬件。",
        "正常任务失败不得重做；只有有记录的硬件/软件中断才允许技术重跑。",
        "",
        "目录规则：06_formal_data/受试者/会话/G##_物体/R重复次数/",
        "示例：06_formal_data/P01/P01_S1/G01_apple/R1/",
        "",
    ]
    previous_subject = previous_session = previous_group = None
    command_count = 0
    for row in rows:
        subject = row["subject_id"]
        session = row["session_id"]
        group = f'G{int(row["object_order"]):02d}_{row["object_id"]}/R{row["repetition"]}'
        if subject != previous_subject:
            lines.extend(["=" * 72, f"受试者 {subject}（共48次）", "=" * 72, ""])
            previous_subject = subject
            previous_session = previous_group = None
        if session != previous_session:
            lines.extend([f"--- 会话 {session}（24次）---", ""])
            previous_session = session
            previous_group = None
        if group != previous_group:
            lines.extend([
                f'物体组：{group}（物体={row["object_id"]}，重复={row["repetition"]}，四个条件）',
                "保存到："
                f'06_formal_data/{subject}/{session}/G{int(row["object_order"]):02d}_{row["object_id"]}/R{row["repetition"]}/',
                "",
            ])
            previous_group = group
        command = (
            f'python3 formal.py --subject-id {subject} '
            f'--trial-order {int(row["trial_order"])}'
        )
        lines.extend([
            f'{row["trial_id"]}：object={row["object_id"]}，condition={row["condition"]}',
            command,
            "",
        ])
        command_count += 1
    assert command_count == 384
    content = "\n".join(lines).rstrip() + "\n"
    assert content.count("python3 formal.py --subject-id ") == 384
    OUTPUT.write_text(content, encoding="utf-8")
    written = OUTPUT.read_text(encoding="utf-8")
    assert written.count("python3 formal.py --subject-id ") == 384
    print(f"Wrote and validated {command_count} formal commands to {OUTPUT}")


if __name__ == "__main__":
    main()
