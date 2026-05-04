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
import panda_py
from panda_py import controllers

# ============================================================
# 配置参数
# ============================================================
SCALE_POS = 0.5        # 移动缩放
CONTROL_FREQ = 200.0   # 控制频率 (Hz)
SIGN = np.array([-1.0, -1.0, 1.0])  # 坐标轴方向修正

GRIPPER_SPEED = 0.1    # 夹爪速度 (m/s)
GRIPPER_FORCE = 20.0   # 夹爪夹持力 (N)
GRIPPER_MAX = 0.08     # 夹爪最大开度 (m)


def main():
    # -----------------------------------------------------------
    # 1. 连接 Omega.7
    # -----------------------------------------------------------
    print("[1] 连接 Omega.7 ...")
    if dhd.open() < 0:
        print("   ❌ Omega.7 连接失败，检查 USB 线")
        sys.exit(1)
    print(f"   ✓ 已连接: {dhd.getSystemName()}")

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
    dt = 1.0 / CONTROL_FREQ

    # 夹爪状态跟踪
    grasp_hysteresis = 0.005  # 防抖阈值
    gripper_was_open = True   # 记录上次夹爪是否打开
    last_gripper_cmd = 0.08   # 上次发送的开度

    try:
        while True:
            loop_start = time.time()

            # ---- a. 读取 Omega.7 位置（位置控制） ----
            raw_pos = np.zeros(3)
            dhd.getPosition(raw_pos)
            delta = raw_pos - omega_home
            target_pos = virtual_ref + delta * SCALE_POS * SIGN
            ctrl.set_control(target_pos, init_ori)

            # ---- b. 读取 Omega 夹钳开度（夹爪控制） ----
            gap = ctypes.c_double()
            dhd.getGripperGap(ctypes.byref(gap))
            omega_grip = max(0.0, gap.value)  # 夹钳开度 ≥ 0

            # 读取灰色按钮
            button_grasp = dhd.getButton(0)

            # ---- c. 映射到 Franka 夹爪 ----
            # Omega 夹钳开度 [0~0.03m] → Franka 夹爪开度 [0.0~GRIPPER_MAX]
            grip_norm = min(1.0, omega_grip / 0.03)  # 归一化
            target_width = grip_norm * GRIPPER_MAX

            # 防抖：变化够大才发送
            width_change = abs(target_width - last_gripper_cmd)
            if width_change > grasp_hysteresis:
                # 夹钳完全松开 → 夹爪张开
                if grip_norm > 0.8:
                    gripper.move(target_width, GRIPPER_SPEED)
                    gripper_was_open = True
                # 夹钳捏合 → 夹爪抓取
                elif grip_norm < 0.2:
                    gripper.grasp(target_width, GRIPPER_SPEED, GRIPPER_FORCE)
                    gripper_was_open = False
                else:
                    gripper.move(target_width, GRIPPER_SPEED)
                last_gripper_cmd = target_width

            # 灰色按钮 → 完全张开
            if button_grasp:
                gripper.move(GRIPPER_MAX, GRIPPER_SPEED)
                last_gripper_cmd = GRIPPER_MAX

            # ---- d. 显示信息 ----
            grip_status = "🖐 张开" if grip_norm > 0.5 else "✊ 抓紧"
            print(
                f"\r   Omega Δ: x={delta[0]:+.3f} y={delta[1]:+.3f} z={delta[2]:+.3f}  "
                f"|  夹钳: {omega_grip:.3f}→{target_width*1000:.0f}mm {grip_status}  "
                f"|  目标: {target_pos[0]:.3f} {target_pos[1]:.3f} {target_pos[2]:.3f}   ",
                end="",
            )

            # ---- e. 控制频率 ----
            elapsed = time.time() - loop_start
            sleep_time = dt - elapsed
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
