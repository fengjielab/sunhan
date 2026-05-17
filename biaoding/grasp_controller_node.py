#!/usr/bin/env python3
"""
机器人抓取控制节点：接收 YOLO 检测结果 → 决策 → 执行抓取
============================================================

订阅:
  /target_grasp_pose     (PoseStamped)  → 目标 3D 位置（相机坐标系）
  /object_property       (String)        → "soft" / "hard" / "medium" (向后兼容)
  /object_physics_profile(String)        → JSON 完整物理参数 (推荐)

执行:
  1. 把目标位置从相机坐标系 → 机器人基坐标系（需要手眼标定 T_gripper_camera）
  2. 根据软硬属性选择抓取策略
  3. 调用 CartesianPose 或 CartesianImpedance 控制器移动到目标
  4. 夹爪根据软硬调整夹持力

依赖:
  pip install panda-py  # 或 franka_ros 控制器
"""

import rospy
import numpy as np
import json
import os, sys
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import String
import tf.transformations as tft

# 引入视觉语义-物理属性映射器
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vision_physics_mapper import PhysicsProfile, profile_to_grasp_controller_dict

# 如果你用 franka_ros（推荐，已经在学）
# from franka_msgs.msg import FrankaState
# from controller_manager_msgs.srv import SwitchController

# 如果你用 panda-py（更简单的 Python API）
import panda_py
import panda_py.libfranka as lf
import panda_py.controllers as controllers


class GraspControllerNode:
    def __init__(self):
        rospy.init_node("grasp_controller")

        # ── 加载手眼标定结果 ──
        self.T_gripper_camera = self.load_calibration("biaoding/calibration_result.json")
        rospy.loginfo(f"手眼标定矩阵 shape: {self.T_gripper_camera.shape}")

        # ── 连接机器人（用 panda-py，也可改用 franka_ros 的 action/service） ──
        self.robot_ip = rospy.get_param("~robot_ip", "192.168.1.51")
        rospy.loginfo(f"连接机器人: {self.robot_ip}")
        # self.robot = panda_py.Panda(self.robot_ip)
        # self.robot.enable_logging()  # 记录状态

        # 当前目标
        self.target_pose_camera = None   # [x, y, z] in camera frame
        self.object_property = None      # "soft" or "hard" (向后兼容)
        self.physics_profile = None      # PhysicsProfile (完整参数)

        # ── 订阅 YOLO 检测结果 ──
        self.sub_pose = rospy.Subscriber(
            "/target_grasp_pose", PoseStamped, self.cb_target_pose
        )
        self.sub_prop = rospy.Subscriber(
            "/object_property", String, self.cb_property
        )
        # 新增：完整物理参数（优先使用）
        self.sub_physics = rospy.Subscriber(
            "/object_physics_profile", String, self.cb_physics_profile
        )

        rospy.loginfo("抓取控制节点已启动，等待目标...")
        rospy.loginfo("按 'Enter' 执行抓取（或自动模式下到达即抓）")

    # ── 加载手眼标定 ──
    def load_calibration(self, path):
        with open(path) as f:
            results = json.load(f)
        best = min(results, key=lambda r: r["consistency_metrics"]["translation_mean_m"])
        T = np.array(best["transform_4x4"], dtype=float)
        rospy.loginfo(f"标定方法: {best['method']}, 误差: {best['consistency_metrics']['translation_mean_m']*1000:.1f}mm")
        return T

    # ── 目标位姿回调 ──
    def cb_target_pose(self, msg: PoseStamped):
        """接收相机坐标系下的目标位置"""
        self.target_pose_camera = np.array([
            msg.pose.position.x,
            msg.pose.position.y,
            msg.pose.position.z,
            1.0  # 齐次坐标
        ])
        rospy.loginfo_throttle(1,
            f"目标(相机系): ({self.target_pose_camera[0]:.3f}, "
            f"{self.target_pose_camera[1]:.3f}, {self.target_pose_camera[2]:.3f})"
        )

    # ── 属性回调（向后兼容）──
    def cb_property(self, msg: String):
        """接收物体软硬属性（向后兼容，当没有 /object_physics_profile 时使用）"""
        self.object_property = msg.data
        rospy.loginfo_throttle(1, f"物体属性(legacy): {self.object_property}")

    # ── 完整物理参数回调（新增，优先）──
    def cb_physics_profile(self, msg: String):
        """接收 JSON 格式的完整物理参数配置"""
        try:
            data = json.loads(msg.data)
            self.physics_profile = PhysicsProfile.from_dict(data)
            rospy.loginfo_throttle(
                1,
                f"物理参数: {self.physics_profile.label} | "
                f"F={self.physics_profile.F_target}N | "
                f"K_trans={self.physics_profile.K_trans} | "
                f"speed={self.physics_profile.approach_speed}m/s"
            )
        except Exception as e:
            rospy.logwarn(f"解析物理参数失败: {e}")

    # ── 坐标变换：相机 → 机器人基坐标系 ──
    def camera_to_base(self, point_camera):
        """
        把相机坐标系下的点转到机器人基坐标系
        
        需要: T_base_gripper (机器人当前末端位姿)
              T_gripper_camera (手眼标定结果)
        
        变换链: P_base = T_base_gripper @ T_gripper_camera @ P_camera
        """
        # 获取机器人当前末端位姿（用 panda-py）
        # state = self.robot.get_state()
        # T_base_gripper = np.array(state.O_T_EE).reshape(4, 4).T  # 列主序转行主序
        
        # 这里用固定值演示（实际运行时获取）
        # 假设机器人末端在某个已知位置
        T_base_gripper = np.eye(4)
        T_base_gripper[0:3, 3] = [0.3, 0.0, 0.4]  # 示例位置

        # 完整变换
        point_base = T_base_gripper @ self.T_gripper_camera @ point_camera
        return point_base[:3]

    # ── 选择抓取策略（优先用完整物理参数）──
    def select_grasp_strategy(self):
        """
        根据物体物理参数返回控制参数

        优先级:
            1. physics_profile (来自 /object_physics_profile)
            2. object_property (来自 /object_property，向后兼容)
        """
        if self.physics_profile is not None:
            # 使用 VisionPhysicsMapper 提供的完整参数
            strategy = self.physics_profile.to_grasp_strategy()
            rospy.loginfo(f"[查表策略] {strategy['description']}")
            return strategy

        # 向后兼容：只用 soft/hard 简单二分
        rospy.logwarn_throttle(5, "未收到完整物理参数，使用 legacy soft/hard 策略")
        if self.object_property == "soft":
            return {
                "stiffness": [100, 100, 50, 10, 10, 10],
                "force": 3.0,
                "approach_speed": 0.02,
                "description": "软物体策略(legacy): 低刚度、小力、慢速"
            }
        else:  # hard or unknown
            return {
                "stiffness": [2000, 2000, 2000, 50, 50, 50],
                "force": 10.0,
                "approach_speed": 0.05,
                "description": "硬物体策略(legacy): 正常刚度、正常力、正常速度"
            }

    # ── 执行抓取 ──
    def execute_grasp(self):
        """
        完整抓取流程：
        1. 预抓取位置（目标上方 10cm）
        2. 设置阻抗参数（根据软硬）
        3. 下降到目标位置
        4. 夹爪闭合
        5. 提升到安全高度
        """
        if self.target_pose_camera is None:
            rospy.logwarn("还没有检测到目标，无法抓取")
            return

        # 坐标变换
        target_base = self.camera_to_base(self.target_pose_camera)
        rospy.loginfo(f"目标(机器人基座系): {target_base}")

        # 选择策略
        strategy = self.select_grasp_strategy()
        rospy.loginfo(strategy["description"])

        # 预抓取位置（上方 10cm，可用 admittance_K 微调）
        pre_grasp = target_base.copy()
        pre_grasp[2] += 0.10  # Z + 10cm

        # 实际抓取位置
        grasp_pos = target_base.copy()

        # ========== 这里接入真实机器人控制 ==========
        # 用 franka_ros:
        #   1. 启动 CartesianImpedance 控制器
        #   2. 发 /equilibrium_pose 到预抓取位置
        #   3. 下降，发 /equilibrium_pose 到 grasp_pos
        #   4. 调用夹爪 action: Grasp(width=0, force=strategy["force"])
        #   5. 提升

        # 用 panda-py:
        # self.robot.move_to_position(pre_grasp, speed=strategy["approach_speed"])
        # self.robot.move_to_position(grasp_pos, speed=0.01)  # 最后下降要慢
        # self.robot.gripper.grasp(width=0, speed=0.1, force=strategy["force"], epsilon=0.01)
        # self.robot.move_to_position(pre_grasp, speed=0.05)

        label = self.physics_profile.label if self.physics_profile else self.object_property
        rospy.loginfo(
            f"[模拟执行] 抓取 @ {grasp_pos} | 属性: {label} | "
            f"夹持力: {strategy['force']}N | 刚度: {strategy['stiffness']}"
        )

    # ── 主循环 ──
    def run(self):
        rate = rospy.Rate(10)
        while not rospy.is_shutdown():
            # 可以改成自动检测到有目标就抓，或等按键触发
            # 这里简单打印状态
            if self.target_pose_camera is not None and (
                self.physics_profile is not None or self.object_property is not None
            ):
                status = self.physics_profile.label if self.physics_profile else self.object_property
                rospy.loginfo_throttle(3,
                    f"就绪: 目标 {self.target_pose_camera[:3]} | 属性 {status}"
                )
            rate.sleep()


def main():
    node = GraspControllerNode()
    node.run()


if __name__ == "__main__":
    main()
