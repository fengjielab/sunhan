#!/usr/bin/env python3
"""
VisionPhysicsMapper 摄像头实时演示
====================================
功能:
    1. 打开本地摄像头 (OpenCV)
    2. 实时 YOLO 检测物体
    3. 查表获取物理参数 (K_trans, F_target, label 等)
    4. 在【终端】打印检测结果 + 物理参数
    5. 在【图像窗口】叠加检测框和物理参数

用法:
    conda activate yolo
    cd /home/mfj/sunhan
    python biaoding/vision_physics_demo.py

按 'q' 退出。
"""

import os
import sys
import cv2
import time

# 引入 VisionPhysicsMapper
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vision_physics_mapper import VisionPhysicsMapper

# ── 配置 ──
MODEL_PATH = "yolo/ultralytics-8.3.163/yolo11n.pt"  # YOLO 模型路径
CAMERA_ID = 4                                         # 摄像头编号，0 为默认
CONF_THRESHOLD = 0.5
PHYSICS_JSON = os.path.join(os.path.dirname(__file__), "physics_table.json")


def main():
    print("=" * 60)
    print("VisionPhysicsMapper 实时摄像头演示")
    print("=" * 60)

    # 1. 初始化查表器（自带 YOLO 模型）
    print("\n[1/3] 加载 YOLO 模型与物理参数表...")
    mapper = VisionPhysicsMapper(
        model_path=MODEL_PATH,
        json_path=PHYSICS_JSON if os.path.exists(PHYSICS_JSON) else None,
        conf_threshold=CONF_THRESHOLD,
    )

    # 2. 打开摄像头
    print(f"[2/3] 打开摄像头 /dev/video{CAMERA_ID}...")
    cap = cv2.VideoCapture(CAMERA_ID)
    if not cap.isOpened():
        print(f"错误: 无法打开摄像头 /dev/video{CAMERA_ID}")
        print("提示: 尝试修改 CAMERA_ID = 2 或 4（你的系统有 video0~5）")
        sys.exit(1)

    # 设置分辨率（可选）
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    print("[3/3] 开始实时检测，按 'q' 退出\n")
    print("-" * 60)

    fps_time = time.time()
    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            print("摄像头读取失败，重试...")
            time.sleep(0.1)
            continue

        # ── YOLO 检测 + 查表 ──
        det = mapper.detect_and_map(frame)

        # ── 绘制与打印 ──
        if det is not None:
            cls_name = det["class"]
            conf = det["conf"]
            bbox = det["bbox"].astype(int)
            profile = det["profile"]

            x1, y1, x2, y2 = bbox

            # 根据 label 选颜色
            color_map = {
                "soft": (0, 255, 0),      # 绿
                "medium": (0, 255, 255),  # 黄
                "hard": (0, 0, 255),      # 红
                "unknown": (128, 128, 128),  # 灰
            }
            box_color = color_map.get(profile.label, (255, 255, 255))

            # 画框
            cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)

            # 标签文字
            label_text = f"{cls_name} | {profile.label} | conf={conf:.2f}"
            cv2.putText(frame, label_text, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, box_color, 2)

            # 物理参数文字（画在框下方）
            info_lines = [
                f"F_target={profile.F_target}N",
                f"K_trans={profile.K_trans}",
                f"K_grip={profile.K_grip}",
                f"speed={profile.approach_speed}m/s",
                f"deadband={profile.deadband}m",
                f"admittance_K={profile.admittance_K}",
            ]
            for i, line in enumerate(info_lines):
                y_pos = y2 + 20 + i * 20
                cv2.putText(frame, line, (x1, y_pos),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 1)

            # ── 终端输出 ──
            print(f"\n[检测到] {cls_name} (conf={conf:.2f})")
            print(f"  语义标签 : {profile.label}")
            print(f"  K_trans  : {profile.K_trans}")
            print(f"  K_grip   : {profile.K_grip}")
            print(f"  F_target : {profile.F_target} N")
            print(f"  deadband : {profile.deadband} m")
            print(f"  admittance_K : {profile.admittance_K}")
            print(f"  approach_speed : {profile.approach_speed} m/s")
            print(f"  → {profile.description}")
            print("-" * 40)

        # ── FPS 计算 ──
        frame_count += 1
        if time.time() - fps_time >= 1.0:
            fps = frame_count
            frame_count = 0
            fps_time = time.time()
        else:
            fps = None

        if fps:
            cv2.putText(frame, f"FPS: {fps}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # ── 显示图像 ──
        cv2.imshow("VisionPhysicsMapper Demo", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("\n用户按 'q' 退出")
            break

    # 清理
    cap.release()
    cv2.destroyAllWindows()
    print("演示结束")


if __name__ == "__main__":
    main()
