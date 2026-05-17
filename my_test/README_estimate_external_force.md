# Panda 末端外力估算

## 1. 原理

机器人动力学方程：

```
tau_ext = J^T * F_ext
```

- `tau_ext`：7x1 外部关节力矩（已由 libfranka 内部重力补偿、摩擦补偿后输出）
- `J`：6x7 零空间雅可比矩阵（zeroJacobian，相对于 base frame）
- `F_ext`：6x1 末端笛卡尔外力/力矩 `[Fx, Fy, Fz, Tx, Ty, Tz]`

估算方法：

```
F_ext = (J^T)^+ * tau_ext
```

其中 `(J^T)^+` 为 `J^T` 的 Moore-Penrose 伪逆。由于 Panda 是 7 自由度（冗余），`J` 为 6x7 列满秩矩阵，伪逆计算稳定。

libfranka 已经在 `RobotState` 中直接提供了滤波后的外部力矩 `tau_ext_hat_filtered`，因此无需手动做重力补偿。

---

## 2. 文件说明

| 文件 | 说明 |
|------|------|
| `estimate_external_force.cpp` | C++ 示例，使用 libfranka 直连机器人 |
| `CMakeLists.txt` | 构建配置 |
| `estimate_external_force_ros.py` | Python 示例，基于 ROS / franka_ros 订阅话题 |

---

## 3. 编译与运行（C++ 方式）

### 前置条件
- 已编译安装 `libfranka`（版本 ≥ 0.8.0）
- 已安装 `Eigen3`
- 机器人已解锁并处于 idle 模式

### 编译
```bash
cd news_5_7
mkdir build && cd build
cmake .. -DFranka_DIR=/path/to/libfranka/build
make
```

### 运行
```bash
./estimate_external_force <robot-hostname>
# 示例：
./estimate_external_force 192.168.1.100
```

---

## 4. 验证实验：末端挂 100g 砝码

### 实验步骤

1. **机器人姿态**：将机器人移动到竖直向下或斜向下的姿态（确保重力主要在 Z 方向，便于观察）。
2. **解锁机器人**：通过 Desk 界面解锁机器人。
3. **运行程序**：启动 `./estimate_external_force`，此时不挂砝码，观察 `Fz` 基线（应接近 0N）。
4. **挂砝码**：在末端法兰上悬挂 100g（0.1kg）砝码。
5. **观察读数**：`Fz` 应稳定在约 **0.98N**（0.1kg × 9.81m/s²）附近。

### 预期结果

| 状态 | Fz 理论值 |
|------|----------|
| 无砝码 | ~0 N |
| 挂 100g 砝码 | ~0.98 N |
| 挂 200g 砝码 | ~1.96 N |

### 注意事项
- **基线漂移**：即使不挂砝码，由于传感器噪声和模型误差，`Fz` 可能在 ±0.5N 范围内波动。挂砝码后变化量才是关键。
- **姿态影响**：如果末端不竖直，重力会分解到 Fx/Fy，需根据当前姿态换算。
- **碰撞阈值**：如程序报 `joint_contact` 或 `cartesian_contact`，说明碰撞检测触发，需降低灵敏度或确保运动缓慢。

---

## 5. 这个实验可以在哪里做到？

### 5.1 实验室环境（推荐）
- **Franka 机器人实验室**：
  - 清华大学 iCenter 机器人实验室
  - 自动化系/机械系相关实验室
  - 需联系实验室管理员获取机器人 IP、Desk 账号密码
- **需要的设备**：
  - Panda 机器人本体（已联网）
  - 100g 标准砝码（或已知质量的物体）
  - 细绳/挂钩（固定在末端法兰上）

### 5.2 远程/仿真环境（无法做真实实验）
- **Franka Gazebo 仿真**：
  - 启动 `franka_gazebo` 仿真环境
  - 通过 `/franka_state_controller/F_ext` 话题直接读取外力（仿真中已计算好）
  - 但**无法验证真实传感器精度**
- **libfranka mock server**：
  - 使用 `libfranka/test/mock_server.cpp` 搭建本地测试服务器
  - 可用于代码逻辑验证，但无真实物理意义

### 5.3 实际操作建议
- 如果**当前就在实验室且有实体机器人**：直接运行 C++ 程序，按步骤 4 验证。
- 如果**只有仿真环境**：先用 ROS 话题 `/franka_state_controller/F_ext` 对比验证算法逻辑。
- 如果**暂时无机器人**：先用 `mock_server` 确保代码能编译运行，再到实验室实地测试。

---

## 6. 核心 API 速查

### libfranka C++
```cpp
franka::Robot robot("192.168.1.100");
franka::Model model = robot.loadModel();

robot.read([&](const franka::RobotState& state) {
    // 滤波后的外部关节力矩（已重力补偿）
    std::array<double, 7> tau_ext = state.tau_ext_hat_filtered;

    // 零空间雅可比（base frame, 6x7 column-major）
    std::array<double, 42> J_array = model.zeroJacobian(
        franka::Frame::kEndEffector, state);
});
```

### franka_ros Python
```python
import rospy
from franka_msgs.msg import FrankaState

rospy.Subscriber("/franka_state_controller/franka_states", FrankaState, callback)

# FrankaState 中:
# tau_ext_hat_filtered  -> 外部关节力矩
# O_F_ext_hat_K         -> 机器人内部估算的末端外力（base frame）
# K_F_ext_hat_K         -> 机器人内部估算的末端外力（stiffness frame）
```

---

## 7. 相关文件参考

- `libfranka/include/franka/robot_state.h` — RobotState 数据结构
- `libfranka/include/franka/model.h` — Model 动力学模型接口
- `libfranka/examples/force_control.cpp` — 力控制示例（含雅可比使用）
- `libfranka/examples/echo_robot_state.cpp` — 状态读取示例
