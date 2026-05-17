#!/usr/bin/env python3
"""
关节空间分段运动：通过 IK 转换到关节空间，再用 move_to_joint_position 平滑运动
完全避开笛卡尔阻抗控制参数
"""

import time
import numpy as np
import panda_py


def main():
    robot_ip = "192.168.1.51"

    # 1. 连接机器人
    print("=" * 50)
    print("Franka 机械臂控制测试（关节空间运动）")
    print("=" * 50)

    print(f"[1] 连接机器人 {robot_ip} ...")
    panda = panda_py.Panda(robot_ip)
    panda.recover()
    panda.set_default_behavior()
    print("   ✓ 连接成功")

    # 2. 读取当前状态
    print(f"[2] 当前关节角度: {np.round(panda.q, 4)}")
    current_pose = panda.get_pose()
    current_pos = current_pose[:3, 3]
    print(f"   当前位置: x={current_pos[0]:.4f}, y={current_pos[1]:.4f}, z={current_pos[2]:.4f}")

    # 3. 目标位姿：Z 方向抬升 3cm
    print("[3] 准备 Z 轴抬升 3cm ...")
    target_pose = current_pose.copy()
    target_pose[2, 3] += 0.03
    target_pos = target_pose[:3, 3]
    print(f"   目标位置: x={target_pos[0]:.4f}, y={target_pos[1]:.4f}, z={target_pos[2]:.4f}")

    # 4. 逆运动学：将笛卡尔目标转为关节目标
    current_q = panda.q
    target_q = panda_py.ik(target_pose, q_init=current_q)
    print(f"   目标关节角度: {np.round(target_q, 4)}")

    # 5. 在关节空间生成中间路点（线性插值，20 段，运动更平缓）
    steps = 20
    joint_waypoints = []
    for i in range(1, steps + 1):
        alpha = i / steps
        q_wp = current_q + alpha * (target_q - current_q)
        joint_waypoints.append(q_wp)

    print("   ▶ 即将开始运动，请确保机器人周围安全！")
    print("   3秒后开始运动 ...")
    time.sleep(3.0)

    # 6. 执行抬升运动（关节空间，默认参数即可）
    print("   ▶ 开始向上抬升 ...")
    panda.move_to_joint_position(joint_waypoints, speed_factor=0.05)
    print("   ✓ 抬升完成！")

    # 7. 保持位置
    print("[4] 保持当前位置 3 秒 ...")
    time.sleep(3.0)

    # 8. 回到原位（同样关节空间分段）
    print("[5] 回到原始位置 ...")
    back_waypoints = []
    for i in range(1, steps + 1):
        alpha = i / steps
        q_wp = target_q + alpha * (current_q - target_q)
        back_waypoints.append(q_wp)
    panda.move_to_joint_position(back_waypoints, speed_factor=0.05)
    print("   ✓ 回到原位完成")

    print("=" * 50)
    print("[6] ✅ 测试全部完成！机器人已回到起始位置。")
    print("=" * 50)


if __name__ == "__main__":
    main()
