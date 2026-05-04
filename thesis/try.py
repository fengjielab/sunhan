# import forcedimension_core.dhd as dhd
# import forcedimension_core.drd as drd
#
# import numpy as np
#
# # 全局变量，位置、旋转矩阵、夹爪角度、线速度、角速度
# pos = np.zeros(3)
# euler = np.zeros(3)
#
# # Drd 初始化
# if drd.open() < 0:
#     print("无法打开设备: " + drd.error())
#     dhd.os_independent.sleep(2)
# if not drd.isInitialized() and drd.autoInit() < 0:
#     print("无法初始化设备: " + drd.error())
#     dhd.os_independent.sleep(2)
# if drd.start() < 0:
#     print("无法启动设备: " + drd.error())
#     dhd.os_independent.sleep(2)
# if drd.moveToPos(pos, block=True) < 0:
#     print("无法移动到位置: " + drd.error())
#     dhd.os_independent.sleep(5)
# if drd.moveToRot(euler, block=True) < 0:
#     print("无法移动到旋转矩阵: " + drd.error())
#     dhd.os_independent.sleep(5)
# if drd.stop(True) < 0:
#     print("无法停止设备: " + drd.error())
#     dhd.os_independent.sleep(2)
#
#
# pos = np.zeros(3)
# matrix = np.zeros((3, 3))
# while True:
#
#     dhd.getPositionAndOrientationFrame(pos, matrix)
#     print(pos)





# import logging
# import pprint
# import time
#
# import cv2
#
# from digit_interface.digit import Digit
# from digit_interface.digit_handler import DigitHandler
#
# logging.basicConfig(level=logging.DEBUG)
#
# # Print a list of connected DIGIT's
# digits = DigitHandler.list_digits()
# print("Connected DIGIT's to Host:")
# pprint.pprint(digits)
#

#
# #
# # Connect to a Digit device with serial number with friendly name
# digit = Digit("D20276", "Left Gripper")
# # digit1 = Digit("D20276", "Right Gripper")#lz
# # digit1.connect()#lz
# digit.connect()
#
# # Print device info
# print(digit.info())
#
# # Change LED illumination intensity
# digit.set_intensity(Digit.LIGHTING_MIN)
# time.sleep(1)
# digit.set_intensity(Digit.LIGHTING_MAX)
#
# # Change DIGIT resolution to QVGA
# qvga_res = Digit.STREAMS["QVGA"]
# digit.set_resolution(qvga_res)
#
# # Change DIGIT FPS to 15fps
# fps_30 = Digit.STREAMS["QVGA"]["fps"]["30fps"]
# digit.set_fps(fps_30)
#
# # Grab single frame from DIGIT
# frame = digit.get_frame()
# print(f"Frame WxH: {frame.shape[0]}{frame.shape[1]}")
#
# # Display stream obtained from DIGIT
# digit.show_view()
#
# # Disconnect DIGIT stream
# digit.disconnect()
#
# # Find a Digit by serial number and connect manually
# digit = DigitHandler.find_digit("D12345")
# pprint.pprint(digit)
# cap = cv2.VideoCapture(digit["dev_name"])
# cap.release()



######################################################################3
# import numpy as np
# import matplotlib.pyplot as plt
# import cv2
#
# # 替换为你的 .npy 文件路径
# file_path = '/home/ljz/LZ/collect_data/data/train/0/ee_pose.npy'
# # file_path = '/home/ljz/LZ/PoseInsert/source_workspace.npy'
#
# # 加载 .npy 文件
# data = np.load(file_path, allow_pickle=True)
#
# # 打印数据
# print(data)
# print(data.shape)
#
# file_path = '/home/ljz/LZ/collect_data/data/train/0/frame_r.npy'
#
# image_data = np.load(file_path)
#
# # 显示图像
# #(54, 320, 240, 3) 表示你有 54 张尺寸为 (320, 240) 的 RGB 图像。
# print(image_data.shape)
#
# for i in range(len(image_data)):
#     #image_data 是一个包含多个图像的数组（例如形状为 (num_images, height, width, channels)），则此循环将迭代每一个图像
#     img = image_data[i]#获取单张图像：
#     cv2.imshow('s',img)#使用 OpenCV 的 imshow 函数在一个窗口中显示当前图像。窗口标题为 's'，可以修改为你想要的任何字符串。
#     cv2.waitKey()
# #调用 cv2.waitKey() 函数会暂停程序执行，直到用户按下键盘上的任意键。默认情况下，waitKey() 不带参数时会无限期等待。这意味着每显示一张图像，程序就会暂停，直到你按下某个键才会继续显示下一张图像。
#
#
#
######################################################################3




"""
Uses the cartesian impedance controller to create a sinusoidal
end-effector movement along the robot's y-axis.
"""
import sys

import numpy as np

import panda_py
from panda_py import controllers

if __name__ == '__main__':


  panda = panda_py.Panda("192.168.1.51")


  print(panda.q)
  print(panda)
  positions = np.array([ 1.40969883e-03 ,-7.84118824e-01 ,-1.82061284e-03 ,-2.35902945e+00,
 -4.62135005e-03 , 1.5 ,  0.6])
  panda.move_to_joint_position(positions,speed_factor=0.1)

  #
  # with panda.create_context(frequency=1e3, max_runtime=runtime) as ctx:
  #   while ctx.ok():
  #     x_d = x0.copy()
  #     x_d[1] += 0.1 * np.sin(ctrl.get_time())
  #     ctrl.set_control(x_d, q0)







