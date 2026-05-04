import time

import rospy
from geometry_msgs.msg import PoseStamped
import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp
import panda_py
from panda_py import controllers
import std_msgs.msg


class FrankaController:
    def __init__(self):
        rospy.init_node('franka2_controller', anonymous=True)

        # 初始化Franka机器人
        self.panda = panda_py.Panda("192.168.1.51")
        self.gripper = panda_py.libfranka.Gripper("192.168.1.51")




        # 订阅控制指令
        rospy.Subscriber("/franka1/pose_control", std_msgs.msg.Float64MultiArray, self.pose_callback)
        self.pub = rospy.Publisher("/franka1/pose_info", std_msgs.msg.Float64MultiArray, queue_size=1000)

        self.gripper_state = 1.
        self.target_pose = None


    def pose_callback(self, msg):
        """接收目标位姿指令"""
        self.target_pose = np.array([
            msg.data[0],  # x位置
            msg.data[1],  # y位置
            msg.data[2],  # z位置
            msg.data[3],  # x方向
            msg.data[4],  # y方向
            msg.data[5],  # z方向
            msg.data[6],  # w方向
            msg.data[7]  # 第8个参数（如时间戳或其他数据）
        ])


    def publish_pose(self):
        """发布当前位姿信息"""
        print("*******************  pub *******************")
        pose_msg = std_msgs.msg.Float64MultiArray()
        pose_msg.data = [
            self.current_joint[0],  # x位置
            self.current_joint[1],  # y位置
            self.current_joint[2],  # z位置
            self.current_joint[3],  # x方向
            self.current_joint[4],  # y方向
            self.current_joint[5],  # z方向
            self.current_joint[6],  # w方向
            self.gripper_state   # 第8个参数
        ]
        self.pub.publish(pose_msg)

    def control_loop(self):
        """主控制循环"""
        # 获取当前位姿
        self.current_joint = self.panda.q
        # 发布当前位姿
        self.publish_pose()

        while not rospy.is_shutdown() :
            # 获取当前位姿
            self.current_joint = self.panda.q
            # 发布当前位姿
            self.publish_pose()
            print("*******************  start *******************")

            # 如果有目标位姿，执行插值运动
            if self.target_pose is not None:
                print("accept !")
                if self.target_pose[7] == 0:
                    print("gripper")
                    self.gripper.grasp(
                        width=0.00,
                        speed=0.5,  # 必需：夹爪运动速度（单位：m/s）
                        force=500.0,  # 必需：夹爪抓取力（单位：N）
                        epsilon_inner=0.5,
                        epsilon_outer=0.5
                    )
                    self.gripper_state = 0
                if self.target_pose[7] == 1:
                    self.gripper.grasp(
                        width=0.01,
                        speed=0.5,  # 必需：夹爪运动速度（单位：m/s）
                        force=100.0,  # 必需：夹爪抓取力（单位：N）
                        epsilon_inner=0.5,
                        epsilon_outer=0.5
                    )
                    self.gripper_state = 1.


                self.panda.move_to_joint_position(self.target_pose[:7], speed_factor=0.1)

                # 更新当前位姿
                self.current_joint = self.panda.q
                self.publish_pose()
                # 保持控制频率
                time.sleep(0.25)

            # rate.sleep()
            time.sleep(0.03)


if __name__ == '__main__':
    controller = FrankaController()
    try:
        controller.control_loop()
    except rospy.ROSInterruptException:
        print("Shutting down Franka controller")