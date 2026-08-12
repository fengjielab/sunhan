# THMS 稿件审阅包

整理日期：2026-08-12

本目录汇总当前 THMS 方法框架优先版本，并保留旧稿和既有图件用于版本追踪。

## 目录入口

- `01_manuscript/manuscript_thms_v4_zh.md`：当前中文主稿；补齐原始工件→证据状态→解释约束两级闭环。
- `01_manuscript/manuscript_thms_v3_zh.md`：上一版方法强化稿，保留用于版本追踪。
- `02_main_figures/`：正文图 1–4，每图均含 PDF、SVG 和 600 dpi PNG。
- `03_supplement/`：补充材料正文及图 S1–S3，每图均含 PDF、SVG 和 600 dpi PNG。
- `04_logic_and_qa/`：逻辑追踪表、可容许解释映射、稿件 QA 报告、就绪审计及投稿待补信息。
- `05_reproduction/figure_scripts/`：当前出图脚本。
- `05_reproduction/figure_source_data/`：冻结的出图源数据快照。
- `05_reproduction/components/`：主图合成前的独立过程证据组件（PDF、SVG、600 dpi PNG）。
- `05_reproduction/qa/`：复现说明、依赖、清单及 QA 脚本/结果。
- `05_reproduction/v3/`：v3 证据状态判定器、冻结 oracle、64组合枚举与版本不变性检查。
- `05_reproduction/v4/`：v4 工件证据接口、结构化语义审计、12案例规则级核验、真实案例状态重建及综合 QA。

## 当前状态

- v4 规则级实现核验：12/12 oracle 完全匹配；记录选择稳健性继续保持64/64组合完整且唯一。
- v4 不覆盖 v1–v3；新图1和图4使用 `02_main_figures/v4/` 中的版本化文件。
- 冻结数值与图形 QA：通过；新增图 2 过程证据专项 QA 为 5/5 项通过。
- 正文采用 4 张主图；图 2 并置真实实验照片与日志重建的连续过程证据，图 4 将解释边界与主要参与者结果合并；窗口敏感性和稳定性材料放入补充材料。
- 图件已经输出为 PDF、SVG 和高分辨率 PNG。
- 本目录是便于审阅和交付的整理快照；原始项目文件没有移动或删除。

## 使用说明

当前修改稿从 `01_manuscript/manuscript_thms_v4_zh.md` 开始；v1–v3保留用于版本追踪。v4验证从 `05_reproduction/v4/validate_v4.py` 运行，新图从 `generate_v4_figures.py` 生成。部分脚本仍依赖原项目的冻结清洗数据目录，因此本目录不等同于完全独立的原始数据复现包。
