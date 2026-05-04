# from frankx import Affine, LinearRelativeMotion, Robot
# from pynput import keyboard
#
# robot = Robot("192.168.1.51")
# robot.set_dynamic_rel(0.05)
#
# motion = LinearRelativeMotion(Affine(0.0, 0.0, 0.0))
# robot.move(motion)
#
# gripper = robot.get_gripper()
# gripper.clamp()
# # gripper.release(50.0)
#
#
# def on_press(key):
#     print(key.char)
#     # if key == keyboard.Key.space:
#
# def on_release(key):
#     pass

####################################################

from argparse import ArgumentParser

from frankx import Affine, JointMotion, Robot, Waypoint, WaypointMotion
from frankx import Affine, LinearRelativeMotion, Robot
from franka_ik import FrankaEasyIK
import numpy as np

from scipy.spatial.transform import Rotation as R
import re












# # Connect to the robot
# robot = Robot('192.168.1.51', repeat_on_error=False)
# robot.set_default_behavior()
# robot.recover_from_errors()
#
#
# robot.set_dynamic_rel(0.2)
#
#
#
# gripper = robot.get_gripper()
# gripper.release(0.05)
# gripper.gripper_force = 100.0
#
#
# for i in range(10):
#     state = robot.read_once()
#     # print('\nPose: ', robot.current_pose())
#     # print('O_TT_E: ', state.O_T_EE)
#     # print('Joints: ', state.q)
#     # print('Elbow: ', state.elbow)
#
# print('Joints: ', state.q)
#
# current_pose = str( robot.current_pose() )
#
# current_pose = re.findall(r"[-+]?\d*\.\d+|\d+", current_pose)
# current_pose = [float(num) for num in current_pose]
#
# euler_angles = np.array([current_pose[3], current_pose[4], current_pose[5]])
# rotation = R.from_euler('xyz', euler_angles)
# quaternion = rotation.as_quat()
# # print(quaternion)
#
#
# ik = FrankaEasyIK()
# position = [current_pose[0], current_pose[1], current_pose[2]] # x, y, z
# orientation = [quaternion[0], quaternion[1], quaternion[2], quaternion[3]] # x, y, z, w
# # orientation = [1., 0., 0., 0.] # x, y, z, w
# q = ik(position, orientation)
# print(q)



# joint_motion = JointMotion(q)
# robot.move(joint_motion)

