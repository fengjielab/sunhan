# 先验可信度补充实验执行包

本目录用于验证第二篇论文新增的核心机制：视觉先验被施加后，机器人依据接触风险在线降低先验可信度，并将刚度从视觉先验有界地回退到安全锚点。它不是材料重分类，也不宣称完整闭环稳定性。

## 四个条件

| 条件 | 先验 | 接触后可信度修正 | 用途 |
|---|---|---:|---|
| C0 | 正确 | 关闭 | 正确先验基线 |
| C1 | 正确 | 开启 | 检查修正器是否过度干预 |
| W0 | 故意过硬（200 N/m） | 关闭 | 错误先验反事实基线 |
| W1 | 故意过硬（200 N/m） | 开启 | 检验闭环纠错收益 |

真实物体为 apple 和 paper cup（命令行写作 `cup`）。正确先验分别为 50 和 120 N/m；安全锚点为 50 N/m。四条件均保留原始视觉识别结果，但该结果只用于端到端识别审计，不改变受控施加的先验。

## 执行顺序

1. 先由不进入正式样本的实验人员执行 `pilot_schedule_8.csv`。
2. 只有全部通过 `pilot_acceptance_checklist.md`，才冻结参数并开始正式实验。
3. 正式实验严格按 `formal_schedule_80.csv` 执行：10 人 × 2 物体 × 4 条件，每人 8 次。
4. 每次运行后立即填写 `trial_outcomes_80_template.csv`。任何失败保留原文件；补测另建 trial_id，并在 `retest_trial_id` 中关联，不能覆盖首测。
5. 不采集 NASA-TLX。本实验的人因变量限于客观操作时间、轨迹、速度波动、失败阶段和学习/顺序效应；背景变量填入 `participant_background_10_template.csv`。

正式开始前阅读 `sample_size_decision.md`：10人只能检出较大的被试内交互；若要扩充到15–20人，应在查看正式条件效应之前决定。

## 主要统计问题

主要终点为接触后 0.05–0.80 s 的基线校正超阈值力冲量。主要机制对比是：

`(W1 − W0) − (C1 − C0)`

若 W1 显著降低错误先验下的接触风险，而 C1 相对 C0 没有同等幅度的代价，才能把“先验可信度闭环纠错”写为主要创新。成功率按所有首测进行端到端分析，补测只进入敏感性分析。

## 代码入口

命令已写入两个顺序表。例如：

```bash
python3 my_test/interactive_teleop.py --mode W1 --actual-object apple --subject-id P01 --object-id apple --trial-id P01_01_apple_W1 --trajectory-dir data/trust_correction/P01
```

重新生成顺序表：

```bash
python3 my_test/generate_trust_experiment_schedule.py
```

单条预试完成后自动验收：

```bash
python3 my_test/validate_trust_trial.py data/trust_correction/PILOT/trust_experiment_YYYYMMDD_HHMMSS.csv
```

正式数据收齐后生成试次指标和预定义对比：

```bash
python3 my_test/trust_experiment_analysis.py --data-dir data/trust_correction
```
