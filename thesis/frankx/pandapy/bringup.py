# #!/usr/bin/env python3
# import rospy
# from geometry_msgs.msg import PoseStamped
# import panda_py
# from panda_py import controllers
# import numpy as np
#
#
#
# def panda_state_publisher():
#     # 初始化 ROS 节点
#     rospy.init_node('franka2_publisher', anonymous=True)
#     pub = rospy.Publisher('/franka2_ee_pose', PoseStamped, queue_size=10)
#
#     # 连接机器人
#     panda = panda_py.Panda("172.16.0.2")
#
#     rate = rospy.Rate(30)  # 30Hz 发布频率
#     while not rospy.is_shutdown():
#         # 获取当前位置和姿态
#         x0 = panda.get_position()
#         q0 = panda.get_orientation()  # 获取旋转矩阵
#
#         # 创建 ROS 消息
#         pose_msg = PoseStamped()
#         pose_msg.pose.position.x = x0[0]
#         pose_msg.pose.position.y = x0[1]
#         pose_msg.pose.position.z = x0[2]
#
#         pose_msg.pose.orientation.x = q0[0]
#         pose_msg.pose.orientation.y = q0[1]
#         pose_msg.pose.orientation.z = q0[2]
#         pose_msg.pose.orientation.w = q0[3]
#
#         # 发布消息
#         pub.publish(pose_msg)
#         rospy.loginfo(f"Published Pose: Position={x0}, Orientation={q0}")
#         rate.sleep()
#
# if __name__ == '__main__':
#     try:
#         panda_state_publisher()
#     except rospy.ROSInterruptException:
#         pass


# !/home/lin/software/miniconda3/envs/aloha/bin/python
# coding=utf-8
import rospy
from geometry_msgs.msg import PoseStamped
import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp
import panda_py
from panda_py import controllers
from typing import Dict, Any


def lerp(start, end, t):
    """Linear interpolation between start and end by a factor of t."""
    return (1 - t) * start + t * end


def slerp(start_rot, end_rot, t):
    """Spherical linear interpolation between two rotations by a factor of t."""
    # 创建旋转对象
    rotation_start = R.from_euler('xyz',start_rot,degrees=False)
    rotation_end = R.from_euler('xyz',end_rot,degrees=False)
    # 定义关键帧的时间点
    times = [0, 1]
    # 创建包含所有关键帧旋转的对象数组
    key_rots = R.concatenate([rotation_start, rotation_end])
    # 创建 Slerp 对象
    slerp_obj = Slerp(times, key_rots)
    # 执行插值
    interpolated_rotation = slerp_obj(t)
    return interpolated_rotation.as_euler("xyz")

#
def inter_pose(current_pose, target_pose, step_size=0.005, angular_step_deg=0.01):
    current_position = np.array(current_pose[:3])
    current_orientation = np.array(current_pose[3:6])

    target_position = np.array(target_pose[:3])
    target_orientation = np.array(target_pose[3:6])


    total_translation = np.linalg.norm(target_position - current_position)
    num_translation_steps = int(np.ceil(total_translation / step_size))

    if num_translation_steps<40:
        num_steps = num_translation_steps +1
    else:
        num_steps = 60


    interpolated_trans = []
    interpolated_qua = []

    for i in range(num_steps + 1):
        t = i / num_steps
        new_position = lerp(current_position, target_position, t)
        new_orientation = slerp(current_orientation, target_orientation, t)

        interpolated_trans.append(new_position)
        interpolated_qua.append(new_orientation)

    return np.array(interpolated_trans), np.array(interpolated_qua)


class FrankaController:
    def __init__(self):
        rospy.init_node('franka2_controller', anonymous=True)

        # 初始化Franka机器人
        self.panda = panda_py.Panda("172.16.0.2")
        self.gripper = panda_py.libfranka.Gripper("172.16.0.2")

        # 初始化笛卡尔阻抗控制器
        impedance = np.diag([200, 200, 200, 100, 100, 100])  # 刚度矩阵 (N/m, Nm/rad)
        self.ctrl = controllers.CartesianImpedance(
            impedance=impedance,
            damping_ratio=0.7,
            nullspace_stiffness=0.3
        )
        self.panda.start_controller(self.ctrl)

        # 订阅控制指令
        rospy.Subscriber("/franka2/pose_control", PoseStamped, self.pose_callback)
        self.pub = rospy.Publisher("/franka2/pose_info", PoseStamped, queue_size=1000)

        # 初始化目标位姿
        self.target_pose = None
        self.current_pose = np.array([3.07484678e-01, -1.52502597e-04 , 4.87187267e-0,
                                      9.99997747e-01, 1.61261318e-03, 1.12282860e-03, 8.03542265e-04])  # [x,y,z, qx,qy,qz,qw]


    def pose_callback(self, msg):
        """接收目标位姿指令"""
        self.target_pose = np.array([
            msg.pose.position.x,
            msg.pose.position.y,
            msg.pose.position.z,
            msg.pose.orientation.x,
            msg.pose.orientation.y,
            msg.pose.orientation.z,
            msg.pose.orientation.w
        ])

    def get_current_pose(self):
        """获取当前末端位姿"""
        position = self.panda.get_position()
        quaternion = self.panda.get_orientation()
        euler = R.from_quat(quaternion).as_euler("xyz")

        return np.concatenate([position, quaternion]),\
               np.concatenate([position, euler])

    def publish_pose(self):
        """发布当前位姿信息"""
        pose_msg = PoseStamped()
        pose_msg.pose.position.x = self.current_pose_q[0]
        pose_msg.pose.position.y = self.current_pose_q[1]
        pose_msg.pose.position.z = self.current_pose_q[2]
        pose_msg.pose.orientation.x = self.current_pose_q[3]
        pose_msg.pose.orientation.y = self.current_pose_q[4]
        pose_msg.pose.orientation.z = self.current_pose_q[5]
        pose_msg.pose.orientation.w = self.current_pose_q[6]
        self.pub.publish(pose_msg)

    def control_loop(self):
        """主控制循环"""
        rate = rospy.Rate(30)  # 30Hz控制频率

        print("*******************  start *******************")

        with self.panda.create_context(frequency=1e3) as ctx:
            while not rospy.is_shutdown() and ctx.ok():
                # 获取当前位姿
                self.current_pose_q, self.current_pose_e = self.get_current_pose()
                # 发布当前位姿
                self.publish_pose()


                # 如果有目标位姿，执行插值运动
                if self.target_pose is not None:
                    print("accept !")
                    if self.target_pose[6] == 0:
                        print("gripper")
                        self.gripper.grasp(
                            width=0.00,
                            speed=0.5,  # 必需：夹爪运动速度（单位：m/s）
                            force=500.0,  # 必需：夹爪抓取力（单位：N）
                            epsilon_inner=0.5,
                            epsilon_outer=0.5
                        )
                    if self.target_pose[6] == 1:
                        self.gripper.grasp(
                            width=0.01,
                            speed=0.5,  # 必需：夹爪运动速度（单位：m/s）
                            force=100.0,  # 必需：夹爪抓取力（单位：N）
                            epsilon_inner=0.5,
                            epsilon_outer=0.5
                        )


                    # 计算插值路径
                    inter_trans, inter_qua = inter_pose(self.current_pose_e, self.target_pose[:6])
                    # 执行插值运动
                    for pos, ori_e in zip(inter_trans, inter_qua):
                        if not ctx.ok() or rospy.is_shutdown():
                            break
                        ori_q = R.from_euler('xyz',ori_e,degrees=False).as_quat()
                        # 设置控制指令
                        self.ctrl.set_control(pos, ori_q)

                        # 更新当前位姿
                        self.current_pose_q = np.concatenate([pos, ori_q])
                        self.publish_pose()
                        # 保持控制频率
                        rospy.sleep(0.001)  # 1ms延迟

                rate.sleep()


if __name__ == '__main__':
    controller = FrankaController()
    try:
        controller.control_loop()
    except rospy.ROSInterruptException:
        print("Shutting down Franka controller")