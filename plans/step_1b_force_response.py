#!/usr/bin/env python3
"""
Step 1b — 外力响应测试
========================
目的: 验证 O_F_ext_hat_K 在施加外部推力时能否正确响应。
      用手推机械臂末端，观察力估计值的变化。

操作:
    1. 连接 Franka，启动笛卡尔阻抗控制（保持位置）
    2. 稳定后提示操作员推末端
    3. 实时打印 F_ext 数值
    4. 按 Enter 停止

用法:
    python3 plans/step_1b_force_response.py

预期:
    推末端时对应轴力明显变化，松开后归零。
    推力方向正确：推+Z → Fz 正值，推-Z → Fz 负值

作者: mfj
日期: 2026-05
"""

import sys
import time
import numpy as np
import panda_py
from panda_py import controllers

ROBOT_IP = "192.168.1.51"
FILTER_ALPHA = 0.3  # 与 force_estimator.py 默认一致

def main():
    print("=" * 60)
    print("  Step 1b: 外力响应测试")
    print("=" * 60)
    print(f"\n  机器人 IP: {ROBOT_IP}")

    # ── 连接 ──
    print("\n[1/3] 连接 Franka Panda ...")
    panda = panda_py.Panda(ROBOT_IP)
    panda.recover()
    panda.set_default_behavior()
    print("   ✓ 已连接")

    # ── 启动阻抗控制 ──
    print("[2/3] 启动笛卡尔阻抗控制器（保持位置不动）...")
    init_pos = panda.get_position().copy()
    init_ori = panda.get_orientation().copy()
    impedance = np.diag([200.0, 200.0, 200.0, 10.0, 10.0, 10.0])
    ctrl = controllers.CartesianImpedance(
        impedance=impedance, damping_ratio=1.0,
        nullspace_stiffness=0.5, filter_coeff=1.0,
    )
    panda.start_controller(ctrl)
    ctrl.set_control(init_pos, init_ori)
    time.sleep(1.0)
    print("   ✓ 控制器已启动")

    # ── 低通滤波 ──
    F_filtered = np.zeros(6)

    # ── 主循环 ──
    print("\n[3/3] 开始采集外力数据")
    print("=" * 60)
    print("  ⚠️  请用手轻轻推机械臂末端（沿 X/Y/Z 方向分别测试）")
    print("  ⚠️  力度约 3~5N，注意安全，不要猛推！")
    print("  ⚠️  按 Enter 停止测试\n")

    start = time.time()
    try:
        while True:
            state = panda.get_state()
            F_raw = np.array(state.O_F_ext_hat_K, dtype=float)

            # 低通滤波
            F_filtered = FILTER_ALPHA * F_raw + (1 - FILTER_ALPHA) * F_filtered

            # 检测是否有明显外力（≥0.5N）
            F_mag = np.linalg.norm(F_filtered[:3])
            contact_str = ""
            if F_mag > 0.5:
                contact_str = " ← ← ← 接触!"
            elif F_mag > 2.0:
                contact_str = " ← ← ← 大力!"

            # 打印
            elapsed = time.time() - start
            print(f"  [{elapsed:5.1f}s] "
                  f"Fx={F_filtered[0]:+6.2f} "
                  f"Fy={F_filtered[1]:+6.2f} "
                  f"Fz={F_filtered[2]:+6.2f} "
                  f"|F|={F_mag:5.2f} N{contact_str}")

            time.sleep(0.05)  # 20Hz 更新

    except KeyboardInterrupt:
        pass  # Enter 触发 EOF

    print("\n\n" + "=" * 60)
    print("  测试总结")
    print("=" * 60)
    print("  验证清单:")
    print("  [ ] 推末端时对应轴力值明显变化（> 推力的 50%）")
    print("  [ ] 松开后 1s 内回到 |F| < 0.5 N")
    print("  [ ] 方向正确（推+Z → Fz>0，推-Z → Fz<0）")
    print("  [ ] 三个轴各自独立响应（推 X 时 Y/Z 变化 < X 的 20%）")

    panda.stop_controller()
    print("\n控制器已停止。\n")


if __name__ == "__main__":
    main()
