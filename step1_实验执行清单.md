# Step 1：实验执行清单（您去硬件上操作）

> 分两大步：先分步验证(Step 0-5)，再正式实验(Step 6)
> 每一步都标注了：**干什么** → **怎么跑** → **判断是否通过**

---

## 1️⃣ Step 0：硬件检查 + 基线遥操作

```bash
# 启动基础遥操作，确认所有硬件正常
python3 my_test/teleop_omega7_franka.py
```

**检查项：**
- [ ] Omega.7 连接成功（打印 "✓ 已连接: xxx"）
- [ ] Franka Panda 连接成功（打印 "✓ 机械臂已连接"）
- [ ] 夹爪连接成功（打印 "✓ 夹爪已连接"）
- [ ] 手柄移动 → 机械臂末端跟随（方向正确）
- [ ] 夹钳捏合 → 夹爪闭合

**通过标准：** 以上5项全部 ✓ → 进入Step 1

---

## 2️⃣ Step 1：力估计器验证

### Step 1a — 空载噪声测试

```bash
python3 plans/step_1a_force_noise.py
```

**干什么：** 机械臂空载，记录5秒 `O_F_ext_hat_K` 数据，看噪声水平。

**预期结果：**
```
F_ext 统计:
  Fx: mean=0.00, std=0.12, max|err|=0.35 N
  Fy: mean=0.00, std=0.10, max|err|=0.30 N
  Fz: mean=-0.01, std=0.15, max|err|=0.40 N
```

- [ ] **通过条件：** std < 0.5 N（所有轴）
- [ ] **如果未通过：** 去 `plans/force_estimator.py` 中调大滤波系数（`_filter_alpha` 从0.3降到0.1）

### Step 1b — 外力响应测试

```bash
python3 plans/step_1b_force_response.py
```

**干什么：** 机械臂保持位置，用手推末端，看 F_ext 读数变化。

**操作：** 脚本运行后，用手推末端（向-Z方向，约3~5N力度），观察终端输出的 F_ext。

**预期结果：** 推的时候 Fz 明显变化，松开后回到零附近。

- [ ] **通过条件：** 用力推时 Fz 明显变化（正负方向正确），松开后回到零附近
- [ ] **如果未通过：** 切到显式模式 `use_builtin=False`（在 force_estimator.py 中）

---

## 3️⃣ Step 2：自适应导纳验证

### Step 2a — 刚度切换手感测试

```bash
python3 plans/step_2a_stiffness_switch.py
```

**干什么：** 机械臂固定位置，每5秒自动切换刚度 K=50 → 150 → 300，用手推末端感受变化。

**预期手感：**
| K值 | 手感 |
|-----|------|
| 50 N/m | 像推海绵，很容易推动 |
| 150 N/m | 像推中等硬度的橡皮 |
| 300 N/m | 像推木板，很硬 |

- [ ] **通过条件：** 切换时机械臂不抖动、不震动，三种手感明显不同
- [ ] **如果切换时抖动：** 在 `plans/adaptive_admittance.py` 中加切换缓冲（`_min_switch_interval`）

### Step 2b — 视觉触发切换测试

```bash
python3 plans/step_2b_visual_trigger.py
```

**干什么：** 模拟YOLO检测到不同物体，自动触发刚度切换。

**预期输出：**
```
[模拟视觉] 检测到 apple (soft) → K=50 N/m
[模拟视觉] 检测到 book (hard) → K=300 N/m
[模拟视觉] 检测到 bottle (medium) → K=150 N/m
```

- [ ] **通过条件：** 切换平滑无震荡，终端打印正确

---

## 4️⃣ Step 3：夹持力估计验证

### Step 3a — 空载基线采集

```bash
python3 plans/step_3a_grip_baseline.py
```

**干什么：** 夹爪完全张开，空载状态记录5秒 τ_wrist 数据。

**预期结果：**
```
|τ_wrist| 统计: mean=0.23 Nm, std=0.08 Nm, max=0.45 Nm
建议: torque_threshold >= 1.0 Nm, tau_max >= 3.0 Nm
```

- [ ] **通过条件：** 拿到空载基线数值
- [ ] **记录 tau_max 建议值：** _______ Nm（后续用到）

### Step 3b — 夹持数据采集

```bash
python3 plans/step_3b_grip_test.py
```

**干什么：** 机械臂移动到物体上方 → 张开夹爪 → 下移 → 夹持 → 保持3s → 释放。全程记录 width, τ_wrist, f_grip。

**操作：** 在夹爪前放一个物体（苹果或水瓶），脚本会自动完成夹持流程。

**预期结果：**
```
[夹持阶段] 夹持中...
  width=0.030m, |τ_wrist|=4.2Nm, f_grip=0.42
  → 接触事件: 📌 已夹持!
[释放阶段] 释放中...
  width=0.070m, |τ_wrist|=0.3Nm, f_grip=0.03
```

- [ ] **通过条件：** 夹持时 f_grip>0.3，释放后 f_grip<0.1，接触事件正确触发
- [ ] **如果误报：** 调高 `plans/grip_force_estimator.py` 中的 `torque_threshold`
- [ ] **如果漏报：** 调低 `debounce_frames`

**✨ 这步的数据可以用来生成论文图3！记得保存CSV文件。**

---

## 5️⃣ Step 4：力反馈验证

### Step 4a — 零力透明模式

```bash
python3 plans/step_4a_force_zero.py
```

**干什么：** Omega.7 输出零力，确认手柄自由无阻力。

- [ ] **通过条件：** 手柄非常轻，几乎没有阻尼

### Step 4b — 力反馈手感确认

```bash
python3 plans/step_4b_force_feedback.py
```

**干什么：** 操作员通过 Omega.7 控制机械臂移动，当末端进入"虚拟墙面"区域时 Omega.7 产生阻力。

**操作：** 移动手柄向 Z 负方向移动，感受阻力变化。

- [ ] **通过条件：** 进入虚拟墙面后 Omega.7 逐渐变重
- [ ] **如果感觉不到力：** 确认 `dhd.enableForce(True)` 已调用

---

## 6️⃣ Step 5：三线集成验证

### Step 5a — 模式B验证

```bash
python3 plans/shared_control_node.py --mode b
```

**检查项：**
- [ ] YOLO 能识别物体（终端打印检测结果）
- [ ] 力反馈有但固定不变（不管抓什么，反馈力度一样）
- [ ] 机械臂跟随手柄移动

### Step 5b — 模式C验证

```bash
python3 plans/shared_control_node.py --mode c
```

**检查项：**
- [ ] YOLO 识别不同物体时刚度自动切换
- [ ] 力反馈随物体变化（抓苹果轻、抓书重）
- [ ] 切换平滑无震荡

---

## 7️⃣ 🔥 Step 6：正式对比实验（核心！）

### 准备工作

- [ ] **准备5类物体：**
  - 苹果 × 5个（软）
  - 香蕉 × 5根（软）
  - 塑料水瓶 × 1个（中等）
  - 书 × 1本（硬）
  - 手机/手机模型 × 1个（硬）
- [ ] **托盘 × 1**（放在机械臂前方20cm处）
- [ ] **NASA-TLX问卷 × 10份**（模板在 `plans/nasa_tlx_template.md`）
- [ ] **笔 × 3**
- [ ] **实验记录表**（人工记录成功/失败/破损）

### 实验流程（每位操作员约40分钟）

```
┌─ 练习5分钟 ──────────────────────────────────────┐
│  让操作员自由操作 Omega.7，熟悉手感                │
└────────────────────────────────────────────────────┘
                        │
                        ▼
┌─ 模式A（传统）─ 25次抓取 ─────────────────────────┐
│  5物体 × 5重复 = 25次                              │
│  命令: python3 plans/experiment_trial_runner.py    │
│         --full --operator 1 --mode a               │
│  每次记录: 成功(s)/失败(f)/破损(d)                 │
└────────────────────────────────────────────────────┘
                        │
                        ▼
┌─ 📝 填写NASA-TLX问卷第1份 ───────────────────────┐
└────────────────────────────────────────────────────┘
                   休息1分钟
                        │
                        ▼
┌─ 模式B（固定增益）─ 25次抓取 ─────────────────────┐
│  5物体 × 5重复 = 25次                              │
│  命令: python3 plans/experiment_trial_runner.py    │
│         --full --operator 1 --mode b               │
└────────────────────────────────────────────────────┘
                        │
                        ▼
┌─ 📝 填写NASA-TLX问卷第2份 ───────────────────────┐
└────────────────────────────────────────────────────┘
                   休息1分钟
                        │
                        ▼
┌─ 模式C（本文方法）─ 25次抓取 ─────────────────────┐
│  5物体 × 5重复 = 25次                              │
│  命令: python3 plans/experiment_trial_runner.py    │
│         --full --operator 1 --mode c               │
└────────────────────────────────────────────────────┘
                        │
                        ▼
┌─ 📝 填写NASA-TLX问卷第3份 ───────────────────────┐
└────────────────────────────────────────────────────┘
                    ✅ 完成！
```

**重复以上流程给操作员2、操作员3。**

### 数据文件产出

实验完成后，会在 `data/` 目录下生成：
```
data/experiment_YYYYMMDD_HHMMSS/
├── operator_1/
│   ├── mode_a_apple.csv, mode_a_banana.csv, ...
│   ├── mode_b_apple.csv, mode_b_banana.csv, ...
│   ├── mode_c_apple.csv, mode_c_banana.csv, ...
│   └── tlx_scores.yaml
├── operator_2/
│   └── ...
└── operator_3/
    └── ...
```

### 快捷命令汇总

```bash
# 完整实验（推荐）
python3 plans/experiment_trial_runner.py --full --operator 1

# 仅打印计划（dry-run，确认顺序）
python3 plans/experiment_trial_runner.py --full --operator 1 --dry-run

# 单次测试（调试用）
python3 plans/experiment_trial_runner.py --operator 1 --mode c --obj banana --trial 1
```

---

## ⚡ 快速验收清单

| 步骤 | 命令 | 预期结果 | 完成？ |
|------|------|---------|-------|
| Step 0 | `teleop_omega7_franka.py` | 手柄→机械臂跟随 | [ ] |
| Step 1a | `step_1a_force_noise.py` | 噪声std<0.5N | [ ] |
| Step 1b | `step_1b_force_response.py` | 推末端Fz变化 | [ ] |
| Step 2a | `step_2a_stiffness_switch.py` | 三档刚度手感不同 | [ ] |
| Step 2b | `step_2b_visual_trigger.py` | 类别→刚度正确切换 | [ ] |
| Step 3a | `step_3a_grip_baseline.py` | 拿到空载基线 | [ ] |
| Step 3b | `step_3b_grip_test.py` | 夹持/释放曲线正确 | [ ] |
| Step 4a | `step_4a_force_zero.py` | 手柄轻无阻力 | [ ] |
| Step 4b | `step_4b_force_feedback.py` | 虚拟墙面有阻力 | [ ] |
| Step 5a | `shared_control_node.py --mode b` | YOLO+固定力反馈 | [ ] |
| Step 5b | `shared_control_node.py --mode c` | 自适应全流程 | [ ] |
| Step 6 | `experiment_trial_runner.py` | 采集75次数据 | [ ] |
