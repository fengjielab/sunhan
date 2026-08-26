from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
from PIL import Image


HERE = Path(__file__).resolve().parent
BUNDLE = HERE.parents[1]
MANUSCRIPT = BUNDLE / "01_manuscript" / "manuscript_thms_v4_zh.md"
SUPPLEMENT = BUNDLE / "03_supplement" / "supplementary_material_v4.md"
LOGIC = BUNDLE / "04_logic_and_qa" / "v4"
FIGURES = BUNDLE / "02_main_figures" / "v4"
README = BUNDLE / "README.md"


def main() -> None:
    checks: list[dict] = []

    def check(name: str, passed: bool, observed: object, expected: object) -> None:
        checks.append({"check": name, "passed": int(bool(passed)), "observed": observed, "expected": expected})

    validation = json.loads((LOGIC / "v4_validation_report.json").read_text(encoding="utf-8"))
    figure_qa = json.loads((LOGIC / "v4_figure_qa.json").read_text(encoding="utf-8"))
    manuscript = MANUSCRIPT.read_text(encoding="utf-8")
    supplement = SUPPLEMENT.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    abstract = manuscript.split("## 摘要", 1)[1].split("# 1. 引言", 1)[0]
    body = manuscript.split("# 参考文献", 1)[0]

    check("v4 validation PASS", validation["status"] == "PASS", validation["status"], "PASS")
    check("v4 figure QA PASS", figure_qa["status"] == "PASS", figure_qa["status"], "PASS")
    check("12 controlled cases", validation["stage_a_stage_b_cases"]["n_cases"] == 12, validation["stage_a_stage_b_cases"]["n_cases"], 12)
    check("12 exact oracle matches", validation["stage_a_stage_b_cases"]["exact_matches"] == 12, validation["stage_a_stage_b_cases"]["exact_matches"], 12)
    for key in ("label_does_not_substitute_for_spec", "one_ms_is_partial", "missing_trace_is_not_zero", "joint_guard_clock_retained", "c_to_r_decoupled_from_exposure", "no_outcome_fields"):
        check(key, validation["stage_a_stage_b_cases"][key] is True, validation["stage_a_stage_b_cases"][key], True)
    check("21 frozen v1-v3 files unchanged", validation["baseline"] == {"verified": 21, "total": 21}, validation["baseline"], {"verified": 21, "total": 21})
    check("180 exact provenance trials", validation["real_case"]["provenance_valid_trials"] == 180, validation["real_case"]["provenance_valid_trials"], 180)
    check("A/G/E/F each 45", validation["real_case"]["mode_counts"] == {"A": 45, "E": 45, "F": 45, "G": 45}, validation["real_case"]["mode_counts"], {"A": 45, "E": 45, "F": 45, "G": 45})
    check("E exposure 39/2/4", validation["real_case"]["exposure_counts"]["E"] == {"full": 39, "partial": 2, "zero": 4}, validation["real_case"]["exposure_counts"]["E"], {"full": 39, "partial": 2, "zero": 4})
    check("F C-to-R not evaluable", validation["real_case"]["configuration_states"]["F"]["c_to_r"] == "not_evaluable", validation["real_case"]["configuration_states"]["F"], "c_to_r=not_evaluable")
    check("G replay rows", validation["real_case"]["g_replay"]["n_replayed_update_rows"] == 12196, validation["real_case"]["g_replay"]["n_replayed_update_rows"], 12196)
    check("G replay error below tolerance", validation["real_case"]["g_replay"]["max_stiffness_update_error_N_per_m"] < validation["real_case"]["g_replay"]["tolerance"], validation["real_case"]["g_replay"]["max_stiffness_update_error_N_per_m"], f"<{validation['real_case']['g_replay']['tolerance']}")
    check("64 combinations carried forward", validation["carry_forward"]["record_selection_combinations"] == 64 and validation["carry_forward"]["record_selection_unique_masks"] == 64, [validation["carry_forward"]["record_selection_combinations"], validation["carry_forward"]["record_selection_unique_masks"]], [64, 64])
    check("64 combinations directly rerun in v4", validation["carry_forward"]["direct_rerun"] is True, validation["carry_forward"]["direct_rerun"], True)
    check("six E non-full rows directly reconstructed", validation["carry_forward"]["e_nonfull_rows"] == 6, validation["carry_forward"]["e_nonfull_rows"], 6)
    fclock = validation["carry_forward"]["f_clock_evidence"]
    check("F source signatures all pass", all(fclock["source_signatures"].values()), fclock["source_signatures"], "all true")
    check("F timing remains 3/45", fclock["n_f_trials"] == 45 and fclock["nominal_plus_0p20_compliant_trials"] == 3, [fclock["nominal_plus_0p20_compliant_trials"], fclock["n_f_trials"]], [3, 45])

    required = [
        "ArtifactEvidence", "Stage A", "Stage B", "名义条件标签不能替代可恢复的干预规范",
        "结构化作者审计", "受控工件扰动与规则级实现核验", "12/12", "不构成方法学或外部验证",
        "c_to_r", "not_evaluable", "约1 ms", "12,196", "outside_fidelity_framework",
        "[ETHICS RECORD REQUIRED—DO NOT SUBMIT]", "02_main_figures/v4", "补充表S1",
    ]
    for phrase in required:
        check(f"required manuscript phrase: {phrase}", phrase in manuscript, phrase in manuscript, True)

    check("abstract omits 64-combination result", "64" not in abstract and "2^6" not in abstract, ["64" in abstract, "2^6" in abstract], [False, False])
    check("abstract omits detailed CI and p values", "95%" not in abstract and "p=" not in abstract and "0.0625" not in abstract, ["95%" in abstract, "p=" in abstract, "0.0625" in abstract], [False, False, False])
    check("abstract retains one illustrative E-A estimate", "−0.3489 N·s" in abstract, "−0.3489 N·s" in abstract, True)
    forbidden = ["可容许估计目标", "admissible estimand", "framework has been validated", "框架已经得到验证", "双人独立复核完成", "审计者一致性为"]
    for phrase in forbidden:
        check(f"forbidden phrase absent: {phrase}", phrase.lower() not in body.lower(), phrase.lower() in body.lower(), False)
    check("31 numbered references", len(re.findall(r"(?m)^\d+\. ", manuscript.split("# 参考文献", 1)[1])) == 31, len(re.findall(r"(?m)^\d+\. ", manuscript.split("# 参考文献", 1)[1])), 31)
    check("correct Automatica DOI", "10.1016/j.automatica.2023.111123" in manuscript, "10.1016/j.automatica.2023.111123" in manuscript, True)

    required_files = [
        HERE / "evidence_pipeline.py", HERE / "controlled_artifact_cases.csv", HERE / "artifact_to_state_rules.csv",
        HERE / "structured_semantic_audit.csv", HERE / "baseline_hashes.json", HERE / "validate_v4.py",
        HERE / "generate_v4_figures.py", SUPPLEMENT, LOGIC / "THMS_V4_LOGIC_TRACEABILITY.md",
        BUNDLE / "03_supplement" / "v4_data" / "controlled_artifact_case_results.csv",
        BUNDLE / "03_supplement" / "v4_data" / "trial_evidence_states.csv",
        BUNDLE / "03_supplement" / "v4_data" / "real_case_artifact_audit.csv",
        BUNDLE / "03_supplement" / "v4_data" / "record_selection_64_combinations.csv",
        BUNDLE / "03_supplement" / "v4_data" / "record_selection_summary.csv",
        BUNDLE / "03_supplement" / "v4_data" / "e_nonfull_exposure_mechanisms.csv",
        BUNDLE / "03_supplement" / "v4_data" / "f_clock_evidence.json",
    ]
    check("all v4 deliverables exist", all(path.exists() and path.stat().st_size > 0 for path in required_files), [str(path.relative_to(BUNDLE)) for path in required_files if not path.exists() or path.stat().st_size == 0], [])
    check("README marks v4 current", "manuscript_thms_v4_zh.md`：当前中文主稿" in readme, "manuscript_thms_v4_zh.md`：当前中文主稿" in readme, True)

    states = pd.read_csv(BUNDLE / "03_supplement" / "v4_data" / "trial_evidence_states.csv")
    check("trial-state table has 180 unique records", len(states) == 180 and states.record_id.nunique() == 180, [len(states), states.record_id.nunique()], [180, 180])
    fstates = states.loc[states.configuration.eq("F")]
    check("F replay/exposure decoupling in all 45 trials", len(fstates) == 45 and fstates.c_to_r.eq("not_evaluable").all() and fstates.exposure.isin(["full", "partial", "zero"]).all(), [len(fstates), fstates.c_to_r.value_counts().to_dict(), fstates.exposure.value_counts().to_dict()], "45 not_evaluable C-to-R with known exposure")

    for stem in ("Fig01_artifact_to_inference_pipeline_v4", "Fig04_fidelity_constrained_outcomes_v4"):
        for suffix in ("pdf", "svg", "png"):
            path = FIGURES / f"{stem}.{suffix}"
            check(f"figure exists: {path.name}", path.exists() and path.stat().st_size > 1000, path.stat().st_size if path.exists() else -1, ">1000 bytes")
        with Image.open(FIGURES / f"{stem}.png") as image:
            dpi = image.info.get("dpi", (0, 0))
            check(f"figure PNG nominal 600 dpi: {stem}", min(dpi) >= 590, dpi, ">=590 dpi")

    markdown_links = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", manuscript)
    missing_links = [(MANUSCRIPT.parent / link).resolve() for link in markdown_links if not (MANUSCRIPT.parent / link).resolve().exists()]
    check("all manuscript image links resolve", not missing_links, [str(path) for path in missing_links], [])
    check("supplement documents structured audit boundary", "not a dual-review agreement study" in supplement, "not a dual-review agreement study" in supplement, True)
    check("supplement documents missing trace boundary", "never imputed as zero" in supplement, "never imputed as zero" in supplement, True)

    status = "PASS" if all(item["passed"] for item in checks) else "FAIL"
    report = {"status": status, "n_checks": len(checks), "n_passed": sum(item["passed"] for item in checks), "checks": checks}
    (LOGIC / "v4_manuscript_qa.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "n_checks": len(checks), "n_passed": report["n_passed"], "failed": [item["check"] for item in checks if not item["passed"]]}, ensure_ascii=False, indent=2))
    if status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
