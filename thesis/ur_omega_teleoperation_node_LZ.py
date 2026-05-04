#!/usr/bin/env python3
import sys
import os

import rospy
# import rclpy
# from rclpy.node import Node
from std_msgs.msg import Float64MultiArray
from std_msgs.msg import Bool

import time
import keyboard

import numpy as np
import forcedimension_core.dhd as dhd
import forcedimension_core.drd as drd
import ctypes
import copy

# from rtde_control import RTDEControlInterface as RTDEControl
# from rtde_receive import RTDEReceiveInterface as RTDEReceive
import psutil

from scipy.spatial.transform import Rotation as R

#  LZ
import panda_py
from panda_py import controllers
from geometry_msgs.msg import PoseStamped
import tf
from std_msgs.msg import Float64
import tf



    #把遥操开合角度写成fanka控制器力度
    #有一个scale可以调操作范围
# #LZ



#这个函数没用到？在后续的主循环里，实际用的是 keyboard.is_pressed('up') / keyboard.is_pressed('down') 这种“实时检测”方式，而不是“事件回调”方式
def on_press(event):
    if event.name == 'add':  # 数字键盘上的加号键
        print("加号键被按下")
        #监听数字键盘上的加号键（NumPad +）
        #如果被按下，就在终端打印
    elif event.name == 'subtract':  # 数字键盘上的减号键
        print("减号键被按下")


# class RobotStatePublisher(Node):
class RobotStatePublisher(object):
    def __init__(self):

        # super().__init__('robot_state_publisher')
        rospy.init_node('robot_state_publisher', anonymous=True)

        rospy.Subscriber("/franka1/pose_info", PoseStamped, self.pose_callback)


        # TF 广播器
        self.br = tf.TransformBroadcaster()

        # 全局变量，位置、旋转矩阵、夹爪角度、线速度、角速度
        pos = np.zeros(3)
        euler = np.zeros(3)

        # Drd 初始化
        if drd.open() < 0:
            print("无法打开设备: " + drd.error())
            dhd.os_independent.sleep(2)
        if not drd.isInitialized() and drd.autoInit() < 0:#	自动校准 → 找到机械零位、校正编码器。
            print("无法初始化设备: " + drd.error())
            dhd.os_independent.sleep(2)
        if drd.start() < 0:#启动 DRD 控制循环 → 允许后续 moveToPos/Rot。
            print("无法启动设备: " + drd.error())
            dhd.os_independent.sleep(2)
        if drd.moveToPos(pos, block=True) < 0:#回到0点位置
            print("无法移动到位置: " + drd.error())
            dhd.os_independent.sleep(5)
        if drd.moveToRot(euler, block=True) < 0:#回到0点旋转
            print("无法移动到旋转矩阵: " + drd.error())
            dhd.os_independent.sleep(5)
        if drd.stop(True) < 0:#完成回零后暂停 DRD 控制，避免后续与 DHD 底层冲突。
            print("无法停止设备: " + drd.error())
            dhd.os_independent.sleep(2)

        #保存“零位”作为后续相对运动计算的基准（后续代码会把人手位移映射到 UR 机械臂）。
        self.first_pos = np.zeros(3)
        self.first_rot = np.identity(3)

        #################### 初始化设备 ########################
        # 打开设备
        dhd.open()

        # 全局变量，位置、旋转矩阵、夹爪角度、线速度、角速度
        #这六行代码为 Omega 设备 建立了“状态缓存区”，后续每 1 kHz 循环用 dhd.getPositionAndOrientationFrame(...) 等函数把实时数据填进来，供遥操作、力控算法或日志记录使用。
        self.pos = np.zeros(3)
        self.matrix = np.zeros((3, 3))#末端 旋转矩阵（3×3，行主序），表示末端姿态。
        self.gripper_pointer = ctypes.pointer(ctypes.c_double(0.0))#C 接口要求的 夹爪角度指针；SDK 会把角度（度）写进 self.gripper_pointer.contents.value。
        self.linear_velocity = np.zeros(3)
        self.angular_velocity = np.zeros(3)
        self.euler = np.zeros(3)#末端 欧拉角 [roll, pitch, yaw]（单位：弧度），便于插值或显示。


        # 力控配置IndexError: index 1 is out of bounds for axis 0 with size 1
        #“给 Omega 末端建了一个‘零位’缓存区，用于后续 1 kHz 的弹簧-阻尼力控计算，使人能感到‘虚拟墙壁’或‘保持力’。”

        self.devicePosition = np.zeros(3)#实时保存 Omega 末端当前位置 (x,y,z)。
        self.deviceRotation = np.zeros((3, 3))#实时保存 Omega 末端当前旋转矩阵。
        self.deviceLinearVelocity = np.zeros(3)#实时保存 末端线速度 (vx,vy,vz)。
        self.deviceAngularVelocity = np.zeros(3)#实时保存 末端角速度 (ωx,ωy,ωz)。

        self.holdPosition = np.zeros(3)#“保持点”位置；当 flagHoldPosition=True 时，人离开该点即产生回弹力。
        self.holdRotation = np.zeros((3, 3))#“保持点”姿态；同上，用于姿态回弹。
        self.last_display_time = dhd.os_independent.getTime()#记录上一次打印/显示信息的时间，用于 0.1 s 打印一次 避免刷屏。

        # # 连续控制
        # pos_continus = np.zeros(3)
        # pos_result = np.zeros(3)
        # flag_continus = False

        self.flagHoldPosition = True#总开关：是否启用“保持位姿”力控。
        self.flagHoldPositionReady = False#True#指示“已经记录过一次 hold 位姿”，防止重复设置。
        #####################################################


        # Set application real-time priority
        #“把当前 Python 进程提升到 实时调度优先级 ，确保 1 kHz 控制循环不被操作系统抢占，从而维持 硬实时 。”
        os_used = sys.platform
        process = psutil.Process(os.getpid())
        if os_used == "win32":  # Windows (either 32-bit or 64-bit)
            process.nice(psutil.REALTIME_PRIORITY_CLASS)
        elif os_used == "linux":  # linux
            rt_app_priority = 80
            param = os.sched_param(rt_app_priority)
            try:
                os.sched_setscheduler(0, os.SCHED_FIFO, param)
            except OSError:
                print("Failed to set real-time process scheduler to %u, priority %u" % (os.SCHED_FIFO, rt_app_priority))
            else:
                print("Process real-time priority set to: %u" % rt_app_priority)

        self.time_counter = 0.0#计时器，用于记录运行秒数。
        self.speed = 0.1#人→机械臂运动的比例系数，后续可键盘 ±0.01 微调。
        ######################### ur ##############################

        # 初始化按键状态字典，给 4 个键（数字键盘 +、-、方向键 ↑、↓）各建一条记录：
        self.key_states = {
            'add': {'pressed': False, 'last_pressed_time': 0},#'pressed'：当前是否正被按住（布尔）。'last_pressed_time'：上次触发动作的时间戳（秒）。
            'subtract': {'pressed': False, 'last_pressed_time': 0},
            'up': {'pressed': False, 'last_pressed_time': 0},
            'down': {'pressed': False, 'last_pressed_time': 0}
        }
        # 设置最小时间间隔（秒）
        self.min_interval = 0.05#两次 有效触发 至少间隔 50 ms，防止 长按抖动 或 CPU 占用过高。


        # 2. 把原来的 self.create_publisher 换成 rospy.Publisher

        self.gripper_pub = rospy.Publisher('/omega/gripper_angle', Float64, queue_size=10)

        self.omega_pose_pub = rospy.Publisher("/franka1/pose_control", PoseStamped, queue_size=10)

        self.tcp_pose_pub = rospy.Publisher(
            'tcp_pose', Float64MultiArray, queue_size=10)
        # # 创建发布器
        # self.joint_position_pub = self.create_publisher(Float64MultiArray, 'joint_positions', 10)
        # self.joint_velocity_pub = self.create_publisher(Float64MultiArray, 'joint_velocities', 10)
        # self.tcp_pose_pub = self.create_publisher(Float64MultiArray, 'tcp_pose', 10)
        # self.tcp_speed_pub = self.create_publisher(Float64MultiArray, 'tcp_speed', 10)
        # self.tcp_force_pub = self.create_publisher(Float64MultiArray, 'tcp_force', 10)
        #
        # self.publisher = self.create_publisher(Bool, '/start_subscribing', 10)
        # # self.timer = self.create_timer(0.02, self.publish_message)  # 50 Hz


        self.ℹ = 0#只是一个计数器（名字特殊，实为普通整数）。初始化阶段用它来“预热”3 次后再开始正式映射，见后面 if self.i > 3 的逻辑。
        self.flag = False#首次标定完成标志。为 False 时反复记录 first_pos/first_rot；置 True 后才开始把 Omega 位移映射到 UR 机械臂。

        self.omega2ur = np.array([[1, 0, 0],   #坐标系对齐矩阵。目前是单位阵，表示“Omega 坐标系 → UR 基坐标系”无额外旋转；如果两台设备安装角度不同，可改成实际旋转矩阵。
                                  [0, 1, 0],
                                  [0, 0, 1]])
        self.sending = False#	“只发一次”开关。第一次进入正式循环后把 /start_subscribing 话题设为 True，随后不再重复发布。


        time.sleep(1)

        self.franka_pose = self.franka_pose_c.copy()


    def pose_callback(self, msg):
        """接收目标位姿指令"""
        self.franka_pose_c = np.array([
            msg.pose.position.x,
            msg.pose.position.y,
            msg.pose.position.z,
            msg.pose.orientation.x,
            msg.pose.orientation.y,
            msg.pose.orientation.z,
            msg.pose.orientation.w
        ])

    def run(self):


        # while True:
        # t_start = self.rtde_c.initPeriod()
        ######################### 读取设备状态 #########################
        # 获取位置、旋转矩阵
        dhd.getPositionAndOrientationFrame(self.pos, self.matrix)
        # 获取夹爪角度
        dhd.getGripperAngleDeg(self.gripper_pointer)#dhd.getGripperAngleDeg(...)→ self.gripper 的数值单位是 度 (degree)
        self.gripper = self.gripper_pointer.contents.value#数值单位是 度 (degree)

        self.gripper_pub.publish(Float64(data=self.gripper))

        # 获取线速度
        dhd.getLinearVelocity(self.linear_velocity)
        # 获取角速度
        dhd.getAngularVelocityDeg(self.angular_velocity)

        # ######################### 控制设备位置 #########################
        # # 设置设备状态
        # self.devicePosition = self.pos
        # self.deviceRotation = self.matrix
        # self.deviceLinearVelocity = self.linear_velocity
        # self.deviceAngularVelocity = self.angular_velocity
        # self.deviceForce = np.zeros(3)
        # self.deviceTorque = np.zeros(3)
        # self.deviceGripperForce = 0.0
        #
        # # 设置刚度和阻尼
        # Kp = 2000.0#平移弹簧刚度 → 位置偏离越大，回弹力越大。
        # Kv = 10.0#平移阻尼 → 抑制振荡，使手感“黏滞”。
        # Kr = 5.0#旋转弹簧刚度 → 姿态偏离越大，回弹扭矩越大。
        # Kw = 0.05#旋转阻尼 → 抑制旋转振荡。
        #
        # # 保持设备位置
        # #人手离开“保持点” → 感受到 拉回力/力矩；人手静止 → 力/力矩趋于零，手感“黏”在保持位姿；改变 Kp/Kr 可让虚拟墙更“硬”或更“软”，改变 Kv/Kw 可调节阻尼手感。
        # if self.flagHoldPosition:
        #     if self.flagHoldPositionReady:
        #         # 计算反作用力  位置误差：devicePosition - holdPosition   用 胡克定律 + 阻尼 计算回弹力   force = ‑Kp·Δx ‑ Kv·v
        #         force = -Kp * (self.devicePosition - self.holdPosition) - Kv * self.deviceLinearVelocity
        #         # 计算反作用力矩
        #         deltaRotation = np.dot(np.transpose(self.deviceRotation), self.holdRotation)#deltaRotation = R_hold^T · R_device
        #         axis, angle = np.zeros(3), 0.0
        #         # 计算旋转轴和角度 #从 deltaRotation 提取 旋转轴-角 (axis, angle)，再用同样的弹簧-阻尼公式计算回弹扭矩
        #         # torque = R_device · [Kr·angle·axis ‑ Kw·ω]
        #         angle = np.arccos((np.trace(deltaRotation) - 1) / 2)
        #         if angle > 1e-6:
        #             axis = np.array([deltaRotation[2, 1] - deltaRotation[1, 2],
        #                              deltaRotation[0, 2] - deltaRotation[2, 0],
        #                              deltaRotation[1, 0] - deltaRotation[0, 1]]) / (2 * np.sin(angle))
        #         torque = np.dot(self.deviceRotation, ((Kr * angle) * axis) - Kw * self.deviceAngularVelocity)
        #         #把计算出的 force 和 torque 累加到 deviceForce / deviceTorque，稍后通过dhd.setForceAndTorqueAndGripperForce(...) 真正输出给 Omega 电机。
        #
        #         # 加上所有力
        #         self.deviceForce = self.deviceForce + force
        #         self.deviceTorque = self.deviceTorque + torque
        #     else:#flagHoldPositionReady=False → 把当前位姿记录为 holdPosition / holdRotation，然后置 True，表示“基准已保存”。
        #         self.holdPosition = self.devicePosition
        #         self.holdRotation = self.deviceRotation
        #         self.flagHoldPositionReady = True
        #
        # # 设置设备力
        # MaxTorque = 0.3#力矩限幅 MaxTorque = 0.3 N·m
        # if np.linalg.norm(self.deviceTorque) > MaxTorque:
        #     self.deviceTorque = MaxTorque * self.deviceTorque / np.linalg.norm(self.deviceTorque)
        # # dhd.setForceAndTorqueAndGripperForce(deviceForce, deviceTorque, deviceGripperForce)
        #
        # #把 力、力矩、夹爪力全部设为 0，相当于 “不给任何力反馈”。这只是 占位/调试 或者 安全测试 阶段；
        # if dhd.setForceAndTorqueAndGripperForce(np.zeros(3), np.zeros(3), 0.0) < 0:
        #     print("无法设置力和力矩: " + dhd.error())
        #     dhd.os_independent.sleep(2)#如果返回 < 0，打印错误信息并休眠 2 秒，让开发者能及时发现通信故障。
        #     # break
        # #在真实力控模式下，应把前面算出的 self.deviceForce 和 限幅后的 self.deviceTorque 传进去：
        # #dhd.setForceAndTorqueAndGripperForce(
        # #self.deviceForce, self.deviceTorque, self.deviceGripperForce)




        ######################### 键盘控制 #########################
        # if dhd.os_independent.kbHit():
        #     keyboard = dhd.os_independent.kbGet()
        #     if keyboard == ' ':
        #         continue
        #     if keyboard == 'q':
        #         break

       # 周期打印设备状态，并刷新输出
        device_time = dhd.os_independent.getTime()
        if device_time - self.last_display_time > 0.1:#一句话：每 0.1 秒才允许输出一次设备状态，避免 1 kHz 循环把终端刷爆。
            self.last_display_time = device_time

        if not self.flag:#预热-标定”阶段（flag=False）
            print('更新初始值')
            self.first_pos = copy.deepcopy(self.pos)
            self.first_rot = copy.deepcopy(self.matrix)
            self.first_rot_euler = R.from_matrix(np.dot(self.first_rot, self.omega2ur)).as_rotvec()

            # first_tcp_pose = self.rtde_r.getActualTCPPose()
            # print('first_tcp_pose', first_tcp_pose)
            # self.first_tcp_rot = R.from_rotvec(first_tcp_pose[3:6]).as_matrix()
            self.i+=1
            if self.i >= 1:#>3
                self.flag = True
            time.sleep(1)
        else:#“正式运行”阶段（flag=True），并在运行时处理 键盘调速 与 单次广播。
            if not self.sending:
                msg = Bool()
                msg.data = True
                #self.start_pub.publish(msg)
                self.sending = True

            current_time = time.time()
            # # 检查上箭头键
            # if keyboard.is_pressed('up'):
            #     if not self.key_states['up']['pressed'] or (
            #             current_time - self.key_states['up']['last_pressed_time'] >= self.min_interval):#self.min_interval=0.05 实现 “长按不连发，但每 50 ms 可调一次速” 的效果。
            #         if self.speed >= 0.04 and self.speed <= 0.5:#self.speed限制在0.04-0.5
            #             self.speed += 0.01
            #         print("self.speed", self.speed)
            #         self.key_states['up']['pressed'] = True
            #         self.key_states['up']['last_pressed_time'] = current_time
            # else:
            #     self.key_states['up']['pressed'] = False
            #
            # # 检查下箭头键
            # if keyboard.is_pressed('down'):
            #     if not self.key_states['down']['pressed'] or (
            #             current_time - self.key_states['down']['last_pressed_time'] >= self.min_interval):
            #         print("self.speed", self.speed)
            #         if self.speed >= 0.05 and self.speed <= 0.52:
            #             self.speed -= 0.01
            #         self.key_states['down']['pressed'] = True
            #         self.key_states['down']['last_pressed_time'] = current_time
            # else:
            #     self.key_states['down']['pressed'] = False
            #
            # print('在发送了')

            # ====== 广播 TF 变换 ======
            # 位置
            translation = (
                self.pos[0],
                self.pos[1],
                self.pos[2]
            )
            # 四元数
            rotation = R.from_matrix(self.matrix).as_quat()

            self.br.sendTransform(
                translation,
                rotation,
                rospy.Time.now(),
                "omega",  # 子坐标系
                "world"  # 父坐标系
            )



            #LZ
            #定义坐标系变换（Omega -> Franka）
            omega_to_franka_rot = R.from_euler('z', 90, degrees=True)

            current_franka_pose2_euler=  R.from_quat(self.franka_pose[3:]).as_euler('xyz')

            current_rot_euler = R.from_matrix(self.matrix).as_euler('xyz')
            add_pos = (self.pos - self.first_pos) * 0.7 #0.5 #$self.speed
            add_rot = (current_rot_euler -self.first_rot_euler) *0.5 #0.05
            #对增量进行坐标系变换
            delta_pos_franka = omega_to_franka_rot.apply(add_pos)
            # 对旋转增量进行坐标系变换（Omega -> Franka）
            # 方法1：把增量欧拉角转为旋转对象，再应用变换
            add_rot_franka = omega_to_franka_rot.apply(R.from_euler('xyz', add_rot).as_rotvec())
            add_rot_franka_euler = R.from_rotvec(add_rot_franka).as_euler('xyz')

            franka_out_pose =self.franka_pose[:3] + delta_pos_franka #[0]#add_pos[0]
            franka_out_rot =current_franka_pose2_euler + add_rot_franka_euler#add_rot

            msg = PoseStamped()
            msg.header.stamp = rospy.Time.now()
            msg.pose.position.x, msg.pose.position.y, msg.pose.position.z = franka_out_pose
            # quat=R.from_quat(quat).as_euler("xyz")
            msg.pose.orientation.x, msg.pose.orientation.y, msg.pose.orientation.z =franka_out_rot #current_franka_pose2_euler


            # ====== 广播 TF 变换 ======
            # LZ: 将 franka_out_pose 和 franka_out_rot 发布为 TF
            franka_out_quat = R.from_euler('xyz', franka_out_rot).as_quat()  # 欧拉角转四元数

            # 发布 TF：omega_controlled -> world
            self.br.sendTransform(
                (franka_out_pose[0], franka_out_pose[1], franka_out_pose[2]),  # 位置
                (franka_out_quat[0], franka_out_quat[1], franka_out_quat[2], franka_out_quat[3]),  # 四元数
                rospy.Time.now(),
                "omega_controlled",  # 子坐标系（你从 Omega 控制的那个位姿）
                "world"  # 父坐标系
            )

            # print(self.franka_pose )
            print("********************************************************: ", delta_pos_franka[0])
            if abs(self.gripper)<12:
                msg.pose.orientation.w = 0
            else :
                msg.pose.orientation.w = 1
            print(self.gripper)

            # ---------- 4) 发布 ----------
            self.omega_pose_pub.publish(msg)
            #


            #rospy.loginfo("RobotStatePublisher started.")


def main():#LZ
    rospy.init_node('robot_state_publisher', anonymous=True)

    robot_state_publisher = RobotStatePublisher()

    time.sleep(1)

    try:
        # 100 Hz 主循环
        rate = rospy.Rate(100)
        while not rospy.is_shutdown():
            aa =time.time()
            robot_state_publisher.run()
            print("-------------------------------------------------------------------------: ",time.time()-aa)
    except KeyboardInterrupt:
        pass
    finally:
        rospy.loginfo("robot_state_publisher shutdown.")



if __name__ == '__main__':
    main()