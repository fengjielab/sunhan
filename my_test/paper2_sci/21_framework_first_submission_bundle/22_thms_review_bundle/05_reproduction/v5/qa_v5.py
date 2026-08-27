from __future__ import annotations

import json
import re
from pathlib import Path

from PIL import Image


HERE = Path(__file__).resolve().parent
BUNDLE = HERE.parents[1]
MANUSCRIPT = BUNDLE / "01_manuscript" / "manuscript_thms_v5_zh.md"
SUPPLEMENT = BUNDLE / "03_supplement" / "supplementary_material_v5.md"
FIGURES = BUNDLE / "02_main_figures" / "v5"
LOGIC = BUNDLE / "04_logic_and_qa" / "v5"


def main() -> None:
    manuscript = MANUSCRIPT.read_text(encoding="utf-8")
    supplement = SUPPLEMENT.read_text(encoding="utf-8")
    validation = json.loads((LOGIC / "v5_validation_report.json").read_text(encoding="utf-8"))
    figure_qa = json.loads((LOGIC / "v5_figure_qa.json").read_text(encoding="utf-8"))
    checks = []

    def check(name: str, passed: bool, observed=None, expected=None):
        checks.append({"check": name, "passed": int(bool(passed)), "observed": observed, "expected": expected})

    check("v5 validation PASS", validation["status"] == "PASS", validation["status"], "PASS")
    check("v5 figure QA PASS", figure_qa["status"] == "PASS", figure_qa["status"], "PASS")

    sections = [
        "# 1. 引言", "# 2. 相关工作", "# 3. 实际干预保真度框架",
        "# 4. 存档人机实验与重建方法", "# 5. 结果", "# 6. 讨论", "# 7. 结论", "# 参考文献",
    ]
    positions = [manuscript.find(value) for value in sections]
    check("seven-section THMS order", all(value >= 0 for value in positions) and positions == sorted(positions), positions, "strictly increasing")
    check("Fig. 1 appears before Related Work", manuscript.find("Fig01_human_machine_fidelity_framework_v5.png") < manuscript.find("# 2. 相关工作"), manuscript.find("Fig01_human_machine_fidelity_framework_v5.png"), f"<{manuscript.find('# 2. 相关工作')}")

    tables = [
        "**表I. 存档实验条件及待核实的操作者经历。**",
        "**表II. 证据情形与允许的科学解释。**",
        "**表III. 实际干预保真度与存档条件的可支持比较身份。**",
    ]
    table_positions = [manuscript.find(value) for value in tables]
    check("Table I–III linked and ordered", all(value >= 0 for value in table_positions) and table_positions == sorted(table_positions), table_positions, "strictly increasing")

    figure_stems = [
        "Fig01_human_machine_fidelity_framework_v5",
        "Fig02_system_experiment_v5",
        "Fig03_realized_intervention_fidelity_v5",
        "Fig04_EA_outcome_robustness_v5",
    ]
    for stem in figure_stems:
        check(f"{stem} linked", f"{stem}.png" in manuscript, f"{stem}.png" in manuscript, True)
        for suffix in ("png", "svg", "pdf"):
            path = FIGURES / f"{stem}.{suffix}"
            check(f"{path.name} nonempty", path.exists() and path.stat().st_size > 1000, path.stat().st_size if path.exists() else 0, ">1000")
        png = FIGURES / f"{stem}.png"
        if png.exists():
            with Image.open(png) as image:
                check(f"{stem} readable dimensions", image.width >= 2400 and image.height >= 1600, [image.width, image.height], ">=2400x1600")

    required = [
        "R_i(t)\\rightarrow H_i(t+\\delta)\\rightarrow R_i(t+\\delta)\\rightarrow Y_i",
        "RQ1（可重建性）", "RQ2（实际断点）", "RQ3（比较身份）",
        "Omega.7", "Franka Panda", "12,196", "43/45", "3/45",
        "39次完全、2次部分和4次零视觉配置暴露", "−0.3489 N·s",
        "64/64", "[ETHICS RECORD REQUIRED—DO NOT SUBMIT]",
        "结构化作者审计", "不构成单独视觉、刚度或力成分的确认性因果证据",
    ]
    for phrase in required:
        check(f"required manuscript statement: {phrase}", phrase in manuscript, phrase in manuscript, True)

    methods = manuscript.split("# 4. 存档人机实验与重建方法", 1)[1].split("# 5. 结果", 1)[0]
    leaked = [value for value in ("43/45", "3/45", "39次完全", "时钟域错配") if value in methods]
    check("no case findings leaked into Methods", not leaked, leaked, [])

    abstract = manuscript.split("## 摘要", 1)[1].split("**关键词：", 1)[0]
    check("abstract omits 64-combination result", "64/64" not in abstract and "2^6" not in abstract, ["64/64" in abstract, "2^6" in abstract], [False, False])
    check("abstract puts rule verification after case findings", abstract.find("12个冻结") > abstract.find("43/45"), [abstract.find("12个冻结"), abstract.find("43/45")], "12-case statement later")

    fig03_svg = (FIGURES / "Fig03_realized_intervention_fidelity_v5.svg").read_text(encoding="utf-8")
    check("Fig. 3 states incomplete F replay", "C→R replay unavailable" in fig03_svg, "C→R replay unavailable" in fig03_svg, True)

    forbidden = [
        "视觉显著提高了安全性", "我们的控制器优于", "首个通用框架", "框架已经得到外部验证",
        "180名参与者", "180个独立人体样本", "单独视觉效应得到证明",
    ]
    for phrase in forbidden:
        check(f"forbidden claim absent: {phrase}", phrase not in manuscript, phrase in manuscript, False)

    reference_count = len(re.findall(r"(?m)^\d+\. ", manuscript.split("# 参考文献", 1)[1]))
    check("31 numbered references", reference_count == 31, reference_count, 31)
    check("v5 supplement preserves full controlled cases", all(f"S{i:02d}" in supplement for i in range(12)), True, True)
    check("v5 supplement links frozen v4 data", "v4_data/controlled_artifact_case_results.csv" in supplement, True, True)
    check("scientific interfaces unchanged", validation["scientific_interface_change"] == "none", validation["scientific_interface_change"], "none")

    report = {
        "status": "PASS" if all(item["passed"] for item in checks) else "FAIL",
        "n_checks": len(checks),
        "n_passed": sum(item["passed"] for item in checks),
        "checks": checks,
    }
    (LOGIC / "v5_manuscript_qa.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "n_checks": report["n_checks"], "n_passed": report["n_passed"]}, ensure_ascii=False, indent=2))
    if report["status"] != "PASS":
        failed = [item for item in checks if not item["passed"]]
        raise SystemExit(json.dumps(failed, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
