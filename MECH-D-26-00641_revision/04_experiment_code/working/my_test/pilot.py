#!/usr/bin/env python3
"""最简预实验入口：运行后按提示输入即可。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REVISION_ROOT = Path(__file__).resolve().parents[3]
SCHEDULE = REVISION_ROOT / "03_ablation_protocol" / "pilot_schedule.csv"
DATA_ROOT = REVISION_ROOT / "05_pilot_data"
MODEL = Path("/home/mfj/sunhan/yolo/ultralytics-8.3.163/yolo11n.pt")


def main():
    subject = input("预实验者（PILOT01 或 PILOT02）: ").strip().upper()
    if subject not in {"PILOT01", "PILOT02"}:
        raise SystemExit("编号只能是 PILOT01 或 PILOT02")

    maximum = 12 if subject == "PILOT01" else 24
    try:
        trial_order = int(input(f"第几次（1-{maximum}）: ").strip())
    except ValueError:
        raise SystemExit(f"次数必须是1-{maximum}的整数")
    if not 1 <= trial_order <= maximum:
        raise SystemExit(f"次数必须在1-{maximum}之间")
    if not MODEL.is_file():
        raise SystemExit(f"找不到YOLO模型，请修改 pilot.py 中的 MODEL：{MODEL}")

    launcher = Path(__file__).with_name("run_scheduled_trial.py")
    preview = [
        sys.executable, str(launcher),
        "--schedule", str(SCHEDULE),
        "--subject-id", subject,
        "--trial-order", str(trial_order),
        "--run-kind", "pilot",
        "--data-root", str(DATA_ROOT),
        "--yolo-model", str(MODEL),
    ]
    subprocess.run(preview, check=True)

    if input("核对物体和条件后，输入 RUN 启动: ").strip() != "RUN":
        print("已取消，没有连接硬件。")
        return
    subprocess.run(preview + ["--execute"], check=True)


if __name__ == "__main__":
    main()
