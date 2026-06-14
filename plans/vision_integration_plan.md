# 视觉相机集成方案（简化版）

## 目标

在现有 [`teleop_omega7_franka.py`](my_test/teleop_omega7_franka.py) 基础上，集成 D435i 视觉相机，
实现：
1. 实时显示相机画面
2. YOLO 持续物体检测 + 3D 定位
3. 物理参数自动匹配
4. 终端输出检测信息

**不修改原始文件**，新建 `teleop_omega7_franka_vision.py`。

## 架构

```
主线程 200Hz 控制循环       相机线程 15-30 FPS
┌─────────────────────┐   ┌─────────────────────────┐
│ Omega.7 → Franka    │   │ D435i poll_for_frames()  │
│ 夹爪控制 (10Hz)      │ ←─│ YOLO推理(每3-5帧降频)    │
│ cv2.imshow (20Hz)   │   │ 深度图→3D定位             │
│ 打印检测信息          │   │ 查表→物理属性              │
└─────────────────────┘   │ 绘制检测画面 → Queue      │
        ↑                 └─────────────────────────┘
        │ Lock 保护
  DetectionResult (共享变量)
```

## 复用资源
- [`biaoding/calibration_result.json`](biaoding/calibration_result.json) → 手眼标定
- [`biaoding/physics_table.json`](biaoding/physics_table.json) → 物理参数表
- [`biaoding/vision_physics_mapper.py`](biaoding/vision_physics_mapper.py) → 查表器

## 待办清单

1. 创建 `my_test/teleop_omega7_franka_vision.py`
   - 复制原 teleop_omega7_franka.py 控制逻辑
   - 创建 `DetectionResult` 数据类（线程安全共享变量）
   - 实现相机线程类 `CameraThread`
     - D435i 初始化（参考 `visual_servo_demo.py`：`setup_camera()`）
     - 主循环：`poll_for_frames()` → YOLO 推理（降频）→ 深度图 3D 定位 → 查表 → 绘制
     - 用 Lock 保护共享 `DetectionResult`
   - 主循环集成：
     - 每 10 帧从队列取显示帧并 `cv2.imshow`
     - 收到检测结果时终端打印
2. 测试与调试
