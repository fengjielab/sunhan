#!/usr/bin/env python3
"""V3.1 human-variability stress test for record-layer runtime exposure.

The locked formal cohort remains F01-F20. Human input, coupled trajectories,
and saturation background are participant-level stressors; they are not treated
as trial-level independent observations or as intrinsic participant traits.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Sequence

import numpy as np
from scipy.stats import rankdata

import analyze_kfb_timing_formal as base
import analyze_kfb_runtime_exposure_v3 as v3


BOOTSTRAP_SEED = 20260827
BOOTSTRAP_REPLICATES = 10_000
TIMING_MAE_LIMIT_S = 0.020
EXPOSURE_MAE_LIMIT = 0.020
STRESSORS = (
    ("approach_duration", "approach_duration_mean_s", "s", "coupled task timing"),
    ("omega_path", "approach_omega_path_mean_m", "m", "human-input-related trajectory"),
    ("panda_path", "approach_robot_path_mean_m", "m", "coupled human-machine trajectory"),
    ("panda_peak_speed", "approach_robot_peak_speed_mean_m_s", "m/s", "coupled human-machine trajectory"),
    ("internal_force_impulse", "force_impulse_mean_Ns", "N*s", "coupled interaction estimate"),
    ("whole_trial_clamp_rate", "any_trial_clamp_rate", "proportion", "condition-and-operator interaction background"),
)


def participant_human_variability(metrics: list[dict]) -> list[dict]:
    output = []
    for participant in sorted({row["participant_id"] for row in metrics}):
        selected = [row for row in metrics if row["participant_id"] == participant]
        complete = [row for row in selected if int(row["fidelity_evaluable"]) == 1]
        timing = [abs(base.finite_float(row["onset_error_s"])) for row in complete]
        exposure = [abs(base.finite_float(row["phi_error"])) for row in complete]
        output.append({
            "participant_id": participant,
            "planned_trials": len(selected),
            "evaluable_trials": len(complete),
            "classification_accuracy": base.mean(int(row["classification_correct"]) for row in complete),
            "timing_mae_s": base.mean(timing),
            "timing_mae_fraction_of_limit": base.mean(timing) / TIMING_MAE_LIMIT_S,
            "exposure_mae": base.mean(exposure),
            "exposure_mae_fraction_of_limit": base.mean(exposure) / EXPOSURE_MAE_LIMIT,
            "approach_duration_mean_s": base.mean(base.finite_float(row["approach_duration_s"]) for row in complete),
            "approach_duration_min_s": min(base.finite_float(row["approach_duration_s"]) for row in complete),
            "approach_duration_max_s": max(base.finite_float(row["approach_duration_s"]) for row in complete),
            "approach_omega_path_mean_m": base.mean(base.finite_float(row["approach_omega_path_m"]) for row in complete),
            "approach_robot_path_mean_m": base.mean(base.finite_float(row["approach_robot_path_m"]) for row in complete),
            "approach_robot_peak_speed_mean_m_s": base.mean(base.finite_float(row["approach_robot_peak_speed_m_s"]) for row in complete),
            "force_impulse_mean_Ns": base.mean(base.finite_float(row["excess_force_impulse_Ns"]) for row in complete),
            "any_trial_clamp_rate": base.mean(int(row["haptic_clamped_any"]) for row in complete),
            "outcome_window_clamp_trial_rate": base.mean(int(row["haptic_clamped_window_any"]) for row in complete),
            "outcome_window_clamp_fraction_mean": base.mean(base.finite_float(row["haptic_clamped_window_fraction"]) for row in complete),
            "analysis_unit": "participant",
        })
    return output


def quartiles(values: Sequence[float]) -> tuple[float, float, float]:
    return (
        base.percentile(values, 0.25),
        base.percentile(values, 0.50),
        base.percentile(values, 0.75),
    )


def human_variability_ranges(participants: list[dict], metrics: list[dict]) -> list[dict]:
    definitions = list(STRESSORS) + [
        ("outcome_window_clamp_trial_rate", "outcome_window_clamp_trial_rate", "proportion", "condition-and-operator interaction background"),
    ]
    rows = []
    for name, key, unit, category in definitions:
        values = [base.finite_float(row[key]) for row in participants]
        q1, median, q3 = quartiles(values)
        rows.append({
            "stressor": name,
            "participant_count": len(values),
            "unit": unit,
            "participant_mean_min": min(values),
            "participant_mean_q1": q1,
            "participant_mean_median": median,
            "participant_mean_q3": q3,
            "participant_mean_max": max(values),
            "participant_mean_iqr": q3 - q1,
            "evidence_category": category,
            "interpretation_guard": "descriptive stressor; not an intrinsic participant trait",
        })
    complete = [row for row in metrics if int(row["fidelity_evaluable"]) == 1]
    durations = [base.finite_float(row["approach_duration_s"]) for row in complete]
    rows.append({
        "stressor": "approach_duration_all_trials",
        "participant_count": 20,
        "unit": "s",
        "participant_mean_min": min(durations),
        "participant_mean_q1": base.percentile(durations, .25),
        "participant_mean_median": base.percentile(durations, .50),
        "participant_mean_q3": base.percentile(durations, .75),
        "participant_mean_max": max(durations),
        "participant_mean_iqr": base.percentile(durations, .75) - base.percentile(durations, .25),
        "evidence_category": "trial-level envelope only",
        "interpretation_guard": "range only; trials are not independent human units",
    })
    return rows


def spearman_stat(x: Sequence[float], y: Sequence[float]) -> float:
    rx = np.asarray(rankdata(x), dtype=float)
    ry = np.asarray(rankdata(y), dtype=float)
    if np.std(rx) == 0 or np.std(ry) == 0:
        return math.nan
    return float(np.corrcoef(rx, ry)[0, 1])


def human_variability_associations(participants: list[dict]) -> tuple[list[dict], dict]:
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    n = len(participants)
    resample_indices = rng.integers(0, n, size=(BOOTSTRAP_REPLICATES, n))
    outcomes = (
        ("timing_mae", "timing_mae_s"),
        ("exposure_mae", "exposure_mae"),
    )
    output = []
    for stressor, key, unit, category in STRESSORS:
        x = np.asarray([base.finite_float(row[key]) for row in participants], dtype=float)
        for outcome, outcome_key in outcomes:
            y = np.asarray([base.finite_float(row[outcome_key]) for row in participants], dtype=float)
            observed = spearman_stat(x, y)
            boot = []
            for indices in resample_indices:
                value = spearman_stat(x[indices], y[indices])
                if math.isfinite(value):
                    boot.append(value)
            output.append({
                "stressor": stressor,
                "stressor_unit": unit,
                "evidence_category": category,
                "outcome": outcome,
                "participant_count": n,
                "spearman_rho": observed,
                "bootstrap_ci_low": base.percentile(boot, .025),
                "bootstrap_ci_high": base.percentile(boot, .975),
                "valid_bootstrap_replicates": len(boot),
                "p_value_computed": 0,
                "analysis_role": "descriptive continuous robustness; no significance screening",
            })
    provenance = {
        "analysis_unit": "participant",
        "participant_count": n,
        "random_generator": "numpy.default_rng/PCG64",
        "seed": BOOTSTRAP_SEED,
        "requested_replicates": BOOTSTRAP_REPLICATES,
        "interval": "2.5th and 97.5th percentiles of valid participant-resampled Spearman statistics",
        "p_values_computed": False,
        "classification_association_computed": False,
        "classification_reason": "all 20 participant accuracies equal 1.0 (ceiling)",
    }
    return output, provenance


def retrospective_rows(path: Path) -> list[dict]:
    rows = base.read_csv(path)
    if len(rows) != 180 or {row["mode_code"] for row in rows} != {"A", "E", "F", "G"}:
        raise RuntimeError("retrospective source must contain 180 locked A/E/F/G trials")
    return rows


def retrospective_summary(rows: list[dict]) -> list[dict]:
    return [
        {"configuration": "A", "nominal_interpretation": "fixed reference", "runtime_evidence": "45/45 fixed recorded state", "key_discrepancy": "no major timing discrepancy identified", "evidence_admissible_interpretation": "reference configuration"},
        {"configuration": "G", "nominal_interpretation": "post-contact force adaptation", "runtime_evidence": "45/45 followed executable rule", "key_discrepancy": "43/45 activated before contact", "evidence_admissible_interpretation": "cannot represent isolated post-contact force effect"},
        {"configuration": "E", "nominal_interpretation": "vision-enabled bundled condition", "runtime_evidence": "39 full / 2 partial / 4 zero visual exposure", "key_discrepancy": "heterogeneous outcome-window exposure", "evidence_admissible_interpretation": "bundled configuration with heterogeneous exposure"},
        {"configuration": "F", "nominal_interpretation": "vision plus +0.20-s adaptive gate", "runtime_evidence": "3/45 met timing; 35/7/3 full/partial/zero combined exposure", "key_discrepancy": "nominal timing largely not realized", "evidence_admissible_interpretation": "cannot represent clean incremental +0.20-s effect"},
    ]


def setup_plotting():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    matplotlib.rcParams.update({
        "font.size": 9,
        "axes.titlesize": 9,
        "axes.labelsize": 9,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 8,
        "svg.hashsalt": "runtime-exposure-v3-1",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })
    return plt


def save_figure(fig, figures: Path, stem: str) -> None:
    fig.savefig(figures / f"{stem}.png", dpi=300, bbox_inches="tight")
    fig.savefig(figures / f"{stem}.svg", bbox_inches="tight", metadata={"Date": None})
    fig.savefig(figures / f"{stem}.pdf", bbox_inches="tight", metadata={"CreationDate": None, "ModDate": None})


def figure1_framework(figures: Path) -> None:
    plt = setup_plotting()
    from matplotlib.patches import FancyBboxPatch
    fig, ax = plt.subplots(figsize=(7.16, 3.30))
    ax.axis("off")
    xs = [.018, .213, .408, .620, .820]
    widths = [.145, .145, .165, .150, .145]
    labels = ["$N_m$\nNominal\nspecification", "$C_m$\nImplementation\nlogic", "$R_i^{rec}$\nRecorded runtime\nexposure", "$D_i^{phys}$\nPhysical delivery", "$Y_i$\nOutcome"]
    colors = ["#D8E8F5", "#D8E8F5", "#AFCFE8", "#F7EEEE", "#F7E7C7"]
    for i, (x, width, label, color) in enumerate(zip(xs, widths, labels, colors)):
        patch = FancyBboxPatch((x, .51), width, .32, boxstyle="round,pad=.010", facecolor=color, edgecolor="#34495E", linewidth=1.2, linestyle="--" if i == 3 else "-")
        ax.add_patch(patch)
        ax.text(x + width/2, .67, label, ha="center", va="center", fontsize=8.2)
        ax.text(x + width/2, .88, "?" if i == 3 else "✓", ha="center", va="center", color="#A93226" if i == 3 else "#1E8449", fontsize=12, weight="bold")
        if i < 4:
            ax.annotate("", xy=(xs[i+1]-.012, .67), xytext=(x+width+.012, .67), arrowprops={"arrowstyle":"->", "lw":1.1, "color":"#2C3E50", "shrinkA":0, "shrinkB":0})
    for y, text_value in zip([.420, .350, .280, .210], ["Events", "Activation state", "Parameter trajectory", "Post-clamp command sent"]):
        ax.text(xs[2] + widths[2]/2, y, text_value, ha="center", va="center", fontsize=7.5)
    ax.plot([xs[2]+widths[2]/2]*2, [.50, .455], color="#34495E", lw=1)
    ax.text(xs[3]+widths[3]/2, .385, "Independent stimulus\nnot observed", ha="center", va="center", fontsize=7.3, color="#A93226")
    ax.plot([.03, .97], [.09, .09], color="#5D6D7E", lw=1.2)
    ax.text(.5, .035, "Provenance $\\mathcal{P}_i$: acquisition identity + byte/canonical-text hashes (orthogonal evidence)", ha="center", va="center", fontsize=8)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    save_figure(fig, figures, "fig1_five_layer_framework")
    plt.close(fig)


def figure2_retrospective(figures: Path, rows: list[dict]) -> None:
    plt = setup_plotting()
    fig, axes = plt.subplots(1, 2, figsize=(7.16, 3.25), gridspec_kw={"width_ratios":[1.35, 1]})
    ax = axes[0]
    rng = np.random.default_rng(20260827)
    colors = {"G":"#C0392B", "F":"#2878B5"}
    for y, code in enumerate(("G", "F")):
        values = [float(row["contact_to_adaptation_latency_s"]) for row in rows if row["mode_code"] == code and row["contact_to_adaptation_latency_s"]]
        jitter = rng.uniform(-.12, .12, len(values))
        ax.scatter(values, y + jitter, s=16, alpha=.62, color=colors[code], edgecolors="none")
        ax.plot(statistics.median(values), y, marker="D", color="black", markersize=4)
    ax.axvline(0, color="black", linestyle="--", lw=1, label="Contact")
    ax.axvline(.20, color="#7D3C98", linestyle=":", lw=1.5, label="Nominal F +0.20 s")
    ax.set_yticks([0,1], ["G", "F"]); ax.set_xlabel("Recorded activation relative to contact (s)")
    ax.set_title("(a) Timing discontinuity")
    ax.text(.02, .96, "G: 43/45 before contact\nF: 3/45 met +0.20-s timing", transform=ax.transAxes, va="top", fontsize=7.5)
    ax.legend(frameon=False, loc="lower center", ncol=2, handlelength=1.4)
    inset = ax.inset_axes([.55, .30, .42, .34])
    for y, code in enumerate(("G", "F")):
        values = [float(row["contact_to_adaptation_latency_s"]) for row in rows if row["mode_code"] == code and row["contact_to_adaptation_latency_s"] and -.30 <= float(row["contact_to_adaptation_latency_s"]) <= .30]
        inset.scatter(values, [y]*len(values), s=8, alpha=.55, color=colors[code], edgecolors="none")
    inset.axvline(0, color="black", linestyle="--", lw=.7); inset.axvline(.2, color="#7D3C98", linestyle=":", lw=.8)
    inset.set_xlim(-.30,.30); inset.set_yticks([]); inset.set_title("Near-contact zoom", fontsize=7); inset.tick_params(labelsize=6)
    inset.patch.set_alpha(.94)

    ax = axes[1]
    counts = {"E":[39,2,4], "F":[35,7,3]}
    labels = ["Full", "Partial", "Zero"]
    bar_colors = ["#2878B5", "#F39C12", "#D5D8DC"]
    hatches = ["", "///", "xx"]
    bottom = np.zeros(2)
    for idx, label in enumerate(labels):
        values = [counts["E"][idx], counts["F"][idx]]
        bars = ax.bar([0,1], values, bottom=bottom, width=.60, color=bar_colors[idx], edgecolor="#34495E", linewidth=.6, hatch=hatches[idx], label=label)
        for x, value, base_y in zip([0,1], values, bottom):
            ax.text(x, base_y + value/2, str(value), ha="center", va="center", fontsize=8)
        bottom += values
    ax.set_xticks([0,1], ["E visual", "F combined"]); ax.set_ylim(0,49); ax.set_ylabel("Trials")
    ax.set_title("(b) Outcome-window exposure")
    ax.legend(frameon=False, loc="upper center", ncol=3, fontsize=7)
    fig.tight_layout(w_pad=1.4)
    save_figure(fig, figures, "fig2_retrospective_discontinuities")
    plt.close(fig)


def figure3_recovery(figures: Path, protocol: dict, metrics: list[dict], fidelity: list[dict]) -> None:
    plt = setup_plotting()
    fig, axes = plt.subplots(1, 2, figsize=(7.16, 3.05))
    specs = protocol["conditions"]
    rng = np.random.default_rng(20260827)
    for x, code in enumerate(v3.CONDITIONS):
        selected = [row for row in metrics if row["true_condition"] == code and int(row["fidelity_evaluable"]) == 1]
        onset = [base.finite_float(row["detected_onset_relative_s"]) for row in selected]
        phi = [base.finite_float(row["phi_hat"]) for row in selected]
        onset_x = x + rng.uniform(-.14, .14, len(onset))
        phi_x = x + rng.uniform(-.14, .14, len(phi))
        axes[0].scatter(onset_x, onset, s=8, alpha=.28, color="#2878B5", edgecolors="none")
        axes[0].plot(x, base.mean(onset), "o", color="#C82423", ms=4)
        axes[0].plot([x-.22,x+.22], [specs[code]["onset_s"]]*2, color="black", lw=1.5)
        axes[1].scatter(phi_x, phi, s=8, alpha=.28, color="#2878B5", edgecolors="none")
        axes[1].plot(x, base.mean(phi), "o", color="#C82423", ms=4)
        axes[1].plot([x-.22,x+.22], [specs[code]["expected_phi"]]*2, color="black", lw=1.5)
    for ax in axes:
        ax.set_xticks(range(5), v3.CONDITIONS); ax.grid(axis="y", alpha=.2)
    axes[0].set_ylabel("Recorded activation after contact (s)"); axes[0].set_title("(a) Activation timing")
    axes[1].set_ylabel("Recorded outcome-window exposure $\\Phi^{rec}$"); axes[1].set_title("(b) Window exposure")
    overall = next(row for row in fidelity if row["condition"] == "OVERALL")
    axes[0].text(.03,.97, f"MAE {1000*overall['timing_mae_s']:.3f} ms\nP95 {1000*overall['timing_p95_abs_error_s']:.3f} ms\nMax {1000*overall['timing_max_abs_error_s']:.3f} ms", transform=axes[0].transAxes, va="top", fontsize=7.5)
    axes[1].text(.03,.55, f"MAE {overall['exposure_mae']:.6f}\nP95 {overall['exposure_p95_abs_error']:.6f}\nMax {overall['exposure_max_abs_error']:.6f}", transform=axes[1].transAxes, va="top", fontsize=7.5)
    fig.tight_layout(w_pad=1.5)
    save_figure(fig, figures, "fig3_record_layer_recovery")
    plt.close(fig)


def figure4_window_binding(figures: Path, command: list[dict]) -> None:
    plt = setup_plotting()
    fig = plt.figure(figsize=(7.16, 3.35))
    grid = fig.add_gridspec(2,1,height_ratios=[3.1,1],hspace=.42)
    ax = fig.add_subplot(grid[0])
    rows = [next(row for row in command if row["condition"] == code) for code in v3.CONDITIONS]
    x = np.arange(5); width=.35
    ax.bar(x-width/2, [row["any_trial_clamp_trials"] for row in rows], width, color="#F39C12", edgecolor="#7E5109", hatch="//", label="Whole trial")
    ax.bar(x+width/2, [row["outcome_window_clamp_trials"] for row in rows], width, color="#2878B5", edgecolor="#154360", label="Outcome window")
    ax.set_xticks(x, v3.CONDITIONS); ax.set_ylabel("Evaluable trials with command clamp")
    ax.set_title("Whole-trial events are not outcome-window exposure")
    ax.legend(frameon=False, ncol=2, loc="upper right")
    ax.text(4+width/2, .35, "0", ha="center", va="bottom", weight="bold", color="#154360")
    ax = fig.add_subplot(grid[1])
    ax.set_xlim(0,1.42); ax.set_ylim(0,1); ax.axis("off")
    ax.plot([.20,1.00],[.60,.60],color="#2878B5",lw=9,solid_capstyle="butt")
    ax.plot([1.10,1.30],[.35,.35],color="#F39C12",lw=9,solid_capstyle="butt")
    for value,label,y in ((.20,"0.20",.76),(1.00,"1.00",.76),(1.10,"1.10",.08),(1.30,"1.30",.08)):
        ax.plot([value,value],[y-.08,y+.08],color="#34495E",lw=.8); ax.text(value,y,label,ha="center",va="bottom" if y>.5 else "top",fontsize=7)
    ax.text(.60,.60,"Outcome window",ha="center",va="center",color="white",fontsize=8,weight="bold")
    ax.text(1.20,.35,"C4 active",ha="center",va="center",color="white",fontsize=8,weight="bold")
    ax.text(.02,.05,"C4: 11 whole-trial clamps, 0 inside the outcome window",fontsize=8,weight="bold")
    save_figure(fig, figures, "fig4_outcome_window_binding")
    plt.close(fig)


def figure5_human_variability(figures: Path, participants: list[dict]) -> None:
    plt = setup_plotting()
    panels = (
        ("Approach duration (s)", "approach_duration_mean_s"),
        ("Omega approach path (m)", "approach_omega_path_mean_m"),
        ("Internal-force impulse (N·s)", "force_impulse_mean_Ns"),
        ("Whole-trial clamp rate", "any_trial_clamp_rate"),
    )
    timing = np.asarray([100*row["timing_mae_fraction_of_limit"] for row in participants])
    exposure = np.asarray([100*row["exposure_mae_fraction_of_limit"] for row in participants])
    fig, axes = plt.subplots(2,2,figsize=(7.16,5.1))
    for ax,(label,key),letter in zip(axes.flat,panels,"abcd"):
        x=np.asarray([row[key] for row in participants])
        ax.scatter(x,timing,s=25,marker="o",facecolor="#2878B5",edgecolor="white",linewidth=.4,label="Timing MAE / 20-ms limit")
        ax.scatter(x,exposure,s=28,marker="^",facecolor="#C58B2A",edgecolor="white",linewidth=.4,label="$\\Phi$ MAE / 0.02 limit")
        for row,xv,yv in zip(participants,x,np.maximum(timing,exposure)):
            if row["participant_id"] in {"F02","F07","F15","F19","F20"}:
                ax.annotate(row["participant_id"],(xv,yv),xytext=(2,2),textcoords="offset points",fontsize=6)
        ax.set_xlabel(label); ax.set_ylabel("MAE as % of criterion limit")
        ax.set_title(f"({letter}) {label.split(' (')[0]}")
        ax.set_ylim(0,17.5); ax.grid(alpha=.18)
    axes[0,0].legend(frameon=False,fontsize=7,loc="upper left")
    fig.text(.5,.008,"Percentages normalize two prespecified error limits for display only; they are not combined into a fidelity score.",ha="center",fontsize=7.5)
    fig.tight_layout(rect=[0,.03,1,1],h_pad=1.2,w_pad=1.2)
    save_figure(fig, figures, "fig5_human_variability_stress_test")
    plt.close(fig)


def create_figures(figures: Path, protocol: dict, metrics: list[dict], fidelity: list[dict], command: list[dict], participants: list[dict], retrospective: list[dict]) -> None:
    figures.mkdir(parents=True, exist_ok=True)
    figure1_framework(figures)
    figure2_retrospective(figures, retrospective)
    figure3_recovery(figures, protocol, metrics, fidelity)
    figure4_window_binding(figures, command)
    figure5_human_variability(figures, participants)


def write_results_summary(path: Path, fidelity: list[dict], quality: list[dict], participants: list[dict], ranges: list[dict]) -> None:
    overall = next(row for row in fidelity if row["condition"] == "OVERALL")
    q = next(row for row in quality if row["condition"] == "OVERALL")
    lookup = {row["stressor"]: row for row in ranges}
    max_timing = max(row["timing_mae_fraction_of_limit"] for row in participants)
    max_exposure = max(row["exposure_mae_fraction_of_limit"] for row in participants)
    lines = [
        "# V3.1 human-variability stress-test results", "",
        f"The locked cohort remained 20 independent participants, 300 planned trials, {q['completed_trials']} evaluable trials, and {q['safety_abort_trials']} safety aborts.", "",
        f"Recorded-state classification was {overall['classification_correct']}/{overall['evaluable_trials']} (100%; exact 95% CI {100*overall['classification_exact_ci_low']:.2f}%–100%). Timing MAE/P95/max were {1000*overall['timing_mae_s']:.3f}/{1000*overall['timing_p95_abs_error_s']:.3f}/{1000*overall['timing_max_abs_error_s']:.3f} ms; exposure MAE/P95/max were {overall['exposure_mae']:.6f}/{overall['exposure_p95_abs_error']:.6f}/{overall['exposure_max_abs_error']:.6f}.", "",
        f"Participant-mean approach duration ranged {lookup['approach_duration']['participant_mean_min']:.4f}–{lookup['approach_duration']['participant_mean_max']:.4f} s, Omega path {lookup['omega_path']['participant_mean_min']:.5f}–{lookup['omega_path']['participant_mean_max']:.5f} m, Panda path {lookup['panda_path']['participant_mean_min']:.5f}–{lookup['panda_path']['participant_mean_max']:.5f} m, peak speed {lookup['panda_peak_speed']['participant_mean_min']:.5f}–{lookup['panda_peak_speed']['participant_mean_max']:.5f} m/s, internal-force impulse {lookup['internal_force_impulse']['participant_mean_min']:.4f}–{lookup['internal_force_impulse']['participant_mean_max']:.4f} N·s, and whole-trial clamp rate {100*lookup['whole_trial_clamp_rate']['participant_mean_min']:.2f}%–{100*lookup['whole_trial_clamp_rate']['participant_mean_max']:.2f}%.", "",
        f"Every participant classified at 100%. The worst participant timing MAE used {100*max_timing:.2f}% of the 20-ms limit and the worst exposure MAE used {100*max_exposure:.2f}% of the 0.02 limit. Within the observed variability envelope, no participant-level criterion failure was observed; this is not proof of invariance outside the sample.", "",
        "Spearman coefficients and participant-resampled bootstrap intervals are descriptive. No p-values or classification associations were computed. Physical delivery was not independently observed, and human force outcomes remain exploratory.",
    ]
    path.write_text("\n".join(lines)+"\n",encoding="utf-8",newline="\n")


def run_analysis(data_dir: Path, protocol_path: Path, oracle_path: Path, participants: Sequence[str], output_dir: Path) -> dict:
    protocol = base.load_protocol(protocol_path)
    oracle = base.load_oracle(oracle_path, participants, protocol["config_sha256"])
    queue, manifests = base.build_cohort(data_dir, participants, oracle, protocol["config_sha256"])
    metrics = [v3.analyze_trial(manifests[trial_id], oracle[trial_id], protocol) for trial_id in base.expected_trial_ids(participants)]
    fidelity = v3.fidelity_summary(metrics, participants)
    quality = base.quality_summary(metrics)
    condition_human, participant_contrasts, contrast_summary = base.participant_summaries(metrics)
    command = v3.record_command_summary(metrics)
    participant_rows = participant_human_variability(metrics)
    ranges = human_variability_ranges(participant_rows, metrics)
    associations, bootstrap = human_variability_associations(participant_rows)
    quartile_rows = v3.quartile_robustness(participant_rows)
    layers = v3.evidence_layers()
    acceptance = base.acceptance_report(fidelity, quality)
    overall = next(row for row in fidelity if row["condition"] == "OVERALL")
    acceptance.update({
        "analysis_scope": "within_system_record_layer_criterion_validation_under_human_generated_variability",
        "classification_exact_95_ci": [overall["classification_exact_ci_low"], overall["classification_exact_ci_high"]],
        "physical_delivery_status": "NOT_INDEPENDENTLY_OBSERVED",
        "human_outcome_role": "EXPLORATORY_ONLY",
        "human_variability_role": "PARTICIPANT_LEVEL_STRESS_TEST",
        "worst_participant_timing_mae_fraction_of_limit": max(row["timing_mae_fraction_of_limit"] for row in participant_rows),
        "worst_participant_exposure_mae_fraction_of_limit": max(row["exposure_mae_fraction_of_limit"] for row in participant_rows),
    })
    retrospective_path = Path(__file__).resolve().parent / "正宫" / "21_framework_first_submission_bundle" / "03_clean_analysis" / "trial_level_fidelity_metrics.csv"
    retrospective = retrospective_rows(retrospective_path)

    output_dir.mkdir(parents=True, exist_ok=True)
    base.write_csv(output_dir/"analysis_cohort_manifest.csv",queue)
    base.write_csv(output_dir/"trial_metrics.csv",metrics)
    base.write_csv(output_dir/"condition_record_fidelity.csv",fidelity)
    base.write_csv(output_dir/"quality_and_safety_summary.csv",quality)
    base.write_csv(output_dir/"record_command_summary.csv",command)
    base.write_csv(output_dir/"participant_human_variability.csv",participant_rows)
    base.write_csv(output_dir/"human_variability_range.csv",ranges)
    base.write_csv(output_dir/"human_variability_associations.csv",associations)
    base.write_csv(output_dir/"supplementary_quartile_robustness.csv",quartile_rows)
    base.write_csv(output_dir/"retrospective_diagnostic_summary.csv",retrospective_summary(retrospective))
    base.write_csv(output_dir/"evidence_layer_status.csv",layers)
    base.write_csv(output_dir/"supplementary_participant_condition_human.csv",condition_human)
    base.write_csv(output_dir/"supplementary_participant_contrasts.csv",participant_contrasts)
    base.write_csv(output_dir/"supplementary_exploratory_contrast_summary.csv",contrast_summary)
    base.write_json(output_dir/"bootstrap_provenance.json",bootstrap)
    base.write_json(output_dir/"validation_acceptance.json",acceptance)
    create_figures(output_dir/"figures",protocol,metrics,fidelity,command,participant_rows,retrospective)
    write_results_summary(output_dir/"results_summary.md",fidelity,quality,participant_rows,ranges)

    outputs=sorted(path for path in output_dir.rglob("*") if path.is_file() and path.name!="analysis_provenance.json")
    provenance={
        "analysis_name":"kfb_runtime_exposure_human_variability_v3_1",
        "analysis_script_sha256":base.sha256_bytes(Path(__file__).resolve()),
        "v3_analysis_dependency_sha256":base.sha256_bytes(Path(v3.__file__).resolve()),
        "v2_analysis_dependency_sha256":base.sha256_bytes(Path(base.__file__).resolve()),
        "data_root_name":data_dir.name,
        "protocol_config_sha256":base.sha256_bytes(protocol_path),
        "oracle_sha256":base.sha256_bytes(oracle_path),
        "retrospective_source_sha256":base.sha256_bytes(retrospective_path),
        "participants":list(participants),
        "expected_trial_count":len(base.expected_trial_ids(participants)),
        "analysis_unit_for_human_variability":"participant",
        "historical_first_five_used_only_for_retrospective_figure":True,
        "historical_first_five_merged_into_formal_cohort":False,
        "raw_files_modified":False,
        "physical_delivery_observed":False,
        "output_sha256":{path.relative_to(output_dir).as_posix():base.sha256_bytes(path) for path in outputs},
    }
    base.write_json(output_dir/"analysis_provenance.json",provenance)
    return acceptance


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir",type=Path,required=True)
    parser.add_argument("--protocol-config",type=Path,required=True)
    parser.add_argument("--oracle",type=Path,required=True)
    parser.add_argument("--participants",default="F01-F20")
    parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args()
    participants=base.parse_participants(args.participants)
    if participants != [f"F{i:02d}" for i in range(1,21)]:
        raise SystemExit("v3.1 analysis is locked to F01-F20")
    result=run_analysis(args.data_dir.resolve(),args.protocol_config.resolve(),args.oracle.resolve(),participants,args.output_dir.resolve())
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
