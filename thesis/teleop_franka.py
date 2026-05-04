#!/usr/bin/env python3

# %%
import time
# import click
# import cv2
import numpy as np
import scipy.spatial.transform as st
import threading

from std_msgs.msg import Int8
from franka_msgs.msg import FrankaState
import actionlib
from franka_gripper.msg import GraspAction, GraspGoal, MoveAction, MoveGoal
from franka_gripper_server import FrankaGripperServer
from sensor_msgs.msg import JointState

import rospy
import tf
from geometry_msgs.msg import PoseStamped

# from diffusion_policy.real_world.real_env import RealEnv
# from diffusion_policy.real_world.spacemouse_shared_memory import Spacemouse
# from diffusion_policy.common.precise_sleep import precise_wait
# from diffusion_policy.real_world.keystroke_counter import (
#     KeystrokeCounter, Key, KeyCode
# )
#python demo_real_robot.py -o data/demo_pusht_real --robot_ip 192.168.0.204

# output = 'data/demo_put_drink_to_shelves'
output = 'data/demo_force'
robot_ip = "172.16.11.3" #"172.16.11.2"
vis_camera_idx = 0
init_joints = False
frequency = 10
command_latency = 0
pos_ratio = 0.45
rot_ratio = 1.0   #2.1
# @click.command()
# @click.option('--output', '-o', required=True, help="Directory to save demonstration dataset.")
# @click.option('--robot_ip', '-ri', required=True, help="UR5's IP address e.g. 192.168.0.204")
# @click.option('--vis_camera_idx', default=0, type=int, help="Which RealSense camera to visualize.")
# @click.option('--init_joints', '-j', is_flag=True, default=False, help="Whether to initialize robot joint configuration in the beginning.")
# @click.option('--frequency', '-f', default=10, type=float, help="Control frequency in Hz.")
# @click.option('--command_latency', '-cl', default=0.01, type=float, help="Latency between receiving SapceMouse command to executing on Robot in Sec.")

def get_homogenous_matrix(rotation_matrix, translate_vector):
    home_matrix = np.eye(4)
    home_matrix[:3,:3] = rotation_matrix
    home_matrix[:3,3] = translate_vector
    return home_matrix

def tcp2base_position(p_tcp, TCPPose):
        '''position transform from TCP to base coordinate'''
        tcp2base = get_homogenous_matrix(
            st.Rotation.from_rotvec(TCPPose[3:]).as_matrix() ,TCPPose[:3])
        p_tcp = get_homogenous_matrix(
            st.Rotation.from_rotvec(p_tcp[3:]).as_matrix(), p_tcp[0:3])
        p_base = tcp2base.dot(p_tcp)
        p_base_trans = p_base[:3,3]
        p_base_rot = st.Rotation.from_matrix(p_base[:3,:3]).as_rotvec()
        p_base = np.concatenate((p_base_trans, p_base_rot), 0)
        return p_base

def base2tcp_position(p_base, TCPPose):
        '''position transform from base to TCP coordinate'''
        tcp2base = get_homogenous_matrix(
            st.Rotation.from_rotvec(TCPPose[3:]).as_matrix() ,TCPPose[:3])
        p_base = get_homogenous_matrix(
            st.Rotation.from_rotvec(p_base[3:]).as_matrix(), p_base[0:3])
        p_tcp = np.linalg.inv(tcp2base).dot(p_base)
        p_tcp = np.concatenate((p_tcp[:3,3], st.Rotation.from_matrix(p_tcp[:3,:3]).as_rotvec()), 0)
        return p_tcp


def franka_state_callback(msg):
    global franka_now_pose
    # order默认不是F，一定要改成F
    T = np.array(msg.O_T_EE).reshape(4, 4, order='F')

    pos = T[:3, 3]
    rot = st.Rotation.from_matrix(T[:3, :3]).as_rotvec()

    franka_now_pose = list(pos) + list(rot)


def callback(msg):
    global now_get_pose
    pos_delta = msg.pose.position
    xyz = [pos_delta.x, pos_delta.y, pos_delta.z]

    q_hand_now = [
        msg.pose.orientation.x,
        msg.pose.orientation.y,
        msg.pose.orientation.z,
        msg.pose.orientation.w,
    ]
    now_get_pose = xyz +  list(st.Rotation.from_quat(q_hand_now).as_rotvec())


def gripper_control_callback(msg):
    if msg.data == 0:
        rospy.loginfo("关闭夹爪")
        gripper.close()

    elif msg.data == 1:
        rospy.loginfo("打开夹爪")
        gripper.open()

def keyboard_listener():
    global move_touch
    global stop
    while True:
        key = input().strip().lower()
        if key == 'b':
            move_touch = not move_touch
            print(f"move_touch = {move_touch}")
        elif key == 'q':
            stop = True
            print("退出遥操作程序")


# %%
if __name__ == '__main__':

    # cv2.setNumThreads(100)
    rospy.init_node('teleop_to_franka_bridge')

    gripper_client = actionlib.SimpleActionClient('/franka_gripper/grasp', GraspAction)
    move_client = actionlib.SimpleActionClient('/franka_gripper/move', MoveAction)

    gripper_client.wait_for_server()
    move_client.wait_for_server()

    #监听tf变换
    listener = tf.TransformListener()
    br = tf.TransformBroadcaster()
    gripper = FrankaGripperServer()

    listener.waitForTransform("/franka_base_link_in_touch", "/touch_end_pose_trans", rospy.Time(0), rospy.Duration(3.0))      
    
    #发布到机械臂话题
    pub = rospy.Publisher(
            "/cartesian_impedance_controller/equilibrium_pose",
            PoseStamped,
            queue_size=10
        )

    #订阅机械臂夹爪控制话题，手柄末端位姿话题，机械臂当前末端位姿话题
    rospy.Subscriber("/robotiq_control",Int8, gripper_control_callback)
    rospy.Subscriber("/touch_end_pose", PoseStamped, callback)
    rospy.Subscriber("/franka_state_controller/franka_states", FrankaState, franka_state_callback)

    try:
        (trans_old,rot_old) = listener.lookupTransform('franka_base_link_in_touch', 'touch_end_pose_trans', rospy.Time(0))
    except (tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException):
        print("error")

    t_start = time.monotonic()
    dt = 1/frequency
    iter_idx = 0
    stop = False
    is_recording = False
    move_touch = False
    franka_now_pose = None


    # 启动键盘监听线程
    threading.Thread(target=keyboard_listener, daemon=True).start()

    print("等待接受Franka初始姿态...\n")
    while franka_now_pose is None and not rospy.is_shutdown():
        rospy.sleep(0.1)
    print("Franka当前姿态已获取")
    print(franka_now_pose)


    print("等待接收到初始遥操作姿态...\n")
    while now_get_pose is None and not rospy.is_shutdown():
        rospy.sleep(0.1)
    print("初始姿态已获取")
    print(now_get_pose)


    #target---手柄位姿
    target = now_get_pose
    target[3:] = st.Rotation.from_quat(rot_old).as_rotvec()

    #target_pose---机械臂实时位姿
    target_pose = franka_now_pose

    time1 = time.time()

    time.sleep(1)
    print("\n初始化完成")

###################################test###############################################


    # target_pose[0] += 0.05

    # msg_out = PoseStamped()
    # msg_out.header.stamp = rospy.Time.now()
    # msg_out.header.frame_id = "panda_link0" 

    
    # msg_out.pose.position.x = target_pose[0]
    # msg_out.pose.position.y = target_pose[1]
    # msg_out.pose.position.z = target_pose[2]

    # quat_target  = st.Rotation.from_rotvec(target_pose[3:]).as_quat()
    # msg_out.pose.orientation.x = quat_target[0]
    # msg_out.pose.orientation.y = quat_target[1]
    # msg_out.pose.orientation.z = quat_target[2]
    # msg_out.pose.orientation.w = quat_target[3]

    # print(msg_out)

    # pub.publish(msg_out)

###################################test###############################################

    while not stop:
        # calculate timing
        # t_cycle_end = t_start + (iter_idx + 1) * dt
        # t_sample = t_cycle_end - command_latency
        # t_command_target = t_cycle_end + dt


        try:
            (trans_new,rot_new) = listener.lookupTransform('/franka_base_link_in_touch', '/touch_end_pose', rospy.Time(0))
        except (tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException):
            continue

        #前一帧的手柄位姿变换矩阵
        old2base = get_homogenous_matrix(
            st.Rotation.from_quat(rot_old).as_matrix() ,trans_old)
        
        #当前帧的手柄位姿变换矩阵
        new2base = get_homogenous_matrix(
            st.Rotation.from_quat(rot_new).as_matrix() ,trans_new)
        
        #手柄位姿相对变换
        delta = np.linalg.inv(old2base).dot(new2base)

        #缩放平移
        delta_trans = delta[:3, 3] * pos_ratio
        delta_trans[0] *= -1   # 反转 x
        delta_trans[2] *= -1   # 反转 z

        #缩放旋转
        delta_rot = st.Rotation.from_matrix(delta[:3, :3]).as_rotvec() * rot_ratio
        delta_rot[0] *= -1  # Roll 绕x
        delta_rot[2] *= -1  # Yaw 绕z

        delta[:3, 3] = delta_trans
        delta[:3, :3] = st.Rotation.from_rotvec(delta_rot).as_matrix()

        #构造Franka姿态位齐次阵
        T_franka_now = get_homogenous_matrix(
            st.Rotation.from_rotvec(target_pose[3:]).as_matrix(),
            target_pose[:3]
        )

        #franka位姿相对变换
        T_target = T_franka_now.dot(delta)

        #目标平移和旋转
        new_pos = T_target[:3, 3]
        new_rotvec = st.Rotation.from_matrix(T_target[:3, :3]).as_rotvec()

        #叠加相对位移
        if move_touch:
            target_pose = list(new_pos) + list(new_rotvec)
        
        msg_out = PoseStamped()
        msg_out.header.stamp = rospy.Time.now()
        msg_out.header.frame_id = "panda_link0" 

        
        msg_out.pose.position.x = target_pose[0]
        msg_out.pose.position.y = target_pose[1]
        msg_out.pose.position.z = target_pose[2]

        quat_target  = st.Rotation.from_rotvec(target_pose[3:]).as_quat()
        msg_out.pose.orientation.x = quat_target[0]
        msg_out.pose.orientation.y = quat_target[1]
        msg_out.pose.orientation.z = quat_target[2]
        msg_out.pose.orientation.w = quat_target[3]

        pub.publish(msg_out)

        #更新
        iter_idx += 1
        trans_old = trans_new
        rot_old = rot_new

        


