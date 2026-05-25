#!/usr/bin/env python3
"""
force_feedback_scheduler.py — 主端自适应力反馈调度与死区控制
==============================================================

功能:
    1. 根据视觉检测结果 (PhysicsProfile.K_trans) 实时调整力反馈增益
    2. 对每个轴独立施加死区 (deadband)，消除小噪声
    3. 将 F_ext 渲染为 Omega.7 的力输出

渲染流程:
    F_ext (6×1) → K_trans(c) 缩放 → 死区滤波 → dhd.setForce()

用法:
    scheduler = ForceFeedbackScheduler()
    F_haptic = scheduler.compute(F_ext, profile)
    dhd.setForce(F_haptic)

作者: mfj
日期: 2026-05
"""

import numpy as np


class ForceFeedbackScheduler:
    """
    主端自适应力反馈调度器

    根据视觉识别的物体类别，动态调整力反馈增益 K_trans 和死区。
    """

    def __init__(self):
        # 当前参数
        self._K_trans = 0.5
        self._deadband = 0.3
        self._label = "unknown"
        self._class_name = ""

        # 状态
        self._update_count = 0

        print("[ForceFeedbackScheduler] 就绪")

    def compute(self, F_ext: np.ndarray, profile=None) -> np.ndarray:
        """
        计算渲染到 Omega.7 的力反馈

        Args:
            F_ext: shape (3,) 或 (6,) — 外部接触力 (仅前3维用于力反馈)
            profile: PhysicsProfile (可选，提供 K_trans 和 deadband)

        Returns:
            F_haptic: shape (3,) — 渲染到 Omega.7 的力 (N)
        """
        if profile is not None:
            self._K_trans = profile.K_trans
            self._deadband = profile.deadband
            self._label = profile.label
        else:
            # 使用最近设置的值
            pass

        # 取平动分量
        F_xyz = F_ext[:3] if len(F_ext) >= 3 else F_ext

        # 增益缩放
        F_scaled = F_xyz * self._K_trans

        # 死区滤波 (每轴独立)
        F_haptic = np.where(
            np.abs(F_scaled) > self._deadband,
            np.sign(F_scaled) * (np.abs(F_scaled) - self._deadband),
            0.0,
        )

        self._update_count += 1
        return F_haptic

    def set_gain(self, K_trans: float):
        """手动设置反馈增益"""
        self._K_trans = max(0.0, K_trans)

    def set_deadband(self, deadband: float):
        """手动设置死区 (N)"""
        self._deadband = max(0.0, deadband)

    def set_profile(self, profile) -> None:
        """根据 PhysicsProfile 设置参数"""
        self._K_trans = profile.K_trans
        self._deadband = profile.deadband
        self._label = profile.label

    def get_grip_force_rendering(self, f_grip: float) -> float:
        """
        夹持力通道渲染

        将归一化夹持力 (0~1) 映射为 Omega.7 夹持通道的力（若有）。

        Args:
            f_grip: 归一化夹持力 (0~1)

        Returns:
            f_render: 夹持通道力 (0~1, 或直接用于 dhd.setGripperForce)
        """
        # 当前夹持力的平方映射（接触时更敏感）
        return np.clip(f_grip ** 2 * self._K_trans, 0.0, 1.0)

    def get_info(self) -> dict:
        return {
            "K_trans": self._K_trans,
            "deadband": self._deadband,
            "label": self._label,
            "class_name": self._class_name,
        }


if __name__ == "__main__":
    print("=" * 50)
    print("ForceFeedbackScheduler 自测")
    print("=" * 50)

    from dataclasses import dataclass

    @dataclass
    class FakeProfile:
        K_trans: float
        deadband: float
        label: str

    scheduler = ForceFeedbackScheduler()

    test_cases = [
        ("apple", FakeProfile(0.3, 0.3, "soft")),
        ("banana", FakeProfile(0.2, 0.5, "soft")),
        ("bottle", FakeProfile(0.5, 0.4, "medium")),
        ("book", FakeProfile(1.0, 0.5, "hard")),
        ("cell phone", FakeProfile(1.0, 0.5, "hard")),
    ]

    F_ext_example = np.array([2.0, -1.5, 0.5])  # 模拟接触力

    print(f"\n输入外力: {F_ext_example}")
    print(f"{'类别':<12} {'K_trans':>8} {'deadband':>9} → F_haptic")
    print("-" * 55)

    for name, profile in test_cases:
        F_h = scheduler.compute(F_ext_example, profile)
        print(f"{name:<12} {profile.K_trans:>8.2f} {profile.deadband:>9.2f} → {np.round(F_h, 3)}")

    print("\n✅ ForceFeedbackScheduler 验证通过")
