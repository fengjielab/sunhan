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




# Connect to the robot
robot = Robot('192.168.1.51', repeat_on_error=False)
robot.set_default_behavior()
robot.recover_from_errors()



# Reduce the acceleration and velocity dynamic
robot.set_dynamic_rel(0.2)



## obv
joint_motion = JointMotion([0.2589151892617524, -1.494084300978142, -0.5790374065031141, -2.401679813418472, -0.2914490202150341,
                            1.4253402276568943, 0.4186703598143326])
robot.move(joint_motion)

gripper = robot.get_gripper()
gripper.release(0.05)
gripper.gripper_force = 100.0

# ## pre grASP
# joint_motion = JointMotion([0.5163265857198192, -0.11771772998885105,-0.4117270355670684, -2.474456648497674, -0.15544344020552106,
#                             2.3577646381812496, 2.4719217600932404])
# robot.move(joint_motion)
#
# ## GRASP
# joint_motion = JointMotion([0.5410196080539649, 0.09356587789593912,-0.4116959350318073, -2.517768547898242, -0.14328716037709627,
#                             2.5842087455325653, 2.470730507338215])
# robot.move(joint_motion)
#
# ########### grasp  ########33
# gripper.clamp()
#
# #### left
# robot.set_dynamic_rel(0.05)
# motion = LinearRelativeMotion(Affine(0.0, 0.0, 0.1))
# robot.move(motion)
# robot.set_dynamic_rel(0.2)
#
#
# ### place
joint_motion = JointMotion([0.5462469888360876, 0.023090262797941945,-0.7516672522544411, -2.3873998343484444, -0.016254064282026803,
                            2.3450240925682917, 0.08659346199449566])

robot.move(joint_motion)

# #### left
robot.set_dynamic_rel(0.05)
motion = LinearRelativeMotion(Affine(0.0, 0.0, -0.05))
robot.move(motion)
robot.set_dynamic_rel(0.2)

gripper.clamp()

# #### left
robot.set_dynamic_rel(0.05)
motion = LinearRelativeMotion(Affine(0.0, 0.0, 0.20))
robot.move(motion)
robot.set_dynamic_rel(0.2)

# gripper.release(50.)
#
#
# ## obv
# joint_motion = JointMotion([0.2589151892617524, -1.494084300978142, -0.5790374065031141, -2.401679813418472, -0.2914490202150341,
#                             1.4253402276568943, 0.4186703598143326])
# robot.move(joint_motion)
#######################################################################################################

# from argparse import ArgumentParser
#
# from frankx import Affine, JointMotion, Robot, Waypoint, WaypointMotion
# from frankx import Affine, LinearRelativeMotion, Robot
#
#
#
#
# # Connect to the robot
# robot = Robot('192.168.1.51', repeat_on_error=False)
# robot.set_default_behavior()
# robot.recover_from_errors()
#
# robot.set_default_behavior()
#
# # while True:
# #     state = robot.read_once()
# #     print('\nPose: ', robot.current_pose())
# #     print('O_TT_E: ', state.O_T_EE)
# #     print('Joints: ', state.q)
# #     print('Elbow: ', state.elbow)
# #     sleep(0.05)
#
# # Reduce the acceleration and velocity dynamic
# robot.set_dynamic_rel(0.2)
#
#
#
# ## obv
# # joint_motion = JointMotion([0.2589151892617524, -1.494084300978142, -0.5790374065031141, -2.401679813418472, -0.2914490202150341,
# #                             1.4253402276568943, 0.4186703598143326])
# # robot.move(joint_motion)
#
# gripper = robot.get_gripper()
# gripper.release(0.082112)
# gripper.gripper_force = 100.0
#
#
# # ### pre grasp
# joint_motion = JointMotion([0.7941625215525374, 0.3685230371278981, -0.898420890239247, -2.071813609240348, 0.5762679945164256, 1.7423078235268157, -0.5535074599941988])
# robot.move(joint_motion)
#
# # ### grasp
# joint_motion = JointMotion([0.7996310583267472, 0.3985977312644002, -0.8680228716016093, -2.1223507289879646, 0.5825531070974614, 1.7418958707253138, -0.5535020693512097])
# robot.move(joint_motion)
#
#
# gripper.clamp()
#
# # #### left
# robot.set_dynamic_rel(0.05)
# motion = LinearRelativeMotion(Affine(0.0, 0.0, 0.10))
# robot.move(motion)
# robot.set_dynamic_rel(0.2)

