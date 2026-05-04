
from argparse import ArgumentParser

from frankx import Affine, JointMotion, Robot, Waypoint, WaypointMotion
from frankx import Affine, LinearRelativeMotion, Robot
from scipy.spatial.transform import Rotation as R

######  [0.321112, -0.010117, 0.500247, 0.043386, -0.672771, -3.082201]  from pose = robot.current_pose()
########### Joints:  [0.034916491837877976, -1.188116476728205, -0.08819328285981877, -2.7552189869797017, 0.02672369770975061, 2.235998588773939, 0.6855433522178194]



# Connect to the robot
robot = Robot('192.168.1.51', repeat_on_error=False)
pose = robot.current_pose()
rotation = R.from_euler('xyz', [pose.c, pose.b, pose.a], degrees=False)
quat = rotation.as_quat()  # 返回[x, y, z, w]
print([pose.x, pose.y, pose.z])
print(quat)
print(pose.c, pose.b, pose.a)

joint_motion = JointMotion([-1.07, 0.0072, -0.026, -1.7734, -0.176,
                            0.76, -0.146])
robot.move(joint_motion)


# state = robot.read_once()
# print('Joints: ', state.q)
# robot.set_default_behavior()
# robot.recover_from_errors()
#
#
# # Reduce the acceleration and velocity dynamic
# robot.set_dynamic_rel(0.2)
#
#
#
# ## obv
# joint_motion = JointMotion([0.2589151892617524, -1.494084300978142, -0.5790374065031141, -2.401679813418472, -0.2914490202150341,
#                             1.4253402276568943, 0.4186703598143326])
# robot.move(joint_motion)
#
# gripper = robot.get_gripper()
# gripper.release(0.05)
# gripper.gripper_force = 100.0
#
#
#
# gripper.clamp()
#
# # #### left
# robot.set_dynamic_rel(0.05)
# motion = LinearRelativeMotion(Affine(0.0, 0.0, 0.20))
# robot.move(motion)
# robot.set_dynamic_rel(0.2)
#
# # gripper.release(50.)
# #
# #

