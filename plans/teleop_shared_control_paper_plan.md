# 《面向非结构化抓取的双边遥操作共享控制系统设计》实现计划

## 约束确认

| 约束项 | 确认结果 |
|--------|---------|
| 夹爪电流 | **不可读**（panda_py Gripper 仅暴露 width/is_grasping） |
| 视觉模型 | YOLOv11n，COCO预训练权重（yolo11n.pt） |
| 实验平台 | 真实 Franka Panda + Omega.7 + RealSense D435i |
| COCO覆盖 | 已覆盖：apple, banana, book, cell phone, bottle |

---

## 架构总图

```
                    ┌──────────────────────────────────────────────────┐
                    │              SharedControlNode                   │
                    │                                                  │
  Omega.7 ──Δx──►   │  ┌──────────────┐    ┌──────────────────┐       │   ──Xd──► Franka Panda
  (主端)             │  │ 位置映射      │───►│ 自适应导纳调度     │       │    (从端)
                    │  │ (scale+sign) │    │ K(c), D(c)       │       │
  Omega.7 ◄──F──    │  └──────────────┘    └──────────────────┘       │   ◄──τ_ext──
  (力反馈)           │         ▲                    ▲                   │
                    │         │                    │                   │
                    │  ┌──────┴────────────────────┴──────────┐       │
                    │  │        视觉模块 (30Hz)                 │       │
                    │  │  RealSense → YOLOv11 → PhysicsProfile │       │
                    │  │  K_trans, deadband, admittance_K ...  │       │
                    │  └──────────────────────────────────────┘       │
                    │         │                    │                   │
                    │  ┌──────▼──────┐    ┌────────▼───────────┐      │
                    │  │ 力反馈调度   │    │ 夹持力估计器        │      │
                    │  │ F·K_trans   │    │ f_grip = ||τ_wrist||│      │
                    │  │ 死区过滤     │    │ 接触事件检测        │      │
                    │  └────────────┘    └────────────────────┘       │
                    │         ▲                    ▲                   │
                    │         │                    │                   │
                    └─────────┼────────────────────┼───────────────────┘
                              │                    │
                    F_ext = pinv(Jᵀ)·τ_ext    τ₆, τ₇ (腕部力矩)
                    雅可比伪逆                    Franka Panda
```

### 三线信息流

- 🔵 **蓝色（位置/运动流）**：Omega.7 Δx → 位置映射 → 自适应导纳 → Franka Xd
- 🔴 **红色（力觉反馈流）**：Franka τ_ext → 雅可比映射 → 增益调度 → Omega.7 F_feedback + 夹持力
- 🟢 **绿色（视觉语义流）**：RealSense RGB → YOLOv11 → PhysicsProfile → 同时驱动 K(c) 和 K_haptic

---

## ✅ 已创建的文件（全部在 `plans/` 目录下）

| 文件 | 功能 | 对应层 | 状态 |
|------|------|--------|------|
| [`plans/force_estimator.py`](plans/force_estimator.py) | 外部接触力估计：双模式（内置O_F_ext_hat_K / 显式pinv(Jᵀ)·τ） | Layer 1 | ✅ 已完成 |
| [`plans/adaptive_admittance.py`](plans/adaptive_admittance.py) | 视觉驱动的自适应导纳控制：运行时刚度调度，自动阻尼计算 | Layer 2 | ✅ 已完成 |
| [`plans/grip_force_estimator.py`](plans/grip_force_estimator.py) | 基于腕部关节力矩的夹持力近似估计 + 接触事件检测 | Layer 3 | ✅ 已完成 |
| [`plans/force_feedback_scheduler.py`](plans/force_feedback_scheduler.py) | 主端自适应力反馈调度：K_trans 增益 + 死区控制 | Layer 4 | ✅ 已完成 |
| [`plans/shared_control_node.py`](plans/shared_control_node.py) | 共享控制主节点：三线集成，支持 A/B/C 三种实验模式 | Layer 1+2+3+4 | ✅ 已完成 |
| [`plans/teleop_shared_control_paper_plan.md`](plans/teleop_shared_control_paper_plan.md) | 本计划文档 | 全部 | ✅ 已完成 |

### 外部依赖文件（无需修改）

| 文件 | 用途 | 路径 |
|------|------|------|
| `teleop_omega7_franka.py` | 遥操作骨架（被 shared_control_node 继承） | `my_test/teleop_omega7_franka.py` |
| `vision_physics_mapper.py` | YOLO + PhysicsProfile 查表 | `biaoding/vision_physics_mapper.py` |
| `estimate_external_force.cpp` | C++ 力估计算法参考 | `my_test/estimate_external_force.cpp` |

---

## 第1层：共享控制架构集成

### 目标
将现有的三线独立代码合并为统一 [`SharedControlNode`](plans/shared_control_node.py)

### 数据流设计

```
主循环 (200Hz):
  for each tick:
    # 1. 读 Omega.7 位姿 (dhd.getPosition)
    # 2. 读 Franka 状态 (panda.get_state → tau_ext + O_F_ext_hat_K)
    # 3. 外力估计 F_ext (ForceEstimator.update)
    # 4. 夹持力近似 f_grip = ||τ_wrist|| / τ_max (GripForceEstimator.update)
    # 5. 力反馈调度 F_haptic = F_ext · K_trans + deadband (ForceFeedbackScheduler.compute)
    # 6. 渲染到 Omega.7: dhd.setForce(F_haptic)
    # 7. 接触事件脉冲: 检测到接触时 Z 方向短脉冲
    # 8. 位置映射: Xd = X₀ + Δomega · scale · sign
    # 9. 发给 Franka: ctrl.set_control(target_pos, init_ori)
    # 10. 夹爪控制 (降频 10Hz)

视觉线程 (30Hz, 独立线程):
  while running:
    frame = realsense.wait_for_frame()
    det = mapper.detect_and_map(frame)
    if det:
        current_profile = det['profile']
        adaptive_admittance.apply_profile(profile)  # 切换刚度
        force_feedback.set_profile(profile)          # 切换增益
```

### 三种对比模式（通过 `--mode` 参数选择）

| 模式 | 视觉引导 | 力反馈 | 导纳刚度 | 启动命令 |
|------|---------|--------|---------|---------|
| A | 无 | 零力输出 | 固定 K=200 | `python3 plans/shared_control_node.py --mode a` |
| B | 有 | 固定 K_trans=0.6 | 固定 K=200 | `python3 plans/shared_control_node.py --mode b` |
| C | 有 | 自适应 K_trans(c) | 自适应 K(c) | `python3 plans/shared_control_node.py` (默认) |

---

## 第2层：从端自适应导纳控制

### 原理
导纳控制律：
```
M·ẍ + D(c)·ẋ + K(c)·(x - xd) = Fext
```
其中 K(c) 和 D(c) 由视觉语义查表确定，M 取固定值 3.0 kg。

阻尼按临界阻尼设计：`Dᵢ = 2·ζ·√(Mᵢ·Kᵢ(c))`, ζ = 1.0

### 实现文件
[`plans/adaptive_admittance.py`](plans/adaptive_admittance.py) — **已完成**
- 类 `AdaptiveAdmittance`: 封装自适应导纳调度逻辑
  - `apply_profile(profile)`: 根据 PhysicsProfile 切换阻抗
  - `apply_class(class_name, label)`: 根据类别名直接切换
  - `set_custom_stiffness(K_trans)`: 手动设置
  - 内部自动计算临界阻尼: `D = 2·ζ·√(M·K)`
- 关键 API: `ctrl.set_impedance(K_6x6)` — 运行时安全切换
- 自动限幅: K 在 [50, 400] N/m 范围内

### 参数映射表

| 物体类别 | label | admittance_K (N/m) | D (Ns/m) | Z轴折扣 |
|---------|-------|-------------------|----------|---------|
| apple   | soft  | 50                | 14.1     | ×0.5    |
| banana  | soft  | 50                | 14.1     | ×0.5    |
| bottle  | medium| 150               | 24.5     | ×0.8    |
| book    | hard  | 300               | 34.6     | ×1.0    |
| cell phone | hard | 300            | 34.6     | ×1.0    |
| default | unknown | 100            | 20.0     | ×0.8    |

---

## 第3层：夹持力近似估计（修订方案）

### 约束
- ❌ 夹爪电机电流不可读
- ✅ Franka 关节力矩 τ_ext_hat_filtered 可读 (通过 `RobotState.tau_ext_hat_filtered`)
- ✅ 夹爪 width 可读 (通过 `Gripper.read_once().width`)

### 方案：基于腕部关节力矩的夹持力近似

[`plans/grip_force_estimator.py`](plans/grip_force_estimator.py) — **已完成**

```
f_grip = ||τ_wrist|| / τ_max
```
其中 τ_wrist = [τ₅, τ₆, τ₇]（0-indexed, 最后三个关节），τ_max = 10 Nm。

#### 接触事件检测
```
条件1: |Δwidth| < ε (ε=2mm, 夹爪停滞 → 接触物体)
条件2: ||τ_wrist|| > τ_threshold (τ=1.5Nm, 腕部力矩超过基线)
条件3: width < 0.95·max_width (不在最大张开位)
防抖: 连续5帧满足 → 触发
→ 触发 "已夹持" → Omega.7 Z方向 -2N 短脉冲提示
```

### 论文表述
- 不回避限制，在论文中明确写："受限于商用夹爪 Franka Hand 无内置指尖力传感器且控制接口不暴露电机电流..."
- 强调创新点：**无需附加传感器**即可实现夹持力近似估计
- 与公式3保持一致：`f_grip = α·f_arm + (1-α)·f_current`，但注明"实际部署中α=1.0"（即退化为纯臂端估计）
- 讨论部分列出限制："夹持力估计精度低于直接力传感器，未来可加装低成本触觉传感器"

---

## 第4层：主端自适应力反馈调度

### 力反馈渲染流程

[`plans/force_feedback_scheduler.py`](plans/force_feedback_scheduler.py) — **已完成**

```
步骤1: ForceEstimator 获取 F_ext (6,) = [Fx, Fy, Fz, Tx, Ty, Tz]
步骤2: PhysicsProfile 提供 K_trans 和 deadband
步骤3: F_haptic = F_ext[:3] · K_trans   (仅平移力)
步骤4: 每轴独立死区:
        if |F_i| < deadband: F_i = 0
        else: F_i = sign(F_i) · (|F_i| - deadband)
步骤5: dhd.setForce(F_haptic)
```

### 增益调度表

| 物体类别 | K_trans | deadband (N) | 物理含义 |
|---------|---------|-------------|---------|
| apple   | 0.3     | 0.3         | 轻触感，避免捏碎水果 |
| banana  | 0.2     | 0.5         | 极轻触感，香蕉最脆弱 |
| bottle  | 0.5     | 0.4         | 中等触感，塑料/玻璃 |
| book    | 1.0     | 0.5         | 正常触感，坚硬物体 |
| cell phone | 1.0  | 0.5         | 正常触感，谨慎夹持 |

---

## 第5层：系统架构图（待绘制）

需用 draw.io 或类似工具绘制：

### 图1：系统总体架构图（论文第2节）
- 上半部分：Omega.7 → 共享控制器 → Franka Panda
- 中间：RealSense + YOLO → 视觉语义映射 → 分叉指向「力反馈调度」和「导纳刚度调度」
- 下半部分：Panda 关节力矩 → 力估计器 → 末端力/夹持力 → Omega.7 力反馈
- 三线颜色：蓝(位置)、红(力觉)、绿(视觉语义)

### 图2：夹持过程三源信号曲线（论文第3节）
- 位移曲线、关节力矩范数、接触点标注

---

## 第6层：对比实验（待执行）

### 实验平台
- 硬件：Franka Emika Panda、Omega.7、RealSense D435i
- 软件：Ubuntu 22.04 + Python 3.10 + panda_py + forcedimension_core + YOLOv11n

### 实验任务
操作员通过 Omega.7 控制 Panda，抓取桌面上的 5 类物体（apple, banana, book, cell phone, bottle），移至 20cm 外托盘放下。

### 三种对比模式（已内置在 shared_control_node.py）

| 模式 | 视觉引导 | 力反馈 | 导纳刚度 |
|------|---------|--------|---------|
| 模式A | 无 | 固定零力 | 固定K=200 |
| 模式B | 有 | 固定增益K=0.6 | 固定K=200 |
| 模式C | 有 | 自适应增益 | 自适应K(c) |

### 评价指标
1. 任务成功率（%）
2. 任务完成时间（s）
3. 软物体破损率（%）
4. NASA-TLX 主观负荷评分（1-10）

### 实验脚本（待创建）
- `plans/experiment_runner.py` — 实验流程自动化 + 数据记录

---

## 第7-8层：论文撰写（待完成）

按用户提供的详细模板逐章撰写，共约7000字，15-20篇参考文献（中英文混合，近5年占70%）。

---

## 当前进度总结

| 层 | 描述 | 状态 | 文件 |
|----|------|------|------|
| 第1层 | 共享控制架构集成 | ✅ 已完成 | [`plans/shared_control_node.py`](plans/shared_control_node.py) |
| 第2层 | 从端自适应导纳控制 | ✅ 已完成 | [`plans/adaptive_admittance.py`](plans/adaptive_admittance.py) |
| 第3层 | 夹持力近似估计 | ✅ 已完成 | [`plans/grip_force_estimator.py`](plans/grip_force_estimator.py) |
| 第4层 | 主端自适应力反馈调度 | ✅ 已完成 | [`plans/force_feedback_scheduler.py`](plans/force_feedback_scheduler.py) |
| 第5层 | 系统架构图 | ❌ 待绘制 | — |
| 第6层 | 对比实验 | ❌ 待执行 | [`plans/experiment_runner.py`](plans/experiment_runner.py) (待创建) |
| 第7层 | 论文撰写 | ❌ 待撰写 | — |
| 第8层 | 审阅与修改 | ❌ 待完成 | — |
