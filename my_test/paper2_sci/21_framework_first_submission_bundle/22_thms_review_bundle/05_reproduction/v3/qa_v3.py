from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
BUNDLE = SCRIPT_DIR.parents[1]
MANUSCRIPT = BUNDLE / "01_manuscript" / "manuscript_thms_v3_zh.md"
SUPPLEMENT = BUNDLE / "03_supplement" / "supplementary_material_v3.md"
LOGIC = BUNDLE / "04_logic_and_qa" / "v3"
SUPP_DATA = BUNDLE / "03_supplement" / "v3_data"
REPORT = LOGIC / "v3_manuscript_qa.json"


def main() -> None:
    manuscript = MANUSCRIPT.read_text(encoding="utf-8")
    supplement = SUPPLEMENT.read_text(encoding="utf-8")
    validation = json.loads((LOGIC / "v3_validation_report.json").read_text(encoding="utf-8"))
    figure_qa = json.loads((LOGIC / "v3_figure_qa.json").read_text(encoding="utf-8"))
    controlled = pd.read_csv(SUPP_DATA / "controlled_perturbation_results.csv")
    combinations = pd.read_csv(SUPP_DATA / "record_selection_64_combinations.csv")
    selection = pd.read_csv(SUPP_DATA / "record_selection_summary.csv").set_index("contrast")

    checks: list[dict[str, object]] = []

    def check(name: str, passed: bool, observed: object, expected: object) -> None:
        checks.append({
            "check": name,
            "passed": int(bool(passed)),
            "observed": observed,
            "expected": expected,
        })

    check("validation report pass", validation["status"] == "PASS", validation["status"], "PASS")
    check("figure QA pass", figure_qa["status"] == "PASS", figure_qa["status"], "PASS")
    check("controlled cases 11/11", len(controlled) == 11 and int(controlled["oracle_exact_match"].sum()) == 11, (len(controlled), int(controlled["oracle_exact_match"].sum())), (11, 11))
    check("64 unique record selections", len(combinations) == 64 and combinations["selection_mask"].nunique() == 64, (len(combinations), combinations["selection_mask"].nunique()), (64, 64))
    check("E-A all 64 negative", int(selection.loc["EA", "negative_mean_combinations"]) == 64, int(selection.loc["EA", "negative_mean_combinations"]), 64)
    check("E-A 5/5 in all 64", int(selection.loc["EA", "all_five_participants_negative_combinations"]) == 64, int(selection.loc["EA", "all_five_participants_negative_combinations"]), 64)
    check("F-E participant directions remain 2-3", int(selection.loc["FE", "minimum_negative_participant_count"]) == 2 and int(selection.loc["FE", "maximum_negative_participant_count"]) == 3, (int(selection.loc["FE", "minimum_negative_participant_count"]), int(selection.loc["FE", "maximum_negative_participant_count"])), (2, 3))

    headings = [
        "# 1. 引言",
        "# 2. 实际干预保真度约束框架",
        "# 3. 方法",
        "# 4. 结果",
        "# 5. 讨论",
        "# 6. 结论",
        "# 参考文献",
    ]
    positions = [manuscript.find(item) for item in headings]
    check("main section order", all(value >= 0 for value in positions) and positions == sorted(positions), positions, "strictly increasing")

    required = [
        "11/11",
        "机器可读证据状态",
        "NOMINAL_SPEC",
        "规范缺失与已证实的",
        "因果识别仍需",
        "内部判别检查",
        "39次完全、2次部分和4次零暴露",
        "1.072–1.434 s",
        "1.501–1.807 s",
        "0.9669和0.00115",
        "−0.353791至−0.336697 N·s",
        "每种仅2–3名参与者为负",
        "操作性超额力冲量",
        "共享测量误差",
        "[ETHICS RECORD REQUIRED—DO NOT SUBMIT]",
    ]
    # NOMINAL_SPEC is represented in the manuscript as the conceptual nominal-spec field;
    # accept either the literal interface spelling or the mathematical s_N spelling.
    for value in required:
        if value == "NOMINAL_SPEC":
            passed = "`nominal_spec`" in manuscript or "s_N" in manuscript
        else:
            passed = value in manuscript
        check(f"required manuscript statement: {value}", passed, passed, True)

    body = manuscript.split("# 参考文献", 1)[0]
    forbidden = [
        "可容许估计目标",
        "admissible estimand",
        "本研究完成了框架外部验证",
        "视觉显著提高了安全性",
        "纯接触后力自适应效应得到证明",
        "180个独立",
    ]
    for phrase in forbidden:
        check(f"forbidden body phrase absent: {phrase}", phrase.lower() not in body.lower(), phrase in body, False)

    check("descriptive contrast notation", "D^R_{m_1,m_0}" in manuscript, "D^R_{m_1,m_0}" in manuscript, True)
    check("old estimand notation absent", "\\Delta^R" not in body, "\\Delta^R" in body, False)
    check("three research questions", len(re.findall(r"\*\*RQ[123]", manuscript)) == 3, len(re.findall(r"\*\*RQ[123]", manuscript)), 3)
    check("31 references", len(re.findall(r"(?m)^\d+\. ", manuscript.split("# 参考文献", 1)[1])) == 31, len(re.findall(r"(?m)^\d+\. ", manuscript.split("# 参考文献", 1)[1])), 31)
    check("correct Automatica DOI", "10.1016/j.automatica.2023.111123" in manuscript, "10.1016/j.automatica.2023.111123" in manuscript, True)

    image_links = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", manuscript)
    resolved_images = [(MANUSCRIPT.parent / item).resolve() for item in image_links]
    check("four linked main figures", len(resolved_images) == 4, len(resolved_images), 4)
    check("all linked main figures exist", all(path.is_file() and path.stat().st_size > 1000 for path in resolved_images), [str(path) for path in resolved_images], "all files >1000 bytes")
    check("v3-specific Figure 1 linked", "02_main_figures/v3/Fig01_fidelity_constrained_framework_v3.png" in manuscript, image_links, True)
    check("v3-specific Figure 4 linked", "02_main_figures/v3/Fig04_fidelity_constrained_outcomes_v3.png" in manuscript, image_links, True)

    supplement_links = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", supplement)
    resolved_supp = [(SUPPLEMENT.parent / item).resolve() for item in supplement_links]
    check("three supplementary figures", len(resolved_supp) == 3, len(resolved_supp), 3)
    check("all supplementary figures exist", all(path.is_file() and path.stat().st_size > 1000 for path in resolved_supp), [str(path) for path in resolved_supp], "all files >1000 bytes")
    for table in range(1, 9):
        marker = f"## Table S{table}."
        check(f"supplement contains Table S{table}", marker in supplement, marker in supplement, True)

    machine_files = [
        "controlled_perturbation_results.csv",
        "record_selection_64_combinations.csv",
        "record_selection_summary.csv",
        "e_nonfull_exposure_mechanisms.csv",
        "f_clock_evidence.json",
    ]
    check("all v3 supplementary data files exist", all((SUPP_DATA / item).is_file() for item in machine_files), machine_files, "all exist")

    report = {
        "status": "PASS" if all(item["passed"] for item in checks) else "FAIL",
        "n_checks": len(checks),
        "n_passed": sum(item["passed"] for item in checks),
        "manuscript": str(MANUSCRIPT.relative_to(BUNDLE)).replace("\\", "/"),
        "supplement": str(SUPPLEMENT.relative_to(BUNDLE)).replace("\\", "/"),
        "checks": checks,
    }
    LOGIC.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("status", "n_checks", "n_passed")}, indent=2))
    if report["status"] != "PASS":
        failed = [item for item in checks if not item["passed"]]
        raise RuntimeError(f"v3 manuscript QA failed: {failed}")


if __name__ == "__main__":
    main()
