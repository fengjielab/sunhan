#!/usr/bin/env python
import time
import numpy as np
from sensor_msgs.msg import Image as IMG
from geometry_msgs.msg import TransformStamped
from cv_bridge import CvBridge, CvBridgeError
from message_filters import ApproximateTimeSynchronizer, Subscriber

from sensor_msgs.msg import JointState

import rospy
import os
from std_msgs.msg import Float64MultiArray, Header
from scipy.spatial.transform import Rotation as RR
from geometry_msgs.msg import PoseStamped
import argparse

from easydict import EasyDict as edict
from copy import deepcopy

def save_data(idx, name,data):
    # 定义保存文件的路径
    save_dir = '/home/sunh/thesis/panda-py/data/{}/'.format(idx)
    file_path = os.path.join(save_dir, '{}.npy'.format(name))

    # 检查并创建目录（如果不存在）
    os.makedirs(save_dir, exist_ok=True)

    # 保存 numpy 数组到指定路径
    np.save(file_path, data)
    print(f"Saved data to {file_path}")


class ImageProcessor:
    def __init__(self):
        rospy.init_node('image_processor', anonymous=True)
        self.i = 1

        rospy.Subscriber("/source/pose", PoseStamped, self.object_pose_callback)
        rospy.Subscriber("/franka1/pose_info", PoseStamped, self.eef_pose_callback)




    def object_pose_callback(self, msg):
        self.object_pose = np.array( [msg.pose.position.x,
                                      msg.pose.position.y,
                                      msg.pose.position.z,
                                      msg.pose.orientation.x,
                                      msg.pose.orientation.y,
                                      msg.pose.orientation.z,
                                      msg.pose.orientation.w])

    def eef_pose_callback(self, msg):
        self.eef_pose = np.array( [msg.pose.position.x,
                                      msg.pose.position.y,
                                      msg.pose.position.z,
                                      msg.pose.orientation.x,
                                      msg.pose.orientation.y,
                                      msg.pose.orientation.z,
                                      msg.pose.orientation.w])

    def process_images(self):
        color_all = []
        depth_all = []
        eef_pose = []
        object_pose = []
        i = 0
        while not rospy.is_shutdown():
            # 进行图像处理

            eef_pose.append(self.eef_pose)
            object_pose.append(self.object_pose)


            time.sleep(0.05)

            print(i)
            i = i+1
        idx = args.idx

        save_data(idx,"eef_pose", eef_pose)
        save_data(idx,"obj_pose", object_pose)











    def spin(self):
        time.sleep(1)
        rate = rospy.Rate(30)
        self.process_images()


if __name__ == '__main__':
    default_args = edict({
        "idx": '0',
    })
    parser = argparse.ArgumentParser()
    parser.add_argument('--idx', default='0')
    args_override = vars(parser.parse_args())

    args = deepcopy(default_args)
    for key, value in args_override.items():
        args[key] = value

    processor = ImageProcessor()
    try:
        processor.spin()
    except KeyboardInterrupt:
        print("shutting down")


