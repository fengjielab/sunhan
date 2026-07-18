# Mechatronics v4 数据与复现归档

本目录只锁定 `Mechatronics_full_English_language_refined_v4.md` 实际引用或用于复核的去标识化数据、结果表和分析代码快照；未把旧版视觉结果混入其中。

## 目录说明

- `01_frozen_tables/all_trials_135.csv`：135 条冻结试验记录；除时长和主端轨迹长度外，已从 S1 合并 `matched_block_id`、`outcome` 和 `outcome_source`。同目录的 `all_trials_135_objective_only_original.csv` 保留合并前的客观指标原表。
- `02_objective_trial_sources/`：CSV 的 135 个 `source_file` 所指向的原始 JSON 汇总文件，保留原相对路径。
- `02_raw_trajectory_csv/`：与 135 条冻结记录一一对应的原始 master-trajectory CSV（`time,x,y,z,...`），保留 soft/medium/hard 的原相对路径。
- `03_outcome_registry/`：完整的 27-block / 135-trial Supplementary Table S1（Markdown 和 XLSX）。这是当前可用的成功/失败登记来源；`all_trials_135.csv` 本身没有 outcome 列。
- `04_nasa_tlx/`：Raw NASA-TLX 的输入和汇总文件。
- `05_vision_validation_final_48_19ms/`：冻结的 180-image 视觉验证数据、汇总结果和图像。`results/vision_validation_per_image.csv` 的平均推理时间为 48.192906 ms，对应正文的 48.19 ms。
- `06_cycle_timing/`：现有的控制周期日志与原说明文件。
- `07_analysis_and_figure_code/`：统计、bootstrap 和 Fig. 4--7 的代码快照。
- `08_manuscript_snapshot/`：本次审核所对应的文稿快照。

## 已验证的复现结果

`bootstrap_ci_ce.py` 固定 `random.seed(42)` 和 `np.random.seed(42)`，对 27 个 matched blocks 重抽样 10,000 次，得到：

| 指标 | 未舍入的 95% percentile bootstrap CI | 正文显示值 |
|:--|--:|--:|
| 完成时间 E-C (s) | [1.104, 2.508] | [1.10, 2.51] |
| 轨迹长度 E-C (m) | [-0.0142, 0.0591] | [-0.014, 0.059] |

`all_trials_135.csv` 中的 27 个 block 由 `operator + object_attr + group_num` 确定，每一 block 均具有 A--E 五个模式。S1 的 135 个时长/轨迹条目均能唯一匹配到该冻结 CSV（分别按 0.01 s 和 0.001 m 的展示精度）；S1 成功数为 A=22、B=21、C=26、D=24、E=24，与 Fig. 5 的硬编码计数相同。

## 已知限制与处理原则

- v4 文稿只写了 S1 标题，未嵌入其 27 行数据；完整 S1 已在本目录 `03_outcome_registry` 保留，投稿时应作为补充文件随稿提交或嵌入。
- 成功/失败已从 S1 合并到 `all_trials_135.csv`；其来源是人工登记的 S1，而非原始 JSON 的机读状态字段。后续采集仍应直接记录 `outcome`（及失败类型）。
- 原始逐采样轨迹 CSV 已归档，且 `complete_checklist_analysis.py` 等历史分析脚本也已保留。它们证明 pause count 的输入数据存在；但以这些脚本中公开的逐差分速度阈值规则直接重算，尚不能得到正文的 C=2.74 ± 1.23、E=3.41 ± 1.67。因此，pause 的原始数据可追溯，最终计算版本/平滑规则仍需确认。
- `control_loop_profile_vision.csv` 的中位数可复算为 5.072 ms，但它来自 mock profiling，且现有说明文件宣称的 591,554 cycles 与目录内两份 CSV 共 44,475 行不一致。该数值未用于当前 v4 文稿；原始日志仍保留在归档中，供后续独立性能测试使用。
- 工作区还存在另一个视觉结果副本，其平均时间为 50.081239 ms。它未被放入本归档；不要以模糊的同名文件替换本目录中的 48.19-ms 版本。
- Fig. 5(a) 绘图代码没有画 Holm 显著性括号/星号；Fig. 6 代码没有显示 p 值或 bootstrap CI。正文的统计报告存在，但这两项属于图内信息呈现待补，而不是已发现的统计数值错误。

## 核验方式

从本目录运行 `python verify_bundle.py` 可检查关键文件哈希、记录数、S1--CSV 数值映射、bootstrap CI、视觉均值和 cycle-time 中位数。该脚本不会修改任何数据。
