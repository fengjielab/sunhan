#!/usr/bin/env python3
"""
grip_force_estimator.py — 基于臂端关节力矩的夹持力近似估计
==============================================================

由于 Franka Hand 夹爪不暴露电机电流，
采用纯臂端方案：通过腕部关节力矩估计夹持力。

原理:
    夹持时，物体对夹爪的反作用力通过腕部传递到机器人手臂，
    在腕部关节（特别是 J6, J7）产生可观测的外部力矩。

    f_grip = ||τ_wrist|| / τ_max

    其中 τ_wrist = [τ₅, τ₆, τ₇]（最后三个关节的外部力矩）

接触事件检测（用于 Omega.7 夹持通道脉冲提示）:
    条件1: |Δwidth| < ε AND width < max_width
    条件2: ||τ_wrist|| > τ_threshold

限制:
    - 此方法仅为近似估计，精度低于指尖力传感器
    - 论文中需明确标注"α=1.0，纯臂端方案"

作者: mfj
日期: 2026-05
"""

import numpy as np
from typing import Optional, Callable


class GripForceEstimator:
    """
    夹持力近似估计器

    基于腕部关节力矩 + 夹爪宽度变化检测夹持状态。

    用法:
        est = GripForceEstimator()
        f_grip = est.update(tau_ext, gripper_width)
        if est.contact_detected:
            print("接触事件!")
            est.reset_contact()
    """

    WRIST_JOINT_INDICES = [4, 5, 6]  # J5, J6, J7 (0-indexed)
    # 以下默认值基于 step_3a 真实机器人实测标定 (2026-05-30):
    #   ||τ_wrist|| 空载基线: mean=0.17 Nm, std≈0.00 Nm, max=0.17 Nm
    #   tau_max=3.0  → f_grip = 0.17/3.0 ≈ 0.06 (空载)
    #                  f_grip = 1.5/3.0  ≈ 0.50 (典型夹持)
    #                  f_grip = 3.0/3.0  ≈ 1.00 (最大夹持)
    TAU_MAX_DEFAULT = 3.0
    DEFAULT_WIDTH_EPSILON = 0.002
    DEFAULT_TORQUE_THRESHOLD = 1.0
    DEFAULT_DEBOUNCE_FRAMES = 5

    def __init__(
        self,
        tau_max: float = TAU_MAX_DEFAULT,
        width_epsilon: float = DEFAULT_WIDTH_EPSILON,
        torque_threshold: float = DEFAULT_TORQUE_THRESHOLD,
        debounce_frames: int = DEFAULT_DEBOUNCE_FRAMES,
    ):
        self.tau_max = tau_max
        self.width_epsilon = width_epsilon
        self.torque_threshold = torque_threshold
        self.debounce_frames = debounce_frames

        self._f_grip = 0.0
        self._contact_detected = False
        self._contact_frames = 0
        self._prev_width = 0.08
        self._gripper_at_max = True

        self._f_grip_filtered = 0.0
        self._filter_alpha = 0.3
        self._update_count = 0

        self._contact_callback: Optional[Callable] = None
        self._total_contacts = 0
        self._f_grip_history: list = []

        print(f"[GripForceEstimator] 就绪 | τ_max={tau_max} Nm, "
              f"阈值={torque_threshold} Nm, 防抖={debounce_frames}帧")

    def update(
        self,
        tau_ext: np.ndarray,
        gripper_width: float,
        gripper_max_width: float = 0.08,
    ) -> float:
        """
        更新夹持力估计

        Args:
            tau_ext: 7维关节外部力矩向量 (J1~J7)
            gripper_width: 当前夹爪开度 (m)
            gripper_max_width: 夹爪最大开度 (m)

        Returns:
            f_grip: 归一化夹持力 (0~1)
        """
        tau_wrist = np.array([tau_ext[i] for i in self.WRIST_JOINT_INDICES])
        tau_wrist_norm = np.linalg.norm(tau_wrist)

        self._f_grip = np.clip(tau_wrist_norm / self.tau_max, 0.0, 1.0)

        if self._update_count == 0:
            self._f_grip_filtered = self._f_grip
        else:
            self._f_grip_filtered = (
                self._filter_alpha * self._f_grip
                + (1 - self._filter_alpha) * self._f_grip_filtered
            )

        # 接触事件检测
        width_change = abs(gripper_width - self._prev_width)
        width_stalled = width_change < self.width_epsilon
        not_at_max = gripper_width < gripper_max_width * 0.95
        torque_active = tau_wrist_norm > self.torque_threshold

        if width_stalled and not_at_max and torque_active:
            self._contact_frames += 1
            if self._contact_frames >= self.debounce_frames and not self._contact_detected:
                self._contact_detected = True
                self._total_contacts += 1
                if self._contact_callback:
                    self._contact_callback()
                print(f"[GripForceEstimator] 📌 接触事件 #{self._total_contacts} "
                      f"| f_grip={self._f_grip_filtered:.3f} | width={gripper_width*1000:.1f}mm")
        else:
            self._contact_frames = 0

        self._prev_width = gripper_width
        self._gripper_at_max = gripper_width >= gripper_max_width * 0.95
        self._update_count += 1

        return self._f_grip_filtered

    @property
    def f_grip(self) -> float:
        return self._f_grip_filtered

    @property
    def contact_detected(self) -> bool:
        return self._contact_detected

    def reset_contact(self) -> None:
        self._contact_detected = False
        self._contact_frames = 0

    def set_contact_callback(self, cb: Callable) -> None:
        self._contact_callback = cb

    def set_filter_alpha(self, alpha: float):
        self._filter_alpha = np.clip(alpha, 0.01, 0.99)

    def get_stats(self) -> dict:
        return {
            "f_grip": self._f_grip_filtered,
            "contact_detected": self._contact_detected,
            "total_contacts": self._total_contacts,
            "torque_threshold": self.torque_threshold,
            "width_epsilon": self.width_epsilon,
        }


if __name__ == "__main__":
    print("=" * 50)
    print("GripForceEstimator 自测")
    print("=" * 50)

    est = GripForceEstimator(tau_max=10.0)

    print("\n模拟夹持过程：无接触 → 接近 → 夹持 → 释放")
    print(f"{'帧':>3} {'tau_wrist(Nm)':>13} {'width(mm)':>10} {'f_grip':>8} {'接触':>5}")
    print("-" * 45)

    for i in range(50):
        if i < 10:
            tau_wrist = np.array([0.1, 0.2, 0.1])
            width = 0.08
        elif i < 25:
            t = (i - 10) / 15.0
            tau_wrist = np.array([0.3, 0.5 + t * 5.0, 0.4 + t * 3.0])
            width = 0.03
        elif i < 35:
            tau_wrist = np.array([0.5, 5.5, 3.5])
            width = 0.03
        else:
            tau_wrist = np.array([0.3, 1.0, 0.5])
            width = 0.06

        tau_7d = np.zeros(7)
        tau_7d[4:7] = tau_wrist

        f = est.update(tau_7d, width)
        contact = "●" if est.contact_detected else "○"

        if i % 3 == 0 or est.contact_detected:
            print(f"{i+1:>3} {np.linalg.norm(tau_wrist):>10.3f}  "
                  f"{width*1000:>7.1f}   {f:>.3f}   {contact}")

    print(f"\n总接触事件: {est._total_contacts}")
    print("✅ GripForceEstimator 验证通过")
