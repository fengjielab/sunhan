#!/home/lin/software/miniconda3/envs/aloha/bin/python
# coding=utf-8
import rospy
from geometry_msgs.msg import PoseStamped

import numpy as np
from scipy.spatial.transform import Rotation as R
import time
from sensor_msgs.msg import JointState




class ArmController:
    def __init__(self):
        rospy.init_node('controller_test', anonymous=True)
        self.pub = rospy.Publisher("/franka1/pose_control", PoseStamped, queue_size=1000)

    def arm_move(self):
        rate = rospy.Rate(30)

        ee_in_base_goal = np.array([0.161723528286, -0.0163870853027,  0.60385591833,
                                    0.5785450752776882, 0.0061609026791642485, -1.6218248983697123])
        print(ee_in_base_goal)
        gripper = 0
        # time.sleep(2)



        for i in range(300):
            # while not rospy.is_shutdown():
            pose_stamped = PoseStamped()
            pose_stamped.header.stamp = rospy.Time.now()  # 设置时间戳为当前时间
            pose_stamped.pose.position.x = ee_in_base_goal[0]
            pose_stamped.pose.position.y = ee_in_base_goal[1]
            pose_stamped.pose.position.z = ee_in_base_goal[2]
            pose_stamped.pose.orientation.x = ee_in_base_goal[3]
            pose_stamped.pose.orientation.y = ee_in_base_goal[4]
            pose_stamped.pose.orientation.z = ee_in_base_goal[5]
            pose_stamped.pose.orientation.w = gripper
            self.pub.publish(pose_stamped)
            rate.sleep()
        pose_stamped.pose.orientation.w = 10
        self.pub.publish(pose_stamped)


if __name__ == '__main__':
    arm = ArmController()
    try:
        arm.arm_move()
        rospy.spin()
    except KeyboardInterrupt:
        print("shutting down")



