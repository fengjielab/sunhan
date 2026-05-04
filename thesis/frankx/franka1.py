#!/usr/bin/env python3
import rospy
from geometry_msgs.msg import PoseStamped
import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp
 ## old 1.4.1

from frankx import Robot, Affine,LinearRelativeMotion,Waypoint, WaypointMotion

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
    quats = np.vstack([
        rotation_start.as_quat(),  # 返回 [x, y, z, w]
        rotation_end.as_quat()
    ])
    # 重新创建合并后的 Rotation 对象
    key_rots = R.from_quat(quats)

    # key_rots = R.concatenate([rotation_start, rotation_end])
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

class FrankaXController:
    def __init__(self):
        # --- ROS 初始化 ---
        rospy.init_node('franka1_controller', anonymous=True)
        self.pose_sub = rospy.Subscriber(
            '/franka1/pose_control', PoseStamped, self.pose_callback
        )
        self.pose_pub = rospy.Publisher(
            '/franka1/pose_info',   PoseStamped, queue_size=10
        )
        self.rate = rospy.Rate(30)  # 30 Hz

        # --- Franka 连接 ---
        self.robot = Robot("192.168.1.51")
        self.robot.set_default_behavior()

        # 当前目标（仅 XYZ+Euler xyz）
        self.target_pose = None

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
        """
        从 frankx.Robot.current_pose() 获取当前：
          vec = [x, y, z, rx, ry, rz]
        然后转换成四元数形式返回：
          - current_q: [x, y, z, qx, qy, qz, qw]
          - current_e: [x, y, z, rx, ry, rz]
        """
        pose = self.robot.current_pose()
        # 将欧拉角(rz, ry, rx)转换为四元数
        rotation = R.from_euler('xyz', [pose.c, pose.b, pose.a], degrees=False)
        quat = rotation.as_quat()  # 返回[x, y, z, w]
        self.current_q = np.hstack(([pose.x,pose.y,pose.z], quat))
        self.current_e = np.hstack(([pose.x,pose.y,pose.z], rotation.as_euler("xyz")))
        return self.current_q, self.current_e

    def publish_pose(self, current_q):
        """把 [x,y,z, qx,qy,qz,qw] 发布为 PoseStamped。"""
        msg = PoseStamped()
        msg.header.stamp = rospy.Time.now()
        msg.pose.position.x = current_q[0]
        msg.pose.position.y = current_q[1]
        msg.pose.position.z = current_q[2]
        msg.pose.orientation.x = current_q[3]
        msg.pose.orientation.y = current_q[4]
        msg.pose.orientation.z = current_q[5]
        msg.pose.orientation.w = current_q[6]
        self.pose_pub.publish(msg)

    def control_loop(self):
        """主循环：持续发布当前位姿，若有目标则插值移动。"""
        rate = rospy.Rate(30)  # 30Hz控制频率
        rospy.loginfo("=== FrankaX 控制器启动 ===")
        while not rospy.is_shutdown():
            # 1) 发布当前位姿
            self.current_q, self.current_e = self.get_current_pose()
            self.publish_pose(self.current_q)

            # 2) 若有目标，则插值执行一系列短程线性运动
            if self.target_pose is not None:
                print("accept !")
                print(self.current_e)
                print(self.target_pose)

                # 计算插值轨迹：transitions + Euler angles
                inter_trans, inter_qua= inter_pose(self.current_e, self.target_pose[:6])
                for pos, ori_e in zip(inter_trans, inter_qua):
                    if rospy.is_shutdown():
                        break

                    print(pos[0],pos[1], pos[2], ori_e[0],ori_e[1],ori_e[2])

                    # 设置控制指令
                    # way = Affine(pos[0],pos[1], pos[2], ori_e[0],ori_e[1],ori_e[2])
                    motion_down = WaypointMotion([
                        Waypoint(Affine(0.0, 0.0, 0.02), 0, Waypoint.Relative),
                    ])
                    self.robot.move(motion_down)


                    # 更新当前位姿
                    ori_q = R.from_euler('xyz', ori_e, degrees=False).as_quat()
                    self.current_q = np.concatenate([pos, ori_q])
                    self.publish_pose(self.current_q)
                    # 保持控制频率
                    rospy.sleep(0.001)  # 1ms延迟

                # 清空目标，等待下一个指令
                self.target_pose = None

            rate.sleep()


if __name__ == '__main__':
    try:
        ctrl = FrankaXController()
        ctrl.control_loop()
    except rospy.ROSInterruptException:
        pass
