# 修改计划：增加机械臂安全限制 + 降低碰撞灵敏度

## 1. 背景
`shared_control_node.py:283` 调用了 `set_default_behavior()`，它设置了极低的碰撞阈值（关节扭矩 10 Nm，笛卡尔力 10 N），导致手指轻轻触碰就触发 Franka Reflex 报警停机。

## 2. 修改内容

### 2.1 提高碰撞阈值 — initialize() 中
在 `self.panda.set_default_behavior()` 之后，通过 libfranka Robot 对象的 `set_collision_behavior()` 方法设置更宽松的阈值：

- 正常运行时关节扭矩阈值：10 → 20 Nm（接触/碰撞一致）
- 正常运行时笛卡尔力阈值：10 → 25 N（接触/碰撞一致）
- 加速/减速时关节扭矩阈值：20 → 30 Nm
- 加速/减速时笛卡尔力阈值：20 → 35 N

### 2.2 添加笛卡尔工作空间边界 — run() 位置映射后
在 `target_pos` 计算后添加立方体边界钳制（相对于初始位姿 `_virtual_ref`）：
- X, Y: ±0.3m
- Z: -0.2m ~ +0.3m（Z 向下为 negative，避免撞地）

### 2.3 添加末端速度限幅 — run() 中
对 `target_pos` 做低通滤波/速率限制，防止 Omega.7 快速抖动导致 Franka 高速运动。

## 3. 实现细节

### 修改位置
| 修改点 | 文件位置 | 行号 |
|-------|---------|------|
| 碰撞阈值 | `shared_control_node.py` initialize() | 第283行后 |
| 笛卡尔边界 | `shared_control_node.py` run() 位置映射段 | 第689-697行 |
| 速度限幅 | `shared_control_node.py` run() | 新增实例变量 `_last_target_pos` 初始化，然后在位置映射后限速 |

### 代码片段

```python
# ── 设置宽松碰撞阈值（避免轻微触碰就报警停机）──
robot = self.panda.get_robot()
robot.set_collision_behavior(
    lower_torque_thresholds_acceleration=[30,30,30,30,30,30,30],
    upper_torque_thresholds_acceleration=[30,30,30,30,30,30,30],
    lower_torque_thresholds_nominal=[20,20,20,20,20,20,20],
    upper_torque_thresholds_nominal=[20,20,20,20,20,20,20],
    lower_force_thresholds_acceleration=[35,35,35,35,35,35],
    upper_force_thresholds_acceleration=[35,35,35,35,35,35],
    lower_force_thresholds_nominal=[25,25,25,25,25,25],
    upper_force_thresholds_nominal=[25,25,25,25,25,25],
)
```

```python
# ── 笛卡尔工作空间边界钳制 ──
POS_BOUNDS = {
    "x": (-0.3, 0.3),
    "y": (-0.3, 0.3),
    "z": (-0.2, 0.3),
}

# 在 target_pos 计算后：
ref = self._virtual_ref
target_pos = np.clip(target_pos,
    [ref[0] + POS_BOUNDS["x"][0], ref[1] + POS_BOUNDS["y"][0], ref[2] + POS_BOUNDS["z"][0]],
    [ref[0] + POS_BOUNDS["x"][1], ref[1] + POS_BOUNDS["y"][1], ref[2] + POS_BOUNDS["z"][1]],
)
```

```python
# ── 末端速度限幅 ──
# 在 __init__ 中：
# self._last_target_pos = np.zeros(3)
# MAX_EE_VELOCITY = 0.3  # m/s

# 在 run() 中，position mapping 后：
dt_pos = 1.0 / POS_CTRL_FREQ  # 0.005s
max_delta = MAX_EE_VELOCITY * dt_pos  # 每周期最大位移
delta = target_pos - self._last_target_pos
delta_mag = np.linalg.norm(delta)
if delta_mag > max_delta:
    target_pos = self._last_target_pos + delta / delta_mag * max_delta
self._last_target_pos = target_pos.copy()
```
