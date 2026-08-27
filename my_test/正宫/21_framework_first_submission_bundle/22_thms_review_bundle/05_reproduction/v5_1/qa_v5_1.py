from __future__ import annotations

import json
import re
from pathlib import Path

from PIL import Image


HERE = Path(__file__).resolve().parent
BUNDLE = HERE.parents[1]
MANUSCRIPT = BUNDLE / "01_manuscript" / "manuscript_thms_v5_1_zh.md"
SUPPLEMENT = BUNDLE / "03_supplement" / "supplementary_material_v5.md"
FIGURES = BUNDLE / "02_main_figures" / "v5_1"
LOGIC = BUNDLE / "04_logic_and_qa" / "v5_1"


def main() -> None:
    manuscript = MANUSCRIPT.read_text(encoding="utf-8")
    supplement = SUPPLEMENT.read_text(encoding="utf-8")
    validation = json.loads((LOGIC / "v5_1_validation_report.json").read_text(encoding="utf-8"))
    figure_qa = json.loads((LOGIC / "v5_1_figure_qa.json").read_text(encoding="utf-8"))
    checks = []

    def check(name: str, passed: bool, observed=None, expected=None):
        checks.append({"check": name, "passed": int(bool(passed)), "observed": observed, "expected": expected})

    check("v5.1 validation PASS", validation["status"] == "PASS", validation["status"], "PASS")
    check("v5.1 figure QA PASS", figure_qa["status"] == "PASS", figure_qa["status"], "PASS")
    check("exact Chinese title", manuscript.startswith("# 从名义条件到实际干预：异步人机实验的保真度框架"), manuscript.splitlines()[0], "frozen v5.1 title")
    check("exact English title", "*From Nominal Conditions to Realized Interventions: A Fidelity Framework for Asynchronous Human–Machine Experiments*" in manuscript, True, True)

    sections = [
        "# 1. 引言", "# 2. 相关工作", "# 3. 实际干预保真度框架",
        "# 4. 存档人机实验与重建方法", "# 5. 结果", "# 6. 讨论", "# 7. 结论", "# 参考文献",
    ]
    positions = [manuscript.find(value) for value in sections]
    check("seven-section order unchanged", all(value >= 0 for value in positions) and positions == sorted(positions), positions, "strictly increasing")
    check("Fig. 1 remains in Introduction", manuscript.find("Fig01_human_machine_fidelity_framework_v5_1.png") < manuscript.find("# 2. 相关工作"), True, True)

    tables = [
        "**表I. 存档实验条件及待核实的操作者侧暴露。**",
        "**表II. 证据情形与允许的科学解释。**",
        "**表III. 实际干预保真度与存档条件的可支持比较身份。**",
    ]
    table_positions = [manuscript.find(value) for value in tables]
    check("Table I–III retained and ordered", all(value >= 0 for value in table_positions) and table_positions == sorted(table_positions), table_positions, "strictly increasing")

    figure_stems = [
        "Fig01_human_machine_fidelity_framework_v5_1",
        "Fig02_system_experiment_v5_1",
        "Fig03_realized_intervention_fidelity_v5_1",
        "Fig04_EA_outcome_robustness_v5_1",
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
        "闭环中实际交付和暴露了什么干预",
        "试次级干预交付及窗口暴露并非主要评价对象",
        "在人机闭环内测得的操作性接触结局",
        "## 5.3 保留比较下的探索性结局模式",
        "## 5.4 规则级内部核验",
        "12,196", "43/45", "3/45", "39次完全、2次部分和4次零视觉配置暴露",
        "−0.3489 N·s", "64/64", "[ETHICS RECORD REQUIRED—DO NOT SUBMIT]",
    ]
    for phrase in required:
        check(f"required statement: {phrase}", phrase in manuscript, phrase in manuscript, True)

    forbidden = [
        "操作者实际经历", "人实际经历", "进入了操作者的经历", "实际经历了什么",
        "操作性人机交互指标", "通常把已分配条件视为已经交付",
        "operator-experienced", "视觉显著提高了安全性", "180名参与者",
    ]
    for phrase in forbidden:
        check(f"forbidden wording absent: {phrase}", phrase.lower() not in manuscript.lower(), phrase.lower() in manuscript.lower(), False)

    methods = manuscript.split("# 4. 存档人机实验与重建方法", 1)[1].split("# 5. 结果", 1)[0]
    leaked = [value for value in ("43/45", "3/45", "39次完全", "时钟域错配") if value in methods]
    check("Methods remains free of case findings", not leaked, leaked, [])

    abstract = manuscript.split("## 摘要", 1)[1].split("**关键词：", 1)[0]
    check("abstract omits controlled cases and oracle", all(value not in abstract.lower() for value in ("12个冻结", "12/12", "oracle")), [value for value in ("12个冻结", "12/12", "oracle") if value in abstract.lower()], [])
    check("abstract omits 64-combination result", "64/64" not in abstract and "2^6" not in abstract, True, True)

    results = manuscript.split("# 5. 结果", 1)[1].split("# 6. 讨论", 1)[0]
    check("retained outcome precedes internal verification", results.find("## 5.3 保留比较") < results.find("## 5.4 规则级"), [results.find("## 5.3 保留比较"), results.find("## 5.4 规则级")], "outcome first")

    fig01_svg = (FIGURES / "Fig01_human_machine_fidelity_framework_v5_1.svg").read_text(encoding="utf-8")
    fig03_svg = (FIGURES / "Fig03_realized_intervention_fidelity_v5_1.svg").read_text(encoding="utf-8")
    check("Fig. 1 removes operator-experienced", "operator-experienced" not in fig01_svg.lower(), False, False)
    check("Fig. 1 states delivery and exposure", "intervention delivery and exposure" in fig01_svg.lower(), True, True)
    check("Fig. 3 retains full replay boundary", "full replay unavailable" in fig03_svg, True, True)

    reference_count = len(re.findall(r"(?m)^\d+\. ", manuscript.split("# 参考文献", 1)[1]))
    check("31 references unchanged", reference_count == 31, reference_count, 31)
    check("v5 supplement reused", "Table S5. Frozen controlled artifact cases" in supplement, True, True)
    check("scientific interfaces unchanged", validation["scientific_interface_change"] == "none", validation["scientific_interface_change"], "none")

    report = {
        "status": "PASS" if all(item["passed"] for item in checks) else "FAIL",
        "n_checks": len(checks),
        "n_passed": sum(item["passed"] for item in checks),
        "checks": checks,
    }
    (LOGIC / "v5_1_manuscript_qa.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "n_checks": report["n_checks"], "n_passed": report["n_passed"]}, ensure_ascii=False, indent=2))
    if report["status"] != "PASS":
        failed = [item for item in checks if not item["passed"]]
        raise SystemExit(json.dumps(failed, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
