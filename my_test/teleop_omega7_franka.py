#!/usr/bin/env python3
"""
Omega.7 → Franka 机械臂遥操作
=================================
- 手柄移动 → 机械臂末端跟随
- 手柄夹钳捏合 → 机械臂夹爪抓取/松开
- 手柄灰色按钮(GRASP) → 夹爪抓取模式切换
- Ctrl+C 安全停止

使用方法：
  python3 teleop_omega7_franka.py
"""

import sys
import time
import ctypes
import numpy as np
import forcedimension_core.dhd as dhd
import forcedimension_core.drd as drd
import panda_py
from panda_py import controllers

# ============================================================
# 配置参数
# ============================================================
SCALE_POS = 3.0        # 位置映射倍数：Omega 手柄位移 → Franka 末端位移（改大后遥操作更灵敏）
SIGN = np.array([-1.0, -1.0, 1.0])  # 坐标轴方向修正

POS_CONTROL_FREQ = 200.0       # 位置控制频率 (Hz) — 只管机械臂末端，不阻塞
GRIPPER_UPDATE_FREQ = 10.0     # 夹爪控制频率 (Hz) — 单独降频，10Hz 足够

GRIPPER_SPEED = 0.1    # 夹爪速度 (m/s)
GRIPPER_FORCE = 20.0   # 夹爪夹持力 (N)
GRIPPER_MAX = 0.08     # 夹爪最大开度 (m)

GRIPPER_INTERVAL = 0.05  # 夹爪命令最小间隔 (s) — 避免高频下发阻塞主循环

# Omega.7 夹爪角度 → Franka 夹爪开度
# 实测 Omega.7 夹爪角度为负值：
#   完全张开约 -60°，完全捏合约 0°（越接近 0 = 捏得越紧）
GRIPPER_ANGLE_OPEN  = -60.0  # Omega.7 夹爪完全张开时的角度（度）
GRIPPER_ANGLE_CLOSE =   0.0  # Omega.7 夹爪完全捏合时的角度（度）

# Franka 夹爪 grasp() 必须提供的容错参数
GRIPPER_EPS_INNER = 0.005
GRIPPER_EPS_OUTER = 0.005


def main():
    # -----------------------------------------------------------
    # 1. 连接 Omega.7
    # -----------------------------------------------------------
    print("[1] 连接 Omega.7 ...")
    if dhd.open() < 0:
        print("   ❌ Omega.7 连接失败，检查 USB 线")
        sys.exit(1)
    print(f"   ✓ 已连接: {dhd.getSystemName()}")

    # 启动 DRD 高频伺服（使 Omega 能输出力/夹持力）
    if drd.start() < 0:
        print("   ⚠️  DRD 启动失败（不影响位置控制，仅力反馈不可用）")
    else:
        print("   ✓ DRD 高频伺服已启动")

    # 开启力输出（零力模式，阻尼最小，操作更顺滑）
    dhd.enableForce(True)
    print("   ✓ 力输出已开启（零力透明模式）")

    # -----------------------------------------------------------
    # 2. 连接 Franka 机械臂
    # -----------------------------------------------------------
    robot_ip = "192.168.1.51"
    print(f"[2] 连接 Franka 机械臂 {robot_ip} ...")
    panda = panda_py.Panda(robot_ip)
    panda.recover()
    panda.set_default_behavior()
    print("   ✓ 机械臂已连接")

    # -----------------------------------------------------------
    # 3. 连接 Franka 夹爪
    # -----------------------------------------------------------
    print(f"[3] 连接 Franka 夹爪 ...")
    gripper = panda_py.libfranka.Gripper(robot_ip)
    gripper.homing()  # 标定
    print("   ✓ 夹爪已连接")

    # -----------------------------------------------------------
    # 4. 读取初始状态
    # -----------------------------------------------------------
    print("[4] 读取初始状态 ...")
    init_pos = panda.get_position().copy()
    init_ori = panda.get_orientation().copy()
    print(f"   初始末端位置: {np.round(init_pos, 4)}")

    # -----------------------------------------------------------
    # 5. 标定 Omega.7 零点
    # -----------------------------------------------------------
    print("[5] 标定 Omega.7 零点（松开手柄，保持静止）...")
    time.sleep(1.0)
    omega_home = np.zeros(3)
    for _ in range(100):
        pos = np.zeros(3)
        dhd.getPosition(pos)
        omega_home += pos
    omega_home /= 100.0
    print(f"   Omega 零点: {np.round(omega_home, 4)}")
    print("   ✓ 标定完成")

    virtual_ref = init_pos.copy()

    # -----------------------------------------------------------
    # 6. 启动笛卡尔阻抗控制器
    # -----------------------------------------------------------
    print("[6] 启动笛卡尔阻抗控制器 ...")
    impedance = np.diag([200.0, 200.0, 200.0, 10.0, 10.0, 10.0])
    ctrl = controllers.CartesianImpedance(
        impedance=impedance,
        damping_ratio=1.0,
        nullspace_stiffness=0.5,
        filter_coeff=1.0,
    )
    panda.start_controller(ctrl)
    ctrl.set_control(init_pos, init_ori)
    print("   ✓ 控制器已启动")

    print()
    print("=" * 60)
    print("   🎮 遥操作已开始！")
    print("   移动手柄 → 控制机械臂位置")
    print("   捏合/松开夹钳 → 夹爪抓取/松开")
    print("   灰色按钮 → 夹爪完全张开复位")
    print("   🔴 Ctrl+C 安全停止")
    print("=" * 60)

    # -----------------------------------------------------------
    # 7. 主控制循环
    # -----------------------------------------------------------
    dt_pos = 1.0 / POS_CONTROL_FREQ       # 5ms
    dt_gripper = 1.0 / GRIPPER_UPDATE_FREQ  # 100ms

    # 夹爪状态跟踪
    grasp_hysteresis = 0.01      # 防抖阈值：开度变化超过 12mm 才触发命令
    gripper_was_open = True      # 记录上次夹爪是否打开
    last_gripper_cmd = 0.08      # 上次发送的开度
    last_gripper_time = 0.0      # 上次夹爪更新的时间戳
    last_print_time = 0.0        # 上次打印刷新的时间戳

    # 夹爪读数缓存（每次位置循环都读，但只在夹爪循环里处理）
    omega_grip = 0.0
    button_grasp = 0

    loop_count = 0

    try:
        while True:
            t_loop_start = time.perf_counter()

            # ======== 1. 读 Omega7 位置 ========
            t1 = time.perf_counter()
            raw_pos = np.zeros(3)
            dhd.getPosition(raw_pos)
            t2 = time.perf_counter()

            # ======== 2. 计算目标位置 ========
            delta = raw_pos - omega_home
            target_pos = virtual_ref + delta * SCALE_POS * SIGN
            t3 = time.perf_counter()

            # ======== 3. 发给 Franka ========
            ctrl.set_control(target_pos, init_ori)
            t4 = time.perf_counter()

            # 每周期发送零力指令，保持手柄零力透明（无阻力手感）
            dhd.setForce(np.zeros(3))

            # 同时读取夹爪角度和按钮（读值不阻塞，供夹爪循环使用）
            gripper_angle = ctypes.c_double()
            dhd.getGripperAngleDeg(gripper_angle)
            omega_grip = gripper_angle.value
            button_grasp = dhd.getButton(0)

            # ======== 4. 夹爪（低频执行） ========
            t5 = time.perf_counter()
            now = time.time()
            if (now - last_gripper_time) >= dt_gripper:
                grip_norm = np.clip(
                    (omega_grip - GRIPPER_ANGLE_CLOSE) / (GRIPPER_ANGLE_OPEN - GRIPPER_ANGLE_CLOSE),
                    0.0, 1.0
                )
                target_width = grip_norm * GRIPPER_MAX
                width_change = abs(target_width - last_gripper_cmd)
                if width_change > grasp_hysteresis:
                    if grip_norm > 0.8:
                        gripper.move(target_width, GRIPPER_SPEED)
                        gripper_was_open = True
                    elif grip_norm < 0.2:
                        gripper.grasp(
                            target_width, GRIPPER_SPEED, GRIPPER_FORCE,
                            GRIPPER_EPS_INNER, GRIPPER_EPS_OUTER,
                        )
                        gripper_was_open = False
                    else:
                        gripper.move(target_width, GRIPPER_SPEED)
                    last_gripper_cmd = target_width
                if button_grasp:
                    gripper.move(GRIPPER_MAX, GRIPPER_SPEED)
                    last_gripper_cmd = GRIPPER_MAX
                last_gripper_time = now

            t_loop_end = time.perf_counter()

            # ======== 每 100 周期打印一次统计 ========
            loop_count += 1
            if loop_count % 100 == 0:
                print(f"\n=== 周期 #{loop_count} ===")
                print(f"  总周期: {(t_loop_end - t_loop_start)*1000:.2f} ms")
                print(f"  Omega读: {(t2 - t1)*1000:.2f} ms")
                print(f"  计算:    {(t3 - t2)*1000:.2f} ms")
                print(f"  Franka写:{(t4 - t3)*1000:.2f} ms")
                print(f"  夹爪:    {(t5 - t4)*1000:.2f} ms")
                print(f"  其他/idle:{(t_loop_end - t5)*1000:.2f} ms")

            # ======== 控制周期（按 200Hz 位置频率 sleep） ========
            elapsed = time.perf_counter() - t_loop_start
            sleep_time = dt_pos - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\n\n⚠️  收到 Ctrl+C，安全停止...")
    except Exception as e:
        print(f"\n\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("   关闭 Omega.7...")
        dhd.close()
        print("✅ 已安全停止")


if __name__ == "__main__":
    main()

