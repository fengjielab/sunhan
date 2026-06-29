#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
force_adaptive_teleop.py — 力自适应阻抗遥操作（实验模式 E）
============================================================
基于接触外力的刚度在线缩放：自由运动高刚度，接触后自动降刚度。
作为论文对比实验的基线方法（力反馈反应式策略 vs 视觉语义前馈式策略）。

核心机制:
    K_t(F_ext) = K_base · (1 − α · clip((|F_ext|−F_db)/(F_sat−F_db), 0, 1))
    
    - 自由运动 (|F_ext| ≈ 0): K_t ≈ K_base（高刚度，跟踪精准）
    - 接触后 (|F_ext| → F_sat): K_t → K_base · (1 − α)（低刚度，顺应保护）
    - 超越饱和 (|F_ext| > F_sat): K_t = K_base · (1 − α)（刚度不再降低）

对应文献:
    Duan J, Gan Y, Chen M, et al. Adaptive variable impedance control
    for dynamic contact force tracking in uncertain environment.
    Robotics and Autonomous Systems, 2018, 102: 54-65.

用法:
    # 默认参数启动
    python3 my_test/force_adaptive_teleop.py

    # 指定基线刚度和缩放系数
    python3 my_test/force_adaptive_teleop.py --K-base 200 --alpha 0.5 --F-sat 5.0

    # 指定轨迹输出目录
    python3 my_test/force_adaptive_teleop.py --trajectory-dir data/

键盘操作:
    ┌──────────┬──────────────────────────────────────┐
    │ 1/2      │ 阻尼比 ζ -/+                           │
    │ 3/4      │ 基线刚度 K_base -/+                    │
    │ 5/6      │ 缩放系数 α -/+                         │
    │ 7/8      │ 饱和力 F_sat -/+                       │
    │ 9/0      │ 力反馈增益 K_fb -/+                    │
    │ q/w      │ 旋转刚度比例 -/+ (K_r = ratio * K_t)   │
    │ h        │ 打印帮助                               │
    │ Ctrl+C   │ 安全退出                               │
    ├──────────┴──────────────────────────────────────┤
    │  🎮 Omega.7 按钮 — 夹爪控制                       │
    │  灰色按钮 (Btn0) → 夹爪完全张开                    │
    │  夹钳捏合 (<20%) → 力控抓取 (grasp)               │
    │  夹钳张开 (>80%) → 夹爪张开 (move)                │
    └─────────────────────────────────────────────────┘

作者: mfj
日期: 2026-06
"""

import sys
import time
import threading
import ctypes
import json
import argparse
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
CTRL_FREQ = 200.0
STATUS_FREQ = 10.0
KEYBOARD_FREQ = 30.0

# 坐标轴方向
SIGN = np.array([-1.0, -1.0, 1.0])

# ── 力自适应默认参数 ──
DEFAULT_K_BASE = 200.0       # 与实验 A 相同的接触前基线刚度 (N/m)
DEFAULT_ALPHA = 0.5          # 饱和时刚度降至基线的 50%
DEFAULT_F_SAT = 5.0          # 饱和力阈值 (N)
DEFAULT_ADAPT_DEADBAND = 1.0 # 自适应死区：过滤约 1N 空载零偏 (N)
DEFAULT_K_ROT_RATIO = 0.065  # 旋转刚度 = K_t * ratio
DEFAULT_DAMPING_RATIO = 1.2  # 与实验 A 对齐，只比较是否启用力自适应

# ── 力反馈固定参数 ──
DEFAULT_K_FB = 0.5           # 力反馈增益
DEFAULT_DEADBAND = 0.3       # 死区 (N)

# 位置映射
DEFAULT_SCALE = 3.0

# 零空间
DEFAULT_NULLSPACE = 0.5

# 平滑过渡
IMPD_UPDATE_INTERVAL = 0.05  # 阻抗参数更新间隔 (s)（20Hz 足够，避免过于频繁）
IMPD_SMOOTH_FACTOR = 0.3     # 一阶低通平滑系数 (0=不平滑, 1=不变)

# ── 夹爪 ──
GRIPPER_SPEED = 0.1
GRIPPER_FORCE = 20.0
GRIPPER_MAX = 0.08
GRIPPER_MIN_WIDTH = 0.0
GRIPPER_HYSTERESIS = 0.003
GRIPPER_EPS_INNER = 0.005
GRIPPER_EPS_OUTER = GRIPPER_MAX  # 未知物体宽度：允许在全行程内判定抓取成功
STOP_SETTLE_TIME = 0.1

# 夹钳角度自适应归一化初始值
GRIP_ANGLE_INIT_MIN = -30.0
GRIP_ANGLE_INIT_MAX = 0.0

# 夹爪力反馈叠加
FORCE_FB_GAIN = 0.3
FORCE_FB_MAX = 1.0
GRIPPER_CTRL_FREQ = 30.0

# 阈值驱动参数
GRASP_THRESHOLD = 0.20
MOVE_THRESHOLD = 0.80

# 轨迹记录
TRAJECTORY_DIR = "data"
TRAJECTORY_DECIMATION = 1
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
    "force_baseline_mean", "force_baseline_std", "force_threshold",
    "alpha", "F_sat",
]

# 参数范围
K_BASE_MIN, K_BASE_MAX = 30.0, 800.0
ALPHA_MIN, ALPHA_MAX = 0.0, 0.9
F_SAT_MIN, F_SAT_MAX = 1.0, 20.0
DAMPING_MIN, DAMPING_MAX = 0.1, 5.0
K_FB_MIN, K_FB_MAX = 0.0, 2.0
DEADBAND_MIN, DEADBAND_MAX = 0.0, 2.0
K_ROT_RATIO_MIN, K_ROT_RATIO_MAX = 0.01, 1.0


# ═══════════════════════════════════════════
# GripperState 夹爪状态机
# ═══════════════════════════════════════════

class GripperState(Enum):
    IDLE = "IDLE"
    GRASPING = "GRASPING"
    HOLDING = "HOLDING"
    RELEASING = "RELEASING"


# ═══════════════════════════════════════════
# ForceAdaptiveTeleop
# ═══════════════════════════════════════════

class ForceAdaptiveTeleop:
    """
    力自适应遥操作控制器（实验模式 E）

    核心设计:
        - 200Hz 主循环: 读Omega → 力自适应阻抗 → 力反馈 → 发Franka
        - 外力超过 F_db 后驱动刚度在线缩放，过滤约 1N 的估计零偏
        - 键盘线程 30Hz: 异步调节 α、F_sat、K_base 等参数
        - 一阶低通平滑: 避免刚度突变引起机械臂抖动
    """

    SAVE_FILE = "/home/mfj/force_adaptive_params.json"

    def __init__(self, K_base: float = DEFAULT_K_BASE,
                 alpha: float = DEFAULT_ALPHA,
                 F_sat: float = DEFAULT_F_SAT,
                 record_trajectory: bool = True,
                 trajectory_dir: str = TRAJECTORY_DIR,
                 subject_id: str = "unknown", object_id: str = "unknown",
                 trial_id: str = "unknown"):
        # ── 力自适应参数 ──
        self._K_base_cur = K_base
        self._alpha_cur = alpha
        self._F_sat_cur = F_sat
        self._adapt_deadband = DEFAULT_ADAPT_DEADBAND
        self._K_rot_ratio_cur = DEFAULT_K_ROT_RATIO

        # ── 当前阻抗参数（力自适应动态更新） ──
        self._K_trans_cur = K_base       # 当前平动刚度
        self._K_rot_cur = K_base * DEFAULT_K_ROT_RATIO  # 当前旋转刚度
        self._damping_ratio_cur = DEFAULT_DAMPING_RATIO

        # ── 力反馈固定参数 ──
        self._K_fb_cur = DEFAULT_K_FB
        self._deadband_cur = DEFAULT_DEADBAND
        self._scale_cur = DEFAULT_SCALE
        self._nullspace_cur = DEFAULT_NULLSPACE

        # ── 运行状态 ──
        self.running = False
        self._loop_count = 0

        # ── 轨迹 ──
        self._trajectory_record = record_trajectory
        self._trajectory_dir = trajectory_dir
        self._trajectory: List[dict] = []
        self._trajectory_start_time = 0.0
        self._traj_cycle = 0

        # ── Omega.7 ──
        self._omega_home = np.zeros(3)
        self._omega_prev_pos = np.zeros(3)
        self._omega_traj_length = 0.0
        self._omega_pos_last_valid = np.zeros(3)
        self._omega_grip_last_valid = 0.0

        # ── 夹爪 ──
        self._last_cmd_width = GRIPPER_MAX
        self._max_width = GRIPPER_MAX
        self._cmd_busy = False
        self._grip_min = GRIP_ANGLE_INIT_MIN
        self._grip_max = GRIP_ANGLE_INIT_MAX
        self._calibration_samples = 0
        self._cmd_count = 0
        self._pending_width: Optional[float] = None
        self._gripper_state = GripperState.IDLE
        self._grasp_armed = True
        self._btn0_prev = 0
        self._gripper_force_feedback = 0.0
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
        self._timeline = ExperimentTimeline(
            mode="E", subject_id=subject_id,
            object_id=object_id, trial_id=trial_id,
        )

        # ── 硬件句柄 ──
        self.panda = None
        self.gripper = None
        self.ctrl = None
        self.force_estimator = None

        # ── 键盘 ──
        self._key_pressed = ""
        self._key_lock = threading.Lock()
        self._last_key_time = 0.0
        self._key_repeat_delay = 0.3
        self._key_repeat_rate = 0.12
        self._key_held = False
        self._key_first_repeat = True

    # ═══════════════════════════════════════════
    # 初始化
    # ═══════════════════════════════════════════

    def initialize(self):
        print("=" * 65)
        print("  🦾 力自适应遥操作 — 接触力驱动刚度在线缩放")
        print("=" * 65)

        # ── Omega.7 ──
        print("[1] 连接 Omega.7 ...")
        ret = dhd.open()
        if ret < 0:
            print(f"    ❌ Omega.7 连接失败: {dhd.errorGetLastStr()}")
            sys.exit(1)
        print(f"    ✅ {dhd.getSystemType()} | SN: {dhd.getSerialNumber()}")

        self._omega_home = np.zeros(3)
        if dhd.getPosition(self._omega_home) < 0:
            time.sleep(0.1)
            dhd.getPosition(self._omega_home)
        self._omega_pos_last_valid = self._omega_home.copy()
        self._omega_prev_pos = self._omega_home.copy()
        print(f"    Omega.7 home: ({self._omega_home[0]:.3f}, {self._omega_home[1]:.3f}, {self._omega_home[2]:.3f}) m")

        if drd.start() < 0:
            print("    ⚠️  DRD 启动失败（仅力反馈不可用）")
        else:
            print("    ✅ DRD 已启动")
        dhd.enableForce(True)
        print("    ✅ 力反馈已启用")

        # ── Franka ──
        print(f"[2] 连接 Franka ({ROBOT_IP}) ...")
        self.panda = panda_py.Panda(ROBOT_IP)
        self.panda.recover()
        self.panda.set_default_behavior()

        print("[2.5] 设置碰撞阈值...")
        _robot = self.panda.get_robot()
        _robot.set_collision_behavior(
            [30.0]*7, [30.0]*7,
            [20.0]*7, [20.0]*7,
            [35.0]*6, [35.0]*6,
            [25.0]*6, [25.0]*6,
        )
        print("    ✅ 碰撞阈值已设置")

        print("    ✅ 保持当前位置，控制器将从此处无缝接管")

        # ── 夹爪 ──
        print("[3] 初始化 Franka Hand ...")
        self.gripper = libfranka.Gripper(ROBOT_IP)
        try:
            self.gripper.homing()
            print("    ✅ Homing 完成")
        except Exception as e:
            print(f"    ⚠️  Homing 失败: {e}")
        self.gripper.move(GRIPPER_MAX, GRIPPER_SPEED)
        self._last_cmd_width = GRIPPER_MAX
        self._gripper_width_actual = float("nan")
        self._gripper_width_valid = False
        print(f"    ✅ 夹爪已打开 ({GRIPPER_MAX*1000:.0f} mm)")

        # ── 状态读取 ──
        state = self.panda.get_state()
        self._init_pos = np.array(
            [state.O_T_EE[12], state.O_T_EE[13], state.O_T_EE[14]], dtype=float
        )
        self._init_ori = np.array(self.panda.get_orientation(), dtype=float)
        self._virtual_ref = self._init_pos.copy()

        # ── 外力估计 ──
        self.force_estimator = ForceEstimator(panda=self.panda)

        # ── 阻抗控制器 ──
        print("[4] 启动 CartesianImpedance 控制器 ...")
        K_init = self._build_stiffness(self._K_base_cur, self._K_base_cur * self._K_rot_ratio_cur)
        self.ctrl = controllers.CartesianImpedance(
            impedance=K_init,
            damping_ratio=self._damping_ratio_cur,
            nullspace_stiffness=self._nullspace_cur,
        )
        self.panda.start_controller(self.ctrl)
        self.ctrl.set_control(self._init_pos, self._init_ori)
        print("    ✅ 控制器已启动")

        print("=" * 65)
        print("  初始化完成 — 力自适应遥操作 🦾")
        print(f"  K_base={self._K_base_cur:.0f}  α={self._alpha_cur:.2f}  "
              f"F_db={self._adapt_deadband:.1f}N  F_sat={self._F_sat_cur:.1f}N  "
              f"ζ={self._damping_ratio_cur:.1f}")
        print("=" * 65)

    def _build_stiffness(self, K_trans: float, K_rot: float) -> np.ndarray:
        K = np.zeros((6, 6))
        K[0, 0] = K[1, 1] = K[2, 2] = K_trans
        K[3, 3] = K[4, 4] = K[5, 5] = K_rot
        return K

    # ═══════════════════════════════════════════
    # 力自适应核心 — 刚度在线缩放
    # ═══════════════════════════════════════════

    def _update_force_adaptive_impedance(self, F_ext: np.ndarray):
        """
        根据接触外力在线计算目标刚度并更新阻抗控制器。

        公式: K_t = K_base · (1 − α · clip((|F_ext|−F_db)/(F_sat−F_db), 0, 1))

        一阶低通平滑: 避免刚度突变导致机械臂抖动。
        """
        # 计算外力幅值（仅平动分量）
        f_mag = float(np.linalg.norm(F_ext[:3]))

        # 过滤空载零偏：F_db 以下不降刚度，F_db~F_sat 线性缩放。
        effective_force = max(f_mag - self._adapt_deadband, 0.0)
        adaptive_span = max(self._F_sat_cur - self._adapt_deadband, 0.1)
        ratio = min(effective_force / adaptive_span, 1.0)
        target_K_trans = self._K_base_cur * (1.0 - self._alpha_cur * ratio)
        target_K_trans = max(target_K_trans, 10.0)  # 兜底最小刚度

        # 旋转刚度按固定比例缩放
        target_K_rot = target_K_trans * self._K_rot_ratio_cur

        # 一阶低通平滑
        self._K_trans_cur += IMPD_SMOOTH_FACTOR * (target_K_trans - self._K_trans_cur)
        self._K_rot_cur += IMPD_SMOOTH_FACTOR * (target_K_rot - self._K_rot_cur)

        # 更新控制器
        K_6x6 = self._build_stiffness(self._K_trans_cur, self._K_rot_cur)
        self.ctrl.set_impedance(K_6x6)

    # ═══════════════════════════════════════════
    # 夹爪控制（与 interactive_teleop.py 保持一致）
    # ═══════════════════════════════════════════

    def _update_grip_calibration(self, angle_deg: float):
        if angle_deg < self._grip_min:
            self._grip_min = angle_deg
        if angle_deg > self._grip_max:
            self._grip_max = angle_deg
        self._calibration_samples += 1

    def _angle_to_norm(self, angle_deg: float) -> float:
        grip_range = self._grip_max - self._grip_min
        if grip_range < 1.0:
            grip_range = GRIP_ANGLE_INIT_MAX - GRIP_ANGLE_INIT_MIN
            norm = (GRIP_ANGLE_INIT_MAX - angle_deg) / grip_range
        else:
            norm = (self._grip_max - angle_deg) / grip_range
        return float(np.clip(norm, 0.0, 1.0))

    def _norm_to_width(self, norm: float) -> float:
        return float(np.clip(norm * GRIPPER_MAX, GRIPPER_MIN_WIDTH, GRIPPER_MAX))

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

    def _gripper_stop(self) -> bool:
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
        if self.gripper is None:
            return
        self._cmd_busy = True
        try:
            self.gripper.move(width, GRIPPER_SPEED)
            self._last_cmd_width = width
            self._gripper_width_actual = float("nan")
            self._gripper_width_valid = False
            self._cmd_count += 1
        except Exception as e:
            print(f"\n  ⚠️ move 失败: {e}")
        finally:
            self._cmd_busy = False

    def _execute_grasp(self, width: float):
        if self.gripper is None:
            self._gripper_state = GripperState.IDLE
            self._cmd_busy = False
            return
        self._cmd_busy = True
        try:
            success = self.gripper.grasp(
                width, GRIPPER_SPEED, GRIPPER_FORCE,
                GRIPPER_EPS_INNER, GRIPPER_EPS_OUTER,
            )
            self._last_cmd_width = width
            self._cmd_count += 1
            if success:
                self._grasp_success = True
                self._gripper_width_actual = float("nan")
                self._gripper_width_valid = False
                print(f"\n  🤖 已抓取物体! (宽度={width*1000:.1f}mm, 力={GRIPPER_FORCE:.0f}N)")
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
            if self._gripper_state != GripperState.RELEASING:
                self._cmd_busy = False

    def _execute_release(self, width: float):
        if self.gripper is None:
            self._gripper_state = GripperState.IDLE
            self._cmd_busy = False
            return
        self._cmd_busy = True
        try:
            if not self._gripper_stop():
                raise RuntimeError("stop() 未能释放夹爪力控")
            moved = self.gripper.move(width, GRIPPER_SPEED)
            if moved is False:
                if not self._gripper_stop():
                    raise RuntimeError("重试前 stop() 失败")
                moved = self.gripper.move(width, GRIPPER_SPEED)
            if moved is False:
                raise RuntimeError("move() 两次均未能张开夹爪")
            self._last_cmd_width = width
            self._gripper_width_actual = float("nan")
            self._gripper_width_valid = False
            self._cmd_count += 1
            self._gripper_state = GripperState.IDLE
        except Exception as e:
            print(f"\n  ⚠️ release 失败: {e}")
            self._gripper_state = GripperState.IDLE
        finally:
            self._cmd_busy = False

    def _trigger_idle_move(self, width: float):
        if self._cmd_busy:
            self._pending_width = width
            return
        self._pending_width = None
        t = threading.Thread(target=self._execute_idle_move, args=(width,), daemon=True)
        t.start()

    def _trigger_grasp(self, width: float):
        self._gripper_state = GripperState.GRASPING
        t = threading.Thread(target=self._execute_grasp, args=(width,), daemon=True)
        t.start()

    def _trigger_release(self, width: float):
        self._gripper_state = GripperState.RELEASING
        t = threading.Thread(target=self._execute_release, args=(width,), daemon=True)
        t.start()

    def _update_state_machine(self, target_norm: float, target_width: float):
        if self._gripper_state == GripperState.IDLE:
            if target_norm > MOVE_THRESHOLD:
                if not self._grasp_armed and not self._cmd_busy:
                    self._grasp_armed = True
                    self._trigger_release(self._max_width)
                else:
                    self._grasp_armed = True
            elif target_norm < GRASP_THRESHOLD and self._grasp_armed:
                if not self._cmd_busy:
                    self._grasp_armed = False
                    self._trigger_grasp(GRIPPER_MIN_WIDTH)
            return

        if self._gripper_state == GripperState.GRASPING:
            if target_norm > MOVE_THRESHOLD:
                self._grasp_armed = True
                self._trigger_release(self._max_width)
            return

        if self._gripper_state == GripperState.HOLDING:
            if target_norm > MOVE_THRESHOLD:
                if not self._cmd_busy:
                    self._grasp_armed = True
                    self._trigger_release(self._max_width)
            return

        if self._gripper_state == GripperState.RELEASING:
            return

    def _update_gripper(self):
        grip_deg = getattr(self, '_omega_grip_current', None)
        if grip_deg is None:
            return
        self._update_grip_calibration(grip_deg)
        target_norm = self._angle_to_norm(grip_deg)
        target_width = self._norm_to_width(target_norm)
        self._update_state_machine(target_norm, target_width)

    # ═══════════════════════════════════════════
    # 键盘
    # ═══════════════════════════════════════════

    def _keyboard_loop(self):
        import select as _sel
        import sys as _sys
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
            finally:
                try:
                    _termios.tcsetattr(fd, _termios.TCSAFLUSH, old)
                except Exception:
                    pass

    def _process_keyboard(self):
        key = ""
        with self._key_lock:
            if self._key_pressed:
                key = self._key_pressed
                if not self._key_held:
                    self._key_pressed = ""

        if not key:
            return

        if key == "1":
            self._damping_ratio_cur = max(DAMPING_MIN, self._damping_ratio_cur - 0.1)
            self.ctrl.set_damping_ratio(self._damping_ratio_cur)
            print(f"\r  阻尼比 ζ ↓ {self._damping_ratio_cur:.1f}")
        elif key == "2":
            self._damping_ratio_cur = min(DAMPING_MAX, self._damping_ratio_cur + 0.1)
            self.ctrl.set_damping_ratio(self._damping_ratio_cur)
            print(f"\r  阻尼比 ζ ↑ {self._damping_ratio_cur:.1f}")
        elif key == "3":
            self._K_base_cur = max(K_BASE_MIN, self._K_base_cur - 20.0)
            print(f"\r  基线刚度 K_base ↓ {self._K_base_cur:.0f}")
        elif key == "4":
            self._K_base_cur = min(K_BASE_MAX, self._K_base_cur + 20.0)
            print(f"\r  基线刚度 K_base ↑ {self._K_base_cur:.0f}")
        elif key == "5":
            self._alpha_cur = max(ALPHA_MIN, self._alpha_cur - 0.05)
            print(f"\r  缩放系数 α ↓ {self._alpha_cur:.2f}")
        elif key == "6":
            self._alpha_cur = min(ALPHA_MAX, self._alpha_cur + 0.05)
            print(f"\r  缩放系数 α ↑ {self._alpha_cur:.2f}")
        elif key == "7":
            self._F_sat_cur = max(F_SAT_MIN, self._F_sat_cur - 0.5)
            print(f"\r  饱和力 F_sat ↓ {self._F_sat_cur:.1f}N")
        elif key == "8":
            self._F_sat_cur = min(F_SAT_MAX, self._F_sat_cur + 0.5)
            print(f"\r  饱和力 F_sat ↑ {self._F_sat_cur:.1f}N")
        elif key == "9":
            self._K_fb_cur = max(K_FB_MIN, self._K_fb_cur - 0.05)
            print(f"\r  力反馈增益 K_fb ↓ {self._K_fb_cur:.2f}")
        elif key == "0":
            self._K_fb_cur = min(K_FB_MAX, self._K_fb_cur + 0.05)
            print(f"\r  力反馈增益 K_fb ↑ {self._K_fb_cur:.2f}")
        elif key == "q":
            self._K_rot_ratio_cur = max(K_ROT_RATIO_MIN, self._K_rot_ratio_cur - 0.01)
            print(f"\r  旋转刚度比例 ↓ {self._K_rot_ratio_cur:.3f}")
        elif key == "w":
            self._K_rot_ratio_cur = min(K_ROT_RATIO_MAX, self._K_rot_ratio_cur + 0.01)
            print(f"\r  旋转刚度比例 ↑ {self._K_rot_ratio_cur:.3f}")
        elif key == "h":
            self._print_help()
        elif key == "v":
            self._save_params()

    def _print_help(self):
        print("\n" + "=" * 65)
        print("  🦾 力自适应遥操作 — 按键帮助")
        print("=" * 65)
        print("  当前参数:")
        print(f"    K_base = {self._K_base_cur:.0f} N/m  (基线平动刚度)")
        print(f"    α      = {self._alpha_cur:.2f}       (缩放系数)")
        print(f"    F_sat  = {self._F_sat_cur:.1f} N     (饱和力阈值)")
        print(f"    K_rot_ratio = {self._K_rot_ratio_cur:.3f}  (旋转刚度比例)")
        print(f"    ζ      = {self._damping_ratio_cur:.2f} (阻尼比)")
        print(f"    K_fb   = {self._K_fb_cur:.2f}       (力反馈增益)")
        print("  ┌──────────┬──────────────────────────────────────┐")
        print("  │ 1/2      │ 阻尼比 ζ -/+  (步长 0.1)             │")
        print("  │ 3/4      │ 基线刚度 K_base -/+  (步长 20 N/m)    │")
        print("  │ 5/6      │ 缩放系数 α -/+  (步长 0.05)           │")
        print("  │ 7/8      │ 饱和力 F_sat -/+  (步长 0.5 N)        │")
        print("  │ 9/0      │ 力反馈增益 K_fb -/+  (步长 0.05)     │")
        print("  │ q/w      │ 旋转刚度比例 -/+  (步长 0.01)         │")
        print("  ├──────────┼──────────────────────────────────────┤")
        print("  │ v        │ 保存参数                               │")
        print("  │ h        │ 打印帮助                               │")
        print("  │ Ctrl+C   │ 安全退出                               │")
        print("  ├──────────┴──────────────────────────────────────┤")
        print("  │  刚度公式: 超过 F_db 后在 F_sat 处饱和          │")
        print("  │  范围: [K_base·(1-α), K_base]                    │")
        print("  └──────────────────────────────────────────────────┘")
        print("=" * 65)

    def _save_params(self):
        params = {
            "K_base": self._K_base_cur,
            "alpha": self._alpha_cur,
            "F_sat": self._F_sat_cur,
            "K_rot_ratio": self._K_rot_ratio_cur,
            "damping_ratio": self._damping_ratio_cur,
            "K_fb": self._K_fb_cur,
            "deadband": self._deadband_cur,
            "scale": self._scale_cur,
        }
        try:
            with open(self.SAVE_FILE, "w") as f:
                json.dump(params, f, indent=2)
            print(f"\n  💾 参数已保存到 {self.SAVE_FILE}")
        except Exception as e:
            print(f"\n  ❌ 保存失败: {e}")

    # ═══════════════════════════════════════════
    # 轨迹
    # ═══════════════════════════════════════════

    def _record_trajectory_sample(self, raw_pos, gripper_deg, button, now_perf=None):
        now_perf = time.perf_counter() if now_perf is None else now_perf
        snap = self._timeline.snapshot(now_perf)
        F = np.asarray(self._F_ext_current, dtype=float)
        if F.size < 6:
            F = np.pad(F, (0, 6 - F.size), constant_values=np.nan)
        row = {
            "schema_version": 2, "system_time": snap["system_time"],
            "operation_time": snap["operation_time"], "phase": snap["phase"],
            "event": self._timeline.consume_events(), "mode": "E",
            "controller_mode": "force_adaptive",
            "subject_id": self._timeline.subject_id, "object_id": self._timeline.object_id,
            "trial_id": self._timeline.trial_id,
            "omega_x": raw_pos[0], "omega_y": raw_pos[1], "omega_z": raw_pos[2],
            "omega_valid": int(self._omega_read_valid), "gripper_deg": gripper_deg,
            "button": button, "target_x": self._target_pos_current[0],
            "target_y": self._target_pos_current[1], "target_z": self._target_pos_current[2],
            "robot_x": self._robot_pos_current[0], "robot_y": self._robot_pos_current[1],
            "robot_z": self._robot_pos_current[2],
            "F_ext_x": F[0], "F_ext_y": F[1], "F_ext_z": F[2],
            "T_ext_x": F[3], "T_ext_y": F[4], "T_ext_z": F[5],
            "F_ext_mag": float(np.linalg.norm(F[:3])),
            "K_trans": self._K_trans_cur, "K_rot": self._K_rot_cur,
            "damping_ratio": self._damping_ratio_cur, "K_fb": self._K_fb_cur,
            "deadband": self._deadband_cur, "scale": self._scale_cur,
            "gripper_state": self._gripper_state.value,
            "gripper_cmd_width": self._last_cmd_width,
            "gripper_width": self._gripper_width_actual,
            "gripper_width_valid": int(self._gripper_width_valid),
            "gripper_speed": GRIPPER_SPEED, "gripper_force": GRIPPER_FORCE,
            "grasp_success": int(self._grasp_success), "vision_class": "",
            "vision_label": "", "vision_confidence": float("nan"), "vision_locked": 0,
            "fusion_delta_K": self._K_trans_cur - self._K_base_cur,
            "fusion_active": int(abs(self._K_trans_cur - self._K_base_cur) > 0.5),
            "control_dt": self._control_dt,
            "force_baseline_mean": snap["force_baseline_mean"],
            "force_baseline_std": snap["force_baseline_std"],
            "force_threshold": snap["force_threshold"],
            "alpha": self._alpha_cur, "F_sat": self._F_sat_cur,
        }
        row.update({"time": row["system_time"], "x": raw_pos[0], "y": raw_pos[1], "z": raw_pos[2]})
        self._trajectory.append(row)

    def _save_trajectory(self, timestamp: str = None):
        if not self._trajectory or len(self._trajectory) < 10:
            return None
        import csv as _csv
        from datetime import datetime as _dt
        if timestamp is None:
            timestamp = _dt.now().strftime('%Y%m%d_%H%M%S')
        path = Path(self._trajectory_dir)
        path.mkdir(parents=True, exist_ok=True)
        fname = f"force_adaptive_{timestamp}.csv"
        fpath = path / fname
        with open(fpath, "w", newline="") as f:
            writer = _csv.writer(f)
            writer.writerow(TRAJECTORY_CSV_HEADER)
            for row in self._trajectory:
                writer.writerow([row.get(key, "") for key in TRAJECTORY_CSV_HEADER])
        duration = self._trajectory[-1]["system_time"] - self._trajectory[0]["system_time"]
        actual_freq = len(self._trajectory) / duration if duration > 0 else 0
        print(f"\n  🎯 轨迹已保存: {fpath}")
        print(f"     {len(self._trajectory)} 点, {duration:.1f}s, {actual_freq:.0f} Hz")
        events_path = path / f"force_adaptive_{timestamp}_events.json"
        self._timeline.save_events(events_path)
        print(f"     事件时间轴: {events_path}")
        return str(fpath)

    def _save_summary(self, timestamp: str):
        import json as _json
        from datetime import datetime as _dt
        path = Path(self._trajectory_dir)
        path.mkdir(parents=True, exist_ok=True)
        fname = f"force_adaptive_{timestamp}_summary.json"
        fpath = path / fname

        traj_len = self._omega_traj_length
        n_samples = len(self._trajectory)
        speed_mean = speed_std = speed_max = 0.0
        force_peak = force_peak_time = force_mean = 0.0

        force_samples = [
            (float(row["time"]), float(row["F_ext_mag"]))
            for row in self._trajectory
            if np.isfinite(row.get("F_ext_mag", np.nan))
        ]
        if force_samples:
            force_peak_time, force_peak = max(force_samples, key=lambda item: item[1])
            force_mean = float(np.mean([item[1] for item in force_samples]))

        if n_samples >= 2:
            speeds = []
            for i in range(1, n_samples):
                dt = self._trajectory[i]["time"] - self._trajectory[i-1]["time"]
                if dt > 0:
                    dx = self._trajectory[i]["x"] - self._trajectory[i-1]["x"]
                    dy = self._trajectory[i]["y"] - self._trajectory[i-1]["y"]
                    dz = self._trajectory[i]["z"] - self._trajectory[i-1]["z"]
                    speed = np.sqrt(dx*dx + dy*dy + dz*dz) / dt
                    speeds.append(speed)
            if speeds:
                arr = np.array(speeds)
                speed_mean = float(np.mean(arr))
                speed_std = float(np.std(arr))
                speed_max = float(np.max(arr))

        summary = {
            "timestamp": timestamp,
            "saved_at": _dt.now().isoformat(),
            "mode": "force_adaptive",
            "params": {
                "K_base": self._K_base_cur,
                "alpha": self._alpha_cur,
                "F_sat": self._F_sat_cur,
                "F_adapt_deadband": self._adapt_deadband,
                "K_rot_ratio": self._K_rot_ratio_cur,
                "damping_ratio": self._damping_ratio_cur,
            },
            "runtime": {
                "duration_s": round(self._timeline.system_time(), 2),
                "operation_time_s": self._timeline.to_dict()["operation_time_s"],
                "traj_length_m": round(traj_len, 4),
                "mean_speed_ms": round(speed_mean, 4),
                "speed_std_ms": round(speed_std, 4),
                "max_speed_ms": round(speed_max, 4),
            },
            "trajectory": {"n_samples": n_samples},
            "external_force": {
                "source": "Franka estimated external wrench",
                "metric": "norm(Fx, Fy, Fz)",
                "F_ext_peak_N": round(force_peak, 3),
                "F_ext_peak_time_s": round(force_peak_time, 4),
                "F_ext_mean_N": round(force_mean, 3),
                "n_samples": len(force_samples),
            },
            "experiment": self._timeline.to_dict(),
        }
        with open(fpath, "w") as f:
            _json.dump(summary, f, indent=2, ensure_ascii=False)
        print(f"  📊 汇总已保存: {fpath}")
        print(f"     轨迹={traj_len:.3f}m  速度均值={speed_mean:.3f}m/s  最大速度={speed_max:.3f}m/s")
        print(
            f"     末端外力峰值={force_peak:.3f} N "
            f"(t={force_peak_time:.3f} s), 均值={force_mean:.3f} N"
        )
        return str(fpath)

    # ═══════════════════════════════════════════
    # 状态打印
    # ═══════════════════════════════════════════

    def _print_status(self):
        F_mag = float(np.linalg.norm(self._F_ext_current[:3]))
        traj_len = self._omega_traj_length
        grip_busy_str = " ⏳" if self._cmd_busy else "   "
        last_grip_mm = self._last_cmd_width * 1000.0

        # 计算刚度范围显示
        K_min = self._K_base_cur * (1.0 - self._alpha_cur)

        status = (
            f"\r[{self._loop_count // int(CTRL_FREQ)}s] "
            f"Kt={self._K_trans_cur:.0f} "
            f"[{K_min:.0f}~{self._K_base_cur:.0f}] "
            f"Kr={self._K_rot_cur:.1f} "
            f"ζ={self._damping_ratio_cur:.2f} "
            f"|Fext|={F_mag:.2f}N "
            f"α={self._alpha_cur:.2f} "
            f"Fsat={self._F_sat_cur:.1f} "
            f"Kfb={self._K_fb_cur:.2f} "
            f"L={traj_len:.2f}m "
            f"夹爪={last_grip_mm:.0f}mm "
            f"|{self._gripper_state.value}{grip_busy_str}"
        )
        # 接触状态指示
        if F_mag > self._adapt_deadband:
            ratio = min(
                (F_mag - self._adapt_deadband)
                / max(self._F_sat_cur - self._adapt_deadband, 0.1),
                1.0,
            )
            bar_len = int(ratio * 10)
            status += f" 接触{'█'*bar_len}{'░'*(10-bar_len)}"
        else:
            status += " 自由运动"

        print(status, end="", flush=True)

    # ═══════════════════════════════════════════
    # 主控制循环
    # ═══════════════════════════════════════════

    def run(self):
        self.running = True

        dt = 1.0 / CTRL_FREQ
        dt_gripper = 1.0 / GRIPPER_CTRL_FREQ
        dt_status = 1.0 / STATUS_FREQ
        dt_keyboard = 1.0 / KEYBOARD_FREQ

        self._trajectory_start_time = time.time()
        self._traj_cycle = 0

        kb_thread = threading.Thread(target=self._keyboard_loop, daemon=True)
        kb_thread.start()

        self._print_help()

        print("\n" + "=" * 65)
        print("  🚀 力自适应遥操作已启动！")
        print(
            "  K_t = K_base · [1 − α · "
            "clip((|F_ext|−F_db)/(F_sat−F_db), 0, 1)]"
        )
        print(f"  F_db={self._adapt_deadband:.1f}N  F_sat={self._F_sat_cur:.1f}N")
        print(f"  刚度范围: [{self._K_base_cur*(1-self._alpha_cur):.0f} ~ {self._K_base_cur:.0f}] N/m")
        print("=" * 65 + "\n")

        last_status_time = 0.0
        last_gripper_time = 0.0
        last_gripper_measure_time = 0.0
        last_kb_time = 0.0
        last_impd_update = 0.0
        last_cycle_perf = time.perf_counter()

        try:
            while self.running:
                t_start = time.perf_counter()
                now = time.time()
                now_perf = t_start
                self._control_dt = now_perf - last_cycle_perf
                last_cycle_perf = now_perf

                # ── 1. 读 Omega.7 ──
                raw_pos = np.zeros(3)
                if dhd.getPosition(raw_pos) < 0:
                    self._omega_read_valid = False
                    raw_pos = self._omega_pos_last_valid.copy()
                else:
                    self._omega_read_valid = True
                    self._omega_pos_last_valid = raw_pos.copy()

                delta_pos = raw_pos - self._omega_prev_pos
                if "task_start" in self._timeline.event_times:
                    self._omega_traj_length += np.linalg.norm(delta_pos)

                gripper_angle = ctypes.c_double()
                if dhd.getGripperAngleDeg(gripper_angle) < 0:
                    omega_grip = self._omega_grip_last_valid
                else:
                    omega_grip = gripper_angle.value
                    self._omega_grip_last_valid = omega_grip
                self._omega_grip_current = omega_grip

                btn0 = 0
                try:
                    btn0 = dhd.getButton(0)
                except Exception:
                    pass

                if btn0 and not self._btn0_prev:
                    print(f"\n  🔘 灰色按钮 → 夹爪完全张开")
                    self._grasp_armed = False
                    if self._gripper_state != GripperState.RELEASING:
                        self._trigger_release(self._max_width)
                self._btn0_prev = btn0

                # ── 2. 读 Franka 外力 ──
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
                        pass

                # ── 2a. 自动实验生命周期 ──
                F_mag_now = float(np.linalg.norm(self._F_ext_current[:3]))
                self._timeline.add_force_baseline(F_mag_now, now_perf)
                if self._timeline.phase == PHASE_PREP and self._timeline.baseline_ready:
                    self._timeline.set_ready(now_perf)
                    self._omega_prev_pos = raw_pos.copy()
                    print("\n\a  ✅ READY — 首次有效操作将自动开始计时")
                self._timeline.observe_motion(raw_pos, now_perf)
                self._timeline.observe_contact(F_mag_now, now_perf)
                self._timeline.observe_gripper(
                    self._gripper_state.value,
                    self._gripper_width_actual if self._gripper_width_valid else self._last_cmd_width,
                    now_perf,
                    grasp_success=self._grasp_success,
                )

                # ── 2a. 力自适应阻抗更新 (降频) ──
                if (now - last_impd_update) >= IMPD_UPDATE_INTERVAL:
                    self._update_force_adaptive_impedance(self._F_ext_current)
                    last_impd_update = now

                # ── 3. 力反馈 ──
                F_ext_xyz = self._F_ext_current[:3]
                F_scaled = F_ext_xyz * self._K_fb_cur
                F_haptic = np.where(
                    np.abs(F_scaled) > self._deadband_cur,
                    np.sign(F_scaled) * (np.abs(F_scaled) - self._deadband_cur),
                    0.0,
                )
                # 夹爪力反馈叠加
                grip_norm = self._angle_to_norm(omega_grip)
                grip_force_mag = min(grip_norm * FORCE_FB_GAIN * FORCE_FB_MAX, FORCE_FB_MAX)
                F_haptic[2] += grip_force_mag
                self._gripper_force_feedback = grip_force_mag
                try:
                    dhd.setForce(F_haptic)
                except Exception:
                    pass

                # ── 4. 位置映射 ──
                delta_raw = raw_pos - self._omega_prev_pos
                if "task_start" in self._timeline.event_times:
                    self._virtual_ref += delta_raw * self._scale_cur * SIGN
                target_pos = self._virtual_ref.copy()
                np.clip(target_pos, -10.0, 10.0, out=target_pos)
                self._omega_prev_pos = raw_pos.copy()
                self._target_pos_current = target_pos.copy()

                # ── 5. 发给 Franka ──
                if self.ctrl is not None:
                    self.ctrl.set_control(target_pos, self._init_ori)

                # ── 6. 夹爪控制 ──
                if (now - last_gripper_time) >= dt_gripper:
                    self._update_gripper()
                    last_gripper_time = now
                if (now - last_gripper_measure_time) >= 0.1:
                    self._refresh_gripper_measurement()
                    last_gripper_measure_time = now

                if self._trajectory_record:
                    self._traj_cycle += 1
                    if self._traj_cycle % TRAJECTORY_DECIMATION == 0:
                        self._record_trajectory_sample(raw_pos, omega_grip, btn0, now_perf)

                if self._timeline.completed:
                    print("\n\a  ✅ 任务释放完成，自动结束并保存数据")
                    self.running = False
                    break

                # ── 7. 键盘 ──
                if (now - last_kb_time) >= dt_keyboard:
                    self._process_keyboard()
                    last_kb_time = now

                # ── 8. 状态打印 ──
                self._loop_count += 1
                if (now - last_status_time) >= dt_status:
                    self._print_status()
                    last_status_time = now

                # ── 同步 ──
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

    def _shutdown(self):
        self.running = False

        if not self._timeline.completed and not self._timeline.incomplete:
            self._timeline.abort("shutdown_before_task_completion")

        elapsed_total = self._timeline.system_time()
        print(f"\n  📏 主端 Omega.7 轨迹长度: {self._omega_traj_length:.3f} m")
        print(f"     运行时长: {elapsed_total:.1f} s")
        if elapsed_total > 0:
            print(f"     平均速度: {self._omega_traj_length / elapsed_total:.3f} m/s")
        print(f"\n  🤖 夹爪命令: {self._cmd_count} 次 | 最终状态: {self._gripper_state.value}")

        if self._trajectory_record:
            from datetime import datetime as _dt
            timestamp = _dt.now().strftime('%Y%m%d_%H%M%S')
            csv_path = self._save_trajectory(timestamp)
            self._save_summary(timestamp)
            if csv_path:
                try:
                    from force_metrics import analyze_csv
                    result = analyze_csv(csv_path, save_plot=True)
                    print(f"  📈 分阶段指标: {result.get('metrics_json')}")
                except Exception as e:
                    print(f"  ⚠️ 分阶段指标生成失败（原始CSV已保留）: {e}")

        print("\n  关闭 Omega.7 力输出...")
        try:
            dhd.setForce(np.zeros(3))
        except Exception:
            pass
        try:
            dhd.close()
        except Exception:
            pass
        print("✅ 已安全停止")


# ═══════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="力自适应遥操作 — 接触力驱动刚度在线缩放（实验模式 E）"
    )
    parser.add_argument("--K-base", type=float, default=DEFAULT_K_BASE,
                        help=f"基线平动刚度 N/m (默认: {DEFAULT_K_BASE})")
    parser.add_argument("--alpha", type=float, default=DEFAULT_ALPHA,
                        help=f"刚度缩放系数 [0,1] (默认: {DEFAULT_ALPHA})")
    parser.add_argument("--F-sat", type=float, default=DEFAULT_F_SAT,
                        help=f"饱和力阈值 N (默认: {DEFAULT_F_SAT})")
    parser.add_argument("--no-trajectory", action="store_true",
                        help="关闭轨迹自动录制")
    parser.add_argument("--trajectory-dir", type=str, default=TRAJECTORY_DIR,
                        help=f"轨迹 CSV 输出目录 (默认: {TRAJECTORY_DIR}/)")
    parser.add_argument("--subject-id", default="unknown", help="被试编号")
    parser.add_argument("--object-id", default="unknown", help="物体编号")
    parser.add_argument("--trial-id", default="unknown", help="试次编号")
    args = parser.parse_args()

    teleop = ForceAdaptiveTeleop(
        K_base=args.K_base,
        alpha=args.alpha,
        F_sat=args.F_sat,
        record_trajectory=not args.no_trajectory,
        trajectory_dir=args.trajectory_dir,
        subject_id=args.subject_id,
        object_id=args.object_id,
        trial_id=args.trial_id,
    )
    teleop.initialize()
    teleop.run()


if __name__ == "__main__":
    main()
