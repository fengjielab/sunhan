from argparse import ArgumentParser

from frankx import Affine, JointMotion, Robot, Waypoint, WaypointMotion


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--host', default='172.16.0.2', help='FCI IP of the robot')
    args = parser.parse_args()

    # Connect to the robot
    robot = Robot(args.host, repeat_on_error=False)
    robot.set_default_behavior()
    robot.recover_from_errors()

    # Reduce the acceleration and velocity dynamic
    robot.set_dynamic_rel(0.05)

    joint_motion = JointMotion([0.5163265857198192, -0.11771772998885105,-0.4117270355670684, -2.474456648497674, -0.15544344020552106,
                            2.3577646381812496, 2.4719217600932404])
    robot.move(joint_motion)

    # Define and move forwards
    motion_down = WaypointMotion([
        Waypoint(Affine(0.0, 0.0, 0.12), -0.2, Waypoint.Relative),
        Waypoint(Affine(0.05, 0.0, 0.0), 0.0, Waypoint.Relative),
        Waypoint(Affine(0.0, 0.05, 0.0, 0.4), 0.0, Waypoint.Relative),
    ])

    # You can try to block the robot now.
    robot.move(motion_down)
