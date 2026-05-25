#!/usr/bin/env python3
"""
Step 2a — 刚度切换手感测试
=============================
目的: 验证 AdaptiveAdmittance 在执行 set_impedance()
      切换刚度时机械臂平稳不抖动，且操作员能明显感受到刚度差异。

操作:
    1. 连接 Franka，启动笛卡尔阻抗控制
    2. 循环切换 K=50 → 150 → 300 → 50 ...（每 5 秒一次）
    3. 每次切换后操作员用手推末端感受软硬变化
    4. 按 Ctrl+C 停止

用法:
    python3 plans/step_2a_stiffness_switch.py

预期手感:
    K=50  N/m → 像推海绵，容易推动
    K=150 N/m → 中等硬度
    K=300 N/m → 像推木板，很硬

作者: mfj
日期: 2026-05
"""

import sys
import time
import numpy as np
import panda_py
from panda_py import controllers

ROBOT_IP = "192.168.1.51"
SWITCH_INTERVAL = 5.0  # 每 5 秒切换一次

# 测试刚度序列: (label, K_xyz, K_rot)
STIFFNESS_SEQ = [
    ("soft",   50.0,  10.0),
    ("medium", 150.0, 10.0),
    ("hard",   300.0, 10.0),
]


def build_impedance(K_xyz: float, K_rot: float = 10.0) -> np.ndarray:
    """构建 6x6 阻抗对角矩阵"""
    return np.diag([K_xyz, K_xyz, K_xyz, K_rot, K_rot, K_rot])


def main():
    print("=" * 60)
    print("  Step 2a: 刚度切换手感测试")
    print("=" * 60)
    print(f"\n  机器人 IP: {ROBOT_IP}")
    print(f"  切换间隔: {SWITCH_INTERVAL}s")
    print(f"  刚度序列: {[s[0] for s in STIFFNESS_SEQ]}")

    # ── 连接 ──
    print("\n[1/3] 连接 Franka Panda ...")
    panda = panda_py.Panda(ROBOT_IP)
    panda.recover()
    panda.set_default_behavior()
    print("   ✓ 已连接")

    # ── 启动阻抗控制 ──
    print("[2/3] 启动笛卡尔阻抗控制器 ...")
    init_pos = panda.get_position().copy()
    init_ori = panda.get_orientation().copy()
    init_impedance = build_impedance(200.0)
    ctrl = controllers.CartesianImpedance(
        impedance=init_impedance, damping_ratio=1.0,
        nullspace_stiffness=0.5, filter_coeff=1.0,
    )
    panda.start_controller(ctrl)
    ctrl.set_control(init_pos, init_ori)
    time.sleep(1.0)
    print("   ✓ 控制器已启动")

    # ── 切换循环 ──
    print("\n[3/3] 开始刚度切换循环")
    print("=" * 60)
    print("  ⚠️  每 5 秒自动切换一次刚度")
    print("  ⚠️  每次切换后请用手推末端感受硬度变化")
    print("  ⚠️  按 Ctrl+C 停止\n")

    idx = 0
    start_time = time.time()
    next_switch = start_time + SWITCH_INTERVAL
    current_label = ""

    try:
        while True:
            now = time.time()
            elapsed = now - start_time

            # 检查是否该切换
            if now >= next_switch:
                label, K_xyz, K_rot = STIFFNESS_SEQ[idx % len(STIFFNESS_SEQ)]
                idx += 1

                # 构建新阻抗矩阵
                K_new = build_impedance(K_xyz, K_rot)

                # 执行切换（panda_py.set_impedance() 只接受阻抗矩阵，
                # 阻尼比在 CartesianImpedance 构造时指定为 1.0）
                ctrl.set_impedance(K_new)
                ctrl.set_control(init_pos, init_ori)

                current_label = label
                K_diag = np.diag(K_new)
                print(f"\n  >>> 切换 → {label.upper():>8} | "
                      f"K=[{K_diag[0]:.0f}, {K_diag[1]:.0f}, {K_diag[2]:.0f}] N/m | "
                      f"ζ=1.0 (临界阻尼)")

                next_switch = now + SWITCH_INTERVAL

            # 实时显示状态
            state = panda.get_state()
            pos = state.O_T_EE[12:15]  # 末端位置
            F = np.array(state.O_F_ext_hat_K, dtype=float)
            F_mag = np.linalg.norm(F[:3])

            pos_deviation = np.linalg.norm(pos - init_pos) * 1000  # mm
            print(f"  [{elapsed:5.1f}s] {current_label:>8} | "
                  f"pos偏差={pos_deviation:5.1f}mm | |F|={F_mag:5.2f}N", end="\r")

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n\n  Ctrl+C 已捕捉，正在停止...")

    # ── 总结 ──
    print("\n" + "=" * 60)
    print("  测试总结")
    print("=" * 60)
    print("  验证清单:")
    print("  [ ] 切换时机械臂不抖动、不震动")
    print("  [ ] K=50 N/m: 像推海绵，很容易推动")
    print("  [ ] K=150 N/m: 像推中等硬度的橡皮")
    print("  [ ] K=300 N/m: 像推木板，很硬")
    print("  [ ] 松开后位置偏差恢复 < 2mm")

    panda.stop_controller()
    print("\n控制器已停止。\n")


if __name__ == "__main__":
    main()
