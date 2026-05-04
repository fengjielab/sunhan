import numpy as np
from scipy.spatial.transform import Rotation as R

# 输入数据（四元数顺序为x,y,z,w）
quaternion = [-0.006, -0.388, 0.881, -0.270]  # 注意：scipy要求w在前
translation = [0.035, -0.360, 0.381]

# 将四元数转换为旋转矩阵
rotation = R.from_quat([quaternion[3], *quaternion[:3]])  # 调整为w,x,y,z顺序
rotation_matrix = rotation.as_matrix()

# 构建4x4齐次变换矩阵
transform_matrix = np.eye(4)
transform_matrix[:3, :3] = rotation_matrix
transform_matrix[:3, 3] = translation

print("4x4 Transform Matrix:\n", transform_matrix)

ee_in_base = transform_matrix

base_in_cam = np.load('/media/sunh/HW/毕业论文/big_exp/cab/base_in_cam.npy')[0]

cam_in_ee = np.dot( np.linalg.inv(ee_in_base),    np.linalg.inv(base_in_cam))


print("4x4 cam_in_ee :\n", cam_in_ee)

r = R.from_matrix(cam_in_ee[0:3,0:3])
qua=r.as_quat()
print("calibration results: rosrun tf static_transform_publisher "+str(cam_in_ee[0,3])+' '+str(cam_in_ee[1,3])+' '+str(cam_in_ee[2,3])+' '+ str(qua[0])+' '+ str(qua[1])+' '+ str(qua[2])+' '+ str(qua[3])+" /world /camera_link 50")

pass










# from argparse import ArgumentParser
# from time import sleep
#
# from frankx import Affine, Robot
#
#
# if __name__ == '__main__':
#     parser = ArgumentParser()
#     parser.add_argument('--host', default='192.168.1.51', help='FCI IP of the robot')
#     args = parser.parse_args()
#
#     robot = Robot(args.host)
#     robot.set_default_behavior()
#
#     while True:
#         state = robot.read_once()
#         print('\nPose: ', robot.current_pose())
#         print('O_TT_E: ', state.O_T_EE)
#         print('Joints: ', state.q)
#         print('Elbow: ', state.elbow)
#         sleep(0.05)


        #       default="-J $(arg arm_id)_joint1 -0.09236488602271026
        #         -J $(arg arm_id)_joint2 -0.718794315681292
        #         -J $(arg arm_id)_joint3 -1.1962582222787956
        #         -J $(arg arm_id)_joint4 -2.3408946975239537
        #         -J $(arg arm_id)_joint5 -0.4090140673849318
        #         -J $(arg arm_id)_joint6 1.1896086776259873
        #         -J $(arg arm_id)_joint7 0.8784220027565541"


