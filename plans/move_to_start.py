#!/usr/bin/env python3
"""
将 Franka 机械臂移动到初始位置（JOINT_POSITION_START）。

⚠️ 关键要点：
  1. 放大碰撞阈值 → 避免 cartesian_reflex 打断运动
  2. 降低关节刚度 → 力矩柔和，不触发安全反射
  3. 分段路点 + 慢速 → 平稳到达目标
"""

import time
import numpy as np
import panda_py
from panda_py.constants import JOINT_POSITION_START


def main():
    robot_ip = "192.168.1.51"

    print("=" * 50)
    print("Franka 机械臂 → 初始位置（关节空间）")
    print("=" * 50)

    # 1. 连接机器人
    print(f"[1] 连接机器人 {robot_ip} ...")
    panda = panda_py.Panda(robot_ip)
    panda.recover()
    panda.set_default_behavior()
    print("   ✓ 连接成功")

    # 2. 获取底层 Robot 对象，配置安全参数
    robot = panda.get_robot()
    print("   → 放大碰撞阈值（避免 cartesian_reflex 打断运动）")
    robot.set_collision_behavior(
        [20.0] * 7, [20.0] * 7,   # 关节力矩上下限 (Nm)
        [30.0] * 6, [30.0] * 6,   # 笛卡尔力上下限 (N)
    )
    print("   → 降低关节刚度（运动更柔和）")
    robot.set_joint_impedance([10.0] * 7)

    # 3. 显示当前状态
    print(f"[2] 当前关节角度: {np.round(panda.q, 4)}")
    current_pose = panda.get_pose()
    current_pos = current_pose[:3, 3]
    print(f"   当前位置: x={current_pos[0]:.4f}, y={current_pos[1]:.4f}, z={current_pos[2]:.4f}")

    # 4. 显示目标初始位置
    print(f"[3] 目标关节角度 (JOINT_POSITION_START): {np.round(JOINT_POSITION_START, 4)}")
    target_pose = panda_py.fk(JOINT_POSITION_START)
    target_pos = target_pose[:3, 3]
    print(f"   目标末端位置: x={target_pos[0]:.4f}, y={target_pos[1]:.4f}, z={target_pos[2]:.4f}")

    # 5. 检查是否已经在初始位置
    joint_diff = np.max(np.abs(panda.q - JOINT_POSITION_START))
    if joint_diff < 0.01:
        print("   ℹ️  机器人已经在初始位置附近，无需移动")
        return

    # 6. 生成分段插值路点（平滑运动）
    current_q = panda.q.copy()
    target_q = JOINT_POSITION_START.copy()

    steps = 100
    waypoints = []
    for i in range(1, steps + 1):
        alpha = i / steps
        q_wp = current_q + alpha * (target_q - current_q)
        waypoints.append(q_wp)

    # 极低刚度 + 高阻尼，避免触发 cartesian_reflex
    soft_stiffness = np.array([30.0, 30.0, 30.0, 30.0, 15.0, 10.0, 5.0])
    soft_damping = np.array([15.0, 15.0, 15.0, 10.0, 10.0, 5.0, 3.0])

    # 7. 安全提示
    print()
    print(f"   ▶ 将经过 {steps} 个中间路点缓慢运动到目标位置")
    print(f"   ⚠️  请确保机器人周围安全！")
    print("   3 秒后开始运动 ...")
    time.sleep(3.0)

    # 8. 第一阶段：粗略到位
    print("   ▶ 第一阶段：粗略到位（放松精度）...")
    success = panda.move_to_joint_position(
        waypoints,
        speed_factor=0.02,
        stiffness=soft_stiffness,
        damping=soft_damping,
        dq_threshold=0.005,
        success_threshold=0.15,
    )
    print(f"     返回: {success}，当前q: {np.round(panda.q, 4)}")

    # 9. 第二阶段：精细修正
    print("   ▶ 第二阶段：精细修正（收紧精度）...")
    current_q = panda.q.copy()
    steps2 = 50
    waypoints2 = []
    for i in range(1, steps2 + 1):
        alpha = i / steps2
        q_wp = current_q + alpha * (target_q - current_q)
        waypoints2.append(q_wp)

    success = panda.move_to_joint_position(
        waypoints2,
        speed_factor=0.02,
        stiffness=soft_stiffness,
        damping=soft_damping,
        dq_threshold=0.002,
        success_threshold=0.02,
    )
    print(f"     返回: {success}")

    # 10. 验证最终位置
    final_q = panda.q
    print(f"[4] 最终关节角度: {np.round(final_q, 4)}")
    final_diff = np.max(np.abs(final_q - JOINT_POSITION_START))
    print(f"   最大关节偏差: {final_diff:.6f} rad")
    current_pose = panda.get_pose()
    current_pos = current_pose[:3, 3]
    print(f"   最终位置: x={current_pos[0]:.4f}, y={current_pos[1]:.4f}, z={current_pos[2]:.4f}")

    if final_diff < 0.05:
        print()
        print("=" * 50)
        print("✅ 完成！机器人已回到初始位置。")
        print("=" * 50)
    else:
        print()
        print("=" * 50)
        print(f"⚠️  偏差较大 ({final_diff:.4f} rad)，可再次运行精修")
        print("=" * 50)


if __name__ == "__main__":
    main()
