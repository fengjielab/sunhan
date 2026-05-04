#!/usr/bin/env python3
import rospy
from geometry_msgs.msg import PoseStamped
from frankx import Robot
import numpy as np
from scipy.spatial.transform import Rotation as R
import tf

class FrankaPosePublisher:
    def __init__(self):
        # 初始化ROS节点
        rospy.init_node('franka1_controller', anonymous=True)

        # 创建位姿发布者
        self.pose_pub = rospy.Publisher('/franka1/pose_info', PoseStamped, queue_size=10)

        # 连接Franka机器人
        self.robot = Robot("192.168.1.51")
        self.robot.set_default_behavior()

        # 设置发布频率 (Hz)
        self.rate = rospy.Rate(30)  # 30Hz

        # TF 广播器
        self.br = tf.TransformBroadcaster()

    def run(self):
        while not rospy.is_shutdown():
            # 读取当前位姿 [x, y, z, rz, ry, rx]
            pose = self.robot.current_pose() #调用 self.robot.current_pose(/) 方法获取当前末端位姿。
            # 将欧拉角(rz, ry, rx)转换为四元数
            # rotation = R.from_euler('zyx', [pose.a, pose.b, pose.c], degrees=False)
            rotation = R.from_euler('xyz', [pose.c, pose.b, pose.a], degrees=False)
            quat = rotation.as_quat()  # 返回[x, y, z, w]
            # print([pose.a, pose.b, pose.c])
            print([pose.x, pose.y, pose.z], quat)

            # 创建ROS位姿消息
            pose_msg = PoseStamped()
            #建议为 pose_msg.header.stamp 添加当前时间戳：

            # 设置位置 (x, y, z)
            pose_msg.pose.position.x = pose.x
            pose_msg.pose.position.y = pose.y
            pose_msg.pose.position.z = pose.z
            # 设置方向 (四元数)
            pose_msg.pose.orientation.x = quat[0]
            pose_msg.pose.orientation.y = quat[1]
            pose_msg.pose.orientation.z = quat[2]
            pose_msg.pose.orientation.w = quat[3]

            # 发布位姿
            self.pose_pub.publish(pose_msg)

            # 控制发布频率
            self.rate.sleep()

            # ====== 广播 TF 变换 ======
            # 位置
            translation = (
                pose.x,
                pose.y,
                pose.z
            )
            # 四元数
            rotation = (
                quat[0],
                quat[1],
                quat[2],
                quat[3]
            )

            self.br.sendTransform(
                translation,
                rotation,
                rospy.Time.now(),
                "end_effector",  # 子坐标系
                "world"  # 父坐标系
            )


if __name__ == '__main__':
    try:
        publisher = FrankaPosePublisher()
        publisher.run()
    except rospy.ROSInterruptException:
        pass