#!/usr/bin/env python3
"""Verify the THMS v2 bundle and optionally refresh its SHA-256 manifest."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BUNDLE = ROOT / "正宫" / "24_framework_validation_submission_bundle_v2"
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


def verify() -> dict:
    required = [
        BUNDLE / "README.md",
        BUNDLE / "analysis_plan_v2.md",
        BUNDLE / "manuscript_thms_v2_zh.md",
        BUNDLE / "manuscript_thms_v2_en.md",
        ANALYSIS / "analysis_cohort_manifest.csv",
        ANALYSIS / "trial_metrics.csv",
        ANALYSIS / "condition_fidelity_summary.csv",
        ANALYSIS / "quality_and_safety_summary.csv",
        ANALYSIS / "exploratory_contrast_summary.csv",
        ANALYSIS / "validation_acceptance.json",
        ANALYSIS / "analysis_provenance.json",
        ANALYSIS / "figures" / "fig4_protocol_design.png",
        ANALYSIS / "figures" / "fig5_fidelity_recovery.png",
        ANALYSIS / "figures" / "fig6_flow_and_quality.png",
    ]
    for path in required:
        require(path.is_file(), f"missing required bundle file: {path}")

    cohort = read_csv(ANALYSIS / "analysis_cohort_manifest.csv")
    metrics = read_csv(ANALYSIS / "trial_metrics.csv")
    fidelity = read_csv(ANALYSIS / "condition_fidelity_summary.csv")
    quality = read_csv(ANALYSIS / "quality_and_safety_summary.csv")
    acceptance = json.loads((ANALYSIS / "validation_acceptance.json").read_text(encoding="utf-8"))
    provenance = json.loads((ANALYSIS / "analysis_provenance.json").read_text(encoding="utf-8"))
    overall = next(row for row in fidelity if row["condition"] == "OVERALL")
    quality_all = next(row for row in quality if row["condition"] == "OVERALL")

    require(len(cohort) == 300, "cohort manifest must contain 300 trials")
    require(len(metrics) == 300, "trial metrics must contain 300 trials")
    require({row["participant_id"] for row in cohort} == {f"F{index:02d}" for index in range(1, 21)}, "cohort must be exactly F01-F20")
    require(sum(int(row["completed"]) for row in cohort) == 294, "cohort must contain 294 completed trials")
    require(sum(int(row["safety_abort"]) for row in metrics) == 6, "metrics must contain six safety aborts")
    require(int(overall["evaluable_trials"]) == 294, "primary fidelity denominator must be 294")
    require(int(overall["classification_correct"]) == 294, "all 294 evaluable trials must classify correctly")
    require(int(quality_all["haptic_clamped_completed_trials"]) == 65, "completed clamped count must be 65")
    require(acceptance["overall_primary_pass"] is True, "all primary criterion checks must pass")
    require(provenance["historical_first_five_scanned"] is False, "historical first_five must remain excluded")
    require(all(row["csv_verification"] == "byte_exact" for row in cohort), "all CSV byte hashes must pass")
    require(all(row["events_verification"] in {"byte_exact", "canonical_text_exact"} for row in cohort), "event hashes must pass byte or canonical verification")
    require(all(row["summary_verification"] in {"byte_exact", "canonical_text_exact"} for row in cohort), "summary hashes must pass byte or canonical verification")

    expected_strings = ["294/294", "2.381", "4.957", "5.408", "0.001798", "0.005996", "0.006760", "65/294"]
    manuscripts = {
        "zh": (BUNDLE / "manuscript_thms_v2_zh.md").read_text(encoding="utf-8"),
        "en": (BUNDLE / "manuscript_thms_v2_en.md").read_text(encoding="utf-8"),
    }
    for language, text in manuscripts.items():
        for value in expected_strings:
            require(value in text, f"{language} manuscript missing traced result {value}")
        require("ETHICS RECORD REQUIRED—DO NOT SUBMIT" in text, f"{language} manuscript must retain ethics blocker")
    require("提供外部验证" not in manuscripts["zh"], "Chinese manuscript must not claim external validation")
    require("provides external validation" not in manuscripts["en"].lower(), "English manuscript must not claim external validation")
    require("all raw byte hashes matched" not in manuscripts["en"].lower(), "English manuscript must not overclaim byte hashes")

    return {
        "bundle": str(BUNDLE),
        "participants": 20,
        "planned_trials": 300,
        "completed_trials": 294,
        "safety_aborts": 6,
        "classification_correct": 294,
        "primary_pass": True,
        "manuscript_trace_check": True,
        "historical_first_five_scanned": False,
    }


def write_manifest() -> Path:
    entries = {}
    manifest_path = BUNDLE / "bundle_manifest_sha256.json"
    for path in sorted(BUNDLE.rglob("*")):
        if path.is_file() and path != manifest_path:
            entries[path.relative_to(BUNDLE).as_posix()] = sha256(path)
    payload = {"algorithm": "SHA-256", "file_count": len(entries), "files": entries}
    manifest_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-manifest", action="store_true")
    args = parser.parse_args()
    report = verify()
    if args.write_manifest:
        report["manifest"] = str(write_manifest())
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
