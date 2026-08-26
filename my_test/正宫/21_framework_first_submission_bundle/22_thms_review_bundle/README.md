# THMS 稿件审阅包

整理日期：2026-08-12

本目录汇总当前 THMS 人机闭环导向版本，并保留旧稿和既有图件用于版本追踪。

## 目录入口

- `01_manuscript/manuscript_thms_v5_1_zh.md`：当前中文精修稿；收紧主观经历边界并优化结果连续性。
- `01_manuscript/manuscript_thms_v5_zh.md`：上一版人机闭环结构稿，完整保留用于版本追踪。
- `01_manuscript/manuscript_thms_v4_zh.md`：工件证据接口稿，连同现有人工改动完整保留。
- `02_main_figures/`：正文图 1–4，每图均含 PDF、SVG 和 600 dpi PNG。
- `03_supplement/`：补充材料正文及图 S1–S3，每图均含 PDF、SVG 和 600 dpi PNG。
- `04_logic_and_qa/`：逻辑追踪表、可容许解释映射、稿件 QA 报告、就绪审计及投稿待补信息。
- `05_reproduction/figure_scripts/`：当前出图脚本。
- `05_reproduction/figure_source_data/`：冻结的出图源数据快照。
- `05_reproduction/components/`：主图合成前的独立过程证据组件（PDF、SVG、600 dpi PNG）。
- `05_reproduction/qa/`：复现说明、依赖、清单及 QA 脚本/结果。
- `05_reproduction/v3/`：v3 证据状态判定器、冻结 oracle、64组合枚举与版本不变性检查。
- `05_reproduction/v4/`：v4 工件证据接口、结构化语义审计、12案例规则级核验、真实案例状态重建及综合 QA。
- `05_reproduction/v5/`：v5 基线保护、四张主图生成、冻结证据复算和正文/图件综合 QA。
- `05_reproduction/v5_1/`：v5.1概念边界精修、v5基线保护、版本化出图和专项措辞/顺序QA。

## 当前状态

- v5.1复跑冻结证据链：12/12 oracle、180/180溯源、G的12,196个重放更新及E/F暴露状态均通过。
- v5.1不覆盖v5；受保护的v5主稿、核心脚本和12个图件哈希全部一致。
- v5.1正文与图件QA：58/58项通过；四张主图均提供PDF、SVG和600 dpi PNG。
- 正文采用4张职责分离的主图：人机闭环/证据链、真实系统/实验流程、实际时序/暴露、E–A参与者结果/记录选择稳健性。
- 图件已经输出为 PDF、SVG 和高分辨率 PNG。
- 本目录是便于审阅和交付的整理快照；原始项目文件没有移动或删除。

## 使用说明

当前修改稿从 `01_manuscript/manuscript_thms_v5_1_zh.md` 开始；v1–v5保留用于版本追踪。依次运行 `05_reproduction/v5_1/validate_v5_1.py`、`generate_v5_1_figures.py` 和 `qa_v5_1.py` 可复算冻结证据、生成图件并执行综合检查。部分脚本仍依赖原项目的冻结清洗数据目录，因此本目录不等同于完全独立的原始数据复现包。
