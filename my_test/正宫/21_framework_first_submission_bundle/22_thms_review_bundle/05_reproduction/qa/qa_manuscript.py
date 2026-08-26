#!/usr/bin/env python3
"""Check the framework-first manuscript against frozen clean-analysis outputs."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def resolve_root(root: Path | None) -> Path:
    candidate = Path(__file__).resolve().parents[2] if root is None else root.resolve()
    if (candidate / "03_clean_analysis").is_dir():
        return candidate
    nested = candidate / "my_test" / "正宫"
    if (nested / "03_clean_analysis").is_dir():
        return nested
    raise FileNotFoundError(f"Could not locate 正宫 below {candidate}")


def close(actual: float, expected: float, tolerance: float = 5e-5) -> bool:
    return math.isclose(actual, expected, rel_tol=0.0, abs_tol=tolerance)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument(
        "--manuscript",
        type=Path,
        default=None,
        help="Manuscript to check; defaults to 18_manuscript_v1/manuscript_v1_en.md.",
    )
    parser.add_argument(
        "--language",
        choices=("auto", "en", "zh"),
        default="auto",
        help="Language used for structural and wording checks.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="QA report path; defaults to 20_submission_package/manuscript_qa_report.json.",
    )
    args = parser.parse_args()
    root = resolve_root(args.root)
    clean = root / "03_clean_analysis"
    manuscript_path = (
        args.manuscript.resolve()
        if args.manuscript is not None
        else root / "18_manuscript_v1" / "manuscript_v1_en.md"
    )
    supplement_path = root / "20_submission_package" / "supplementary_material.md"
    report_path = (
        args.report.resolve()
        if args.report is not None
        else root / "20_submission_package" / "manuscript_qa_report.json"
    )

    manuscript = manuscript_path.read_text(encoding="utf-8")
    supplement = supplement_path.read_text(encoding="utf-8")
    interpretation_map_path = root / "20_submission_package" / "thms_admissible_interpretation_map.csv"
    language = args.language
    if language == "auto":
        language = "zh" if "## 摘要" in manuscript else "en"
    trials = read_csv(clean / "trial_level_fidelity_metrics.csv")
    stats = read_csv(clean / "statistics_summary.csv")
    lineage = read_csv(clean / "data_lineage_audit.csv")

    checks: list[dict[str, object]] = []

    def check(name: str, actual: object, expected: object, passed: bool) -> None:
        checks.append({"check": name, "actual": actual, "expected": expected, "passed": bool(passed)})

    modes = {mode: [row for row in trials if row["mode_code"] == mode] for mode in "AGEF"}
    check("trial count", len(trials), 180, len(trials) == 180)
    check("45 trials per mode", {key: len(value) for key, value in modes.items()}, {key: 45 for key in "AGEF"}, all(len(value) == 45 for value in modes.values()))
    participants = sorted({row["participant"] for row in trials})
    check("independent participants", participants, ["P01", "P02", "P03", "P04", "P05"], participants == ["P01", "P02", "P03", "P04", "P05"])

    binary_expectations = [
        ("A fixed-command fidelity", modes["A"], "A_fixed_command_compliance_task_to_end", 1, 45),
        ("G executable compliance", modes["G"], "executable_logic_compliance", 1, 45),
        ("G pre-contact activation", modes["G"], "pre_contact_activation", 1, 43),
        ("F nominal timing compliance", modes["F"], "nominal_activation_timing_compliance", 1, 3),
        ("F pre-contact activation", modes["F"], "pre_contact_activation", 1, 0),
    ]
    for name, rows, column, target, expected in binary_expectations:
        actual = sum(int(float(row[column])) == target for row in rows if row[column] != "")
        check(name, actual, expected, actual == expected)

    def median(rows: list[dict[str, str]], column: str) -> float:
        values = sorted(float(row[column]) for row in rows if row[column] != "")
        midpoint = len(values) // 2
        return values[midpoint] if len(values) % 2 else (values[midpoint - 1] + values[midpoint]) / 2

    f_latency = median(modes["F"], "contact_to_adaptation_latency_s")
    f_error = median(modes["F"], "activation_timing_error_s")
    check("F median activation", round(f_latency, 4), 0.0533, close(f_latency, 0.0533))
    check("F median timing error", round(f_error, 4), -0.1467, close(f_error, -0.1467))

    def exposure_counts(rows: list[dict[str, str]], column: str) -> dict[str, int]:
        values = [float(row[column]) for row in rows if row[column] != ""]
        return {
            "full": sum(value >= 1.0 - 1e-9 for value in values),
            "partial": sum(1e-9 < value < 1.0 - 1e-9 for value in values),
            "zero": sum(value <= 1e-9 for value in values),
        }

    exposure_expectations = [
        ("E vision exposure", modes["E"], "vision_configuration_outcome_window_overlap", {"full": 39, "partial": 2, "zero": 4}),
        ("F vision exposure", modes["F"], "vision_configuration_outcome_window_overlap", {"full": 42, "partial": 0, "zero": 3}),
        ("F adaptation exposure", modes["F"], "adaptation_outcome_window_overlap", {"full": 35, "partial": 7, "zero": 3}),
        ("F joint exposure", modes["F"], "outcome_window_overlap", {"full": 35, "partial": 7, "zero": 3}),
    ]
    for name, rows, column, expected in exposure_expectations:
        actual = exposure_counts(rows, column)
        check(name, actual, expected, actual == expected)

    selected = [row for row in lineage if row["included_main_clean"] == "1"]
    hash_count = sum(int(float(row[column])) for row in selected for column in ("csv_hash_verified", "events_hash_verified", "summary_hash_verified"))
    check("selected acquisition links", len(selected), 180, len(selected) == 180)
    check("selected-file hashes", hash_count, 540, hash_count == 540)

    ea = next(row for row in stats if row["metric"] == "primary_excess_impulse_Ns_0p2_1p0" and row["contrast"] == "E-A")
    frozen_ea = {
        "difference": float(ea["raw_mean_difference"]),
        "ci_low": float(ea["ci95_low"]),
        "ci_high": float(ea["ci95_high"]),
        "paired_t_p": float(ea["paired_t_p"]),
        "sign_flip_p": float(ea["exact_sign_flip_p"]),
        "wilcoxon_p": float(ea["wilcoxon_p"]),
        "holm_p": float(ea["paired_t_p_holm"]),
    }
    expected_ea = {"difference": -0.3489, "ci_low": -0.6080, "ci_high": -0.0898, "paired_t_p": 0.0201, "sign_flip_p": 0.0625, "wilcoxon_p": 0.0625, "holm_p": 0.0633}
    for key, expected in expected_ea.items():
        check(f"E-A {key}", round(frozen_ea[key], 4), expected, close(frozen_ea[key], expected))

    if language == "en":
        abstract_match = re.search(r"## Abstract\s+(.*?)\s+\*\*Keywords:", manuscript, flags=re.S)
        # Journal word counters generally treat hyphenated technical compounds as one
        # space-delimited word; use that conservative, reproducible convention here.
        abstract_words = abstract_match.group(1).split() if abstract_match else []
        check("abstract length", len(abstract_words), "200–250 words", 200 <= len(abstract_words) <= 250)
        section_markers = (
            "# 2. Realized-Intervention Fidelity Framework",
            "# 3. Teleoperation Case Study",
            "# 4. Fidelity Audit Results",
            "# 5. Exploratory Pilot Outcome Patterns",
            "# 6. Discussion",
            "# 7. Conclusion",
        )
    else:
        abstract_match = re.search(r"## 摘要\s+(.*?)\s+\*\*关键词：", manuscript, flags=re.S)
        abstract_characters = len(re.sub(r"\s+", "", abstract_match.group(1))) if abstract_match else 0
        check("Chinese abstract present", abstract_characters, "> 0 characters", abstract_characters > 0)
        literature_table = "**表I. 与人机实验评价相关的方法学路线及尚未解决的连接。**"
        main_table_markers = (
            literature_table,
            "**表II. 人机干预评价的最低证据包。**",
            "**表III. 名义主张、关键保真度证据与证据可容许解释。**",
        )
        table_positions = [manuscript.find(marker) for marker in main_table_markers]
        check(
            "Chinese literature-differentiation table",
            literature_table in manuscript,
            True,
            literature_table in manuscript,
        )
        check(
            "Chinese main Table I–III order",
            table_positions,
            "strictly increasing",
            all(value >= 0 for value in table_positions) and table_positions == sorted(table_positions),
        )
        check(
            "estimand differentiation reference",
            "Lundberg et al., 2021" in manuscript and "10.1177/00031224211004187" in manuscript,
            True,
            "Lundberg et al., 2021" in manuscript and "10.1177/00031224211004187" in manuscript,
        )
        interpretation_rows = read_csv(interpretation_map_path)
        interpretation_contrasts = [row["contrast"] for row in interpretation_rows]
        check(
            "THMS Table III machine-readable contrast map",
            interpretation_contrasts,
            ["G-A", "E-A", "F-E", "F-G"],
            interpretation_contrasts == ["G-A", "E-A", "F-E", "F-G"],
        )
        check(
            "G/F layer-boundary wording",
            {
                "G nominal unavailable": "没有恢复一项独立、同期的“接触后G”名义规范" in manuscript,
                "F not separately C!=R": r"没有把它另行归为\(C\neq R\)" in manuscript,
            },
            "both true",
            "没有恢复一项独立、同期的“接触后G”名义规范" in manuscript
            and r"没有把它另行归为\(C\neq R\)" in manuscript,
        )
        section_markers = (
            "# 2. 面向人机实验评价的实际干预保真度框架",
            "# 3. 回顾性遥操作案例研究",
            "# 4. 结果",
            "# 5. 讨论",
            "# 6. 结论",
        )
    section_order = [manuscript.find(marker) for marker in section_markers]
    check("framework-first section order", section_order, "strictly increasing", all(value >= 0 for value in section_order) and section_order == sorted(section_order))

    required_strings = (
        [
            "45/45 trials",
            "43/45 trials",
            "3/45",
            "+0.0533 s",
            "−0.1467",
            "39 trials, partial in 2, and zero in 4",
            "35 trials, partial in 7, and zero in 3",
            "540 selected-file SHA-256 hashes",
            "-0.3489 N·s",
            "-0.6080 to -0.0898",
        ]
        if language == "en"
        else [
            "45/45次",
            "43/45次",
            "3/45",
            "+0.0533 s",
            "−0.1467",
            "39次完全、2次部分、4次零暴露",
            "35次完全、7次部分、3次零暴露",
            "540个入选文件的SHA-256哈希",
            "−0.3489 N·s",
            "−0.6080至−0.0898",
        ]
    )
    for value in required_strings:
        check(f"manuscript contains frozen statement: {value}", value in manuscript, True, value in manuscript)

    forbidden = (
        ["baseline-corrected excess-force impulse", "vision significantly improved safety", "our controller outperformed", "first-ever framework", "novel universal framework"]
        if language == "en"
        else ["基线校正超额力冲量", "视觉显著提高了安全性", "我们的控制器优于", "首个通用框架", "新颖的通用框架"]
    )
    for phrase in forbidden:
        check(f"forbidden phrase absent: {phrase}", phrase in manuscript.lower(), False, phrase not in manuscript.lower())

    main_figure_names = [
        "Fig01_realized_intervention_framework.png",
        "Fig02_system_and_lineage.png",
        "Fig03_realized_intervention_fidelity.png",
        "Fig04_participant_EA_outcomes.png",
    ]
    if language == "en":
        main_figure_names.append("Fig05_contact_aligned_trajectories.png")
    main_figures = [root / "19_publication_figures" / "figures" / name for name in main_figure_names]
    check("main figure files exist", [path.name for path in main_figures], "all non-empty", all(path.is_file() and path.stat().st_size > 1000 for path in main_figures))
    check("main figures linked", [path.name for path in main_figures], "all linked", all(path.name in manuscript for path in main_figures))
    if language == "zh":
        check("Figure 5 moved out of THMS main manuscript", "Fig05_contact_aligned_trajectories.png" in manuscript, False, "Fig05_contact_aligned_trajectories.png" not in manuscript)
    check("legacy Figures 6–7 absent from main manuscript", "Fig06" in manuscript or "Fig07" in manuscript, False, "Fig06" not in manuscript and "Fig07" not in manuscript)
    check("Supplementary Figure S1 linked", "Fig05_contact_aligned_trajectories.png" in supplement, True, "Fig05_contact_aligned_trajectories.png" in supplement)
    check("Supplementary Figure S2 linked", "Fig06_participant_lopo_stability.png" in supplement, True, "Fig06_participant_lopo_stability.png" in supplement)
    check("Supplementary Figure S3 linked", "Fig07_lineage_trace_examples.png" in supplement, True, "Fig07_lineage_trace_examples.png" in supplement)

    report = {
        "status": "PASS" if all(item["passed"] for item in checks) else "FAIL",
        "n_checks": len(checks),
        "n_passed": sum(item["passed"] for item in checks),
        "manuscript": str(manuscript_path.relative_to(root)).replace("\\", "/"),
        "language": language,
        "frozen_sources": [
            "03_clean_analysis/trial_level_fidelity_metrics.csv",
            "03_clean_analysis/statistics_summary.csv",
            "03_clean_analysis/data_lineage_audit.csv",
        ],
        "checks": checks,
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("status", "n_checks", "n_passed")}, indent=2))
    if report["status"] != "PASS":
        failed = [item for item in checks if not item["passed"]]
        raise SystemExit(f"Manuscript QA failed: {failed}")


if __name__ == "__main__":
    main()
