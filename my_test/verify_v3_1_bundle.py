#!/usr/bin/env python3
"""Independently verify the THMS v3.1 bundle and write its audit artifacts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import tempfile
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BUNDLE = ROOT / "正宫" / "26_runtime_exposure_submission_bundle_v3_1"
ANALYSIS = BUNDLE / "analysis"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def verify_prior_bundle(bundle: Path) -> None:
    manifest_path = bundle / "bundle_manifest_sha256.json"
    require(manifest_path.is_file(), f"prior manifest missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for relative, entry in manifest["files"].items():
        expected = entry["sha256"] if isinstance(entry, dict) else entry
        path = bundle / relative
        require(path.is_file(), f"prior bundle file missing: {path}")
        require(sha256(path) == expected, f"prior bundle changed: {path}")


def verify_not_touched_since(path: Path, cutoff: datetime) -> None:
    changed = [p for p in path.rglob("*") if p.is_file() and datetime.fromtimestamp(p.stat().st_mtime) >= cutoff]
    require(not changed, f"protected source or v1 was touched during v3.1 work: {changed[:3]}")


def manuscript_structure(text: str, language: str) -> None:
    image_lines = re.findall(r"^!\[[^\n]*\]\(analysis/figures/[^\n]+\)$", text, flags=re.MULTILINE)
    table_separators = re.findall(r"^\|---(?:\||$)", text, flags=re.MULTILINE)
    require(len(image_lines) == 5, f"{language} main manuscript must contain exactly five figures")
    require(len(table_separators) == 3, f"{language} main manuscript must contain exactly three tables")
    expected_stems = {
        "fig1_five_layer_framework", "fig2_retrospective_discontinuities",
        "fig3_record_layer_recovery", "fig4_outcome_window_binding",
        "fig5_human_variability_stress_test",
    }
    require({Path(line.split("(", 1)[1][:-1]).stem for line in image_lines} == expected_stems,
            f"{language} figure allocation differs from the fixed five-figure story")
    captions = ["Table I.", "Table II.", "Table III."] if language == "en" else ["表I.", "表II.", "表III."]
    require(all(text.count(caption) == 1 for caption in captions), f"{language} table captions mismatch")


def verify_bundle() -> dict:
    required = [
        BUNDLE / "README.md",
        BUNDLE / "analysis_plan_v3_1.md",
        BUNDLE / "supplementary_methods_and_results_v3_1.md",
        BUNDLE / "manuscript_thms_v3_1_en.md",
        BUNDLE / "manuscript_thms_v3_1_zh.md",
        ANALYSIS / "analysis_cohort_manifest.csv",
        ANALYSIS / "trial_metrics.csv",
        ANALYSIS / "condition_record_fidelity.csv",
        ANALYSIS / "quality_and_safety_summary.csv",
        ANALYSIS / "record_command_summary.csv",
        ANALYSIS / "participant_human_variability.csv",
        ANALYSIS / "human_variability_range.csv",
        ANALYSIS / "human_variability_associations.csv",
        ANALYSIS / "bootstrap_provenance.json",
        ANALYSIS / "supplementary_quartile_robustness.csv",
        ANALYSIS / "retrospective_diagnostic_summary.csv",
        ANALYSIS / "evidence_layer_status.csv",
        ANALYSIS / "validation_acceptance.json",
        ANALYSIS / "analysis_provenance.json",
    ]
    stems = [
        "fig1_five_layer_framework", "fig2_retrospective_discontinuities",
        "fig3_record_layer_recovery", "fig4_outcome_window_binding",
        "fig5_human_variability_stress_test",
    ]
    required.extend(ANALYSIS / "figures" / f"{stem}.{ext}" for stem in stems for ext in ("png", "svg", "pdf"))
    for path in required:
        require(path.is_file(), f"required v3.1 file missing: {path}")

    cohort = read_csv(ANALYSIS / "analysis_cohort_manifest.csv")
    metrics = read_csv(ANALYSIS / "trial_metrics.csv")
    fidelity = read_csv(ANALYSIS / "condition_record_fidelity.csv")
    quality = read_csv(ANALYSIS / "quality_and_safety_summary.csv")
    command = read_csv(ANALYSIS / "record_command_summary.csv")
    participants = read_csv(ANALYSIS / "participant_human_variability.csv")
    ranges = {r["stressor"]: r for r in read_csv(ANALYSIS / "human_variability_range.csv")}
    associations = read_csv(ANALYSIS / "human_variability_associations.csv")
    quartiles = read_csv(ANALYSIS / "supplementary_quartile_robustness.csv")
    retrospective = {r["configuration"]: r for r in read_csv(ANALYSIS / "retrospective_diagnostic_summary.csv")}
    layers = {r["layer"]: r for r in read_csv(ANALYSIS / "evidence_layer_status.csv")}
    bootstrap = json.loads((ANALYSIS / "bootstrap_provenance.json").read_text(encoding="utf-8"))
    acceptance = json.loads((ANALYSIS / "validation_acceptance.json").read_text(encoding="utf-8"))
    provenance = json.loads((ANALYSIS / "analysis_provenance.json").read_text(encoding="utf-8"))

    overall = next(r for r in fidelity if r["condition"] == "OVERALL")
    quality_all = next(r for r in quality if r["condition"] == "OVERALL")
    command_all = next(r for r in command if r["condition"] == "OVERALL")
    command_c4 = next(r for r in command if r["condition"] == "C4")

    require(len(cohort) == 300 and len(metrics) == 300, "queue and metrics must contain 300 planned trials")
    require({r["participant_id"] for r in cohort} == {f"F{i:02d}" for i in range(1, 21)}, "queue must be exactly F01-F20")
    require(sum(int(r["completed"]) for r in cohort) == 294, "queue must contain 294 complete trials")
    require(sum(int(r["safety_abort"]) for r in metrics) == 6, "metrics must retain six safety aborts")
    require(int(overall["evaluable_trials"]) == 294 and int(overall["classification_correct"]) == 294, "primary denominator or classification mismatch")
    require(abs(float(overall["classification_exact_ci_low"]) - 0.9875311790067285) < 1e-14, "exact binomial interval mismatch")
    require(abs(float(overall["timing_mae_s"]) - 0.0023808570170068197) < 1e-15, "timing MAE mismatch")
    require(abs(float(overall["exposure_mae"]) - 0.001797513269557801) < 1e-15, "exposure MAE mismatch")
    require(int(quality_all["haptic_clamped_completed_trials"]) == 65, "whole-trial clamp count mismatch")
    require(int(command_all["outcome_window_clamp_trials"]) == 47, "window clamp count mismatch")
    require(int(command_c4["any_trial_clamp_trials"]) == 11 and int(command_c4["outcome_window_clamp_trials"]) == 0, "C4 window-binding result mismatch")

    require(len(participants) == 20 and {r["analysis_unit"] for r in participants} == {"participant"}, "human stress test must have 20 participant units")
    require(all(float(r["classification_accuracy"]) == 1.0 for r in participants), "participant classification must be 100%")
    worst_timing = max(float(r["timing_mae_fraction_of_limit"]) for r in participants)
    worst_exposure = max(float(r["exposure_mae_fraction_of_limit"]) for r in participants)
    require(abs(worst_timing - 0.1526000666666731) < 1e-14, "worst timing margin mismatch")
    require(abs(worst_exposure - 0.12605323333332827) < 1e-14, "worst exposure margin mismatch")
    require(worst_timing < 1 and worst_exposure < 1, "at least one participant failed an analysis limit")

    require(len(associations) == 12, "six stressors by two errors must produce 12 relations")
    require({r["participant_count"] for r in associations} == {"20"}, "association unit count mismatch")
    require({r["p_value_computed"] for r in associations} == {"0"}, "association output must not contain computed p-values")
    require("classification_accuracy" not in {r["outcome"] for r in associations}, "constant accuracy must not enter association analysis")
    require(bootstrap["seed"] == 20260827 and bootstrap["requested_replicates"] == 10000, "bootstrap freeze mismatch")
    require(bootstrap["analysis_unit"] == "participant" and bootstrap["p_values_computed"] is False, "bootstrap interpretation mismatch")
    require(len(quartiles) == 12 and all(int(r["participant_count"]) == 5 for r in quartiles), "quartile supplement mismatch")

    require(abs(float(ranges["approach_duration"]["participant_mean_min"]) - 1.3033435424666666) < 1e-14, "approach range mismatch")
    require(abs(float(ranges["approach_duration"]["participant_mean_max"]) - 2.835968462923077) < 1e-14, "approach range mismatch")
    require(abs(float(ranges["omega_path"]["participant_mean_min"]) - 0.023673988333101356) < 1e-15, "Omega range mismatch")
    require(abs(float(ranges["omega_path"]["participant_mean_max"]) - 0.04642987106651571) < 1e-15, "Omega range mismatch")
    require(abs(float(ranges["whole_trial_clamp_rate"]["participant_mean_max"]) - 0.7857142857142857) < 1e-15, "clamp range mismatch")

    require(set(retrospective) == {"A", "G", "E", "F"}, "retrospective configurations mismatch")
    require("43/45" in retrospective["G"]["key_discrepancy"], "G diagnostic mismatch")
    require("3/45" in retrospective["F"]["runtime_evidence"] and "35/7/3" in retrospective["F"]["runtime_evidence"], "F diagnostic mismatch")
    require("39 full / 2 partial / 4 zero" in retrospective["E"]["runtime_evidence"], "E diagnostic mismatch")

    require(layers["R_i^cmd"]["status"] == "OBSERVED_AS_SOFTWARE_COMMAND", "command must remain software evidence")
    require(layers["D_i^phys"]["status"] == "NOT_INDEPENDENTLY_OBSERVED", "physical layer must remain unobserved")
    require(acceptance["overall_primary_pass"] is True, "primary criteria did not pass")
    require(acceptance["human_outcome_role"] == "EXPLORATORY_ONLY", "human outcomes were promoted beyond scope")
    require(provenance["historical_first_five_merged_into_formal_cohort"] is False, "historical F01-F05 entered formal cohort")
    require(provenance["raw_files_modified"] is False, "raw files were modified")
    require(all(r["csv_verification"] == "byte_exact" for r in cohort), "CSV byte audit mismatch")
    require(all(r["events_verification"] in {"byte_exact", "canonical_text_exact"} for r in cohort), "event hash audit failed")
    require(all(r["summary_verification"] in {"byte_exact", "canonical_text_exact"} for r in cohort), "summary hash audit failed")

    manuscripts = {
        "en": (BUNDLE / "manuscript_thms_v3_1_en.md").read_text(encoding="utf-8"),
        "zh": (BUNDLE / "manuscript_thms_v3_1_zh.md").read_text(encoding="utf-8"),
    }
    for language, text in manuscripts.items():
        manuscript_structure(text, language)
        require("ETHICS RECORD REQUIRED—DO NOT SUBMIT" in text, f"{language} ethics blocker missing")
        for value in ("294/294", "98.75", "2.381", "4.957", "5.408", "0.001798", "0.005996", "0.006760", "15.26", "12.61", "43/45", "3/45", "35/7/3"):
            require(value in text, f"{language} manuscript missing traced value: {value}")
    require("39/2/4" in manuscripts["en"] and "39/2/4" in manuscripts["zh"], "retrospective E counts missing")
    require("65/294" in manuscripts["en"] and "47/294" in manuscripts["en"], "English clamp denominators missing")
    require("65个" in manuscripts["zh"] and "47个" in manuscripts["zh"], "Chinese clamp counts missing")

    banned = {
        "en": ["external validation", "physical truth recovery", "confirmatory human effect", "preregistered", "all raw byte hashes matched"],
        "zh": ["外部验证", "物理真值恢复", "确认性人体效应", "预注册", "全部原始字节哈希通过"],
    }
    for language, phrases in banned.items():
        lowered = manuscripts[language].lower()
        for phrase in phrases:
            require(phrase.lower() not in lowered, f"{language} prohibited phrase found: {phrase}")

    for relative, expected in provenance["output_sha256"].items():
        path = ANALYSIS / relative
        require(path.is_file() and sha256(path) == expected, f"analysis artifact changed after provenance freeze: {relative}")

    verify_not_touched_since(ROOT / "正宫" / "21_framework_first_submission_bundle", datetime(2026, 8, 27))
    verify_prior_bundle(ROOT / "正宫" / "24_framework_validation_submission_bundle_v2")
    verify_prior_bundle(ROOT / "正宫" / "25_runtime_exposure_submission_bundle_v3")
    verify_not_touched_since(ROOT / "data" / "kfb_timing_formal_v1", datetime(2026, 8, 27))

    return {
        "status": "PASS",
        "participants": 20,
        "planned_trials": 300,
        "evaluable_trials": 294,
        "safety_aborts": 6,
        "classification": "294/294",
        "classification_exact_95_ci": [0.9875311790067285, 1.0],
        "worst_participant_limit_fraction": {"timing": worst_timing, "exposure": worst_exposure},
        "whole_trial_clamps": 65,
        "outcome_window_clamps": 47,
        "main_figures": 5,
        "main_tables": 3,
        "continuous_relations": 12,
        "physical_delivery": "NOT_INDEPENDENTLY_OBSERVED",
        "human_outcomes": "EXPLORATORY_ONLY",
        "prior_bundles_and_raw_sources_unchanged": True,
    }


def deterministic_rerun() -> dict:
    from analyze_kfb_runtime_exposure_v3_1 import run_analysis
    from analyze_kfb_timing_formal import parse_participants

    data = ROOT / "data" / "kfb_timing_formal_v1" / "participants"
    protocol = ROOT / "正宫" / "23_kfb_timing_pilot" / "frozen_schedule_formal_v1" / "protocol_config_v1.json"
    oracle = ROOT / "正宫" / "23_kfb_timing_pilot" / "frozen_schedule_formal_v1" / "private_oracle" / "oracle.csv"
    with tempfile.TemporaryDirectory() as left_name, tempfile.TemporaryDirectory() as right_name:
        left, right = Path(left_name), Path(right_name)
        participants = parse_participants("F01-F20")
        run_analysis(data, protocol, oracle, participants, left)
        run_analysis(data, protocol, oracle, participants, right)
        left_files = sorted(p.relative_to(left).as_posix() for p in left.rglob("*") if p.is_file())
        right_files = sorted(p.relative_to(right).as_posix() for p in right.rglob("*") if p.is_file())
        require(left_files == right_files, "independent reruns produced different file sets")
        mismatches = [name for name in left_files if sha256(left / name) != sha256(right / name)]
        require(not mismatches, f"independent reruns were not byte-identical: {mismatches}")
        packaged_mismatch = [name for name in left_files if name != "analysis_provenance.json" and sha256(left / name) != sha256(ANALYSIS / name)]
        require(not packaged_mismatch, f"packaged analysis differs from clean rerun: {packaged_mismatch}")
        return {"runs": 2, "files_compared": len(left_files), "byte_identical": True, "packaged_outputs_matched": True}


def write_report(report: dict) -> Path:
    path = BUNDLE / "validation_report_v3_1.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return path


def write_manifest() -> Path:
    path = BUNDLE / "bundle_manifest_sha256.json"
    entries = {
        p.relative_to(BUNDLE).as_posix(): sha256(p)
        for p in sorted(BUNDLE.rglob("*")) if p.is_file() and p != path
    }
    payload = {"algorithm": "SHA-256", "file_count": len(entries), "files": entries}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-rerun", action="store_true", help="skip the two clean deterministic analysis runs")
    args = parser.parse_args()
    report = verify_bundle()
    report["deterministic_rerun"] = {"skipped": True} if args.skip_rerun else deterministic_rerun()
    report["validation_report_written"] = True
    report["bundle_manifest_written"] = True
    report_path = write_report(report)
    manifest_path = write_manifest()
    print(json.dumps({**report, "validation_report": str(report_path), "bundle_manifest": str(manifest_path)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
