#!/usr/bin/env python3
"""
Step 4b — 力反馈手感确认（虚拟墙 + 遥操作）
==============================================
目的: 在实际遥操作场景中验证力反馈通道的完整链路：
      Franka 末端外力 → ForceEstimator → ForceFeedbackScheduler → Omega.7 力输出

操作:
    1. 连接 Omega.7 + Franka
    2. 启动遥操作，操作员控制机械臂移动
    3. 设置一个"虚拟墙"（在某个空间区域施加虚拟弹簧力）
    4. 操作员将机械臂移动到虚拟墙区域，感受 Omega.7 的阻力
    5. 对比有无力反馈的体验差异

用法:
    python3 plans/step_4b_force_feedback.py

预期:
    机械臂末端接近虚拟墙时，Omega.7 产生阻力
    F_ext 越大 → Omega.7 力越大（经 K_trans 缩放 + 死区滤波）

注意:
    需要 Omega.7 USB 连接和 Franka 网络连接
    初始阶段是"透明模式"，操作员确认手柄轻便后开始测试

作者: mfj
日期: 2026-05
"""

import sys
import time
import ctypes
import numpy as np
import forcedimension_core.dhd as dhd
import forcedimension_core.drd as drd
import panda_py
from panda_py import controllers

# ── 配置 ──
ROBOT_IP = "192.168.1.51"
SCALE_POS = 3.0
SIGN = np.array([-1.0, -1.0, 1.0])

# 虚拟墙参数
VIRTUAL_WALL_Z = 0.0        # 虚拟墙 Z 位置 (m)，相对于初始位置
VIRTUAL_WALL_K = 200.0      # 虚拟墙刚度 (N/m) — 进入墙区域后的弹簧刚度

# 力反馈参数（模拟 force_feedback_scheduler.py）
K_TRANS = 0.6
DEADBAND = 0.3


def main():
    print("=" * 60)
    print("  Step 4b: 力反馈手感确认")
    print("=" * 60)
    print(f"\n  机器人 IP: {ROBOT_IP}")
    print(f"  虚拟墙 Z 位置: {VIRTUAL_WALL_Z:.2f}m (相对于初始)")
    print(f"  虚拟墙刚度 K  : {VIRTUAL_WALL_K:.0f} N/m")
    print(f"  力反馈 K_trans : {K_TRANS}")
    print(f"  死区            : ±{DEADBAND} N")

    # ════════════════════════════════════
    # 1. 连接 Omega.7
    # ════════════════════════════════════
    print("\n[1/5] 连接 Omega.7 ...")
    if dhd.open() < 0:
        print("   ❌ Omega.7 连接失败")
        sys.exit(1)
    sysname = dhd.getSystemName()
    if isinstance(sysname, bytes):
        sysname = sysname.decode('utf-8', errors='replace')
    print(f"   ✓ {sysname}")

    if drd.start() < 0:
        print("   ⚠️  DRD 启动失败，力反馈不可用")
    else:
        print("   ✓ DRD 已启动")

    dhd.enableForce(True)
    print("   ✓ 力输出已使能（开始为零力透明模式）\n")

    # ════════════════════════════════════
    # 2. 连接 Franka
    # ════════════════════════════════════
    print("[2/5] 连接 Franka Panda ...")
    panda = panda_py.Panda(ROBOT_IP)
    panda.recover()
    panda.set_default_behavior()
    # Step 4b 不需要夹爪，跳过（panda.get_gripper() 不存在）
    print("   ✓ 已连接\n")

    # ════════════════════════════════════
    # 3. 初始化
    # ════════════════════════════════════
    print("[3/5] 初始化 ...")
    init_pos = panda.get_position().copy()
    init_ori = panda.get_orientation().copy()

    # Omega.7 零点标定
    print("   标定 Omega.7 零点（松开手柄）...")
    time.sleep(1.0)
    omega_home = np.zeros(3)
    pos_arr = (ctypes.c_double * 3)(0.0, 0.0, 0.0)
    for _ in range(100):
        dhd.getPosition(pos_arr)
        omega_home[0] += pos_arr[0]
        omega_home[1] += pos_arr[1]
        omega_home[2] += pos_arr[2]
    omega_home /= 100.0
    print(f"   Omega 零点: {np.round(omega_home, 4)}")

    # 虚拟墙的绝对 Z 位置
    wall_z_abs = init_pos[2] + VIRTUAL_WALL_Z
    print(f"   虚拟墙绝对位置 Z={wall_z_abs:.3f}m\n")

    # ════════════════════════════════════
    # 4. 启动阻抗控制
    # ════════════════════════════════════
    print("[4/5] 启动笛卡尔阻抗控制器 ...")
    impedance = np.diag([200.0, 200.0, 200.0, 10.0, 10.0, 10.0])
    ctrl = controllers.CartesianImpedance(
        impedance=impedance, damping_ratio=1.0,
        nullspace_stiffness=0.5, filter_coeff=1.0,
    )
    panda.start_controller(ctrl)
    ctrl.set_control(init_pos, init_ori)
    time.sleep(0.5)
    print("   ✓ 控制器已启动\n")

    # ════════════════════════════════════
    # 5. 主循环：遥操作 + 力反馈
    # ════════════════════════════════════
    print("[5/5] 开始遥操作 + 力反馈测试")
    print("=" * 60)
    print("  🎮 操作说明:")
    print("  1. 移动手柄，机械臂会跟随")
    print("  2. 将机械臂向 Z 负方向移动（向下）")
    print("  3. 当机械臂低于虚拟墙位置时，Omega.7 会产生阻力")
    print("  4. 试着手动感受力反馈的 '虚拟墙' 效果")
    print("  5. 按 Ctrl+C 停止\n")

    virtual_ref = init_pos.copy()
    loop_count = 0
    F_filtered = np.zeros(3)
    FILTER_ALPHA = 0.3

    try:
        while True:
            # ── 读 Omega.7 位置 ──
            dhd.getPosition(pos_arr)
            omega_pos = np.array([pos_arr[0], pos_arr[1], pos_arr[2]])

            # ── 计算目标位置 ──
            delta = (omega_pos - omega_home) * SIGN * SCALE_POS
            target_pos = virtual_ref + delta

            # ── 发送给 Franka ──
            ctrl.set_control(target_pos, init_ori)

            # ── 读 Franka 外力 ──
            state = panda.get_state()
            F_raw = np.array(state.O_F_ext_hat_K[:3], dtype=float)
            F_filtered = FILTER_ALPHA * F_raw + (1 - FILTER_ALPHA) * F_filtered

            # ── 虚拟墙力计算 ──
            # 如果机械臂末端低于虚拟墙位置，产生弹簧力阻止继续下移
            current_z = state.O_T_EE[14]  # 末端 Z 位置
            F_wall = np.zeros(3)
            if current_z < wall_z_abs:
                penetration = wall_z_abs - current_z
                F_wall[2] = VIRTUAL_WALL_K * penetration  # 正 Z 方向推回

            # ── 合并外力 + 虚拟墙力 → Omega.7 力反馈 ──
            F_total = F_filtered + F_wall
            F_scaled = F_total * K_TRANS

            # 死区滤波
            F_haptic = np.where(
                np.abs(F_scaled) > DEADBAND,
                np.sign(F_scaled) * (np.abs(F_scaled) - DEADBAND),
                0.0,
            )
            # 限幅 Omega.7 最大输出 ~10N
            F_haptic = np.clip(F_haptic, -10.0, 10.0)

            # 设置力
            dhd_force = (ctypes.c_double * 3)(
                F_haptic[0], F_haptic[1], F_haptic[2]
            )
            dhd.setForce(dhd_force)

            # ── 打印状态 ──
            loop_count += 1
            if loop_count % 40 == 0:  # 约 5Hz 打印
                wall_active = "🧱 触墙!" if current_z < wall_z_abs else "自由   "
                print(f"  Z={current_z:.3f}m {wall_active} | "
                      f"F_wall={F_wall[2]:+.1f}N | "
                      f"F_ext=[{F_filtered[0]:+.1f}, {F_filtered[1]:+.1f}, {F_filtered[2]:+.1f}] | "
                      f"F_omg=[{F_haptic[0]:+.1f}, {F_haptic[1]:+.1f}, {F_haptic[2]:+.1f}]")

            time.sleep(0.005)  # 200Hz

    except KeyboardInterrupt:
        print("\n\n  Ctrl+C 已捕捉，正在停止...")

    # ── 清理 ──
    zero_force = (ctypes.c_double * 3)(0.0, 0.0, 0.0)
    dhd.setForce(zero_force)
    panda.stop_controller()

    print("\n" + "=" * 60)
    print("  测试总结")
    print("=" * 60)
    print("  验证清单:")
    print("  [ ] 遥操作: 手柄移动 → 机械臂流畅跟随")
    print("  [ ] 自由区: 手柄轻便（只有 F_ext 滤波后的残余力）")
    print("  [ ] 虚拟墙: 机械臂低于墙位置时，手柄有明显阻力")
    print("  [ ] 力方向: 向下推 → 手柄向上推回（方向正确）")
    print("  [ ] 力大小: F_haptic 随着穿透深度增大而增大")
    print("  [ ] 退出恢复: 停止后 Omega.7 力归零，不残留")

    dhd.close()
    print("\nOmega.7 已断开。\n")


if __name__ == "__main__":
    main()
