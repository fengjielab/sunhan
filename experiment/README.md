# 视觉语义驱动的多参数阻抗辅助遥操作实验系统

本目录是论文方案 **“视觉语义驱动的多参数阻抗辅助遥操作方法研究”** 的主实验入口。
系统使用 D435i + YOLO 识别物体语义类别，将类别映射到软/中/硬三类
“视觉语义-阻抗策略库”，并在本文方法 Mode C 中同时调度机械臂阻抗、
Omega.7 力反馈和夹爪策略参数。

## 📂 文件结构

| 文件 | 说明 |
|------|------|
| [`unified_teleop_experiment.py`](unified_teleop_experiment.py) | **主实验脚本** — 4种模式按键切换 + 多参数策略库 + 轨迹记录 + 评分卡 |
| [`01_experiment_architecture.md`](01_experiment_architecture.md) | 实验架构设计文档（参数表/评分体系/键盘映射） |
| [`enhanced_physics_table.json`](enhanced_physics_table.json) | 增强版物理参数查表（含 K_rot/D_trans/D_rot/M/K_fb/gripper_speed） |
| [`physics_table.json`](physics_table.json) | 原始 YOLO 查表（vision_physics_mapper 使用） |
| [`vision_physics_mapper.py`](vision_physics_mapper.py) | YOLO 视觉 → PhysicsProfile 查表映射模块 |
| [`force_estimator.py`](force_estimator.py) | 外部接触力估计器（基于 Jacobian 伪逆） |
| [`grip_force_estimator.py`](grip_force_estimator.py) | 夹持力近似估计器（基于腕部关节力矩） |

## 🚀 快速开始

### 硬件连接

- Franka Panda IP: `172.16.0.2`
- Omega.7 通过 USB 连接
- (可选) RealSense D415/D435 用于 YOLO 视觉

### 运行实验

```bash
# 1. 干跑模式（测试评分界面，不需要硬件）
python3 experiment/unified_teleop_experiment.py --dry-run

# 2. 运行完整实验（轨迹保存到 data/ 目录）
python3 experiment/unified_teleop_experiment.py

# 3. 指定轨迹输出目录和 YOLO 模型
python3 experiment/unified_teleop_experiment.py \
    --trajectory-dir my_experiment_data \
    --yolo-model yolo11n.pt
```

### 实验流程

1. **放一个物体**（软/中/硬）
2. 按 **a/b/c/d** 选择实验模式
3. Mode B 下按 **1/2/3** 人工选择软/中/硬策略；Mode C/D 由视觉识别记录物体类别
4. 按 **s/m/h** 手动标记物体类型（可用于无视觉或校正记录标签）
5. 按 **r** 开始录制
6. 操作 Omega.7 完成抓取任务
7. 按 **r** 停止录制 → 自动弹出评分卡
8. 输入人工评分 → 保存到 `_score.json`
9. 每个物体完成 a/b/c/d 后查看对比表，换物体继续

### 键盘快捷键

| 按键 | 功能 |
|------|------|
| `a` | mode a — 固定阻抗基线 |
| `b` | mode b — 人工选择软/中/硬多参数策略 |
| `c` | mode c — 视觉自动调用多参数阻抗策略库（本文方法）|
| `d` | mode d — 仅视觉显示/记录，不改变控制参数 |
| `1` / `2` / `3` | mode b 下选择软/中/硬策略 |
| `s` | 标记软物体 |
| `m` | 标记中等物体 |
| `h` | 标记硬物体 |
| `r` | 开始/停止录制 |
| `i` / `↑` | mode b: K_trans +10 |
| `k` / `↓` | mode b: K_trans -10 |
| `j` / `←` | mode b: deadband -0.05 |
| `l` / `→` | mode b: deadband +0.05 |
| `[` / `]` | mode b: gripper_speed ±0.01 |
| `q` | 退出（自动汇总）|

## 📊 评价体系

### 自动计算指标

- ⏱ 完成时间 (s)
- 📏 Omega.7 路径长度 (m)
- 💪 末端外力峰值 (N)

### 人工评分

- 成功率 (0/1)
- NASA-TLX (0-100)
- 损伤评分 (0=无损伤 ~ 3=严重)
- 人工评分 (0=差 ~ 3=优秀)

### 输出文件

- `trajectory_{timestamp}_{mode}_{object}.csv` — 轨迹数据，含当前多参数策略和策略来源
- `trajectory_{timestamp}_{mode}_{object}_score.json` — 评分数据 + 自动指标 + 策略快照
- `trajectory_{timestamp}_{mode}_{object}_metrics.txt` — 自动指标文本摘要
- `experiment_summary.json` — 实验汇总

## 四种实验模式

| 模式 | 作用 | 控制参数是否变化 |
|------|------|----------------|
| Mode A | 固定阻抗基线 | 固定 medium/default 参数 |
| Mode B | 人工选择阻抗策略 | 操作者按 `1/2/3` 选择 soft/medium/hard |
| Mode C | 本文方法 | YOLO 自动调用视觉语义-阻抗策略库 |
| Mode D | 视觉消融 | YOLO 只显示/记录类别，不改变任何控制参数 |

## 视觉语义-阻抗策略库

| 物体 | K_trans | K_rot | D_trans | D_rot | M | 夹爪速度 | 夹爪力上限 |
|------|---------|-------|---------|-------|---|---------|---------|
| 软 | 50 N/m | 5 Nm/rad | 14.1 Ns/m | 4.5 Nms/rad | 0.5 kg | 20 mm/s | 8 N |
| 中 | 150 N/m | 10 Nm/rad | 24.5 Ns/m | 6.3 Nms/rad | 1.0 kg | 50 mm/s | 20 N |
| 硬 | 800 N/m | 50 Nm/rad | 56.6 Ns/m | 14.1 Nms/rad | 2.0 kg | 100 mm/s | 60 N |

阻尼自动推导公式: `D = 2 * ζ * √(K * M)`, ζ=1.0 (临界阻尼)

Mode C 会把视觉语义类别转换成一组协同参数：
`K_trans, K_rot, damping_ratio, K_fb, deadband, gripper_speed, gripper_force_limit`。
论文表述应强调“多参数阻抗辅助”，而不是单一参数查表。
