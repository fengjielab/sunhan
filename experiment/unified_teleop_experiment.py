#!/usr/bin/env python3
"""
unified_teleop_experiment.py — 统一遥操作实验脚本（修订版）
===============================================================

基于 interactive_teleop.py 的优雅架构，融合 4 种实验模式 + YOLO 视觉 + 评分卡。

【修订要点】
1. Mode B 改为三档选择（1/2/3 = 软/中/硬），确保实验可重复、与 C 组公平对比
2. Mode C/D YOLO 只在物体类别变化时更新参数，避免 200Hz 震荡
3. 录制改为手动 r 键控制，模式切换不再自动保存/自动开始
4. 增加实验计数器，实时提示当前进度（n/10）
5. YOLO 子进程支持 OpenCV 普通摄像头 fallback
6. 最终汇总输出均值、标准差、成功率等统计量
7. 评分卡增加变形量（mm）输入
8. 参数过渡增加线程锁，避免并发读写异常
9. 菜单同步更新，反映新的按键映射

实验流程:
   放物体 → 按 s/m/h 标记类别 → 按 a/b/c/d 切换模式 → 按 r 开始录制 → 
   操作 → 按 r 停止并评分 → 换模式/换物体 → 全部做完后按 q 退出汇总

按键:
   a → mode a (固定阻抗)          b → mode b (人工选阻抗: 1/2/3 选软/中/硬)
   c → mode c (自动YOLO+查表)      d → mode d (YOLO只选夹爪速度)
   s → 标记软物体                  m → 标记中等物体
   h → 标记硬物体                  r → 开始/停止录制 + 评分卡

   mode b 下:
     1 → 软物体参数 (K=50)          2 → 中等物体参数 (K=150)
     3 → 硬物体参数 (K=800)         i/k → K_trans +/- (10 N/m)
     j/l → deadband +/- (0.05 N)    [/] → gripper_speed +/-

   全局参数调节:
     !/@ → 阻尼比 ζ -/+ (步长 0.1)      5/6 → 力反馈增益 -/+ (步长 0.05)
     7/8 → 死区 -/+ (步长 0.05 N)        9/0 → 位置比例 -/+ (步长 0.5)

   z → 软物体手感预设                x → 中物体手感预设
   v → 保存参数到文件                n → 从文件加载参数
   q → 退出 (自动汇总)
"""

import argparse
import csv
import ctypes
import json
import math
import os
import queue
import select
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Tuple

import numpy as np

# ── 硬件依赖 ──
try:
    import forcedimension_core.dhd as dhd
    import forcedimension_core.drd as drd
except ImportError:
    try:
        import dhd as _dhd_mod
        dhd = _dhd_mod
        drd = None
    except ImportError:
        dhd = None
        drd = None
        print("⚠️  dhd 模块不可用", file=sys.stderr)

try:
    import panda_py
    from panda_py import controllers, libfranka
except ImportError:
    panda_py = None
    controllers = None
    libfranka = None
    print("⚠️  panda_py 模块不可用", file=sys.stderr)

# ── 项目内模块 ──
_EXP_DIR = os.path.dirname(os.path.abspath(__file__))
if _EXP_DIR not in sys.path:
    sys.path.insert(0, _EXP_DIR)
from vision_physics_mapper import (
    VisionPhysicsMapper,
    PhysicsProfile,
)
from grip_force_estimator import GripForceEstimator
from force_estimator import ForceEstimator


# ═══════════════════════════════════════════════════════
# Omega.7 统一封装层
# ═══════════════════════════════════════════════════════

if dhd is not None:
    def _omega_dhd_ok(ret: int) -> bool:
        return ret >= 0

    def _omega_open() -> bool:
        ret = dhd.open()
        if not _omega_dhd_ok(ret):
            print(f"    ❌ Omega.7 open 失败: {dhd.errorGetLastStr()}", file=sys.stderr)
            return False
        return True

    def _omega_close() -> None:
        dhd.close()

    def _omega_get_position(pos: np.ndarray) -> bool:
        ret = dhd.getPosition(pos)
        return _omega_dhd_ok(ret)

    def _omega_get_orientation(out) -> bool:
        ret = dhd.getOrientationDeg(out)
        return _omega_dhd_ok(ret)

    def _omega_get_gripper_angle(angle) -> bool:
        ret = dhd.getGripperAngleDeg(angle)
        return _omega_dhd_ok(ret)

    def _omega_get_button(btn_idx: int = 0) -> int:
        ret = dhd.getButton(btn_idx)
        if ret < 0:
            return 0
        return ret

    def _omega_set_force(force: np.ndarray) -> bool:
        ret = dhd.setForce(force)
        return _omega_dhd_ok(ret)

    def _omega_enable_force(enabled: bool = True) -> bool:
        ret = dhd.enableForce(enabled)
        return _omega_dhd_ok(ret)
else:
    def _omega_open() -> bool:
        return False

    def _omega_close() -> None:
        pass

    def _omega_get_position(pos: np.ndarray) -> bool:
        return False

    def _omega_get_orientation(out) -> bool:
        out[:] = [0.0, 0.0, 0.0]
        return False

    def _omega_get_gripper_angle(angle) -> bool:
        angle.value = 0.0
        return False

    def _omega_get_button(btn_idx: int = 0) -> int:
        return 0

    def _omega_set_force(force: np.ndarray) -> bool:
        return False

    def _omega_enable_force(enabled: bool = True) -> bool:
        return False


# ═══════════════════════════════════════════════════════
# 常量
# ═══════════════════════════════════════════════════════

CTRL_FREQ = 200.0
STATUS_FREQ = 3.0
KEYBOARD_FREQ = 30.0
GRIPPER_FREQ = 20.0
TRAJECTORY_DECIMATION = 4

SIGN = np.array([-1.0, -1.0, 1.0])

DEFAULT_K_TRANS = 200.0
DEFAULT_K_ROT = 10.0
DEFAULT_DAMPING_RATIO = 1.0

DEFAULT_K_FB = 0.5
DEFAULT_DEADBAND = 0.3

DEFAULT_SCALE = 3.0

DEFAULT_GRIPPER_SPEED = 0.05

GRIPPER_SPEED = 0.1
GRIPPER_FORCE = 20.0
GRIPPER_MAX = 0.08
GRIPPER_HYSTERESIS = 0.01
GRIPPER_EPS_INNER = 0.005
GRIPPER_EPS_OUTER = 0.005

ROBOT_IP = "192.168.1.51"
COLLISION_TORQUE_NOMINAL = 30.0
COLLISION_FORCE_NOMINAL = 30.0

TRANSITION_STEPS = 30
TRANSITION_INTERVAL = 0.01

K_TRANS_MIN, K_TRANS_MAX = 10.0, 1000.0
K_ROT_MIN, K_ROT_MAX = 1.0, 50.0
DAMPING_MIN, DAMPING_MAX = 0.1, 5.0
K_FB_MIN, K_FB_MAX = 0.0, 2.0
DEADBAND_MIN, DEADBAND_MAX = 0.0, 2.0
SCALE_MIN, SCALE_MAX = 0.5, 15.0

SAVE_FILE = os.path.expanduser("~/teleop_experiment_params.json")

TRAJECTORY_CSV_HEADER = [
    "time_s", "loop_count",
    "mode", "object_label", "object_class",
    "omega_x", "omega_y", "omega_z",
    "omega_wrist1_deg", "omega_wrist2_deg", "omega_wrist3_deg",
    "omega_gripper_deg", "omega_button",
    "F_ext_x", "F_ext_y", "F_ext_z",
    "F_fb_x", "F_fb_y", "F_fb_z",
    "f_grip", "f_grip_filtered", "contact_detected",
    "K_trans", "K_rot", "damping_ratio", "deadband", "K_fb", "scale",
    "target_x", "target_y", "target_z",
    "actual_x", "actual_y", "actual_z",
    "pos_error_x", "pos_error_y", "pos_error_z",
    "gripper_width", "gripper_speed",
    "is_grasping",
]

# ═══════════════════════════════════════════════════════
# 实验参数表（软/中/硬三档）
# ═══════════════════════════════════════════════════════

OBJECT_PARAMS = {
    "soft": {
        "K_trans": 50, "K_rot": 5, "D_trans": 14.1, "D_rot": 4.5, "M": 0.5,
        "K_fb": 0.3, "deadband": 0.3,
        "damping_ratio": 0.8,
        "gripper_speed": 0.02, "gripper_force_limit": 8.0,
        "admittance_K": 150.0, "approach_speed": 0.05,
    },
    "medium": {
        "K_trans": 150, "K_rot": 10, "D_trans": 24.5, "D_rot": 6.3, "M": 1.0,
        "K_fb": 0.5, "deadband": 0.4,
        "damping_ratio": 1.0,
        "gripper_speed": 0.05, "gripper_force_limit": 20.0,
        "admittance_K": 150.0, "approach_speed": 0.05,
    },
    "hard": {
        "K_trans": 800, "K_rot": 50, "D_trans": 56.6, "D_rot": 14.1, "M": 2.0,
        "K_fb": 1.0, "deadband": 0.5,
        "damping_ratio": 1.2,
        "gripper_speed": 0.10, "gripper_force_limit": 60.0,
        "admittance_K": 150.0, "approach_speed": 0.05,
    },
}


# ═══════════════════════════════════════════════════════
# 预设手感场景
# ═══════════════════════════════════════════════════════

PRESETS = {
    "light": {
        "name": "✨ 灵动模式",
        "desc": "低阻尼 + 低刚度 — 操作轻盈灵动",
        "K_trans": 50.0, "K_rot": 5.0,
        "damping_ratio": 0.3, "K_fb": 0.2, "deadband": 0.2,
        "scale": 5.0,
    },
    "standard": {
        "name": "⚙️ 标准模式",
        "desc": "临界阻尼 + 适中刚度 — 平衡手感",
        "K_trans": 150.0, "K_rot": 10.0,
        "damping_ratio": 1.0, "K_fb": 0.5, "deadband": 0.3,
        "scale": 3.0,
    },
    "stable": {
        "name": "🪨 沉稳模式",
        "desc": "高阻尼 + 高刚度 — 适合精密定位",
        "K_trans": 250.0, "K_rot": 13.0,
        "damping_ratio": 2.0, "K_fb": 0.8, "deadband": 0.4,
        "scale": 2.0,
    },
    "rigid": {
        "name": "🧱 刚硬模式",
        "desc": "超高阻尼 + 超高刚度 — 刚性极强",
        "K_trans": 500.0, "K_rot": 20.0,
        "damping_ratio": 3.0, "K_fb": 1.0, "deadband": 0.5,
        "scale": 1.5,
    },
    "soft_obj": {
        "name": "🫧 软物体手感",
        "desc": "低力反馈 + 低刚度 — 模拟海绵/泡沫",
        "K_trans": 50.0, "K_rot": 5.0,
        "damping_ratio": 0.8, "K_fb": 0.2, "deadband": 0.3,
        "scale": 3.0,
    },
    "medium_obj": {
        "name": "📦 中物体手感",
        "desc": "中力反馈 + 中刚度 — 模拟纸盒/塑料瓶",
        "K_trans": 150.0, "K_rot": 10.0,
        "damping_ratio": 1.0, "K_fb": 0.5, "deadband": 0.4,
        "scale": 3.0,
    },
    "hard_obj": {
        "name": "🪨 硬物体手感",
        "desc": "强力反馈 + 高刚度 — 模拟金属/岩石",
        "K_trans": 250.0, "K_rot": 13.0,
        "damping_ratio": 1.2, "K_fb": 1.0, "deadband": 0.5,
        "scale": 3.0,
    },
}


# ═══════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════

def compute_trajectory_metrics(positions: np.ndarray, timestamps: np.ndarray) -> dict:
    if len(positions) < 2:
        return {"completion_time_s": 0, "path_length_m": 0,
                "avg_speed_m_s": 0, "max_speed_m_s": 0}

    duration = timestamps[-1] - timestamps[0]
    deltas = np.diff(positions, axis=0)
    segment_lengths = np.linalg.norm(deltas, axis=1)
    path_length = float(np.sum(segment_lengths))

    dt_segments = np.diff(timestamps)
    dt_segments = np.where(dt_segments < 1e-6, 1e-6, dt_segments)
    speeds = segment_lengths / dt_segments
    avg_speed = float(np.mean(speeds))
    max_speed = float(np.max(speeds))

    return {
        "completion_time_s": round(duration, 2),
        "path_length_m": round(path_length, 4),
        "avg_speed_m_s": round(avg_speed, 3),
        "max_speed_m_s": round(max_speed, 3),
    }


def compute_force_metrics(F_ext_hist: List[np.ndarray]) -> dict:
    if not F_ext_hist:
        return {"F_ext_peak_N": 0, "F_ext_mean_N": 0}
    F_ext_all = np.array(F_ext_hist)
    F_ext_norms = np.linalg.norm(F_ext_all[:, :3], axis=1)
    return {
        "F_ext_peak_N": round(float(np.max(F_ext_norms)), 2),
        "F_ext_mean_N": round(float(np.mean(F_ext_norms)), 2),
    }


def _safe_input_int(prompt: str, default: int, min_val: int = 0, max_val: int = 100) -> int:
    try:
        raw = input(prompt).strip()
        if not raw:
            return default
        val = int(raw)
        return max(min_val, min(val, max_val))
    except (ValueError, EOFError):
        return default


def print_scorecard(mode: str, object_label: str,
                    auto_metrics: dict,
                    dry_run: bool = False) -> dict:
    print()
    print("╔" + "═" * 55 + "╗")
    print(f"║               📊 实验评分卡{' ' * 27}║")
    print("╠" + "═" * 55 + "╣")
    mode_display = {"a": "固定阻抗", "b": "人工选阻抗",
                     "c": "自动YOLO+查表", "d": "YOLO只选夹爪速度"}
    mode_name = mode_display.get(mode, mode)
    print(f"║  模式:  mode {mode} ({mode_name}){' ' * (28 - len(mode_name))}║")
    emoji = {"soft": "🟢", "medium": "🟡", "hard": "🔴"}
    print(f"║  物体:  {object_label} {emoji.get(object_label, '⚪')}{' ' * 40}║")
    print("╠" + "═" * 55 + "╣")
    print(f"║  ─────── 自动指标 ───────{' ' * 23}║")
    print(f"║  ⏱  完成时间:      {auto_metrics.get('completion_time_s', 0):>6.2f} s{' ' * 24}║")
    print(f"║  📏 路径长度:      {auto_metrics.get('path_length_m', 0):>6.4f} m{' ' * 24}║")
    print(f"║  💪 外力峰值:      {auto_metrics.get('F_ext_peak_N', 0):>6.2f} N{' ' * 24}║")
    print("╠" + "═" * 55 + "╣")
    print(f"║  ─────── 人工评分 ───────{' ' * 23}║")
    print("╠" + "═" * 55 + "╣")

    if dry_run:
        print("║  成功率? (0=失败 / 1=成功): [模拟] 1        ║")
        print("║" + " " * 55 + "║")
        print("║  NASA-TLX (0-100): [模拟] 25              ║")
        print("║" + " " * 55 + "║")
        print("║  损伤评分 (0=无损伤 ~ 3=严重): [模拟] 0      ║")
        print("║" + " " * 55 + "║")
        print("║  变形量 (mm): [模拟] 0                    ║")
        print("║" + " " * 55 + "║")
        print("║  人工评分 (0=差 ~ 3=优秀): [模拟] 3        ║")
        print("╚" + "═" * 55 + "╝")
        return {"success": 1, "nasa_tlx": 25,
                "damage_score": 0, "deformation_mm": 0, "human_score": 3}
    else:
        success = _safe_input_int("║  成功率? (0=失败 / 1=成功): ", default=1, min_val=0, max_val=1)
        print("║" + " " * 55 + "║")
        nasa_tlx = _safe_input_int("║  NASA-TLX (0-100): ", default=50, min_val=0, max_val=100)
        print("║" + " " * 55 + "║")
        damage = _safe_input_int("║  损伤评分 (0=无损伤 ~ 3=严重): ", default=0, min_val=0, max_val=3)
        print("║" + " " * 55 + "║")
        deformation = _safe_input_int("║  变形量 (mm, 0=无变形): ", default=0, min_val=0, max_val=50)
        print("║" + " " * 55 + "║")
        human = _safe_input_int("║  人工评分 (0=差 ~ 3=优秀): ", default=0, min_val=0, max_val=3)
        print("╚" + "═" * 55 + "╝")
        return {
            "success": success,
            "nasa_tlx": nasa_tlx,
            "damage_score": damage,
            "deformation_mm": deformation,
            "human_score": human,
        }


def print_comparison_table(results: List[dict], object_label: str) -> None:
    print()
    print("╔" + "═" * 73 + "╗")
    title = f"📊 {object_label.upper()} 四种模式对比"
    print(f"║{title:^71}║")
    print("╠════╤════════╤════════╤══════════╤═══════╤══════╤══════╤══════╤══════╣")
    print("║模式│ 用时(s) │ 路径(m) │F_ext_max│成功率 │TLX   │损伤  │变形  │人工  ║")
    print("╠════╪════════╪════════╪══════════╪═══════╪══════╪══════╪══════╪══════╣")

    scores = []
    for r in results:
        manual = r.get("manual_scores", {})
        score = (manual.get("human_score", 0)
                 - manual.get("damage_score", 0)
                 - manual.get("deformation_mm", 0) / 10.0
                 - manual.get("nasa_tlx", 50) / 100.0)
        scores.append(score)
    best_idx = max(range(len(scores)), key=lambda i: scores[i]) if scores else 0

    for i, r in enumerate(results):
        mode_name = f"mode {r['mode']}"
        star = " ★" if i == best_idx else "  "
        auto = r.get("auto_metrics", {})
        manual = r.get("manual_scores", {})
        print(f"║ {mode_name}{star}│{auto.get('completion_time_s', 0):>7.2f} "
              f"│{auto.get('path_length_m', 0):>7.4f} "
              f"│{auto.get('F_ext_peak_N', 0):>8.2f} "
              f"│{manual.get('success', '-'):>5}  "
              f"│{manual.get('nasa_tlx', '-'):>4}  "
              f"│{manual.get('damage_score', '-'):>4}  "
              f"│{manual.get('deformation_mm', '-'):>4}  "
              f"│{manual.get('human_score', '-'):>4}    ║")
    print("╚════╧════════╧════════╧══════════╧═══════╧══════╧══════╧══════╧══════╝")
    best = results[best_idx]
    mode_display = {"a": "固定阻抗", "b": "人工选阻抗",
                     "c": "自动YOLO+查表", "d": "YOLO只选夹爪速度"}
    print(f"  🏆 mode {best['mode']} ({mode_display.get(best['mode'], '')}) 综合最优")
    print()


# ═══════════════════════════════════════════════════════
# 统一遥操作实验类
# ═══════════════════════════════════════════════════════

class UnifiedTeleopExperiment:

    def __init__(self, trajectory_dir: str = "data",
                 yolo_model: str = "yolo11n.pt",
                 physics_json: Optional[str] = None,
                 dry_run: bool = False):
        self._dry_run = dry_run
        self.running = False
        self._loop_count = 0
        self._mode = "a"
        self._object_label = "soft"
        self._object_class = "unknown"

        self._trajectory_dir = Path(trajectory_dir)
        self._trajectory_dir.mkdir(parents=True, exist_ok=True)
        self._recording = False
        self._trajectory_buffer: List[dict] = []
        self._trajectory_start_time = 0.0
        self._F_ext_history: List[np.ndarray] = []
        self._results: List[dict] = []
        self._per_object_results: Dict[str, List[dict]] = {
            "soft": [], "medium": [], "hard": [],
        }

        # ── 实验计数器（新增） ──
        self._trial_counter = {
            "soft": {"a": 0, "b": 0, "c": 0, "d": 0},
            "medium": {"a": 0, "b": 0, "c": 0, "d": 0},
            "hard": {"a": 0, "b": 0, "c": 0, "d": 0},
        }

        # ── 当前参数 ──
        self._K_trans_cur = DEFAULT_K_TRANS
        self._K_rot_cur = DEFAULT_K_ROT
        self._damping_ratio_cur = DEFAULT_DAMPING_RATIO
        self._K_fb_cur = DEFAULT_K_FB
        self._deadband_cur = DEFAULT_DEADBAND
        self._scale_cur = DEFAULT_SCALE
        self._gripper_speed = DEFAULT_GRIPPER_SPEED

        # ── 线程锁（新增） ──
        self._param_lock = threading.Lock()

        # ── 过渡状态 ──
        self._transition_active = False
        self._transition_stop = threading.Event()

        # ── Omega.7 状态 ──
        self._omega_home = np.zeros(3)
        self._omega_grip = 0.0
        self._omega_quat = np.array([1.0, 0.0, 0.0, 0.0])
        self._button_now = 0
        self._button_prev = 0

        # ── Franka/控制状态 ──
        self._init_pos = np.zeros(3)
        self._init_ori = np.zeros(4)
        self._virtual_ref = np.zeros(3)
        self._F_ext_current = np.zeros(6)
        self._F_haptic_current = np.zeros(3)
        self._f_grip_current = 0.0
        self._contact_detected = False
        self._is_grasping = False
        self._actual_pos = np.zeros(3)
        self._pos_error = np.zeros(3)

        # ── 夹爪 ──
        self._gripper_width = 0.08
        self._last_gripper_cmd = 0.08
        self._last_gripper_time = 0.0
        self._grip_min = -30.0
        self._grip_max = 0.0

        # ── 硬件句柄 ──
        self.panda = None
        self.gripper = None
        self.ctrl = None
        self.force_estimator = None
        self.grip_estimator = None

        # ── 视觉模块 ──
        self._yolo_model_path = yolo_model
        self._physics_json = physics_json
        self._yolo_process = None
        self._frame_queue = None
        self._result_queue = None
        self._latest_yolo_detection: Optional[dict] = None
        self._yolo_lock = threading.Lock()
        self._profile_from_yolo: Optional[PhysicsProfile] = None
        self._yolo_stop_event = None

        # ── YOLO 检测保持 ──
        self._last_seen_class = "N/A"
        self._last_seen_label = "unknown"
        self._last_seen_cycle = -999

        # ── 键盘输入 ──
        self._key_pressed = ""
        self._key_lock = threading.Lock()
        self._last_key_time = 0.0
        self._key_repeat_delay = 0.3
        self._key_repeat_rate = 0.12
        self._key_held = False
        self._key_first_repeat = True

        self.SAVE_FILE = SAVE_FILE
        self._object_results_for_object: List[dict] = []

    @staticmethod
    def mode_name(m: str) -> str:
        names = {
            "a": "固定阻抗", "b": "人工选阻抗",
            "c": "自动YOLO+查表", "d": "YOLO只选夹爪速度",
        }
        return names.get(m, "未知")

    # ═══════════════════════════════════════════
    # 初始化
    # ═══════════════════════════════════════════

    def initialize(self):
        print("=" * 60)
        print("  🚀 统一遥操作实验系统初始化")
        print("=" * 60)

        print("[1/6] 连接 Franka Panda...")
        try:
            self.panda = panda_py.Panda(ROBOT_IP)
            self.panda.recover()
            self.panda.set_default_behavior()
            self.panda.move_to_start()
            print("  ✅ Franka 就绪")
        except Exception as e:
            print(f"  ⚠️  无法连接 Franka: {e}")
            if not self._dry_run:
                self.panda = None

        print("[2/6] 初始化笛卡尔阻抗控制器...")
        if self.panda:
            K_init = self._build_stiffness(self._K_trans_cur, self._K_rot_cur)
            self.ctrl = controllers.CartesianImpedance(
                impedance=K_init,
                damping_ratio=self._damping_ratio_cur,
                nullspace_stiffness=0.5,
            )
            self.panda.start_controller(self.ctrl)
            state = self.panda.get_state()
            self._init_pos = np.array(
                [state.O_T_EE[12], state.O_T_EE[13], state.O_T_EE[14]],
                dtype=float,
            )
            self._init_ori = np.array(self.panda.get_orientation(), dtype=float)
            self._virtual_ref = self._init_pos.copy()
            self.ctrl.set_control(self._init_pos, self._init_ori)
            print(f"  ✅ 控制器就绪 | init_pos: {self._init_pos}")
        else:
            self._init_pos = np.array([0.5, 0.0, 0.3])
            self._virtual_ref = self._init_pos.copy()
            print("  ⚠️  无 Franka，使用虚拟位姿")

        print("[3/6] 初始化力估计器...")
        if self.panda:
            try:
                self.force_estimator = ForceEstimator(panda=self.panda)
                self.grip_estimator = GripForceEstimator()
                print("  ✅ 力估计器就绪")
            except Exception as e:
                print(f"  ⚠️  力估计器初始化失败: {e}")
        else:
            print("  ⚠️  无 Franka，跳过力估计器")

        print("[4/6] 连接 Omega.7 力反馈手柄...")
        try:
            if not _omega_open():
                raise RuntimeError("Omega.7 打开失败")
            raw_pos = np.zeros(3)
            _omega_get_position(raw_pos)
            self._omega_home = raw_pos.copy()
            wrist_deg = (ctypes.c_double * 3)()
            _omega_get_orientation(wrist_deg)
            self._omega_quat = np.array([wrist_deg[0], wrist_deg[1], wrist_deg[2], 0.0])
            _omega_enable_force(True)
            print(f"  ✅ Omega.7 就绪 | home: {self._omega_home}")
        except Exception as e:
            print(f"  ❌ Omega.7 连接失败: {e}")

        print("[5/6] 初始化夹爪...")
        try:
            if self.panda:
                self.gripper = libfranka.Gripper(ROBOT_IP)
                self.gripper.homing()
                print("  ✅ 夹爪就绪")
            else:
                print("  ⚠️  无 Franka，跳过夹爪")
        except Exception as e:
            print(f"  ⚠️  夹爪初始化失败: {e}")

        print("[6/6] 初始化 YOLO 视觉模块...")
        if self._dry_run:
            print("  ⚪ [dry-run] 跳过 YOLO")
        else:
            self._init_vision()

        print()
        print("=" * 60)
        print("  ✅ 初始化完成 — 开始实验 🎮")
        print("=" * 60 + "\n")

    def _build_stiffness(self, K_trans: float, K_rot: float) -> np.ndarray:
        K = np.zeros((6, 6))
        K[0, 0] = K[1, 1] = K[2, 2] = K_trans
        K[3, 3] = K[4, 4] = K[5, 5] = K_rot
        return K

    def _build_damping(self, K: np.ndarray, zeta: float) -> np.ndarray:
        D = np.zeros((6, 6))
        for i in range(6):
            D[i, i] = 2.0 * zeta * np.sqrt(K[i, i] + 1e-6)
        return D

    def _compute_damping_from_params(self) -> np.ndarray:
        K = self._build_stiffness(self._K_trans_cur, self._K_rot_cur)
        return self._build_damping(K, self._damping_ratio_cur)

    def _init_vision(self) -> bool:
        import multiprocessing as mp
        try:
            self._frame_queue = mp.Queue(maxsize=2)
            self._result_queue = mp.Queue(maxsize=2)
            self._yolo_stop_event = mp.Event()
            self._yolo_process = mp.Process(
                target=_yolo_process_main,
                args=(self._yolo_model_path, 0.5,
                      self._frame_queue, self._result_queue,
                      self._yolo_stop_event),
                daemon=True,
            )
            self._yolo_process.start()
            print(f"  ✅ YOLO 进程已启动 (PID={self._yolo_process.pid})")
            return True
        except Exception as e:
            print(f"  ⚠️  YOLO 启动失败: {e}")
            return False

    # ═══════════════════════════════════════════
    # 平滑参数过渡（带线程锁）
    # ═══════════════════════════════════════════

    def _smooth_transition(self, target_K_trans: float, target_K_rot: float,
                            target_zeta: float, duration: float = None):
        if duration is None:
            duration = TRANSITION_STEPS * TRANSITION_INTERVAL

        def _worker():
            try:
                steps = max(5, int(duration / (TRANSITION_INTERVAL + 1e-6)))
                with self._param_lock:
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
                    s = t * t * (3.0 - 2.0 * t)
                    K_mid = K_start + s * (K_target - K_start)
                    zeta_mid = zeta_start + s * (zeta_target - zeta_start)

                    with self._param_lock:
                        self._K_trans_cur = K_mid[0]
                        self._K_rot_cur = K_mid[1]
                        self._damping_ratio_cur = zeta_mid

                    if self.ctrl:
                        K_6x6 = self._build_stiffness(self._K_trans_cur, self._K_rot_cur)
                        self.ctrl.set_impedance(K_6x6)
                        try:
                            self.ctrl.set_damping_ratio(self._damping_ratio_cur)
                        except AttributeError:
                            pass

                    try:
                        time.sleep(TRANSITION_INTERVAL)
                    except KeyboardInterrupt:
                        break

                with self._param_lock:
                    self._K_trans_cur = target_K_trans
                    self._K_rot_cur = target_K_rot
                    self._damping_ratio_cur = target_zeta
                if self.ctrl:
                    K_6x6 = self._build_stiffness(self._K_trans_cur, self._K_rot_cur)
                    self.ctrl.set_impedance(K_6x6)
                    try:
                        self.ctrl.set_damping_ratio(self._damping_ratio_cur)
                    except AttributeError:
                        pass
            except Exception as e:
                import traceback
                print(f"\n[❌ 过渡线程异常] {e}")
                traceback.print_exc()
            finally:
                self._transition_active = False

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    def _change_param(self, name: str, delta: float):
        limits = {
            "damping_ratio": (DAMPING_MIN, DAMPING_MAX),
            "K_trans": (K_TRANS_MIN, K_TRANS_MAX),
            "K_rot": (K_ROT_MIN, K_ROT_MAX),
            "K_fb": (K_FB_MIN, K_FB_MAX),
            "deadband": (DEADBAND_MIN, DEADBAND_MAX),
            "scale": (SCALE_MIN, SCALE_MAX),
        }
        lower, upper = limits.get(name, (0, 1e6))
        with self._param_lock:
            current = getattr(self, f"_{name}_cur", 0.0)
            before = current
            current = max(lower, min(upper, current + delta))
            setattr(self, f"_{name}_cur", current)

        if name == "damping_ratio" and self.ctrl:
            try:
                self.ctrl.set_damping_ratio(self._damping_ratio_cur)
            except AttributeError:
                pass

        if name in ("K_trans", "K_rot") and self.ctrl:
            K = self._build_stiffness(self._K_trans_cur, self._K_rot_cur)
            self.ctrl.set_impedance(K)

        self._print_param_change(name, before, current)

    def _set_preset(self, preset_name: str):
        if preset_name not in PRESETS:
            return
        p = PRESETS[preset_name]
        print(f"\n  🎯 切换 → {p['name']}")
        print(f"     {p['desc']}")
        self._smooth_transition(p["K_trans"], p["K_rot"], p["damping_ratio"])
        with self._param_lock:
            self._K_fb_cur = p["K_fb"]
            self._deadband_cur = p["deadband"]
            self._scale_cur = p["scale"]

    def _print_param_change(self, name: str, before: float, after: float):
        labels = {
            "damping_ratio": "阻尼比 ζ",
            "K_trans": "刚度 K_trans",
            "K_rot": "旋转刚度 K_rot",
            "K_fb": "力反馈增益 K_fb",
            "deadband": "死区 deadband",
            "scale": "位置比例 scale",
        }
        label = labels.get(name, name)
        if after != before:
            arrow = "↑" if after > before else "↓"
            print(f"  {label}: {before:.3f} {arrow} {after:.3f}")

    # ═══════════════════════════════════════════
    # 模式管理（关键修订）
    # ═══════════════════════════════════════════

    def _apply_mode_params(self, mode: str):
        """根据模式设置控制参数（修订版：B组改为查表，C/D组变化检测）"""
        if mode == "a":
            # 固定阻抗：所有物体使用同一套默认参数
            target_K = DEFAULT_K_TRANS
            target_Kr = DEFAULT_K_ROT
            target_zeta = DEFAULT_DAMPING_RATIO
            with self._param_lock:
                self._deadband_cur = DEFAULT_DEADBAND
                self._K_fb_cur = DEFAULT_K_FB
                self._gripper_speed = DEFAULT_GRIPPER_SPEED

        elif mode == "b":
            # 人工选阻抗：根据当前标记的物体类型查表应用参数
            if self._profile_from_yolo and hasattr(self._profile_from_yolo, 'label'):
                p = self._profile_from_yolo
                target_K = getattr(p, 'K_trans', DEFAULT_K_TRANS)
                target_Kr = getattr(p, 'K_rot', DEFAULT_K_ROT)
                target_zeta = getattr(p, 'damping_ratio', DEFAULT_DAMPING_RATIO)
                with self._param_lock:
                    self._deadband_cur = getattr(p, 'deadband', DEFAULT_DEADBAND)
                    self._K_fb_cur = getattr(p, 'K_fb', DEFAULT_K_FB)
                    self._gripper_speed = getattr(p, 'gripper_speed', DEFAULT_GRIPPER_SPEED)
            else:
                # 未选择时默认用中等
                params = OBJECT_PARAMS["medium"]
                target_K = params["K_trans"]
                target_Kr = params["K_rot"]
                target_zeta = params.get("damping_ratio", DEFAULT_DAMPING_RATIO)
                with self._param_lock:
                    self._deadband_cur = params["deadband"]
                    self._K_fb_cur = params["K_fb"]
                    self._gripper_speed = params["gripper_speed"]

        elif mode == "c":
            # 自动YOLO+查表：根据 YOLO 识别的物体类型查表
            if self._profile_from_yolo:
                p = self._profile_from_yolo
                target_K = getattr(p, 'K_trans', DEFAULT_K_TRANS)
                target_Kr = getattr(p, 'K_rot', DEFAULT_K_ROT)
                target_zeta = getattr(p, 'damping_ratio', DEFAULT_DAMPING_RATIO)
                with self._param_lock:
                    self._deadband_cur = getattr(p, 'deadband', DEFAULT_DEADBAND)
                    self._K_fb_cur = getattr(p, 'K_fb', DEFAULT_K_FB)
                    self._gripper_speed = getattr(p, 'gripper_speed', DEFAULT_GRIPPER_SPEED)
            else:
                params = OBJECT_PARAMS.get(self._object_label, OBJECT_PARAMS["medium"])
                target_K = params["K_trans"]
                target_Kr = params["K_rot"]
                target_zeta = params.get("damping_ratio", DEFAULT_DAMPING_RATIO)
                with self._param_lock:
                    self._deadband_cur = params["deadband"]
                    self._K_fb_cur = params["K_fb"]
                    self._gripper_speed = params["gripper_speed"]

        elif mode == "d":
            # YOLO只选夹爪速度：阻抗固定，仅夹爪速度随物体变化
            target_K = DEFAULT_K_TRANS
            target_Kr = DEFAULT_K_ROT
            target_zeta = DEFAULT_DAMPING_RATIO
            with self._param_lock:
                self._deadband_cur = DEFAULT_DEADBAND
                self._K_fb_cur = DEFAULT_K_FB
            if self._profile_from_yolo:
                self._gripper_speed = getattr(self._profile_from_yolo, 'gripper_speed', DEFAULT_GRIPPER_SPEED)
            else:
                params = OBJECT_PARAMS.get(self._object_label, OBJECT_PARAMS["medium"])
                self._gripper_speed = params["gripper_speed"]

        else:
            return

        # 平滑过渡到目标参数
        self._smooth_transition(target_K, target_Kr, target_zeta)

        print(f"  [MODE {mode}] K_trans={target_K:.0f}, "
              f"K_rot={target_Kr:.1f}, "
              f"ζ={target_zeta:.2f}, "
              f"deadband={self._deadband_cur:.2f}, "
              f"K_fb={self._K_fb_cur:.2f}, "
              f"gripper_speed={self._gripper_speed:.3f}, "
              f"scale={self._scale_cur:.1f}")

    def _switch_mode(self, new_mode: str):
        """切换模式（修订版：不再自动保存/自动开始录制）"""
        if new_mode == self._mode:
            print(f"  ℹ️  已在 mode {new_mode}")
            return

        # 如果正在录制，提示先保存
        if self._recording and self._trajectory_buffer:
            print(f"\n  ⚠️  请先按 r 保存当前 mode {self._mode} 的数据，再切换模式")
            return

        self._mode = new_mode
        self._apply_mode_params(new_mode)
        print(f"  🎮 切换到 mode {new_mode} ({self.mode_name(new_mode)})")
        print(f"     当前物体: {self._object_label} | 按 r 开始录制")

    # ═══════════════════════════════════════════
    # 参数保存/加载
    # ═══════════════════════════════════════════

    def _save_params(self):
        with self._param_lock:
            params = {
                "K_trans": self._K_trans_cur,
                "K_rot": self._K_rot_cur,
                "damping_ratio": self._damping_ratio_cur,
                "K_fb": self._K_fb_cur,
                "deadband": self._deadband_cur,
                "scale": self._scale_cur,
                "gripper_speed": self._gripper_speed,
            }
        try:
            with open(self.SAVE_FILE, "w") as f:
                json.dump(params, f, indent=2)
            print(f"  💾 参数已保存到 {self.SAVE_FILE}")
        except Exception as e:
            print(f"  ❌ 保存失败: {e}")

    def _load_params(self):
        try:
            with open(self.SAVE_FILE, "r") as f:
                params = json.load(f)
        except Exception as e:
            print(f"  ❌ 加载失败: {e}")
            return

        with self._param_lock:
            for key, val in params.items():
                attr = f"_{key}_cur"
                if hasattr(self, attr):
                    setattr(self, attr, val)
                elif key == "gripper_speed":
                    self._gripper_speed = val

        if self.ctrl:
            K = self._build_stiffness(self._K_trans_cur, self._K_rot_cur)
            self.ctrl.set_impedance(K)
            try:
                self.ctrl.set_damping_ratio(self._damping_ratio_cur)
            except AttributeError:
                pass

        print(f"  📂 已从 {self.SAVE_FILE} 加载参数")
        for key, val in params.items():
            print(f"     {key}: {val}")

    # ═══════════════════════════════════════════
    # 轨迹记录
    # ═══════════════════════════════════════════

    def _record_sample(self, raw_pos, quat, gripper_deg, button):
        self._trajectory_buffer.append({
            "time": time.time() - self._trajectory_start_time,
            "loop": self._loop_count,
            "mode": self._mode,
            "object_label": self._object_label,
            "object_class": self._object_class,
            "x": raw_pos[0], "y": raw_pos[1], "z": raw_pos[2],
            "qw": quat[0], "qx": quat[1], "qy": quat[2], "qz": quat[3],
            "gripper_deg": gripper_deg,
            "button": button,
            "F_ext_x": self._F_ext_current[0],
            "F_ext_y": self._F_ext_current[1],
            "F_ext_z": self._F_ext_current[2],
            "F_fb_x": self._F_haptic_current[0],
            "F_fb_y": self._F_haptic_current[1],
            "F_fb_z": self._F_haptic_current[2],
            "f_grip": self._f_grip_current,
            "f_grip_filtered": (self.grip_estimator.f_grip
                                if self.grip_estimator else 0),
            "contact": self._contact_detected,
            "K_trans": self._K_trans_cur,
            "K_rot": self._K_rot_cur,
            "damping_ratio": self._damping_ratio_cur,
            "deadband": self._deadband_cur,
            "K_fb": self._K_fb_cur,
            "scale": self._scale_cur,
            "target_x": self._virtual_ref[0],
            "target_y": self._virtual_ref[1],
            "target_z": self._virtual_ref[2],
            "actual_x": self._actual_pos[0],
            "actual_y": self._actual_pos[1],
            "actual_z": self._actual_pos[2],
            "pos_error_x": self._pos_error[0],
            "pos_error_y": self._pos_error[1],
            "pos_error_z": self._pos_error[2],
            "gripper_width": self._gripper_width,
            "gripper_speed": self._gripper_speed,
            "is_grasping": int(self._is_grasping),
        })

    def _save_current_recording(self):
        """保存当前轨迹 + 自动指标 + 弹出评分卡（修订版：增加计数器）"""
        if not self._trajectory_buffer or len(self._trajectory_buffer) < 5:
            print("  ⚠️  轨迹数据不足，跳过保存")
            return

        # ── 保存 CSV ──
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = f"trajectory_{timestamp}_{self._mode}_{self._object_label}.csv"
        fpath = self._trajectory_dir / fname

        with open(fpath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(TRAJECTORY_CSV_HEADER)
            for row in self._trajectory_buffer:
                writer.writerow([
                    f"{row['time']:.4f}", row["loop"],
                    row["mode"], row["object_label"], row["object_class"],
                    f"{row['x']:.6f}", f"{row['y']:.6f}", f"{row['z']:.6f}",
                    f"{row['qw']:.6f}", f"{row['qx']:.6f}", f"{row['qy']:.6f}",
                    f"{row['gripper_deg']:.2f}", row["button"],
                    f"{row['F_ext_x']:.6f}", f"{row['F_ext_y']:.6f}",
                    f"{row['F_ext_z']:.6f}",
                    f"{row['F_fb_x']:.6f}", f"{row['F_fb_y']:.6f}",
                    f"{row['F_fb_z']:.6f}",
                    f"{row['f_grip']:.6f}", f"{row['f_grip_filtered']:.6f}",
                    row["contact"],
                    f"{row['K_trans']:.1f}", f"{row['K_rot']:.1f}",
                    f"{row['damping_ratio']:.2f}",
                    f"{row['deadband']:.3f}", f"{row['K_fb']:.3f}",
                    f"{row['scale']:.2f}",
                    f"{row['target_x']:.6f}", f"{row['target_y']:.6f}",
                    f"{row['target_z']:.6f}",
                    f"{row['actual_x']:.6f}", f"{row['actual_y']:.6f}",
                    f"{row['actual_z']:.6f}",
                    f"{row['pos_error_x']:.6f}", f"{row['pos_error_y']:.6f}",
                    f"{row['pos_error_z']:.6f}",
                    f"{row['gripper_width']:.4f}", f"{row['gripper_speed']:.3f}",
                    row["is_grasping"],
                ])

        print(f"\n  💾 轨迹已保存: {fpath} ({len(self._trajectory_buffer)} 点)")

        # ── 计算自动指标 ──
        positions = np.array([
            [r["x"], r["y"], r["z"]] for r in self._trajectory_buffer
        ])
        timestamps_arr = np.array([
            r["time"] for r in self._trajectory_buffer
        ])
        auto_metrics = compute_trajectory_metrics(positions, timestamps_arr)
        force_metrics = compute_force_metrics(self._F_ext_history)
        auto_metrics.update(force_metrics)

        # ── 保存指标到文件 ──
        metrics_path = fpath.with_name(fpath.stem + "_metrics.txt")
        with open(metrics_path, "w") as f:
            f.write(f"Mode: {self._mode}\n")
            f.write(f"Object: {self._object_label}\n")
            f.write(f"Duration: {auto_metrics['completion_time_s']:.2f}s\n")
            f.write(f"Path Length: {auto_metrics['path_length_m']:.4f}m\n")
            f.write(f"Avg Speed: {auto_metrics['avg_speed_m_s']:.3f}m/s\n")
            f.write(f"Max Speed: {auto_metrics['max_speed_m_s']:.3f}m/s\n")
            f.write(f"F_ext Peak: {auto_metrics['F_ext_peak_N']:.2f}N\n")
            f.write(f"F_ext Mean: {auto_metrics['F_ext_mean_N']:.2f}N\n")

        # ── 评分卡 ──
        manual_scores = print_scorecard(
            self._mode, self._object_label,
            auto_metrics, dry_run=self._dry_run,
        )

        # ── 记录结果 ──
        result = {
            "mode": self._mode,
            "object_label": self._object_label,
            "object_class": self._object_class,
            "auto_metrics": auto_metrics,
            "manual_scores": manual_scores,
            "trajectory_file": str(fpath),
            "timestamp": timestamp,
        }
        self._results.append(result)
        self._per_object_results[self._object_label].append(result)

        # ── 计数器更新（新增） ──
        self._trial_counter[self._object_label][self._mode] += 1
        count = self._trial_counter[self._object_label][self._mode]
        print(f"  📊 {self._object_label} / mode {self._mode} : 第 {count}/10 次")
        if count >= 10:
            print(f"  🎉 {self._object_label} / mode {self._mode} 已完成10次！")

    # ═══════════════════════════════════════════
    # 键盘监听
    # ═══════════════════════════════════════════

    def _keyboard_loop(self):
        import sys as _sys
        import select as _sel
        import tty as _tty
        import termios as _termios

        try:
            fd = _sys.stdin.fileno()
            old = _termios.tcgetattr(fd)
            _tty.setraw(_sys.stdin.fileno())
            try:
                while self.running:
                    r, _, _ = _sel.select([_sys.stdin], [], [], 1.0 / 30.0)
                    if not r:
                        continue
                    ch = _sys.stdin.read(1)
                    with self._key_lock:
                        if ch == '\x1b':
                            r2, _, _ = _sel.select([_sys.stdin], [], [], 0.02)
                            if r2:
                                seq = ch + _sys.stdin.read(2)
                                self._key_pressed = seq
                            else:
                                self._key_pressed = ch
                        else:
                            self._key_pressed = ch
            finally:
                _termios.tcsetattr(fd, _termios.TCSADRAIN, old)
        except Exception:
            while self.running:
                try:
                    ch = input()
                    with self._key_lock:
                        self._key_pressed = ch
                except (EOFError, KeyboardInterrupt):
                    break

    def _process_keyboard(self):
        key = ""
        with self._key_lock:
            if self._key_pressed:
                key = self._key_pressed
                self._key_pressed = ""

        if not key:
            return

        # ── 全局参数调节（修订：避免与 mode b 的 1/2/3 冲突） ──
        if key == "!":
            self._change_param("damping_ratio", -0.1)
        elif key == "@":
            self._change_param("damping_ratio", 0.1)
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

        # ── 模式切换 ──
        elif key in ("a",):
            self._switch_mode("a")
        elif key in ("b",):
            self._switch_mode("b")
        elif key in ("c",):
            self._switch_mode("c")
        elif key in ("d",):
            self._switch_mode("d")

        # ── 物体标记 ──
        elif key == "s":
            self._object_label = "soft"
            self._object_class = "soft_generic"
            self._profile_from_yolo = PhysicsProfile.from_dict(OBJECT_PARAMS["soft"])
            print(f"\n  🏷️  物体标记为: soft (软物体)")
            if self._mode in ("b", "c", "d"):
                self._apply_mode_params(self._mode)

        elif key == "m":
            self._object_label = "medium"
            self._object_class = "medium_generic"
            self._profile_from_yolo = PhysicsProfile.from_dict(OBJECT_PARAMS["medium"])
            print(f"\n  🏷️  物体标记为: medium (中等物体)")
            if self._mode in ("b", "c", "d"):
                self._apply_mode_params(self._mode)

        elif key == "h":
            self._object_label = "hard"
            self._object_class = "hard_generic"
            self._profile_from_yolo = PhysicsProfile.from_dict(OBJECT_PARAMS["hard"])
            print(f"\n  🏷️  物体标记为: hard (硬物体)")
            if self._mode in ("b", "c", "d"):
                self._apply_mode_params(self._mode)

        # ── 录制控制（修订：手动 r 键控制开始/停止） ──
        elif key == "r":
            if not self._recording:
                self._recording = True
                self._trajectory_buffer = []
                self._F_ext_history = []
                self._trajectory_start_time = time.time()
                print(f"\n  📝 开始录制 | mode={self._mode}, object={self._object_label}")
            else:
                self._recording = False
                self._save_current_recording()
                print("  📝 录制停止，数据已保存")

        # ── mode b 参数调节（修订：1/2/3 改为选物体类型） ──
        elif key == "1":
            if self._mode == "b":
                self._object_label = "soft"
                self._profile_from_yolo = PhysicsProfile.from_dict(OBJECT_PARAMS["soft"])
                self._apply_mode_params("b")
                print("  [mode b] 人工选择: 软物体参数 (K=50, 慢速, 低力)")
            else:
                print("  ℹ️  数字 1 仅在 mode b 下用于选择软物体")
        elif key == "2":
            if self._mode == "b":
                self._object_label = "medium"
                self._profile_from_yolo = PhysicsProfile.from_dict(OBJECT_PARAMS["medium"])
                self._apply_mode_params("b")
                print("  [mode b] 人工选择: 中等物体参数 (K=150, 中速, 中力)")
            else:
                print("  ℹ️  数字 2 仅在 mode b 下用于选择中等物体")
        elif key == "3":
            if self._mode == "b":
                self._object_label = "hard"
                self._profile_from_yolo = PhysicsProfile.from_dict(OBJECT_PARAMS["hard"])
                self._apply_mode_params("b")
                print("  [mode b] 人工选择: 硬物体参数 (K=800, 快速, 大力)")
            else:
                print("  ℹ️  数字 3 仅在 mode b 下用于选择硬物体")
        elif key == "i":
            if self._mode == "b":
                self._change_param("K_trans", 10.0)
        elif key == "k":
            if self._mode == "b":
                self._change_param("K_trans", -10.0)
        elif key == "j":
            if self._mode == "b":
                self._change_param("deadband", -0.05)
        elif key == "l":
            if self._mode == "b":
                self._change_param("deadband", 0.05)
        elif key == "[":
            if self._mode == "b":
                self._gripper_speed = max(0.01, round(self._gripper_speed - 0.01, 3))
                print(f"  [mode b] gripper_speed -0.01 → {self._gripper_speed:.3f}")
        elif key == "]":
            if self._mode == "b":
                self._gripper_speed = min(0.15, round(self._gripper_speed + 0.01, 3))
                print(f"  [mode b] gripper_speed +0.01 → {self._gripper_speed:.3f}")

        # 方向键
        elif key == '\x1b[A':
            if self._mode == "b":
                self._change_param("K_trans", 10.0)
        elif key == '\x1b[B':
            if self._mode == "b":
                self._change_param("K_trans", -10.0)
        elif key == '\x1b[D':
            if self._mode == "b":
                self._change_param("deadband", -0.05)
        elif key == '\x1b[C':
            if self._mode == "b":
                self._change_param("deadband", 0.05)

        # ── 预设手感场景 ──
        elif key == "z":
            self._set_preset("soft_obj")
        elif key == "x":
            self._set_preset("medium_obj")
        elif key == "#":
            self._set_preset("stable")
        elif key == "$":
            self._set_preset("rigid")

        # ── 保存/加载 ──
        elif key == "v":
            self._save_params()
        elif key == "n":
            self._load_params()

        # ── 退出 ──
        elif key == "q":
            if self._recording:
                self._recording = False
                self._save_current_recording()
            self._print_final_summary()
            print("\n  正在退出...")
            self.running = False

    # ═══════════════════════════════════════════
    # 夹爪控制
    # ═══════════════════════════════════════════

    def _update_gripper(self):
        omega_norm = np.clip((self._omega_grip - self._grip_min)
                             / (self._grip_max - self._grip_min), 0, 1)
        target_width = (1.0 - omega_norm) * GRIPPER_MAX

        if self._button_now:
            self._is_grasping = True
        elif omega_norm > 0.7:
            self._is_grasping = False

        if self.gripper:
            self._gripper_cmd_thread(target_width)
        self._gripper_width = target_width

    def _gripper_cmd_thread(self, width: float):
        if abs(width - self._last_gripper_cmd) < GRIPPER_HYSTERESIS:
            return
        self._last_gripper_cmd = width
        try:
            self.gripper.stop()
            time.sleep(0.02)
            with self._param_lock:
                speed = self._gripper_speed
            self.gripper.move(width, speed=speed)
        except Exception:
            pass

    # ═══════════════════════════════════════════
    # YOLO 检测轮询（修订：只在类别变化时更新参数）
    # ═══════════════════════════════════════════

    def _poll_yolo_result(self):
        if not hasattr(self, "_result_queue") or self._result_queue is None:
            return
        try:
            det = self._result_queue.get_nowait()
            if det is not None:
                new_label = det["profile"].label
                # 只在类别变化或首次检测时更新参数（避免 200Hz 震荡）
                if new_label != self._object_label or self._last_seen_cycle == -999:
                    self._object_label = new_label
                    self._object_class = det["class"]

                    if self._mode == "c":
                        self._profile_from_yolo = det["profile"]
                        self._apply_mode_params(self._mode)
                    elif self._mode == "d":
                        self._profile_from_yolo = det["profile"]
                        self._apply_mode_params(self._mode)

                # 更新视觉信息（不触发参数变化）
                self._last_seen_class = det["class"]
                self._last_seen_label = new_label
                self._last_seen_cycle = self._loop_count

        except queue.Empty:
            pass

    # ═══════════════════════════════════════════
    # 主控制循环
    # ═══════════════════════════════════════════

    def run(self):
        self.running = True

        dt = 1.0 / CTRL_FREQ
        dt_status = 1.0 / STATUS_FREQ
        dt_keyboard = 1.0 / KEYBOARD_FREQ
        dt_gripper = 1.0 / GRIPPER_FREQ

        last_status_time = 0.0
        last_kb_time = 0.0
        last_gripper_time = 0.0

        kb_thread = threading.Thread(target=self._keyboard_loop, daemon=True)
        kb_thread.start()

        self._print_menu()

        try:
            while self.running:
                t_start = time.perf_counter()
                now = time.time()

                # ── 读取当前参数（加锁） ──
                with self._param_lock:
                    K_fb = self._K_fb_cur
                    deadband = self._deadband_cur
                    scale = self._scale_cur
                    gripper_speed = self._gripper_speed

                # ── 1. 读 Omega.7 ──
                raw_pos = np.zeros(3)
                _omega_get_position(raw_pos)

                wrist_deg = (ctypes.c_double * 3)()
                _omega_get_orientation(wrist_deg)

                gripper_angle = ctypes.c_double()
                _omega_get_gripper_angle(gripper_angle)
                self._omega_grip = gripper_angle.value if hasattr(gripper_angle, 'value') else 0.0
                self._button_now = _omega_get_button(0)

                # ── 2. 读取 Franka 状态 ──
                if self.panda:
                    try:
                        state = self.panda.get_state()
                        tau_ext = np.array(state.tau_ext_hat_filtered, dtype=float)
                        self._actual_pos = np.array(
                            [state.O_T_EE[12], state.O_T_EE[13], state.O_T_EE[14]],
                            dtype=float,
                        )
                        if self.force_estimator:
                            self._F_ext_current = self.force_estimator.update(state)
                        if self.grip_estimator:
                            self._f_grip_current = self.grip_estimator.update(
                                tau_ext, self._gripper_width,
                            )
                            self._contact_detected = self.grip_estimator.contact_detected
                    except Exception:
                        pass

                # ── 3. 力反馈计算 ──
                F_ext_xyz = self._F_ext_current[:3]
                F_scaled = F_ext_xyz * K_fb
                F_haptic = np.where(
                    np.abs(F_scaled) > deadband,
                    np.sign(F_scaled) * (np.abs(F_scaled) - deadband),
                    0.0,
                )
                self._F_haptic_current = F_haptic
                if len(F_haptic) == 3:
                    _omega_set_force(F_haptic)

                # ── 4. 位姿映射 ──
                delta = raw_pos - self._omega_home
                target_pos = self._virtual_ref + delta * scale * SIGN

                # ── 5. 发送到 Franka ──
                if self.ctrl:
                    self.ctrl.set_control(target_pos, self._init_ori)

                self._pos_error = target_pos - self._actual_pos

                # ── 6. 轨迹记录 ──
                if self._recording:
                    if self._loop_count % TRAJECTORY_DECIMATION == 0:
                        self._record_sample(
                            raw_pos, [wrist_deg[0], wrist_deg[1], wrist_deg[2], 0.0],
                            self._omega_grip, self._button_now,
                        )
                        self._F_ext_history.append(self._F_ext_current.copy())

                # ── 7. YOLO 结果轮询 ──
                self._poll_yolo_result()

                # ── 8. 夹爪控制 (降频) ──
                if (now - last_gripper_time) >= dt_gripper:
                    self._update_gripper()
                    last_gripper_time = now

                # ── 9. 键盘处理 (降频) ──
                if (now - last_kb_time) >= dt_keyboard:
                    self._process_keyboard()
                    last_kb_time = now

                # ── 10. 状态打印 (降频) ──
                self._loop_count += 1
                if (now - last_status_time) >= dt_status:
                    self._print_status()
                    last_status_time = now

                # ── 控制周期同步 ──
                elapsed = time.perf_counter() - t_start
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
            self._shutdown()

    # ═══════════════════════════════════════════
    # 状态打印
    # ═══════════════════════════════════════════

    def _print_status(self):
        obj_str = f"{self._object_label}[{self._last_seen_class}]"
        with self._param_lock:
            K_trans = self._K_trans_cur
            K_rot = self._K_rot_cur
            zeta = self._damping_ratio_cur
            K_fb = self._K_fb_cur
            db = self._deadband_cur
            scale = self._scale_cur
            gripper_speed = self._gripper_speed

        status = (f"[{self._loop_count // int(CTRL_FREQ)}s] "
                  f"mode={self._mode} "
                  f"obj={obj_str} "
                  f"ζ={zeta:.2f} "
                  f"Kt={K_trans:.0f} "
                  f"Kr={K_rot:.1f} "
                  f"Kfb={K_fb:.2f} "
                  f"db={db:.2f} "
                  f"s={scale:.1f} "
                  f"grip={gripper_speed:.3f} "
                  f"|F_ext|={np.linalg.norm(self._F_ext_current[:3]):.2f} "
                  f"rec={'🔴' if self._recording else '⚫'}"
                  f"btn={'🟢' if self._button_now else '⚪'}")
        if self._transition_active:
            status += " [🌀 过渡中]"
        print(status)

    def _print_menu(self):
        print()
        print("=" * 65)
        print("  ⌨️  键盘快捷键")
        print("=" * 65)
        print("  ┌──────────┬──────────────────────────────────────┐")
        print("  │ a/b/c/d  │ 切换实验模式 (固定/人工/自动/YOLO速度) │")
        print("  │ s/m/h    │ 标记软/中/硬物体                      │")
        print("  │ r        │ 开始/停止录制 + 评分卡                │")
        print("  ├──────────┼──────────────────────────────────────┤")
        print("  │ mode b:  │ 人工选择阻抗参数（按数字键）           │")
        print("  │   1      │ 软物体 (K=50, 慢速, 低力)              │")
        print("  │   2      │ 中等物体 (K=150, 中速, 中力)           │")
        print("  │   3      │ 硬物体 (K=800, 快速, 大力)             │")
        print("  │ i/k (↑/↓)│ K_trans +/- (10 N/m)                  │")
        print("  │ j/l (←/→)│ deadband +/- (0.05 N)                 │")
        print("  │ [/]      │ gripper_speed +/-                     │")
        print("  ├──────────┼──────────────────────────────────────┤")
        print("  │ 全局:    │                                      │")
        print("  │ !/@      │ 阻尼比 ζ -/+ (步长 0.1)               │")
        print("  │ 5/6      │ 力反馈增益 -/+ (步长 0.05)             │")
        print("  │ 7/8      │ 死区 -/+ (步长 0.05 N)                │")
        print("  │ 9/0      │ 位置比例 -/+ (步长 0.5)               │")
        print("  ├──────────┼──────────────────────────────────────┤")
        print("  │ z/x      │ 软/中物体手感预设                     │")
        print("  │ v/n      │ 保存/加载参数                         │")
        print("  │ q        │ 退出 (自动汇总)                       │")
        print("  └──────────┴──────────────────────────────────────┘")
        print("=" * 65)

    # ═══════════════════════════════════════════
    # 最终汇总（修订：增加统计量输出）
    # ═══════════════════════════════════════════

    def _print_final_summary(self):
        print("\n" + "=" * 70)
        print("  📊 最终实验汇总")
        print("=" * 70)

        for obj_label in ["soft", "medium", "hard"]:
            results = self._per_object_results.get(obj_label, [])
            if results:
                print_comparison_table(results, obj_label)

        # ── 统计汇总（新增） ──
        print("\n" + "=" * 70)
        print("  📈 统计分析")
        print("=" * 70)
        try:
            import statistics
            for obj_label in ["soft", "medium", "hard"]:
                results = self._per_object_results.get(obj_label, [])
                if not results:
                    continue

                print(f"\n  【{obj_label.upper()}】")
                for mode in ["a", "b", "c", "d"]:
                    mode_results = [r for r in results if r["mode"] == mode]
                    if not mode_results:
                        continue

                    times = [r["auto_metrics"]["completion_time_s"] for r in mode_results]
                    paths = [r["auto_metrics"]["path_length_m"] for r in mode_results]
                    successes = [r["manual_scores"]["success"] for r in mode_results]
                    tlxs = [r["manual_scores"]["nasa_tlx"] for r in mode_results]
                    damages = [r["manual_scores"].get("damage_score", 0) for r in mode_results]
                    deformations = [r["manual_scores"].get("deformation_mm", 0) for r in mode_results]

                    n = len(mode_results)
                    print(f"    Mode {mode} ({self.mode_name(mode)}) — n={n}/10")
                    print(f"      成功率:  {sum(successes)}/{n} = {sum(successes)/n*100:.1f}%")
                    if n > 1:
                        print(f"      时间:    {statistics.mean(times):.2f} ± {statistics.stdev(times):.2f} s")
                        print(f"      路径:    {statistics.mean(paths):.4f} ± {statistics.stdev(paths):.4f} m")
                        print(f"      NASA-TLX:{statistics.mean(tlxs):.1f} ± {statistics.stdev(tlxs):.1f}")
                        print(f"      损伤:    {statistics.mean(damages):.2f} ± {statistics.stdev(damages):.2f}")
                        print(f"      变形:    {statistics.mean(deformations):.2f} ± {statistics.stdev(deformations):.2f} mm")
                    else:
                        print(f"      时间:    {times[0]:.2f} s")
                        print(f"      路径:    {paths[0]:.4f} m")
                        print(f"      NASA-TLX:{tlxs[0]:.1f}")
                        print(f"      损伤:    {damages[0]:.2f}")
                        print(f"      变形:    {deformations[0]:.2f} mm")
        except Exception as e:
            print(f"  统计计算出错: {e}")

        # 保存汇总到 JSON
        summary_path = self._trajectory_dir / "experiment_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump({
                "total_trials": len(self._results),
                "trial_counter": self._trial_counter,
                "timestamp": datetime.now().isoformat(),
                "results": self._results,
            }, f, ensure_ascii=False, indent=2)
        print(f"\n  📁 汇总已保存: {summary_path}")

    # ═══════════════════════════════════════════
    # 安全关闭
    # ═══════════════════════════════════════════

    def _shutdown(self):
        self.running = False
        self._transition_stop.set()

        if self._recording and self._trajectory_buffer:
            self._recording = False
            self._save_current_recording()

        self._print_final_summary()

        print("\n   关闭 Omega.7 力输出...")
        _omega_set_force(np.zeros(3))
        _omega_close()

        if hasattr(self, '_yolo_stop_event') and self._yolo_stop_event is not None:
            self._yolo_stop_event.set()
            print("  ⏳ 发送 YOLO 停止信号...")
        if self._yolo_process and self._yolo_process.is_alive():
            self._yolo_process.join(timeout=5)
            if self._yolo_process.is_alive():
                self._yolo_process.terminate()
                self._yolo_process.join(timeout=2)
                print("  ⚠️  YOLO 进程强制终止")
            else:
                print("  ✅ YOLO 进程已优雅退出")

        print("✅ 已安全停止")


# ═══════════════════════════════════════════════════════
# YOLO 子进程入口（修订：支持 OpenCV 普通摄像头 fallback）
# ═══════════════════════════════════════════════════════

def _yolo_process_main(model_path, conf_threshold,
                       frame_queue, result_queue, stop_event=None):
    """独立进程: YOLO 推理（支持 RealSense / OpenCV / 无摄像头）"""
    _sys = __import__("sys")
    _exp_dir = os.path.dirname(os.path.abspath(__file__))
    if _exp_dir not in _sys.path:
        _sys.path.insert(0, _exp_dir)

    import queue as _q
    import numpy as _np
    from vision_physics_mapper import VisionPhysicsMapper

    pid = os.getpid()
    print(f"[YOLO进程-{pid}] 已启动", flush=True)

    mapper = VisionPhysicsMapper(
        model_path=model_path,
        conf_threshold=conf_threshold,
    )

    # ── 摄像头初始化：先尝试 RealSense，再 fallback 到 OpenCV ──
    pipeline = None
    cap = None
    camera_ok = False

    try:
        import pyrealsense2 as rs
        pipeline = rs.pipeline()
        config = rs.config()
        config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
        pipeline.start(config)
        camera_ok = True
        print(f"[YOLO进程-{pid}] RealSense 摄像头已启动", flush=True)
    except Exception:
        pass

    if not camera_ok:
        try:
            import cv2
            cap = cv2.VideoCapture(0)
            if cap.isOpened():
                camera_ok = True
                print(f"[YOLO进程-{pid}] OpenCV 摄像头已启动", flush=True)
            else:
                cap = None
        except Exception:
            cap = None

    if not camera_ok:
        print(f"[YOLO进程-{pid}] ⚠️ 无可用的摄像头，使用空帧模拟", flush=True)

    cycle = 0
    try:
        while True:
            if stop_event is not None and stop_event.is_set():
                print(f"[YOLO进程-{pid}] 收到停止信号，正在退出...", flush=True)
                break

            try:
                rgb = None
                if camera_ok:
                    if cap is not None:
                        # OpenCV 模式
                        ret, frame = cap.read()
                        if ret:
                            import cv2
                            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        else:
                            time.sleep(0.05)
                            continue
                    else:
                        # RealSense 模式
                        frames = pipeline.wait_for_frames(timeout_ms=500)
                        if not frames:
                            continue
                        color = frames.get_color_frame()
                        if not color:
                            continue
                        rgb = _np.asanyarray(color.get_data())
                else:
                    rgb = _np.zeros((480, 640, 3), dtype=_np.uint8)
                    time.sleep(0.1)

                if rgb is not None:
                    cycle += 1
                    det = mapper.detect_and_map(rgb)

                    if det is not None:
                        bbox = det["bbox"]
                        det["bbox"] = tuple(map(int, bbox))
                        result_queue.put(det)
                        print(
                            f"[YOLO进程-{pid}] 🟢 #{cycle}: {det['class']} "
                            f"({det['profile'].label}) conf={det['conf']:.2f}",
                            flush=True,
                        )
            except _q.Full:
                pass
            except Exception as e:
                if cycle <= 10:
                    print(f"[YOLO进程-{pid}] ⚠️ 异常 #{cycle}: {e}", flush=True)
    finally:
        if pipeline is not None and camera_ok and cap is None:
            try:
                pipeline.stop()
                print(f"[YOLO进程-{pid}] RealSense pipeline 已关闭", flush=True)
            except Exception:
                pass
        if cap is not None:
            try:
                cap.release()
                print(f"[YOLO进程-{pid}] OpenCV 摄像头已释放", flush=True)
            except Exception:
                pass
        print(f"[YOLO进程-{pid}] 进程退出", flush=True)


# ═══════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="统一遥操作实验系统 — 4种模式按键切换 + 评分卡")
    parser.add_argument("--trajectory-dir", type=str, default="data",
                        help="轨迹 CSV 输出目录 (默认: data/)")
    parser.add_argument("--yolo-model", type=str, default="yolo11n.pt",
                        help="YOLO 模型路径 (默认: yolo11n.pt)")
    parser.add_argument("--physics-json", type=str, default=None,
                        help="PhysicsProfile JSON 表路径")
    parser.add_argument("--dry-run", action="store_true",
                        help="干跑模式 (不连接硬件)")
    parser.add_argument("--load", "-l", type=str, default=None,
                        help="启动时加载参数文件路径")
    args = parser.parse_args()

    exp = UnifiedTeleopExperiment(
        trajectory_dir=args.trajectory_dir,
        yolo_model=args.yolo_model,
        physics_json=args.physics_json,
        dry_run=args.dry_run,
    )

    if args.load and os.path.exists(args.load):
        exp.SAVE_FILE = args.load

    if args.dry_run:
        print("=" * 60)
        print("  DRY RUN 模式 — 模拟运行")
        print("=" * 60)
        auto = {"completion_time_s": 12.5, "path_length_m": 0.42,
                "F_ext_peak_N": 4.5, "F_ext_mean_N": 2.1}
        print_scorecard("c", "soft", auto, dry_run=True)
        print()
        print_comparison_table([
            {"mode": "a", "auto_metrics": {"completion_time_s": 18.2,
             "path_length_m": 0.52, "F_ext_peak_N": 8.5},
             "manual_scores": {"success": 1, "nasa_tlx": 45,
                               "damage_score": 1, "deformation_mm": 3, "human_score": 2}},
            {"mode": "b", "auto_metrics": {"completion_time_s": 15.0,
             "path_length_m": 0.48, "F_ext_peak_N": 6.8},
             "manual_scores": {"success": 1, "nasa_tlx": 35,
                               "damage_score": 0, "deformation_mm": 1, "human_score": 2}},
            {"mode": "c", "auto_metrics": {"completion_time_s": 12.1,
             "path_length_m": 0.38, "F_ext_peak_N": 4.2},
             "manual_scores": {"success": 1, "nasa_tlx": 25,
                               "damage_score": 0, "deformation_mm": 0, "human_score": 3}},
            {"mode": "d", "auto_metrics": {"completion_time_s": 16.5,
             "path_length_m": 0.50, "F_ext_peak_N": 7.0},
             "manual_scores": {"success": 1, "nasa_tlx": 40,
                               "damage_score": 1, "deformation_mm": 2, "human_score": 2}},
        ], "soft")
        return

    exp.initialize()

    if args.load and os.path.exists(args.load):
        exp.SAVE_FILE = args.load
        exp._load_params()

    exp.run()


if __name__ == "__main__":
    main()
