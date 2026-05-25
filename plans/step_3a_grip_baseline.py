#!/usr/bin/env python3
"""
Step 3a — 夹持力空载基线采集
==============================
目的: 确定 tau_max 和 torque_threshold 的合理值。
      在夹爪完全张开、空载状态下记录腕部关节（J5,J6,J7）的外部力矩噪声。

操作:
    1. 连接 Franka
    2. 夹爪张开到最大（open 状态）
    3. 采集 5 秒 tau_ext_hat_filtered 数据
    4. 输出统计和建议参数值

用法:
    python3 plans/step_3a_grip_baseline.py

预期输出:
    |τ_wrist| 统计: mean=0.23 Nm, std=0.08 Nm, max=0.45 Nm
    建议: torque_threshold >= 1.0 Nm, tau_max >= 3.0 Nm

作者: mfj
日期: 2026-05
"""

import sys
import time
import numpy as np
import panda_py
import panda_py.libfranka

ROBOT_IP = "192.168.1.51"
DURATION = 5.0
FREQ = 100

WRIST_JOINT_INDICES = [4, 5, 6]  # J5, J6, J7 (0-indexed)


def main():
    print("=" * 60)
    print("  Step 3a: 夹持力空载基线采集")
    print("=" * 60)
    print(f"\n  机器人 IP: {ROBOT_IP}")
    print(f"  采集时长: {DURATION} 秒 @ {FREQ} Hz")
    print(f"  腕部关节: J5, J6, J7 (0-indexed: {WRIST_JOINT_INDICES})")

    # ── 连接 ──
    print("\n[1/3] 连接 Franka Panda ...")
    panda = panda_py.Panda(ROBOT_IP)
    panda.recover()
    panda.set_default_behavior()
    print("   ✓ 已连接")

    # ── 张开夹爪 ──
    print("[2/3] 张开夹爪到最大（空载状态）...")
    gripper = panda_py.libfranka.Gripper(ROBOT_IP)
    gripper.homing()  # 标定
    gripper.move(0.08, 0.1)  # 张开到最大
    time.sleep(2.0)
    print(f"   ✓ 夹爪已张开 (move to 0.08m)")

    # ── 采集数据 ──
    print(f"[3/3] 采集 {DURATION} 秒腕部关节力矩数据...")
    print("   ⚠️  确保机械臂末端空载，夹爪不接触任何物体")

    tau_j5, tau_j6, tau_j7 = [], [], []
    tau_wrist_norm = []

    start = time.time()
    last_print = 0
    while time.time() - start < DURATION:
        state = panda.get_state()
        tau_ext = np.array(state.tau_ext_hat_filtered, dtype=float)

        tau_j5.append(tau_ext[4])
        tau_j6.append(tau_ext[5])
        tau_j7.append(tau_ext[6])

        wrist_norm = np.linalg.norm(tau_ext[WRIST_JOINT_INDICES])
        tau_wrist_norm.append(wrist_norm)

        elapsed = time.time() - start
        if int(elapsed) > last_print:
            last_print = int(elapsed)
            print(f"   采集 {int(elapsed)}/{DURATION}s ... "
                  f"τ_wrist=|{tau_ext[4]:+.2f}, {tau_ext[5]:+.2f}, {tau_ext[6]:+.2f}| "
                  f"norm={wrist_norm:.3f} Nm")

        time.sleep(1.0 / FREQ)

    # ── 统计分析 ──
    a_j5 = np.array(tau_j5)
    a_j6 = np.array(tau_j6)
    a_j7 = np.array(tau_j7)
    a_norm = np.array(tau_wrist_norm)

    print("\n" + "=" * 60)
    print("  统计结果")
    print("=" * 60)
    print(f"\n  采样: {len(tau_j5)} 帧")

    print(f"\n  {'轴':>6} {'mean(Nm)':>10} {'std(Nm)':>10} {'max(Nm)':>10} {'min(Nm)':>10}")
    print("  " + "-" * 50)
    for name, arr in [("J5", a_j5), ("J6", a_j6), ("J7", a_j7)]:
        print(f"  {name:>6} {np.mean(arr):>+10.3f} {np.std(arr):>10.3f} "
              f"{np.max(arr):>+10.3f} {np.min(arr):>+10.3f}")

    print(f"\n  ||τ_wrist|| norm:")
    print(f"    mean = {np.mean(a_norm):.3f} Nm")
    print(f"    std  = {np.std(a_norm):.3f} Nm")
    print(f"    max  = {np.max(a_norm):.3f} Nm")

    # ── 参数建议 ──
    mean_norm = np.mean(a_norm)
    std_norm = np.std(a_norm)
    max_norm = np.max(a_norm)

    suggested_torque_threshold = max(1.0, mean_norm + 5 * std_norm)
    suggested_tau_max = max(3.0, max_norm * 5)

    print("\n" + "=" * 60)
    print("  参数建议")
    print("=" * 60)

    # 四舍五入到一位小数
    torque_th = round(suggested_torque_threshold * 2) / 2  # round to 0.5
    tau_mx = round(suggested_tau_max)

    print(f"  torque_threshold = {torque_th:.1f} Nm  "
          f"(建议 >= 噪声均值+5σ = {mean_norm+5*std_norm:.1f})")
    print(f"  tau_max          = {tau_mx:.0f} Nm  "
          f"(建议 >= 空载最大值的 5 倍 = {max_norm*5:.1f})")

    print("\n  配置位置:")
    print(f"    grip_force_estimator.py: __init__() 中 tau_max, torque_threshold")
    print(f"    当前默认: tau_max=10.0, torque_threshold=1.5")
    print(f"    根据基线数据决定是否需要修改默认值")

    # ── 结论 ──
    print("\n" + "=" * 60)
    print("  结论")
    print("=" * 60)
    if std_norm < 0.15:
        print(f"  ✅ PASS: 腕部力矩噪声 std={std_norm:.3f} Nm < 0.15 Nm → 基线干净")
    elif std_norm < 0.3:
        print(f"  ⚠️  边缘: 腕部力矩噪声 std={std_norm:.3f} Nm < 0.3 Nm → 可接受")
    else:
        print(f"  ❌ FAIL: 腕部力矩噪声 std={std_norm:.3f} Nm > 0.3 Nm → 噪声偏大")
        print(f"  建议检查机械臂是否震动，或夹爪是否完全张开")

    print(f"\n  记录基线参数:")
    print(f"    torque_threshold = {torque_th:.1f}")
    print(f"    tau_max          = {tau_mx:.0f}")
    print(f"  请在 grip_force_estimator.py 中更新这两个参数。\n")


if __name__ == "__main__":
    main()
