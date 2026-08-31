#!/usr/bin/env python3
"""Minimal guarded entry point for one scheduled formal trial."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


REVISION_ROOT = Path(__file__).resolve().parents[3]
SCHEDULE = REVISION_ROOT / "03_ablation_protocol" / "randomization_schedule.csv"
LOCK_FILE = REVISION_ROOT / "03_ablation_protocol" / "FORMAL_LOCK.md"
DATA_ROOT = REVISION_ROOT / "06_formal_data"
MODEL = Path("/home/mfj/sunhan/yolo/ultralytics-8.3.163/yolo11n.pt")
SUBJECTS = {f"P{number:02d}" for number in range(1, 9)}


def formal_is_locked() -> bool:
    if not LOCK_FILE.is_file():
        return False
    text = LOCK_FILE.read_text(encoding="utf-8")
    return bool(re.search(r"^Status:\s*\*\*LOCKED\*\*\s*$", text, re.MULTILINE))


def prior_runs(subject_id: str, trial_order: int):
    matches = []
    if not DATA_ROOT.is_dir():
        return matches
    for summary_path in DATA_ROOT.rglob("*_summary.json"):
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if (
            summary.get("run_kind") == "formal"
            and summary.get("subject_id") == subject_id
            and int(summary.get("trial_order") or 0) == trial_order
        ):
            matches.append(summary_path)
    return matches


def main():
    parser = argparse.ArgumentParser(description="Run one locked formal trial")
    parser.add_argument("--subject-id")
    parser.add_argument("--trial-order", type=int)
    parser.add_argument(
        "--technical-repeat-reason",
        help="Only for a documented hardware/software interruption; preserves prior files",
    )
    args = parser.parse_args()

    subject = (args.subject_id or input("正式受试者（P01-P08）: ")).strip().upper()
    if subject not in SUBJECTS:
        raise SystemExit("受试者编号只能是P01-P08")
    trial_order = args.trial_order
    if trial_order is None:
        try:
            trial_order = int(input("第几次（1-48）: ").strip())
        except ValueError:
            raise SystemExit("次数必须是1-48的整数")
    if not 1 <= trial_order <= 48:
        raise SystemExit("次数必须在1-48之间")
    if not MODEL.is_file():
        raise SystemExit(f"找不到锁定YOLO模型，请核对formal.py中的MODEL：{MODEL}")

    existing = prior_runs(subject, trial_order)
    if existing and not args.technical_repeat_reason:
        paths = "\n".join(str(path) for path in existing)
        raise SystemExit(
            "该正式试次已有记录，禁止误重复：\n" + paths
            + "\n只有技术中断才可使用--technical-repeat-reason并填写原因。"
        )
    if args.technical_repeat_reason is not None and not args.technical_repeat_reason.strip():
        raise SystemExit("技术重跑必须填写非空原因")

    launcher = Path(__file__).with_name("run_scheduled_trial.py")
    command = [
        sys.executable, str(launcher),
        "--schedule", str(SCHEDULE),
        "--subject-id", subject,
        "--trial-order", str(trial_order),
        "--run-kind", "formal",
        "--data-root", str(DATA_ROOT),
        "--yolo-model", str(MODEL),
    ]
    subprocess.run(command, check=True)

    if not formal_is_locked():
        raise SystemExit(
            f"仅完成预览：{LOCK_FILE} 当前不是LOCKED，未连接硬件、未写正式数据。"
        )
    if args.technical_repeat_reason:
        print(f"技术重跑原因：{args.technical_repeat_reason.strip()}")
        print("请同时写入人工outcome/audit记录。")
    if input("核对受试者、物体、条件和文件夹后，输入 RUN 启动正式试验: ").strip() != "RUN":
        print("已取消，没有连接硬件。")
        return
    subprocess.run(command + ["--execute"], check=True)


if __name__ == "__main__":
    main()
