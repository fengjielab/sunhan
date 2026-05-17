#!/usr/bin/env python

import rospy
import sys
from moveit_commander import MoveGroupCommander
from actionlib_msgs.msg import GoalStatusArray

if __name__ == '__main__':
    rospy.init_node('move_to_start')
    rospy.wait_for_message('move_group/status', GoalStatusArray)
    commander = MoveGroupCommander('panda_arm')

    # 速度/加速度缩放因子 (0.0 ~ 1.0)，值越小运动越慢越安全
    # 默认 0.1 表示只用 10% 的最大速度和加速度
    velocity_scaling = rospy.get_param('~velocity_scaling', 0.1)
    acceleration_scaling = rospy.get_param('~acceleration_scaling', 0.1)

    rospy.loginfo('Velocity scaling: %.2f, Acceleration scaling: %.2f',
                  velocity_scaling, acceleration_scaling)

    commander.set_max_velocity_scaling_factor(velocity_scaling)
    commander.set_max_acceleration_scaling_factor(acceleration_scaling)

    commander.set_named_target('ready')
    commander.go()
