# 分步验证计划 — 在真实机械臂上逐步验证每个功能

> **原则**：每一步都是一个可独立运行的 Python 脚本，跑完后观察现象、记录数据、确认是否符合预期。不符合就改代码，符合就进入下一步。

---

## 验证流程图

```
Step 0: 硬件检查 + 基线遥操作
    │
    ▼
Step 1: 力估计器在线验证
    ├── 1a: 空载噪声测试 (只读数据，不控制)
    └── 1b: 外力响应测试 (推末端，看 F_ext 变化)
    │
    ▼
Step 2: 自适应导纳在线验证
    ├── 2a: 刚度切换测试 (50→300 N/m，用手推感受差异)
    └── 2b: 视觉触发切换测试 (模拟 YOLO 检测结果)
    │
    ▼
Step 3: 夹持力估计在线验证
    ├── 3a: 空载基线采集 (抓手张开，记录 τ_wrist 噪声)
    └── 3b: 夹持数据采集 (抓物体→保持→释放，观察 f_grip)
    │
    ▼
Step 4: 力反馈在线验证
    ├── 4a: 零力透明模式
    └── 4b: 力反馈手感确认 (推机械臂，Omega.7 应感受到阻力)
    │
    ▼
Step 5: 完整三线集成验证
    ├── 5a: 模式B (视觉+固定增益) 完整流程跑通
    └── 5b: 模式C (视觉+自适应) 完整流程跑通
```

---

## Step 0: 硬件连接检查 + 基线遥操作

**目标**：确认所有硬件正常工作，[`my_test/teleop_omega7_franka.py`](my_test/teleop_omega7_franka.py) 可流畅运行。

**操作**：
```bash
# 直接在 teleop 基础上跑，确认 baseline 没问题
cd ~/sunhan
python3 my_test/teleop_omega7_franka.py
```

**观察清单**：
- [ ] Omega.7 连接成功（打印系统名）
- [ ] Franka 连接成功（无错误）
- [ ] 手柄移动 → 机械臂跟随（方向正确、无抖动、延迟<50ms）
- [ ] 夹钳捏合 → 夹爪闭合（角度映射正确）
- [ ] Ctrl+C 安全停止

**预期问题**：
- 方向不对 → 调 [`SIGN`](my_test/teleop_omega7_franka.py:27)
- 速度太慢/太快 → 调 [`SCALE_POS`](my_test/teleop_omega7_franka.py:26)
- 夹爪映射不对 → 调 [`GRIPPER_ANGLE_OPEN/CLOSE`](my_test/teleop_omega7_franka.py:41-42)

**进入下一步的条件**：机械臂流畅跟随手柄移动，夹爪可以抓取/释放。

---

## Step 1: 力估计器在线验证

### 1a — 空载噪声测试

**脚本**：[`plans/step_1a_force_noise.py`](plans/step_1a_force_noise.py)

**干什么**：连接 Franka，空载时采集 5 秒 `O_F_ext_hat_K` 数据，看噪声水平。

```bash
python3 plans/step_1a_force_noise.py
```

**预期输出**：
```
[Step 1a] 空载外力噪声测试 (5秒) ...
采样: 500 帧
F_ext 统计:
  Fx: mean=0.00, std=0.12, max|err|=0.35 N
  Fy: mean=0.00, std=0.10, max|err|=0.30 N
  Fz: mean=-0.01, std=0.15, max|err|=0.40 N
```

**判断标准**：
- ✅ std < 0.5 N → 噪声可接受
- ❌ std > 1.0 N → 需要加大滤波 α，或检查机器人状态（是否在震动）

### 1b — 外力响应测试

**脚本**：[`plans/step_1b_force_response.py`](plans/step_1b_force_response.py)

**干什么**：保持机械臂位置固定（阻抗控制模式），用手推末端，看 F_ext 读数是否合理。

```bash
python3 plans/step_1b_force_response.py
```

**操作**：
1. 脚本运行后提示 "请用手推末端执行器 (Z方向)"
2. 用手轻轻推机械臂末端（向-Z方向，约3~5N力度）
3. 观察终端打印的 F_ext
4. 按 Enter 停止

**预期输出**：
```
[Step 1b] 外力响应测试
  模式: 固定刚度 K=200 N/m，用手推末端
  Fx: -0.05 | Fy: 0.03 | Fz: -3.21 ← 推的时候 Z 方向明显变化
  Fx: -0.02 | Fy: 0.01 | Fz: -4.85 ← 推得更用力
  Fx:  0.01 | Fy: 0.00 | Fz: -0.12 ← 松开，恢复零
```

**判断标准**：
- ✅ 用力推时 Fz 明显变化（正负方向正确）
- ✅ 松开后回到零附近
- ❌ 数值一直很大（>5N）→ 机器人负载参数没设对
- ❌ 推了没反应 → `O_F_ext_hat_K` 被禁用或滤波太强

**可能的修改**：
- [`plans/force_estimator.py`](plans/force_estimator.py) 中调 `set_filter_alpha(0.5)` 加快响应
- 如果 O_F_ext_hat_K 不可靠，切到显式模式 `use_builtin=False`

---

## Step 2: 自适应导纳在线验证

### 2a — 刚度切换手感测试

**脚本**：[`plans/step_2a_stiffness_switch.py`](plans/step_2a_stiffness_switch.py)

**干什么**：机械臂保持固定位置，运行时切换 K=50 / K=300，用手推末端感受刚度变化。

```bash
python3 plans/step_2a_stiffness_switch.py
```

**操作**：
1. 脚本每 5 秒自动切换刚度：50 → 150 → 300 → 50 ...
2. 每次切换后用手推末端，感受软硬变化
3. 观察终端输出的当前 K 值

**预期手感**：
```
K=50 N/m  → 像推海绵，很容易推动，有缓冲感
K=150 N/m → 像推中等硬度的橡皮
K=300 N/m → 像推木板，很硬
```

**判断标准**：
- ✅ 切换时机械臂不抖动、不震动
- ✅ 手感明显不同（50 和 300 差别很大）
- ❌ 切换时机械臂弹跳/震荡 → `set_impedance()` 需要先减速再切换
- ❌ 推不动（刚度可能被限幅了）→ 检查 [`K_TRANS_MIN/MAX`](plans/adaptive_admittance.py:54-55)

### 2b — 视觉触发切换测试（模拟 YOLO）

**脚本**：[`plans/step_2b_visual_trigger.py`](plans/step_2b_visual_trigger.py)

**干什么**：模拟视觉检测到不同物体，自动触发刚度切换。

```bash
python3 plans/step_2b_visual_trigger.py
```

**效果**：
```
[模拟视觉] 检测到 apple (soft) → K=50 N/m
[模拟视觉] 检测到 book (hard) → K=300 N/m
[模拟视觉] 检测到 bottle (medium) → K=150 N/m
...
```

**这步通过后**：[`plans/adaptive_admittance.py`](plans/adaptive_admittance.py) 可认为已验证完成。

---

## Step 3: 夹持力估计在线验证

### 3a — 空载基线采集

**脚本**：[`plans/step_3a_grip_baseline.py`](plans/step_3a_grip_baseline.py)

```bash
python3 plans/step_3a_grip_baseline.py
```

**干什么**：夹爪完全张开，空载状态记录 5 秒 τ_wrist 数据，确定 `torque_threshold` 和 `tau_max` 的合理值。

**预期输出**：
```
[Step 3a] 夹持力空载基线 (5秒)
|τ_wrist| 统计: mean=0.23 Nm, std=0.08 Nm, max=0.45 Nm
建议: torque_threshold >= 1.0 Nm, tau_max >= 3.0 Nm
```

### 3b — 夹持数据采集

**脚本**：[`plans/step_3b_grip_test.py`](plans/step_3b_grip_test.py)

```bash
python3 plans/step_3b_grip_test.py
```

**操作**：
1. 机械臂移动到目标物体上方
2. 脚本控制夹爪：张开 → 下移 → 夹持 → 保持 3s → 释放
3. 全程记录 width, τ_wrist, f_grip

**预期输出**：
```
[夹持阶段] 夹持中...
  width=0.030m, |τ_wrist|=4.2Nm, f_grip=0.42
  → 接触事件: 📌 已夹持!
[释放阶段] 释放中...
  width=0.070m, |τ_wrist|=0.3Nm, f_grip=0.03
```

**判断标准**：
- ✅ 夹持时 f_grip 明显上升（>0.3），释放后下降（<0.1）
- ✅ 接触事件触发正确（不误报、不漏报）
- ❌ 一直报接触（误报）→ 提高 [`torque_threshold`](plans/grip_force_estimator.py:67)
- ❌ 夹持了没触发 → 降低 [`debounce_frames`](plans/grip_force_estimator.py:68)

---

## Step 4: 力反馈在线验证

### 4a — 零力透明模式

**脚本**：[`plans/step_4a_force_zero.py`](plans/step_4a_force_zero.py)

```bash
python3 plans/step_4a_force_zero.py
```

**干什么**：Omega.7 输出零力，确认手柄自由无阻力。

**效果**：手柄应该非常轻，几乎没有阻尼。

### 4b — 力反馈手感确认

**脚本**：[`plans/step_4b_force_feedback.py`](plans/step_4b_force_feedback.py)

```bash
python3 plans/step_4b_force_feedback.py
```

**操作**：
1. 脚本给机械臂施加一个虚拟的"墙面"（Z=0.5m 处虚拟弹簧）
2. 操作员通过 Omega.7 控制机械臂向 Z 负方向移动
3. 当机械臂末端进入 "虚拟墙面" 区域时，Omega.7 应产生阻力

**手感**：
```
F_ext 小 → Omega.7 无阻力（死区内）
F_ext 大 → Omega.7 逐渐变重（K_trans 缩放后）
```

---

## Step 5: 完整三线集成验证

**脚本**：[`plans/shared_control_node.py`](plans/shared_control_node.py)（直接跑）

### 5a — 模式 B 验证
```bash
python3 plans/shared_control_node.py --mode b
```
- 确认 YOLO 能识别物体
- 确认力反馈有但固定不变

### 5b — 模式 C 验证
```bash
python3 plans/shared_control_node.py --mode c
```
- 完整体验：视觉→刚度→力反馈 全部自适应
- 确认切换平滑无震荡

---

## 常见问题排查

| 现象 | 可能原因 | 修改位置 |
|------|---------|---------|
| 力估计一直为零 | O_F_ext_hat_K 未启用 | 切 `use_builtin=False` |
| 力估计噪声太大 | 滤波系数太大 | 调小 `_filter_alpha` |
| 切换刚度时机臂抖 | 切换太频繁 | 加 `_min_switch_interval` |
| 夹持力一直很大 | τ_max 太小 | 调大 `tau_max` |
| 接触事件不触发 | 阈值太高或防抖太多 | 降低阈值或帧数 |
| Omega.7 没力反馈 | 力输出未使能 | 确认 `dhd.enableForce(True)` |
