#!/usr/bin/env python3
"""
test_modes_hand_feel.py — 三种共享控制模式手感对比测试
================================================================

通过 Omega.7 力反馈手柄，让操作员直观感受模式 A/B/C 的力觉反馈差异。

测试目的:
    操作员在三种模式下移动 Franka 机械臂触碰物体，感受:
    - Omega.7 力反馈的大小 / 有无
    - Franka 机械臂的"软硬"程度（阻抗刚度）
    - 自适应增益随"物体"变化的手感差异

模式手感设计:
    ┌────────┬─────────────────────────┬──────────────────────────────┐
    │ 模式   │ Omega.7 力反馈          │ Franka 阻抗手感              │
    ├────────┼─────────────────────────┼──────────────────────────────┤
    │ A(传统)│ 🔵 无力反馈 (透明模式)   │ 🧱 固定高刚度 200 N/m       │
    │ B(固定)│ 🟡 恒定增益 K=0.6        │ 🧱 固定高刚度 200 N/m       │
    │ C(自适应│ 🟢 变增益 K=0.2~1.0     │ 🫧 变刚度 50~300 N/m        │
    └────────┴─────────────────────────┴──────────────────────────────┘

    模式 C 内部自动循环 soft → medium → hard（每 6 秒切换一次），
    让操作员无需 YOLO 检测即可感受自适应参数变化带来的手感差异。

用法:
    python3 plans/test_modes_hand_feel.py [--start-mode a|b|c]

操作说明:
    - Omega.7 灰色按钮: 切换模式 A → B → C → A ...
    - 移动手柄: 控制 Franka 末端移动
    - 夹钳: 控制 Franka 夹爪抓取/松开
    - 模式 C 下，每 6 秒自动切换模拟物体 soft/medium/hard
      手动也可通过灰色**长按 2 秒**切换
    - Ctrl+C 安全退出

作者: mfj
日期: 2026-06
"""

import sys
import time
import threading
import ctypes
import argparse
from dataclasses import dataclass
import numpy as np
import forcedimension_core.dhd as dhd
import forcedimension_core.drd as drd
import panda_py
from panda_py import controllers, libfranka

sys.path.insert(0, "/home/mfj/sunhan")
from plans.force_estimator import ForceEstimator
from plans.force_feedback_scheduler import ForceFeedbackScheduler
from plans.adaptive_admittance import AdaptiveAdmittance
from plans.grip_force_estimator import GripForceEstimator

# ═══════════════════════════════════════════
# 配置参数
# ═══════════════════════════════════════════

ROBOT_IP = "192.168.1.51"

# Omega 映射
SCALE_POS = 3.0
SIGN = np.array([-1.0, -1.0, 1.0])

# 控制频率
CTRL_FREQ = 200.0         # 位置控制 (Hz)
GRIPPER_UPDATE_FREQ = 10.0

# 夹爪
GRIPPER_SPEED = 0.1
GRIPPER_MAX = 0.08
GRIPPER_HYSTERESIS = 0.01

# 模式 B 固定增益参数
MODE_B_K_TRANS = 0.6
MODE_B_DEADBAND = 0.4

# 模式 C 自适应参数 — 模拟三种物体的手感
#   soft:   低增益 + 低刚度  → 力反馈弱，机械臂软 → 接触时"柔"
#   medium: 中增益 + 中刚度  → 力反馈适中，机械臂适中
#   hard:   高增益 + 高刚度  → 力反馈强，机械臂硬 → 接触时"刚"
SOFT_PROFILE  = {"K_trans": 0.2, "deadband": 0.3, "admittance_K":  50.0, "label": "soft"}
MED_PROFILE   = {"K_trans": 0.5, "deadband": 0.4, "admittance_K": 150.0, "label": "medium"}
HARD_PROFILE  = {"K_trans": 1.0, "deadband": 0.5, "admittance_K": 300.0, "label": "hard"}
MODE_C_PROFILES = [SOFT_PROFILE, MED_PROFILE, HARD_PROFILE]

# 模式 C 物体自动切换间隔 (秒)
MODE_C_AUTO_SWITCH_INTERVAL = 6.0

# 按钮长按判定阈值 (秒)
BUTTON_LONG_PRESS_THRESHOLD = 2.0

# ═══════════════════════════════════════════
# 假 Profile（用于模式 C 的参数更新，无需 YOLO 检测）
# ═══════════════════════════════════════════

@dataclass
class FakePhysicsProfile:
    """与 PhysicsProfile 接口兼容的假 profile，用于手感测试"""
    K_trans: float = 0.4
    K_grip: float = 0.3
    F_target: float = 10.0
    deadband: float = 0.3
    admittance_K: float = 100.0
    approach_speed: float = 0.03
    label: str = "unknown"

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, d):
        return cls(**{k: d.get(k, v) for k, v in cls().__dict__.items()})


# ═══════════════════════════════════════════
# 默认阻抗
# ═══════════════════════════════════════════

DEFAULT_IMPEDANCE = np.diag([200.0, 200.0, 200.0, 10.0, 10.0, 10.0])


# ═══════════════════════════════════════════════════════
# 手感对比测试器
# ═══════════════════════════════════════════════════════

class ModeFeelTester:
    """
    手感对比测试器

    让操作员通过 Omega.7 依次体验三种模式的不同手感:
      - A: 无反馈 + 固定刚度（传统遥操作基准）
      - B: 有反馈 + 固定刚度（恒定力觉增益）
      - C: 自适应反馈 + 自适应刚度（本文方法）
    """

    def __init__(self):
        self.mode = "a"
        self.running = False

        # ── Omega.7 状态 ──
        self._omega_home = np.zeros(3)
        self._omega_grip = 0.0
        self._button_now = 0
        self._button_prev = 0
        self._button_released = False
        self._btn_press_start = 0.0    # 按钮按下起始时间
        self._btn_pressing = False     # 按钮正在被按下

        # ── 夹爪 ──
        self._last_gripper_cmd = GRIPPER_MAX
        self._last_gripper_time = 0.0
        self._grip_min = -30.0
        self._grip_max = 0.0

        # ── 模式 C 物体模拟 ──
        self._mc_idx = 0
        self._mc_last_switch = 0.0

        # ── 子模块 ──
        self.admittance: AdaptiveAdmittance = None
        self.feedback_sched: ForceFeedbackScheduler = None
        self.force_estimator: ForceEstimator = None
        self.grip_est: GripForceEstimator = None
        self.panda = None
        self.gripper = None
        self.ctrl = None

        # ── 状态打印 ──
        self._loop_count = 0
        self._F_haptic_current = np.zeros(3)

        print("\n" + "=" * 60)
        print("  🎮 共享控制三模式手感对比测试")
        print("=" * 60)

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

        # 5. Omega.7 标定 — 位置零点
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

        # 7. 子模块
        print("[初始化] 子模块 ...")
        self.force_estimator = ForceEstimator(self.panda, use_builtin=True)
        self.feedback_sched = ForceFeedbackScheduler()
        self.grip_est = GripForceEstimator()
        self.admittance = AdaptiveAdmittance(self.ctrl)

        # 应用起始模式的参数
        self._apply_mode_params()

        print("\n✅ 初始化完成\n")
        self._print_mode_info()

    # ═══════════════════════════════════════════
    # 模式管理
    # ═══════════════════════════════════════════

    def _apply_mode_params(self):
        """根据当前模式应用参数到子模块"""
        if self.mode == "a":
            # 模式 A: 默认高刚度，无力反馈调度
            self.ctrl.set_impedance(DEFAULT_IMPEDANCE)
            # 设置一个虚拟 profile，scheduler 仍可用但不影响手感
            dummy = FakePhysicsProfile(K_trans=0.0, deadband=999, admittance_K=200, label="mode_a")
            self.feedback_sched.set_profile(dummy)

        elif self.mode == "b":
            # 模式 B: 默认高刚度 + 固定增益力反馈
            self.ctrl.set_impedance(DEFAULT_IMPEDANCE)
            fb = FakePhysicsProfile(K_trans=MODE_B_K_TRANS, deadband=MODE_B_DEADBAND,
                                    admittance_K=200, label="mode_b")
            self.feedback_sched.set_profile(fb)

        else:  # mode "c"
            # 模式 C: 自适应刚度 + 自适应力反馈
            prof_dict = MODE_C_PROFILES[self._mc_idx]
            fp = FakePhysicsProfile(
                K_trans=prof_dict["K_trans"],
                deadband=prof_dict["deadband"],
                admittance_K=prof_dict["admittance_K"],
                label=prof_dict["label"],
            )
            self.admittance.apply_profile(fp)
            self.feedback_sched.set_profile(fp)

    def _switch_mode(self):
        """切换模式: A → B → C → A"""
        next_map = {"a": "b", "b": "c", "c": "a"}
        self.mode = next_map[self.mode]
        self._apply_mode_params()
        self._print_mode_info()

    def _next_mode_c_object(self):
        """切换模式 C 的模拟物体: soft → medium → hard → soft"""
        self._mc_idx = (self._mc_idx + 1) % len(MODE_C_PROFILES)
        prof_dict = MODE_C_PROFILES[self._mc_idx]
        fp = FakePhysicsProfile(
            K_trans=prof_dict["K_trans"],
            deadband=prof_dict["deadband"],
            admittance_K=prof_dict["admittance_K"],
            label=prof_dict["label"],
        )
        self.admittance.apply_profile(fp)
        self.feedback_sched.set_profile(fp)
        print(f"\n  🔄 模式 C 切换模拟物体 → \033[1m{prof_dict['label'].upper()}\033[0m "
              f"(K_trans={prof_dict['K_trans']:.1f}, "
              f"admittance_K={prof_dict['admittance_K']:.0f} N/m)\n")
        self._mc_last_switch = time.time()

    def _print_mode_info(self):
        """打印当前模式的详细说明"""
        mode_names = {"a": "传统遥操作", "b": "固定增益", "c": "本文方法（自适应）"}
        mode_icons = {"a": "🔵", "b": "🟡", "c": "🟢"}
        fb_desc = {
            "a": "❌ 力反馈关闭 — Omega.7 透明模式，无任何阻力",
            "b": f"📌 固定力反馈 K_trans={MODE_B_K_TRANS} — 接触力 × 0.6 恒定映射到 Omega.7",
            "c": "📊 自适应力反馈 K_trans=0.2~1.0 — 软物体力反馈弱，硬物体力反馈强",
        }
        imp_desc = {
            "a": "🧱 固定高刚度 200 N/m — 机械臂很硬",
            "b": "🧱 固定高刚度 200 N/m — 机械臂很硬",
            "c": "🫧 自适应刚度 50~300 N/m — 软物体机械臂柔顺，硬物体机械臂刚硬",
        }
        icon = mode_icons[self.mode]
        name = mode_names[self.mode]

        print(f"\n{'=' * 65}")
        print(f"  {icon}  当前模式: \033[1m{self.mode.upper()} — {name}\033[0m")
        print(f"  ├─ Omega.7 手柄: {fb_desc[self.mode]}")
        print(f"  └─ Franka 机械臂: {imp_desc[self.mode]}")

        if self.mode == "c":
            pd = MODE_C_PROFILES[self._mc_idx]
            progress = " | ".join(
                f"{'🟢' if i == self._mc_idx else '○'} {p['label'].upper()}"
                for i, p in enumerate(MODE_C_PROFILES)
            )
            print(f"\n     模拟物体: [{progress}]")
            print(f"     当前: \033[1m{pd['label'].upper()}\033[0m → "
                  f"K_trans={pd['K_trans']:.1f}, 死区={pd['deadband']:.1f}N, "
                  f"刚度={pd['admittance_K']:.0f} N/m")
            print(f"     自动切换: 每 {MODE_C_AUTO_SWITCH_INTERVAL}s 轮换一次")

        print(f"\n  🕹️  操作:")
        print(f"    单击灰色按钮 → 切换模式 A→B→C→A")
        if self.mode == "c":
            print(f"    长按灰色按钮 (>2s) → 手动切换模式 C 的模拟物体")
        print(f"    移动手柄 → 控制 Franka 末端位置")
        print(f"    捏合/松开夹钳 → 夹爪开合")
        print(f"    Ctrl+C → 安全停止")
        print(f"{'=' * 65}\n")

    # ═══════════════════════════════════════════
    # 主控制循环
    # ═══════════════════════════════════════════

    def run(self):
        """主控制循环 (200 Hz)"""
        self.running = True
        dt = 1.0 / CTRL_FREQ
        dt_gripper = 1.0 / GRIPPER_UPDATE_FREQ

        # 模式 C 自动切换定时器
        self._mc_last_switch = time.time()

        print("\n  🚀 测试已启动！请握住 Omega.7 手柄开始体验\n")
        print("  💡 建议: 移动 Franka 去触碰桌面/物体/另一只手，")
        print("     感受不同模式下 Omega.7 力反馈和机械臂刚度的差异。\n")

        try:
            while True:
                t_start = time.perf_counter()
                now = time.time()

                # ── 1. 读 Omega.7 位置 ──
                raw_pos = np.zeros(3)
                dhd.getPosition(raw_pos)

                # ── 2. 读 Franka 状态 + 外力估计 ──
                state = self.panda.get_state()
                tau_ext = np.array(state.tau_ext_hat_filtered, dtype=float)
                F_ext = self.force_estimator.update(state)

                # ── 3. 按钮状态机 ──
                self._button_now = dhd.getButton(0)

                if self._button_now == 1 and self._button_prev == 0:
                    # 按钮被按下（下降沿），记录开始时间
                    self._btn_press_start = now
                    self._btn_pressing = True

                elif self._button_now == 0 and self._button_prev == 1:
                    # 按钮被释放（上升沿）
                    press_duration = now - self._btn_press_start
                    self._btn_pressing = False

                    if press_duration < BUTTON_LONG_PRESS_THRESHOLD:
                        # 短按 → 切换模式
                        self._switch_mode()
                    else:
                        # 长按 → 仅在模式 C 下切换模拟物体
                        if self.mode == "c":
                            self._next_mode_c_object()
                        else:
                            print("  长按仅在模式 C 下有效（切换模拟物体）")

                self._button_prev = self._button_now

                # ── 4. 夹爪控制 (降频) ──
                if (now - self._last_gripper_time) >= dt_gripper:
                    self._update_gripper()

                # ── 5. 力反馈计算 (按模式) ──
                if self.mode == "a":
                    # 模式 A: 零力反馈 (透明模式)
                    F_haptic = np.zeros(3)

                elif self.mode == "b":
                    # 模式 B: 固定增益
                    F_haptic = self.feedback_sched.compute(F_ext)

                else:  # mode "c"
                    # 模式 C: 自适应力反馈
                    F_haptic = self.feedback_sched.compute(F_ext)

                    # 自动切换模拟物体
                    if (now - self._mc_last_switch) >= MODE_C_AUTO_SWITCH_INTERVAL:
                        self._next_mode_c_object()

                self._F_haptic_current = F_haptic
                dhd.setForce(F_haptic)

                # ── 6. 位置映射 → Franka ──
                delta = raw_pos - self._omega_home
                target_pos = self._virtual_ref + delta * SCALE_POS * SIGN
                self.ctrl.set_control(target_pos, self._init_ori)

                # ── 7. 状态打印 (5 Hz) ──
                self._loop_count += 1
                if self._loop_count % (CTRL_FREQ // 5) == 0:
                    self._print_status(F_ext[:3], F_haptic)

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
    # 夹爪控制
    # ═══════════════════════════════════════════

    def _update_gripper(self):
        """夹爪控制 (10Hz)"""
        gripper_angle = ctypes.c_double()
        dhd.getGripperAngleDeg(gripper_angle)
        raw = gripper_angle.value
        self._omega_grip = raw

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

        if self._button_now:
            target_width = GRIPPER_MAX

        if abs(target_width - self._last_gripper_cmd) > GRIPPER_HYSTERESIS:
            threading.Thread(
                target=self._gripper_cmd_thread,
                args=(target_width,),
                daemon=True,
            ).start()
            self._last_gripper_cmd = target_width

        self._last_gripper_time = time.time()

    def _gripper_cmd_thread(self, width: float):
        """线程内执行 stop+move，不阻塞主循环"""
        try:
            try:
                self.gripper.stop()
            except Exception:
                pass
            self.gripper.move(width, GRIPPER_SPEED)
        except Exception as e:
            print(f"   ⚠️ 夹爪 cmd 异常 ({width:.3f}): {e}")

    # ═══════════════════════════════════════════
    # 状态打印
    # ═══════════════════════════════════════════

    def _print_status(self, F_ext: np.ndarray, F_haptic: np.ndarray):
        """每 0.2s 打印一次运行状态"""
        mode_icon = {"a": "🔵A", "b": "🟡B", "c": "🟢C"}
        icon = mode_icon.get(self.mode, "⚪")

        fn = np.linalg.norm(F_ext)
        fhn = np.linalg.norm(F_haptic)

        # 模式 C 额外显示当前模拟物体
        extra = ""
        if self.mode == "c":
            pd = MODE_C_PROFILES[self._mc_idx]
            rem = MODE_C_AUTO_SWITCH_INTERVAL - (time.time() - self._mc_last_switch)
            extra = f" | {pd['label'].upper()} (⏱{rem:.0f}s)"

        print(f"[{self._loop_count:>6}] {icon} "
              f"|F_ext|={fn:5.2f}N  "
              f"|F_fb|={fhn:5.2f}N  "
              f"F_fb=({F_haptic[0]:+.2f},{F_haptic[1]:+.2f},{F_haptic[2]:+.2f})"
              f"{extra}")

    # ═══════════════════════════════════════════
    # 安全关闭
    # ═══════════════════════════════════════════

    def _shutdown(self):
        """安全关闭所有硬件"""
        self.running = False
        print("\n   关闭 Omega.7 力输出...")
        dhd.setForce(np.zeros(3))
        dhd.close()
        print("✅ 已安全停止")


# ═══════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="三模式手感对比测试")
    parser.add_argument(
        "--start-mode", type=str, default="a",
        choices=["a", "b", "c"],
        help="起始模式: a=传统(默认), b=固定增益, c=自适应",
    )
    args = parser.parse_args()

    tester = ModeFeelTester()
    tester.mode = args.start_mode
    tester.initialize()
    tester.run()


if __name__ == "__main__":
    main()
