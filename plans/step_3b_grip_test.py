#!/usr/bin/env python3
"""
Step 3b — 夹持数据采集（抓物体→保持→释放）
==============================================
目的: 在实际夹持和释放过程中验证 GripForceEstimator 的 f_grip 输出
      和 contact_detected 事件是否能正确反映夹持状态。

操作:
    1. 连接 Franka，移动到目标物体上方（预设位置）
    2. 记录: 张开 → 接近 → 夹持 → 保持 3s → 释放
    3. 全程记录 width, τ_wrist, f_grip
    4. 检测接触事件是否触发

用法:
    python3 plans/step_3b_grip_test.py

预期:
    夹持时 f_grip 明显上升（>0.3），释放后下降（<0.1）
    接触事件在夹持阶段触发，释放后复位

作者: mfj
日期: 2026-05
"""

import sys
import time
import numpy as np
import panda_py
from panda_py import controllers, libfranka

ROBOT_IP = "192.168.1.51"
WRIST_JOINT_INDICES = [4, 5, 6]

# ── 基于 Step 3a/3b 实测数据校准的参数 ──
#   Step 3a: ||τ_wrist|| 空载基线 mean=0.16 Nm
#   Step 3b 实测: 张开期 f_grip≈0.05 (0.16 Nm)
#                 夹持期 f_grip≈0.14 (0.41 Nm), 峰值 0.15 (0.46 Nm)
#                 为空载基线的 2.6~2.9 倍
TAU_MAX = 3.0             # 归一化分母，空载 f_grip=0.05
TORQUE_THRESHOLD = 0.4    # 基于峰值 0.46 Nm 下调（原 0.5）
WIDTH_EPSILON = 0.002     # 宽度变化停滞阈值
DEBOUNCE_FRAMES = 5       # 接触防抖帧数
FILTER_ALPHA = 0.3        # 低通滤波系数

# 预设夹持高度（相对于初始位置的 Z 偏移）
APPROACH_OFFSET = -0.05   # 下移 5cm 接近物体
GRIPPER_CLOSE_WIDTH = 0.03  # 夹持目标宽度

# ── 安全运动参数 ──
STEP_M = 0.002            # 每步移动 2mm
STEP_INTERVAL = 0.5       # 每步间隔 0.5s（越慢越安全）


def move_smoothly(panda, ctrl, target_pos, ori, step_m=0.002, step_s=0.5):
    """逐毫米步进平滑移动到目标位置，每步间隔 step_s 秒"""
    current = np.array(panda.get_position())
    target = np.array(target_pos)
    delta = target - current
    dist = np.linalg.norm(delta)
    steps = max(1, int(dist / step_m))
    vec = delta / steps
    for i in range(1, steps + 1):
        interim = current + vec * i
        ctrl.set_control(interim.tolist(), ori)
        time.sleep(step_s)
        print(f"      → 移动中: {i}/{steps} 步, Z={interim[2]:.3f}m")


def main():
    print("=" * 60)
    print("  Step 3b: 夹持数据采集")
    print("=" * 60)
    print(f"\n  机器人 IP: {ROBOT_IP}")
    print(f"  tau_max={TAU_MAX}, torque_threshold={TORQUE_THRESHOLD}")
    print(f"  debounce_frames={DEBOUNCE_FRAMES}, width_epsilon={WIDTH_EPSILON}")
    print(f"  运动参数: step={STEP_M*1000:.0f}mm/step, interval={STEP_INTERVAL}s\n")

    # ── 连接 ──
    print("[1/5] 连接 Franka Panda ...")
    panda = panda_py.Panda(ROBOT_IP)
    panda.recover()
    panda.set_default_behavior()
    gripper = panda_py.libfranka.Gripper(ROBOT_IP)
    gripper.homing()
    gripper.move(0.08, 0.1)
    time.sleep(1.0)
    print("   ✓ 已连接 + 夹爪张开\n")

    # ── 启动阻抗控制 ──
    print("[2/5] 启动笛卡尔阻抗控制器 ...")
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
    print("   ✓ 控制器已启动\n")

    # ── 数据记录 ──
    print("[3/5] 准备采集数据 ...")
    print("   请将物体放在机械臂末端正下方，按 Enter 开始夹持测试")
    input("   [按 Enter 继续] ")

    # 数据容器
    timestamps = []
    widths = []
    tau_wrist_norms = []
    f_grips = []
    contact_events = []
    phases = []  # "open", "approach", "grasp", "hold", "release"

    # 状态
    f_grip_filtered = 0.0
    contact_frames = 0
    contact_detected = False
    prev_width = gripper.read_once().width

    # ── 阶段 1: 张开 ──
    print("\n[阶段 A] 夹爪张开，记录基线 ...")
    input("   按 Enter 继续")
    for _ in range(20):
        state = panda.get_state()
        gw = gripper.read_once().width
        tau_ext = np.array(state.tau_ext_hat_filtered, dtype=float)
        tau_wrist = np.array([tau_ext[i] for i in WRIST_JOINT_INDICES])
        tau_norm = np.linalg.norm(tau_wrist)

        f_grip_raw = np.clip(tau_norm / TAU_MAX, 0.0, 1.0)
        f_grip_filtered = FILTER_ALPHA * f_grip_raw + (1 - FILTER_ALPHA) * f_grip_filtered \
            if len(timestamps) > 0 else f_grip_raw

        timestamps.append(time.time())
        widths.append(gw)
        tau_wrist_norms.append(tau_norm)
        f_grips.append(f_grip_filtered)
        contact_events.append(contact_detected)
        phases.append("open")

        print(f"    [{len(timestamps):3d}] width={gw*1000:.1f}mm | "
              f"||τ||={tau_norm:.2f} | f_grip={f_grip_filtered:.3f}")
        time.sleep(0.1)

    # ── 阶段 2: 下移（接近物体） ──
    print("\n[阶段 B] 末端下移接近物体 ...")
    approach_pos = init_pos.copy()
    approach_pos[2] += APPROACH_OFFSET
    total_dist = abs(APPROACH_OFFSET)
    print(f"   目标: Z 降 {total_dist*1000:.0f}mm → {approach_pos[2]:.3f}m")
    print(f"   步进: {STEP_M*1000:.0f}mm/步 × {STEP_INTERVAL}s/步")
    print("   (随时可按 Ctrl+C 中止)")
    move_smoothly(panda, ctrl, approach_pos, init_ori, step_m=STEP_M, step_s=STEP_INTERVAL)
    time.sleep(0.5)

    for _ in range(10):
        state = panda.get_state()
        gw = gripper.read_once().width
        tau_ext = np.array(state.tau_ext_hat_filtered, dtype=float)
        tau_norm = np.linalg.norm(tau_ext[WRIST_JOINT_INDICES])

        f_grip_raw = np.clip(tau_norm / TAU_MAX, 0.0, 1.0)
        f_grip_filtered = FILTER_ALPHA * f_grip_raw + (1 - FILTER_ALPHA) * f_grip_filtered

        timestamps.append(time.time())
        widths.append(gw)
        tau_wrist_norms.append(tau_norm)
        f_grips.append(f_grip_filtered)
        contact_events.append(contact_detected)
        phases.append("approach")

        print(f"    [{len(timestamps):3d}] approach | "
              f"width={gw*1000:.1f}mm | ||τ||={tau_norm:.2f} | f_grip={f_grip_filtered:.3f}")
        time.sleep(0.1)

    # ── 阶段 3: 夹持 ──
    print(f"\n[阶段 C] 夹持 (width={GRIPPER_CLOSE_WIDTH*1000:.0f}mm, force=20N) ...")
    gripper.grasp(GRIPPER_CLOSE_WIDTH, speed=0.1, force=20.0,
                  epsilon_inner=0.005, epsilon_outer=0.005)

    for _ in range(30):  # 3 秒
        state = panda.get_state()
        gw = gripper.read_once().width
        tau_ext = np.array(state.tau_ext_hat_filtered, dtype=float)
        tau_wrist = np.array([tau_ext[i] for i in WRIST_JOINT_INDICES])
        tau_norm = np.linalg.norm(tau_wrist)

        f_grip_raw = np.clip(tau_norm / TAU_MAX, 0.0, 1.0)
        f_grip_filtered = FILTER_ALPHA * f_grip_raw + (1 - FILTER_ALPHA) * f_grip_filtered

        # 接触检测（双模式：力矩阈值 + is_grasped 辅助）
        width_change = abs(gw - prev_width) if prev_width > 0 else 999.0
        width_stalled = width_change < WIDTH_EPSILON
        not_at_max = gw < 0.08 * 0.95

        # 模式 A: 力矩阈值（基于实测重物体 0.55 Nm 校准）
        torque_active = tau_norm > TORQUE_THRESHOLD

        # 模式 B: 夹爪自身 is_grasped（备选）
        gripper_state = gripper.read_once()
        is_grasped = gripper_state.is_grasped

        if width_stalled and not_at_max and (torque_active or is_grasped):
            contact_frames += 1
            if contact_frames >= DEBOUNCE_FRAMES and not contact_detected:
                contact_detected = True
                print(f"    >>> 📌 接触事件触发! f_grip={f_grip_filtered:.3f}, "
                      f"||τ||={tau_norm:.2f}Nm, is_grasped={is_grasped}")
        else:
            contact_frames = 0

        timestamps.append(time.time())
        widths.append(gw)
        tau_wrist_norms.append(tau_norm)
        f_grips.append(f_grip_filtered)
        contact_events.append(contact_detected)
        phases.append("hold")

        status = "📌 已夹持!" if contact_detected else "夹持中..."
        print(f"    [{len(timestamps):3d}] {status} | "
              f"width={gw*1000:.1f}mm | ||τ||={tau_norm:.2f} | f_grip={f_grip_filtered:.3f}")
        prev_width = gw
        time.sleep(0.1)

    # ── 阶段 4: 释放 ──
    print("\n[阶段 D] 释放夹爪 ...")
    gripper.move(0.08, 0.1)
    time.sleep(0.5)

    for _ in range(15):
        state = panda.get_state()
        gw = gripper.read_once().width
        tau_ext = np.array(state.tau_ext_hat_filtered, dtype=float)
        tau_norm = np.linalg.norm(tau_ext[WRIST_JOINT_INDICES])

        f_grip_raw = np.clip(tau_norm / TAU_MAX, 0.0, 1.0)
        f_grip_filtered = FILTER_ALPHA * f_grip_raw + (1 - FILTER_ALPHA) * f_grip_filtered

        timestamps.append(time.time())
        widths.append(gw)
        tau_wrist_norms.append(tau_norm)
        f_grips.append(f_grip_filtered)
        contact_events.append(contact_detected)
        phases.append("release")

        print(f"    [{len(timestamps):3d}] 释放中... | "
              f"width={gw*1000:.1f}mm | ||τ||={tau_norm:.2f} | f_grip={f_grip_filtered:.3f}")
        time.sleep(0.1)

    # ── 慢速回到初始位置 ──
    print("\n[阶段 E] 慢速回到初始位置 ...")
    move_smoothly(panda, ctrl, init_pos, init_ori, step_m=STEP_M, step_s=STEP_INTERVAL)

    # ── 统计报告 ──
    print("\n" + "=" * 60)
    print("  测试报告")
    print("=" * 60)

    f_grip_arr = np.array(f_grips)
    grasp_f_grip = f_grip_arr[np.array(phases) == "hold"]
    release_f_grip = f_grip_arr[np.array(phases) == "release"]
    open_f_grip = f_grip_arr[np.array(phases) == "open"]

    print(f"\n  相位数: {len(timestamps)} 帧")
    print(f"  张开期 f_grip: mean={np.mean(open_f_grip):.3f}, max={np.max(open_f_grip):.3f}")
    print(f"  夹持期 f_grip: mean={np.mean(grasp_f_grip):.3f}, max={np.max(grasp_f_grip):.3f}")
    print(f"  释放期 f_grip: mean={np.mean(release_f_grip):.3f}, max={np.max(release_f_grip):.3f}")

    contact_any = any(contact_events)
    n_contacts = sum(1 for c in contact_events if c)
    print(f"\n  接触事件触发: {'✅ 是' if contact_any else '❌ 否'} ({n_contacts} 帧)")

    print("\n" + "-" * 60)
    print("  验证清单:")
    print("  [ ] 张开期 f_grip < 0.1（空载噪声小）")
    print("  [ ] 夹持期 f_grip 明显上升 > 0.3")
    print("  [ ] 释放后 f_grip 下降回到 < 0.1")
    print("  [ ] 接触事件在夹持阶段正确触发（不误报、不漏报）")
    print("  [ ] ||τ_wrist|| 在夹持时明显 > 空载基线")

    panda.stop_controller()
    print("\n控制器已停止。\n")


if __name__ == "__main__":
    main()
