#!/usr/bin/env python3
"""
D435i + YOLO + 软硬判断 → ROS 节点
====================================
功能:
  1. 订阅 D435i 的彩色图 + 对齐深度图
  2. 用 YOLO 检测物体，获取边界框
  3. 从深度图获取物体中心的 3D 坐标
  4. 判断物体软硬（简单规则/自定义模型）
  5. 发布检测结果（2D框+3D点+物理参数）给机器人控制节点

依赖:
  pip install ultralytics opencv-python rospy sensor_msgs vision_msgs
  sudo apt install ros-noetic-vision-msgs ros-noetic-realsense2-camera

用法:
  # 终端1: 启动 D435i
  roslaunch realsense2_camera rs_camera.launch align_depth:=true

  # 终端2: 启动本节点
  python3 biaoding/yolo_object_detector_node.py

  # 终端3: 查看输出
  rostopic echo /detected_objects_3d
"""

import rospy
import numpy as np
import cv2
from cv_bridge import CvBridge

from sensor_msgs.msg import Image, CameraInfo, PointCloud2
from geometry_msgs.msg import PoseStamped, Point
from vision_msgs.msg import Detection2DArray, Detection2D, ObjectHypothesisWithPose
from std_msgs.msg import String, Header

# 视觉语义-物理属性查表器
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vision_physics_mapper import VisionPhysicsMapper, PhysicsProfile

# YOLO —— 如果你已经训练了专门的软硬检测模型，换成你的模型路径
# 先用预训练模型做示例，你只需把 model_path 改成自己的 .pt 文件
MODEL_PATH = "yolo/ultralytics-8.3.163/yolo11n.pt"  # 改成你的模型

# 物理参数查表器（不重复加载模型，YOLO 已在此节点加载）
PHYSICS_JSON = os.path.join(os.path.dirname(__file__), "physics_table.json")


class YoloObjectDetectorNode:
    def __init__(self):
        rospy.init_node("yolo_object_detector")

        # ── 1. 加载 YOLO 模型 ──
        rospy.loginfo("正在加载 YOLO 模型...")
        from ultralytics import YOLO
        self.model = YOLO(MODEL_PATH)
        rospy.loginfo(f"YOLO 模型加载完成: {MODEL_PATH}")

        self.bridge = CvBridge()
        self.camera_info = None
        self.depth_scale = 0.001  # D435i 默认深度单位: 毫米→米

        # ── 2. 订阅 D435i 输入 ──
        self.sub_color = rospy.Subscriber(
            "/camera/color/image_raw", Image, self.cb_color, queue_size=1
        )
        self.sub_depth = rospy.Subscriber(
            "/camera/aligned_depth_to_color/image_raw", Image, self.cb_depth, queue_size=1
        )
        self.sub_info = rospy.Subscriber(
            "/camera/color/camera_info", CameraInfo, self.cb_camera_info
        )

        # ── 3. 发布输出 ──
        # ① 2D 检测结果（边界框+类别）
        self.pub_detections = rospy.Publisher(
            "/detected_objects_2d", Detection2DArray, queue_size=1
        )
        # ② 3D 目标位置（相机坐标系下）
        self.pub_target_pose = rospy.Publisher(
            "/target_grasp_pose", PoseStamped, queue_size=1
        )
        # ③ 物体软硬属性（向后兼容）
        self.pub_property = rospy.Publisher(
            "/object_property", String, queue_size=1
        )
        # ④ 完整物理参数配置（新增）
        self.pub_physics_profile = rospy.Publisher(
            "/object_physics_profile", String, queue_size=1
        )
        # ⑤ 可视化图像（带检测框）
        self.pub_vis = rospy.Publisher(
            "/detection_visualization", Image, queue_size=1
        )
        # 初始化查表器
        self.physics_mapper = VisionPhysicsMapper(
            model_path=None,  # 不重复加载 YOLO
            json_path=PHYSICS_JSON if os.path.exists(PHYSICS_JSON) else None,
        )

        # 缓存最新帧
        self.color_img = None
        self.depth_img = None

        rospy.loginfo("YOLO 检测节点已启动，等待 D435i 图像...")

    # ── 相机内参回调 ──
    def cb_camera_info(self, msg: CameraInfo):
        self.camera_info = msg
        # fx, fy, cx, cy = msg.K[0], msg.K[4], msg.K[2], msg.K[5]

    # ── 彩色图回调 ──
    def cb_color(self, msg: Image):
        self.color_img = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        self.process_frame()

    # ── 深度图回调 ──
    def cb_depth(self, msg: Image):
        self.depth_img = self.bridge.imgmsg_to_cv2(msg, "16UC1")

    # ── 核心处理：检测 → 3D定位 → 软硬判断 → 发布 ──
    def process_frame(self):
        if self.color_img is None or self.depth_img is None:
            return
        if self.camera_info is None:
            rospy.logwarn_throttle(5, "等待相机内参...")
            return

        color = self.color_img.copy()
        depth = self.depth_img.copy()

        # ── Step 1: YOLO 推理 ──
        results = self.model(color, verbose=False)[0]

        detections_msg = Detection2DArray()
        detections_msg.header = Header()
        detections_msg.header.stamp = rospy.Time.now()
        detections_msg.header.frame_id = "camera_color_optical_frame"

        best_target = None  # 用于发布最佳目标

        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            cls_name = self.model.names[cls_id]

            # 跳过低置信度
            if conf < 0.5:
                continue

            # ── Step 2: 从深度图获取 3D 坐标 ──
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2

            # 取边界框中心附近一个小区域的平均深度，避免噪声
            roi = depth[max(0, cy-5):cy+5, max(0, cx-5):cx+5]
            valid_depths = roi[(roi > 100) & (roi < 8000)]  # 过滤无效值
            if len(valid_depths) == 0:
                continue
            z_m = np.median(valid_depths) * self.depth_scale

            # 用相机内参反投影到 3D (相机坐标系: X向右, Y向下, Z向前)
            fx = self.camera_info.K[0]
            fy = self.camera_info.K[4]
            cx_cam = self.camera_info.K[2]
            cy_cam = self.camera_info.K[5]

            x_m = (cx - cx_cam) * z_m / fx
            y_m = (cy - cy_cam) * z_m / fy

            # ── Step 3: 查表获取完整物理参数 ──
            profile = self.physics_mapper.lookup(cls_name)
            property_str = profile.label  # soft / hard / medium / unknown

            # ── 填充 Detection2D 消息 ──
            det = Detection2D()
            det.header = detections_msg.header
            det.bbox.center.x = (x1 + x2) / 2.0
            det.bbox.center.y = (y1 + y2) / 2.0
            det.bbox.size_x = float(x2 - x1)
            det.bbox.size_y = float(y2 - y1)

            hypo = ObjectHypothesisWithPose()
            hypo.id = f"{cls_name}_{property_str}"  # 例如: "bottle_medium"
            hypo.score = conf
            det.results.append(hypo)

            # 把 3D 点也塞进去（用 source_img 字段存中心点）
            det.source_img.header = detections_msg.header
            det.source_img.width = cx
            det.source_img.height = cy

            detections_msg.detections.append(det)

            # 画框和文字
            color_box = (0, 255, 0) if property_str == "soft" else (0, 0, 255)
            cv2.rectangle(color, (x1, y1), (x2, y2), color_box, 2)
            label = f"{cls_name} | {property_str} | {conf:.2f}"
            cv2.putText(color, label, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color_box, 2)

            # 画中心点和 3D 坐标
            cv2.circle(color, (cx, cy), 3, (255, 0, 0), -1)
            coord_text = f"({x_m:.2f}, {y_m:.2f}, {z_m:.2f})m"
            cv2.putText(color, coord_text, (cx + 5, cy - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)

            # 记录最佳目标（置信度最高或最近的）
            if best_target is None or conf > best_target["conf"]:
                best_target = {
                    "conf": conf,
                    "x": x_m, "y": y_m, "z": z_m,
                    "name": cls_name,
                    "property": property_str,
                    "profile": profile,
                    "cls_id": cls_id
                }

        # ── Step 4: 发布消息 ──
        if len(detections_msg.detections) > 0:
            self.pub_detections.publish(detections_msg)
            self.pub_vis.publish(self.bridge.cv2_to_imgmsg(color, "bgr8"))

        if best_target:
            # 发布 3D 目标位姿（相机坐标系）
            pose = PoseStamped()
            pose.header = detections_msg.header
            pose.pose.position.x = best_target["x"]
            pose.pose.position.y = best_target["y"]
            pose.pose.position.z = best_target["z"]
            pose.pose.orientation.w = 1.0
            self.pub_target_pose.publish(pose)

            # 发布软硬属性（向后兼容）
            self.pub_property.publish(String(data=best_target["property"]))

            # 发布完整物理参数配置（新增）
            import json as _json
            profile_dict = best_target["profile"].to_dict()
            profile_dict["class_name"] = best_target["name"]
            profile_dict["3d_position"] = {
                "x": best_target["x"],
                "y": best_target["y"],
                "z": best_target["z"],
            }
            self.pub_physics_profile.publish(
                String(data=_json.dumps(profile_dict, ensure_ascii=False))
            )

            rospy.loginfo_throttle(
                2,
                f"检测到 {best_target['name']} ({best_target['property']}) "
                f"@ ({best_target['x']:.3f}, {best_target['y']:.3f}, {best_target['z']:.3f})m"
            )


def main():
    node = YoloObjectDetectorNode()
    rospy.spin()


if __name__ == "__main__":
    main()
