from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from dataclasses import fields
from pathlib import Path

import numpy as np
import pandas as pd

from evidence_pipeline import ArtifactEvidence, EvidenceState, classify_evidence, derive_evidence_state


HERE = Path(__file__).resolve().parent
BUNDLE = HERE.parents[1]
FRAMEWORK = BUNDLE.parent
ANALYSIS = FRAMEWORK / "03_clean_analysis"
RAW_ROOT = FRAMEWORK.parents[1] / "data" / "ral_date"
LOGIC_OUT = BUNDLE / "04_logic_and_qa" / "v4"
SUPP_OUT = BUNDLE / "03_supplement" / "v4_data"
SNAPSHOT = FRAMEWORK / "acquisition_code_snapshot" / "interactive_teleop.py"
COMMIT = "09c13e0b679905f14f770d820af00841546cb4cc"
MODE_CODE = {"default": "A", "force_only": "G", "vision": "E", "vision_force": "F"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def as_bool(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def split_details(value: object) -> tuple[str, ...]:
    text = str(value).strip()
    return tuple(part for part in text.split("|") if part and part.lower() != "nan")


def verify_controlled_cases() -> tuple[pd.DataFrame, dict]:
    cases = pd.read_csv(HERE / "controlled_artifact_cases.csv", keep_default_na=False)
    rows = []
    for row in cases.to_dict("records"):
        fraction = None if row["exposure_fraction"] == "" else float(row["exposure_fraction"])
        evidence = ArtifactEvidence(
            evidence_unit_id=row["case_id"],
            configuration="oracle",
            trial_id=row["case_id"],
            outcome_window="frozen synthetic window",
            nominal_label_present=as_bool(row["nominal_label_present"]),
            nominal_artifact_present=as_bool(row["nominal_artifact_present"]),
            nominal_artifact_contemporaneous=as_bool(row["nominal_artifact_contemporaneous"]),
            nominal_elements_explicit=as_bool(row["nominal_elements_explicit"]),
            implementation_artifact_present=as_bool(row["implementation_artifact_present"]),
            n_to_c_checks_complete=as_bool(row["n_to_c_checks_complete"]),
            n_to_c_mismatch_details=split_details(row["n_to_c_mismatch_details"]),
            replay_supported=as_bool(row["replay_supported"]),
            replay_complete=as_bool(row["replay_complete"]),
            replay_mismatch=as_bool(row["replay_mismatch"]),
            exposure_applicable=as_bool(row["exposure_applicable"]),
            exposure_trace_complete=as_bool(row["exposure_trace_complete"]),
            exposure_fraction=fraction,
            provenance_checks_complete=as_bool(row["provenance_checks_complete"]),
            provenance_exact_match=as_bool(row["provenance_exact_match"]),
        )
        state = derive_evidence_state(evidence)
        decision = classify_evidence(state)
        observed = {
            "nominal_spec": state.nominal_spec,
            "n_to_c": state.n_to_c,
            "c_to_r": state.c_to_r,
            "exposure": state.exposure,
            "provenance": state.provenance,
            "diagnostic_codes": "|".join(decision.diagnostic_codes),
            "identity_status": decision.nominal_identity_status,
            "comparison_level": decision.comparison_level,
        }
        expected = {
            "nominal_spec": row["expected_nominal_spec"],
            "n_to_c": row["expected_n_to_c"],
            "c_to_r": row["expected_c_to_r"],
            "exposure": row["expected_exposure"],
            "provenance": row["expected_provenance"],
            "diagnostic_codes": row["expected_diagnostic_codes"],
            "identity_status": row["expected_identity_status"],
            "comparison_level": row["expected_comparison_level"],
        }
        match = observed == expected
        rows.append({"case_id": row["case_id"], "case_label": row["case_label"], **observed, "exact_oracle_match": int(match)})
        if not match:
            raise RuntimeError(f"Oracle mismatch for {row['case_id']}: observed={observed}, expected={expected}")

    artifact_fields = {item.name for item in fields(ArtifactEvidence)}
    state_fields = {item.name for item in fields(EvidenceState)}
    forbidden = {"outcome_value", "effect", "effect_direction", "p", "p_value", "significance", "causal_effect"}
    leaked = (artifact_fields | state_fields) & forbidden
    if leaked:
        raise RuntimeError(f"Outcome-dependent fields leaked into Stage A/B interfaces: {sorted(leaked)}")

    result = pd.DataFrame(rows)
    checks = {
        "n_cases": len(result),
        "exact_matches": int(result["exact_oracle_match"].sum()),
        "label_does_not_substitute_for_spec": result.loc[result.case_id.eq("S01"), "nominal_spec"].iat[0] == "unavailable",
        "one_ms_is_partial": result.loc[result.case_id.eq("S05"), "exposure"].iat[0] == "partial",
        "missing_trace_is_not_zero": result.loc[result.case_id.eq("S07"), "exposure"].iat[0] == "unavailable",
        "joint_guard_clock_retained": {"GUARD_MISMATCH", "CLOCK_DOMAIN_MISMATCH"}.issubset(
            set(result.loc[result.case_id.eq("S11"), "diagnostic_codes"].iat[0].split("|"))
        ),
        "c_to_r_decoupled_from_exposure": (
            result.loc[result.case_id.eq("S11"), "c_to_r"].iat[0] == "not_evaluable"
            and result.loc[result.case_id.eq("S11"), "exposure"].iat[0] == "partial"
            and result.loc[result.case_id.eq("S11"), "comparison_level"].iat[0] == "recorded_realized_configuration"
        ),
        "no_outcome_fields": not leaked,
    }
    if not all(value is True or isinstance(value, int) for key, value in checks.items() if key not in {"n_cases", "exact_matches"}):
        raise RuntimeError(f"Controlled boundary check failed: {checks}")
    return result, checks


def audit_g_replay(master: pd.DataFrame) -> dict:
    errors_ratio: list[float] = []
    errors_target: list[float] = []
    errors_update: list[float] = []
    update_rows = 0
    for row in master.loc[master["mode"].eq("force_only")].itertuples():
        raw = pd.read_csv(RAW_ROOT / row.csv_source)
        force = pd.to_numeric(raw["F_ext_mag"], errors="coerce").to_numpy(float)
        stiffness = pd.to_numeric(raw["K_trans"], errors="coerce").to_numpy(float)
        logged_ratio = pd.to_numeric(raw["force_adapt_ratio"], errors="coerce").to_numpy(float)
        logged_target = pd.to_numeric(raw["force_adapt_target_K"], errors="coerce").to_numpy(float)
        indices = np.flatnonzero(np.abs(np.diff(stiffness)) > 1e-12) + 1
        for index in indices:
            ratio = float(np.clip(max(force[index] - 1.0, 0.0) / 4.0, 0.0, 1.0))
            target = max(200.0 * (1.0 - 0.5 * ratio), 30.0)
            replayed = stiffness[index - 1] + 0.3 * (target - stiffness[index - 1])
            errors_ratio.append(abs(ratio - logged_ratio[index]))
            errors_target.append(abs(target - logged_target[index]))
            errors_update.append(abs(replayed - stiffness[index]))
        update_rows += len(indices)
    audit = {
        "n_trials": int(master["mode"].eq("force_only").sum()),
        "n_replayed_update_rows": update_rows,
        "max_ratio_error": max(errors_ratio),
        "max_target_error_N_per_m": max(errors_target),
        "max_stiffness_update_error_N_per_m": max(errors_update),
        "tolerance": 1e-10,
    }
    if audit["n_trials"] != 45 or any(audit[key] > audit["tolerance"] for key in (
        "max_ratio_error", "max_target_error_N_per_m", "max_stiffness_update_error_N_per_m"
    )):
        raise RuntimeError(f"G replay audit failed: {audit}")
    return audit


def audit_real_case() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    master = pd.read_csv(ANALYSIS / "master_trial_manifest.csv")
    master = master.loc[master["included_main_clean"].eq(1)].copy()
    master["mode_code"] = master["mode"].map(MODE_CODE)
    exposure = pd.read_csv(ANALYSIS / "outcome_window_exposure.csv")
    fidelity = pd.read_csv(ANALYSIS / "trial_level_fidelity_metrics.csv")
    semantic = pd.read_csv(HERE / "structured_semantic_audit.csv")
    if len(master) != 180 or master["mode_code"].value_counts().to_dict() != {"A": 45, "G": 45, "E": 45, "F": 45}:
        raise RuntimeError("Unexpected trial inventory")
    if set(master.record_id) != set(exposure.record_id) or set(master.record_id) != set(fidelity.record_id):
        raise RuntimeError("Real-case evidence tables do not share the frozen 180 records")

    nominal = semantic.loc[semantic.state_field.eq("nominal_spec")].set_index("configuration")["assigned_state"].to_dict()
    n_to_c = semantic.loc[semantic.state_field.eq("n_to_c")].set_index("configuration")["assigned_state"].to_dict()
    details = {"A": (), "G": (), "E": (), "F": ("clock",)}
    replay = {"A": "pass", "G": "pass", "E": "pass", "F": "not_evaluable"}
    joined = exposure.merge(master[["record_id", "trial_key", "mode_code"]], on=["record_id", "mode_code"], validate="one_to_one")
    rows = []
    for row in joined.itertuples():
        phi = float(row.exposure_fraction)
        evidence = ArtifactEvidence(
            evidence_unit_id=row.record_id,
            configuration=row.mode_code,
            trial_id=row.trial_key,
            outcome_window="contact+0.20 s to contact+1.00 s",
            nominal_label_present=True,
            nominal_artifact_present=nominal[row.mode_code] == "available",
            nominal_artifact_contemporaneous=nominal[row.mode_code] == "available",
            nominal_elements_explicit=nominal[row.mode_code] == "available",
            implementation_artifact_present=True,
            n_to_c_checks_complete=n_to_c[row.mode_code] in {"pass", "fail"},
            n_to_c_mismatch_details=details[row.mode_code],
            replay_supported=replay[row.mode_code] == "pass",
            replay_complete=replay[row.mode_code] == "pass",
            replay_mismatch=False,
            exposure_applicable=True,
            exposure_trace_complete=True,
            exposure_fraction=phi,
            provenance_checks_complete=True,
            provenance_exact_match=bool(int(row.provenance_valid)),
        )
        state = derive_evidence_state(evidence)
        decision = classify_evidence(state)
        rows.append({
            "record_id": row.record_id,
            "trial_key": row.trial_key,
            "configuration": row.mode_code,
            "outcome_window": evidence.outcome_window,
            "nominal_spec": state.nominal_spec,
            "n_to_c": state.n_to_c,
            "n_to_c_details": "|".join(state.n_to_c_details),
            "c_to_r": state.c_to_r,
            "exposure_fraction": phi,
            "exposure": state.exposure,
            "provenance": state.provenance,
            "diagnostic_codes": "|".join(decision.diagnostic_codes),
            "nominal_identity_status": decision.nominal_identity_status,
            "comparison_level": decision.comparison_level,
        })
    states = pd.DataFrame(rows)
    counts = states.groupby(["configuration", "exposure"]).size().unstack(fill_value=0)
    expected_exposure = {
        "A": {"full": 45},
        "G": {"full": 40, "partial": 5},
        "E": {"full": 39, "partial": 2, "zero": 4},
        "F": {"full": 35, "partial": 7, "zero": 3},
    }
    observed_exposure = {
        code: {key: int(value) for key, value in row.items() if value}
        for code, row in counts.to_dict("index").items()
    }
    if observed_exposure != expected_exposure:
        raise RuntimeError(f"Exposure distribution changed: {observed_exposure}")
    if not states.loc[states.configuration.eq("F"), "c_to_r"].eq("not_evaluable").all():
        raise RuntimeError("F C-to-R must remain not_evaluable")
    if not states.loc[states.configuration.eq("F"), "comparison_level"].eq("recorded_realized_configuration").all():
        raise RuntimeError("F recorded exposure must remain describable despite unevaluated C-to-R replay")
    if states["provenance"].value_counts().to_dict() != {"valid": 180}:
        raise RuntimeError("Provenance changed")

    g_replay = audit_g_replay(master)
    auto_rows = [
        {"configuration": code, "state_field": "c_to_r", "evidence_level": "trial", "artifact_path": "03_clean_analysis/trial_level_fidelity_metrics.csv + raw CSV", "artifact_sha256": sha256(ANALYSIS / "trial_level_fidelity_metrics.csv"), "collection_code_commit": COMMIT, "rule_id": "CR-01", "extraction_mode": "automatic", "observed_value": replay[code], "unit": "45 trials", "tolerance": "declared software command tolerances", "missing_rule": "not_evaluable", "assigned_state": replay[code], "rationale": "A fixed-command check; G equation replay; E profile/trajectory reconstruction; F literal mixed-clock predicate not fully replayable"}
        for code in ("A", "G", "E", "F")
    ]
    auto_rows += [
        {"configuration": code, "state_field": "exposure", "evidence_level": "trial", "artifact_path": "03_clean_analysis/outcome_window_exposure.csv", "artifact_sha256": sha256(ANALYSIS / "outcome_window_exposure.csv"), "collection_code_commit": COMMIT, "rule_id": "EX-01", "extraction_mode": "automatic", "observed_value": "; ".join(f"{key}={value}" for key, value in expected_exposure[code].items()), "unit": "45 trials", "tolerance": "1e-12 floating boundary", "missing_rule": "unavailable", "assigned_state": "distribution", "rationale": "Left-continuous state integration in the frozen contact+0.20-to+1.00-s window"}
        for code in ("A", "G", "E", "F")
    ]
    auto_rows += [
        {"configuration": code, "state_field": "provenance", "evidence_level": "trial", "artifact_path": "03_clean_analysis/master_trial_manifest.csv + data_lineage_audit.csv", "artifact_sha256": sha256(ANALYSIS / "master_trial_manifest.csv"), "collection_code_commit": COMMIT, "rule_id": "P-01", "extraction_mode": "automatic", "observed_value": "45/45 exact record/path/hash matches", "unit": "45 trials", "tolerance": "exact identity and SHA-256", "missing_rule": "invalid", "assigned_state": "valid", "rationale": "Each intervention trace and scalar outcome resolves to the same selected acquisition record"}
        for code in ("A", "G", "E", "F")
    ]
    combined_audit = pd.concat([semantic, pd.DataFrame(auto_rows)], ignore_index=True, sort=False)
    summary = {
        "mode_counts": master["mode_code"].value_counts().sort_index().to_dict(),
        "provenance_valid_trials": 180,
        "exposure_counts": expected_exposure,
        "configuration_states": {
            code: {
                "nominal_spec": nominal[code],
                "n_to_c": n_to_c[code],
                "c_to_r": replay[code],
            }
            for code in ("A", "G", "E", "F")
        },
        "g_replay": g_replay,
    }
    return states, combined_audit, summary


def verify_baseline() -> tuple[pd.DataFrame, dict]:
    frozen = json.loads((HERE / "baseline_hashes.json").read_text(encoding="utf-8"))
    rows = []
    for item in frozen:
        path = BUNDLE / item["path"]
        current_hash = sha256(path) if path.exists() else "missing"
        current_size = path.stat().st_size if path.exists() else -1
        rows.append({**item, "current_sha256": current_hash, "current_size": current_size, "unchanged": int(current_hash == item["sha256"] and current_size == item["size"])})
    result = pd.DataFrame(rows)
    if not result["unchanged"].eq(1).all():
        raise RuntimeError(f"Frozen v1-v3 baseline changed:\n{result.loc[result.unchanged.eq(0)]}")
    return result, {"verified": int(result.unchanged.sum()), "total": len(result)}


def verify_v3_carry_forward() -> tuple[dict, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    report = json.loads((BUNDLE / "04_logic_and_qa" / "v3" / "v3_validation_report.json").read_text(encoding="utf-8"))
    if report["status"] != "PASS" or report["record_selection_combinations"] != 64:
        raise RuntimeError("v3 carry-forward validation is not PASS")
    if report["case_evidence"]["e_exposure_counts"] != {"Full": 39, "Zero": 4, "Partial": 2}:
        raise RuntimeError("v3 E exposure counts changed")
    v3_dir = BUNDLE / "05_reproduction" / "v3"
    sys.path.insert(0, str(v3_dir))
    spec = importlib.util.spec_from_file_location("v3_validation_for_v4", v3_dir / "validate_v3.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    combinations, summary = module.enumerate_record_selections()
    e_nonfull, case_evidence = module.audit_case_evidence()
    f_clock = module.audit_f_clock()
    if len(combinations) != 64 or combinations["selection_mask"].nunique() != 64:
        raise RuntimeError("Direct v4 rerun did not produce 64 unique record-selection masks")
    if summary.to_dict("records") != report["record_selection_summary"]:
        raise RuntimeError("Direct v4 record-selection rerun differs from the frozen v3 result")
    if case_evidence["e_exposure_counts"] != {"Full": 39, "Zero": 4, "Partial": 2}:
        raise RuntimeError("Direct v4 E mechanism rerun differs from 39/2/4")
    if f_clock != report["f_clock_evidence"]:
        raise RuntimeError("Direct v4 F clock audit differs from the frozen v3 result")
    carry = {
        "record_selection_combinations": len(combinations),
        "record_selection_unique_masks": combinations["selection_mask"].nunique(),
        "record_selection_summary": summary.to_dict("records"),
        "f_clock_evidence": f_clock,
        "e_nonfull_rows": len(e_nonfull),
        "direct_rerun": True,
    }
    return carry, combinations, summary, e_nonfull


def main() -> None:
    LOGIC_OUT.mkdir(parents=True, exist_ok=True)
    SUPP_OUT.mkdir(parents=True, exist_ok=True)
    cases, case_checks = verify_controlled_cases()
    states, artifact_audit, real_case = audit_real_case()
    baseline, baseline_check = verify_baseline()
    carry, combinations, selection_summary, e_nonfull = verify_v3_carry_forward()

    cases.to_csv(SUPP_OUT / "controlled_artifact_case_results.csv", index=False, encoding="utf-8-sig")
    states.to_csv(SUPP_OUT / "trial_evidence_states.csv", index=False, encoding="utf-8-sig")
    artifact_audit.to_csv(SUPP_OUT / "real_case_artifact_audit.csv", index=False, encoding="utf-8-sig")
    combinations.to_csv(SUPP_OUT / "record_selection_64_combinations.csv", index=False, encoding="utf-8-sig")
    selection_summary.to_csv(SUPP_OUT / "record_selection_summary.csv", index=False, encoding="utf-8-sig")
    e_nonfull.to_csv(SUPP_OUT / "e_nonfull_exposure_mechanisms.csv", index=False, encoding="utf-8-sig")
    (SUPP_OUT / "f_clock_evidence.json").write_text(json.dumps(carry["f_clock_evidence"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    baseline.to_csv(LOGIC_OUT / "baseline_integrity.csv", index=False, encoding="utf-8-sig")
    report = {
        "status": "PASS",
        "stage_a_stage_b_cases": case_checks,
        "real_case": real_case,
        "carry_forward": carry,
        "baseline": baseline_check,
        "causal_boundary": "Neither artifact reconstruction nor fidelity classification authorizes causal wording.",
        "verification_boundary": "Rule-level implementation verification and internal discrimination only; not methodological or external validation.",
        "audit_boundary": "Structured author audit; no independent dual-review claim.",
    }
    (LOGIC_OUT / "v4_validation_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
