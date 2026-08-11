# 统计工作簿运行时说明

本次环境未提供电子表格技能要求的 `load_workspace_dependencies`，且 Node 运行时无法导入 `@oai/artifact-tool`。依据电子表格交付规范，本次没有使用 `openpyxl`、`xlsxwriter`、LibreOffice 自动化或其他替代工具伪造 `.xlsx`。

所有计划中的工作表内容已分别输出为可审计 CSV：

- README：见本说明与项目根目录 `README.md`；
- Trial Manifest：`../02_audit/trial_manifest_180.csv`；
- Trial Metrics：`../03_processed_data/trial_metrics_main_180.csv`；
- Model Results：`mixed_effects_primary.csv` 与 `predefined_contrasts_all_metrics.csv`；
- Sensitivity：当前数据已清理为平衡的 180 个唯一试次，见 `sensitivity_results.csv`；
- Figure Data：`figure_data_trial_level.csv` 与 `figure_data_aligned_curves.csv`。

这些 CSV 是后续生成工作簿时的唯一数据源，不需要重新计算或改写结果。
