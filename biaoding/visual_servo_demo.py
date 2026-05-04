#!/usr/bin/env python3
"""
视觉伺服演示：相机看到标定板 → 机器人自动移过去
=============================================
流程:
  1. 加载标定结果 T_gripper_camera
  2. D435i 实时检测 ChArUco 板
  3. 换算成基坐标系下的目标位置
  4. 按回车 → 机器人平滑移动到标定板前方

用法:
  python3 biaoding/visual_servo_demo.py --robot-ip 192.168.1.51

依赖:
  pip install pyrealsense2 numpy opencv-python opencv-contrib-python panda-py
"""

import argparse
import json
import math
import select
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import pyrealsense2 as rs
import panda_py
import panda_py.libfranka as lf
import panda_py.controllers as controllers

# ── ChArUco 参数（与标定时一致） ──
SQUARES_X = 5
SQUARES_Y = 7
SQUARE_LENGTH = 0.030
MARKER_LENGTH = 0.022
DICT_NAME = "DICT_5X5_100"

ARUCO_DICT = {
    "DICT_4X4_50": cv2.aruco.DICT_4X4_50,
    "DICT_4X4_100": cv2.aruco.DICT_4X4_100,
    "DICT_4X4_250": cv2.aruco.DICT_4X4_250,
    "DICT_5X5_50": cv2.aruco.DICT_5X5_50,
    "DICT_5X5_100": cv2.aruco.DICT_5X5_100,
    "DICT_5X5_250": cv2.aruco.DICT_5X5_250,
    "DICT_6X6_50": cv2.aruco.DICT_6X6_50,
    "DICT_6X6_100": cv2.aruco.DICT_6X6_100,
    "DICT_6X6_250": cv2.aruco.DICT_6X6_250,
}


def load_calibration(path="biaoding/calibration_result.json"):
    """加载标定结果，返回 T_gripper_camera (4×4 numpy 数组)。"""
    with open(path) as f:
        results = json.load(f)
    best = min(results, key=lambda r: r["consistency_metrics"]["translation_mean_m"])
    T = np.array(best["transform_4x4"], dtype=float)
    print(f"  加载标定: {best['method']} | 平移误差 {best['consistency_metrics']['translation_mean_m']*1000:.1f} mm")
    return T


def create_charuo_board():
    dictionary = cv2.aruco.getPredefinedDictionary(ARUCO_DICT[DICT_NAME])
    board = cv2.aruco.CharucoBoard_create(
        SQUARES_X, SQUARES_Y, SQUARE_LENGTH, MARKER_LENGTH, dictionary,
    )
    return board, dictionary


def detect_board(pipeline, align, board, dictionary, camera_matrix, dist_coeffs):
    """捕获一帧 → 检测 ChArUco → 返回 T_target_camera 或 None。"""
    frames = pipeline.wait_for_frames()
    aligned_frames = align.process(frames)
    color_frame = aligned_frames.get_color_frame()
    color_image = np.asanyarray(color_frame.get_data())
    gray = cv2.cvtColor(color_image, cv2.COLOR_BGR2GRAY)

    corners, ids, _ = cv2.aruco.detectMarkers(gray, dictionary)
    annotated = color_image.copy()

    if ids is None or len(ids) < 3:
        return False, annotated, None

    cv2.aruco.drawDetectedMarkers(annotated, corners, ids)

    retval, charuco_corners, charuco_ids = cv2.aruco.interpolateCornersCharuco(
        corners, ids, gray, board,
    )
    if charuco_corners is None or len(charuco_corners) < 4:
        return False, annotated, None

    cv2.aruco.drawDetectedCornersCharuco(annotated, charuco_corners, charuco_ids)

    rvec = np.zeros((3, 1), dtype=float)
    tvec = np.zeros((3, 1), dtype=float)
    success = cv2.aruco.estimatePoseCharucoBoard(
        charuco_corners, charuco_ids, board, camera_matrix, dist_coeffs, rvec, tvec,
    )
    if not success:
        return False, annotated, None

    cv2.drawFrameAxes(annotated, camera_matrix, dist_coeffs, rvec, tvec, 0.04)

    T_target_camera = np.eye(4, dtype=float)
    T_target_camera[:3, :3] = cv2.Rodrigues(rvec)[0]
    T_target_camera[:3, 3] = tvec.flatten()

    return True, annotated, T_target_camera


def setup_camera():
    """初始化 D435i，返回 pipeline 和相机内参。"""
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.color, 1280, 720, rs.format.bgr8, 30)
    config.enable_stream(rs.stream.depth, 1280, 720, rs.format.z16, 30)
    profile = pipeline.start(config)

    for _ in range(10):
        pipeline.wait_for_frames()

    align = rs.align(rs.stream.color)
    color_stream = profile.get_stream(rs.stream.color)
    intrinsics = color_stream.as_video_stream_profile().get_intrinsics()

    camera_matrix = np.array([
        [intrinsics.fx, 0, intrinsics.ppx],
        [0, intrinsics.fy, intrinsics.ppy],
        [0, 0, 1],
    ], dtype=float)
    dist_coeffs = np.array(intrinsics.coeffs, dtype=float)

    return pipeline, align, camera_matrix, dist_coeffs


def otee_to_transform(O_T_EE):
    """16元素列主序 → 4×4 numpy 数组。"""
    T = np.array([
        [O_T_EE[0], O_T_EE[4], O_T_EE[8],  O_T_EE[12]],
        [O_T_EE[1], O_T_EE[5], O_T_EE[9],  O_T_EE[13]],
        [O_T_EE[2], O_T_EE[6], O_T_EE[10], O_T_EE[14]],
        [0.0,        0.0,        0.0,         1.0],
    ], dtype=float)
    return T


def rotation_to_quat(R):
    """旋转矩阵 → 四元数 [x, y, z, w]。"""
    trace = np.trace(R)
    if trace > 0:
        S = np.sqrt(trace + 1.0) * 2
        qw = 0.25 * S
        qx = (R[2, 1] - R[1, 2]) / S
        qy = (R[0, 2] - R[2, 0]) / S
        qz = (R[1, 0] - R[0, 1]) / S
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        S = np.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2
        qw = (R[2, 1] - R[1, 2]) / S
        qx = 0.25 * S
        qy = (R[0, 1] + R[1, 0]) / S
        qz = (R[0, 2] + R[2, 0]) / S
    elif R[1, 1] > R[2, 2]:
        S = np.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2
        qw = (R[0, 2] - R[2, 0]) / S
        qx = (R[0, 1] + R[1, 0]) / S
        qy = 0.25 * S
        qz = (R[1, 2] + R[2, 1]) / S
    else:
        S = np.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2
        qw = (R[1, 0] - R[0, 1]) / S
        qx = (R[0, 2] + R[2, 0]) / S
        qy = (R[1, 2] + R[2, 1]) / S
        qz = 0.25 * S
    norm = math.sqrt(qx*qx + qy*qy + qz*qz + qw*qw)
    return np.array([qx/norm, qy/norm, qz/norm, qw/norm])


def move_smoothly(panda, robot, target_pos, step_m=0.002, step_s=0.08):
    """笛卡尔阻抗控制器 + 逐毫米增量平滑移动（加减速，保持末端朝向不变）。

    只控制位置，不改变末端朝向，避免朝向拧成标定板角度导致"倾斜"。

    参数:
        panda: Panda 实例
        robot: libfranka.Robot 实例
        target_pos: [x, y, z] 目标位置
        step_m: 每步移动距离 (默认 2mm)
        step_s: 每步间隔 (默认 0.08s = 80ms)
    """
    # 读取当前位置和朝向
    state = robot.read_once()
    current_pos = np.array([state.O_T_EE[12], state.O_T_EE[13], state.O_T_EE[14]], dtype=float)

    # 目标位置
    target_pos = np.array(target_pos, dtype=float).flatten()

    # 计算当前位置 => 目标位置的向量和距离
    delta = target_pos - current_pos
    total_dist = np.linalg.norm(delta)

    if total_dist < 0.005:  # < 5mm 就不动了
        print("   📏 目标太近 (< 5mm)，跳过移动")
        return

    direction = delta / total_dist
    n_steps = max(10, int(total_dist / step_m))  # 最少 10 步
    print(f"   📏 距离 {total_dist*1000:.0f}mm → 分 {n_steps} 步 ≈ {step_m*1000:.1f}mm/步")

    # 提取当前朝向四元数
    current_R = np.array([
        [state.O_T_EE[0], state.O_T_EE[4], state.O_T_EE[8]],
        [state.O_T_EE[1], state.O_T_EE[5], state.O_T_EE[9]],
        [state.O_T_EE[2], state.O_T_EE[6], state.O_T_EE[10]],
    ], dtype=float)
    current_quat = rotation_to_quat(current_R)

    # 启动笛卡尔阻抗控制器（软刚度，防止抖动和 reflex）
    impedance = np.diag([100.0, 100.0, 100.0, 5.0, 5.0, 5.0])  # 更软的刚度
    ctrl = controllers.CartesianImpedance(
        impedance=impedance,
        damping_ratio=1.5,      # 更大的阻尼抑制抖动
        nullspace_stiffness=0.3,
        filter_coeff=0.5,       # 更强的滤波
    )
    panda.start_controller(ctrl)

    # 先设置到当前位置（避免控制器启动时的跳变）
    ctrl.set_control(current_pos, current_quat)
    time.sleep(0.2)

    try:
        accel_steps = max(3, n_steps // 5)   # 前 20% 加速
        decel_steps = max(3, n_steps // 5)   # 后 20% 减速

        for i in range(n_steps):
            # 速度曲线：三角形加减速
            if i < accel_steps:
                speed_factor = i / accel_steps
            elif i >= n_steps - decel_steps:
                speed_factor = (n_steps - i) / decel_steps
            else:
                speed_factor = 1.0

            # 位置插值：用速度因子控制每步位移
            step = direction * (total_dist / n_steps) * speed_factor
            pos = current_pos + delta * (i + 1) / n_steps

            ctrl.set_control(pos, current_quat)
            time.sleep(step_s)

            # 进度显示
            pct = (i + 1) * 100 // n_steps
            bar_len = 30
            filled = bar_len * (i + 1) // n_steps
            bar = '█' * filled + '░' * (bar_len - filled)
            print(f"\r   进度: {bar} {pct}% | 距离 {total_dist*(1-(i+1)/n_steps)*1000:.0f}mm"
                  f" | 速度 {'🟢' if speed_factor > 0.8 else '🟡' if speed_factor > 0.3 else '🔴'}", end="", flush=True)

        print()
        print("   ✅ 平滑移动完成")
    finally:
        panda.stop_controller()
        try:
            panda.set_default_behavior()
        except RuntimeError:
            pass


def main():
    parser = argparse.ArgumentParser(description="手眼标定视觉伺服演示")
    parser.add_argument("--robot-ip", default="192.168.1.51", help="Panda IP")
    parser.add_argument("--calib", default="biaoding/calibration_result.json", help="标定结果路径")
    args = parser.parse_args()

    print("=" * 70)
    print("  🎯 视觉伺服演示：D435i 看到标定板 → Panda 自动移过去")
    print("=" * 70)
    print()

    # ── 1. 加载标定结果 ──
    print("[1/4] 加载标定结果 ...")
    T_gripper_camera = load_calibration(args.calib)
    print(f"   T_gripper_camera =")
    print(T_gripper_camera.round(4))
    print()

    # ── 2. 连接 D435i ──
    print("[2/4] 连接 D435i ...")
    pipeline, align, camera_matrix, dist_coeffs = setup_camera()
    board, dictionary = create_charuo_board()
    print("   ✓ D435i 就绪")
    print()

    # ── 3. 连接 Panda ──
    print(f"[3/4] 连接 Panda ({args.robot_ip}) ...")
    panda = panda_py.Panda(args.robot_ip)
    robot = panda.get_robot()
    try:
        panda.recover()
    except RuntimeError:
        pass
    try:
        panda.set_default_behavior()
    except RuntimeError:
        pass
    print("   ✓ Panda 就绪")
    print()

    # ── 4. 视觉伺服循环 ──
    print("[4/4] 视觉伺服循环")
    print("-" * 70)
    print("  预览窗口显示实时画面，绿色文字表示检测到标定板")
    print("  Enter → 计算机器人目标位置并移动（保持当前朝向）")
    print("  终端显示：标定板在基坐标系下的坐标")
    print("  q → 退出")
    print("-" * 70)
    print()

    window_name = "Visual Servo Demo"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 960, 600)

    try:
        while True:
            # ── 检测标定板 ──
            detected, annotated, T_target_camera = detect_board(
                pipeline, align, board, dictionary, camera_matrix, dist_coeffs,
            )

            # ── 如果检测到了，换算成基坐标系 ──
            if detected:
                state = robot.read_once()
                T_base_gripper = otee_to_transform(state.O_T_EE)

                # 核心公式：T_base_target = T_base_gripper × T_gripper_camera × T_target_camera
                T_base_target = T_base_gripper @ T_gripper_camera @ T_target_camera

                # 标定板在基坐标系下的位置
                board_pos = T_base_target[:3, 3]

                # 相机朝向 (相机 z 轴在基坐标系下的方向)
                cam_R_base = T_base_gripper[:3, :3] @ T_gripper_camera[:3, :3]
                cam_z_base = cam_R_base @ np.array([0, 0, 1])

                # 目标位置：标定板前方 15cm（沿相机视线方向后退）
                # 相机看到板子 → 板子在相机前方 → 相机后退 15cm
                target_pos = board_pos - 0.15 * cam_z_base

                color = (0, 255, 0)
                info = (f"Board pos: x={board_pos[0]:.3f}  "
                        f"y={board_pos[1]:.3f}  z={board_pos[2]:.3f}  "
                        f"| 按 Enter 移动")
            else:
                color = (0, 0, 255)
                info = "未检测到标定板"

            # ── 窗口显示 ──
            cv2.putText(annotated, info, (15, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
            cv2.putText(annotated, "Enter: Move  |  Q: Quit",
                        (15, annotated.shape[0] - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 180, 180), 2)
            cv2.imshow(window_name, annotated)

            # ── 终端：实时打印状态 ──
            if detected:
                print(f"\r  标定板在基坐标系: x={board_pos[0]:+.3f}  "
                      f"y={board_pos[1]:+.3f}  z={board_pos[2]:+.3f}  "
                      f"目标位置: x={target_pos[0]:+.3f}  "
                      f"y={target_pos[1]:+.3f}  z={target_pos[2]:+.3f}  "
                      f"末端: x={T_base_gripper[0,3]:+.3f}  "
                      f"y={T_base_gripper[1,3]:+.3f}  "
                      f"z={T_base_gripper[2,3]:+.3f}    ", end="", flush=True)

            # ── 非阻塞终端输入 ──
            has_input = select.select([sys.stdin], [], [], 0.05)[0]
            if has_input:
                cmd = sys.stdin.readline().strip().lower()
                if cmd == "q":
                    print("\n   ⏹ 退出")
                    break

                if cmd == "" and detected:
                    print("\n")
                    print("   ╔" + "═" * 60 + "╗")
                    print(f"   ║  🚀 平滑移动（保持当前朝向）")
                    print("   ╠" + "═" * 60 + "╣")
                    print(f"   ║  目标位置: x={target_pos[0]:.3f}  "
                          f"y={target_pos[1]:.3f}  z={target_pos[2]:.3f}")
                    print("   ╚" + "═" * 60 + "╝")
                    print()

                    print("   🚀 开始平滑移动")
                    print("   (按 Ctrl+C 可随时停止)")
                    print()
                    try:
                        move_smoothly(
                            panda, robot,
                            target_pos=target_pos,
                            step_m=0.002,
                            step_s=0.08,
                        )
                    except RuntimeError as e:
                        print(f"\n   ⚠ 移动失败: {e}")
                        print("   💡 示教模式 (T1) 下无法自动移动，需要退出示教模式后才能用")

            cv2.waitKey(1)

    except KeyboardInterrupt:
        print("\n\n⚠ 中断")
    finally:
        cv2.destroyAllWindows()
        pipeline.stop()
        print("✅ 资源已释放")


if __name__ == "__main__":
    main()
