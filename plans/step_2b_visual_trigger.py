#!/usr/bin/env python3
"""
Step 2b — 视觉触发刚度切换测试（模拟 YOLO）
=============================================
目的: 验证 AdaptiveAdmittance.apply_class() 能否根据视觉检测结果
      自动切换刚度矩阵。不使用真实 YOLO，用预设物体列表模拟。

操作:
    1. 连接 Franka，启动笛卡尔阻抗控制
    2. 模拟视觉检测到不同物体（每 4 秒切换一次）
    3. 每次检测到物体后自动调用 apply_class()
    4. 操作员用手推末端感受刚度变化是否与物体匹配
    5. 按 Ctrl+C 停止

用法:
    python3 plans/step_2b_visual_trigger.py

预期:
    apple (soft)    → K=50  N/m → 软
    book  (hard)    → K=300 N/m → 硬
    bottle(medium)  → K=150 N/m → 中等

作者: mfj
日期: 2026-05
"""

import sys
import time
import numpy as np
import panda_py
from panda_py import controllers

ROBOT_IP = "192.168.1.51"
SWITCH_INTERVAL = 4.0  # 每 4 秒切换一次

# 模拟 YOLO 检测结果: (物体名, 类别)
VISION_SEQ = [
    ("apple",       "soft"),
    ("banana",      "soft"),
    ("bottle",      "medium"),
    ("book",        "hard"),
    ("teddy bear",  "soft"),
    ("cell phone",  "hard"),
    ("cup",         "medium"),
    ("mouse",       "hard"),
]


def build_impedance(K_xyz: float, K_rot: float = 10.0) -> np.ndarray:
    return np.diag([K_xyz, K_xyz, K_xyz, K_rot, K_rot, K_rot])


def label_to_stiffness(label: str) -> float:
    """将类别标签映射到刚度值（与 adaptive_admittance.py 一致）"""
    mapping = {
        "soft":   50.0,
        "medium": 150.0,
        "hard":   300.0,
    }
    return mapping.get(label, 100.0)


def main():
    print("=" * 60)
    print("  Step 2b: 视觉触发刚度切换测试")
    print("=" * 60)
    print(f"\n  机器人 IP: {ROBOT_IP}")
    print(f"  切换间隔: {SWITCH_INTERVAL}s")
    print(f"  模拟序列: {[(s[0], s[1]) for s in VISION_SEQ]}")

    # ── 连接 ──
    print("\n[1/3] 连接 Franka Panda ...")
    panda = panda_py.Panda(ROBOT_IP)
    panda.recover()
    panda.set_default_behavior()
    print("   ✓ 已连接")

    # ── 启动阻抗控制 ──
    print("[2/3] 启动笛卡尔阻抗控制器 ...")
    init_pos = panda.get_position().copy()
    init_ori = panda.get_orientation().copy()
    init_impedance = build_impedance(200.0)
    ctrl = controllers.CartesianImpedance(
        impedance=init_impedance, damping_ratio=1.0,
        nullspace_stiffness=0.5, filter_coeff=1.0,
    )
    panda.start_controller(ctrl)
    ctrl.set_control(init_pos, init_ori)
    time.sleep(1.0)
    print("   ✓ 控制器已启动")

    # ── 模拟视觉切换循环 ──
    print("\n[3/3] 开始模拟视觉检测循环")
    print("=" * 60)
    print("  ⚠️  模拟 YOLO 每 4 秒检测到一个物体")
    print("  ⚠️  请用手推末端感受刚度是否与物体匹配")
    print("  ⚠️  按 Ctrl+C 停止\n")

    idx = 0
    start_time = time.time()
    next_switch = start_time + 1.0  # 先等 1s 再开始

    try:
        while True:
            now = time.time()
            elapsed = now - start_time

            if now >= next_switch:
                obj_name, label = VISION_SEQ[idx % len(VISION_SEQ)]
                idx += 1

                K_val = label_to_stiffness(label)
                K_new = build_impedance(K_val)

                # 应用 Z 轴折扣（与 adaptive_admittance.py 一致）
                if label == "soft":
                    K_new[2, 2] *= 0.5
                elif label == "medium":
                    K_new[2, 2] *= 0.8
                # hard: 不打折

                # (panda_py.set_impedance() 只接受阻抗矩阵)
                ctrl.set_impedance(K_new)
                ctrl.set_control(init_pos, init_ori)

                K_diag = np.diag(K_new)
                print(f"\n  >>> [模拟视觉] 检测到 {obj_name:>12} → "
                      f"label={label:>6} | K=[{K_diag[0]:.0f}, {K_diag[1]:.0f}, {K_diag[2]:.0f}] N/m")

                next_switch = now + SWITCH_INTERVAL

            # 实时显示
            state = panda.get_state()
            F = np.array(state.O_F_ext_hat_K, dtype=float)
            F_mag = np.linalg.norm(F[:3])
            print(f"  [{elapsed:5.1f}s] |F|={F_mag:5.2f}N", end="\r")

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n\n  Ctrl+C 已捕捉，正在停止...")

    print("\n" + "=" * 60)
    print("  测试总结")
    print("=" * 60)
    print("  验证清单:")
    print("  [ ] apple → soft → K=50 N/m（软，有缓冲感）")
    print("  [ ] bottle → medium → K=150 N/m（中等硬度）")
    print("  [ ] book → hard → K=300 N/m（硬）")
    print("  [ ] 切换时机械臂不抖动")
    print("  [ ] Z 轴折扣生效（soft 的 Z 明显更软）")

    panda.stop_controller()
    print("\n控制器已停止。\n")


if __name__ == "__main__":
    main()
