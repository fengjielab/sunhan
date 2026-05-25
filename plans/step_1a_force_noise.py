#!/usr/bin/env python3
"""
Step 1a — 空载外力噪声测试
============================
目的: 测量 Franka Panda 在空载静止状态下 O_F_ext_hat_K 的噪声水平
     以确定 filter_alpha 和 ForceEstimator 的初始参数。

操作:
    1. 连接 Franka 机械臂
    2. 保持末端空载（不接触任何物体）
    3. 采集 5 秒外力数据
    4. 输出统计: mean, std, max|err|

用法:
    python3 plans/step_1a_force_noise.py

预期结果:
    Fx: std < 0.5 N, Fy: std < 0.5 N, Fz: std < 0.5 N

作者: mfj
日期: 2026-05
"""

import sys
import time
import numpy as np
import panda_py

ROBOT_IP = "192.168.1.51"
DURATION = 5.0  # 采集时长 (秒)
FREQ = 100      # 采样频率 (Hz)

def main():
    print("=" * 60)
    print("  Step 1a: 空载外力噪声测试")
    print("=" * 60)
    print(f"\n  机器人 IP: {ROBOT_IP}")
    print(f"  采集时长: {DURATION} 秒 @ {FREQ} Hz")

    # ── 连接 ──
    print("\n[1/3] 连接 Franka Panda ...")
    panda = panda_py.Panda(ROBOT_IP)
    panda.recover()
    panda.set_default_behavior()
    print("   ✓ 已连接")

    # ── 读取初始位姿 + 启动阻抗控制（保持不动） ──
    print("[2/3] 启动笛卡尔阻抗控制器（保持位置）...")
    init_pos = panda.get_position().copy()
    init_ori = panda.get_orientation().copy()
    impedance = np.diag([200.0, 200.0, 200.0, 10.0, 10.0, 10.0])
    from panda_py import controllers
    ctrl = controllers.CartesianImpedance(
        impedance=impedance, damping_ratio=1.0,
        nullspace_stiffness=0.5, filter_coeff=1.0,
    )
    panda.start_controller(ctrl)
    ctrl.set_control(init_pos, init_ori)
    time.sleep(1.0)  # 等待稳定
    print("   ✓ 控制器已启动，等待稳定...")

    # ── 采集数据 ──
    print(f"[3/3] 采集 {DURATION} 秒外力数据...")
    print("   ⚠️  请确保机械臂末端空载，无人触碰")

    Fx, Fy, Fz = [], [], []
    Tx, Ty, Tz = [], [], []
    start = time.time()
    last_print = 0
    while time.time() - start < DURATION:
        state = panda.get_state()
        F = np.array(state.O_F_ext_hat_K, dtype=float)
        Fx.append(F[0]); Fy.append(F[1]); Fz.append(F[2])
        Tx.append(F[3]); Ty.append(F[4]); Tz.append(F[5])
        time.sleep(1.0 / FREQ)

        elapsed = time.time() - start
        if int(elapsed) > last_print:
            last_print = int(elapsed)
            print(f"   采集 {int(elapsed)}/{DURATION}s ... F=({F[0]:+.2f}, {F[1]:+.2f}, {F[2]:+.2f}) N")

    # ── 统计分析 ──
    print("\n" + "=" * 60)
    print("  统计结果")
    print("=" * 60)

    data = {
        "Fx": np.array(Fx), "Fy": np.array(Fy), "Fz": np.array(Fz),
        "Tx": np.array(Tx), "Ty": np.array(Ty), "Tz": np.array(Tz),
    }

    print(f"\n  采样: {len(Fx)} 帧")
    print(f"\n  {'轴':>6} {'mean(N)':>10} {'std(N)':>10} {'max|err|(N)':>13} {'p-p(N)':>10}")
    print("  " + "-" * 55)
    for axis, arr in [("Fx", Fx), ("Fy", Fy), ("Fz", Fz)]:
        a = np.array(arr)
        mean = np.mean(a)
        std = np.std(a)
        max_err = np.max(np.abs(a - mean))
        pp = np.ptp(a)
        print(f"  {axis:>6} {mean:>+10.3f} {std:>10.3f} {max_err:>13.3f} {pp:>10.3f}")

    print(f"\n  {'轴':>6} {'mean(Nm)':>10} {'std(Nm)':>10} {'max|err|(Nm)':>13} {'p-p(Nm)':>10}")
    print("  " + "-" * 55)
    for axis, arr in [("Tx", Tx), ("Ty", Ty), ("Tz", Tz)]:
        a = np.array(arr)
        mean = np.mean(a)
        std = np.std(a)
        max_err = np.max(np.abs(a - mean))
        pp = np.ptp(a)
        print(f"  {axis:>6} {mean:>+10.3f} {std:>10.3f} {max_err:>13.3f} {pp:>10.3f}")

    # ── 判断 ──
    F_std = np.array([np.std(Fx), np.std(Fy), np.std(Fz)])
    max_std = np.max(F_std)

    print("\n" + "=" * 60)
    print("  结论")
    print("=" * 60)

    if max_std < 0.3:
        print(f"  ✅ PASS: 最大 std = {max_std:.3f} N < 0.3 N → 噪声水平优秀")
        print("  建议: filter_alpha = 0.3 (默认值)，无需调整")
    elif max_std < 0.5:
        print(f"  ⚠️  边缘: 最大 std = {max_std:.3f} N < 0.5 N → 可接受")
        print("  建议: filter_alpha = 0.2 (稍大滤波)")
    else:
        print(f"  ❌ FAIL: 最大 std = {max_std:.3f} N > 0.5 N → 噪声偏大")
        print("  建议:")
        print("    1. 检查机器人是否处于震动状态")
        print("    2. 在 force_estimator.py 中设 filter_alpha = 0.1")
        print("    3. 尝试 use_builtin=False 手动显式模式")

    panda.stop_controller()
    print("\n控制器已停止。\n")


if __name__ == "__main__":
    main()
