#!/usr/bin/env python
import time
import numpy as np
from sensor_msgs.msg import Image as IMG
from geometry_msgs.msg import TransformStamped
from cv_bridge import CvBridge, CvBridgeError
from message_filters import ApproximateTimeSynchronizer, Subscriber


import rospy
import os
from std_msgs.msg import Float64MultiArray, Header
from scipy.spatial.transform import Rotation as RR
from geometry_msgs.msg import PoseStamped
import argparse

from easydict import EasyDict as edict
from copy import deepcopy
from sensor_msgs.msg import JointState
# from calibation.bimanual import tool_forward_kinematics
#作用是根据机器人关节角度（joint angles），计算出机器人末端执行器（end-effector）在基坐标系（base frame）中的 位姿（pose），
#也就是位置（x, y, z）和姿态（通常用欧拉角或旋转矩阵表示）。

from digit_interface import Digit
from digit_interface import DigitHandler
from tf.transformations import quaternion_matrix, quaternion_from_matrix, concatenate_matrices, inverse_matrix, translation_matrix


# base1
#base1是我现在采的末端位姿作为一个基准坐标系，现在read.py里读出来的是相对franka基坐标的末端位姿，要转换为base1坐标下的位姿
# [0.38362177686530297, 0.03175118002508272, 0.5799483452495572] [-0.01717335  0.01581056 -0.68323482  0.72982551]
# [0.3836206598292234, 0.03175118915533661, 0.5799504628421928] [-0.01717169  0.01581039 -0.6832339   0.72982642]
# [0.38362237717761216, 0.03174917251378606, 0.579949178882486] [-0.0171741   0.01580997 -0.68323598  0.72982443]
# [0.38362168739250974, 0.031750253615356105, 0.5799459729816486] [-0.01717685  0.01581226 -0.68323573  0.72982455]
# [0.3836214734894137, 0.03174984105547841, 0.5799489919496135] [-0.01717288  0.01580979 -0.68323728  0.72982324]
# 假设 base1 的位置和姿态四元数
base1_position = [0.38362177686530297, 0.03175118002508272, 0.5799483452495572]
base1_quaternion = [-0.01717335, 0.01581056, -0.68323482, 0.72982551]


def pose_stamped_to_matrix(pose_stamped):
    """
    将 PoseStamped 转换为 4x4 齐次变换矩阵。
    """
    # 创建位置变换矩阵
    position = [pose_stamped.pose.position.x, pose_stamped.pose.position.y, pose_stamped.pose.position.z]
    trans_mat = translation_matrix(position)

    # 创建旋转矩阵
    quat = [pose_stamped.pose.orientation.x, pose_stamped.pose.orientation.y,
            pose_stamped.pose.orientation.z, pose_stamped.pose.orientation.w]
    rot_mat = quaternion_matrix(quat)

    # 合并得到完整的齐次变换矩阵
    transform_matrix = concatenate_matrices(trans_mat, rot_mat)
    return transform_matrix


def matrix_to_pose_stamped(matrix, frame_id="base1"):
    """
    将 4x4 齐次变换矩阵转换回 PoseStamped。
    """
    pose_stamped = PoseStamped()
    pose_stamped.header.frame_id = frame_id

    # 提取平移部分
    pose_stamped.pose.position.x = matrix[0, 3]
    pose_stamped.pose.position.y = matrix[1, 3]
    pose_stamped.pose.position.z = matrix[2, 3]

    # 提取旋转部分
    quat = quaternion_from_matrix(matrix)
    pose_stamped.pose.orientation.x = quat[0]
    pose_stamped.pose.orientation.y = quat[1]
    pose_stamped.pose.orientation.z = quat[2]
    pose_stamped.pose.orientation.w = quat[3]

    return pose_stamped




def save_data(idx, name,data):#通过传入索引（idx）、文件名（name）和要保存的数据（data）；创建对应的目录并将数据保存为.npy文件。
    # 定义保存文件的路径
    # save_dir = '/home/agilex/sunhan/collect_data/data/train_touch/{}/'.format(idx)
    save_dir = '/home/ljz/LZ/collect_data/data/train/{}/'.format(idx)
    file_path = os.path.join(save_dir, '{}.npy'.format(name))

    # 检查并创建目录（如果不存在）
    os.makedirs(save_dir, exist_ok=True)

    # 保存 numpy 数组到指定路径
    np.save(file_path, data)
    print(f"Saved color_all to {file_path}")


class ImageProcessor:
    def __init__(self):

        rospy.init_node('image_processor', anonymous=True)

        self.bridge = CvBridge()
        # self.i = 1 #没用到
        # 使用message_filters设置同步器
        # self.rgb_sub = Subscriber("/camera_f/color/image_raw", IMG)
        # self.depth_sub = Subscriber("/camera_f/depth/image_raw", IMG)
        # self.astt = ApproximateTimeSynchronizer([self.rgb_sub, self.depth_sub], queue_size=1, slop=0.1)
        # self.astt.registerCallback(self.image_callback)

        ##read.py 创建位姿发布者
        # self.pose_pub = rospy.Publisher('/franka1/pose_info', PoseStamped, queue_size=10)
        # rospy.Subscriber("/master/joint_left", JointState, self.joint_right_callback)#读关节角度
        #不是通过直接读取 robot.current_pose()，而是通过 正运动学计算（forward kinematics）从关节角度推算出末端位姿。
        rospy.Subscriber("/franka1/pose_info", PoseStamped, self.tcp_callback)

        self.d_r = Digit('D20276')
        # self.d_l = Digit('D20276')
        # self.d_l.connect()
        self.d_r.connect()


    def joint_right_callback(self, msg):
        self.joint_state = msg.position[:6]#(1) 提取前6个关节角度（Franka 的7个自由度中，前6个用于定位，最后一个用于姿态）：
        # # self.gripper = msg.position[6] #不需要夹爪信息？#lz
        # ee_in_base_ori = tool_forward_kinematics(self.joint_state[:6])# (2) 使用 tool_forward_kinematics() 函数计算末端位姿：
        # #它返回一个 6 维向量 [x, y, z, rx, ry, rz]，表示末端的位置和欧拉角（弧度）。
        # #(3) 构建 4x4 齐次变换矩阵 ee_in_base 表示末端位姿：
        # ee_in_base = np.identity(4)# 4*4 矩阵
        # ee_in_base[:3, 3] = ee_in_base_ori[:3]
        # ee_in_base[:3, :3] = RR.from_euler("xyz", ee_in_base_ori[3:], degrees=False).as_matrix()
        # #这一步将 [rx, ry, rz] 转换为旋转矩阵，并构建完整的 4x4 位姿矩阵。
        # self.ee_pose = ee_in_base

    def tcp_callback(self, msg):
        """
        从 /franka1/pose_info 主题接收末端执行器的位姿信息，并保存到 self.ee_pose。
        """
        # 创建一个 4x4 齐次变换矩阵
        ee_in_base = np.identity(4)
        # 获取 franka 末端执行器在基坐标系中的位姿
        ee_in_base = pose_stamped_to_matrix(msg)

        # 创建 base1 的变换矩阵
        base1_trans_mat = translation_matrix(base1_position)
        base1_rot_mat = quaternion_matrix(base1_quaternion)
        base1_transform = concatenate_matrices(base1_trans_mat, base1_rot_mat)

        # 计算 base1 到基坐标系的逆变换
        base_to_base1_inv = inverse_matrix(base1_transform)

        # 应用逆变换，将末端执行器的位姿转换到 base1 坐标系下
        ee_in_base1 = np.dot(base_to_base1_inv, ee_in_base)

        # 如果需要，可以将结果转换回 PoseStamped 格式#后面就是要4*4矩阵的格式
        # ee_pose_base1 = matrix_to_pose_stamped(ee_in_base1, frame_id="base1")

        self.ee_pose = ee_in_base1


    def image_callback(self, rgb_msg, depth_msg):#当同步收到RGB和深度图像消息时被触发，将这些图像从ROS消息格式转换为OpenCV可处理的格式。
        try:
            # 转换图像并放入队列以便后续处理
            self.rgb_image = self.bridge.imgmsg_to_cv2(rgb_msg, "bgra8")
            self.depth_image = self.bridge.imgmsg_to_cv2(depth_msg, "16UC1") # Y11  16UC1
        except CvBridgeError as e:
            print(e)



    def process_images(self):
    #在主循环中运行，持续采集并处理图像数据、关节位置、抓手状态以及来自Digit传感器的数据，并将它们存储在相应的列表中。
    #每隔一段时间（通过time.sleep(0.03)实现），就将当前收集的所有数据保存到文件。
        color_all = []
        depth_all = []
        ee_pose = []
        ee_joint = []
        gripper = []
        frame_l_all = []
        frame_r_all = []
        i = 0
        while not rospy.is_shutdown():
            # 进行图像处理
            # depth = np.asanyarray(self.depth_image)
            # color = np.asanyarray(self.rgb_image)
            # color = color[:, :, :3]
            # depth_full = np.zeros((480,640))
            # depth_full[:400,:] = depth

            # frame_l = self.d_l.get_frame()
            frame_r = self.d_r.get_frame()


            # color_all.append(color)
            # depth_all.append(depth_full)
            ee_pose.append(self.ee_pose)
            # ee_joint.append(self.joint_state)
            # gripper.append(self.gripper)#不需要夹爪信息？#lz
            # frame_l_all.append(frame_l)
            frame_r_all.append(frame_r)

            time.sleep(0.03)

            print(i)
            i = i+1
        idx = args.idx
        # save_data(idx,"color_all", color_all)
        # save_data(idx,"depth_all", depth_all)
        save_data(idx,"ee_pose", ee_pose)
        # save_data(idx,"ee_joint", ee_joint)
        # save_data(idx,"gripper", gripper)
        # save_data(idx,"frame_l", frame_l_all)
        save_data(idx,"frame_r", frame_r_all)




    def spin(self):#启动一个循环，确保只要图像数据可用，就会调用process_images方法处理这些数据。
        time.sleep(1)
        rate = rospy.Rate(30)
        while not rospy.is_shutdown():
            # if hasattr(self, "rgb_image") and hasattr(self, "depth_image"):#没加入图像，所以运行不了
                #检查是否已经成功接收到了 RGB 图像和深度图像（即 self.rgb_image 和 self.depth_image 是否存在）。
            self.process_images()
            rate.sleep()


if __name__ == '__main__':
    default_args = edict({#edict 是 easydict 模块中的字典类，允许像对象一样访问属性，如 args.idx。
        "idx": '0',
    })
    parser = argparse.ArgumentParser()
    parser.add_argument('--idx', default='0')
    args_override = vars(parser.parse_args())#解析命令行参数，返回一个字典格式的参数。

    args = deepcopy(default_args)#复制默认参数，防止修改原始默认值
    for key, value in args_override.items():#将命令行参数覆盖到 args 中（如果有传入 --idx 的话）。
        args[key] = value

    ee_pose = []
    frame_r_all = []

    processor = ImageProcessor()

    try:
        processor.spin()
    except KeyboardInterrupt:
        print("Shutting down, saving data...")
        save_data(args.idx, "ee_pose", ee_pose)
        save_data(args.idx, "frame_r", frame_r_all)
        print("Data saved.")


