# teleop_omega7_franka_vision.py 三种手感模式添加方案

## 目标

基于 [`interactive_teleop.py`](my_test/interactive_teleop.py) 的三种物体手感预设，为 [`teleop_omega7_franka_vision.py`](my_test/teleop_omega7_franka_vision.py) 添加软/中/硬三种手感模式，并建立 YOLO 物体→模式的映射表。

## 映射表 (Object → Mode)

| 物体 | 模式 | label | K_trans | K_rot | damping_ratio | K_fb | deadband | scale |
|------|------|-------|---------|-------|---------------|------|----------|-------|
| banana (香蕉) | soft_obj | soft | 50 | 5 | 0.8 | 0.2 | 0.3 | 3.0 |
| bottle (瓶子) | medium_obj | medium | 150 | 10 | 1.0 | 0.5 | 0.4 | 3.0 |
| mouse (鼠标) | hard_obj | hard | 250 | 13 | 1.2 | 1.0 | 0.5 | 3.0 |

## 修改方式

按代码逻辑顺序列出 8 项修改，每项说明位置和内容。

---

### 修改 1：添加 PRESETS 字典 (位置: 文件顶部, 配置区)

在现有配置参数（约第 52-86 行）之后添加三个手感模式的 PRESETS：

```python
# ── 三种手感模式预设 ──
PRESETS = {
    "soft_obj": {
        "name": "🫧 软物体手感",
        "desc": "低刚度 + 低力反馈 — 模拟触碰香蕉/海绵",
        "K_trans": 50.0, "K_rot": 5.0,
        "damping_ratio": 0.8, "K_fb": 0.2, "deadband": 0.3,
        "scale": 3.0,
    },
    "medium_obj": {
        "name": "📦 中物体手感",
        "desc": "中刚度 + 中力反馈 — 模拟触碰瓶子/纸盒",
        "K_trans": 150.0, "K_rot": 10.0,
        "damping_ratio": 1.0, "K_fb": 0.5, "deadband": 0.4,
        "scale": 3.0,
    },
    "hard_obj": {
        "name": "🪨 硬物体手感",
        "desc": "高刚度 + 强力反馈 — 模拟触碰鼠标/金属",
        "K_trans": 250.0, "K_rot": 13.0,
        "damping_ratio": 1.2, "K_fb": 1.0, "deadband": 0.5,
        "scale": 3.0,
    },
}
```

### 修改 2：添加物体→模式映射表 (位置: PRESETS 之后)

```python
# ── YOLO 检测类名 → 手感模式映射 ──
OBJECT_TO_MODE = {
    "banana": "soft_obj",
    "apple": "soft_obj",
    "orange": "soft_obj",
    "bottle": "medium_obj",
    "cup": "medium_obj",
    "bowl": "medium_obj",
    "book": "hard_obj",
    "mouse": "hard_obj",
    "cell phone": "hard_obj",
    "keyboard": "hard_obj",
    "scissors": "hard_obj",
}
```

### 修改 3：添加平滑过渡函数 (位置: main() 之前)

参考 [`interactive_teleop.py`](my_test/interactive_teleop.py:602) 的 `_smooth_transition`，实现一个函数级别的版本：

```python
# 平滑过渡参数
TRANSITION_STEPS = 30
TRANSITION_INTERVAL = 0.01

def smooth_transition(ctrl, current, target, steps=TRANSITION_STEPS):
    """
    后台线程：将控制器参数从 current 平滑过渡到 target
    current/target: dict of {K_trans, K_rot, damping_ratio}
    """
    # 实现 smoothstep 插值，逐步设置阻抗和阻尼
```

### 修改 4：添加键盘检测线程 (位置: main() 之前)

参考 [`interactive_teleop.py`](my_test/interactive_teleop.py:957) 的 `_keyboard_loop`，实现一个独立的键盘线程，检测 z/x/c/v/b/h 按键。

### 修改 5：主循环添加模式管理变量 (位置: main() 第 4 节 "读取初始状态" 之后)

初始化模式相关变量：

```python
# ── 模式管理 ──
current_mode = "soft_obj"          # 当前激活模式
prev_mode = None                   # 用于检测切换
impedance = np.diag([200.0, 200.0, 200.0, 10.0, 10.0, 10.0])  # 初始阻抗
```

### 修改 6：主循环阻尼矩阵动态更新 (位置: 控制循环内)

当前 `teleop_omega7_franka_vision.py` 使用固定阻抗矩阵。修改为根据当前模式动态更新刚度和阻尼：

```python
# 根据当前模式更新阻抗
p = PRESETS[current_mode]
impedance = np.diag([p["K_trans"]]*3 + [p["K_rot"]]*3)
ctrl.set_impedance(impedance)
ctrl.set_damping_ratio(p["damping_ratio"])
```

### 修改 7：主循环 Omega.7 力反馈 (位置: 控制循环 "保持 Omega 零力" 处)

将 `dhd.setForce(np.zeros(3))` 替换为：

```python
p = PRESETS[current_mode]
# 计算力反馈（可以简单用法向量的 K_fb 分量，或后续接入外力估计）
F_haptic = np.zeros(3)
F_haptic[2] = 0.3 * p["K_fb"]  # Z 方向模拟接触反力
dhd.setForce(F_haptic)
```

### 修改 8：主循环集成视觉自动切换 (位置: 主循环末尾/检测信息打印处)

在读取 [`camera.get_result()`](my_test/teleop_omega7_franka_vision.py:627) 后，增加自动切换逻辑：

```python
# 视觉自动切换模式
det = camera.get_result()
if det.detected and det.physics_label:
    # 从 detection 的 physics_label 或者 class_name 映射
    if det.class_name in OBJECT_TO_MODE:
        target_mode = OBJECT_TO_MODE[det.class_name]
        if target_mode != current_mode:
            print(f"\n  👁️ YOLO 检测到 {det.class_name} → 切换到 {PRESETS[target_mode]['name']}")
            current_mode = target_mode
```

## 参数对照表 (交互参考)

| 参数 | interactive_teleop.py PRESETS | teleop_omega7_franka_vision.py 新代码 |
|------|-------------------------------|---------------------------------------|
| PRESETS 定义 | 第 204-256 行 | 新文件，配置区 |
| _profile_to_preset | 第 712-720 行 | 新 OBJECT_TO_MODE 映射表 |
| _smooth_transition | 第 602-659 行 | 新函数 |
| _keyboard_loop | 第 957-1030 行 | 新函数 |
| Vision 自动切换 | 第 1638-1665 行 | 修改主循环，第 8 项 |

## 代码编辑具体位置

**文件**: [`my_test/teleop_omega7_franka_vision.py`](my_test/teleop_omega7_franka_vision.py)

| # | 操作 | 起始行 | 结束行 | 说明 |
|---|------|--------|--------|------|
| 1 | 添加 | 87 | 88 | 在 GRIPPER_EPS_OUTER 之后添加 PRESETS |
| 2 | 添加 | 88 | 89 | 在 PRESETS 之后添加 OBJECT_TO_MODE |
| 3 | 添加 | 410 | 430 | 在 main() 之前添加平滑过渡函数 |
| 4 | 添加 | 430 | 460 | 在 main() 之前添加键盘线程函数 |
| 5 | 修改 | 484 | 493 | 将固定阻抗矩阵改为变量 |
| 6 | 修改 | 478 | 478 | 初始化 current_mode |
| 7 | 修改 | 578 | 578 | dhd.setForce 替换为力反馈 |
| 8 | 修改 | 626 | 646 | 在检测信息打印处添加 auto-switch |

## 执行顺序 (Code 模式)

1. 添加 PRESETS 字典 + OBJECT_TO_MODE 映射
2. 添加 `smooth_transition()` + `keyboard_loop()` 函数
3. 修改 main() 初始化：增加 `current_mode`、`transition_active` 等变量
4. 修改阻抗初始化：设 `impedance` 为变量，后续可修改
5. 修改控制循环：添加 `apply_current_mode()` 函数，动态更新阻抗/阻尼/力反馈
6. 启动键盘线程，在主循环中处理 z/x/c 按键
7. 在检测结果逻辑处添加 YOLO 自动切换
8. 修改 dhd.setForce 为按 K_fb 策略施加反馈力
