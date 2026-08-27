from __future__ import annotations

import hashlib
import itertools
import json
import subprocess
from dataclasses import fields
from pathlib import Path

import numpy as np
import pandas as pd

from evidence_state import EvidenceState, classify_evidence


SCRIPT_DIR = Path(__file__).resolve().parent
BUNDLE = SCRIPT_DIR.parents[1]
FRAMEWORK_BUNDLE = BUNDLE.parent
MY_TEST = FRAMEWORK_BUNDLE.parents[1]
GIT_ROOT = MY_TEST.parent
ANALYSIS = FRAMEWORK_BUNDLE / "03_clean_analysis"
LOGIC_OUT = BUNDLE / "04_logic_and_qa" / "v3"
SUPP_OUT = BUNDLE / "03_supplement" / "v3_data"

ORACLE = SCRIPT_DIR / "controlled_cases.csv"
BASELINE_HASHES = SCRIPT_DIR / "baseline_hashes.json"
OLD_NEW = ANALYSIS / "old_new_trial_metric_comparison.csv"
FIDELITY = ANALYSIS / "trial_level_fidelity_metrics.csv"
MASTER = ANALYSIS / "master_trial_manifest.csv"
INTERACTIVE = FRAMEWORK_BUNDLE / "acquisition_code_snapshot" / "interactive_teleop.py"

CONTRASTS = {
    "EA": ("E", "A"),
    "GA": ("G", "A"),
    "FE": ("F", "E"),
    "FG": ("F", "G"),
}
MODE_CODE = {"default": "A", "force_only": "G", "vision": "E", "vision_force": "F"}

EXPECTED_SELECTION = {
    "EA": {"min": -0.353791, "max": -0.336697, "negative": 64, "all_five": 64},
    "GA": {"min": -0.074218, "max": -0.074218, "negative": 64, "all_five": 64},
    "FE": {"min": -0.067805, "max": -0.000304, "negative": 64, "all_five": 0},
    "FG": {"min": -0.330284, "max": -0.279877, "negative": 64, "all_five": 64},
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def validate_baseline() -> pd.DataFrame:
    payload = json.loads(BASELINE_HASHES.read_text(encoding="utf-8"))
    rows = []
    for relative, expected in payload["files"].items():
        path = BUNDLE / relative
        actual = sha256(path)
        rows.append({
            "relative_path": relative,
            "expected_sha256": expected,
            "actual_sha256": actual,
            "unchanged": int(actual == expected),
        })
    result = pd.DataFrame(rows)
    if not bool(result["unchanged"].all()):
        failed = result.loc[result["unchanged"].eq(0), "relative_path"].tolist()
        raise RuntimeError(f"v1/v2 baseline changed: {failed}")
    return result


def run_controlled_cases() -> pd.DataFrame:
    oracle = pd.read_csv(ORACLE, dtype=str).fillna("")
    observed_rows = []
    for row in oracle.itertuples(index=False):
        state = EvidenceState(
            nominal_spec=row.nominal_spec,
            n_to_c=row.n_to_c,
            c_to_r=row.c_to_r,
            exposure=row.exposure,
            provenance=row.provenance,
            n_to_c_detail=row.n_to_c_detail,
        )
        decision = classify_evidence(state)
        diagnostics = "|".join(decision.diagnostic_codes)
        exact = (
            diagnostics == row.expected_diagnostic_codes
            and decision.nominal_identity_status == row.expected_identity_status
            and decision.comparison_level == row.expected_comparison_level
            and decision.causal_status == "outside_fidelity_framework"
        )
        observed_rows.append({
            **row._asdict(),
            "observed_diagnostic_codes": diagnostics,
            "observed_identity_status": decision.nominal_identity_status,
            "observed_comparison_level": decision.comparison_level,
            "allowed_wording": decision.allowed_wording,
            "prohibited_wording": decision.prohibited_wording,
            "causal_status": decision.causal_status,
            "oracle_exact_match": int(exact),
        })
    result = pd.DataFrame(observed_rows)
    if len(result) != 11 or int(result["oracle_exact_match"].sum()) != 11:
        raise RuntimeError("Controlled perturbation oracle did not pass 11/11 cases")

    state_fields = {item.name for item in fields(EvidenceState)}
    forbidden_state_fields = {"outcome", "effect", "direction", "p_value", "significance"}
    if state_fields & forbidden_state_fields:
        raise RuntimeError(f"Outcome-dependent fields leaked into EvidenceState: {state_fields & forbidden_state_fields}")
    if result["allowed_wording"].str.contains(r"causal effect", case=False, regex=True).any():
        raise RuntimeError("Fidelity decision emitted causal-effect wording")
    return result


def enumerate_record_selections() -> tuple[pd.DataFrame, pd.DataFrame]:
    source = pd.read_csv(OLD_NEW)
    changed = source[source["record_changed"].astype(str).str.lower().isin({"true", "1"})].copy()
    if len(source) != 180 or len(changed) != 6 or changed["trial_key"].nunique() != 6:
        raise RuntimeError(f"Expected 180 logical trials and six changed identities; observed {len(source)} and {len(changed)}")
    changed_keys = changed["trial_key"].tolist()
    bit_for_key = {key: i for i, key in enumerate(changed_keys)}

    rows = []
    for mask in range(2 ** len(changed_keys)):
        trial_rows = []
        selected_old = []
        for row in source.itertuples(index=False):
            bit = bit_for_key.get(row.trial_key)
            use_old = bit is not None and bool(mask & (1 << bit))
            if use_old:
                selected_old.append(row.trial_key)
            metric = (
                row.old_primary_excess_impulse_Ns_0p2_1p0
                if use_old else row.clean_primary_excess_impulse_Ns_0p2_1p0
            )
            parts = str(row.trial_key).split("|")
            trial_rows.append({
                "participant": parts[1],
                "mode_code": MODE_CODE[parts[3]],
                "metric": float(metric),
            })
        participant = (
            pd.DataFrame(trial_rows)
            .groupby(["participant", "mode_code"], as_index=False)["metric"]
            .mean()
        )
        output = {
            "selection_mask": mask,
            "selection_bits": format(mask, "06b"),
            "n_initial_records_selected": len(selected_old),
            "initial_record_trial_keys": json.dumps(selected_old, ensure_ascii=False, separators=(",", ":")),
        }
        for label, (high, low) in CONTRASTS.items():
            pivot = participant.pivot(index="participant", columns="mode_code", values="metric")
            differences = pivot[high] - pivot[low]
            output[f"{label}_mean_difference_Ns"] = float(differences.mean())
            output[f"{label}_negative_participant_count"] = int((differences < 0).sum())
        rows.append(output)

    combinations = pd.DataFrame(rows)
    if len(combinations) != 64 or combinations["selection_mask"].nunique() != 64:
        raise RuntimeError("Record-selection enumeration is not complete and unique")

    summary_rows = []
    for label in CONTRASTS:
        values = combinations[f"{label}_mean_difference_Ns"]
        directions = combinations[f"{label}_negative_participant_count"]
        summary_rows.append({
            "contrast": label,
            "minimum_mean_difference_Ns": float(values.min()),
            "maximum_mean_difference_Ns": float(values.max()),
            "negative_mean_combinations": int((values < 0).sum()),
            "all_five_participants_negative_combinations": int((directions == 5).sum()),
            "minimum_negative_participant_count": int(directions.min()),
            "maximum_negative_participant_count": int(directions.max()),
            "n_unique_mean_differences": int(values.nunique()),
        })
    summary = pd.DataFrame(summary_rows)

    for row in summary.itertuples(index=False):
        expected = EXPECTED_SELECTION[row.contrast]
        checks = [
            np.isclose(row.minimum_mean_difference_Ns, expected["min"], atol=5e-7),
            np.isclose(row.maximum_mean_difference_Ns, expected["max"], atol=5e-7),
            row.negative_mean_combinations == expected["negative"],
            row.all_five_participants_negative_combinations == expected["all_five"],
        ]
        if not all(checks):
            raise RuntimeError(f"Unexpected 64-combination summary for {row.contrast}: {row}")
    return combinations, summary


def audit_case_evidence() -> tuple[pd.DataFrame, dict]:
    fidelity = pd.read_csv(FIDELITY)
    counts = fidelity.groupby("mode_code").size().to_dict()
    if counts != {"A": 45, "E": 45, "F": 45, "G": 45}:
        raise RuntimeError(f"Unexpected mode counts: {counts}")
    if int(fidelity["acquisition_lineage_consistency"].sum()) != 180:
        raise RuntimeError("Exact acquisition provenance failed for one or more selected trials")

    e = fidelity[fidelity["mode_code"].eq("E")].copy()
    e["exposure_fraction"] = e["vision_configuration_outcome_window_overlap"].astype(float)
    e["exposure_class"] = np.where(
        np.isclose(e["exposure_fraction"], 1.0, atol=1e-12),
        "Full",
        np.where(np.isclose(e["exposure_fraction"], 0.0, atol=1e-12), "Zero", "Partial"),
    )
    exposure_counts = e["exposure_class"].value_counts().to_dict()
    if exposure_counts != {"Full": 39, "Zero": 4, "Partial": 2}:
        raise RuntimeError(f"Unexpected E exposure counts: {exposure_counts}")
    e["vision_lock_minus_contact_s"] = e["vision_lock_system_s"] - e["contact_system_s"]
    e["transition_complete_minus_contact_s"] = e["transition_complete_system_s"] - e["contact_system_s"]
    nonfull = e[e["exposure_class"].ne("Full")][[
        "record_id", "participant", "material", "block", "exposure_class", "exposure_fraction",
        "vision_lock_minus_contact_s", "transition_complete_minus_contact_s",
        "vision_lock_to_transition_complete_latency_s",
    ]].sort_values(["exposure_class", "transition_complete_minus_contact_s"])

    zero = nonfull[nonfull["exposure_class"].eq("Zero")]
    partial = nonfull[nonfull["exposure_class"].eq("Partial")]
    evidence = {
        "mode_counts": counts,
        "provenance_valid_trials": 180,
        "e_exposure_counts": exposure_counts,
        "e_zero_lock_minus_contact_range_s": [float(zero["vision_lock_minus_contact_s"].min()), float(zero["vision_lock_minus_contact_s"].max())],
        "e_zero_transition_complete_minus_contact_range_s": [float(zero["transition_complete_minus_contact_s"].min()), float(zero["transition_complete_minus_contact_s"].max())],
        "e_partial_exposure_fractions": sorted(float(value) for value in partial["exposure_fraction"]),
    }
    return nonfull, evidence


def audit_f_clock() -> dict:
    fidelity = pd.read_csv(FIDELITY)
    f = fidelity[fidelity["mode_code"].eq("F")]
    master = pd.read_csv(MASTER)
    commits = master["collection_code_commit"].dropna().astype(str).unique().tolist()
    if len(commits) != 1:
        raise RuntimeError(f"Expected one collection commit, observed {commits}")
    commit = commits[0]

    interactive = INTERACTIVE.read_text(encoding="utf-8")
    protocol = subprocess.run(
        ["git", "-C", str(GIT_ROOT), "show", f"{commit}:my_test/experiment_protocol.py"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout
    signatures = {
        "run_assigns_wall_clock": "now = time.time()" in interactive,
        "wall_clock_passed_to_fusion": "self._update_vision_force_fusion(now)" in interactive,
        "fusion_gate_calls_system_time": "self._timeline.system_time(now) - contact_t < FUSION_CONTACT_DELAY_S" in interactive,
        "timeline_origin_uses_perf_counter": "self.start_perf = time.perf_counter()" in protocol,
        "system_time_subtracts_perf_origin": "return (time.perf_counter() if now is None else now) - self.start_perf" in protocol,
    }
    if not all(signatures.values()):
        raise RuntimeError(f"F clock-domain source signature failed: {signatures}")

    evidence = {
        "collection_code_commit": commit,
        "source_signatures": signatures,
        "n_f_trials": int(len(f)),
        "nominal_plus_0p20_compliant_trials": int(f["nominal_activation_timing_compliance"].sum()),
        "pre_contact_activation_trials": int(f["pre_contact_activation"].sum()),
        "median_contact_to_activation_s": float(f["contact_to_adaptation_latency_s"].median()),
        "median_activation_timing_error_s": float(f["activation_timing_error_s"].median()),
        "interpretation": (
            "The mixed clock predicate makes the nominal delay guard pass once contact exists; "
            "the observed approximately 53-ms activation is the downstream realized timing, "
            "not a delay numerically generated by the clock mismatch."
        ),
    }
    expected = {
        "n_f_trials": 45,
        "nominal_plus_0p20_compliant_trials": 3,
        "pre_contact_activation_trials": 0,
    }
    if any(evidence[key] != value for key, value in expected.items()):
        raise RuntimeError(f"Unexpected F evidence: {evidence}")
    if not np.isclose(evidence["median_contact_to_activation_s"], 0.053273633006, atol=5e-10):
        raise RuntimeError("Unexpected F median activation latency")
    return evidence


def main() -> None:
    LOGIC_OUT.mkdir(parents=True, exist_ok=True)
    SUPP_OUT.mkdir(parents=True, exist_ok=True)

    baseline = validate_baseline()
    controlled = run_controlled_cases()
    combinations, selection_summary = enumerate_record_selections()
    e_nonfull, case_evidence = audit_case_evidence()
    f_clock = audit_f_clock()

    baseline.to_csv(LOGIC_OUT / "baseline_integrity.csv", index=False, encoding="utf-8-sig")
    controlled.to_csv(SUPP_OUT / "controlled_perturbation_results.csv", index=False, encoding="utf-8-sig")
    controlled[[
        "case_id", "case_label", "nominal_spec", "n_to_c", "c_to_r", "exposure", "provenance",
        "observed_diagnostic_codes", "observed_identity_status", "observed_comparison_level",
        "allowed_wording", "prohibited_wording",
    ]].to_csv(LOGIC_OUT / "evidence_decision_matrix.csv", index=False, encoding="utf-8-sig")
    combinations.to_csv(SUPP_OUT / "record_selection_64_combinations.csv", index=False, encoding="utf-8-sig")
    selection_summary.to_csv(SUPP_OUT / "record_selection_summary.csv", index=False, encoding="utf-8-sig")
    e_nonfull.to_csv(SUPP_OUT / "e_nonfull_exposure_mechanisms.csv", index=False, encoding="utf-8-sig")
    (SUPP_OUT / "f_clock_evidence.json").write_text(
        json.dumps(f_clock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    report = {
        "status": "PASS",
        "controlled_perturbation_cases": 11,
        "controlled_oracle_exact_matches": int(controlled["oracle_exact_match"].sum()),
        "record_selection_combinations": int(len(combinations)),
        "record_selection_unique_masks": int(combinations["selection_mask"].nunique()),
        "record_selection_summary": selection_summary.to_dict(orient="records"),
        "case_evidence": case_evidence,
        "f_clock_evidence": f_clock,
        "baseline_files_verified_unchanged": int(baseline["unchanged"].sum()),
        "baseline_files_total": int(len(baseline)),
        "causal_boundary": "Fidelity classification does not by itself authorize causal wording.",
        "validation_boundary": "Internal deterministic discrimination check; not external validation.",
    }
    (LOGIC_OUT / "v3_validation_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

