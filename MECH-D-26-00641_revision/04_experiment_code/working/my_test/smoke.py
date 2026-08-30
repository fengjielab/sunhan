#!/usr/bin/env python3
"""One-command repaired-code hardware smoke test, isolated from pilot data."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from pilot import MODEL, REVISION_ROOT, SCHEDULE


DATA_ROOT = REVISION_ROOT / "05_pilot_data" / "SMOKE_V1"


def main():
    if not MODEL.is_file():
        raise SystemExit(f"找不到YOLO模型，请修改 pilot.py 中的 MODEL：{MODEL}")

    launcher = Path(__file__).with_name("run_scheduled_trial.py")
    command = [
        sys.executable, str(launcher),
        "--schedule", str(SCHEDULE),
        "--subject-id", "PILOT02",
        "--trial-order", "4",  # cup + I_H_G checks both H and G
        "--run-kind", "pilot",
        "--data-root", str(DATA_ROOT),
        "--yolo-model", str(MODEL),
    ]
    subprocess.run(command, check=True)
    if input("确认屏幕显示 cup 和 I_H_G，输入 RUN 开始冒烟试验: ").strip() != "RUN":
        print("已取消，没有连接硬件。")
        return
    subprocess.run(command + ["--execute"], check=True)


if __name__ == "__main__":
    main()
