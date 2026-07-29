#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
interactive_teleop.py — 交互式遥操作：实时调节阻尼/刚度/力反馈，感受手感变化
===============================================================================

核心功能:
    1. Omega.7 → Franka 笛卡尔阻抗遥操作 (200Hz)
    2. 运行时通过键盘实时调节 (default 模式):
       - 阻尼比 ζ (0.1~5.0)     → 改变"黏滞感"
       - 平移刚度 K_trans (10~1000 N/m) → 改变"软硬感"
       - 旋转刚度 K_rot (1~50 Nm/rad)
       - 力反馈增益 K_fb (0~2.0)   → Omega.7 力反馈强度
       - 力反馈死区 deadband (0~2.0 N)
       - 位置映射比例 scale (0.5~15.0)
    3. Vision 模式: YOLO 识别物体 → 自动映射软/中/硬物体手感
       - RealSense D435i 相机 + YOLO 子进程 (独立 GIL)
       - PhysicsProfile.label → PRESETS: soft→软物体, medium→中物体, hard→硬物体
       - 🔒 第一次检测到物体后参数即被锁定，不再跟随后续检测变化
       - Vision 模式下键盘手动参数调节被禁用
    4. Vision-Observe 模式: YOLO 视觉识别并显示检测结果，但不改变阻抗参数
       - RealSense D435i 相机 + YOLO 子进程 (独立 GIL)
       - 视觉识别结果仅在屏幕上显示，不自动映射手感参数
       -  键盘手动参数调节可用（与 default 模式相同）
    5. G 模式 / Force-Only 模式: 无视觉，仅接触力驱动在线变阻抗
       - Panda 外力估计 → K_trans/K_rot 有界在线缩放
       - 与 E/F 使用相同的阶段计时、数据记录和自动结束协议
    6. F 模式 / Vision-Force 模式: 视觉语义前馈 + 接触力反馈微调
       - 接触前: YOLO → soft/medium/hard → 多参数策略库
       - 接触后: Panda 外力估计 → 有界修正 K_trans/K_rot
       - 运行入口: --mode f 或 --mode vision_force
    7. 预设手感场景切换（一键切换多组参数）
    8. Omega.7 力反馈实时渲染（从端外力 → 主端力觉）
    9. Omega.7 夹钳 → Franka 夹爪控制

手感维度:
    ┌──────────────┬──────────────────────────────────────┐
    │ 调节参数      │ 手感影响                              │
    ├──────────────┼──────────────────────────────────────┤
    │ 阻尼比 ζ      │ 小=灵动顺滑  大=黏滞沉重               │
    │ 刚度 K        │ 小=柔软有弹性  大=坚硬刚性              │
    │ 力反馈增益    │ 小=力觉微弱  大=力觉强烈真实            │
    │ 死区          │ 小=细微力都能感知  大=忽略小扰动         │
    │ 位置映射比例  │ 小=精细操作  大=大范围快速移动           │
    └──────────────┴──────────────────────────────────────┘

操作方式 (default 模式):
    ┌──────────┬───────────────────────────────────────────┐
    │ 按键       │ 功能                                      │
    ├──────────┼───────────────────────────────────────────┤
    │ 1/2       │ 阻尼比 ζ -/+  (步长 0.1)                   │
    │ 3/4       │ 刚度 K -/+     (步长 10 N/m)               │
    │ 5/6       │ 力反馈增益 -/+  (步长 0.05)                 │
    │ 7/8       │ 死区 -/+       (步长 0.05 N)               │
    │ 9/0       │ 位置比例 -/+   (步长 0.5)                   │
    │ q/w       │ 旋转刚度 -/+   (步长 1 Nm/rad)             │
    │ a          │ 切换"灵动模式" ζ=0.3 K=50                │
    │ s          │ 切换"标准模式" ζ=1.0 K=150               │
    │ d          │ 切换"沉稳模式" ζ=2.0 K=300               │
    │ f          │ 切换"刚硬模式" ζ=3.0 K=500               │
    │ z          │ 切换"软物体手感" (低增益+低刚度)          │
    │ x          │ 切换"中物体手感" (中增益+中刚度)          │
    │ c          │ 切换"硬物体手感" (高增益+高刚度)          │
    │ v          │ 保存当前参数到文件                         │
    │ b          │ 从文件加载参数                             │
    │ h          │ 打印帮助菜单                              │
    │ Ctrl+C     │ 安全退出                                  │
    └──────────┴───────────────────────────────────────────┘

操作方式 (vision 模式):
    ┌──────────┬───────────────────────────────────────────┐
    │ YOLO自动 │ 识别物体 → 自动切换软/中/硬手感              │
    │ 按键       │ 功能                                      │
    ├──────────┼───────────────────────────────────────────┤
    │ h          │ 打印帮助菜单                              │
    │ v          │ 保存当前参数到文件                         │
    │ b          │ 从文件加载参数                             │
    │ q (画面)   │ 关闭摄像头预览窗口                         │
    │ Ctrl+C     │ 安全退出                                  │
    │ 其他按键   │ (vision模式下参数调节被禁用)               │
    └──────────┴───────────────────────────────────────────┘

用法:
    # default 模式 — 基础操作 + 轨迹自动录制
    python3 my_test/interactive_teleop.py

    # vision 模式 — YOLO 视觉自动映射物体手感
    python3 my_test/interactive_teleop.py --mode vision

    # G 模式 — 纯外力在线变阻抗（无视觉）
    python3 my_test/interactive_teleop.py --mode g

    # F 模式 — 视觉前馈 + 力反馈微调融合
    python3 my_test/interactive_teleop.py --mode f
    # 等价写法:
    python3 my_test/interactive_teleop.py --mode vision_force

    # 指定轨迹输出目录
    python3 my_test/interactive_teleop.py --trajectory-dir data/

    # 关闭轨迹录制以节省内存
    python3 my_test/interactive_teleop.py --no-trajectory

用法示例:
    终端1: python3 my_test/interactive_teleop.py --mode vision
    # 结束后用离线分析工具:
    python3 my_test/omega7_trajectory_analyzer.py --load data/trajectory_*.csv

作者: mfj
日期: 2026-06
"""

import sys
import time
import threading
import ctypes
import json
import os
import argparse
import multiprocessing as mp
from enum import Enum
from pathlib import Path
from typing import List, Optional
import numpy as np
import forcedimension_core.dhd as dhd
import forcedimension_core.drd as drd
import panda_py
from panda_py import controllers, libfranka

from experiment_protocol import ExperimentTimeline, PHASE_PREP

sys.path.insert(0, "/home/mfj/sunhan")
from plans.force_estimator import ForceEstimator

# ═══════════════════════════════════════════
# 默认配置
# ═══════════════════════════════════════════

ROBOT_IP = "192.168.1.51"

# 控制频率
CTRL_FREQ = 200.0          # 主控制循环 (Hz)
STATUS_FREQ = 1.0           # 状态打印 (Hz)：每秒一行，便于实验观察/回溯
KEYBOARD_FREQ = 30.0        # 键盘轮询 (Hz)

# 坐标轴方向
SIGN = np.array([-1.0, -1.0, 1.0])

# 默认阻抗
DEFAULT_K_TRANS = 200.0     # 平移刚度 (N/m)
DEFAULT_K_ROT = 10.0        # 旋转刚度 (Nm/rad)
DEFAULT_DAMPING_RATIO = 1.0 # 临界阻尼
DEFAULT_NULLSPACE = 0.5     # 零空间刚度

# 默认力反馈
DEFAULT_K_FB = 0.5          # 力反馈增益
DEFAULT_DEADBAND = 0.3      # 死区 (N)

# 默认位置映射
DEFAULT_SCALE = 3.0

# 夹爪
GRIPPER_SPEED = 0.05        # 实验统一夹爪运动速度 (m/s)
GRIPPER_FORCE = 20.0        # 夹爪夹持力 (N)
GRIPPER_MAX = 0.08          # 夹爪最大开度 (m)
GRIPPER_MIN_WIDTH = 0.0     # 夹爪最小开度 (m)
GRIPPER_HYSTERESIS = 0.003  # 夹爪命令死区 (m)
GRIPPER_EPS_INNER = 0.005   # grasp 内容差
GRIPPER_EPS_OUTER = GRIPPER_MAX  # 未知物体宽度：允许在全行程内判定抓取成功

# 夹钳角度自适应归一化初始值
GRIP_ANGLE_INIT_MIN = -30.0  # 完全张开 (度)
GRIP_ANGLE_INIT_MAX = 0.0   # 完全捏合 (度)

# 夹爪力反馈
FORCE_FB_GAIN = 0.3         # 力反馈增益 (N/比例)
FORCE_FB_MAX = 1.0          # 力反馈最大值 (N)
# 夹爪控制频率
GRIPPER_CTRL_FREQ = 30.0    # 夹爪主控制频率 (Hz)

# 阈值驱动参数 (状态机用)
GRASP_THRESHOLD = 0.20      # 归一化开度 < 此值 → 力控抓取 grasp()
MOVE_THRESHOLD = 0.80       # 归一化开度 > 此值 → 位置张开 move()
# 注意: 0.20 ~ 0.80 之间为过渡区，不发送命令

# stop 后等待夹爪状态切换的时间 (秒)
STOP_SETTLE_TIME = 0.1


# 轨迹记录
TRAJECTORY_DIR = "data"          # 轨迹 CSV 输出目录
TRAJECTORY_DECIMATION = 1        # 降采样: 1=每周期记录(200Hz), 5=每5周期记录(40Hz)
TRAJECTORY_CSV_HEADER = [
    "schema_version", "system_time", "operation_time", "phase", "event",
    "mode", "controller_mode", "subject_id", "object_id", "trial_id",
    "omega_x", "omega_y", "omega_z", "omega_valid", "gripper_deg", "button",
    "target_x", "target_y", "target_z", "robot_x", "robot_y", "robot_z",
    "F_ext_x", "F_ext_y", "F_ext_z", "T_ext_x", "T_ext_y", "T_ext_z", "F_ext_mag",
    "K_trans", "K_rot", "damping_ratio", "K_fb", "deadband", "scale",
    "gripper_state", "gripper_cmd_width", "gripper_width", "gripper_width_valid",
    "gripper_speed", "gripper_force", "grasp_success",
    "vision_class", "vision_label", "vision_confidence", "vision_locked",
    "fusion_delta_K", "fusion_active", "control_dt",
    "force_adapt_target_K", "force_adapt_ratio", "force_adapt_active",
    "force_adapt_delta_K",
    "force_baseline_mean", "force_baseline_std", "force_threshold",
]

# 平滑过渡步长
TRANSITION_STEPS = 30       # 刚度/阻尼过渡步数
TRANSITION_INTERVAL = 0.01  # 每步间隔 (s) → 约 300ms 完成过渡

# 参数范围限制
K_TRANS_MIN, K_TRANS_MAX = 10.0, 1000.0
K_ROT_MIN, K_ROT_MAX = 1.0, 50.0
DAMPING_MIN, DAMPING_MAX = 0.1, 5.0
K_FB_MIN, K_FB_MAX = 0.0, 2.0
DEADBAND_MIN, DEADBAND_MAX = 0.0, 2.0
SCALE_MIN, SCALE_MAX = 0.5, 15.0

# ═══════════════════════════════════════════
# GripperState 夹爪状态机
# ═══════════════════════════════════════════

class GripperState(Enum):
    """夹爪状态机状态"""
    IDLE = "IDLE"           # 空闲：跟随用户夹钳角度 (move)
    GRASPING = "GRASPING"   # 力控抓取中（grasp 阻塞执行）
    HOLDING = "HOLDING"     # 力保持状态：夹住物体
    RELEASING = "RELEASING" # 松开中（stop + move）


# ═══════════════════════════════════════════
# 预设手感场景
# ═══════════════════════════════════════════

# 注意：阻尼感通过 damping_ratio 体现，刚度感通过 K 体现，力觉通过 K_fb 体现
PRESETS = {
    # ── 基础模式 ──
    "light": {
        "name": "✨ 灵动模式",
        "desc": "低阻尼 + 低刚度 — 操作轻盈灵动，如在空中写字",
        "K_trans": 50.0, "K_rot": 5.0,
        "damping_ratio": 0.3, "K_fb": 0.2, "deadband": 0.2,
        "scale": 5.0,
    },
    "standard": {
        "name": "⚙️ 标准模式",
        "desc": "临界阻尼 + 适中刚度 — 平衡的日常操作手感",
        "K_trans": 150.0, "K_rot": 10.0,
        "damping_ratio": 1.0, "K_fb": 0.5, "deadband": 0.3,
        "scale": 3.0,
    },
    "stable": {
        "name": "🪨 沉稳模式",
        "desc": "高阻尼 + 高刚度 — 操作沉稳厚重，适合精密定位",
        "K_trans": 250.0, "K_rot": 13.0,
        "damping_ratio": 2.0, "K_fb": 0.8, "deadband": 0.4,
        "scale": 2.0,
    },
    "rigid": {
        "name": "🧱 刚硬模式",
        "desc": "超高阻尼 + 超高刚度 — 机械臂纹丝不动，刚性极强",
        "K_trans": 500.0, "K_rot": 20.0,
        "damping_ratio": 3.0, "K_fb": 1.0, "deadband": 0.5,
        "scale": 1.5,
    },
    # ── 模拟物体手感（用于测试力觉反馈） ──
    "soft_obj": {
        "name": "🫧 人工选择模式（实验 B）",
        "desc": "人工正确选择 soft 策略，与视觉 soft 前馈参数一致",
        "K_trans": 50.0, "K_rot": 5.0,
        "damping_ratio": 0.8, "K_fb": 0.2, "deadband": 0.3,
        "scale": 3.0, "gripper_speed": GRIPPER_SPEED, "gripper_force": 8.0,
    },
    "medium_obj": {
        "name": "📦 中物体手感",
        "desc": "人工正确选择 medium 策略，与视觉 medium 前馈参数一致",
        "K_trans": 120.0, "K_rot": 8.0,
        "damping_ratio": 1.0, "K_fb": 0.5, "deadband": 0.4,
        "scale": 3.0, "gripper_speed": GRIPPER_SPEED, "gripper_force": 15.0,
    },
    "hard_obj": {
        "name": "🪨 硬物体手感",
        "desc": "人工正确选择 hard 策略，与视觉 hard 前馈参数一致",
        "K_trans": 200.0, "K_rot": 13.0,
        "damping_ratio": 1.2, "K_fb": 0.7, "deadband": 0.5,
        "scale": 3.0, "gripper_speed": GRIPPER_SPEED, "gripper_force": 20.0,
    },
    # ── 六模式预实验专用参数 ──
    "experiment_fixed_a": {
        "name": "🇦 固定参数模式",
        "desc": "实验 A — 与旧108次原始数据一致的固定基线",
        "K_trans": 150.0, "K_rot": 10.0,
        "damping_ratio": 1.0, "K_fb": 0.5, "deadband": 0.3,
        "scale": 3.0,
    },
    "experiment_observe_d": {
        "name": "🇨 视觉显示模式",
        "desc": "实验 C — 视觉仅提示，与 A 使用相同固定参数",
        "K_trans": 150.0, "K_rot": 10.0,
        "damping_ratio": 1.0, "K_fb": 0.5, "deadband": 0.3,
        "scale": 3.0,
    },
    "vision_soft": {
        "name": "👁️ 视觉软物体",
        "desc": "实验 D/E/F 的 soft 视觉前馈基线",
        "K_trans": 50.0, "K_rot": 5.0,
        "damping_ratio": 0.8, "K_fb": 0.2, "deadband": 0.3,
        "scale": 3.0, "gripper_speed": GRIPPER_SPEED, "gripper_force": 8.0,
    },
    "vision_medium": {
        "name": "👁️ 视觉中等物体",
        "desc": "实验 D/E/F 的 medium 视觉前馈基线",
        "K_trans": 120.0, "K_rot": 8.0,
        "damping_ratio": 1.0, "K_fb": 0.5, "deadband": 0.4,
        "scale": 3.0, "gripper_speed": GRIPPER_SPEED, "gripper_force": 15.0,
    },
    "vision_hard": {
        "name": "👁️ 视觉硬物体",
        "desc": "实验 D/E/F 的 hard 视觉前馈基线",
        "K_trans": 200.0, "K_rot": 13.0,
        "damping_ratio": 1.2, "K_fb": 0.7, "deadband": 0.5,
        "scale": 3.0, "gripper_speed": GRIPPER_SPEED, "gripper_force": 20.0,
    },
}

# 在 InteractiveTeleop 类中通过 cls.SAVE_FILE 或 self.SAVE_FILE 访问
SAVE_FILE_PATH = os.path.expanduser("~/teleop_params.json")

# ═══════════════════════════════════════════
# Vision 模式配置
# ═══════════════════════════════════════════

YOLO_MODEL_PATH = "/home/mfj/sunhan/yolo/ultralytics-8.3.163/yolo11n.pt"
YOLO_CONF_THRESHOLD = 0.25
VISION_DETECTION_HOLD_TIMEOUT = 5.0  # 检测丢失后保持参数的最大时间 (s)
VISION_START_DELAY = 0.0             # 控制循环进入 run 后立即异步启动视觉
VISION_USB_RECOVERY_PAUSE = 1.5      # Omega 连续读取失败时，暂停 RealSense 的时长 (s)
OMEGA_READ_RETRY_DELAY = 0.001       # Omega 读取失败后的快速重试间隔 (s)
OMEGA_FAIL_WARN_INTERVAL = 2.0       # Omega 读取失败状态打印最小间隔 (s)
OMEGA_FAIL_RECOVERY_THRESHOLD = 120  # 连续失败多少次后触发相机暂停恢复

# Vision + Force 融合模式配置（实验模式 F）
FUSION_IMPD_UPDATE_INTERVAL = 0.05   # 力反馈微调阻抗更新频率: 20Hz
FUSION_CONTACT_DELAY_S = 0.20        # contact_onset 后延迟启动融合，避免接触前误触发

# Force-Only 在线变阻抗模式配置（实验模式 G）
# 保持 force_adaptive_teleop.py 的核心参数和公式，
# 但接入 interactive_teleop.py 的统一实验协议与数据记录。
G_K_BASE = 200.0
G_ALPHA = 0.5
G_F_SAT = 5.0
G_ADAPT_DEADBAND = 1.0
G_K_ROT_RATIO = 0.065
G_DAMPING_RATIO = 1.2
G_IMPD_SMOOTH_FACTOR = 0.3

# 视觉后验微调策略:
#   视觉前验由 PRESETS 给出 K_base(c)、K_rot(c)、K_fb(c)、deadband(c)。
#   接触后再按下表为不同类别使用不同的力阈值、饱和值、修正方向和刚度边界。
FUSION_POSTERIOR_POLICY = {
    "soft": {
        "gain": -0.25,          # 更大幅度降低刚度
        "force_deadband": 0.3,  # 更早进入微调，减轻接触冲击
        "force_sat": 2.5,       # 更低饱和阈值，提升视觉柔顺效果
        "smooth_factor": 0.40,
        "K_min": 30.0,          # 接触时允许降到更低刚度 (原来55)
        "K_max": 90.0,          # 自由空间保持vision_soft基线刚度，不影响跟踪
    },
    "medium": {
        "gain": -0.35,          # 中等物体接触后降到约85 N/m
        "force_deadband": 0.8,
        "force_sat": 6.0,
        "smooth_factor": 0.25,
        "K_min": 85.0,
        "K_max": 130.0,
    },
    "hard": {
        "gain": -0.15,          # 硬物体仅做轻度顺应修正
        "force_deadband": 1.2,
        "force_sat": 8.0,
        "smooth_factor": 0.20,
        "K_min": 140.0,
        "K_max": 170.0,
    },
    "unknown": {
        "gain": -0.10,
        "force_deadband": 1.0,
        "force_sat": 8.0,
        "smooth_factor": 0.25,
        "K_min": 60.0,
        "K_max": 135.0,
    },
}

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

        # 推理永远面向最新画面：丢弃模型加载/上一轮推理期间积压的旧帧。
        while True:
            try:
                rgb = frame_queue.get_nowait()
            except _q.Empty:
                break

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
                # detect_and_map 已经执行过一次模型推理；这里不能为了诊断
                # 再调用 mapper._model，否则无结果帧会耗费双倍推理时间。
                if cycle <= 5 or cycle % 20 == 0:
                    print(
                        f"[YOLO进程-{pid}] 推理 #{cycle}: 未得到有效映射目标",
                        flush=True,
                    )
        except Exception as e:
            print(f"[YOLO进程-{pid}] ⚠️ 推理异常 #{cycle}: {e}", flush=True)
            import traceback
            traceback.print_exc()


class InteractiveTeleop:
    """
    交互式遥操作控制器

    核心设计:
        - 主循环 200Hz: 读Omega → 阻抗控制 → 力反馈 → 发Franka
        - 键盘线程 30Hz: 异步轮询输入，不阻塞主循环
        - 平滑过渡: 参数变更时以 smoothstep 插值过渡 (~300ms)
        - Omega.7 力反馈: F_haptic = K_fb · (|F_ext| - deadband) · sign(F_ext)
    """

    # 类级常量（self.SAVE_FILE / cls.SAVE_FILE 均可访问）
    SAVE_FILE = SAVE_FILE_PATH

    def __init__(self, mode: str = "default", record_trajectory: bool = True,
                 trajectory_dir: str = "data", subject_id: str = "unknown",
                 object_id: str = "unknown", trial_id: str = "unknown",
                 auto_stop: bool = True):
        # ── 运行模式 ──
        self.mode = mode  # "default" | "force_only" | "vision" | PRESETS key
        self._experiment_condition = {
            "default": "A", "experiment_fixed_a": "A",
            "soft_obj": "B", "medium_obj": "B", "hard_obj": "B",
            "vision_observe": "C", "vision_stiffness": "D",
            "vision": "E", "vision_force": "F",
            "force_only": "G",
        }.get(mode, mode)

        # ── 运行状态 ──
        self.running = False
        self._loop_count = 0
        self._trajectory_record = record_trajectory
        self._trajectory_dir = trajectory_dir
        self._trajectory: List[dict] = []
        self._auto_stop = auto_stop
        self._completion_announced = False
        # 正式实验模式一旦启动即锁定参数，避免按键误触破坏组间控制变量。
        # default/light/standard/stable/rigid 仍保留交互调参能力，供设备调试。
        self._experiment_parameters_locked = mode in (
            "experiment_fixed_a", "soft_obj", "medium_obj", "hard_obj",
            "vision_observe", "vision_stiffness", "vision", "vision_force",
            "force_only",
        )

        # ── Vision 模式状态 ──
        self._vision_enabled = (mode in ("vision", "vision_observe", "vision_stiffness", "vision_force"))
        self._vision_auto_map = (mode in ("vision", "vision_stiffness", "vision_force"))
        self._vision_stiffness_only = (mode == "vision_stiffness")
        self._vision_force_fusion = (mode == "vision_force")
        self._force_only_adaptive = (mode == "force_only")
        self._init_preset = mode if mode in PRESETS else None  # 命令行指定的初始预设
        self._vision_lock = threading.Lock()
        self._vision_detection = None       # 最新 YOLO 检测结果 dict
        self._vision_profile = None         # 最新 PhysicsProfile
        self._vision_last_time = 0.0        # 最后检测成功时间戳
        self._vision_current_preset = "standard"  # 当前应用的 PRESET key
        self._vision_locked = False         # 参数是否已锁定（第一次检测后固定不变）
        self._vision_locked_label = "unknown"  # 融合模式中力反馈微调的语义类别
        self._vision_base_K_trans = DEFAULT_K_TRANS
        self._vision_base_K_rot = DEFAULT_K_ROT
        self._vision_base_damping = DEFAULT_DAMPING_RATIO
        self._fusion_last_update = 0.0
        self._fusion_delta_K = 0.0
        self._fusion_active = False

        # ── G 模式：纯外力在线变阻抗状态 ──
        self._force_adapt_last_update = 0.0
        self._force_adapt_base_K = G_K_BASE
        self._force_adapt_alpha = G_ALPHA
        self._force_adapt_F_sat = G_F_SAT
        self._force_adapt_deadband = G_ADAPT_DEADBAND
        self._force_adapt_target_K = G_K_BASE
        self._force_adapt_ratio = 0.0
        self._force_adapt_active = False
        self._force_adapt_delta_K = 0.0
        self._vision_active = False         # 视觉线程是否已启动
        self._vision_thread = None
        self._vision_yolo_proc = None       # YOLO 子进程句柄
        self._vision_enable_display = True  # 是否显示 RealSense 摄像头预览窗口
        self._vision_pause_until = 0.0       # USB 恢复时临时暂停 RealSense
        self._vision_restarts = 0            # RealSense pipeline 重启次数
        self._vision_confidence = float("nan")
        self._vision_class = "unknown"
        self._first_frame_marked = False
        # 直接在视觉线程内调用 cv2.imshow (而非独立显示进程)，参考 shared_control_node.py
        # 使用 cv2.startWindowThread() 确保 OpenCV GUI 线程安全

        # ── Omega.7 主端轨迹长度跟踪 ──
        self._omega_traj_length = 0.0          # 累计轨迹长度 (m)
        self._omega_prev_pos = np.zeros(3)     # 上一帧 Omega.7 位置

        # ── Omega.7 位置缓存（USB 带宽争用保护） ──
        #   RealSense 运行时可能干扰 Omega.7 的 USB 等时传输，导致 dhd.getPosition() 返回 -1。
        #   缓存最后有效位置，读取失败时复用缓存值，避免机械臂跳回原点或剧烈抖动。
        self._omega_pos_last_valid = np.zeros(3)   # 最后成功读取的 Omega 位置
        self._omega_grip_last_valid = 0.0           # 最后成功读取的夹钳角度
        self._omega_read_fail_count = 0             # 连续位置读取失败次数
        self._omega_read_fail_total = 0             # 累计位置读取失败次数
        self._omega_last_fail_warn = 0.0            # 上次失败提示时间
        self._omega_usb_recovery_requested = False  # 是否已请求视觉线程让出 USB

        # ── 当前参数（含过渡目标） ──
        self._K_trans_cur = DEFAULT_K_TRANS
        self._K_rot_cur = DEFAULT_K_ROT
        self._damping_ratio_cur = DEFAULT_DAMPING_RATIO
        self._K_fb_cur = DEFAULT_K_FB
        self._deadband_cur = DEFAULT_DEADBAND
        self._scale_cur = DEFAULT_SCALE
        self._nullspace_cur = DEFAULT_NULLSPACE

        # G 模式沿用 force_adaptive_teleop.py 的接触前基线和阻尼参数。
        if self._force_only_adaptive:
            self._K_trans_cur = self._force_adapt_base_K
            self._K_rot_cur = self._force_adapt_base_K * G_K_ROT_RATIO
            self._damping_ratio_cur = G_DAMPING_RATIO

        # ── 过渡状态 ──
        self._transition_active = False
        self._transition_stop = threading.Event()

        # ── Omega.7 状态 ──
        self._omega_home = np.zeros(3)
        self._omega_grip = 0.0
        self._button_now = 0
        self._button_prev = 0

        # ── 夹爪 ──
        # 跟踪已执行命令的最新宽度
        self._last_cmd_width = GRIPPER_MAX
        self._cmd_busy = False
        self._grip_min = GRIP_ANGLE_INIT_MIN
        self._grip_max = GRIP_ANGLE_INIT_MAX
        self._max_width = GRIPPER_MAX
        self._calibration_samples = 0   # 自适应学习样本数
        self._cmd_count = 0             # 夹爪命令计数
        self._pending_width: Optional[float] = None  # 追赶模式：待执行的目标宽度
        self._gripper_state = GripperState.IDLE      # 当前状态机状态
        self._grasp_armed = True                     # 必须先张开，才允许下一次抓取
        self._btn0_prev = 0  # 灰色按钮 (上一帧)
        self._gripper_force_feedback = 0.0  # 夹爪力反馈值
        self._gripper_speed_cur = GRIPPER_SPEED
        self._gripper_force_cur = GRIPPER_FORCE
        self._gripper_width_actual = float("nan")
        self._gripper_width_valid = False
        self._grasp_success = False

        # ── Franka 状态 ──
        self._init_pos = np.zeros(3)
        self._init_ori = np.zeros(4)
        self._virtual_ref = np.zeros(3)
        self._F_ext_current = np.zeros(6)
        self._robot_pos_current = np.full(3, np.nan)
        self._target_pos_current = np.full(3, np.nan)
        self._omega_read_valid = True
        self._control_dt = float("nan")

        # ── 自动实验计时 / 阶段 ──
        self._timeline = ExperimentTimeline(
            mode=self._experiment_condition, subject_id=subject_id,
            object_id=object_id, trial_id=trial_id,
        )

        # ── 硬件句柄 ──
        self.panda = None
        self.gripper = None
        self.ctrl = None
        self.force_estimator = None

        # ── 键盘输入 ──
        self._key_pressed = ""
        self._key_lock = threading.Lock()
        self._last_key_time = 0.0
        self._key_repeat_delay = 0.3    # 首次重复延迟 (s)
        self._key_repeat_rate = 0.12    # 后续重复间隔 (s)
        self._key_held = False
        self._key_first_repeat = True

        # ── 帮助菜单是否显示 ──
        self._show_help = True

    # ═══════════════════════════════════════════
    # 初始化
    # ═══════════════════════════════════════════

    def initialize(self):
        """初始化所有硬件"""
        print("=" * 65)
        print("  🚀 交互式遥操作 — 实时调节手感参数")
        print("=" * 65)

        # ── Omega.7 ──
        print("[1] 连接 Omega.7 ...")
        ret = dhd.open()
        if ret < 0:
            print(f"    ❌ Omega.7 连接失败: {dhd.errorGetLastStr()}")
            sys.exit(1)
        print(f"    ✅ {dhd.getSystemType()} | SN: {dhd.getSerialNumber()}")

        # 记录起始位置作为 home
        self._omega_home = np.zeros(3)
        if dhd.getPosition(self._omega_home) < 0:
            print("    ⚠️  首次 Omega.7 位置读取失败，重试...")
            time.sleep(0.1)
            dhd.getPosition(self._omega_home)
        print(f"    Omega.7 home: ({self._omega_home[0]:.3f}, {self._omega_home[1]:.3f}, {self._omega_home[2]:.3f}) m")

        # 初始化位置缓存（USB 带宽争用时 fallback 使用）
        self._omega_pos_last_valid = self._omega_home.copy()

        # 初始化轨迹长度跟踪的上一帧位置
        self._omega_prev_pos = self._omega_home.copy()
        self._omega_traj_length = 0.0

        # 启动 DRD (Device Real-time Driver) — 高优先级 USB 通道
        # 确保 Omega.7 的 USB 等时传输不被 RealSense 等其他 USB 设备抢占
        if drd.start() < 0:
            print("    ⚠️  DRD 启动失败（仅力反馈不可用）")
        else:
            print("    ✅ DRD 已启动（实时 USB 通道保护）")
        dhd.enableForce(True)
        print("    ✅ 力反馈已启用")

        # ── Franka ──
        print(f"[2] 连接 Franka ({ROBOT_IP}) ...")
        self.panda = panda_py.Panda(ROBOT_IP)
        self.panda.recover()
        self.panda.set_default_behavior()

        # ── 碰撞阈值 ──
        print("[2.5] 设置碰撞阈值...")
        _robot = self.panda.get_robot()
        _robot.set_collision_behavior(
            [30.0]*7, [30.0]*7,   # 加速/减速时关节扭矩阈值
            [20.0]*7, [20.0]*7,   # 正常运行时关节扭矩阈值
            [35.0]*6, [35.0]*6,   # 加速/减速时笛卡尔力阈值
            [25.0]*6, [25.0]*6,   # 正常运行时笛卡尔力阈值
        )
        print("    ✅ 碰撞阈值已设置 (关节 20Nm / 笛卡尔 25N)")

        # ⚡ 遥操作场景下不调用 move_to_start()。
        # move_to_start() 是 panda_py/libfranka 的关节位置运动方法，
        # 会将机械臂移动到出厂 home 位置，这在遥操作中会导致:
        #   1. 控制器启动前机械臂位置被改变，造成不期望的运动
        #   2. 后续 _init_pos / _virtual_ref 基于 home 而非当前姿态
        #   3. Omega 映射与机械臂实际状态不匹配
        # 直接使用当前状态启动控制器，实现无缝接管。
        print("    ✅ 保持当前位置，控制器将从此处无缝接管")

        # ── 夹爪 ──
        print("[3] 初始化 Franka Hand 夹爪 ...")
        self.gripper = libfranka.Gripper(ROBOT_IP)
        try:
            self.gripper.homing()
            print("    ✅ Homing 完成")
        except Exception as e:
            print(f"    ⚠️  Homing 失败: {e}")
        self.gripper.move(GRIPPER_MAX, self._gripper_speed_cur)
        self._last_cmd_width = GRIPPER_MAX
        self._gripper_width_actual = float("nan")
        self._gripper_width_valid = False
        print(f"    ✅ 夹爪已打开 ({GRIPPER_MAX*1000:.0f} mm)")

        # ── 状态读取 ──
        state = self.panda.get_state()
        # O_T_EE 是 16 元素列主序 4×4: [R00,R10,R20,0, R01,R11,R21,0, R02,R12,R22,0, x,y,z,1]
        # 位置: index 12, 13, 14; 旋转矩阵各列: 0-2, 4-6, 8-10
        self._init_pos = np.array([state.O_T_EE[12], state.O_T_EE[13], state.O_T_EE[14]], dtype=float)
        # 用 panda.get_orientation() 直接获取四元数，避免手动矩阵→四元数转换
        self._init_ori = np.array(self.panda.get_orientation(), dtype=float)
        self._virtual_ref = self._init_pos.copy()

        # ── 外力估计 ──
        self.force_estimator = ForceEstimator(panda=self.panda)

        # ── 阻抗控制器 ──
        print("[4] 启动 CartesianImpedance 控制器 ...")
        K_init = self._build_stiffness(self._K_trans_cur, self._K_rot_cur)

        self.ctrl = controllers.CartesianImpedance(
            impedance=K_init,
            damping_ratio=self._damping_ratio_cur,
            nullspace_stiffness=self._nullspace_cur,
        )
        self.panda.start_controller(self.ctrl)
        self.ctrl.set_control(self._init_pos, self._init_ori)
        print("    ✅ 控制器已启动")

        print("=" * 65)
        print("  初始化完成 — 开始遥操作 🎮")
        print("=" * 65)

        # ⚡ Vision 线程不在 initialize() 中启动，而是在 run() 中启动
        #   让 200Hz 控制循环先稳定运行，避免 YOLO fork + PyTorch 模型加载
        #   造成的 CPU 峰值触发 Franka communication_constraints_violation
        #   参考 shared_control_node.py line 605-608

    def _build_stiffness(self, K_trans: float, K_rot: float) -> np.ndarray:
        """构造 6x6 对角线刚度矩阵"""
        K = np.zeros((6, 6))
        K[0, 0] = K[1, 1] = K[2, 2] = K_trans
        K[3, 3] = K[4, 4] = K[5, 5] = K_rot
        return K

    def _build_damping(self, K: np.ndarray, zeta: float) -> np.ndarray:
        """从刚度矩阵和阻尼比构造阻尼矩阵 (对角, D=2*ζ*sqrt(M*K))"""
        # 假设质量矩阵 M 近似为单位矩阵
        # 则 D_i = 2 * ζ * sqrt(K_i)
        D = np.zeros((6, 6))
        for i in range(6):
            D[i, i] = 2.0 * zeta * np.sqrt(K[i, i] + 1e-6)
        return D

    def _compute_damping_from_params(self) -> np.ndarray:
        """根据当前刚度与阻尼比计算阻尼矩阵"""
        K = self._build_stiffness(self._K_trans_cur, self._K_rot_cur)
        return self._build_damping(K, self._damping_ratio_cur)

    # ═══════════════════════════════════════════
    # 平滑参数过渡
    # ═══════════════════════════════════════════

    def _smooth_transition(self, target_K_trans: float, target_K_rot: float,
                            target_zeta: float, duration: float = None):
        """后台线程：将当前参数平滑过渡到目标值（smoothstep 插值）"""

        if duration is None:
            duration = TRANSITION_STEPS * TRANSITION_INTERVAL

        def _worker():
            try:
                steps = max(5, int(duration / (TRANSITION_INTERVAL + 1e-6)))
                K_start = np.array([self._K_trans_cur, self._K_rot_cur])
                zeta_start = self._damping_ratio_cur
                K_target = np.array([target_K_trans, target_K_rot])
                zeta_target = target_zeta

                self._transition_active = True
                self._transition_stop.clear()

                for i in range(steps):
                    if self._transition_stop.is_set():
                        break
                    t = i / max(steps - 1, 1)
                    # smoothstep: 3t^2 - 2t^3
                    s = t * t * (3.0 - 2.0 * t)

                    K_mid = K_start + s * (K_target - K_start)
                    zeta_mid = zeta_start + s * (zeta_target - zeta_start)

                    self._K_trans_cur = K_mid[0]
                    self._K_rot_cur = K_mid[1]
                    self._damping_ratio_cur = zeta_mid

                    K_6x6 = self._build_stiffness(self._K_trans_cur, self._K_rot_cur)
                    self.ctrl.set_impedance(K_6x6)
                    self.ctrl.set_damping_ratio(self._damping_ratio_cur)

                    try:
                        time.sleep(TRANSITION_INTERVAL)
                    except KeyboardInterrupt:
                        break

                # 确保最终值精确
                self._K_trans_cur = target_K_trans
                self._K_rot_cur = target_K_rot
                self._damping_ratio_cur = target_zeta
                K_6x6 = self._build_stiffness(self._K_trans_cur, self._K_rot_cur)
                self.ctrl.set_impedance(K_6x6)
                self.ctrl.set_damping_ratio(self._damping_ratio_cur)
            except Exception as e:
                import traceback
                import traceback
                print(f"\n[❌ 过渡线程异常] {e}")
                traceback.print_exc()
            finally:
                self._transition_active = False

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    # ═══════════════════════════════════════════
    # 键盘控制
    # ═══════════════════════════════════════════

    def _change_param(self, name: str, delta: float) -> bool:
        """通用参数增减，带范围限制。返回 True 表示参数有变化。"""
        """通用参数增减，带范围限制"""
        limits = {
            "damping_ratio": (DAMPING_MIN, DAMPING_MAX),
            "K_trans": (K_TRANS_MIN, K_TRANS_MAX),
            "K_rot": (K_ROT_MIN, K_ROT_MAX),
            "K_fb": (K_FB_MIN, K_FB_MAX),
            "deadband": (DEADBAND_MIN, DEADBAND_MAX),
            "scale": (SCALE_MIN, SCALE_MAX),
        }
        lower, upper = limits.get(name, (0, 1e6))
        current = getattr(self, f"_{name}_cur", 0.0)
        before = current
        current = max(lower, min(upper, current + delta))
        setattr(self, f"_{name}_cur", current)

        changed = abs(current - before) > 1e-9

        if changed:
            if name in ("damping_ratio",) and self.ctrl is not None:
                self.ctrl.set_damping_ratio(self._damping_ratio_cur)

            if name in ("K_trans", "K_rot") and self.ctrl is not None:
                K = self._build_stiffness(self._K_trans_cur, self._K_rot_cur)
                self.ctrl.set_impedance(K)

            self._print_param_change(name, before, current)

        return changed

    def _set_preset(self, preset_name: str):
        """切换到预设手感场景"""
        if preset_name not in PRESETS:
            return
        p = PRESETS[preset_name]
        print(f"\n  🎯 切换 → {p['name']}")
        print(f"     {p['desc']}")
        self._smooth_transition(p["K_trans"], p["K_rot"], p["damping_ratio"])
        self._K_fb_cur = p["K_fb"]
        self._deadband_cur = p["deadband"]
        self._scale_cur = p["scale"]
        self._gripper_speed_cur = p.get("gripper_speed", GRIPPER_SPEED)
        self._gripper_force_cur = p.get("gripper_force", GRIPPER_FORCE)

    # ═══════════════════════════════════════════
    # Vision 模式 — profile → PRESETS 映射
    # ═══════════════════════════════════════════

    def _profile_to_preset(self, profile) -> str:
        """将 PhysicsProfile.label 映射到 PRESETS 字典的 key"""
        mapping = {
            "soft": "vision_soft",
            "medium": "vision_medium",
            "hard": "vision_hard",
            "unknown": "vision_medium",  # 默认回退到中物体
        }
        return mapping.get(profile.label, "vision_medium")

    def _start_vision_thread(self):
        """启动视觉线程。由主控制循环延迟调用，避免启动阶段抢占 USB/CPU。"""
        if not self._vision_enabled or self._vision_active:
            return
        self._timeline.mark("vision_start")
        self._vision_active = True
        self._vision_thread = threading.Thread(
            target=self._vision_loop, daemon=True, name="VisionThread"
        )
        self._vision_thread.start()
        print("    ✅ 视觉线程已启动（控制循环已稳定）")

    def _read_omega_position(self) -> np.ndarray:
        """读取 Omega.7 位置；失败时快速重试并最终复用最后有效值。"""
        raw_pos = np.zeros(3)
        pos_ret = dhd.getPosition(raw_pos)
        if pos_ret < 0:
            time.sleep(OMEGA_READ_RETRY_DELAY)
            pos_ret = dhd.getPosition(raw_pos)

        if pos_ret < 0:
            self._omega_read_fail_count += 1
            self._omega_read_fail_total += 1
            self._handle_omega_read_failure()
            self._omega_read_valid = False
            return self._omega_pos_last_valid.copy()

        if self._omega_read_fail_count > 0:
            print(
                f"\n  ✅ Omega.7 位置读取恢复 "
                f"(连续失败 {self._omega_read_fail_count} 次, "
                f"累计 {self._omega_read_fail_total} 次)"
            )
        self._omega_read_fail_count = 0
        self._omega_read_valid = True
        self._omega_usb_recovery_requested = False
        self._omega_pos_last_valid = raw_pos.copy()
        return raw_pos

    def _handle_omega_read_failure(self):
        """Omega 读取失败时给出可见提示，并在 vision 模式下短暂停相机恢复 USB。"""
        now = time.time()
        if now - self._omega_last_fail_warn >= OMEGA_FAIL_WARN_INTERVAL:
            print(
                f"\n  ⚠️  Omega.7 位置读取失败 "
                f"(连续 {self._omega_read_fail_count}, 累计 {self._omega_read_fail_total})，"
                "暂用最后有效位置"
            )
            self._omega_last_fail_warn = now

        if (self._vision_enabled and self._vision_active
                and self._omega_read_fail_count >= OMEGA_FAIL_RECOVERY_THRESHOLD
                and not self._omega_usb_recovery_requested):
            self._omega_usb_recovery_requested = True
            self._vision_pause_until = now + VISION_USB_RECOVERY_PAUSE
            print(
                f"\n  🔧 Omega.7 连续读取失败，暂停 RealSense "
                f"{VISION_USB_RECOVERY_PAUSE:.1f}s 释放 USB 带宽"
            )

    def _update_vision_force_fusion(self, now: float):
        """视觉前馈 + 力反馈微调。

        视觉首次识别提供 K_base(c)，接触外力按类别后验策略提供有界修正项 ΔK_f(t)：
            K_t(t) = clip(K_base(c) + gain(c) * K_base(c) * s(F), K_min, K_max)
        其中 s(F) 为 [0, 1] 的接触力归一化强度。
        """
        if not self._vision_force_fusion or not self._vision_locked:
            return
        if self._transition_active:
            self._fusion_active = False
            return
        contact_t = self._timeline.event_times.get("contact_onset")
        if contact_t is None:
            self._fusion_active = False
            return
        if self._timeline.system_time(now) - contact_t < FUSION_CONTACT_DELAY_S:
            self._fusion_active = False
            return
        if now - self._fusion_last_update < FUSION_IMPD_UPDATE_INTERVAL:
            return
        self._fusion_last_update = now

        label = self._vision_locked_label
        policy = FUSION_POSTERIOR_POLICY.get(label, FUSION_POSTERIOR_POLICY["unknown"])
        force_deadband = policy["force_deadband"]
        force_sat = policy["force_sat"]

        F_mag = float(np.linalg.norm(self._F_ext_current[:3]))
        if F_mag <= force_deadband:
            force_ratio = 0.0
        else:
            force_ratio = min(
                (F_mag - force_deadband)
                / max(force_sat - force_deadband, 1e-6),
                1.0,
            )

        gain = policy["gain"]
        target_K = self._vision_base_K_trans * (1.0 + gain * force_ratio)
        target_K = float(np.clip(target_K, policy["K_min"], policy["K_max"]))
        target_K_rot = target_K * (self._vision_base_K_rot / max(self._vision_base_K_trans, 1e-6))

        prev_K = self._K_trans_cur
        smooth_factor = policy["smooth_factor"]
        self._K_trans_cur += smooth_factor * (target_K - self._K_trans_cur)
        self._K_rot_cur += smooth_factor * (target_K_rot - self._K_rot_cur)
        self._fusion_delta_K = self._K_trans_cur - self._vision_base_K_trans
        self._fusion_active = force_ratio > 0.0

        if self.ctrl is not None and abs(self._K_trans_cur - prev_K) > 0.5:
            K_6x6 = self._build_stiffness(self._K_trans_cur, self._K_rot_cur)
            self.ctrl.set_impedance(K_6x6)

    def _update_force_only_adaptive_impedance(self, now: float):
        """G 模式：复用 force_adaptive_teleop.py 的纯外力在线变阻抗。

        该模式不使用视觉。外力超过自适应死区后，按线性饱和律
        将当前平动/旋转刚度从固定基线平滑降低：

            K_t = K_base * (1 - alpha * clip((|F|-F_db)/(F_sat-F_db), 0, 1))

        G 与 E/F 共用同一主循环、ExperimentTimeline、CSV 和事件 JSON，
        便于进行 A/E/G/F 的匹配比较。
        """
        if not self._force_only_adaptive:
            return
        if now - self._force_adapt_last_update < FUSION_IMPD_UPDATE_INTERVAL:
            return
        self._force_adapt_last_update = now

        f_mag = float(np.linalg.norm(self._F_ext_current[:3]))
        effective_force = max(f_mag - self._force_adapt_deadband, 0.0)
        force_span = max(
            self._force_adapt_F_sat - self._force_adapt_deadband, 0.1
        )
        ratio = float(np.clip(effective_force / force_span, 0.0, 1.0))
        target_K = self._force_adapt_base_K * (
            1.0 - self._force_adapt_alpha * ratio
        )
        target_K = max(target_K, K_TRANS_MIN)
        target_K_rot = target_K * G_K_ROT_RATIO

        prev_K = self._K_trans_cur
        self._K_trans_cur += G_IMPD_SMOOTH_FACTOR * (
            target_K - self._K_trans_cur
        )
        self._K_rot_cur += G_IMPD_SMOOTH_FACTOR * (
            target_K_rot - self._K_rot_cur
        )

        self._force_adapt_target_K = target_K
        self._force_adapt_ratio = ratio
        self._force_adapt_active = ratio > 0.0
        self._force_adapt_delta_K = self._K_trans_cur - self._force_adapt_base_K

        if self.ctrl is not None and abs(self._K_trans_cur - prev_K) > 0.5:
            K_6x6 = self._build_stiffness(self._K_trans_cur, self._K_rot_cur)
            self.ctrl.set_impedance(K_6x6)

    # ═══════════════════════════════════════════
    # Vision 模式 — 视觉线程 (RealSense + YOLO)
    # ═══════════════════════════════════════════

    def _vision_loop(self):
        """视觉检测循环 — 双进程架构

        主进程 (本线程): 15fps 捕获 + 显示 (永不阻塞)
        ⚡ 低帧率 (15fps) / 低分辨率 (424×240) 防止与 Omega.7 USB 等时传输争用带宽
        ──────────────────────────────────────────────
        wait_for_frames → 入队 frame_queue → 读 result_queue → imshow → 循环

        YOLO 独立进程: 异步推理 (拥有独立 GIL)
        ──────────────────────────────────────
        读 frame_queue → detect_and_map → 入队 result_queue → 循环
        """
        import cv2
        import pyrealsense2 as rs
        import queue as _q

        # ── 配置 RealSense ──
        # ⚡ USB 带宽保护: 使用低位深 (424×240@15fps) 避免与 Omega.7 USB 等时传输争用
        #   高带宽 (640×480@30fps) 会抢占 Omega.7 的 USB 带宽导致 dhd.getPosition() 冻结
        #   详见 plans/vision_mode_usb_fix_plan.md
        pipeline = rs.pipeline()
        config = rs.config()
        config.enable_stream(rs.stream.color, 424, 240, rs.format.bgr8, 15)
        pipeline.start(config)
        pipeline_running = True
        align = rs.align(rs.stream.color)
        print("[视觉线程] RealSense D435i 已启动")

        # ── 进程间通信 ──
        frame_queue = mp.Queue(maxsize=1)     # 仅保留最新 RGB 帧，避免视觉延迟累积
        result_queue = mp.Queue(maxsize=2)    # 检测结果 ← YOLO 进程

        # ── 启动 YOLO 独立进程 ──
        self._vision_yolo_proc = mp.Process(
            target=_yolo_process_main,
            args=(YOLO_MODEL_PATH, YOLO_CONF_THRESHOLD,
                  frame_queue, result_queue),
            daemon=True,
        )
        self._vision_yolo_proc.start()
        print(f"[视觉线程] YOLO 独立进程已启动 (PID={self._vision_yolo_proc.pid})")

        # ── 初始化 OpenCV 显示窗口（直接在本线程内 imshow，参考 shared_control_node.py）──
        #   独立显示进程 + mp.Queue 帧传输会增加 IPC 开销和延迟，且可能加剧 USB 带宽争用
        if self._vision_enable_display:
            cv2.namedWindow("Camera View (Vision Mode)", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("Camera View (Vision Mode)", 640, 480)
            cv2.startWindowThread()
            print("[视觉线程] 📷 相机画面已开启（按 'q' 关闭画面）")

        # ── 共享状态（仅在本线程使用，无需锁）──
        last_det = {"bbox": None, "active": False}
        _cycle = 0

        # ── 主循环: 15fps 捕获 + 推理结果上报（不涉及任何 cv2 GUI 操作）──
        # timeout_ms=5000: 与 shared_control_node.py 一致，RealSense 首次启动/带宽暂用
        #   时需等待较长时间；200ms 过短会频繁抛出异常，浪费 CPU 导致 Franka 通信丢包
        while self._vision_active:
            _cycle += 1
            try:
                # Omega.7 连续读取失败时，主控制线程会要求视觉线程短暂停止
                # RealSense pipeline，让 USB 带宽归还给 Omega.7。
                pause_until = self._vision_pause_until
                if pause_until > time.time():
                    if pipeline_running:
                        try:
                            pipeline.stop()
                            pipeline_running = False
                            print("[视觉线程] ⏸️  RealSense 暂停，等待 Omega.7 USB 恢复")
                        except Exception as e:
                            print(f"[视觉线程] ⚠️ 暂停 RealSense 失败: {e}")
                    time.sleep(0.05)
                    continue
                elif not pipeline_running:
                    try:
                        pipeline.start(config)
                        align = rs.align(rs.stream.color)
                        pipeline_running = True
                        self._vision_restarts += 1
                        print(f"[视觉线程] ▶️  RealSense 已恢复 (#{self._vision_restarts})")
                    except Exception as e:
                        print(f"[视觉线程] ⚠️ 恢复 RealSense 失败: {e}")
                        time.sleep(0.2)
                        continue

                frames = pipeline.wait_for_frames(timeout_ms=5000)
                aligned = align.process(frames)
                color_frame = aligned.get_color_frame()
                if not color_frame:
                    continue

                if not self._first_frame_marked:
                    self._timeline.mark("first_frame")
                    self._first_frame_marked = True

                rgb = np.asanyarray(color_frame.get_data())

                # ── 送帧 → YOLO 进程 ──
                try:
                    frame_queue.put_nowait(rgb)
                except _q.Full:
                    pass  # YOLO 处理不过来时丢帧（不影响显示）

                # ── 收结果 ← YOLO 进程 ──
                try:
                    det = result_queue.get_nowait()
                    last_det["bbox"] = det["bbox"]
                    last_det["profile"] = det["profile"]
                    last_det["class"] = det["class"]
                    last_det["conf"] = det["conf"]
                    last_det["active"] = True

                    # ── 更新共享状态 (线程安全) ──
                    with self._vision_lock:
                        self._vision_detection = det
                        self._vision_profile = det["profile"]
                        self._vision_last_time = time.time()
                        self._vision_confidence = float(det.get("conf", float("nan")))
                        self._vision_class = str(det.get("class", "unknown"))
                    self._timeline.mark(
                        "first_detection", confidence=self._vision_confidence,
                        detected_class=self._vision_class,
                    )

                except _q.Empty:
                    pass

                # ── 在视觉线程内直接显示（无需独立显示进程，参考 shared_control_node.py）──
                if self._vision_enable_display:
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
                    cv2.putText(display, "Vision Mode", (10, 460),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                                (0, 255, 0), 1)
                    cv2.imshow("Camera View (Vision Mode)", display)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        print("[视觉线程] 用户按 'q' 关闭画面")
                        self._vision_enable_display = False

            except Exception as e:
                if self._vision_active:
                    print(f"[视觉] ⚠️ 异常: {e}")

        if pipeline_running:
            pipeline.stop()
        print("[视觉线程] 已停止")

    def _print_param_change(self, name: str, before: float, after: float):
        """打印参数变更"""
        labels = {
            "damping_ratio": "阻尼比",
            "K_trans": "刚度",
            "K_rot": "旋转刚度",
            "K_fb": "力反馈增益",
            "deadband": "死区",
            "scale": "位置比例",
        }
        label = labels.get(name, name)
        if after != before:
            arrow = "↑" if after > before else "↓"
            print(f"  {label}: {before:.3f} {arrow} {after:.3f}")

    # ──── 键盘线程 ────

    def _keyboard_loop(self):
        """后台线程：异步读取键盘输入（带 fallback：无 tty 时降级到阻塞读）"""
        import sys as _sys
        import select as _sel

        # 先尝试 tty 模式
        use_tty = False
        try:
            import tty as _tty
            import termios as _termios
            fd = _sys.stdin.fileno()
            old = _termios.tcgetattr(fd)
            _tty.setcbreak(fd)
            use_tty = True
        except Exception:
            use_tty = False

        if use_tty:
            try:
                while self.running:
                    r, _, _ = _sel.select([_sys.stdin], [], [], 0.03)
                    if r:
                        ch = _sys.stdin.read(1)
                        with self._key_lock:
                            now = time.time()
                            self._key_pressed = ch
                            self._last_key_time = now
                            self._key_held = False
                            self._key_first_repeat = True
                    else:
                        with self._key_lock:
                            if self._key_pressed:
                                now = time.time()
                                elapsed = now - self._last_key_time
                                if self._key_first_repeat:
                                    if elapsed > self._key_repeat_delay:
                                        self._key_held = True
                                        self._key_first_repeat = False
                                        self._last_key_time = now
                                else:
                                    if elapsed > self._key_repeat_rate:
                                        self._last_key_time = now
                                        self._key_held = True
                                    else:
                                        self._key_held = False
            except Exception:
                pass
            finally:
                try:
                    _termios.tcsetattr(fd, _termios.TCSAFLUSH, old)
                except Exception:
                    pass
        else:
            # Fallback: 无真实 tty 环境
            try:
                import termios as _termios_fb
            except ImportError:
                _termios_fb = None
            while self.running:
                try:
                    r, _, _ = _sel.select([_sys.stdin], [], [], 0.1)
                    if r:
                        ch = _sys.stdin.read(1)
                        if ch:
                            with self._key_lock:
                                now = time.time()
                                self._key_pressed = ch
                                self._last_key_time = now
                                self._key_held = False
                                self._key_first_repeat = True
                except (EOFError, ValueError):
                    break
                except Exception:
                    pass

    def _process_keyboard(self):
        """主循环中处理缓存的键盘输入"""
        # ── 正式实验模式：仅允许查看帮助，禁用调参、预设切换和参数加载 ──
        if self._experiment_parameters_locked:
            key = ""
            with self._key_lock:
                if self._key_pressed and not self._key_held:
                    key = self._key_pressed
                    self._key_pressed = ""
            if key == "h":
                self._print_help()
            # 忽略所有会改变参数的按键 (1-0, q/w, a-f, z-c, b)
            return

        key = ""
        with self._key_lock:
            if self._key_pressed:
                key = self._key_pressed
                if not self._key_held:
                    self._key_pressed = ""

        if not key:
            return

        # ── 参数微调 ──
        if key == "1":
            self._change_param("damping_ratio", -0.1)
        elif key == "2":
            self._change_param("damping_ratio", 0.1)
        elif key == "3":
            self._change_param("K_trans", -10.0)
        elif key == "4":
            self._change_param("K_trans", 10.0)
        elif key == "5":
            self._change_param("K_fb", -0.05)
        elif key == "6":
            self._change_param("K_fb", 0.05)
        elif key == "7":
            self._change_param("deadband", -0.05)
        elif key == "8":
            self._change_param("deadband", 0.05)
        elif key == "9":
            self._change_param("scale", -0.5)
        elif key == "0":
            self._change_param("scale", 0.5)
        # ── 旋转刚度 ──
        elif key == "q":
            self._change_param("K_rot", -1.0)
        elif key == "w":
            self._change_param("K_rot", 1.0)
        # ── 预设切换 ──
        elif key == "a":
            self._set_preset("light")
        elif key == "s":
            self._set_preset("standard")
        elif key == "d":
            self._set_preset("stable")
        elif key == "f":
            self._set_preset("rigid")
        elif key == "z":
            self._set_preset("soft_obj")
        elif key == "x":
            self._set_preset("medium_obj")
        elif key == "c":
            self._set_preset("hard_obj")
        # ── 保存/加载 ──
        elif key == "v":
            self._save_params()
        elif key == "b":
            self._load_params()
        # ── 帮助 ──
        elif key == "h":
            self._print_help()

    # ═══════════════════════════════════════════
    # 参数保存/加载
    # ═══════════════════════════════════════════

    def _save_params(self):
        """保存当前参数到 JSON 文件"""
        params = {
            "K_trans": self._K_trans_cur,
            "K_rot": self._K_rot_cur,
            "damping_ratio": self._damping_ratio_cur,
            "K_fb": self._K_fb_cur,
            "deadband": self._deadband_cur,
            "scale": self._scale_cur,
        }
        try:
            with open(self.SAVE_FILE, "w") as f:
                json.dump(params, f, indent=2)
            print(f"  💾 参数已保存到 {self.SAVE_FILE}")
        except Exception as e:
            print(f"  ❌ 保存失败: {e}")

    def _load_params(self):
        """从 JSON 文件加载参数"""
        try:
            with open(self.SAVE_FILE, "r") as f:
                params = json.load(f)
        except Exception as e:
            print(f"  ❌ 加载失败: {e}")
            return

        for key, val in params.items():
            attr = f"_{key}_cur"
            if hasattr(self, attr):
                setattr(self, attr, val)

        # 更新控制器
        K = self._build_stiffness(self._K_trans_cur, self._K_rot_cur)
        self.ctrl.set_impedance(K)

        print(f"  📂 已从 {self.SAVE_FILE} 加载参数")
        for key, val in params.items():
            print(f"     {key}: {val}")

    # ═══════════════════════════════════════════
    # 夹爪控制 — 有限状态机
    # ═══════════════════════════════════════════

    # ── 夹钳角度自适应归一化 ──

    def _update_grip_calibration(self, angle_deg: float):
        """运行时自适应更新夹钳角度范围 (只向外扩展)"""
        if angle_deg < self._grip_min:
            self._grip_min = angle_deg
        if angle_deg > self._grip_max:
            self._grip_max = angle_deg
        self._calibration_samples += 1

    def _angle_to_norm(self, angle_deg: float) -> float:
        """夹钳角度 → 归一化开度 [0,1] (0=闭合, 1=全开)"""
        grip_range = self._grip_max - self._grip_min
        if grip_range < 1.0:
            grip_range = GRIP_ANGLE_INIT_MAX - GRIP_ANGLE_INIT_MIN
            norm = (GRIP_ANGLE_INIT_MAX - angle_deg) / grip_range
        else:
            norm = (self._grip_max - angle_deg) / grip_range
        return float(np.clip(norm, 0.0, 1.0))

    def _norm_to_width(self, norm: float) -> float:
        """归一化开度 [0,1] → 夹爪宽度 (m)"""
        return float(np.clip(norm * self._max_width, GRIPPER_MIN_WIDTH, self._max_width))

    def _refresh_gripper_measurement(self):
        """低频读取夹爪实测宽度；失败时不以命令宽度冒充实测值。"""
        if self.gripper is None:
            return
        try:
            state = self.gripper.read_once()
            width = float(getattr(state, "width"))
            if np.isfinite(width):
                self._gripper_width_actual = width
                self._gripper_width_valid = True
                return
        except Exception:
            pass
        self._gripper_width_actual = float("nan")
        self._gripper_width_valid = False

    def _angle_to_width(self, angle_deg: float) -> float:
        """保留的兼容接口：夹钳角度 → 夹爪宽度 (m)"""
        return self._norm_to_width(self._angle_to_norm(angle_deg))

    # ── 夹爪命令执行 (独立线程) ──

    def _gripper_stop(self) -> bool:
        """停止夹爪并释放力保持状态"""
        if self.gripper is None:
            return False
        try:
            self.gripper.stop()
            time.sleep(STOP_SETTLE_TIME)
            return True
        except Exception as e:
            print(f"\n  ⚠️ 夹爪 stop() 失败: {e}")
            return False

    def _execute_idle_move(self, width: float):
        """IDLE 状态：move() 跟随用户角度"""
        if self.gripper is None:
            return
        self._cmd_busy = True
        try:
            self.gripper.move(width, self._gripper_speed_cur)
            self._last_cmd_width = width
            self._gripper_width_actual = float("nan")
            self._gripper_width_valid = False
            self._cmd_count += 1
        except Exception as e:
            print(f"\n  ⚠️ move 失败: {e}")
        finally:
            self._cmd_busy = False

    def _execute_grasp(self, width: float):
        """GRASPING 状态：grasp() 力控抓取"""
        if self.gripper is None:
            self._gripper_state = GripperState.IDLE
            self._cmd_busy = False
            return
        self._cmd_busy = True
        try:
            success = self.gripper.grasp(
                width, self._gripper_speed_cur, self._gripper_force_cur,
                GRIPPER_EPS_INNER, GRIPPER_EPS_OUTER,
            )
            self._last_cmd_width = width
            self._cmd_count += 1
            if success:
                self._grasp_success = True
                self._gripper_width_actual = float("nan")
                self._gripper_width_valid = False
                print(f"\n  🤖 已抓取物体! (宽度={width*1000:.1f}mm, 力={self._gripper_force_cur:.0f}N)")
                if self._gripper_state == GripperState.GRASPING:
                    self._gripper_state = GripperState.HOLDING
            else:
                self._grasp_success = False
                print(f"\n  🤖 未检测到物体 (宽度={width*1000:.1f}mm)")
                if self._gripper_state == GripperState.GRASPING:
                    self._gripper_state = GripperState.IDLE
        except Exception as e:
            print(f"\n  ⚠️ grasp 失败: {e}")
            self._grasp_success = False
            if self._gripper_state == GripperState.GRASPING:
                self._gripper_state = GripperState.IDLE
        finally:
            # release 可能已中断 grasp，不要提前清掉 release 线程的 busy 状态。
            if self._gripper_state != GripperState.RELEASING:
                self._cmd_busy = False

    def _execute_release(self, width: float):
        """RELEASING 状态：先 stop 释放力保持，再 move 张开"""
        if self.gripper is None:
            self._gripper_state = GripperState.IDLE
            self._cmd_busy = False
            return
        self._cmd_busy = True
        try:
            # 第一步：stop 释放力保持
            print(f"\n  🛑 释放力保持...")
            if not self._gripper_stop():
                raise RuntimeError("stop() 未能释放夹爪力控")
            # 第二步：move 到目标开度
            moved = self.gripper.move(width, self._gripper_speed_cur)
            if moved is False:
                print("  ⚠️ 首次张开被拒绝，再次 stop 后重试...")
                if not self._gripper_stop():
                    raise RuntimeError("重试前 stop() 失败")
                moved = self.gripper.move(width, self._gripper_speed_cur)
            if moved is False:
                raise RuntimeError("move() 两次均未能张开夹爪")
            self._last_cmd_width = width
            self._gripper_width_actual = float("nan")
            self._gripper_width_valid = False
            self._cmd_count += 1
            print(f"  ✅ 夹爪已张开到 {width*1000:.1f}mm")
            self._gripper_state = GripperState.IDLE
        except Exception as e:
            print(f"\n  ⚠️ release 失败: {e}")
            self._gripper_state = GripperState.IDLE
        finally:
            self._cmd_busy = False

    def _trigger_idle_move(self, width: float):
        """触发 IDLE 状态下的 move（跟随）"""
        if self._cmd_busy:
            self._pending_width = width
            return
        self._pending_width = None
        t = threading.Thread(target=self._execute_idle_move, args=(width,),
                             daemon=True)
        t.start()

    def _trigger_grasp(self, width: float):
        """触发 GRASPING 状态的 grasp"""
        self._gripper_state = GripperState.GRASPING
        t = threading.Thread(target=self._execute_grasp, args=(width,),
                             daemon=True)
        t.start()

    def _trigger_release(self, width: float):
        """触发 RELEASING 状态的 stop+move"""
        self._gripper_state = GripperState.RELEASING
        t = threading.Thread(target=self._execute_release, args=(width,),
                             daemon=True)
        t.start()

    # ── 有限状态机 (核心逻辑) ──

    def _update_state_machine(self, target_norm: float, target_width: float):
        """
        二值锁存夹爪：闭合只执行一次力控 grasp，张开执行 stop + 完全打开。

        状态图:
          IDLE:
            - norm < GRASP_THRESHOLD (0.20):  → GRASPING (grasp)
            - norm > MOVE_THRESHOLD (0.80):    → move() 跟随
            - 过渡区 (0.20~0.80): 不发送命令

          GRASPING:
            - 等待 grasp 线程完成
            - 成功: → HOLDING; 失败: → IDLE

          HOLDING:
            - norm > MOVE_THRESHOLD (0.80): → RELEASING (stop + move)
            - 灰色按钮: → RELEASING (由按钮事件处理)

          RELEASING:
            - 等待 release 线程完成 → 自动 → IDLE
        """
        # ── IDLE: 只响应张开/闭合边沿，不再连续 move 干扰力保持 ──
        if self._gripper_state == GripperState.IDLE:
            if target_norm > MOVE_THRESHOLD:
                if not self._grasp_armed and not self._cmd_busy:
                    # grasp() 可能返回 False 但夹爪仍在施力，张开时仍强制 stop。
                    self._grasp_armed = True
                    self._trigger_release(self._max_width)
                else:
                    self._grasp_armed = True
            elif target_norm < GRASP_THRESHOLD and self._grasp_armed:
                if not self._cmd_busy:
                    self._grasp_armed = False
                    # 目标设为 0 mm，由 20 N 力控在物体表面停止并持续保持。
                    self._trigger_grasp(GRIPPER_MIN_WIDTH)
            return

        # ── GRASPING: 允许张开手势中断 ──
        if self._gripper_state == GripperState.GRASPING:
            if target_norm > MOVE_THRESHOLD:
                self._grasp_armed = True
                self._trigger_release(self._max_width)
            return

        # ── HOLDING: 力保持中，检测释放意图 ──
        if self._gripper_state == GripperState.HOLDING:
            if target_norm > MOVE_THRESHOLD:
                if not self._cmd_busy:
                    self._grasp_armed = True
                    self._trigger_release(self._max_width)
            return

        # ── RELEASING: 等待 release 完成 ──
        if self._gripper_state == GripperState.RELEASING:
            return

    # ── 夹爪控制主入口（由主循环降频调用）──

    def _update_gripper(self):
        """根据 Omega.7 夹钳角度 → 状态机控制 Franka 夹爪"""
        grip_deg = getattr(self, '_omega_grip_current', None)
        if grip_deg is None:
            return

        # 自适应更新角度范围
        self._update_grip_calibration(grip_deg)

        # 计算归一化开度和目标宽度
        target_norm = self._angle_to_norm(grip_deg)
        target_width = self._norm_to_width(target_norm)

        # 状态机更新
        self._update_state_machine(target_norm, target_width)

    # ═══════════════════════════════════════════
    # 界面打印
    # ═══════════════════════════════════════════

    def _print_help(self):
        """打印按键帮助"""
        if self._force_only_adaptive:
            print("\n" + "=" * 65)
            print("  🟣 G Force-Only 模式 — 纯外力在线变阻抗")
            print("=" * 65)
            print("  无视觉；接触外力超过自适应死区后在线降低阻抗刚度")
            print(
                f"  K_t = {G_K_BASE:.0f} · "
                f"(1 − {G_ALPHA:.2f} · clip((|F|−{G_ADAPT_DEADBAND:.1f})/"
                f"({G_F_SAT:.1f}−{G_ADAPT_DEADBAND:.1f}), 0, 1))"
            )
            print("  参数已锁定，使用与 E/F 相同的实验阶段和数据记录")
            print("  ┌──────────┬──────────────────────────────────────┐")
            print("  │ h        │ 打印此帮助                            │")
            print("  │ v        │ 保存参数到 ~/teleop_params.json       │")
            print("  │ b        │ 从 ~/teleop_params.json 加载参数      │")
            print("  │ Ctrl+C   │ 安全退出                              │")
            print("  └──────────┴──────────────────────────────────────┘")
            print("=" * 65)
        elif self._vision_enabled and hasattr(self, '_vision_auto_map') and self._vision_auto_map:
            print("\n" + "=" * 65)
            if self._vision_force_fusion:
                print("  👁️+F Vision-Force 模式 — 视觉前馈 + 力反馈微调")
            else:
                print("  👁️  Vision 模式 — YOLO 自动映射物体手感")
            print("=" * 65)
            print("  YOLO 检测物体 → PhysicsProfile.label → PRESETS:")
            print("    soft   → 🫧 软物体手感 (低刚度 50N/m, 低增益 0.2)")
            print("    medium → 📦 中物体手感 (中刚度 150N/m, 中增益 0.5)")
            print("    hard   → 🪨 硬物体手感 (高刚度 250N/m, 高增益 1.0)")
            print("  🔒 第一次检测到物体后参数即被锁定，不再跟随后续检测变化")
            if self._vision_force_fusion:
                print("  🔁 锁定后以视觉策略为前馈基线，接触外力只做有界刚度微调")
            print("  ┌──────────┬──────────────────────────────────────┐")
            print("  │ h        │ 打印此帮助                            │")
            print("  │ v        │ 保存参数到 ~/teleop_params.json       │")
            print("  │ b        │ 从 ~/teleop_params.json 加载参数      │")
            print("  │ q (画面) │ 关闭摄像头预览窗口                     │")
            print("  │ Ctrl+C   │ 安全退出                              │")
            print("  │ 其他按键 │ ⚠️  vision模式下参数调节已禁用         │")
            print("  ├──────────┴──────────────────────────────────────┤")
            print("  │  🎮 Omega.7 按钮 — 夹爪控制                       │")
            print("  │  灰色按钮 (Btn0) → 夹爪完全张开 (复位)             │")
            print("  │  夹钳张开 (>80%) → 夹爪张开 (move)                 │")
            print("  │  夹钳捏合 (<20%) → 力控抓取 (grasp)                │")
            print("  │  过渡区 (20~80%) → 保持当前状态                    │")
            print("  └──────────────────────────────────────────────────┘")
            print("=" * 65)
        elif self._vision_enabled and hasattr(self, '_vision_auto_map') and not self._vision_auto_map:
            print("\n" + "=" * 65)
            print("  👁️  Vision-Observe 模式 — 视觉仅观察，不改变手感")
            print("=" * 65)
            print("  YOLO 检测结果仅在屏幕上显示，参数调节保持手动控制:")
            print("  ┌──────────┬──────────────────────────────────────┐")
            print("  │ 1/2      │ 阻尼比 ζ -/+  (步长 0.1)             │")
            print("  │ 3/4      │ 刚度 K -/+     (步长 10 N/m)          │")
            print("  │ 5/6      │ 力反馈增益 -/+  (步长 0.05)           │")
            print("  │ 7/8      │ 死区 -/+       (步长 0.05 N)          │")
            print("  │ 9/0      │ 位置比例 -/+   (步长 0.5)             │")
            print("  │ q/w      │ 旋转刚度 -/+   (步长 1 Nm/rad)        │")
            print("  ├──────────┼──────────────────────────────────────┤")
            print("  │ a        │ 灵动模式 (低阻尼+低刚度)              │")
            print("  │ s        │ 标准模式 (临界阻尼+中刚度)            │")
            print("  │ d        │ 沉稳模式 (高阻尼+高刚度)              │")
            print("  │ f        │ 刚硬模式 (超高阻尼+超高刚度)          │")
            print("  ├──────────┼──────────────────────────────────────┤")
            print("  │ z        │ 软物体手感 (低增益+低刚度)            │")
            print("  │ x        │ 中物体手感 (中增益+中刚度)            │")
            print("  │ c        │ 硬物体手感 (高增益+高刚度)            │")
            print("  ├──────────┼──────────────────────────────────────┤")
            print("  │ v        │ 保存参数到 ~/teleop_params.json       │")
            print("  │ b        │ 从 ~/teleop_params.json 加载参数      │")
            print("  │ h        │ 打印此帮助                            │")
            print("  ├──────────┴──────────────────────────────────────┤")
            print("  │  🎮 Omega.7 按钮 — 夹爪控制                       │")
            print("  │  灰色按钮 (Btn0) → 夹爪完全张开 (复位)             │")
            print("  │  夹钳张开 (>80%) → 夹爪张开 (move)                 │")
            print("  │  夹钳捏合 (<20%) → 力控抓取 (grasp)                │")
            print("  │  过渡区 (20~80%) → 保持当前状态                    │")
            print("  ├──────────────────────────────────────────────────┤")
            print("  │ Ctrl+C → 安全退出                                │")
            print("  └──────────────────────────────────────────────────┘")
            print("=" * 65)
        else:
            print("\n" + "=" * 65)
            print("  ⌨️  键盘控制 — 实时调节手感")
            print("=" * 65)
            print("  ┌──────────┬──────────────────────────────────────┐")
            print("  │ 1/2      │ 阻尼比 ζ -/+  (步长 0.1)             │")
            print("  │ 3/4      │ 刚度 K -/+     (步长 10 N/m)          │")
            print("  │ 5/6      │ 力反馈增益 -/+  (步长 0.05)           │")
            print("  │ 7/8      │ 死区 -/+       (步长 0.05 N)          │")
            print("  │ 9/0      │ 位置比例 -/+   (步长 0.5)             │")
            print("  │ q/w      │ 旋转刚度 -/+   (步长 1 Nm/rad)        │")
            print("  ├──────────┼──────────────────────────────────────┤")
            print("  │ a        │ 灵动模式 (低阻尼+低刚度)              │")
            print("  │ s        │ 标准模式 (临界阻尼+中刚度)            │")
            print("  │ d        │ 沉稳模式 (高阻尼+高刚度)              │")
            print("  │ f        │ 刚硬模式 (超高阻尼+超高刚度)          │")
            print("  ├──────────┼──────────────────────────────────────┤")
            print("  │ z        │ 软物体手感 (低增益+低刚度)            │")
            print("  │ x        │ 中物体手感 (中增益+中刚度)            │")
            print("  │ c        │ 硬物体手感 (高增益+高刚度)            │")
            print("  ├──────────┼──────────────────────────────────────┤")
            print("  │ v        │ 保存参数到 ~/teleop_params.json       │")
            print("  │ b        │ 从 ~/teleop_params.json 加载参数      │")
            print("  │ h        │ 打印此帮助                            │")
            print("  ├──────────┴──────────────────────────────────────┤")
            print("  │  🎮 Omega.7 按钮 — 夹爪控制                       │")
            print("  │  灰色按钮 (Btn0) → 夹爪完全张开 (复位)             │")
            print("  │  夹钳张开 (>80%) → 夹爪张开 (move)                 │")
            print("  │  夹钳捏合 (<20%) → 力控抓取 (grasp)                │")
            print("  │  过渡区 (20~80%) → 保持当前状态                    │")
            print("  ├──────────────────────────────────────────────────┤")
            print("  │ Ctrl+C → 安全退出                                │")
            print("  └──────────────────────────────────────────────────┘")
            print("=" * 65)

    def _print_status(self):
        """打印当前参数和状态（每次独立一行）。"""
        # 现场显示使用 CSV operation_time：首次有效操作为 0 s，
        # 一直连续到任务结束。system_time 仍保留在 CSV 中用于诊断启动阶段。
        timeline = self._timeline.snapshot(time.perf_counter())
        operation_time = timeline["operation_time"]
        elapsed_s = operation_time if np.isfinite(operation_time) else 0.0
        phase = timeline["phase"]
        K_fb_disp = self._K_fb_cur
        deadband_disp = self._deadband_cur
        F_xyz = self._F_ext_current[:3]
        F_mag = np.linalg.norm(F_xyz)
        traj_len = self._omega_traj_length  # 主端 Omega.7 累计轨迹长度 (m)

        # 夹爪状态（状态机）
        grip_busy_str = " ⏳" if self._cmd_busy else "   "
        last_grip_mm = self._last_cmd_width * 1000.0

        status = (
            f"[t={elapsed_s:7.1f}s] [阶段={phase}] "
            f"ζ={self._damping_ratio_cur:.2f} "
            f"Kt={self._K_trans_cur:.0f} "
            f"Kr={self._K_rot_cur:.1f} "
            f"Kfb={K_fb_disp:.2f} "
            f"db={deadband_disp:.2f} "
            f"s={self._scale_cur:.1f} "
            f"|Fext|={F_mag:.2f}N "
            f"L={traj_len:.2f}m "
            f"夹爪={last_grip_mm:.0f}mm "
            f"|{self._gripper_state.value}{grip_busy_str}"
        )
        if self._transition_active:
            status += " [🌀 过渡中]"
        if self._omega_read_fail_count > 0:
            status += f" ⚠️OmegaFail={self._omega_read_fail_count}"

        if self._force_only_adaptive:
            active = "*" if self._force_adapt_active else ""
            status += (
                f" 🟣G ΔK={self._force_adapt_delta_K:+.1f}{active}"
                f" r={self._force_adapt_ratio:.2f}"
            )

        # Vision 模式下附加检测信息
        if self._vision_enabled:
            lock_str = "🔒" if self._vision_locked else "🔓"
            with self._vision_lock:
                det = self._vision_detection
                profile = self._vision_profile
            if self._vision_force_fusion and self._vision_locked:
                active = "*" if self._fusion_active else ""
                status += f" 👁️+F ΔKf={self._fusion_delta_K:+.1f}{active}"
            elif hasattr(self, '_vision_auto_map') and not self._vision_auto_map:
                status += " 👁️OBS"
            else:
                status += " 👁️"
            if det is not None and profile is not None:
                now_ts = time.time()
                det_age = now_ts - self._vision_last_time
                if det_age < VISION_DETECTION_HOLD_TIMEOUT:
                    status += f" {lock_str}{det['class']}({profile.label})"
                else:
                    status += f" {lock_str}⚠️超时{det_age:.0f}s"
            else:
                status += f" {lock_str}无检测"

        # 不用 \r 覆盖旧内容：保留每秒状态，方便现场观察和事后对照。
        print(f"  {status}", flush=True)

    # ═══════════════════════════════════════════
    # 主控制循环
    # ═══════════════════════════════════════════

    def run(self):
        """主控制循环 (200Hz)"""
        self.running = True

        dt = 1.0 / CTRL_FREQ
        dt_gripper = 1.0 / GRIPPER_CTRL_FREQ
        dt_status = 1.0 / STATUS_FREQ
        dt_keyboard = 1.0 / KEYBOARD_FREQ

        # 轨迹录制计时
        self._trajectory_start_time = time.time()
        self._traj_cycle = 0

        # 启动键盘线程
        kb_thread = threading.Thread(target=self._keyboard_loop, daemon=True)
        kb_thread.start()

        # 显示初始帮助
        self._print_help()

        # 确定启动预设：命令行 preset > 实验模式基线
        if self._init_preset:
            self._set_preset(self._init_preset)
        elif self.mode in ("default", "vision_stiffness"):
            self._set_preset("experiment_fixed_a")
        elif self.mode == "vision_observe":
            self._set_preset("experiment_observe_d")
        elif self._force_only_adaptive:
            # G 模式已在 __init__ 中设置 force_adaptive 基线，不能被 standard 覆盖。
            pass
        else:
            self._set_preset("standard")

        if self._vision_enabled:
            if hasattr(self, '_vision_auto_map') and not self._vision_auto_map:
                mode_str = "👁️ Vision-Observe 模式 — 视觉仅观察不改变手感"
            elif self._vision_force_fusion:
                mode_str = "👁️+F Vision-Force 模式 — 视觉前馈 + 力反馈微调"
            else:
                mode_str = "👁️ Vision 模式 — YOLO 自动映射物体手感"
        elif self._init_preset:
            p = PRESETS[self._init_preset]
            mode_str = f"🎯 {p['name']} — {p['desc']}"
        elif self._force_only_adaptive:
            mode_str = "🟣 G Force-Only 模式 — 纯外力在线变阻抗"
        else:
            mode_str = "🕹️ Default 模式 — 键盘手动调节手感参数"
        print("\n" + "=" * 65)
        print(f"  🚀 遥操作已启动！{mode_str}")
        print("=" * 65 + "\n")

        # 状态调度使用单调时钟，避免系统时间校准导致跳秒。
        next_status_time = time.perf_counter()
        last_gripper_time = 0.0
        last_gripper_ctrl_time = 0.0
        last_gripper_measure_time = 0.0
        last_kb_time = 0.0
        last_cycle_perf = time.perf_counter()
        vision_start_time = time.time() + VISION_START_DELAY
        vision_start_announced = False

        try:
            while self.running:
                t_start = time.perf_counter()
                now = time.time()
                now_perf = t_start
                self._control_dt = now_perf - last_cycle_perf
                last_cycle_perf = now_perf

                # ⚡ Vision 模式：控制循环先稳定运行，再启动相机/YOLO。
                # 这样避免 RealSense/PyTorch 启动峰值把 Omega.7 或 Franka 通信挤掉。
                if self._vision_enabled and not self._vision_active:
                    if now >= vision_start_time:
                        self._start_vision_thread()
                    elif not vision_start_announced:
                        print(f"    ⏳ 控制循环先运行 {VISION_START_DELAY:.1f}s 后再启动视觉线程")
                        vision_start_announced = True

                # ── 1. 读 Omega.7 位置 + 夹爪 + 按钮 ──
                # ⚡ dhd.getPosition() 返回 -1 表示失败（不抛 Python 异常），
                #    失败时 raw_pos 不会被修改。Vision 模式下 RealSense D435i
                #    可能抢占 Omega.7 USB 等时传输带宽，导致读取失败。
                #    解决方案：检查返回值，失败时复用最后有效位置缓存。
                raw_pos = self._read_omega_position()

                # ── 1b. 累加主端 Omega.7 轨迹长度 ──
                # ⚡ 仅计算帧间位移用于轨迹累加，不更新 _omega_prev_pos。
                #    _omega_prev_pos 的更新推迟到 section 4（位置映射）末尾，
                #    确保 section 4 也能用正确的帧间位移累积到 _virtual_ref。
                delta_pos = raw_pos - self._omega_prev_pos
                if "task_start" in self._timeline.event_times:
                    self._omega_traj_length += np.linalg.norm(delta_pos)

                gripper_angle = ctypes.c_double()
                grip_ret = dhd.getGripperAngleDeg(gripper_angle)
                if grip_ret < 0:
                    # 读取失败 → 复用最后有效夹钳角度
                    omega_grip = self._omega_grip_last_valid
                else:
                    omega_grip = gripper_angle.value
                    self._omega_grip_last_valid = omega_grip
                self._omega_grip_current = omega_grip   # ← 供 _update_gripper 使用（已验证的角度）

                # ── 读取按钮 ──
                btn0 = 0
                try:
                    btn0 = dhd.getButton(0)  # 灰色按钮
                except Exception:
                    pass
                button = btn0  # 轨迹记录沿用 btn0

                # ── 按钮事件处理 (上升沿检测) ──
                # 灰色按钮 (button 0) → 夹爪完全张开复位 (状态机路径)
                if btn0 and not self._btn0_prev:
                    print(f"\n  🔘 灰色按钮 → 夹爪完全张开")
                    self._grasp_armed = False  # 主端仍闭合时，避免张开后立即重抓
                    if self._gripper_state != GripperState.RELEASING:
                        # 不依赖逻辑状态，始终 stop 力控后完全张开。
                        self._trigger_release(self._max_width)
                self._btn0_prev = btn0

                # ── 2. 读 Franka 状态 + 外力估计 ──
                if self.panda is not None:
                    try:
                        state = self.panda.get_state()
                        self._robot_pos_current = np.array(
                            [state.O_T_EE[12], state.O_T_EE[13], state.O_T_EE[14]],
                            dtype=float,
                        )
                        if self.force_estimator is not None:
                            self._F_ext_current = self.force_estimator.update(state)
                    except Exception:
                        pass  # Franka 读取失败时继续

                # ── 2b. 自动实验生命周期 ──
                F_mag_now = float(np.linalg.norm(self._F_ext_current[:3]))
                self._timeline.add_force_baseline(F_mag_now, now_perf)
                controller_ready = not self._transition_active
                if (self._timeline.phase == PHASE_PREP and
                        self._timeline.baseline_ready and controller_ready):
                    self._timeline.set_ready(now_perf)
                    self._timeline.start_task(now_perf, trigger="system_ready")
                    self._omega_prev_pos = raw_pos.copy()
                    print(
                        "\n\a  ✅ 实验开始 — 机械臂已可操作；"
                        "视觉识别在后台独立进行"
                    )
                self._timeline.observe_contact(F_mag_now, now_perf)
                self._timeline.observe_gripper(
                    self._gripper_state.value,
                    self._gripper_width_actual if self._gripper_width_valid else self._last_cmd_width,
                    now_perf,
                    grasp_success=self._grasp_success,
                )

                # ── 3. 力反馈计算 ──
                F_ext_xyz = self._F_ext_current[:3]
                F_scaled = F_ext_xyz * self._K_fb_cur
                F_haptic = np.where(
                    np.abs(F_scaled) > self._deadband_cur,
                    np.sign(F_scaled) * (np.abs(F_scaled) - self._deadband_cur),
                    0.0,
                )

                # ── 3a. 夹爪力反馈叠加 ──
                # 夹爪闭合程度映射到 Omega.7 力反馈 (Z 方向)，模拟夹持力感
                grip_norm = self._angle_to_norm(omega_grip)
                grip_force_mag = grip_norm * FORCE_FB_GAIN * FORCE_FB_MAX
                grip_force_mag = min(grip_force_mag, FORCE_FB_MAX)
                F_haptic[2] += grip_force_mag
                self._gripper_force_feedback = grip_force_mag

                try:
                    dhd.setForce(F_haptic)
                except Exception:
                    pass

                # ── 4. 位置映射（增量式） ──
                # 每帧累加 Omega.7 的位移变化量，而非计算相对于固定 home 的偏移。
                # 解决机械臂"被拴在" _virtual_ref 的问题：松开 Omega 回中时，
                # 机械臂停留在最后位置而非跳回初始位置。
                #   delta_raw = raw_pos - prev_pos（帧间变化）
                #   _virtual_ref += delta_raw * scale（累积位移）
                #   target_pos = _virtual_ref
                delta_raw = raw_pos - self._omega_prev_pos
                # READY前冻结从端，并持续更新主端参考，解锁时不会产生位置跳变。
                if "task_start" in self._timeline.event_times:
                    self._virtual_ref += delta_raw * self._scale_cur * SIGN
                target_pos = self._virtual_ref.copy()
                # 防止数值爆炸
                np.clip(target_pos, -10.0, 10.0, out=target_pos)

                # 更新上一帧 Omega 位置（供下轮 section 1b 和 section 4 使用）
                self._omega_prev_pos = raw_pos.copy()
                self._target_pos_current = target_pos.copy()

                # ── 4a. Vision 模式：从检测结果自动同步参数（首次检测后锁定）──
                #    vision_observe 模式：视觉仅观察不改变手感，跳过此段
                if self._vision_enabled and hasattr(self, '_vision_auto_map') and self._vision_auto_map:
                    with self._vision_lock:
                        profile = self._vision_profile
                        det_time = self._vision_last_time
                    now_ts = time.time()

                    if profile is not None and (now_ts - det_time) < VISION_DETECTION_HOLD_TIMEOUT:
                        # 有有效检测
                        if not self._vision_locked:
                            # ── 第一次检测到物体 → 锁定参数 ──
                            preset_key = self._profile_to_preset(profile)
                            self._vision_current_preset = preset_key
                            p = PRESETS.get(preset_key)
                            if p:
                                print(f"\n  👁️ 首次检测到物体 → {p['name']} (参数已锁定)")
                                print(f"     {p['desc']}")
                                # D模式调度完整阻抗组(Kt/Kr/zeta)；E/F应用完整多参数组。
                                self._smooth_transition(
                                    p["K_trans"], p["K_rot"], p["damping_ratio"]
                                )
                                if not self._vision_stiffness_only:
                                    self._K_fb_cur = p["K_fb"]
                                    self._deadband_cur = p["deadband"]
                                    self._scale_cur = p["scale"]
                                    self._gripper_speed_cur = p.get("gripper_speed", GRIPPER_SPEED)
                                    self._gripper_force_cur = p.get("gripper_force", GRIPPER_FORCE)
                                self._vision_locked_label = getattr(profile, "label", "unknown")
                                self._vision_base_K_trans = p["K_trans"]
                                self._vision_base_K_rot = p["K_rot"]
                                self._vision_base_damping = p["damping_ratio"]
                                self._fusion_delta_K = 0.0
                                self._fusion_active = False
                                if self._vision_force_fusion:
                                    print(
                                        "     🔁 融合模式: 视觉参数作为前馈基线，"
                                        "接触后按外力微调刚度"
                                    )
                            self._vision_locked = True
                            self._timeline.mark(
                                "vision_lock", detected_class=self._vision_class,
                                semantic_label=self._vision_locked_label,
                                confidence=self._vision_confidence,
                            )
                        # 锁定后不再更新参数，即使检测结果变化也不响应
                    # 锁定后也不再执行超时回退

                # ── 4b. G 模式：纯外力在线变阻抗 ──
                self._update_force_only_adaptive_impedance(now)

                # ── 4c. F 模式：视觉前馈基线 + 力反馈微调 ──
                self._update_vision_force_fusion(now)

                # ── 5. 发给 Franka ──
                if self.ctrl is not None:
                    self.ctrl.set_control(target_pos, self._init_ori)

                # ── 6. 夹爪控制 (降频) ──
                if (now - last_gripper_time) >= dt_gripper:
                    self._update_gripper()
                    last_gripper_time = now
                if (now - last_gripper_measure_time) >= 0.1:
                    self._refresh_gripper_measurement()
                    last_gripper_measure_time = now

                # ── 6b. 统一原始数据记录（状态更新完成后） ──
                if self._trajectory_record:
                    self._traj_cycle += 1
                    if self._traj_cycle % TRAJECTORY_DECIMATION == 0:
                        self._record_trajectory_sample(
                            raw_pos, omega_grip, button, now_perf
                        )

                if self._timeline.completed:
                    if self._auto_stop:
                        print("\n\a  ✅ 任务释放完成，自动结束并保存数据")
                        self.running = False
                        break
                    if not self._completion_announced:
                        print(
                            "\n\a  ✅ 任务释放完成；manual-stop 调试模式继续运行，"
                            "请按 Ctrl+C 保存并安全退出"
                        )
                        self._completion_announced = True

                # ── 7. 键盘处理 (降频) ──
                if (now - last_kb_time) >= dt_keyboard:
                    self._process_keyboard()
                    last_kb_time = now

                # ── 8. 状态打印 (降频) ──
                self._loop_count += 1
                if now_perf >= next_status_time:
                    self._print_status()
                    next_status_time += dt_status
                    # 如果某个控制周期阻塞过久，不补打过期状态，直接对齐下一秒。
                    if next_status_time <= now_perf:
                        missed = int((now_perf - next_status_time) / dt_status) + 1
                        next_status_time += missed * dt_status

                # ── 8a. 轨迹录制进度提示（每 30s） ──
                if self._trajectory_record and self._loop_count % int(CTRL_FREQ * 30) == 0:
                    elapsed = time.time() - self._trajectory_start_time
                    print(f"\n  📝 轨迹录制中: {len(self._trajectory)} 点, {elapsed:.0f}s")

                # ── 控制周期同步 ──
                elapsed = time.perf_counter() - t_start
                sleep_time = dt - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except KeyboardInterrupt:
            print("\n\n⚠️  收到 Ctrl+C，安全停止...")
            self._timeline.abort("keyboard_interrupt")
        except Exception as e:
            print(f"\n\n❌ 错误: {e}")
            self._timeline.abort(f"exception:{type(e).__name__}")
            import traceback
            traceback.print_exc()
        finally:
            self._shutdown()

    # ═══════════════════════════════════════════
    # 轨迹录制
    # ═══════════════════════════════════════════

    def _record_trajectory_sample(self, raw_pos, gripper_deg, button, now_perf=None):
        """记录一个轨迹样本点（主循环每周期调用）"""
        now_perf = time.perf_counter() if now_perf is None else now_perf
        F_mag = float(np.linalg.norm(self._F_ext_current[:3]))
        timeline = self._timeline.snapshot(now_perf)
        event = self._timeline.consume_events()
        F = np.asarray(self._F_ext_current, dtype=float)
        if F.size < 6:
            F = np.pad(F, (0, 6 - F.size), constant_values=np.nan)
        self._trajectory.append({
            "schema_version": 2,
            "system_time": timeline["system_time"],
            "time": timeline["system_time"],  # 内部兼容旧汇总逻辑
            "operation_time": timeline["operation_time"],
            "phase": timeline["phase"], "event": event,
            "mode": self._experiment_condition,
            "controller_mode": self.mode,
            "subject_id": self._timeline.subject_id,
            "object_id": self._timeline.object_id,
            "trial_id": self._timeline.trial_id,
            "omega_x": raw_pos[0], "omega_y": raw_pos[1], "omega_z": raw_pos[2],
            "x": raw_pos[0], "y": raw_pos[1], "z": raw_pos[2],
            "omega_valid": int(self._omega_read_valid),
            "gripper_deg": gripper_deg,
            "button": button,
            "target_x": self._target_pos_current[0],
            "target_y": self._target_pos_current[1],
            "target_z": self._target_pos_current[2],
            "robot_x": self._robot_pos_current[0],
            "robot_y": self._robot_pos_current[1],
            "robot_z": self._robot_pos_current[2],
            "F_ext_x": F[0], "F_ext_y": F[1], "F_ext_z": F[2],
            "T_ext_x": F[3], "T_ext_y": F[4], "T_ext_z": F[5],
            "K_trans": self._K_trans_cur,
            "K_rot": self._K_rot_cur,
            "damping_ratio": self._damping_ratio_cur,
            "K_fb": self._K_fb_cur,
            "deadband": self._deadband_cur,
            "scale": self._scale_cur,
            "F_ext_mag": F_mag,
            "gripper_state": self._gripper_state.value,
            "gripper_cmd_width": self._last_cmd_width,
            "gripper_width": self._gripper_width_actual,
            "gripper_width_valid": int(self._gripper_width_valid),
            "gripper_speed": self._gripper_speed_cur,
            "gripper_force": self._gripper_force_cur,
            "grasp_success": int(self._grasp_success),
            "vision_class": self._vision_class,
            "fusion_delta_K": self._fusion_delta_K,
            "fusion_active": int(self._fusion_active),
            "vision_label": self._vision_locked_label,
            "vision_confidence": self._vision_confidence,
            "vision_locked": int(self._vision_locked),
            "control_dt": self._control_dt,
            "force_adapt_target_K": self._force_adapt_target_K,
            "force_adapt_ratio": self._force_adapt_ratio,
            "force_adapt_active": int(self._force_adapt_active),
            "force_adapt_delta_K": self._force_adapt_delta_K,
            "force_baseline_mean": timeline["force_baseline_mean"],
            "force_baseline_std": timeline["force_baseline_std"],
            "force_threshold": timeline["force_threshold"],
        })

    def _save_trajectory(self, timestamp: str = None):
        """保存轨迹数据到 CSV

        Args:
            timestamp: 时间戳字符串 (YYYYMMDD_HHMMSS)，为 None 时自动生成
        Returns:
            (csv_path, timestamp): CSV 文件路径和实际使用的时间戳
        """
        if not self._trajectory or len(self._trajectory) < 10:
            return None, None

        import csv as _csv
        from datetime import datetime as _dt

        if timestamp is None:
            timestamp = _dt.now().strftime('%Y%m%d_%H%M%S')

        path = Path(self._trajectory_dir)
        path.mkdir(parents=True, exist_ok=True)
        fname = f"{self.mode}_{timestamp}.csv"
        fpath = path / fname

        # 计算采样率
        times = [row["system_time"] for row in self._trajectory]
        duration = times[-1] - times[0] if len(times) > 1 else 0
        actual_freq = len(times) / duration if duration > 0 else 0

        with open(fpath, "w", newline="") as f:
            writer = _csv.writer(f)
            writer.writerow(TRAJECTORY_CSV_HEADER)
            for row in self._trajectory:
                writer.writerow([row.get(key, "") for key in TRAJECTORY_CSV_HEADER])

        print(f"\n  🎯 轨迹已保存: {fpath}")
        print(f"     {len(self._trajectory)} 点, {duration:.1f}s, {actual_freq:.0f} Hz")
        print(f"     使用离线分析工具评估疲劳度:")
        print(f"     python3 my_test/omega7_trajectory_analyzer.py --load {fpath} --save-plot")
        events_path = path / f"{self.mode}_{timestamp}_events.json"
        self._timeline.save_events(events_path)
        print(f"     事件时间轴: {events_path}")
        return str(fpath), timestamp

    def _save_summary(self, timestamp: str):
        """保存运行汇总统计到 JSON 文件

        包含: 运行时间、轨迹长度、速度均值/方差/标准差、位置范围、
              模式名、预设名、最终参数等
        """
        import json as _json
        from datetime import datetime as _dt

        path = Path(self._trajectory_dir)
        path.mkdir(parents=True, exist_ok=True)
        fname = f"{self.mode}_{timestamp}_summary.json"
        fpath = path / fname

        # ── 基本时间统计 ──
        elapsed_total = self._timeline.system_time()

        # ── 轨迹统计 ──
        traj_len = self._omega_traj_length
        n_samples = len(self._trajectory)

        # 从轨迹数据计算速度统计
        speed_mean = 0.0
        speed_std = 0.0
        speed_var = 0.0
        speed_max = 0.0
        pos_x_range = [0.0, 0.0]
        pos_y_range = [0.0, 0.0]
        pos_z_range = [0.0, 0.0]

        # 末端平动外力模长统计，数据来自每个轨迹采样点的 F_ext_mag。
        force_peak = 0.0
        force_peak_time = 0.0
        force_mean = 0.0
        force_samples = [
            (float(row["time"]), float(row["F_ext_mag"]))
            for row in self._trajectory
            if np.isfinite(row.get("F_ext_mag", np.nan))
        ]
        if force_samples:
            force_peak_time, force_peak = max(force_samples, key=lambda item: item[1])
            force_mean = float(np.mean([item[1] for item in force_samples]))

        if n_samples >= 2:
            # 计算每帧瞬时速度 (m/s)
            speeds = []
            xs, ys, zs = [], [], []
            for i in range(1, n_samples):
                dt = self._trajectory[i]["time"] - self._trajectory[i-1]["time"]
                if dt > 0:
                    dx = self._trajectory[i]["x"] - self._trajectory[i-1]["x"]
                    dy = self._trajectory[i]["y"] - self._trajectory[i-1]["y"]
                    dz = self._trajectory[i]["z"] - self._trajectory[i-1]["z"]
                    speed = np.sqrt(dx*dx + dy*dy + dz*dz) / dt
                    speeds.append(speed)
                xs.append(self._trajectory[i]["x"])
                ys.append(self._trajectory[i]["y"])
                zs.append(self._trajectory[i]["z"])

            if speeds:
                speeds_arr = np.array(speeds)
                speed_mean = float(np.mean(speeds_arr))
                speed_var = float(np.var(speeds_arr))
                speed_std = float(np.std(speeds_arr))
                speed_max = float(np.max(speeds_arr))

            if xs:
                pos_x_range = [float(np.min(xs)), float(np.max(xs))]
                pos_y_range = [float(np.min(ys)), float(np.max(ys))]
                pos_z_range = [float(np.min(zs)), float(np.max(zs))]

        # ── 最终参数 ──
        final_params = {
            "K_trans": self._K_trans_cur,
            "K_rot": self._K_rot_cur,
            "damping_ratio": self._damping_ratio_cur,
            "K_fb": self._K_fb_cur,
            "deadband": self._deadband_cur,
            "scale": self._scale_cur,
            "vision_base_K_trans": self._vision_base_K_trans,
            "vision_base_K_rot": self._vision_base_K_rot,
            "fusion_delta_K_final": self._fusion_delta_K,
            "force_adapt_target_K_final": self._force_adapt_target_K,
            "force_adapt_ratio_final": self._force_adapt_ratio,
            "force_adapt_delta_K_final": self._force_adapt_delta_K,
        }

        # ── 模式信息 ──
        mode_info = {
            "mode": self.mode,
            "vision_enabled": self._vision_enabled,
            "vision_auto_map": self._vision_auto_map,
            "vision_force_fusion": self._vision_force_fusion,
            "force_only_adaptive": self._force_only_adaptive,
            "vision_locked": self._vision_locked,
            "vision_label": self._vision_locked_label,
        }
        if self.mode in PRESETS:
            mode_info["preset_name"] = PRESETS[self.mode]["name"]
            mode_info["preset_desc"] = PRESETS[self.mode]["desc"]

        fusion_config = None
        if self._vision_force_fusion:
            fusion_config = {
                "update_interval_s": FUSION_IMPD_UPDATE_INTERVAL,
                "contact_delay_s": FUSION_CONTACT_DELAY_S,
                "posterior_policy": FUSION_POSTERIOR_POLICY,
            }

        force_adapt_config = None
        if self._force_only_adaptive:
            force_adapt_config = {
                "update_interval_s": FUSION_IMPD_UPDATE_INTERVAL,
                "K_base_N_per_m": self._force_adapt_base_K,
                "alpha": self._force_adapt_alpha,
                "F_sat_N": self._force_adapt_F_sat,
                "force_deadband_N": self._force_adapt_deadband,
                "K_rot_ratio": G_K_ROT_RATIO,
                "smooth_factor": G_IMPD_SMOOTH_FACTOR,
            }

        summary = {
            "timestamp": timestamp,
            "saved_at": _dt.now().isoformat(),
            "mode": mode_info,
            "runtime": {
                "duration_s": round(elapsed_total, 2),
                "traj_length_m": round(traj_len, 4),
                "mean_speed_ms": round(speed_mean, 4),
                "speed_variance": round(speed_var, 6),
                "speed_std_ms": round(speed_std, 4),
                "max_speed_ms": round(speed_max, 4),
            },
            "trajectory": {
                "n_samples": n_samples,
                "pos_x_range_m": [round(v, 4) for v in pos_x_range],
                "pos_y_range_m": [round(v, 4) for v in pos_y_range],
                "pos_z_range_m": [round(v, 4) for v in pos_z_range],
            },
            "external_force": {
                "source": "Franka estimated external wrench",
                "metric": "norm(Fx, Fy, Fz)",
                "F_ext_peak_N": round(force_peak, 3),
                "F_ext_peak_time_s": round(force_peak_time, 4),
                "F_ext_mean_N": round(force_mean, 3),
                "n_samples": len(force_samples),
            },
            "final_params": final_params,
            "fusion_config": fusion_config,
            "force_adapt_config": force_adapt_config,
            "experiment": self._timeline.to_dict(),
        }

        with open(fpath, "w") as f:
            _json.dump(summary, f, indent=2, ensure_ascii=False)

        print(f"  📊 汇总已保存: {fpath}")
        print(f"     时长={elapsed_total:.1f}s  轨迹={traj_len:.3f}m  "
              f"速度均值={speed_mean:.3f}m/s  速度方差={speed_var:.4f}")
        print(
            f"     末端外力峰值={force_peak:.3f} N "
            f"(t={force_peak_time:.3f} s), 均值={force_mean:.3f} N"
        )

        return str(fpath)

    # ═══════════════════════════════════════════
    # 安全关闭
    # ═══════════════════════════════════════════

    def _shutdown(self):
        """安全关闭所有硬件"""
        self.running = False
        self._transition_stop.set()
        if not self._timeline.completed and not self._timeline.incomplete:
            self._timeline.abort("shutdown_before_task_completion")

        # 停止视觉线程和 YOLO 进程
        if self._vision_enabled and self._vision_active:
            self._vision_active = False
            print("\n   视觉模块已停止（YOLO 进程自动终止）")

        # 打印主端 Omega.7 轨迹长度统计
        elapsed_total = self._timeline.system_time()
        print(f"\n  📏 主端 Omega.7 轨迹长度统计:")
        print(f"     累计轨迹长度: {self._omega_traj_length:.3f} m")
        print(f"     运行时长:     {elapsed_total:.1f} s")
        if elapsed_total > 0:
            print(f"     平均速度:     {self._omega_traj_length / elapsed_total:.3f} m/s")
        if self._omega_read_fail_total > 0:
            print(f"     Omega读取失败: {self._omega_read_fail_total} 次")
        if self._vision_restarts > 0:
            print(f"     视觉USB恢复:   {self._vision_restarts} 次")

        # 打印夹爪统计
        print(f"\n  🤖 夹爪控制统计:")
        print(f"     总计命令:   {self._cmd_count} 次")
        print(f"     标定样本:   {self._calibration_samples} 次")
        print(f"     夹钳角度范围: [{self._grip_min:.1f}°, {self._grip_max:.1f}°] (自适应学习)")
        print(f"     最终状态:   {self._gripper_state.value}")

        # 保存轨迹 + 汇总统计（共用同一时间戳）
        if self._trajectory_record:
            from datetime import datetime as _dt
            timestamp = _dt.now().strftime('%Y%m%d_%H%M%S')
            csv_path, ts = self._save_trajectory(timestamp)
            if ts:
                self._save_summary(ts)
            if csv_path:
                try:
                    from force_metrics import analyze_csv
                    result = analyze_csv(csv_path, save_plot=True)
                    print(f"  📈 分阶段指标: {result.get('metrics_json')}")
                except Exception as e:
                    print(f"  ⚠️ 分阶段指标生成失败（原始CSV已保留）: {e}")

        print("\n   关闭 Omega.7 力输出...")
        try:
            dhd.setForce(np.zeros(3))
        except Exception:
            pass
        try:
            dhd.close()
        except Exception:
            pass
        print("✅ 已安全停止")


# ═══════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════

def main():
    # 动态从 PRESETS 生成 choices: default + vision + 所有 preset key
    MODE_CHOICES = [
        "default", "vision", "vision_observe", "vision_stiffness",
        "vision_force", "force_only", "g", "G", "f", "F",
    ] + sorted(PRESETS.keys())
    parser = argparse.ArgumentParser(description="交互式遥操作：实时调节阻尼/刚度/力反馈")
    parser.add_argument("--mode", "-m", type=str, default="default",
                        choices=MODE_CHOICES,
                        help="运行模式: experiment_fixed_a=SCI模式A固定参数, "
                             "soft_obj/medium_obj/hard_obj=SCI模式B人工预设, "
                             "vision_observe=SCI模式C视觉仅显示, "
                             "vision_stiffness=SCI模式D视觉仅调阻抗, "
                             "vision=SCI模式E视觉多参数前馈, "
                             "g/force_only=实验G纯外力在线变阻抗, "
                             "f/vision_force=实验F模式(视觉前馈+力反馈微调融合), "
                             "或直接指定预设: " + ", ".join(sorted(PRESETS.keys())))
    parser.add_argument("--load", "-l", type=str, default=None,
                        help="启动时加载参数文件路径")
    parser.add_argument("--no-trajectory", action="store_true",
                        help="关闭轨迹自动录制（默认开启）")
    parser.add_argument("--trajectory-dir", type=str, default=TRAJECTORY_DIR,
                        help=f"轨迹 CSV 输出目录 (默认: {TRAJECTORY_DIR}/)")
    parser.add_argument("--subject-id", default="unknown", help="被试编号")
    parser.add_argument("--object-id", default="unknown", help="物体编号")
    parser.add_argument("--trial-id", default="unknown", help="试次编号")
    parser.add_argument(
        "--manual-stop", action="store_true",
        help="调试模式：任务完成后不自动退出，按 Ctrl+C 时保存并安全关闭",
    )
    args = parser.parse_args()
    if args.mode in ("f", "F"):
        canonical_mode = "vision_force"
    elif args.mode in ("g", "G"):
        canonical_mode = "force_only"
    else:
        canonical_mode = args.mode

    teleop = InteractiveTeleop(
        mode=canonical_mode,
        record_trajectory=not args.no_trajectory,
        trajectory_dir=args.trajectory_dir,
        subject_id=args.subject_id,
        object_id=args.object_id,
        trial_id=args.trial_id,
        auto_stop=not args.manual_stop,
    )

    # 若指定了启动参数文件，替换默认保存路径
    if args.load:
        teleop.SAVE_FILE = args.load

    teleop.initialize()

    # 初始化后自动加载参数（若指定了加载文件）
    if args.load and os.path.exists(args.load):
        teleop._load_params()

    teleop.run()


if __name__ == "__main__":
    main()
