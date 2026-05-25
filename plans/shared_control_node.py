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

import sys
import time
import threading
import ctypes
import argparse
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
GRIPPER_FORCE = 20.0
GRIPPER_MAX = 0.08
GRIPPER_EPS_INNER = 0.005
GRIPPER_EPS_OUTER = 0.005
GRIPPER_ANGLE_OPEN = -60.0
GRIPPER_ANGLE_CLOSE = 0.0
GRIPPER_HYSTERESIS = 0.01

# 视觉
YOLO_MODEL_PATH = "yolo11n.pt"
CONF_THRESHOLD = 0.5

# 默认阻抗
DEFAULT_IMPEDANCE = np.diag([200.0, 200.0, 200.0, 10.0, 10.0, 10.0])


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

        # 5. Omega.7 标定
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

        # 7. 视觉模块
        if self.mode in ("b", "c"):
            print("[初始化] YOLO + 视觉查表 ...")
            self.mapper = VisionPhysicsMapper(
                model_path=YOLO_MODEL_PATH,
                conf_threshold=CONF_THRESHOLD,
            )
            self.current_profile = self.mapper.get_default()
            print(f"   ✓ 初始 profile: {self.current_profile.label}")
        else:
            print("[初始化] 模式A: 跳过视觉模块")

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
        self._gripper_was_open = True

    # ═══════════════════════════════════════════
    # 视觉线程
    # ═══════════════════════════════════════════

    def _vision_loop(self):
        """视觉检测循环 (30Hz, 独立线程)

        每帧检测 → 查 PhysicsProfile → 事件触发更新 stiffness + 力反馈增益
        """
        import cv2
        import pyrealsense2 as rs

        # 配置 RealSense
        pipeline = rs.pipeline()
        config = rs.config()
        config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
        pipeline.start(config)
        align = rs.align(rs.stream.color)

        print("[视觉线程] RealSense D435i 已启动")

        while self.running:
            try:
                frames = pipeline.wait_for_frames(timeout_ms=5000)
                aligned = align.process(frames)
                color_frame = aligned.get_color_frame()
                if not color_frame:
                    continue

                rgb = np.asanyarray(color_frame.get_data())

                # YOLO 检测 + 查表
                det = self.mapper.detect_and_map(rgb)

                if det is not None:
                    profile = det["profile"]
                    class_name = det["class"]

                    with self._profile_lock:
                        self.current_profile = profile

                    with self.latest_detection_lock:
                        self.latest_detection = det

                    # 事件触发: 更新 stiffness + 力反馈增益
                    if self.mode == "c":
                        self.admittance.apply_profile(profile)
                        self.feedback_sched.set_profile(profile)

                    print(f"[视觉] 🟢 {class_name} ({profile.label}) "
                          f"K_trans={profile.K_trans} deadband={profile.deadband}")
                else:
                    # 用默认值
                    pass

            except Exception as e:
                if self.running:
                    print(f"[视觉] ⚠️ 异常: {e}")
                time.sleep(0.1)

        pipeline.stop()
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
        if self.mapper is not None:
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
                now = time.time()
                if (now - self._last_gripper_time) >= dt_gripper:
                    self._update_gripper()

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
        """夹爪控制逻辑 (10Hz)"""
        gripper_angle = ctypes.c_double()
        dhd.getGripperAngleDeg(gripper_angle)
        self._omega_grip = gripper_angle.value
        self._button_grasp = dhd.getButton(0)

        grip_norm = np.clip(
            (self._omega_grip - GRIPPER_ANGLE_CLOSE) / (GRIPPER_ANGLE_OPEN - GRIPPER_ANGLE_CLOSE),
            0.0, 1.0,
        )
        target_width = grip_norm * GRIPPER_MAX
        width_change = abs(target_width - self._last_gripper_cmd)

        if width_change > GRIPPER_HYSTERESIS:
            if grip_norm > 0.8:
                self.gripper.move(target_width, GRIPPER_SPEED)
            elif grip_norm < 0.2:
                self.gripper.grasp(
                    target_width, GRIPPER_SPEED, GRIPPER_FORCE,
                    GRIPPER_EPS_INNER, GRIPPER_EPS_OUTER,
                )
            else:
                self.gripper.move(target_width, GRIPPER_SPEED)
            self._last_gripper_cmd = target_width

        if self._button_grasp:
            self.gripper.move(GRIPPER_MAX, GRIPPER_SPEED)
            self._last_gripper_cmd = GRIPPER_MAX

        self._last_gripper_time = time.time()

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

        profile_label = self.current_profile.label if self.current_profile else "N/A"
        profile_class = self.latest_detection["class"] if self.latest_detection else "N/A"

        print(f"[{loop_count:>6}] 物体={profile_class:<12} label={profile_label:<8} "
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
    args = parser.parse_args()

    node = SharedControlNode(mode=args.mode)
    node.initialize()
    node.run()


if __name__ == "__main__":
    main()
