# 视觉语义驱动的多参数阻抗辅助遥操作实验方案

## 方法定位

论文题目暂定为：**视觉语义驱动的多参数阻抗辅助遥操作方法研究**。

系统使用 D435i + YOLO 识别物体语义类别，并将类别归入 soft、medium、hard 三类。
本文方法不是单一参数查表，而是通过“视觉语义-阻抗策略库”同时调度：

- `K_trans`：Panda 末端平动刚度
- `K_rot`：Panda 末端旋转刚度
- `damping_ratio`：阻尼比
- `K_fb`：Omega.7 主端力反馈增益
- `deadband`：力反馈死区
- `gripper_speed`：Franka Hand 夹爪速度
- `gripper_force_limit`：夹爪力限制记录值

## 四种模式

| 模式 | 名称 | 视觉 | 控制参数 |
|------|------|------|----------|
| Mode A | 固定阻抗基线 | 不参与控制 | 全部固定为 default/medium |
| Mode B | 人工选择策略 | 不自动调参 | 操作者按 `1/2/3` 选择 soft/medium/hard 策略 |
| Mode C | 本文方法 | 自动识别 | YOLO 自动调用多参数阻抗策略库 |
| Mode D | 视觉消融 | 只显示/记录 | 不改变阻抗、力反馈或夹爪参数 |

## 推荐实验流程

1. 选择 soft、medium、hard 三类物体，每类 1-2 个。
2. 每个物体依次完成 Mode A/B/C/D。
3. 每个“物体类型 × 模式”建议重复 5-10 次。
4. 每次 trial 按 `r` 开始录制，完成抓取/搬运任务后再按 `r` 停止。
5. 停止后填写评分卡：成功率、NASA-TLX、损伤评分、人工整体评分。
6. 完成一类物体的四模式实验后，查看终端四模式对比表。

## 评价指标

自动指标：

- 完成时间 `completion_time_s`
- Omega.7 路径长度 `path_length_m`
- 平均/最大速度
- 末端外力峰值 `F_ext_peak_N`
- 末端外力均值 `F_ext_mean_N`

人工指标：

- 成功率 `success`
- 主观劳累程度 `nasa_tlx`
- 损伤评分 `damage_score`
- 变形量 `deformation_mm`
- 整体评分 `human_score`

## 数据产物

每次 trial 会生成：

- `trajectory_YYYYMMDD_HHMMSS_{mode}_{object}.csv`
- `trajectory_YYYYMMDD_HHMMSS_{mode}_{object}_metrics.txt`
- `trajectory_YYYYMMDD_HHMMSS_{mode}_{object}_score.json`

最终退出时生成：

- `experiment_summary.json`

CSV 中记录当前模式、物体标签、策略来源、阻抗参数、力反馈参数、夹爪参数、
Omega.7 轨迹、末端外力、目标/实际末端位置等字段，可直接用于论文统计和绘图。
