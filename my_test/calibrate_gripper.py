#!/usr/bin/env python3
"""
calibrate_gripper.py — Omega.7 夹爪角度标定（一次运行，永久生效）

在 3 秒内张/合一次夹爪，自动记录角度行程。
标定结果写入 plans/.gripper_calib.py，shared_control_node.py
启动时会自动加载此文件，不再需要每次手动标定。

用法:
    python3 my_test/calibrate_gripper.py

注意:
    Omega.7 必须已通过 USB 连接到电脑。
    执行时手柄上不要有其他程序占用设备。
"""

import time
import ctypes
import sys
from pathlib import Path
import forcedimension_core.dhd as dhd


def main():
    calib_path = Path(__file__).resolve().parent.parent / "plans" / ".gripper_calib.py"

    print("=" * 60)
    print("  Omega.7 夹爪角度标定工具")
    print("=" * 60)

    # ── 连接 ──
    print("\n[1] 连接 Omega.7 ...")
    if dhd.open() < 0:
        print("   ❌ 连接失败，检查 USB")
        sys.exit(1)
    print(f"   ✓ {dhd.getSystemName()}")

    # ── 采样 ──
    print("\n[2] 请在 3 秒内将夹爪完全张开 → 完全捏合 → 再完全张开")
    print("    ⏱  倒计时开始...")

    samples = []
    t0 = time.time()
    while time.time() - t0 < 3.0:
        a = ctypes.c_double()
        dhd.getGripperAngleDeg(a)
        samples.append(a.value)
        time.sleep(0.01)

    dhd.close()

    open_angle = max(samples)
    close_angle = min(samples)
    range_deg = open_angle - close_angle

    print(f"\n   📐 张开={open_angle:.1f}°  捏合={close_angle:.1f}°  "
          f"行程={range_deg:.1f}°")

    if range_deg < 5:
        print("   ⚠️  行程<5°，标定失败！")
        print("   请确保在 3 秒内充分张合夹爪，然后重试")
        sys.exit(1)

    # ── 写入标定文件 ──
    content = (
        f"# Omega.7 夹爪角度标定 (自动生成)\n"
        f"# 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"# 行程: {range_deg:.1f}°\n"
        f'GRIPPER_ANGLE_OPEN = {open_angle:.1f}   # 完全张开\n'
        f'GRIPPER_ANGLE_CLOSE = {close_angle:.1f}  # 完全捏合\n'
    )
    calib_path.write_text(content)
    print(f"\n   ✅ 标定已写入: {calib_path}")
    print(f"      shared_control_node.py 启动时将自动加载\n")


if __name__ == "__main__":
    main()
