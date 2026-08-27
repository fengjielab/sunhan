#!/usr/bin/env python3
"""Verify the THMS v3 record-layer bundle and refresh its SHA-256 manifest."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import tempfile
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BUNDLE = ROOT / "正宫" / "25_runtime_exposure_submission_bundle_v3"
ANALYSIS = BUNDLE / "analysis"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def verify_prior_bundle(bundle: Path) -> None:
    manifest_path = bundle / "bundle_manifest_sha256.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for relative, expected in manifest["files"].items():
        expected_hash = expected["sha256"] if isinstance(expected, dict) else expected
        path = bundle / relative
        require(path.is_file(), f"prior bundle file missing: {path}")
        require(sha256(path) == expected_hash, f"prior bundle changed: {path}")


def verify_not_touched_since(path: Path, cutoff: datetime) -> None:
    changed = [item for item in path.rglob("*") if item.is_file() and datetime.fromtimestamp(item.stat().st_mtime) >= cutoff]
    require(not changed, f"protected source or prior bundle was touched during v3 work: {changed[:3]}")


def verify() -> dict:
    required = [
        BUNDLE / "README.md",
        BUNDLE / "analysis_plan_v3.md",
        BUNDLE / "supplementary_methods_and_results_v3.md",
        BUNDLE / "manuscript_thms_v3_zh.md",
        BUNDLE / "manuscript_thms_v3_en.md",
        ANALYSIS / "analysis_cohort_manifest.csv",
        ANALYSIS / "trial_metrics.csv",
        ANALYSIS / "condition_record_fidelity.csv",
        ANALYSIS / "quality_and_safety_summary.csv",
        ANALYSIS / "record_command_summary.csv",
        ANALYSIS / "participant_runtime_summary.csv",
        ANALYSIS / "trajectory_robustness_quartiles.csv",
        ANALYSIS / "evidence_layer_status.csv",
        ANALYSIS / "validation_acceptance.json",
        ANALYSIS / "analysis_provenance.json",
        ANALYSIS / "figures" / "fig1_five_layer_framework.png",
        ANALYSIS / "figures" / "fig2_record_layer_recovery.png",
        ANALYSIS / "figures" / "fig3_command_layer.png",
        ANALYSIS / "figures" / "fig4_variability_stress_test.png",
    ]
    for path in required:
        require(path.is_file(), f"missing required bundle file: {path}")

    cohort = read_csv(ANALYSIS / "analysis_cohort_manifest.csv")
    metrics = read_csv(ANALYSIS / "trial_metrics.csv")
    fidelity = read_csv(ANALYSIS / "condition_record_fidelity.csv")
    quality = read_csv(ANALYSIS / "quality_and_safety_summary.csv")
    command = read_csv(ANALYSIS / "record_command_summary.csv")
    participants = read_csv(ANALYSIS / "participant_runtime_summary.csv")
    robustness = read_csv(ANALYSIS / "trajectory_robustness_quartiles.csv")
    layers = {row["layer"]: row for row in read_csv(ANALYSIS / "evidence_layer_status.csv")}
    acceptance = json.loads((ANALYSIS / "validation_acceptance.json").read_text(encoding="utf-8"))
    provenance = json.loads((ANALYSIS / "analysis_provenance.json").read_text(encoding="utf-8"))
    overall = next(row for row in fidelity if row["condition"] == "OVERALL")
    q_all = next(row for row in quality if row["condition"] == "OVERALL")
    cmd_all = next(row for row in command if row["condition"] == "OVERALL")
    cmd_c4 = next(row for row in command if row["condition"] == "C4")

    require(len(cohort) == 300 and len(metrics) == 300, "queue and trial metrics must each contain 300 trials")
    require({row["participant_id"] for row in cohort} == {f"F{i:02d}" for i in range(1, 21)}, "cohort must be exactly F01-F20")
    require(sum(int(row["completed"]) for row in cohort) == 294, "cohort must contain 294 completed trials")
    require(sum(int(row["safety_abort"]) for row in metrics) == 6, "metrics must retain six safety aborts")
    require(int(overall["evaluable_trials"]) == 294, "record-layer primary denominator must be 294")
    require(int(overall["classification_correct"]) == 294, "all 294 evaluable trials must classify correctly")
    require(abs(float(overall["classification_exact_ci_low"]) - 0.9875311790067285) < 1e-14, "exact binomial interval mismatch")
    require(int(q_all["haptic_clamped_completed_trials"]) == 65, "whole-trial completed clamp count must be 65")
    require(int(cmd_all["outcome_window_clamp_trials"]) == 47, "outcome-window clamp count must be 47")
    require(int(cmd_c4["any_trial_clamp_trials"]) == 11 and int(cmd_c4["outcome_window_clamp_trials"]) == 0, "C4 window-binding result mismatch")
    require(len(participants) == 20 and all(float(row["classification_accuracy"]) == 1.0 for row in participants), "participant-level recovery mismatch")
    require(len(robustness) == 12 and all(float(row["classification_accuracy_mean"]) == 1.0 for row in robustness), "quartile robustness mismatch")
    require(layers["D_i^phys"]["status"] == "NOT_INDEPENDENTLY_OBSERVED", "physical layer must remain unobserved")
    require(layers["R_i^cmd"]["status"] == "OBSERVED_AS_SOFTWARE_COMMAND", "command layer must remain software-only")
    require(acceptance["overall_primary_pass"] is True, "primary record-layer criteria must pass")
    require(acceptance["physical_delivery_status"] == "NOT_INDEPENDENTLY_OBSERVED", "acceptance report overstates physical evidence")
    require(provenance["historical_first_five_scanned"] is False, "historical first_five must remain excluded")
    require(provenance["raw_files_modified"] is False, "raw data must be read-only")
    require(all(row["csv_verification"] == "byte_exact" for row in cohort), "all CSV byte hashes must match")
    require(all(row["events_verification"] in {"byte_exact", "canonical_text_exact"} for row in cohort), "event verification failed")
    require(all(row["summary_verification"] in {"byte_exact", "canonical_text_exact"} for row in cohort), "summary verification failed")

    manuscripts = {
        "zh": (BUNDLE / "manuscript_thms_v3_zh.md").read_text(encoding="utf-8"),
        "en": (BUNDLE / "manuscript_thms_v3_en.md").read_text(encoding="utf-8"),
    }
    expected_strings = ["294/294", "98.75", "2.381", "4.957", "5.408", "0.001798", "0.005996", "0.006760", "65/294", "47/294"]
    for language, text in manuscripts.items():
        for value in expected_strings:
            require(value in text, f"{language} manuscript missing traced value {value}")
        require("ETHICS RECORD REQUIRED—DO NOT SUBMIT" in text, f"{language} manuscript missing ethics blocker")
    banned = {
        "zh": ["外部验证", "物理真值恢复", "确认性人体效应", "预注册", "全部原始字节哈希通过"],
        "en": ["external validation", "physical truth recovery", "confirmatory human effect", "preregistered", "all raw byte hashes matched"],
    }
    for language, phrases in banned.items():
        lower = manuscripts[language].lower()
        for phrase in phrases:
            require(phrase.lower() not in lower, f"{language} manuscript contains prohibited phrase: {phrase}")

    verify_not_touched_since(ROOT / "正宫" / "21_framework_first_submission_bundle", datetime(2026, 8, 27))
    verify_prior_bundle(ROOT / "正宫" / "24_framework_validation_submission_bundle_v2")
    verify_not_touched_since(ROOT / "data" / "kfb_timing_formal_v1", datetime(2026, 8, 27))

    for relative, expected_hash in provenance["output_sha256"].items():
        path = ANALYSIS / relative
        require(path.is_file() and sha256(path) == expected_hash, f"analysis output changed after provenance freeze: {relative}")

    return {
        "bundle": str(BUNDLE),
        "participants": 20,
        "planned_trials": 300,
        "evaluable_trials": 294,
        "safety_aborts": 6,
        "classification": "294/294",
        "classification_exact_95_ci": [0.9875311790067285, 1.0],
        "whole_trial_clamps": 65,
        "outcome_window_clamps": 47,
        "physical_delivery": "NOT_INDEPENDENTLY_OBSERVED",
        "prior_bundles_unchanged": True,
        "manuscript_trace_and_claim_check": True,
    }


def deterministic_rerun() -> dict:
    from analyze_kfb_runtime_exposure_v3 import run_analysis
    from analyze_kfb_timing_formal import parse_participants

    data = ROOT / "data" / "kfb_timing_formal_v1" / "participants"
    protocol = ROOT / "正宫" / "23_kfb_timing_pilot" / "frozen_schedule_formal_v1" / "protocol_config_v1.json"
    oracle = ROOT / "正宫" / "23_kfb_timing_pilot" / "frozen_schedule_formal_v1" / "private_oracle" / "oracle.csv"
    with tempfile.TemporaryDirectory() as left_name, tempfile.TemporaryDirectory() as right_name:
        left, right = Path(left_name), Path(right_name)
        participants = parse_participants("F01-F20")
        run_analysis(data, protocol, oracle, participants, left)
        run_analysis(data, protocol, oracle, participants, right)
        left_files = sorted(path.relative_to(left).as_posix() for path in left.rglob("*") if path.is_file())
        right_files = sorted(path.relative_to(right).as_posix() for path in right.rglob("*") if path.is_file())
        require(left_files == right_files, "independent reruns produced different file sets")
        mismatches = [name for name in left_files if sha256(left / name) != sha256(right / name)]
        require(not mismatches, f"independent reruns were not byte-identical: {mismatches}")
        return {"files_compared": len(left_files), "byte_identical": True}


def write_manifest() -> Path:
    manifest_path = BUNDLE / "bundle_manifest_sha256.json"
    entries = {
        path.relative_to(BUNDLE).as_posix(): sha256(path)
        for path in sorted(BUNDLE.rglob("*"))
        if path.is_file() and path != manifest_path
    }
    payload = {"algorithm": "SHA-256", "file_count": len(entries), "files": entries}
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return manifest_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rerun", action="store_true", help="perform two independent byte-identity reruns")
    parser.add_argument("--write-manifest", action="store_true")
    args = parser.parse_args()
    report = verify()
    if args.rerun:
        report["deterministic_rerun"] = deterministic_rerun()
    if args.write_manifest:
        report["manifest"] = str(write_manifest())
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
