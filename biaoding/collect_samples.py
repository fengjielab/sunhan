#!/usr/bin/env python3
"""
D435i + Panda 手眼标定数据采集脚本
====================================
流程:
  1. 连接 D435i 和 Panda
  2. 用户移动机械臂到新姿态 → 按回车采集
  3. 自动检测 ChArUco + 读取末端位姿 → 保存到 samples.json
  4. 采集 20~30 组后自动调用 handeye_calibrate.py 求解

用法:
  python3 collect_samples.py --robot-ip 192.168.1.51

依赖:
  pip install pyrealsense2 numpy opencv-python opencv-contrib-python panda-py
"""

import argparse
import json
import select
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import pyrealsense2 as rs
import panda_py
import panda_py.libfranka as lf

# ──────────────────────────────────────────────
# ChArUco 板参数（与 boards/charuco_a4_5x7_30mm.json 一致）
# ──────────────────────────────────────────────
SQUARES_X = 5
SQUARES_Y = 7
SQUARE_LENGTH = 0.030       # 30mm → 米
MARKER_LENGTH = 0.022       # 22mm → 米
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


def create_charuco_board():
    """创建 ChArUco 板对象，用于角点检测和位姿估计。"""
    dictionary = cv2.aruco.getPredefinedDictionary(ARUCO_DICT[DICT_NAME])
    board = cv2.aruco.CharucoBoard_create(
        SQUARES_X, SQUARES_Y,
        SQUARE_LENGTH, MARKER_LENGTH,
        dictionary,
    )
    return board, dictionary


def detect_and_draw(pipeline, align, board, dictionary, camera_matrix, dist_coeffs):
    """捕获一帧 → 检测 ChArUco → 在原图上画出结果。

    返回:
        (color_image_with_annotations, 成功标志, target_wrt_camera, 角点数)
    """
    frames = pipeline.wait_for_frames()
    aligned_frames = align.process(frames)
    color_frame = aligned_frames.get_color_frame()
    color_image = np.asanyarray(color_frame.get_data())
    gray = cv2.cvtColor(color_image, cv2.COLOR_BGR2GRAY)

    # 1. 检测 ArUco 码
    corners, ids, _ = cv2.aruco.detectMarkers(gray, dictionary)
    annotated = color_image.copy()

    if ids is not None and len(ids) >= 3:
        # 画出 ArUco 码边框
        cv2.aruco.drawDetectedMarkers(annotated, corners, ids)

        # 2. ChArUco 角点插值
        retval, charuco_corners, charuco_ids = cv2.aruco.interpolateCornersCharuco(
            corners, ids, gray, board
        )

        if charuco_corners is not None and len(charuco_corners) >= 4:
            # 3. 画出 ChArUco 角点（用圆圈标注）
            cv2.aruco.drawDetectedCornersCharuco(annotated, charuco_corners, charuco_ids)

            # 4. 估算标定板位姿
            rvec = np.zeros((3, 1), dtype=float)
            tvec = np.zeros((3, 1), dtype=float)
            success = cv2.aruco.estimatePoseCharucoBoard(
                charuco_corners, charuco_ids, board, camera_matrix, dist_coeffs, rvec, tvec
            )

            if success:
                # 5. 画出坐标系轴 (红色=X, 绿色=Y, 蓝色=Z)
                cv2.drawFrameAxes(annotated, camera_matrix, dist_coeffs, rvec, tvec, 0.04)

                target_wrt_camera = np.eye(4, dtype=float)
                target_wrt_camera[:3, :3] = cv2.Rodrigues(rvec)[0]
                target_wrt_camera[:3, 3] = tvec.flatten()
                return True, annotated, target_wrt_camera, len(charuco_corners)

    return False, annotated, None, 0


def rotation_matrix_to_quaternion_xyzw(R):
    """旋转矩阵 → 四元数 (xyzw 顺序)。"""
    trace = np.trace(R)
    if trace > 0.0:
        s = np.sqrt(trace + 1.0) * 2.0
        w = 0.25 * s
        x = (R[2, 1] - R[1, 2]) / s
        y = (R[0, 2] - R[2, 0]) / s
        z = (R[1, 0] - R[0, 1]) / s
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        s = np.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2.0
        w = (R[2, 1] - R[1, 2]) / s
        x = 0.25 * s
        y = (R[0, 1] + R[1, 0]) / s
        z = (R[0, 2] + R[2, 0]) / s
    elif R[1, 1] > R[2, 2]:
        s = np.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2.0
        w = (R[0, 2] - R[2, 0]) / s
        x = (R[0, 1] + R[1, 0]) / s
        y = 0.25 * s
        z = (R[1, 2] + R[2, 1]) / s
    else:
        s = np.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2.0
        w = (R[1, 0] - R[0, 1]) / s
        x = (R[0, 2] + R[2, 0]) / s
        y = (R[1, 2] + R[2, 1]) / s
        z = 0.25 * s

    norm = np.sqrt(x * x + y * y + z * z + w * w)
    return np.array([x / norm, y / norm, z / norm, w / norm])


def otee_to_pos_quat(O_T_EE):
    """从 libfranka RobotState.O_T_EE (16元素列主序) 提取位置和四元数。
    
    O_T_EE 布局 (列主序 4×4):
      [R00, R10, R20, 0, R01, R11, R21, 0, R02, R12, R22, 0, x, y, z, 1]
    即:
      translation: O_T_EE[12], O_T_EE[13], O_T_EE[14]
      rotation:    O_T_EE[0:3] = R[:,0], O_T_EE[4:7] = R[:,1], O_T_EE[8:11] = R[:,2]
    """
    pos = np.array([O_T_EE[12], O_T_EE[13], O_T_EE[14]], dtype=float)
    R = np.array([
        [O_T_EE[0], O_T_EE[4], O_T_EE[8]],
        [O_T_EE[1], O_T_EE[5], O_T_EE[9]],
        [O_T_EE[2], O_T_EE[6], O_T_EE[10]],
    ], dtype=float)
    quat = rotation_matrix_to_quaternion_xyzw(R)
    return pos, quat


def setup_camera():
    """初始化 RealSense D435i，返回 pipeline 和相机内参。"""
    pipeline = rs.pipeline()
    config = rs.config()

    config.enable_stream(rs.stream.color, 1280, 720, rs.format.bgr8, 30)
    config.enable_stream(rs.stream.depth, 1280, 720, rs.format.z16, 30)

    profile = pipeline.start(config)

    for _ in range(10):
        pipeline.wait_for_frames()

    align_to = rs.stream.color
    align = rs.align(align_to)

    color_stream = profile.get_stream(rs.stream.color)
    intrinsics = color_stream.as_video_stream_profile().get_intrinsics()

    camera_matrix = np.array([
        [intrinsics.fx, 0, intrinsics.ppx],
        [0, intrinsics.fy, intrinsics.ppy],
        [0, 0, 1],
    ], dtype=float)

    dist_coeffs = np.array(intrinsics.coeffs, dtype=float)

    print(f"   分辨率: {intrinsics.width}×{intrinsics.height}")
    print(f"   内参 K: fx={intrinsics.fx:.2f}, fy={intrinsics.fy:.2f}")
    print(f"          ppx={intrinsics.ppx:.2f}, ppy={intrinsics.ppy:.2f}")
    print(f"   畸变: {dist_coeffs}")

    return pipeline, align, camera_matrix, dist_coeffs


def main():
    parser = argparse.ArgumentParser(
        description="采集 D435i + Panda 手眼标定样本"
    )
    parser.add_argument(
        "--robot-ip", default="192.168.1.51",
        help="Franka 机械臂 IP 地址 (默认: 192.168.1.51)"
    )
    parser.add_argument(
        "--samples", type=Path, default="samples.json",
        help="输出样本 JSON 文件路径 (默认: samples.json)"
    )
    parser.add_argument(
        "--min-samples", type=int, default=15,
        help="最少采集样本数 (默认: 15, 建议 20~30)"
    )
    parser.add_argument(
        "--skip-calibrate", action="store_true",
        help="采集完成后跳过自动标定求解"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("  D435i → Panda 手眼标定数据采集")
    print("=" * 70)
    print()

    # ── 1. 初始化 ChArUco ──
    print("[1/5] 初始化 ChArUco 检测器 ...")
    board, dictionary = create_charuco_board()
    print(f"   标定板: {SQUARES_X}×{SQUARES_Y}, {SQUARE_LENGTH*1000:.0f}mm 方格, {DICT_NAME}")
    print()

    # ── 2. 连接 RealSense ──
    print("[2/5] 连接 D435i ...")
    pipeline, align, camera_matrix, dist_coeffs = setup_camera()
    print("   ✓ D435i 已连接")
    print()

    # ── 3. 连接 Panda (仅读取模式) ──
    print(f"[3/5] 连接 Franka Panda ({args.robot_ip}) ...")
    panda = panda_py.Panda(args.robot_ip)
    # 获取底层 libfranka.Robot，用于 read_once() 实时读取（示教模式下必须）
    robot = panda.get_robot()
    try:
        panda.recover()
    except RuntimeError as e:
        print(f"   注意: recover 跳过 ({e})")
    try:
        panda.set_default_behavior()
    except RuntimeError as e:
        print(f"   注意: set_default_behavior 跳过 ({e})")
    print("   ✓ Panda 已连接（仅读取）")
    print()

    # ── 4. 采集样本 ──
    print("[4/5] 开始采集样本")
    print("-" * 70)
    print("  操作说明:")
    print("  1. 拖动机械臂到新姿态（示教模式）")
    print("  2. 观察 **预览窗口** 确认标定板被正确识别")
    print("     - ArUco 码被绿色方框标记")
    print("     - ChArUco 角点被圆圈标记")
    print("     - 坐标轴（红绿蓝）画出标定板姿态")
    print("  3. 机械臂静止后，在预览窗口按 Enter 采集")
    print("  4. 按 Q 退出（至少采集15组后可用）")
    print("-" * 70)
    print()

    samples = []
    sample_idx = 0
    failed_count = 0

    # 创建预览窗口，支持鼠标拖动调整大小
    window_name = "ChArUco Preview"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 960, 600)

    print("  按 Enter 开始采集  |  输入 q 退出")
    print()

    try:
        while True:
            # ── 实时预览：检测 + 画图 ──
            success, annotated, _, n_corners = detect_and_draw(
                pipeline, align, board, dictionary, camera_matrix, dist_coeffs,
            )

            # 窗口上叠加状态文字
            color = (0, 255, 0) if success else (0, 0, 255)
            status = f"Collected: {len(samples)}  |  Corners: {n_corners}  |  {'DETECT OK' if success else 'NO DETECT'}"
            cv2.putText(annotated, status, (15, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            cv2.imshow(window_name, annotated)

            # ── 非阻塞检查终端输入（0.05s 超时），同时兼顾 OpenCV 窗口刷新 ──
            has_input = select.select([sys.stdin], [], [], 0.05)[0]
            if not has_input:
                cv2.waitKey(1)
                continue

            user_input = sys.stdin.readline().strip().lower()

            if user_input in ("q", "quit"):
                if len(samples) >= args.min_samples:
                    print("   ⏹ 结束采集")
                    break
                else:
                    print(f"   ⚠ 至少 {args.min_samples} 组，当前 {len(samples)} 组，继续")
                    continue

            # ── 按 Enter（空行）触发采集 ──
            # 先输出一行提示，让用户知道开始采集了
            print(f"\n  采集 #{sample_idx+1} 中...    |  预览: {'✅ ' + str(n_corners) + ' 个角点' if success else '❌ 未检测到'}")

            # 短暂闪烁提示
            flash = annotated.copy()
            cv2.putText(flash, ">>> CAPTURING <<<", (annotated.shape[1] // 2 - 160, annotated.shape[0] // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)
            cv2.imshow(window_name, flash)
            cv2.waitKey(200)

            # ── 正式采集（再取一帧，确保最新） ──
            success, color_img, target_wrt_camera, n_corners = detect_and_draw(
                pipeline, align, board, dictionary, camera_matrix, dist_coeffs,
            )

            if not success:
                failed_count += 1
                print(f"   ❌ 检测失败 (连续 {failed_count})", flush=True)
                if failed_count >= 5:
                    print("   ⚠ 检查标定板位置/光照/清晰度")
                    failed_count = 0
                continue
            failed_count = 0

            # 读取机械臂末端位姿（使用 read_once 实时读取，示教模式也生效）
            state = robot.read_once()
            pos, ori = otee_to_pos_quat(state.O_T_EE)

            # 构建样本
            target_q = rotation_matrix_to_quaternion_xyzw(target_wrt_camera[:3, :3])
            sample = {
                "name": f"pose_{sample_idx+1:03d}",
                "gripper_wrt_base": {
                    "translation": [float(pos[0]), float(pos[1]), float(pos[2])],
                    "quaternion_xyzw": [float(ori[0]), float(ori[1]), float(ori[2]), float(ori[3])],
                },
                "target_wrt_camera": {
                    "translation": [
                        float(target_wrt_camera[0, 3]),
                        float(target_wrt_camera[1, 3]),
                        float(target_wrt_camera[2, 3]),
                    ],
                    "quaternion_xyzw": [float(q) for q in target_q],
                },
            }

            samples.append(sample)
            sample_idx += 1

            # 实时保存到 JSON
            payload = {
                "description": (
                    f"D435i-Panda hand-eye calibration samples. "
                    f"ChArUco: {SQUARES_X}x{SQUARES_Y}, {SQUARE_LENGTH*1000:.0f}mm squares, {DICT_NAME}. "
                    f"Units: meters. Quaternion order: xyzw."
                ),
                "samples": samples,
            }
            with open(args.samples, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)

            # ── 详细结果显示 ──
            print()
            print("   ╔" + "═" * 60 + "╗")
            print(f"   ║  ✅ #{sample_idx:03d}  采集成功 | ChArUco 角点: {n_corners}")
            print("   ╠" + "═" * 60 + "╣")
            print("   ║  📍 机械臂末端 (base→gripper):")
            print(f"   ║     位置:    x={pos[0]:+.4f}  y={pos[1]:+.4f}  z={pos[2]:+.4f}")
            print(f"   ║     四元数:  x={ori[0]:+.4f}  y={ori[1]:+.4f}  z={ori[2]:+.4f}  w={ori[3]:+.4f}")
            t = target_wrt_camera[:3, 3]
            print("   ║  🎯 标定板位姿 (camera→target):")
            print(f"   ║     位置:    x={t[0]:+.4f}  y={t[1]:+.4f}  z={t[2]:+.4f}")
            print(f"   ║     四元数:  x={target_q[0]:+.4f}  y={target_q[1]:+.4f}  z={target_q[2]:+.4f}  w={target_q[3]:+.4f}")
            print("   ╚" + "═" * 60 + "╝")

            # ── 采集结果显示在窗口上 ──
            if success:
                result_display = color_img.copy()
                cv2.putText(result_display, f"✅ #{sample_idx:03d}  SAVED", (15, 70),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                cv2.imshow(window_name, result_display)
                cv2.waitKey(800)

    except KeyboardInterrupt:
        print("\n\n⚠ 用户中断采集")
    finally:
        cv2.destroyAllWindows()

    print()
    print(f"采集完成: {len(samples)} 组有效样本, 保存至 {args.samples}")

    # ── 5. 求解标定 ──
    if len(samples) >= 3 and not args.skip_calibrate:
        print()
        print("[5/5] 运行手眼标定求解 ...")
        print()

        from handeye_calibrate import solve_handeye, load_samples, serialize_result, print_result, METHODS

        sample_names, base_gripper_list, camera_target_list = load_samples(args.samples)

        print(f"加载 {len(sample_names)} 组样本，正在求解...")
        print()

        results = []
        for method_name in METHODS.keys():
            transform, metrics = solve_handeye(
                base_gripper_list,
                camera_target_list,
                "eye_in_hand",
                method_name,
            )
            result = serialize_result(transform, metrics, "eye_in_hand", method_name)
            print_result(result)
            print()
            results.append(result)

        output_path = Path("calibration_result.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"标定结果已保存至 {output_path}")

        best = min(results, key=lambda r: r["consistency_metrics"]["translation_mean_m"])
        print()
        print("=" * 70)
        print("  🏆 推荐结果（一致性误差最小）:")
        print(f"     方法: {best['method']}")
        print(f"     T_gripper_camera = {best['result_name']}")
        print(f"     位移: {best['translation_xyz_m']}")
        print(f"     四元数: {best['quaternion_xyzw']}")
        print(f"     平移误差均值: {best['consistency_metrics']['translation_mean_m']*1000:.2f} mm")
        print(f"     旋转误差均值: {best['consistency_metrics']['rotation_mean_deg']:.2f} deg")
        print("=" * 70)

        best_t = best["translation_xyz_m"]
        best_q = best["quaternion_xyzw"]
        print()
        print("ROS TF 静态变换命令:")
        print(f"  rosrun tf static_transform_publisher "
              f"{best_t[0]} {best_t[1]} {best_t[2]} "
              f"{best_q[0]} {best_q[1]} {best_q[2]} {best_q[3]} "
              f"/panda_hand /camera_color_optical_frame 50")

    else:
        if args.skip_calibrate:
            print("已跳过标定求解")
        else:
            print(f"样本数不足 ({len(samples)} < 3)，无法标定")

    pipeline.stop()
    print()
    print("✅ 采集完成，资源已释放")


if __name__ == "__main__":
    main()
