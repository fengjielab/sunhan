# paper2_sci 当前文件索引

## 当前论文唯一完整版本

**所有当前投稿材料统一位于：**

`21_framework_first_submission_bundle/`

该目录是目前唯一应继续查看、修改、复核和交接的论文版本，包含：

- framework-first 英文主稿；
- 较早的中文审阅稿（尚未与英文稿同步，不能用于投稿）；
- Supplementary Material；
- Figures 1–7 的 PNG、PDF 和 SVG；
- figure source data 与作图代码；
- clean 派生数据、统计结果和 fidelity outputs；
- clean/fidelity/figure/manuscript QA；
- 投稿前待补信息和 manuscript-readiness audit；
- `interactive_teleop.py` 采集代码快照；
- 全包 SHA-256 manifest。

## 新增前瞻性 K_fb 可行性预试

`23_kfb_timing_pilot/` 是独立于存档 `n=5` 数据的新实验执行包。现场仍以
`F:\sun\sunhan\my_test\interactive_teleop.py --mode kfb_timing` 为入口；该目录
保存冻结顺序、私有oracle、执行说明和工程/志愿者检查表。当前状态仅为软件实现
完成，尚未运行实体机器人验收或人体采集，不能写成已有前瞻性结果。

入口文件：

- `21_framework_first_submission_bundle/README.md`
- `21_framework_first_submission_bundle/18_manuscript_v1/manuscript_v1_en.md`
- `21_framework_first_submission_bundle/20_submission_package/MANUSCRIPT_READINESS_AUDIT.md`
- `21_framework_first_submission_bundle/20_submission_package/SUBMISSION_REQUIRED_INFORMATION.md`

## 从原始 acquisition 重新构建时仍需保留的证据链

完整投稿包可以独立复核 clean 结果并重新生成全部图，但没有重复打包原始人体实验 acquisition。若要从原始 acquisition 重新运行 `clean_analysis.py`，仍需：

- 原始只读 acquisition：`F:\sun\sunhan\my_test\data\ral_date`
- `02_audit/`：186-record source manifest 与 lineage audit 输入
- `03_processed_data/`：旧 trial metrics，仅用于 clean rebuild/historical comparison
- `03_clean_analysis/`：工作区中的原始 clean-analysis 输出与脚本

不要删除或改写这些路径，除非先修改并验证脚本中的路径依赖。

## 顶层目录分类

### A. 当前投稿版本

- `21_framework_first_submission_bundle/`：唯一当前论文包。

### B. 原始/重建证据链，暂时保留

- `02_audit/`
- `03_processed_data/`
- `03_clean_analysis/`
- 工作区外的 `F:\sun\sunhan\my_test\data\ral_date`

### C. 大型数据副本，删除前必须单独核验

- `01_primary_first_attempt_data/`：约 240.54 MB。
- `01_selected_data/`：约 240.28 MB，属于旧 selection 副本。

它们不在当前投稿包内，也不是当前主稿的直接读取位置；但在逐文件确认与原始 `ral_date` 一致之前，不自动删除。

### D. 历史分析、旧论文方向和分章节中间稿

以下目录已经统一移动至 `90_legacy_archive/`，没有删除：

- `04_statistics/`
- `05_figures/`
- `06_manuscript/`
- `07_supplement_experiment/`
- `08_timing_compensation/`
- `09_latency_aware_paper/`
- `10_confirmatory_experiment/`
- `11_existing_data_paper_blueprint/`
- `12_results_writing/`
- `13_methods_writing/`
- `14_discussion_writing/`
- `15_introduction_related_work/`
- `16_conclusion_writing/`
- `17_abstract_writing/`

### E. 已复制进完整投稿包的原工作区源目录

以下内容已经复制进 `21_framework_first_submission_bundle/`；原工作副本已移动至 `90_legacy_archive/`：

- `18_manuscript_v1/`
- `19_publication_figures/`
- `20_submission_package/`

后续只修改 bundle 内文件。`90_legacy_archive/` 中的副本仅用于历史追溯。

### F. 历史归档

- `90_legacy_archive/`：约 58.28 MB，包含 04–20 阶段的旧分析、旧论文方向、分章节中间稿、原工作副本和旧 `analysis_summary.json`。该目录可以恢复，但不是当前论文入口。

## 当前验证状态

- Clean QA：38/38 PASS
- Fidelity QA：30/30 PASS
- Manuscript QA：44/44 PASS
- Figures 1–7：已在 bundle 内完整重建
- Bundle SHA-256：PASS

## 仍未完成的投稿事项

伦理/知情同意、作者和单位、funding、conflict of interest、author contributions、数据/代码仓库 DOI 或稳定链接，以及目标期刊格式仍需补充。详见 bundle 内 `SUBMISSION_REQUIRED_INFORMATION.md`。
