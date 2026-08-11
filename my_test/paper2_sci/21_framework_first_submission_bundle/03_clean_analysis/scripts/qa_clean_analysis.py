from __future__ import annotations

import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


OUT = Path(r"F:\sun\sunhan\my_test\paper2_sci\03_clean_analysis")


def exact_sign_flip(values: np.ndarray) -> float:
    x = np.asarray(values, dtype=float)
    observed = abs(float(np.mean(x)))
    samples = [abs(float(np.mean(x * np.asarray(s)))) for s in itertools.product((-1.0, 1.0), repeat=len(x))]
    return float(np.mean(np.asarray(samples) >= observed - 1e-15))


def main() -> None:
    master = pd.read_csv(OUT / "master_trial_manifest.csv")
    lineage = pd.read_csv(OUT / "data_lineage_audit.csv")
    trial = pd.read_csv(OUT / "trial_level_metrics.csv")
    timing = pd.read_csv(OUT / "timing_audit.csv")
    participant = pd.read_csv(OUT / "participant_level_metrics.csv")
    summary = pd.read_csv(OUT / "statistics_summary.csv")
    lopo = pd.read_csv(OUT / "leave_one_participant_out.csv")
    aligned = pd.read_csv(OUT / "contact_aligned_trajectories.csv")
    aligned_summary = pd.read_csv(OUT / "contact_aligned_summary.csv")

    checks: list[dict] = []

    def add(name: str, passed: bool, observed, expected) -> None:
        checks.append({"check": name, "passed": int(bool(passed)), "observed": str(observed), "expected": str(expected)})

    add("master_rows", len(master) == 186, len(master), 186)
    add("master_unique_trial_keys", master["trial_key"].nunique() == 180, master["trial_key"].nunique(), 180)
    add("main_clean_rows", master["included_main_clean"].sum() == 180, master["included_main_clean"].sum(), 180)
    add("excluded_known_errors", master["analysis_role"].eq("excluded_known_error").sum() == 6, master["analysis_role"].eq("excluded_known_error").sum(), 6)
    add("valid_replacements", master["analysis_role"].eq("main_valid_replacement").sum() == 6, master["analysis_role"].eq("main_valid_replacement").sum(), 6)
    add("all_raw_triplets_verified", lineage["all_triplet_files_verified"].eq(1).all(), lineage["all_triplet_files_verified"].sum(), 186)
    add("trial_rows", len(trial) == 180, len(trial), 180)
    add("trial_unique_record_ids", trial["record_id"].nunique() == 180, trial["record_id"].nunique(), 180)
    add("trial_unique_keys", trial["trial_key"].nunique() == 180, trial["trial_key"].nunique(), 180)
    add("mode_balance", trial.groupby("mode").size().eq(45).all(), trial.groupby("mode").size().to_dict(), "45 per mode")
    add("participant_balance", trial.groupby("participant").size().eq(36).all(), trial.groupby("participant").size().to_dict(), "36 per participant")
    add("core_metric_complete", trial[["primary_excess_impulse_Ns_0p2_1p0", "initial_peak_force_N_0_0p2", "approach_time_s", "total_task_time_s", "success"]].notna().all().all(), int(trial[["primary_excess_impulse_Ns_0p2_1p0", "initial_peak_force_N_0_0p2", "approach_time_s", "total_task_time_s", "success"]].isna().sum().sum()), 0)
    add("timing_rows", len(timing) == 180, len(timing), 180)
    add("all_csv_time_monotonic", timing["csv_system_time_monotonic"].eq(1).all(), timing["csv_system_time_monotonic"].sum(), 180)
    add("event_times_in_csv_range", timing["event_times_within_csv_range"].eq(1).all(), timing["event_times_within_csv_range"].sum(), 180)
    add("participant_rows", len(participant) == 20, len(participant), 20)
    add("participant_mode_balance", participant.groupby("participant").size().eq(4).all(), participant.groupby("participant").size().to_dict(), "4 modes per participant")
    add("statistics_rows", len(summary) == 16, len(summary), 16)
    add("statistics_use_n5", summary["n_participants"].eq(5).all(), summary["n_participants"].unique().tolist(), [5])
    add("lopo_rows", len(lopo) == 80, len(lopo), 80)
    add("aligned_rows", len(aligned) == 180 * 201, len(aligned), 180 * 201)
    add("aligned_summary_rows", len(aligned_summary) == 4 * 201, len(aligned_summary), 4 * 201)

    metric = "primary_excess_impulse_Ns_0p2_1p0"
    wide = participant.pivot(index="participant", columns="mode", values=metric)
    for contrast, mode2, mode1 in [
        ("E-A", "vision", "default"),
        ("G-A", "force_only", "default"),
        ("F-E", "vision_force", "vision"),
        ("F-G", "vision_force", "force_only"),
    ]:
        diff = (wide[mode2] - wide[mode1]).to_numpy(float)
        row = summary[(summary["metric"].eq(metric)) & (summary["contrast"].eq(contrast))].iloc[0]
        add(f"{contrast}_mean_recomputed", np.isclose(np.mean(diff), row["raw_mean_difference"], atol=1e-12), np.mean(diff), row["raw_mean_difference"])
        add(f"{contrast}_t_p_recomputed", np.isclose(stats.ttest_1samp(diff, 0).pvalue, row["paired_t_p"], atol=1e-12), stats.ttest_1samp(diff, 0).pvalue, row["paired_t_p"])
        add(f"{contrast}_signflip_recomputed", np.isclose(exact_sign_flip(diff), row["exact_sign_flip_p"], atol=1e-12), exact_sign_flip(diff), row["exact_sign_flip_p"])

    figure_names = [
        "participant_level_primary_outcome.png",
        "force_activation_timing_audit.png",
        "contact_aligned_force_stiffness_clean.png",
    ]
    for name in figure_names:
        path = OUT / "figures" / name
        add(f"figure_{name}", path.is_file() and path.stat().st_size > 0, path.stat().st_size if path.exists() else 0, ">0 bytes")
    add("readme_exists", (OUT / "README.md").is_file(), (OUT / "README.md").is_file(), True)

    report = pd.DataFrame(checks)
    report.to_csv(OUT / "tables" / "qa_checks.csv", index=False, encoding="utf-8-sig")
    passed = int(report["passed"].sum())
    result = {"checks": len(report), "passed": passed, "failed": int(len(report) - passed)}
    (OUT / "qa_report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    if result["failed"]:
        print(report[report["passed"].eq(0)].to_string(index=False))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
