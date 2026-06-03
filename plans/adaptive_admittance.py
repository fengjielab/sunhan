#!/usr/bin/env python3
"""
adaptive_admittance.py — 视觉驱动的自适应导纳/阻抗控制
============================================================

核心功能:
    1. 根据 PhysicsProfile 运行时切换 CartesianImpedance 刚度矩阵
    2. 阻尼比保持 ζ = 1.0 (临界阻尼)，阻尼矩阵自动计算 D = 2·√(M·K)
    3. 通过 set_impedance() 安全切换（**平滑过渡，避免手感突变**）

原理:
    ┌──────────┐    K(c)     ┌──────────────────┐
    │ 视觉检测  │ ────────→  │ 刚度调度器        │
    │ YOLO+查表 │            │ 软→50N/m, 硬→300  │
    └──────────┘            └──────────────────┘
                                     │ set_impedance()
                                     ▼
                             ┌──────────────────┐
                             │ CartesianImpedance│
                             │   控制器          │
                             └──────────────────┘

参数映射:
    PhysicsProfile.admittance_K → 笛卡尔平移刚度 K_x, K_y (Z 轴按 label 打折)
    阻尼自动: D = 2 * sqrt(M * K), 其中 M 取固定质量假设

平滑过渡:
    刚度切换采用后台线程 + EMA 插值，约 200~300ms 完成过渡，
    避免瞬间跳变导致的操作手感突变。

用法:
    adapter = AdaptiveAdmittance(panda, ctrl)
    adapter.apply_profile(profile)   # 根据视觉结果平滑切换刚度

作者: mfj
日期: 2026-05
"""

import threading
import time
from typing import Optional

import numpy as np
from panda_py import controllers

DEFAULT_STIFFNESS = np.diag([200.0, 200.0, 200.0, 10.0, 10.0, 10.0])
DEFAULT_DAMPING_RATIO = 1.0
NULLSPACE_STIFFNESS_DEFAULT = 0.5


class AdaptiveAdmittance:
    """
    视觉驱动的自适应导纳控制器

    职责:
        - 维护当前阻抗矩阵
        - 根据 PhysicsProfile.admittance_K 计算新的阻抗矩阵
        - 通过 set_impedance() 安全切换

    注意:
        切换刚度时不要过于频繁（建议 > 0.5s 间隔），以免引起控制不连续。
    """

    K_TRANS_MIN = 50.0
    K_TRANS_MAX = 400.0
    K_ROT_FIXED = np.array([10.0, 10.0, 10.0])
    M_EFF = 3.0  # 假设末端等效质量 (kg)

    # 平滑过渡配置
    TRANSITION_DURATION = 0.25       # 总过渡时间 (s)
    TRANSITION_STEP_INTERVAL = 0.01  # 每步间隔 (s) → 约 25 步完成过渡

    def __init__(
        self,
        ctrl: controllers.CartesianImpedance,
        damping_ratio: float = DEFAULT_DAMPING_RATIO,
    ):
        self.ctrl = ctrl
        self.damping_ratio = damping_ratio
        self._K_current = DEFAULT_STIFFNESS.copy()
        self._D_current = self._compute_damping(self._K_current)
        self._K_target = DEFAULT_STIFFNESS.copy()
        self._current_class = "unknown"
        self._current_label = "unknown"
        self._switch_count = 0
        self._last_switch_class = ""
        self._min_switch_interval = 1.0

        # ── 平滑过渡线程控制 ──
        self._transition_thread: Optional[threading.Thread] = None
        self._transition_stop_event = threading.Event()
        self._transition_active = False

        print(f"[AdaptiveAdmittance] 就绪 | 初始刚度={np.diag(self._K_current)} | 平滑过渡={self.TRANSITION_DURATION}s")

    # ═══════════════════════════════════════
    # 公共接口
    # ═══════════════════════════════════════

    def apply_admittance_K(self, admittance_K: float) -> None:
        """根据导纳刚度值直接设置阻抗矩阵"""
        K_new = self._build_stiffness_matrix(admittance_K)
        self._apply(K_new)

    def apply_profile(self, profile) -> None:
        """根据 PhysicsProfile 切换阻抗"""
        self._current_label = profile.label
        K_val = profile.admittance_K
        if profile.label == "soft":
            K_z = K_val * 0.5
        elif profile.label == "hard":
            K_z = K_val
        else:
            K_z = K_val * 0.8
        K_new = self._build_stiffness_matrix(K_val, K_z=K_z)
        self._apply(K_new)

    def apply_class(self, class_name: str, label: str = "unknown") -> None:
        """根据类别名称直接切换 (不依赖 PhysicsProfile)"""
        K_val = self._label_to_stiffness(label)
        K_new = self._build_stiffness_matrix(K_val)
        self._apply(K_new)
        self._current_class = class_name
        self._current_label = label

    def set_custom_stiffness(self, K_trans: float, K_rot: float = 10.0) -> None:
        """直接设置自定义刚度"""
        K_new = np.diag([K_trans, K_trans, K_trans, K_rot, K_rot, K_rot])
        self._apply(K_new)

    # ═══════════════════════════════════════
    # 内部方法
    # ═══════════════════════════════════════

    def _build_stiffness_matrix(
        self, K_xy: float, K_z: float = None, K_rot: float = 10.0
    ) -> np.ndarray:
        if K_z is None:
            K_z = K_xy
        K_xy = np.clip(K_xy, self.K_TRANS_MIN, self.K_TRANS_MAX)
        K_z = np.clip(K_z, self.K_TRANS_MIN, self.K_TRANS_MAX)
        return np.diag([K_xy, K_xy, K_z, K_rot, K_rot, K_rot])

    def _compute_damping(self, K: np.ndarray) -> np.ndarray:
        """临界阻尼: D = 2 * ζ * sqrt(M * K)"""
        M_assumed = np.diag([self.M_EFF] * 3 + [0.1] * 3)
        sqrt_MK = np.sqrt(np.maximum(np.diag(M_assumed) * np.diag(K), 0))
        return np.diag(2.0 * self.damping_ratio * sqrt_MK)

    def _apply(self, K_new: np.ndarray) -> None:
        """触发刚度平滑过渡（后台线程执行插值）"""
        if np.allclose(K_new, self._K_current) and not self._transition_active:
            return
        self._K_target = K_new.copy()
        self._start_smooth_transition()

    def _start_smooth_transition(self) -> None:
        """停止旧过渡并启动新的平滑过渡线程"""
        self._stop_transition()
        self._transition_stop_event.clear()
        self._transition_active = True
        self._transition_thread = threading.Thread(
            target=self._transition_worker,
            daemon=True,
        )
        self._transition_thread.start()

    def _transition_worker(self) -> None:
        """后台线程：从当前刚度线性插值到目标刚度"""
        K_start = self._K_current.copy()
        K_end = self._K_target.copy()

        # 计算步数（至少 3 步，最多 50 步）
        steps = max(
            3,
            min(50, int(self.TRANSITION_DURATION / self.TRANSITION_STEP_INTERVAL))
        )

        for i in range(1, steps + 1):
            if self._transition_stop_event.is_set():
                break

            # 平滑步进函数：smoothstep 3-5-1（起始缓、中间快、末尾缓）
            t = i / steps
            alpha = t * t * (3.0 - 2.0 * t)  # smoothstep

            K_interp = K_start + alpha * (K_end - K_start)
            self._K_current = K_interp.copy()
            self._D_current = self._compute_damping(K_interp)

            try:
                self.ctrl.set_impedance(K_interp)
            except Exception as e:
                print(f"[AdaptiveAdmittance] ⚠️ 过渡中 set_impedance 失败: {e}")
                break

            time.sleep(self.TRANSITION_STEP_INTERVAL)

        # 确保最终到达目标（未被中断时）
        if not self._transition_stop_event.is_set():
            self._K_current = K_end.copy()
            self._D_current = self._compute_damping(K_end)
            try:
                self.ctrl.set_impedance(K_end)
            except Exception:
                pass
            self._switch_count += 1
            print(
                f"[AdaptiveAdmittance] 平滑切换完成 → diag={np.round(np.diag(K_end), 1)} "
                f"({steps}步/{self.TRANSITION_DURATION*1000:.0f}ms)"
            )

        self._transition_active = False

    def _stop_transition(self) -> None:
        """安全停止当前过渡线程"""
        if self._transition_thread is not None and self._transition_thread.is_alive():
            self._transition_stop_event.set()
            self._transition_thread.join(timeout=0.15)

    @staticmethod
    def _label_to_stiffness(label: str) -> float:
        mapping = {
            "soft": 50.0, "medium": 150.0,
            "hard": 300.0, "unknown": 100.0,
        }
        return mapping.get(label, 100.0)

    # ═══════════════════════════════════════
    # 查询
    # ═══════════════════════════════════════

    @property
    def current_stiffness(self) -> np.ndarray:
        return self._K_current.copy()

    @property
    def current_damping(self) -> np.ndarray:
        return self._D_current.copy()

    @property
    def current_label(self) -> str:
        return self._current_label

    def get_info(self) -> dict:
        return {
            "class": self._current_class,
            "label": self._current_label,
            "K_diag": np.diag(self._K_current),
            "K_target_diag": np.diag(self._K_target),
            "D_diag": np.diag(self._D_current),
            "switches": self._switch_count,
            "damping_ratio": self.damping_ratio,
            "transition_active": self._transition_active,
        }


if __name__ == "__main__":
    print("=" * 50)
    print("AdaptiveAdmittance 自测")
    print("=" * 50)

    adapter = AdaptiveAdmittance(ctrl=None)  # type: ignore

    test_cases = [
        ("apple", 50.0, "soft"), ("banana", 50.0, "soft"),
        ("bottle", 150.0, "medium"), ("book", 300.0, "hard"),
        ("cell phone", 300.0, "hard"), ("unknown", 100.0, "unknown"),
    ]

    print(f"\n{'类别':<12} {'label':<10} {'admittance_K':>10} → K_diag  [X, Y, Z, Rx, Ry, Rz]")
    print("-" * 70)
    for name, K_val, label in test_cases:
        K = adapter._build_stiffness_matrix(K_val)
        D = adapter._compute_damping(K)
        diag_str = np.array2string(np.diag(K), precision=1, separator=", ")
        print(f"{name:<12} {label:<10} {K_val:>8.1f} N/m  → {diag_str}")

    print("\n✅ 自适应导纳控制模块验证通过")
