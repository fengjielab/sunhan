

from frankx import Affine, JointMotion, Robot, Waypoint, WaypointMotion
from frankx import Affine, LinearRelativeMotion, Robot
import numpy as np


# Connect to the robot
robot = Robot('192.168.1.51', repeat_on_error=False)
robot.set_default_behavior()
robot.recover_from_errors()
robot.set_dynamic_rel(0.2)

robot.set_default_behavior()

# while True:
#     state = robot.read_once()
#     print('\nPose: ', robot.current_pose())
#     print('O_TT_E: ', state.O_T_EE)
#     print('Joints: ', state.q)
#     print('Elbow: ', state.elbow)
    # sleep(0.05)


# gripper = robot.get_gripper()wwww
# gripper.clamp()

# motion = LinearRelativeMotion(Affine(0.0, 0.01, 0.2))
# robot.move(motion)


from frankx import Affine, Kinematics, NullSpaceHandling
import re
from pynput import keyboard

def on_press(key):
    try:
        if key.char == 'w':
            print("Key W pressed")
            state = robot.read_once()
            q = state.q
            print(q)
            # Forward kinematic
            x = Affine(Kinematics.forward(q))
            # Define new target position
            x_new = Affine(x=0., y=0.0, z=0.1) * x
            print(x)

            # Franka has 7 DoFs, so what to do with the remaining Null space?
            null_space = NullSpaceHandling(2, 1.1)  # Set elbow joint to 1.4
            # Inverse kinematic with target, initial joint angles, and Null space configuration
            x_new = str(x_new)
            x_new = re.findall(r"[-+]?\d*\.\d+|\d+", x_new)
            x_new = [float(num) for num in x_new]
            print(x_new)
            q_new = Kinematics.inverse(np.array(x_new), q, null_space)
            print(q_new)

            joint_motion = JointMotion(q_new)
            robot.move(joint_motion)

            # motion = LinearRelativeMotion(Affine(0.0, 0.01, 0.0))
            # robot.move(motion)
        elif key.char == 'a':
            print("Key A pressed")
            motion = LinearRelativeMotion(Affine(0.01, 0.0, 0.1))
            robot.move(motion)
        elif key.char == 's':
            print("Key S pressed")
            motion = LinearRelativeMotion(Affine(0.0, -0.01, 0.0))
            robot.move(motion)
        elif key.char == 'd':
            print("Key D pressed")
            motion = LinearRelativeMotion(Affine(-0.01, 0.0, 0.0))
            robot.move(motion)
    except AttributeError:
        pass  # Ignore special keys like Ctrl, Shift etc.

with keyboard.Listener(on_press=on_press) as listener:
    listener.join()


