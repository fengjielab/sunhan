#!/usr/bin/env python3
"""
shared_control_node.py — 共享控制架构主节点
==============================================

整合三线信息流：
    🔵 蓝色（位置/运动流）: Omega.7 Δx → 位置映射 → 自适应导纳 → Franka Xd
    🔴 红色（力觉反馈流）: Franka τ_ext → 雅可比映射 → 增益调度 → Omega.7 F_feedback
    🟢 绿色（视觉语义流）: RealSense RGB → YOLOv11 → PhysicsProfile → K(c) + K_haptic(c)

依赖模块 (均在 plans/ 下):
    - force_estimator.py      : F_ext = pinv(J^T) · τ_ext
    - adaptive_admittance.py  : K(c) 运行时刚度调度
    - grip_force_estimator.py : f_grip = ||τ_wrist|| 夹持力近似
    - force_feedback_scheduler.py: F_haptic 渲染 + 死区
    - biaoding/vision_physics_mapper.py: YOLO + 查表 → PhysicsProfile

硬件:
    - Omega.7 (主端, 3DOF 力反馈手柄 + 夹钳)
    - Franka Panda (从端, 7-DOF 机械臂 + Franka Hand 夹爪)
    - RealSense D435i (视觉, RGB 30fps)

用法:
    python3 plans/shared_control_node.py [--mode a|b|c]

模式:
    a — 传统遥操作 (无视觉, 零力反馈, 固定刚度)
    b — 固定增益 (有视觉, 固定力反馈增益, 固定刚度)
    c — 本文方法 (有视觉, 自适应力反馈, 自适应刚度) ← 默认

作者: mfj
日期: 2026-05
"""

import os
import sys
import time
import threading
import ctypes
import argparse
import multiprocessing as mp
from typing import Optional
import numpy as np
import forcedimension_core.dhd as dhd
import forcedimension_core.drd as drd
import panda_py
from panda_py import controllers, libfranka

# ── 项目内部模块 ──
sys.path.insert(0, "/home/mfj/sunhan")
from plans.force_estimator import ForceEstimator
from plans.adaptive_admittance import AdaptiveAdmittance
from plans.grip_force_estimator import GripForceEstimator
from plans.force_feedback_scheduler import ForceFeedbackScheduler
from biaoding.vision_physics_mapper import VisionPhysicsMapper, PhysicsProfile

# ═══════════════════════════════════════════
# 配置参数
# ═══════════════════════════════════════════

# 检测保持（holdover）配置
DETECTION_HOLD_TIMEOUT = 5.0       # 检测丢失后保持参数的最大时间 (s)
FALLBACK_DETECTION_LABEL = "hold"  # 保持模式下的显示标签

# 机器人
ROBOT_IP = "192.168.1.51"

# Omega 映射
SCALE_POS = 3.0
SIGN = np.array([-1.0, -1.0, 1.0])

# 频率
POS_CTRL_FREQ = 200.0       # 位置控制 (Hz)
GRIPPER_UPDATE_FREQ = 10.0  # 夹爪控制 (Hz)
VISION_FREQ = 30.0           # 视觉检测 (Hz)
FORCE_PRINT_FREQ = 10.0      # 力反馈打印 (Hz)

# 夹爪
GRIPPER_SPEED = 0.1
GRIPPER_MAX = 0.08
GRIPPER_HYSTERESIS = 0.01

# Omega.7 夹钳意图阈值
OMEGA_ACTIVE_THRESHOLD = 0.7  # grip_norm < 0.7 → 用户开始操作（保持 profile）
OMEGA_GRASP_THRESHOLD = 0.3   # grip_norm < 0.3 → 用户正在抓取（锁定 profile）

# 视觉
YOLO_MODEL_PATH = "/home/mfj/sunhan/yolo/ultralytics-8.3.163/yolo11n.pt"
CONF_THRESHOLD = 0.25

# 默认阻抗
DEFAULT_IMPEDANCE = np.diag([200.0, 200.0, 200.0, 10.0, 10.0, 10.0])


# ═══════════════════════════════════════════
# YOLO 独立进程（拥有独立 GIL，不受控制循环争用）
# ═══════════════════════════════════════════

def _yolo_process_main(
    model_path: str,
    conf_threshold: float,
    frame_queue: mp.Queue,
    result_queue: mp.Queue,
):
    """
    独立进程入口：YOLO 推理（完全隔离 GIL 争用）

    主进程通过 frame_queue 发送 RGB 帧，YOLO 进程
    通过 result_queue 返回检测结果字典 {class, bbox, profile, conf}。

    以 daemon 方式运行，主进程退出时自动终止。
    """
    _sys = __import__("sys")
    _sys.path.insert(0, "/home/mfj/sunhan")

    import queue as _q
    import numpy as _np

    from biaoding.vision_physics_mapper import VisionPhysicsMapper

    pid = os.getpid()
    print(f"[YOLO进程-{pid}] 已启动", flush=True)

    mapper = VisionPhysicsMapper(
        model_path=model_path,
        conf_threshold=conf_threshold,
    )

    cycle = 0
    while True:
        try:
            rgb = frame_queue.get(timeout=0.5)
        except _q.Empty:
            if cycle == 0:
                print(f"[YOLO进程-{pid}] 等待帧入队...", flush=True)
            continue

        try:
            cycle += 1
            det = mapper.detect_and_map(rgb)

            if det is not None:
                # 转换为可 pickle 格式
                bbox = det["bbox"]
                det["bbox"] = tuple(map(int, bbox))
                result_queue.put(det)
                print(
                    f"[YOLO进程-{pid}] 🟢 #{cycle}: {det['class']} "
                    f"({det['profile'].label}) conf={det['conf']:.2f}",
                    flush=True,
                )
            else:
                # 打印所有检测到的物体（便于调试）
                _results = mapper._model(rgb, verbose=False)[0]
                if len(_results.boxes) > 0:
                    _all = [
                        f"{_results.names[int(b.cls[0])]}({float(b.conf[0]):.2f})"
                        for b in _results.boxes
                    ]
                    if cycle <= 5 or cycle % 20 == 0:
                        print(
                            f"[YOLO进程-{pid}] 推理 #{cycle}: "
                            f"检测到但未通过过滤: {', '.join(_all)}",
                            flush=True,
                        )
                elif cycle <= 5 or cycle % 20 == 0:
                    print(
                        f"[YOLO进程-{pid}] 推理 #{cycle}: 未检测到任何物体",
                        flush=True,
                    )
        except Exception as e:
            print(f"[YOLO进程-{pid}] ⚠️ 推理异常 #{cycle}: {e}", flush=True)
            import traceback
            traceback.print_exc()


class SharedControlNode:
    """
    共享控制主节点

    整合所有子模块，在三个线程中运行:
        - 主线程: 位置控制 (200Hz) + 力反馈 (200Hz)
        - 视觉线程: YOLO 检测 (30Hz)
        - 夹爪线程: 夹爪控制 (10Hz)
    """

    def __init__(self, mode: str = "c"):
        """
        Args:
            mode: 实验模式
                "a" — 传统遥操作 (无视觉, 零力反馈, 固定刚度)
                "b" — 固定增益 (有视觉, 固定力反馈, 固定刚度)
                "c" — 本文方法 (有视觉, 自适应增益, 自适应刚度)
        """
        self.mode = mode
        self.running = False
        self._enable_visualize = True  # 默认显示摄像头画面

        # ── 检测保持（holdover）状态 ──
        self._last_seen_class = "N/A"       # 最后检测到的物体类别
        self._last_seen_label = "unknown"   # 最后检测到的标签 soft/hard/medium
        self._last_seen_cycle = 0           # 最后检测成功时的 cycle 编号
        self._last_detection_time = 0.0     # 最后检测成功的时间戳
        self._is_holding = False            # 是否处于"保持模式"

        # ── Omega.7 夹钳意图状态（用户意图的唯一来源，不用 Franka 宽度）──
        # Omega 角度: -30°=张开, 0°=捏合
        # omega_grip_norm: 0=捏合, 1=张开
        #   张开 (>0.7) → 用户未操作 → 标准 5s 超时回退
        #   半捏合 (0.3~0.7) → 用户正在靠近 → 保持 profile，不回退
        #   全捏合 (<0.3) → 用户正在抓取 → 锁定 profile
        self._omega_grip_norm = 0.0
        self._user_active = False
        self._user_grasping = False
        self._grasp_profile: Optional[PhysicsProfile] = None
        self._grasp_profile_applied = False

        # ── 参数锁定（首次识别后保持到实验结束）──
        self._profile_locked = False       # 是否已锁定
        self._locked_profile: Optional[PhysicsProfile] = None  # 锁定的参数
        self._locked_class = "N/A"         # 锁定时的物体类别
        self._locked_label = "unknown"     # 锁定时的标签

        # ── 运行模式打印 ──
        mode_names = {
            "a": "传统遥操作",
            "b": "固定增益（视觉辅助）",
            "c": "本文方法（自适应视觉-导纳-力觉协同）",
        }
        print(f"\n{'='*60}")
        print(f"  模式 {mode}: {mode_names.get(mode, '未知')}")
        print(f"{'='*60}\n")

        # ── 视觉模块 ──
        # PhysicsProfile -> 包含 K_trans, K_grip, F_target, deadband,
        #                   admittance_K, approach_speed, label
        self.mapper: VisionPhysicsMapper = None
        self.current_profile: PhysicsProfile = None
        self._default_profile: PhysicsProfile = None   # 默认 profile（用于超时回退）
        self._profile_lock = threading.Lock()

        # ── 机器人状态 (由主线程更新，视觉线程读取) ──
        self.latest_detection: dict = None
        self.latest_detection_lock = threading.Lock()

        # ── 力反馈 ──
        self._F_ext_current = np.zeros(6)
        self._F_haptic_current = np.zeros(3)
        self._f_grip_current = 0.0

        # ── Omega.7 状态 ──
        self._omega_home = np.zeros(3)
        self._omega_grip = 0.0
        self._button_grasp = 0

    # ═══════════════════════════════════════════
    # 初始化
    # ═══════════════════════════════════════════

    def initialize(self):
        """初始化所有硬件和模块"""

        # 1. Omega.7
        print("[初始化] Omega.7 ...")
        if dhd.open() < 0:
            print("   ❌ Omega.7 连接失败")
            sys.exit(1)
        print(f"   ✓ {dhd.getSystemName()}")

        if drd.start() < 0:
            print("   ⚠️  DRD 启动失败（仅力反馈不可用）")
        dhd.enableForce(True)
        print("   ✓ DRD + 力输出已启动")

        # 2. Franka 机械臂
        print(f"[初始化] Franka Panda ({ROBOT_IP}) ...")
        self.panda = panda_py.Panda(ROBOT_IP)
        self.panda.recover()
        self.panda.set_default_behavior()
        print("   ✓ 机械臂已连接")

        # 3. Franka 夹爪
        print("[初始化] Franka Hand ...")
        self.gripper = libfranka.Gripper(ROBOT_IP)
        self.gripper.homing()
        print("   ✓ 夹爪已连接")

        # 4. 初始位姿
        init_pos = self.panda.get_position().copy()
        init_ori = self.panda.get_orientation().copy()
        print(f"   初始末端: {np.round(init_pos, 4)}")

        # 5. Omega.7 标定 — 位置零点 + 夹爪角度范围
        print("[初始化] 标定 Omega.7 零点（松开手柄）...")
        time.sleep(1.0)
        omega_home = np.zeros(3)
        for _ in range(100):
            pos = np.zeros(3)
            dhd.getPosition(pos)
            omega_home += pos
        omega_home /= 100.0
        self._omega_home = omega_home
        print(f"   Omega 零点: {np.round(omega_home, 4)}")

        # 6. CartesianImpedance 控制器
        print("[初始化] 启动笛卡尔阻抗控制器 ...")
        self.ctrl = controllers.CartesianImpedance(
            impedance=DEFAULT_IMPEDANCE,
            damping_ratio=1.0,
            nullspace_stiffness=0.5,
            filter_coeff=1.0,
        )
        self.panda.start_controller(self.ctrl)
        self.ctrl.set_control(init_pos, init_ori)
        self._virtual_ref = init_pos.copy()
        self._init_ori = init_ori.copy()
        print("   ✓ 控制器已启动")

        # 7. 视觉模块（YOLO 在独立进程中加载，避免 GIL 争用）
        if self.mode in ("b", "c"):
            self._enable_vision = True
            print("[初始化] 视觉模块（YOLO 将在独立进程中加载）...")
        else:
            self._enable_vision = False
            print("[初始化] 模式A: 跳过视觉模块")

        # 初始 profile（所有模式共用，避免后续 None 引用导致 AttributeError）
        self._default_profile = PhysicsProfile(
            K_trans=0.4, K_grip=0.3, F_target=10.0,
            deadband=0.3, admittance_K=100.0,
            approach_speed=0.03, label="unknown",
        )
        self.current_profile = PhysicsProfile.from_dict(
            self._default_profile.to_dict()
        )  # 深拷贝，避免与 _default_profile 共享同一对象
        print(f"   ✓ 初始 profile: {self.current_profile.label}")

        # 8. 子模块
        print("[初始化] 力估计/导纳/夹持力/力反馈 子模块 ...")

        # 根据模式选择模块创建
        self._init_submodules()

        print("\n✅ 所有模块初始化完成\n")

    def _init_submodules(self):
        """根据模式初始化子模块"""

        # 力估计器 (始终创建，用于监控)
        self.force_estimator = ForceEstimator(
            self.panda, use_builtin=True
        )

        # 自适应导纳 (仅模式c)
        if self.mode == "c":
            self.admittance = AdaptiveAdmittance(self.ctrl)
        else:
            self.admittance = None

        # 夹持力估计器
        self.grip_est = GripForceEstimator()

        # 力反馈调度器
        self.feedback_sched = ForceFeedbackScheduler()

        # 夹爪状态
        self._last_gripper_cmd = GRIPPER_MAX
        self._last_gripper_time = 0.0

        # ── 夹爪角度：运行时自适应归一化 ──
        # Omega.7 典型范围: -30°=完全张开, 0°=完全捏合
        # 归一化公式: grip_norm = (max - raw) / (max - min)
        #   raw=-30° → grip_norm=1.0 → 完全张开
        #   raw=0°   → grip_norm=0.0 → 完全捏合
        # 运行时只向外扩展（min 向下, max 向上）
        self._grip_min = -30.0   # 最小角度（完全张开）
        self._grip_max = 0.0     # 最大角度（完全捏合）

    # ═══════════════════════════════════════════
    # 视觉线程
    # ═══════════════════════════════════════════

    def _vision_loop(self):
        """视觉检测循环 — 双进程架构

        主进程 (本线程): 30fps 捕获 + 显示 (永不阻塞)
        ──────────────────────────────────────────────
        wait_for_frames → 入队 frame_queue → 读 result_queue → imshow → 循环

        YOLO 独立进程: 异步推理 (拥有独立 GIL)
        ──────────────────────────────────────
        读 frame_queue → detect_and_map → 入队 result_queue → 循环

        使用 multiprocessing.Queue 进行跨进程通信，YOLO 推理
        完全不受主线程 200Hz 控制循环的 GIL 争用影响。
        """
        import cv2
        import pyrealsense2 as rs
        import queue as _q

        # ── 配置 RealSense ──
        pipeline = rs.pipeline()
        config = rs.config()
        config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
        pipeline.start(config)
        align = rs.align(rs.stream.color)
        print("[视觉线程] RealSense D435i 已启动")

        if self._enable_visualize:
            cv2.namedWindow("Camera View", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("Camera View", 640, 480)
            # 启动OpenCV GUI线程（防止Qt后端报跨线程timer警告）
            cv2.startWindowThread()
            print("[视觉线程] 📷 相机画面已开启（按 'q' 关闭画面）")

        # ── 进程间通信 ──
        frame_queue = mp.Queue(maxsize=2)    # RGB 帧 → YOLO 进程
        result_queue = mp.Queue(maxsize=2)   # 检测结果 ← YOLO 进程

        # ── 启动 YOLO 独立进程 ──
        yolo_proc = mp.Process(
            target=_yolo_process_main,
            args=(YOLO_MODEL_PATH, CONF_THRESHOLD,
                  frame_queue, result_queue),
            daemon=True,
        )
        yolo_proc.start()
        print(f"[视觉线程] YOLO 独立进程已启动 (PID={yolo_proc.pid})")

        # ── 共享状态（仅在本线程使用，无需锁）──
        last_det = {"bbox": None, "active": False}
        _cycle = 0  # 视觉循环帧计数器（修复: 之前引用了未定义的 cycle 变量）

        # ── 主循环: 30fps 捕获 + 显示 ──
        while self.running:
            _cycle += 1
            try:
                frames = pipeline.wait_for_frames(timeout_ms=5000)
                aligned = align.process(frames)
                color_frame = aligned.get_color_frame()
                if not color_frame:
                    continue

                rgb = np.asanyarray(color_frame.get_data())

                # ── 送帧 → YOLO 进程 ──
                try:
                    frame_queue.put_nowait(rgb)
                except _q.Full:
                    pass  # YOLO 处理不过来时丢帧（不影响显示）

                # ── 收结果 ← YOLO 进程 ──
                try:
                    det = result_queue.get_nowait()
                    # 更新检测框（用于显示）
                    last_det["bbox"] = det["bbox"]
                    last_det["profile"] = det["profile"]
                    last_det["class"] = det["class"]
                    last_det["conf"] = det["conf"]
                    last_det["active"] = True

                    if not self._profile_locked:
                        # ── 首次识别 → 锁定参数 ──
                        self._profile_locked = True
                        self._locked_profile = PhysicsProfile.from_dict(
                            det["profile"].to_dict()
                        )
                        self._locked_class = det["class"]
                        self._locked_label = det["profile"].label
                        # 更新控制参数（线程安全锁）
                        with self._profile_lock:
                            self.current_profile = self._locked_profile
                        with self.latest_detection_lock:
                            self.latest_detection = det
                        if self.mode == "c":
                            self.admittance.apply_profile(self._locked_profile)
                        self.feedback_sched.set_profile(self._locked_profile)
                        print(
                            f"\n  🔒 参数已锁定 — 物体={det['class']} "
                            f"label={det['profile'].label} "
                            f"K_trans={det['profile'].K_trans:.2f} "
                            f"(直到实验结束)\n"
                        )
                    else:
                        # ── 已锁定 → 仅更新显示，不更新控制参数 ──
                        with self.latest_detection_lock:
                            self.latest_detection = det
                        # 调试：检测到不同物体时提示
                        if (det["class"] != self._locked_class
                                and _cycle % 30 == 0):
                            print(
                                f"[视觉] 检测到 {det['class']}，"
                                f"但参数已锁定为 {self._locked_class}"
                            )

                    # 更新检测保持状态（用于显示和状态打印）
                    self._last_seen_class = det["class"]
                    self._last_seen_label = det["profile"].label
                    self._last_seen_cycle = _cycle
                    self._last_detection_time = time.time()
                    self._is_holding = False
                except _q.Empty:
                    pass

                # ── 显示 (30fps, 永不阻塞) ──
                if self._enable_visualize:
                    display = rgb.copy()
                    if last_det["active"]:
                        x1, y1, x2, y2 = map(int, last_det["bbox"])
                        color_map = {
                            "soft": (0, 255, 0),
                            "medium": (0, 255, 255),
                            "hard": (0, 0, 255),
                        }
                        box_color = color_map.get(
                            last_det["profile"].label, (255, 255, 255)
                        )
                        cv2.rectangle(display, (x1, y1), (x2, y2), box_color, 2)
                        label = (
                            f"{last_det['class']} | {last_det['profile'].label} "
                            f"| {last_det['conf']:.2f}"
                        )
                        cv2.putText(display, label, (x1, y1 - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 2)
                    else:
                        cv2.putText(display, "No detection", (10, 30),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                                    (128, 128, 128), 2)
                    cv2.putText(display, f"Mode: {self.mode}", (10, 460),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                                (255, 255, 255), 1)
                    if self._profile_locked:
                        lock_text = f"\U0001f512 LOCKED: {self._locked_class}/{self._locked_label}"
                        cv2.putText(display, lock_text, (10, 475),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                                    (0, 255, 255), 2)
                    cv2.imshow("Camera View", display)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        print("[视觉线程] 用户关闭画面窗口")
                        self._enable_visualize = False
                        # 仅关闭显示，不调用destroyWindow（跨线程Qt会报错）
                        # 进程退出时OS自动清理

            except Exception as e:
                if self.running:
                    print(f"[视觉] ⚠️ 异常: {e}")

        pipeline.stop()
        # 不调用destroyAllWindows（跨线程Qt会报QObject::killTimer警告）
        # 进程退出时OS自动清理所有GUI资源
        print("[视觉线程] 已停止")

    # ═══════════════════════════════════════════
    # 主控制循环
    # ═══════════════════════════════════════════

    def run(self):
        """主控制循环

        单循环 (200Hz):
            1. 读 Omega.7 位置
            2. 读 Franka 状态 + 力估计
            3. 夹持力估计 + 接触事件
            4. 力反馈计算 + 渲染
            5. 自适应导纳更新 (模式c)
            6. 位置映射 + 发给 Franka
            7. 夹爪控制 (降频 10Hz)
        """
        self.running = True
        dt_pos = 1.0 / POS_CTRL_FREQ
        dt_gripper = 1.0 / GRIPPER_UPDATE_FREQ
        dt_force_print = 1.0 / FORCE_PRINT_FREQ

        # 启动视觉线程
        if self._enable_vision:
            vision_thread = threading.Thread(target=self._vision_loop, daemon=True)
            vision_thread.start()
            print("[主线程] 视觉线程已启动")

        loop_count = 0
        last_force_print = 0.0
        state = None

        print("\n" + "=" * 60)
        print("   🎮 共享控制已启动！")
        print(f"   模式: {'A-传统' if self.mode=='a' else 'B-固定增益' if self.mode=='b' else 'C-本文方法'}")
        print("   移动手柄 → 控制机械臂位置")
        print("   捏合/松开夹钳 → 夹爪抓取/松开")
        print("   灰色按钮 → 夹爪完全张开复位")
        print("   🔴 Ctrl+C 安全停止")
        print("=" * 60 + "\n")

        try:
            while True:
                t_start = time.perf_counter()
                now = time.time()  # 统一时间戳，供抓取检测/超时检测/夹爪控制共用

                # ── 1. 读 Omega.7 ──
                raw_pos = np.zeros(3)
                dhd.getPosition(raw_pos)

                # ── 2. 读 Franka 状态 + 外力估计 ──
                state = self.panda.get_state()
                tau_ext = np.array(state.tau_ext_hat_filtered, dtype=float)
                self._F_ext_current = self.force_estimator.update(state)

                # ── 3. 夹持力估计 + 接触事件检测 ──
                gripper_state = self.gripper.read_once()
                gw = gripper_state.width

                self._f_grip_current = self.grip_est.update(
                    tau_ext, gw, GRIPPER_MAX
                )

                # 接触事件: Omega.7 脉冲提示
                if self.grip_est.contact_detected:
                    self._render_contact_pulse()
                    self.grip_est.reset_contact()

                # ── 3a. Omega.7 夹钳状态 → 用户意图判定 ──
                # 计算 omega_grip_norm (0=完全捏合, 1=完全张开)
                # _omega_grip 在 _update_gripper() 中更新（10Hz），其他循环沿用旧值
                # 归一化公式与 _update_gripper() 一致
                _grip_range = max(self._grip_max - self._grip_min, 1.0)
                omega_grip_norm = (self._grip_max - self._omega_grip) / _grip_range
                self._omega_grip_norm = omega_grip_norm

                # 更新用户操作状态
                self._user_active = omega_grip_norm < OMEGA_ACTIVE_THRESHOLD  # 夹钳捏合>30%
                user_grasping = omega_grip_norm < OMEGA_GRASP_THRESHOLD       # 夹钳捏合>70%

                if user_grasping and not self._user_grasping:
                    # 用户从张开/半捏合 → 全捏合：锁定当前 profile
                    self._user_grasping = True
                    self._grasp_profile_applied = False
                    with self._profile_lock:
                        self._grasp_profile = PhysicsProfile.from_dict(
                            self.current_profile.to_dict()
                        )
                    print(
                        f"\n  🔒 用户抓取锁定 — Omega={self._omega_grip:.1f}° "
                        f"(norm={omega_grip_norm:.2f}) | "
                        f"label={self.current_profile.label}, "
                        f"K_trans={self.current_profile.K_trans:.2f}"
                    )

                elif not user_grasping and self._user_grasping:
                    # 用户从全捏合 → 松开：解除锁定
                    self._user_grasping = False
                    self._grasp_profile = None
                    self._grasp_profile_applied = False
                    print(
                        f"\n  🔓 用户抓取解除 — Omega={self._omega_grip:.1f}° "
                        f"(norm={omega_grip_norm:.2f})"
                    )

                # ── 4. 力反馈计算 + 渲染 ──
                if self.mode == "a":
                    # 模式A: 零力 (透明模式)
                    F_haptic = np.zeros(3)
                elif self.mode == "b":
                    # 模式B: 固定增益 K_trans=0.6
                    profile = PhysicsProfile(
                        K_trans=0.6, K_grip=0.5, F_target=15.0,
                        deadband=0.4, admittance_K=150.0,
                        approach_speed=0.03, label="medium",
                    )
                    F_haptic = self.feedback_sched.compute(
                        self._F_ext_current, profile
                    )
                else:  # mode "c"
                    with self._profile_lock:
                        profile = self.current_profile
                    if profile is not None:
                        F_haptic = self.feedback_sched.compute(
                            self._F_ext_current, profile
                        )
                    else:
                        F_haptic = np.zeros(3)

                self._F_haptic_current = F_haptic
                dhd.setForce(F_haptic)

                # ── 5. 位置映射 ──
                delta = raw_pos - self._omega_home
                target_pos = self._virtual_ref + delta * SCALE_POS * SIGN

                # ── 6. 发给 Franka ──
                self.ctrl.set_control(target_pos, self._init_ori)

                # ── 7. 夹爪控制 (降频) ──
                if (now - self._last_gripper_time) >= dt_gripper:
                    self._update_gripper()

                # ── 检测保持 + 用户意图驱动的 profile 管理 ──
                if self._enable_vision and self._last_detection_time > 0:

                    # 如果参数已锁定，跳过所有检测保持/超时回退逻辑
                    if self._profile_locked:
                        self._is_holding = True
                    else:
                        time_since_last_det = now - self._last_detection_time
                        omega_norm = self._omega_grip_norm  # 0=捏合, 1=张开

                        if self._user_grasping:
                            # ── 场景：Omega 全捏合 → 锁定 profile ──
                            # 用户正在抓取，无论检测结果如何，锁定开始抓取时的 profile
                            with self._profile_lock:
                                if (self._grasp_profile is not None
                                        and self.current_profile != self._grasp_profile):
                                    self.current_profile = self._grasp_profile
                            # 只在首次进入时同步更新子模块
                            if not self._grasp_profile_applied and self._grasp_profile is not None:
                                if self.mode == "c" and self.admittance is not None:
                                    self.admittance.apply_profile(self._grasp_profile)
                                self.feedback_sched.set_profile(self._grasp_profile)
                                self._grasp_profile_applied = True
                                print(f"  🔒 抓取 profile 已应用到子模块")
                            self._is_holding = True

                        elif self._user_active:
                            # ── 场景：Omega 半捏合 → 保持最后检测的 profile ──
                            # 用户正在靠近/对准物体，即使超时也保持 profile
                            # 当有新的检测结果时，视觉线程会更新 current_profile（正常运行）
                            # 当检测丢失时，保持最后的 profile
                            if time_since_last_det > DETECTION_HOLD_TIMEOUT:
                                # 保持当前 profile，不回退
                                self._is_holding = True
                            elif time_since_last_det > 1.0:
                                self._is_holding = True
                            else:
                                self._is_holding = False

                        else:
                            # ── 场景：Omega 完全张开 → 标准超时逻辑 ──
                            # 用户没有在操作，按标准 5 秒超时回退
                            if time_since_last_det > DETECTION_HOLD_TIMEOUT:
                                with self._profile_lock:
                                    if self.current_profile != self._default_profile:
                                        self.current_profile = self._default_profile
                                        print(
                                            f"\n  ⚠️  检测保持超时 ({time_since_last_det:.1f}s > "
                                            f"{DETECTION_HOLD_TIMEOUT}s)，回退到默认参数"
                                        )
                                        if self.mode == "c" and self.admittance is not None:
                                            self.admittance.apply_profile(self._default_profile)
                                        self.feedback_sched.set_profile(self._default_profile)
                                self._is_holding = False
                            elif time_since_last_det > 1.0:
                                self._is_holding = True
                            else:
                                self._is_holding = False

                # ── 力反馈统计打印 ──
                loop_count += 1
                if now - last_force_print >= dt_force_print:
                    self._print_status(loop_count)
                    last_force_print = now

                # ── 控制周期同步 ──
                elapsed = time.perf_counter() - t_start
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
            self._shutdown()

    # ═══════════════════════════════════════════
    # 辅助方法
    # ═══════════════════════════════════════════

    def _update_gripper(self):
        """夹爪控制逻辑 (10Hz) — daemon 线程中 stop+move 永不阻塞

        Omega.7 夹钳角度直接映射到 Franka 夹爪宽度。
        每次发命令前先 gripper.stop() 中止任何正在进行的运动，
        确保夹爪不会因为被物体卡住而阻塞后续命令。
        stop+move 在独立 daemon 线程中执行，不阻塞 200Hz 主循环。
        """
        gripper_angle = ctypes.c_double()
        dhd.getGripperAngleDeg(gripper_angle)
        raw = gripper_angle.value
        self._omega_grip = raw
        self._button_grasp = dhd.getButton(0)

        # ── Omega.7 夹爪归一化 ──
        if raw < self._grip_min:
            self._grip_min = raw
        if raw > self._grip_max:
            self._grip_max = raw

        grip_range = self._grip_max - self._grip_min
        if grip_range > 1.0:
            grip_norm = np.clip(
                (self._grip_max - raw) / grip_range, 0.0, 1.0
            )
        else:
            grip_norm = 0.0
        target_width = grip_norm * GRIPPER_MAX

        # 按钮 → 强制张开
        if self._button_grasp:
            target_width = GRIPPER_MAX

        # ── 在线程中执行 stop+move，不阻塞主循环 ──
        if abs(target_width - self._last_gripper_cmd) > GRIPPER_HYSTERESIS:
            threading.Thread(
                target=self._gripper_cmd_thread,
                args=(target_width,),
                daemon=True,
            ).start()
            self._last_gripper_cmd = target_width

        self._last_gripper_time = time.time()

    def _gripper_cmd_thread(self, width: float):
        """线程内：先 stop 中止旧命令 → move 发新命令"""
        try:
            # 中止任何正在进行的夹爪运动，释放夹爪 FSM
            try:
                self.gripper.stop()
            except Exception:
                pass  # 没有运动中的命令时 stop() 可能抛异常，忽略
            # 发送新命令
            self.gripper.move(width, GRIPPER_SPEED)
        except Exception as e:
            print(f"   ⚠️ 夹爪 cmd 异常 ({width:.3f}): {e}")

    def _render_contact_pulse(self):
        """接触事件: Omega.7 夹持通道脉冲提示"""
        # 施加一个短的力脉冲 (持续 ~0.1s, 在下一周期被覆盖)
        try:
            dhd.setForce(np.array([0.0, 0.0, -2.0]))  # Z 方向短脉冲
        except Exception:
            pass

    def _print_status(self, loop_count: int):
        """打印状态信息"""
        F = self._F_haptic_current
        F_ext = self._F_ext_current[:3]
        f_grip = self._f_grip_current

        # ── 用 Omega.7 意图状态决定显示内容 ──
        if self._enable_vision and self._last_detection_time > 0:
            if self._profile_locked:
                # 参数已锁定（首次识别后保持到实验结束）
                profile_class = f"🔒{self._locked_class}"
                profile_label = f"{self._locked_label}(locked)"
            elif self._user_grasping:
                # 全捏合锁定
                profile_class = f"🔒{self._last_seen_class}"
                profile_label = f"{self._last_seen_label}(lock)"
            elif self._user_active:
                # 半捏合保持
                profile_class = f"⏸{self._last_seen_class}"
                profile_label = self._last_seen_label
            elif self._is_holding:
                # 保持期内（<5s）
                profile_class = f" ⏸{self._last_seen_class}"
                profile_label = self._last_seen_label
            else:
                # 超时回退
                profile_class = "⚠️回退默认"
                profile_label = "default"
        else:
            # 无视觉或从未检测到
            profile_class = f" {self._last_seen_class}"
            profile_label = "unknown"

        print(f"[{loop_count:>6}] 意图={'抓取' if self._user_grasping else '靠近' if self._user_active else '空闲':>4} "
              f"Omega_norm={self._omega_grip_norm:.2f} "
              f"物体={profile_class:<14} label={profile_label:<14} "
              f"F_ext=({F_ext[0]:+.2f},{F_ext[1]:+.2f},{F_ext[2]:+.2f}) "
              f"F_fb=({F[0]:+.2f},{F[1]:+.2f},{F[2]:+.2f}) "
              f"grip={f_grip:.2f}")

    def _shutdown(self):
        """安全关闭"""
        self.running = False
        print("\n   关闭 Omega.7...")
        dhd.setForce(np.zeros(3))
        dhd.close()
        print("✅ 已安全停止")

    # ═══════════════════════════════════════════
    # 属性
    # ═══════════════════════════════════════════

    @property
    def F_ext(self) -> np.ndarray:
        return self._F_ext_current.copy()

    @property
    def F_haptic(self) -> np.ndarray:
        return self._F_haptic_current.copy()

    @property
    def f_grip(self) -> float:
        return self._f_grip_current


# ══════════════════════════════════════════════
# 入口
# ══════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="共享控制主节点")
    parser.add_argument(
        "--mode", "-m", type=str, default="c",
        choices=["a", "b", "c"],
        help="实验模式: a=传统, b=固定增益, c=本文方法 (默认)",
    )
    parser.add_argument(
        "--visualize", action="store_true",
        help="显示 YOLO 检测实时画面窗口（默认已开启，此选项保留向后兼容）",
    )
    args = parser.parse_args()

    node = SharedControlNode(mode=args.mode)
    # 摄像头画面默认开启（_enable_visualize 已在构造函数中设为 True）
    # 向后兼容：保留 --visualize 参数，但无需额外赋值
    node.initialize()
    node.run()


if __name__ == "__main__":
    main()
