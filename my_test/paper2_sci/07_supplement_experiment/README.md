# 先验可信度补充实验执行包

本目录用于验证第二篇论文新增的核心机制：视觉先验被施加后，机器人依据接触风险在线降低先验可信度，并将刚度从视觉先验有界地回退到安全锚点。它不是材料重分类，也不宣称完整闭环稳定性。

## 四个条件

| 条件 | 先验 | 接触后可信度修正 | 用途 |
|---|---|---:|---|
| C0 | 正确 | 关闭 | 正确先验基线 |
| C1 | 正确 | 开启 | 检查修正器是否过度干预 |
| W0 | 故意过硬（200 N/m） | 关闭 | 错误先验反事实基线 |
| W1 | 故意过硬（200 N/m） | 开启 | 检验闭环纠错收益 |

实验对象为标准化仿制香蕉（`banana`）和限制状态水瓶（`bottle`）。正确先验暂定分别为50和120 N/m；夹爪力暂定分别为8和15 N；安全锚点为50 N/m。参数须经8次预试确认后一次性冻结。四条件均保留原始视觉识别结果，但该结果只用于端到端识别审计，不改变受控施加的先验。

## 执行顺序

1. 先由不进入正式样本的实验人员执行 `pilot_schedule_8.csv`。当前第二轮预试统一写入 `data/trust_correction/PILOT_V2`，旧 `PILOT` 数据只作诊断，不覆盖也不进入正式统计。
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
python3 my_test/interactive_teleop.py --mode W1 --actual-object banana --subject-id P01 --object-id banana --trial-id P01_01_banana_W1 --trajectory-dir data/trust_correction/P01
```

重新生成顺序表：

```bash
python3 my_test/generate_trust_experiment_schedule.py
```

单条预试完成后自动验收：

```bash
python3 my_test/validate_trust_trial.py data/trust_correction/PILOT_V2/trust_experiment_YYYYMMDD_HHMMSS.csv
```

若8次预试出现控制长尾，先单独执行一次 `TIMING_DIAG`，不要立即开始12次水瓶诊断：

```bash
python3 my_test/interactive_teleop.py --mode C0 --actual-object bottle --subject-id TIMING_DIAG --object-id bottle --trial-id TIMING_DIAG_01_bottle_C0 --trajectory-dir data/trust_correction/TIMING_DIAG
python3 my_test/analyze_control_timing.py data/trust_correction/TIMING_DIAG
```

定位并解决控制长尾后，如果水瓶C1过度修正或W1收益方向仍不稳定，再按
`bottle_diagnostic_schedule_12.csv` 完成4条件×3重复的诊断数据；保存目录为
`data/trust_correction/BOTTLE_DIAG`，不得并入正式统计。新版CSV包含逐模块控制耗时，
收齐后运行：

```bash
python3 my_test/analyze_control_timing.py data/trust_correction/BOTTLE_DIAG
```

正式数据收齐后生成试次指标和预定义对比：

```bash
python3 my_test/trust_experiment_analysis.py --data-dir data/trust_correction
```
