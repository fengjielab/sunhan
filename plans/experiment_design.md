# 对比实验设计方案

## 1. 实验目的

验证所提出的"视觉-导纳-力觉协同双边遥操作共享控制方法"相比传统固定参数方法的有效性。

### 核心研究问题
1. **抓取成功率**: 自适应方法是否比固定参数方法有更高的抓取成功率？
2. **软物体保护**: 自适应方法是否能有效降低软物体（apple, banana）的破损率？
3. **操作负荷**: 自适应方法是否能降低操作员的认知/体力负荷（NASA-TLX）？
4. **力反馈品质**: 自适应力反馈调度是否比固定增益提供更自然的触感？

---

## 2. 实验变量

### 自变量 (Independent Variables)

| 变量 | 水平 | 说明 |
|------|------|------|
| **控制模式** | 3水平: A/B/C | 详见§3 |
| **物体类别** | 5水平: apple/banana/bottle/book/cell_phone | 覆盖软/中/硬三档 |
| **操作者** | ≥3人 | 不同熟练度 |

### 因变量 (Dependent Variables)

| 指标 | 符号 | 定义 | 采集方式 |
|------|------|------|---------|
| 抓取成功率 | SR | 成功抓取并移至托盘 / 总尝试次数 | 人工记录 |
| 任务完成时间 | TTC | 从开始移动到抓取完成的时间(s) | 人工计时 |
| 软物体破损率 | DR | 破损物体数 / 该类别总尝试次数 | 人工检查 |
| 主端力反馈幅值 | \|F_fb\| | Omega.7 输出力均值/峰值 | CSV 记录 |
| F_ext 峰值 | \|F_ext\|_max | 接触瞬间外力峰值(N) | CSV 记录 |
| 夹持力估计 | f_grip | 归一化夹持力(0~1)均值/峰值 | CSV 记录 |
| NASA-TLX | TLX | 6维度主观负荷评分(1-10) | 问卷 |
| 接触力建立时间 | T_contact | 从接触触发到稳定夹持的时间(s) | CSV 后处理 |

---

## 3. 三种对比模式

详细定义见 [`shared_control_node.py`](plans/shared_control_node.py) 和 [`teleop_shared_control_paper_plan.md`](plans/teleop_shared_control_paper_plan.md#L107-L111)。

| 特性 | 模式A (Baseline) | 模式B (固定增益) | 模式C (本文方法) |
|------|-----------------|-----------------|-----------------|
| 视觉语义 | ❌ 无YOLO | ✅ 有YOLO检测 | ✅ 有YOLO检测 |
| 力反馈 | 零力(透明模式) | 固定 K_trans=0.6 | 自适应 K_trans(c) |
| 导纳刚度 | 固定 K=200 N/m | 固定 K=200 N/m | 自适应 K(c) |
| 死区 | 无 | 固定 deadband=0.4N | 自适应 deadband(c) |
| 夹持力估计 | ✅ 有(仅监控) | ✅ 有(仅监控) | ✅ 有(接触脉冲) |

> **模式A** 对应纯位置遥操作（零力反馈），作为传统方法基线。
> **模式B** 对应有视觉辅助但无自适应控制的中间方案，用于消融分析。
> **模式C** 对应本文提出的完整方法。

---

## 4. 实验对象

基于 [`VisionPhysicsMapper`](biaoding/vision_physics_mapper.py#L99-L182) 内置表，选择以下在 COCO 数据集中可用且能实际获取的物体：

| 类别 | label | 导纳刚度 | K_trans | deadband | 实物示例 | 测试内容 |
|------|-------|---------|---------|---------|---------|---------|
| `apple` | soft | 50 N/m | 0.3 | 0.3 N | 真实苹果 | 软物体保护 |
| `banana` | soft | 50 N/m | 0.3 | 0.3 N | 真实香蕉 | 软物体保护 |
| `bottle` | medium | 150 N/m | 0.5 | 0.4 N | 塑料水瓶 | 中等硬度 |
| `book` | hard | 300 N/m | 1.0 | 0.5 N | 硬皮书 | 硬物体 |
| `cell phone` | hard | 300 N/m | 1.0 | 0.5 N | 手机模型 | 硬物体 |

---

## 5. 实验流程

### 5.1 实验准备

```
1. 启动硬件: Franka Panda + Omega.7 + RealSense D435i
2. 运行 Step 0: 硬件检查 + 基线遥操作 (确认所有硬件正常工作)
3. 操作员练习: 5分钟自由操作，熟悉 Omega.7 手柄
4. 随机化实验顺序: 使用拉丁方设计避免顺序效应
```

### 5.2 单次抓取流程

```
位置: 物体放置在桌面标记位置（距机械臂基底 0.4~0.6m）
操作员: 通过 Omega.7 控制机械臂

1. [0s]   操作员移动手柄，机械臂从初始位置出发
2. [~5s]  机械臂接近物体，YOLO 检测触发（模式B/C）
3. [~8s]  夹爪接触物体 → 夹持
4. [~10s] 提升物体至 10cm
5. [~15s] 移至 20cm 外托盘上方
6. [~18s] 释放物体到托盘
7. [~20s] 返回初始位置

判断标准:
  ✅ 成功: 物体被夹持、提起、移至托盘、释放，全程无掉落/破损
  ❌ 失败: 抓取掉落/夹持不稳/物体破损/操作超时(30s)
```

### 5.3 实验矩阵

每名操作员执行:

| 模式 | 物体 | 重复次数 |
|------|------|---------|
| A | apple | 5 |
| A | banana | 5 |
| A | bottle | 5 |
| A | book | 5 |
| A | cell phone | 5 |
| B | apple | 5 |
| B | banana | 5 |
| B | bottle | 5 |
| B | book | 5 |
| B | cell phone | 5 |
| C | apple | 5 |
| C | banana | 5 |
| C | bottle | 5 |
| C | book | 5 |
| C | cell phone | 5 |

> **总计**: 3 模式 × 5 物体 × 5 重复 = **75 次抓取/人**
> **每操作员预计耗时**: ~30分钟 (75次 × 20秒 + 中间换物体+休息)

### 5.4 随机化策略

使用**拉丁方**避免顺序效应:

```
操作员1: A→B→C  (每模式内物体顺序随机)
操作员2: B→C→A
操作员3: C→A→B
```

### 5.5 数据文件命名规则

```
data/experiment_{YYYYMMDD}_{HHMMSS}/
├── operator_{id}/                  # 操作员
│   ├── config.yaml                 # 操作员+实验配置
│   ├── trial_{n}_{mode}_{obj}.csv  # 单次抓取的时序数据
│   └── trial_{n}_{mode}_{obj}_meta.yaml  # 元数据(结果/耗时等)
├── summary.md                      # 汇总报告
├── results_table.csv               # 结果汇总表
└── plots/                          # 可视化
    ├── success_rate.png
    ├── completion_time.png
    ├── force_comparison.png
    ├── grip_comparison.png
    └── nasa_tlx.png
```

---

## 6. 评价指标详细定义

### 6.1 客观指标

| 指标 | 公式/定义 | 来源 |
|------|----------|------|
| 抓取成功率 SR | `成功次数 / 总次数 × 100%` | 人工标注 |
| 任务完成时间 TTC | 从首次移动至成功释放的时间(s) | 人工+时间戳 |
| 软物体破损率 DR | `破损次数 / 该类别总次数 × 100%` | 人工检查 |
| 峰值接触力 | `max(|F_ext|)` 在接触阶段 | CSV 数据分析 |
| 平均力反馈幅值 | `mean(|F_haptic|)` 全程均值 | CSV 数据分析 |
| 力反馈波动 | `std(|F_haptic|)` 反映触感平滑度 | CSV 数据分析 |
| 夹持力均值 | `mean(f_grip)` 夹持阶段均值 | CSV 数据分析 |

### 6.2 主观指标 — NASA-TLX 量表

使用 **NASA Task Load Index (NASA-TLX)** — 人机交互/遥操作领域最广泛使用的主观负荷评估工具 (Hart & Staveland, 1988; Hart, 2006)。

#### 问卷格式（论文标准版）

每维采用 **0-20 分制**（20 cm 线段），见 [`plans/nasa_tlx_template.md`](plans/nasa_tlx_template.md) 可打印版本。

| 维度 | 定义 | 低端(0) | 高端(20) |
|------|------|---------|---------|
| 脑力需求 (Mental Demand) | 任务对脑力/知觉/思考的要求 | 低 | 高 |
| 体力需求 (Physical Demand) | 任务对体力/推拉/移动的要求 | 低 | 高 |
| 时间需求 (Temporal Demand) | 任务节奏带来的时间紧迫感 | 慢/充裕 | 快/紧迫 |
| 努力程度 (Effort) | 完成任务所需付出的努力 | 小 | 大 |
| 任务表现 (Performance) | 自我感知的完成质量 | 好 | 差 |
| 挫败感 (Frustration) | 操作中的焦虑/压力/烦躁感 | 小 | 大 |

> **注意**: 维度 5 "任务表现" 与其他 5 维方向相反（越低越好），计分时需反向编码：`score = 20 - raw_score`。

#### 评分方法

| 方法 | 计算方式 | 论文引用 |
|------|---------|---------|
| **Raw TLX (RTLX)** | 6 维度算术平均 | Hart, 2006 — ⭐ 最推荐 |
| **加权 TLX** | 6 维度 × 权重 → 加权平均 | Hart & Staveland, 1988 |

> 推荐使用 **Raw TLX**，无需额外权重配对比较问卷，在论文中写为:
> "After each experimental condition, participants rated their perceived workload using the NASA Raw Task Load Index (RTLX; Hart, 2006) on a 0-20 scale."

#### 实验实施方式

| 时机 | 内容 | 说明 |
|------|------|------|
| 实验开始前 | 培训 + 基线练习 | 熟悉量表含义 |
| **每种模式全部完成后** | 1 份 NASA-TLX | 对比 A/B/C 三种模式，共 3 份/人 |

#### 配对比较权重（可选，用于加权 TLX）

若采用加权 TLX，需在实验后做 15 对两两比较：

```
请在每一对中选出对您工作负荷影响更大的因素：
1.  脑力需求  /  体力需求
2.  脑力需求  /  时间需求
3.  脑力需求  /  努力程度
4.  脑力需求  /  任务表现
5.  脑力需求  /  挫败感
6.  体力需求  /  时间需求
7.  体力需求  /  努力程度
8.  体力需求  /  任务表现
9.  体力需求  /  挫败感
10. 时间需求  /  努力程度
11. 时间需求  /  任务表现
12. 时间需求  /  挫败感
13. 努力程度  /  任务表现
14. 努力程度  /  挫败感
15. 任务表现  /  挫败感

各维度被选中次数 = 权重 (0-5)
```

---

## 7. 实验假设与统计检验

### 7.1 假设

| 编号 | 假设 | 预期结果 |
|------|------|---------|
| H1 | 模式C的抓取成功率显著高于模式A和B | SR_C > SR_A, SR_C > SR_B |
| H2 | 模式C的软物体破损率显著低于模式A和B | DR_C < DR_A, DR_C < DR_B |
| H3 | 模式C的NASA-TLX评分显著低于模式A | TLX_C < TLX_A |
| H4 | 模式C的接触力峰值显著低于模式A和B | F_peak_C < F_peak_B, F_peak_C < F_peak_A |

### 7.2 统计方法

| 数据类型 | 检验方法 | 备注 |
|---------|---------|------|
| 成功率(二项分布) | χ² 检验 / Fisher精确检验 | 比较3模式 |
| 完成时间(连续) | 单因素ANOVA + Tukey HSD | 比较3模式 |
| 破损率(二项分布) | Fisher精确检验 | 仅软物体 |
| NASA-TLX(有序) | Kruskal-Wallis + Dunn检验 | 非参数 |
| 力峰值(连续) | 单因素ANOVA | 需验证正态性 |

---

## 8. 数据分析流程

```
data/ 目录
    │
    ├── 1-parse.py          # 解析 CSV → 宽表格式
    ├── 2-summary.py        # 计算统计量 → summary.md
    ├── 3-plot.py           # 生成可视化 → plots/
    ├── 4-statistics.py     # 统计检验
    └── 5-report.py         # 生成实验报告 TeX/MD
```

### 输出报告内容

1. **成功率对比柱状图**（3模式 × 5物体，带误差棒）
2. **完成时间箱线图**（3模式对比）
3. **力反馈幅值对比**（时序叠加图）
4. **夹持力对比**（时序叠加图）
5. **NASA-TLX 雷达图**（6维度对比）
6. **统计检验结果表**

---

## 9. 实验进度追踪

| 阶段 | 内容 | 预计时间 | 状态 |
|------|------|---------|------|
| 1. 硬件检查 | Step 0 基线遥操作 | ~10min | 🔲 |
| 2. Step 1 | 力估计器在线验证 | ~10min | 🔲 |
| 3. Step 2 | 自适应导纳在线验证 | ~10min | 🔲 |
| 4. Step 3 | 夹持力估计在线验证 | ~10min | 🔲 |
| 5. Step 4 | 力反馈在线验证 | ~10min | 🔲 |
| 6. 实验采集 | 操作员1（模式顺序随机） | ~30min | 🔲 |
| 7. 实验采集 | 操作员2（模式顺序随机） | ~30min | 🔲 |
| 8. 实验采集 | 操作员3（模式顺序随机） | ~30min | 🔲 |
| 9. 数据分析 | 生成图表 + 统计检验 | ~60min | 🔲 |
| 10. 论文撰写 | 实验结果章节 | ~2h | 🔲 |

---

## 10. 实验命令速查

```bash
# Step 0: 硬件基线
python3 my_test/teleop_omega7_franka.py

# Step 1a: 力估计噪声测试
python3 plans/step_1a_force_noise.py

# Step 2b: 视觉触发测试
python3 plans/step_2b_visual_trigger.py --simulate

# Step 3a: 夹持力基线
python3 plans/step_3a_grip_baseline.py

# 单次模式测试
python3 plans/shared_control_node.py --mode a
python3 plans/shared_control_node.py --mode b
python3 plans/shared_control_node.py --mode c

# 运行实验运行器
python3 plans/experiment_runner.py --operator 1 --mode a --trials 5
python3 plans/experiment_runner.py --mode all --operator 1 --trials 5
```

---

## 11. 与现有 `experiment_runner.py` 的差异

现有的 [`plans/experiment_runner.py`](plans/experiment_runner.py) 存在以下问题，新版将修复：

| 问题 | 现有方案 | 改进方案 |
|------|---------|---------|
| 对象列表不一致 | 使用 `cup`, `clock` 等不支持的类别 | 与 `vision_physics_mapper.py` 保持一致 |
| 缺乏重复试验设计 | 仅1次/组合 | 每组合 5 次重复 |
| 缺乏操作员管理 | 无 | 支持多操作员 ID |
| 数据解析脆弱 | 依赖 stdout 文本解析 | 独立 CSV 逐帧记录 + 独立元数据 |
| 缺乏随机化 | 固定顺序 | 拉丁方 + 物体内随机 |
| 缺乏失败记录 | 仅记录成功数据 | 记录成功/失败/破损状态 |
| 无可视化 | 仅有文本总结 | 生成统计图表 |
| 无统计检验 | 无 | 集成 ANOVA/χ² 检验 |
