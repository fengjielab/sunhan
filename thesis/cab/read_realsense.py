import pyrealsense2 as rs
import open3d as o3d
import cv2
import numpy as np

#相机配置
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
profile = pipeline.start(config)

#相机深度参数，包括精度以及 depth_scale
depth_sensor = profile.get_device().first_depth_sensor()
depth_sensor.set_option(rs.option.visual_preset, 3)
depth_scale = depth_sensor.get_depth_scale()
clipping_distance_in_meters = 8  # 8 meter
clipping_distance = clipping_distance_in_meters / depth_scale
#color和depth对齐
align_to = rs.stream.color
align = rs.align(align_to)

print('<<<<<<<<<<<<<<<<<<<<<<<<<<<<<   Start Detection >>>>>>>>>>>>>>>>>>>>>>>>>>>>')
# for i in range(30):
while True:
    frames = pipeline.wait_for_frames()
    aligned_frames = align.process(frames)
    aligned_depth_frame = aligned_frames.get_depth_frame()
    color_frame = aligned_frames.get_color_frame()
    #读取图像
    depth_image = np.asanyarray(aligned_depth_frame.get_data())
    color_image = np.asanyarray(color_frame.get_data())
    #读取内参
    intrinsics = color_frame.profile.as_video_stream_profile().intrinsics


    print(intrinsics)

    cv2.imshow("color_image",color_image)
    cv2.waitKey(1)
    #
    # depth_image[depth_image>500] = 0
    # # cv2.imwrite('/home/sunh/thesis/cab/data2/rgb/{:06d}-color.png'.format(i),color_image)
    # # cv2.imwrite('/home/sunh/thesis/cab/data2/depth/{:06d}-depth.png'.format(i),np.uint16(depth_image))
    #
    # intrinsics = color_frame.profile.as_video_stream_profile().intrinsics
    # o3d_inter = o3d.camera.PinholeCameraIntrinsic(intrinsics.width, intrinsics.height, intrinsics.fx, intrinsics.fy,
    #                                               intrinsics.ppx, intrinsics.ppy)
    # # 点云生成和显示
    # color_image = cv2.cvtColor(color_image, cv2.COLOR_BGR2RGB)
    # rgbd_image = o3d.geometry.RGBDImage.create_from_color_and_depth(
    #     o3d.geometry.Image(color_image.copy()),
    #     o3d.geometry.Image(depth_image),
    #     depth_scale=1.0 / depth_scale,
    #     depth_trunc=clipping_distance_in_meters,
    #     convert_rgb_to_intensity=False)
    # pcd = o3d.geometry.PointCloud.create_from_rgbd_image(rgbd_image, o3d_inter)
    # o3d.visualization.draw_geometries([pcd])
    # o3d.io.write_point_cloud("/home/sunh/thesis/cab/pc2.pcd",pcd)


