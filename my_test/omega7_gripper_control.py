#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
omega7_gripper_control.py — Omega.7 手柄控制 Franka 夹爪
=========================================================

功能:
  1. Omega.7 夹钳角度 → Franka 夹爪开度（连续控制 30Hz）
  2. 阈值驱动: 夹钳张开 > 80% → move()，夹钳捏合 < 20% → grasp()
  3. 灰色按钮 (button 0) → 夹爪完全张开复位
  4. 有限状态机确保 grasp 后可靠松开 (stop + move)
  5. 运行时自适应归一化（无需预先标定）
  6. 力反馈：夹爪闭合程度映射到 Omega.7
  7. 状态实时显示

状态机:
  ┌─────────┐   norm < 0.20    ┌──────────┐   grasp成功   ┌──────────┐
  │  IDLE   │ ───────────────→ │ GRASPING │ ────────────→ │ HOLDING  │
  │ (跟随)  │                   │ (力控抓取)│               │ (力保持)  │
  └─────────┘ ←─────────────── └──────────┘               └──────────┘
      │  ↑       grasp失败        │                            │
      │  └────────────────────────┘          norm > 0.80      │
      │                                             或灰色按钮  │
      │                                                       ↓
      │                                                  ┌──────────┐
      │                                                  │ RELEASING│
      │                                                  │ stop+move│
      └──────────────────────────────────────────────────└──────────┘

对比工作版 teleop_omega7_franka.py 的改进:
  - 有限状态机代替简单的 busy 标志
  - HOLDING→RELEASING 时先 stop() 释放力保持，再 move() 张开
  - 其余行为与工作版完全一致（阈值驱动、追赶模式）

用法:
  python3 my_test/omega7_gripper_control.py

依赖:
  pip install forcedimension-core panda-py numpy

作者: mfj
日期: 2026-06
"""

import sys
import time
import ctypes
import threading
from enum import Enum
from typing import Optional

import numpy as np
import forcedimension_core.dhd as dhd
import forcedimension_core.drd as drd
from panda_py import libfranka


# ═══════════════════════════════════════════
# 配置参数
# ═══════════════════════════════════════════

ROBOT_IP = "192.168.1.51"

# 夹爪基本参数
GRIPPER_SPEED = 0.1         # 夹爪运动速度 (m/s)
GRIPPER_FORCE = 20.0        # 夹爪夹持力 (N)
GRIPPER_MAX_WIDTH = 0.08    # 夹爪最大开度 (m)
GRIPPER_MIN_WIDTH = 0.0     # 夹爪最小开度 (m)
GRIPPER_HYSTERESIS = 0.003  # 夹爪命令死区 (m)
GRIPPER_EPS_INNER = 0.005   # grasp 内容差
GRIPPER_EPS_OUTER = 0.005   # grasp 外容差

# 阈值驱动参数 (与工作版 teleop_omega7_franka.py 一致)
GRASP_THRESHOLD = 0.20      # 归一化开度 < 此值 → 执行力控抓取 grasp()
MOVE_THRESHOLD = 0.80       # 归一化开度 > 此值 → 执行位置张开 move()
# 注意: 0.20 ~ 0.80 之间的区域为过渡区，不发送命令（让夹爪保持当前状态）

# 控制频率
CTRL_FREQ = 30.0            # 主控制循环频率 (Hz)
STATUS_FREQ = 10.0          # 状态显示频率 (Hz)
FORCE_FREQ = 100.0          # 力反馈频率 (Hz)

# 夹钳角度自适应归一化初始值
GRIP_ANGLE_INIT_MIN = -30.0  # 完全张开 (度)
GRIP_ANGLE_INIT_MAX = 0.0   # 完全捏合 (度)

# 力反馈
FORCE_FB_GAIN = 0.3         # 力反馈增益
FORCE_FB_MAX = 1.0          # 力反馈最大值 (N)

# stop 后等待夹爪状态切换的时间 (秒)
STOP_SETTLE_TIME = 0.1


class GripperState(Enum):
    """夹爪状态机状态"""
    IDLE = "IDLE"           # 空闲：跟随用户夹钳角度 (move)
    GRASPING = "GRASPING"   # 力控抓取中（grasp 阻塞执行）
    HOLDING = "HOLDING"     # 力保持状态：夹住物体
    RELEASING = "RELEASING" # 松开中（stop + move）


# ═══════════════════════════════════════════
# Omega7GripperController
# ═══════════════════════════════════════════

class Omega7GripperController:
    """
    Omega.7 → Franka 夹爪控制器 (有限状态机)

    核心设计:
      - 阈值驱动: 夹钳张开 > 80% → move(), 夹钳捏合 < 20% → grasp()
      - 有限状态机管理夹爪状态，避免 grasp 力保持与 move 的冲突
      - HOLDING→RELEASING: 先 stop() 释放力保持，再 move() 张开

    关键修复 (grasp 后无法松开):
      grasp() 成功后 Franka 夹爪进入"力保持状态"持续施力。
      直接调 move() 张开需要克服保持力，经常失败。
      修复: 在 HOLDING 状态下检测张开意图 → 先 stop() → 再 move()
    """

    def __init__(self, robot_ip: str = ROBOT_IP):
        self.robot_ip = robot_ip

        # ── Omega.7 设备 ──
        self._omega_opened = False
        self._drd_started = False

        # ── Franka ──
        self.gripper: Optional[libfranka.Gripper] = None

        # ── 夹钳角度自适应归一化 ──
        self._grip_angle_min = GRIP_ANGLE_INIT_MIN
        self._grip_angle_max = GRIP_ANGLE_INIT_MAX
        self._calibration_samples = 0

        # ── 夹爪状态机 ──
        self._state = GripperState.IDLE
        self._max_width = GRIPPER_MAX_WIDTH
        self._last_cmd_width = GRIPPER_MAX_WIDTH
        self._cmd_count = 0

        # 追赶模式：只记录最新目标宽度，worker 线程追赶执行
        self._pending_width: Optional[float] = None
        self._cmd_busy = False

        # ── 按钮状态 ──
        self._btn0_prev = 0  # 灰色按钮 (上一帧)

        # ── 力反馈 ──
        self._force_feedback = 0.0

        # ── 运行控制 ──
        self._running = False
        self._loop_count = 0
        self._last_ctrl_time = 0.0
        self._last_status_time = 0.0
        self._last_force_time = 0.0

        # ── Omega 读值缓存 ──
        self._omega_grip_deg = 0.0

    # ═══════════════════════════════════════════
    # 硬件初始化
    # ═══════════════════════════════════════════

    def initialize(self) -> bool:
        """初始化 Omega.7 和 Franka 夹爪"""
        print("=" * 60)
        print("  Omega.7 → Franka 夹爪控制 (状态机版)")
        print("=" * 60)

        # ── 0. 诊断: 先尝试连 Panda 发 recover ──
        print("\n[0/3] 诊断: 尝试连接 Panda (recover)...")
        try:
            import panda_py
            panda_diag = panda_py.Panda(self.robot_ip)
            state = panda_diag.get_state()
            print(f"  📊 机器人模式: {state.robot_mode}")
            print(f"  📊 机器人状态: {[hex(s) for s in state.current_errors]}")
            panda_diag.recover()
            print("  ✅ recover() 已发送")
            panda_diag.set_default_behavior()
            print("  ✅ set_default_behavior() 已发送")
        except Exception as e:
            print(f"  ⚠️  Panda 诊断连接失败: {e}")
            print(f"  ⚠️  但这不影响夹爪直连，继续初始化...")

        # ── 1. 连接 Omega.7 ──
        print("\n[1/3] 连接 Omega.7 ...")
        ret = dhd.open()
        if ret < 0:
            print(f"  ❌ Omega.7 连接失败: {dhd.errorGetLastStr()}")
            return False
        self._omega_opened = True
        print(f"  ✅ {dhd.getSystemType()} | SN: {dhd.getSerialNumber()}")

        if drd.start() < 0:
            print("  ⚠️  DRD 启动失败（力反馈不可用）")
        else:
            self._drd_started = True
            print("  ✅ DRD 实时通道已启动")

            # ── 关键修复: Omega.7 自动校准机械零位 ──
            # 不调用 autoInit() 会导致编码器零点偏移，
            # 夹钳角度读数不准，自适应归一化收敛变慢。
            if not drd.isInitialized():
                if drd.autoInit() < 0:
                    print(f"  ⚠️  Omega.7 自动校准失败: {dhd.errorGetLastStr()}")
                else:
                    print("  ✅ Omega.7 自动校准完成（机械零位已校正）")
                    # 校准后重设归一化范围，以校准后的零点为基准
                    self._grip_angle_min = GRIP_ANGLE_INIT_MIN
                    self._grip_angle_max = GRIP_ANGLE_INIT_MAX

        dhd.enableForce(True)
        dhd.enableGripperForce(True)
        print("  ✅ 夹钳力反馈已启用")

        # ── 2. 连接 Franka 夹爪 ──
        print(f"\n[2/3] 连接 Franka 夹爪 ({self.robot_ip}) ...")
        try:
            self.gripper = libfranka.Gripper(self.robot_ip)
            print("  ✅ Franka Hand 已连接")
        except Exception as e:
            print(f"  ❌ 夹爪连接失败: {e}")
            return False

        # ── 3. Homing 标定 → 张开到最大 ──
        print(f"\n[3/3] 夹爪标定 (homing) ...")
        try:
            # 诊断: 先读夹爪状态（homing 前）
            try:
                gripper_state = self.gripper.read_once()
                print(f"  📊 Homing 前: width={gripper_state.width*1000:.1f}mm, "
                      f"max_width={gripper_state.max_width*1000:.1f}mm, "
                      f"temperature={gripper_state.temperature:.1f}°C")
            except Exception as e:
                print(f"  ⚠️  读夹爪状态失败: {e}")

            self.gripper.homing()
            print("  ✅ Homing 完成")

            # 标定后重读状态，确认 max_width 已更新
            try:
                gripper_state = self.gripper.read_once()
                print(f"  📊 Homing 后: width={gripper_state.width*1000:.1f}mm, "
                      f"max_width={gripper_state.max_width*1000:.1f}mm, "
                      f"temperature={gripper_state.temperature:.1f}°C")
                self._max_width = gripper_state.max_width
            except Exception as e:
                print(f"  ⚠️  重读夹爪状态失败: {e}")

            self.gripper.move(GRIPPER_MAX_WIDTH, GRIPPER_SPEED)
            self._last_cmd_width = GRIPPER_MAX_WIDTH
        except Exception as e:
            print(f"  ❌ Homing 失败: {e}")
            print(f"  ❌ 夹爪未初始化，夹爪控制不可用")
            # 诊断: 不返回 False, 让 Omega 还能用
            # return False  # ← 如果需要严格初始化失败，取消注释这行

        print("\n" + "=" * 60)
        print("  🎮 初始化完成！")
        print("  夹钳自然松开 (>80%) → 夹爪张开 (move)")
        print("  夹钳捏合 (<20%)    → 力控抓取 (grasp)")
        print("  灰色按钮 → 夹爪完全张开复位")
        print("  Ctrl+C → 安全停止")
        print("=" + "=" * 60)

        return True

    # ═══════════════════════════════════════════
    # 夹钳角度 → 夹爪开度 (自适应归一化)
    # ═══════════════════════════════════════════

    def _update_grip_calibration(self, angle_deg: float):
        """运行时自适应更新夹钳角度范围 (只向外扩展)"""
        if angle_deg < self._grip_angle_min:
            self._grip_angle_min = angle_deg
        if angle_deg > self._grip_angle_max:
            self._grip_angle_max = angle_deg
        self._calibration_samples += 1

    def _angle_to_norm(self, angle_deg: float) -> float:
        """夹钳角度 → 归一化开度 [0,1] (0=闭合, 1=全开)"""
        grip_range = self._grip_angle_max - self._grip_angle_min

        if grip_range < 1.0:
            # 还没操作过，用默认范围
            grip_range = GRIP_ANGLE_INIT_MAX - GRIP_ANGLE_INIT_MIN
            norm = (GRIP_ANGLE_INIT_MAX - angle_deg) / grip_range
        else:
            # 角度靠近 max (~0°)  → 捏合   → norm 小
            # 角度靠近 min (~-60°) → 张开 → norm 大
            norm = (self._grip_angle_max - angle_deg) / grip_range

        return float(np.clip(norm, 0.0, 1.0))

    def _norm_to_width(self, norm: float) -> float:
        """归一化开度 [0,1] → 夹爪宽度 (m)"""
        return float(np.clip(norm * self._max_width, GRIPPER_MIN_WIDTH, self._max_width))

    # ═══════════════════════════════════════════
    # 夹爪命令执行 (独立线程)
    # ═══════════════════════════════════════════

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
            self.gripper.move(width, GRIPPER_SPEED)
            self._last_cmd_width = width
            self._cmd_count += 1
        except Exception as e:
            print(f"\n  ⚠️ move 失败: {e}")
        finally:
            self._cmd_busy = False

    def _execute_grasp(self, width: float):
        """GRASPING 状态：grasp() 力控抓取"""
        if self.gripper is None:
            self._state = GripperState.IDLE
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
                print(f"\n  🤖 已抓取物体! (宽度={width*1000:.1f}mm, 力={GRIPPER_FORCE:.0f}N)")
                self._state = GripperState.HOLDING
            else:
                print(f"\n  🤖 未检测到物体 (宽度={width*1000:.1f}mm)")
                self._state = GripperState.IDLE
        except Exception as e:
            print(f"\n  ⚠️ grasp 失败: {e}")
            self._state = GripperState.IDLE
        finally:
            self._cmd_busy = False

    def _execute_release(self, width: float):
        """RELEASING 状态：先 stop 释放力保持，再 move 张开"""
        if self.gripper is None:
            self._state = GripperState.IDLE
            self._cmd_busy = False
            return

        self._cmd_busy = True
        try:
            # 第一步：stop 释放力保持
            print(f"\n  🛑 释放力保持...")
            self._gripper_stop()

            # 第二步：move 到目标开度
            self.gripper.move(width, GRIPPER_SPEED)
            self._last_cmd_width = width
            self._cmd_count += 1
            print(f"  ✅ 夹爪已张开到 {width*1000:.1f}mm")

            self._state = GripperState.IDLE
        except Exception as e:
            print(f"\n  ⚠️ release 失败: {e}")
            self._state = GripperState.IDLE
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
        self._state = GripperState.GRASPING
        t = threading.Thread(target=self._execute_grasp, args=(width,),
                             daemon=True)
        t.start()

    def _trigger_release(self, width: float):
        """触发 RELEASING 状态的 stop+move"""
        self._state = GripperState.RELEASING
        t = threading.Thread(target=self._execute_release, args=(width,),
                             daemon=True)
        t.start()

    # ═══════════════════════════════════════════
    # 力反馈
    # ═══════════════════════════════════════════

    def _update_force_feedback(self, grip_norm: float):
        """
        根据夹爪闭合程度更新 Omega.7 力反馈

        重要: 夹爪力反馈映射到 Omega.7 的独立夹钳通道 (gripper channel),
        而不是 XYZ 平移轴。
          - XYZ 轴: 永远置零, 保持手把零力透明
          - Gripper 通道: grip_norm 越大 (夹爪越张开) → 力越小
                          grip_norm 越小 (夹爪越闭合) → 力越大 (模拟夹持阻力)

        使用 API:
          - dhd.setForceAndGripperForce(force_xyz, gripper_force)
          - 需提前调用 dhd.enableGripperForce(True)
        """
        # 夹钳力: 闭合度越高 (norm 小) → 力越大 (模拟抓握阻力)
        # 转换: grip_norm=1(全开) → 0N, grip_norm=0(全闭) → MAX
        grip_force = (1.0 - grip_norm) * FORCE_FB_GAIN * FORCE_FB_MAX
        grip_force = min(grip_force, FORCE_FB_MAX)

        # XYZ 轴保持零力透明，不干扰手柄平移运动
        force_xyz = np.zeros(3)
        try:
            dhd.setForceAndGripperForce(force_xyz, grip_force)
            self._force_feedback = grip_force
        except Exception:
            pass

    # ═══════════════════════════════════════════
    # 状态显示
    # ═══════════════════════════════════════════

    def _print_status(self, angle_deg: float, target_norm: float, target_width: float):
        """显示当前状态"""
        busystr = " ⏳" if self._cmd_busy else "   "
        status = (
            f"\r  [{self._loop_count}s] "
            f"夹钳={angle_deg:+.1f}° "
            f"→ {target_width*1000:5.1f}mm ({target_norm:.2f}) "
            f"| {self._state.value}{busystr}"
            f" | cmd#{self._cmd_count}"
        )
        print(status, end="", flush=True)

    # ═══════════════════════════════════════════
    # 状态机更新 (核心逻辑)
    # ═══════════════════════════════════════════

    def _update_state_machine(self, target_norm: float, target_width: float):
        """
        有限状态机控制夹爪

        与工作版 teleop_omega7_franka.py 的关键区别:
          - 有限状态机代替简单的 busy 标志
          - HOLDING→RELEASING 时先 stop() 释放力保持

        状态图:
          IDLE:
            - norm < GRASP_THRESHOLD (0.20):  → GRASPING (grasp)
            - norm > MOVE_THRESHOLD (0.80):    → move() 跟随
            - 过渡区 (0.20~0.80): 不发送命令

          GRASPING:
            - 等待 grasp 线程完成
            - 成功: → HOLDING
            - 失败: → IDLE

          HOLDING:
            - norm > MOVE_THRESHOLD (0.80): → RELEASING (stop + move)
            - 灰色按钮: → RELEASING (由按钮事件处理)

          RELEASING:
            - 等待 release 线程完成
            - 完成后自动 → IDLE
        """
        # ── 追赶模式：如果命令执行完但还有 pending ──
        if not self._cmd_busy and self._pending_width is not None:
            pw = self._pending_width
            self._pending_width = None
            # 查一下当前合适的状态
            pn = pw / self._max_width
            if pn > MOVE_THRESHOLD or self._state == GripperState.IDLE:
                self._execute_idle_move(pw)
            return

        # ── IDLE: 跟随用户 ──
        if self._state == GripperState.IDLE:
            if target_norm > MOVE_THRESHOLD:
                # 张开 → move
                if not self._cmd_busy:
                    if abs(target_width - self._last_cmd_width) > GRIPPER_HYSTERESIS:
                        self._trigger_idle_move(target_width)
            elif target_norm < GRASP_THRESHOLD:
                # 捏合 → grasp
                if not self._cmd_busy:
                    self._trigger_grasp(target_width)
            # else: 过渡区，不操作
            return

        # ── GRASPING: 等待 grasp 完成 ──
        if self._state == GripperState.GRASPING:
            return

        # ── HOLDING: 力保持中，检测释放意图 ──
        if self._state == GripperState.HOLDING:
            if target_norm > MOVE_THRESHOLD:
                if not self._cmd_busy:
                    self._trigger_release(target_width)
                else:
                    # 追赶模式
                    self._pending_width = target_width
            return

        # ── RELEASING: 等待 release 完成 ──
        if self._state == GripperState.RELEASING:
            return

    # ═══════════════════════════════════════════
    # 主控制循环
    # ═══════════════════════════════════════════

    def run(self):
        """主控制循环 (30Hz)"""
        if not self._omega_opened or self.gripper is None:
            print("❌ 请先调用 initialize()")
            return

        self._running = True

        dt_ctrl = 1.0 / CTRL_FREQ       # ~33ms
        dt_status = 1.0 / STATUS_FREQ   # 100ms
        dt_force = 1.0 / FORCE_FREQ     # 10ms

        print("\n🔄 状态机已启动 ...\n")

        try:
            while self._running:
                t_start = time.perf_counter()
                now = time.time()

                # ════════════════════════════════
                # 1. 读取 Omega.7 状态
                # ════════════════════════════════
                angle = ctypes.c_double()
                ret = dhd.getGripperAngleDeg(angle)
                if ret >= 0:
                    self._omega_grip_deg = angle.value

                btn0 = dhd.getButton(0)  # 灰色按钮

                # ════════════════════════════════
                # 2. 自适应标定 + 归一化
                # ════════════════════════════════
                self._update_grip_calibration(self._omega_grip_deg)
                target_norm = self._angle_to_norm(self._omega_grip_deg)
                target_width = self._norm_to_width(target_norm)

                # ════════════════════════════════
                # 3. 按钮事件 (上升沿)
                # ════════════════════════════════
                if btn0 and not self._btn0_prev:
                    print(f"\n  🔘 灰色按钮 → 夹爪完全张开")
                    if self._state == GripperState.HOLDING:
                        # 力保持中 → 走 release 路径 (stop + move)
                        self._trigger_release(self._max_width)
                    elif self._state == GripperState.IDLE and not self._cmd_busy:
                        # 空闲中 → 直接 move 张开
                        self._trigger_idle_move(self._max_width)
                    # 其他状态忽略（GRASPING/RELEASING 不打断）
                self._btn0_prev = btn0

                # ════════════════════════════════
                # 4. 状态机更新 (CTRL_FREQ Hz)
                # ════════════════════════════════
                if (now - self._last_ctrl_time) >= dt_ctrl:
                    self._update_state_machine(target_norm, target_width)
                    self._last_ctrl_time = now

                # ════════════════════════════════
                # 5. 力反馈 (FORCE_FREQ Hz)
                # ════════════════════════════════
                if (now - self._last_force_time) >= dt_force:
                    self._update_force_feedback(target_norm)
                    self._last_force_time = now

                # ════════════════════════════════
                # 6. 状态显示 (STATUS_FREQ Hz)
                # ════════════════════════════════
                self._loop_count += 1
                if (now - self._last_status_time) >= dt_status:
                    self._print_status(self._omega_grip_deg, target_norm, target_width)
                    self._last_status_time = now

                # ════════════════════════════════
                # 7. 周期同步
                # ════════════════════════════════
                elapsed = time.perf_counter() - t_start
                sleep_time = dt_ctrl - elapsed
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
    # 安全关闭
    # ═══════════════════════════════════════════

    def _shutdown(self):
        """安全关闭所有硬件"""
        self._running = False
        print("\n   正在关闭 ...")

        # 关闭 Omega.7 力输出 (XYZ + 夹钳通道)
        try:
            dhd.setForceAndGripperForce(np.zeros(3), 0.0)
        except Exception:
            pass

        # 关闭 Omega.7
        if self._omega_opened:
            try:
                dhd.close()
                print("  ✅ Omega.7 已关闭")
            except Exception as e:
                print(f"  ⚠️  Omega.7 关闭异常: {e}")

        # 打印统计
        print(f"  📊 总计命令: {self._cmd_count} 次")
        print(f"  📏 夹钳标定样本: {self._calibration_samples} 次")
        print(f"  📐 夹钳角度范围: [{self._grip_angle_min:.1f}°, "
              f"{self._grip_angle_max:.1f}°] (自适应学习)")
        print(f"  📋 最终状态: {self._state.value}")

        print("✅ 已安全停止")


# ═══════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════

def main():
    controller = Omega7GripperController(robot_ip=ROBOT_IP)

    if not controller.initialize():
        print("\n❌ 初始化失败，请检查硬件连接")
        sys.exit(1)

    controller.run()


if __name__ == "__main__":
    main()
