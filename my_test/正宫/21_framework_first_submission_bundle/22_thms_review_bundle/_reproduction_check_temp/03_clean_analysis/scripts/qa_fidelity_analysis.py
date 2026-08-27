from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


OUT = Path(r"F:\sun\sunhan\my_test\paper2_sci\03_clean_analysis")
FIG = OUT / "figures"
TAB = OUT / "tables"


def main() -> None:
    specs = pd.read_csv(OUT / "intervention_specification.csv")
    fidelity = pd.read_csv(OUT / "trial_level_fidelity_metrics.csv")
    exposure = pd.read_csv(OUT / "outcome_window_exposure.csv")
    summary = pd.read_csv(OUT / "configuration_fidelity_summary.csv")
    interpretation = pd.read_csv(TAB / "nominal_vs_realized_interpretation.csv")
    clean_metrics = pd.read_csv(OUT / "trial_level_metrics.csv")

    checks: list[dict] = []

    def check(name: str, passed: bool, observed: object, expected: object) -> None:
        checks.append({
            "check": name,
            "passed": int(bool(passed)),
            "observed": str(observed),
            "expected": str(expected),
        })
        if not passed:
            raise RuntimeError(f"QA failure: {name}: observed={observed}, expected={expected}")

    check("specification has A/G/E/F", set(specs["mode_code"]) == {"A", "G", "E", "F"}, sorted(specs["mode_code"].tolist()), ["A", "E", "F", "G"])
    check("four specification rows", len(specs) == 4, len(specs), 4)
    check("180 fidelity rows", len(fidelity) == 180, len(fidelity), 180)
    check("180 unique record IDs", fidelity["record_id"].nunique() == 180, fidelity["record_id"].nunique(), 180)
    check("45 trials per mode", fidelity.groupby("mode_code").size().to_dict() == {"A": 45, "E": 45, "F": 45, "G": 45}, fidelity.groupby("mode_code").size().to_dict(), {"A": 45, "E": 45, "F": 45, "G": 45})
    check("exposure keys match fidelity", set(exposure["record_id"]) == set(fidelity["record_id"]), len(set(exposure["record_id"]) ^ set(fidelity["record_id"])), 0)
    check("clean outcome keys match fidelity", set(clean_metrics["record_id"]) == set(fidelity["record_id"]), len(set(clean_metrics["record_id"]) ^ set(fidelity["record_id"])), 0)

    joined = exposure[["record_id", "outcome"]].merge(
        clean_metrics[["record_id", "primary_excess_impulse_Ns_0p2_1p0"]],
        on="record_id", how="inner", validate="one_to_one",
    )
    max_outcome_diff = float(np.max(np.abs(joined["outcome"] - joined["primary_excess_impulse_Ns_0p2_1p0"])))
    check("exposure outcome equals frozen clean outcome", max_outcome_diff <= 1e-12, max_outcome_diff, "<=1e-12")

    check("all clean provenance valid", int(fidelity["acquisition_lineage_consistency"].sum()) == 180, int(fidelity["acquisition_lineage_consistency"].sum()), 180)
    check("all current source hashes verified", int(fidelity[["raw_csv_hash_verified_current", "event_log_hash_verified_current", "summary_hash_verified_current"]].to_numpy().sum()) == 540, int(fidelity[["raw_csv_hash_verified_current", "event_log_hash_verified_current", "summary_hash_verified_current"]].to_numpy().sum()), 540)
    check("all outcome windows observed", int(fidelity["outcome_window_fully_observed"].sum()) == 180, int(fidelity["outcome_window_fully_observed"].sum()), 180)
    check("overlap fractions bounded", bool(((fidelity["outcome_window_overlap"] >= 0) & (fidelity["outcome_window_overlap"] <= 1)).all()), (float(fidelity["outcome_window_overlap"].min()), float(fidelity["outcome_window_overlap"].max())), "[0,1]")

    a = fidelity[fidelity.mode_code == "A"]
    g = fidelity[fidelity.mode_code == "G"]
    e = fidelity[fidelity.mode_code == "E"]
    f = fidelity[fidelity.mode_code == "F"]
    check("A fixed-command pass control", int(a["A_fixed_command_compliance_task_to_end"].sum()) == 45, int(a["A_fixed_command_compliance_task_to_end"].sum()), 45)
    check("G timing error is not computed", g["activation_timing_error_s"].isna().all(), int(g["activation_timing_error_s"].notna().sum()), 0)
    check("G pre-contact count", int(g["pre_contact_activation"].sum()) == 43, int(g["pre_contact_activation"].sum()), 43)
    check("G executable logic compliance", int(g["executable_logic_compliance"].sum()) == 45, int(g["executable_logic_compliance"].sum()), 45)
    check("F pre-contact count", int(f["pre_contact_activation"].sum()) == 0, int(f["pre_contact_activation"].sum()), 0)
    check("F nominal +0.20-s compliance count", int(f["nominal_activation_timing_compliance"].sum()) == 3, int(f["nominal_activation_timing_compliance"].sum()), 3)
    check("F gate clock-domain integrity fails", int(f["intervention_gate_clock_domain_integrity"].sum()) == 0, int(f["intervention_gate_clock_domain_integrity"].sum()), 0)
    check("E transition observed for all trials", int(e["transition_complete_system_s"].notna().sum()) == 45, int(e["transition_complete_system_s"].notna().sum()), 45)
    check("F transition observed for all trials", int(f["transition_complete_system_s"].notna().sum()) == 45, int(f["transition_complete_system_s"].notna().sum()), 45)

    check("summary includes all four modes", set(summary["mode_code"]) == {"A", "G", "E", "F"}, sorted(summary["mode_code"].unique()), ["A", "E", "F", "G"])
    check("interpretation table has nine required rows", len(interpretation) == 9, len(interpretation), 9)
    check("no inferential fishing columns", not any("p_value" in c.lower() or "significance" in c.lower() for c in fidelity.columns), [c for c in fidelity.columns if "p_value" in c.lower() or "significance" in c.lower()], [])

    figure_stems = ["realized_intervention_fidelity_framework", "trial_level_intervention_timing_raster"]
    for stem in figure_stems:
        for suffix in (".png", ".pdf", ".svg"):
            path = FIG / f"{stem}{suffix}"
            check(f"figure exists and nonempty: {path.name}", path.is_file() and path.stat().st_size > 1000, path.stat().st_size if path.is_file() else 0, ">1000 bytes")

    checks_df = pd.DataFrame(checks)
    checks_df.to_csv(TAB / "fidelity_qa_checks.csv", index=False, encoding="utf-8-sig")
    report = {
        "status": "PASS",
        "n_checks": len(checks),
        "n_passed": int(checks_df["passed"].sum()),
        "n_trials": len(fidelity),
        "mode_counts": fidelity.groupby("mode_code").size().to_dict(),
        "source_hashes_verified": int(fidelity[["raw_csv_hash_verified_current", "event_log_hash_verified_current", "summary_hash_verified_current"]].to_numpy().sum()),
        "notes": [
            "No compliant-only subgroup efficacy test was performed.",
            "Existing clean outcome/statistics files were read but not rewritten.",
            "Logged commanded parameters are not independent physical impedance measurements.",
        ],
    }
    (OUT / "fidelity_qa_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
