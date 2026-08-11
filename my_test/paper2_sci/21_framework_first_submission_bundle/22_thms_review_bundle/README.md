# THMS 稿件审阅包

整理日期：2026-08-11

本目录汇总当前 THMS 方法框架优先版本，只包含本轮需要审阅和继续投稿准备的有效文件，不包含旧图与中间稿。

## 目录入口

- `01_manuscript/manuscript_thms_v1_zh.md`：当前中文主稿，正文图链接已改为本审阅包内的相对路径。
- `02_main_figures/`：正文图 1–4，每图均含 PDF、SVG 和 600 dpi PNG。
- `03_supplement/`：补充材料正文及图 S1–S3，每图均含 PDF、SVG 和 600 dpi PNG。
- `04_logic_and_qa/`：逻辑追踪表、可容许解释映射、稿件 QA 报告、就绪审计及投稿待补信息。
- `05_reproduction/figure_scripts/`：当前出图脚本。
- `05_reproduction/figure_source_data/`：冻结的出图源数据快照。
- `05_reproduction/qa/`：复现说明、依赖、清单及 QA 脚本/结果。

## 当前状态

- 中文稿 QA：52/52 项通过。
- 正文采用 4 张主图；解释映射保留为表 III；窗口敏感性和背景/稳定性材料放入补充材料。
- 图件已经输出为 PDF、SVG 和高分辨率 PNG。
- 本目录是便于审阅和交付的整理快照；原始项目文件没有移动或删除。

## 使用说明

审稿内容核对从 `01_manuscript/manuscript_thms_v1_zh.md` 开始。需要修改图片时，先使用 `05_reproduction/figure_scripts/` 中的脚本在原项目结构中重新生成，再同步更新本审阅包。部分脚本仍依赖原项目的清洗数据目录，因此本目录不等同于完全独立的原始数据复现包。
