import time

import rospy
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Float64
import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp
import panda_py
from panda_py import controllers


import sys
import tty
import termios
import threading


#	三维空间线性插值（位置）。
def lerp(start, end, t):
    """Linear interpolation between start and end by a factor of t."""
    return (1 - t) * start + t * end


#	用 scipy.spatial.transform.Slerp 做球面线性插值（旋转），保证旋转路径最短。
def slerp(start_rot, end_rot, t):
    """Spherical linear interpolation between two rotations by a factor of t."""
    # 创建旋转对象
    rotation_start = R.from_euler('xyz',start_rot,degrees=False)
    rotation_end = R.from_euler('xyz',end_rot,degrees=False)
    # 定义关键帧的时间点
    times = [0, 1]
    # 创建包含所有关键帧旋转的对象数组
    key_rots = R.concatenate([rotation_start, rotation_end])
    # 创建 Slerp 对象
    slerp_obj = Slerp(times, key_rots)
    # 执行插值
    interpolated_rotation = slerp_obj(t)
    return interpolated_rotation.as_euler("xyz")


#输入 当前位姿 与 目标位姿，生成 N 步 的平滑轨迹：
def inter_pose(current_pose, target_pose, step_size=0.005, angular_step_deg=0.01):
    current_position = np.array(current_pose[:3])
    current_orientation = np.array(current_pose[3:6])

    target_position = np.array(target_pose[:3])
    target_orientation = np.array(target_pose[3:6])


    total_translation = np.linalg.norm(target_position - current_position)
    num_translation_steps = int(np.ceil(total_translation / step_size))

    if num_translation_steps<20:#如果平移距离 < 40×step_size，则最少 40 步；否则 60 步，保证运动平稳
        num_steps = num_translation_steps +1
    else:
        num_steps = 20

    # num_steps = 1

    interpolated_trans = []#
    interpolated_qua = []

    for i in range(num_steps + 1):
        t = i / num_steps
        new_position = lerp(current_position, target_position, t)
        new_orientation = slerp(current_orientation, target_orientation, t)

        interpolated_trans.append(new_position)
        interpolated_qua.append(new_orientation)

    return np.array(interpolated_trans), np.array(interpolated_qua)


# 假设的 Gripper 类（根据你实际的 gripper API 替换）
class FrankaGripper:
    def grasp(self, width, force, speed):
        rospy.loginfo(f"Grasping: width={width}, force={force}, speed={speed}")
        # 实际调用 gripper action 或 service

    def release(self, width, speed):
        rospy.loginfo(f"Releasing: width={width}, speed={speed}")
        # 实际调用 gripper action 或 service




import tf
class FrankaController:
    def __init__(self):
        rospy.init_node('franka2_controller', anonymous=True)

        # 初始化Franka机器人
        self.panda = panda_py.Panda("192.168.1.51")
        self.gripper = panda_py.libfranka.Gripper("192.168.1.51")

        # self.panda.move_to_start()

        # 初始化笛卡尔阻抗控制器
        impedance = np.diag([500, 500, 500, 100, 100, 100])  # 刚度矩阵 (N/m, Nm/rad)
        self.ctrl = controllers.CartesianImpedance(
            impedance=impedance,
            damping_ratio=0.7,
            nullspace_stiffness=0.3
        )
        self.panda.start_controller(self.ctrl)

        # 订阅控制指令
        rospy.Subscriber("/franka1/pose_control", PoseStamped, self.pose_callback)

        rospy.Subscriber("/omega/gripper_angle", Float64, self.gripper_callback)#LZ

        self.pub = rospy.Publisher("/franka1/pose_info", PoseStamped, queue_size=1000)

        # 初始化目标位姿
        self.target_pose = None
        self.current_pose = np.array([3.07484678e-01, -1.52502597e-04 , 4.87187267e-0,
                                      9.99997747e-01, 1.61261318e-03, 1.12282860e-03, 8.03542265e-04])  # [x,y,z, qx,qy,qz,qw]

        # TF 广播器
        self.br = tf.TransformBroadcaster()

    def gripper_callback(self, msg):
        """实时接收 Omega 夹爪角度（单位：度或弧度，与发布端一致）"""
        self.omega_gripper_angle = msg.data  # 保存到成员变量



    def pose_callback(self, msg):
        """接收目标位姿指令"""#把 ROS1 PoseStamped → 7 维 numpy 数组 [x, y, z, qx, qy, qz, qw] 保存到 self.target_pose
        self.target_pose = np.array([
            msg.pose.position.x,
            msg.pose.position.y,
            msg.pose.position.z,
            msg.pose.orientation.x,
            msg.pose.orientation.y,
            msg.pose.orientation.z,
            msg.pose.orientation.w
        ])

    def get_current_pose(self):
        """获取当前末端位姿"""
        position = self.panda.get_position()
        quaternion = self.panda.get_orientation()
        euler = R.from_quat(quaternion).as_euler("xyz")

        return np.concatenate([position, quaternion]),\
               np.concatenate([position, euler])

    def publish_pose(self):
        """发布当前位姿信息"""
        # print("*******************  pub *******************")
        pose_msg = PoseStamped()
        pose_msg.header.stamp = rospy.Time.now()
        pose_msg.header.frame_id = "world"  # 父坐标系
        pose_msg.pose.position.x = self.current_pose_q[0]
        pose_msg.pose.position.y = self.current_pose_q[1]
        pose_msg.pose.position.z = self.current_pose_q[2]
        pose_msg.pose.orientation.x = self.current_pose_q[3]
        pose_msg.pose.orientation.y = self.current_pose_q[4]
        pose_msg.pose.orientation.z = self.current_pose_q[5]
        pose_msg.pose.orientation.w = self.current_pose_q[6]
        self.pub.publish(pose_msg)

        # ====== 广播 TF 变换 ======
        # 位置
        translation = (
            self.current_pose_q[0],
            self.current_pose_q[1],
            self.current_pose_q[2]
        )
        # 四元数
        rotation = (
            self.current_pose_q[3],
            self.current_pose_q[4],
            self.current_pose_q[5],
            self.current_pose_q[6]
        )

        self.br.sendTransform(
            translation,
            rotation,
            rospy.Time.now(),
            "end_effector",  # 子坐标系
            "world"  # 父坐标系
        )

    #LZ
    def keyboard_listener(self):
        rospy.loginfo("Keyboard listener started. Press 'g' to grasp, 'r' to release, 'q' to quit.")
#在 非终端设备（如 IDE、Jupyter、PyCharm、VSCode 的调试终端、ROS launch 文件等）中运行了终端专属的代码，而这段代码原本是为 Linux 终端（TTY）设计的。
        settings = termios.tcgetattr(sys.stdin)

        try:
            tty.setcbreak(sys.stdin.fileno())
            while True:
                key = sys.stdin.read(1)
                if key == 'g':
                    rospy.loginfo("Keyboard: Grasping...")
                    self.gripper.grasp(width=0.0, force=100.0, speed=0.5,epsilon_inner=0.5,epsilon_outer=0.5)
                elif key == 'r':
                    rospy.loginfo("Keyboard: Releasing...")
                    # self.gripper.grasp(width=0.08, force=10.0,speed=0.5,epsilon_inner=0.5,epsilon_outer=0.5)
                    self.gripper.move(width=0.08, speed=0.5)  # 替换为 move
                elif key == 'q':
                    rospy.loginfo("Quitting...")
                    break
        except Exception as e:
            rospy.logerr("Error in keyboard listener: %s", e)
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)

    def grasp_lz(self):
        self.gripper.grasp(width=0.0, force=100.0, speed=0.5, epsilon_inner=0.5, epsilon_outer=0.5)


    def control_loop(self):
        """主控制循环"""
        # rate = rospy.Rate(30)  # 30Hz控制频率
        # 获取当前位姿
        self.current_pose_q, self.current_pose_e = self.get_current_pose()
        # 发布当前位姿
        self.publish_pose()

        with self.panda.create_context(frequency=1e3) as ctx:#进入 1 kHz 实时控制上下文（libfranka 要求）。
            rate = rospy.Rate(100)  #LZ  # 与上游对齐
            while not rospy.is_shutdown() and ctx.ok():
                # 获取当前位姿
                self.current_pose_q, self.current_pose_e = self.get_current_pose()
                # 发布当前位姿
                self.publish_pose()

                #
                #gripper_force=self.omega_gripper_angle/(max1-min1)#LZ #10-50N
                #self.target_pose[6]

                # print("*******************  start *******************")
                #
                # 如果有目标位姿，执行插值运动，
                #若收到新 target_pose：用 inter_pose 计算 40~60 步的平滑轨迹。
                start = time.time()
                if self.target_pose is not None:
                    # print("accept !")
                    # if self.target_pose[6] == 0:
                    #     print("gripper")
                    #     self.gripper.grasp(
                    #         width=0.00,
                    #         speed=0.5,  # 必需：夹爪运动速度（单位：m/s）
                    #         force=100.0,  # 必需：夹爪抓取力（单位：N）
                    #         epsilon_inner=0.5,
                    #         epsilon_outer=0.5
                    #     )
                    # if self.target_pose[6] == 1:
                    #     self.gripper.grasp(
                    #         width=0.001, #0.01
                    #         speed=0.5,  # 必需：夹爪运动速度（单位：m/s）
                    #         force= 50.0,     #100.0,  # 必需：夹爪抓取力（单位：N）
                    #         epsilon_inner=0.5,
                    #         epsilon_outer=0.5
                    #     )

                    # print(time.time() - start)

                    # 计算插值路径
                    inter_trans, inter_qua = inter_pose(self.current_pose_e, self.target_pose[:6])
                    # print(len(inter_trans))
                    # 执行插值运动
                    for pos, ori_e in zip(inter_trans, inter_qua):
                        if not ctx.ok() or rospy.is_shutdown():
                            break
                        ori_q = R.from_euler('xyz',ori_e,degrees=False).as_quat()
                        # 设置控制指令
                        self.ctrl.set_control(pos, ori_q)#逐点 self.ctrl.set_control(pos, quat) 把目标下发给阻抗控制器。


                        # 更新当前位姿
                        self.current_pose_q = np.concatenate([pos, ori_q])
                        self.publish_pose()
                        # 保持控制频率
                        # rospy.sleep(0.5)  # 1ms延迟
                        # rospy.sleep(0.01)  # 1ms延迟
                        time.sleep(0.001)#每步 time.sleep(0.03) ≈ 30 Hz 插值更新。
                                        #若机械臂断开 / Ctrl-C | 自动退出循环并安全关闭。



                # rate.sleep()
                # time.sleep(0.03)


if __name__ == '__main__':
    controller = FrankaController()

    # 启动键盘监听线程     这个得在终端执行
    keyboard_thread = threading.Thread(target=controller.keyboard_listener)
    keyboard_thread.daemon = True  # 设置为守护线程，主程序退出时自动关闭
    keyboard_thread.start()

    # controller.grasp_lz()


    try:
        controller.control_loop()
    except rospy.ROSInterruptException:
        print("Shutting down Franka controller")