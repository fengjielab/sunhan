#!/usr/bin/env python3
"""Record-layer runtime-exposure analysis for the locked F01-F20 study.

The analyzer is deliberately separated from the online controller.  It reads
only the frozen protocol, private oracle, and acquisition files.  Scheduled
condition truth, recorded runtime state, and post-clamp sent commands are kept
as distinct evidence layers.  Physical delivery is never inferred because no
independent output sensor was acquired.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Sequence

import analyze_kfb_timing_formal as base


PRIMARY_LIMITS = base.PRIMARY_LIMITS
CONDITIONS = ("C0", "C1", "C2", "C3", "C4")
WINDOW_DURATION_S = 0.8


def exact_binomial_ci(successes: int, trials: int, confidence: float = 0.95) -> tuple[float, float]:
    """Two-sided Clopper-Pearson interval."""
    if trials <= 0 or not 0 <= successes <= trials:
        raise ValueError("binomial counts must satisfy 0 <= successes <= trials and trials > 0")
    from scipy.stats import beta

    alpha = 1.0 - confidence
    low = 0.0 if successes == 0 else float(beta.ppf(alpha / 2.0, successes, trials - successes + 1))
    high = 1.0 if successes == trials else float(beta.ppf(1.0 - alpha / 2.0, successes + 1, trials - successes))
    return low, high


def event_time(rows: Sequence[dict], event_name: str) -> float:
    for row in rows:
        if event_name in str(row.get("event", "")).split("|"):
            return base.row_time(row)
    return math.nan


def vector(row: dict, prefix: str) -> tuple[float, float, float]:
    return tuple(base.finite_float(row.get(f"{prefix}_{axis}")) for axis in ("x", "y", "z"))


def distance(left: Sequence[float], right: Sequence[float]) -> float:
    if not all(math.isfinite(value) for value in (*left, *right)):
        return math.nan
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right)))


def interval_integral(
    rows: Sequence[dict], start_s: float, end_s: float, value_key: str,
    max_gap_s: float, *, step: bool = False,
) -> tuple[float, float]:
    """Integrate a logged sample value over a bounded interval.

    Booleans/state values use left-hold integration; continuous command norms
    use a trapezoid.  Returned coverage allows missing-window auditing.
    """
    total = 0.0
    covered = 0.0
    for left, right in zip(rows, rows[1:]):
        t0, t1 = base.row_time(left), base.row_time(right)
        dt = t1 - t0
        if not (0 < dt <= max_gap_s):
            continue
        lo, hi = max(t0, start_s), min(t1, end_s)
        if hi <= lo:
            continue
        v0 = base.finite_float(left.get(value_key))
        v1 = base.finite_float(right.get(value_key))
        if not math.isfinite(v0) or (not step and not math.isfinite(v1)):
            continue
        width = hi - lo
        covered += width
        if step:
            total += v0 * width
        else:
            fraction_lo = (lo - t0) / dt
            fraction_hi = (hi - t0) / dt
            vlo = v0 + (v1 - v0) * fraction_lo
            vhi = v0 + (v1 - v0) * fraction_hi
            total += 0.5 * (vlo + vhi) * width
    return total, covered


def trajectory_metrics(rows: Sequence[dict], task_start_s: float, contact_s: float, max_gap_s: float) -> dict:
    if not all(math.isfinite(value) for value in (task_start_s, contact_s)) or contact_s <= task_start_s:
        return {
            "approach_duration_s": math.nan,
            "approach_robot_path_m": math.nan,
            "approach_omega_path_m": math.nan,
            "approach_robot_peak_speed_m_s": math.nan,
        }
    selected = [row for row in rows if task_start_s <= base.row_time(row) <= contact_s]
    robot_path = 0.0
    omega_path = 0.0
    robot_speeds: list[float] = []
    used = 0
    for left, right in zip(selected, selected[1:]):
        dt = base.row_time(right) - base.row_time(left)
        if not (0 < dt <= max_gap_s):
            continue
        robot_step = distance(vector(left, "robot"), vector(right, "robot"))
        omega_step = distance(vector(left, "omega"), vector(right, "omega"))
        if math.isfinite(robot_step):
            robot_path += robot_step
            robot_speeds.append(robot_step / dt)
            used += 1
        if math.isfinite(omega_step):
            omega_path += omega_step
    return {
        "approach_duration_s": contact_s - task_start_s,
        "approach_robot_path_m": robot_path if used else math.nan,
        "approach_omega_path_m": omega_path if used else math.nan,
        "approach_robot_peak_speed_m_s": max(robot_speeds, default=math.nan),
    }


def analyze_trial(manifest: dict, oracle: dict, protocol: dict) -> dict:
    result = base.analyze_trial(manifest, oracle, protocol)
    rows = base.read_csv(manifest["_paths"]["csv"])
    config = protocol["config"]
    contact_s = base.finite_float(result["contact_confirmed_s"])
    task_start_s = event_time(rows, "task_start")
    result.update(trajectory_metrics(rows, task_start_s, contact_s, config["max_metric_gap_s"]))
    result["task_start_s"] = task_start_s

    if math.isfinite(contact_s):
        start = contact_s + config["outcome_window_start_s"]
        end = contact_s + config["outcome_window_end_s"]
        clamp_duration, clamp_coverage = interval_integral(
            rows, start, end, "haptic_clamped", config["max_metric_gap_s"], step=True,
        )
        command_dose, command_coverage = interval_integral(
            rows, start, end, "haptic_cmd_norm", config["max_metric_gap_s"], step=False,
        )
        window = base.window_rows(rows, contact_s, config["outcome_window_start_s"], config["outcome_window_end_s"])
    else:
        clamp_duration = clamp_coverage = command_dose = command_coverage = math.nan
        window = []

    complete_window = (
        math.isfinite(clamp_coverage) and math.isfinite(command_coverage)
        and clamp_coverage >= WINDOW_DURATION_S - config["max_metric_gap_s"]
        and command_coverage >= WINDOW_DURATION_S - config["max_metric_gap_s"]
    )
    command_norms = [base.finite_float(row.get("haptic_cmd_norm")) for row in window]
    command_norms = [value for value in command_norms if math.isfinite(value)]
    result.update({
        "scheduled_truth_layer": "frozen_protocol_and_oracle",
        "recorded_state_layer": "observed",
        "sent_command_layer": "observed_post_clamp_command",
        "physical_delivery_layer": "NOT_INDEPENDENTLY_OBSERVED",
        "outcome_window_duration_s": WINDOW_DURATION_S,
        "haptic_clamped_window_duration_s": clamp_duration if complete_window else math.nan,
        "haptic_clamped_window_fraction": clamp_duration / WINDOW_DURATION_S if complete_window else math.nan,
        "haptic_clamped_window_any": int(complete_window and clamp_duration > 0),
        "haptic_command_window_mean_N": command_dose / WINDOW_DURATION_S if complete_window else math.nan,
        "haptic_command_window_peak_N": max(command_norms, default=math.nan) if complete_window else math.nan,
        "haptic_command_window_integral_Ns": command_dose if complete_window else math.nan,
        "haptic_command_window_coverage_s": command_coverage,
        "haptic_send_ok_semantics": "API_RETURN_ONLY",
    })
    return result


def fidelity_summary(metrics: list[dict], participants: Sequence[str]) -> list[dict]:
    rows = base.fidelity_summary(metrics, participants)
    for row in rows:
        low, high = exact_binomial_ci(int(row["classification_correct"]), int(row["evaluable_trials"]))
        row["classification_exact_ci_low"] = low
        row["classification_exact_ci_high"] = high
    return rows


def participant_value_ci(metrics: list[dict], key: str, condition: str) -> tuple[float, float, float, int]:
    selected = [row for row in metrics if condition == "OVERALL" or row["true_condition"] == condition]
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in selected:
        if int(row["fidelity_evaluable"]) == 1:
            grouped[row["participant_id"]].append(base.finite_float(row[key]))
    return base.mean_ci(base.mean(values) for values in grouped.values())


def record_command_summary(metrics: list[dict]) -> list[dict]:
    output = []
    for condition in (*CONDITIONS, "OVERALL"):
        selected = [row for row in metrics if condition == "OVERALL" or row["true_condition"] == condition]
        complete = [row for row in selected if int(row["fidelity_evaluable"]) == 1]
        clamp_fraction = [base.finite_float(row["haptic_clamped_window_fraction"]) for row in complete]
        command_integral = [base.finite_float(row["haptic_command_window_integral_Ns"]) for row in complete]
        command_mean, command_low, command_high, participant_n = participant_value_ci(
            metrics, "haptic_command_window_integral_Ns", condition,
        )
        output.append({
            "condition": condition,
            "planned_trials": len(selected),
            "evaluable_trials": len(complete),
            "any_trial_clamp_trials": sum(int(row["haptic_clamped_any"]) for row in complete),
            "outcome_window_clamp_trials": sum(int(row["haptic_clamped_window_any"]) for row in complete),
            "outcome_window_clamp_fraction_mean": base.mean(clamp_fraction),
            "outcome_window_clamp_fraction_p95": base.percentile(clamp_fraction, 0.95),
            "outcome_window_clamp_fraction_max": max((v for v in clamp_fraction if math.isfinite(v)), default=math.nan),
            "command_integral_trial_mean_Ns": base.mean(command_integral),
            "command_integral_trial_p95_Ns": base.percentile(command_integral, 0.95),
            "command_integral_participant_mean_Ns": command_mean,
            "command_integral_participant_ci_low_Ns": command_low,
            "command_integral_participant_ci_high_Ns": command_high,
            "participant_count": participant_n,
            "physical_delivery_status": "NOT_INDEPENDENTLY_OBSERVED",
        })
    return output


def participant_runtime_summary(metrics: list[dict]) -> list[dict]:
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
            "exposure_mae": base.mean(exposure),
            "approach_duration_mean_s": base.mean(base.finite_float(row["approach_duration_s"]) for row in complete),
            "approach_duration_min_s": min((base.finite_float(row["approach_duration_s"]) for row in complete), default=math.nan),
            "approach_duration_max_s": max((base.finite_float(row["approach_duration_s"]) for row in complete), default=math.nan),
            "approach_robot_path_mean_m": base.mean(base.finite_float(row["approach_robot_path_m"]) for row in complete),
            "approach_robot_peak_speed_mean_m_s": base.mean(base.finite_float(row["approach_robot_peak_speed_m_s"]) for row in complete),
            "force_impulse_mean_Ns": base.mean(base.finite_float(row["excess_force_impulse_Ns"]) for row in complete),
            "any_trial_clamp_rate": base.mean(int(row["haptic_clamped_any"]) for row in complete),
            "outcome_window_clamp_fraction_mean": base.mean(base.finite_float(row["haptic_clamped_window_fraction"]) for row in complete),
        })
    return output


def quartile_robustness(participants: list[dict]) -> list[dict]:
    output = []
    variables = (
        ("approach_duration", "approach_duration_mean_s"),
        ("approach_robot_path", "approach_robot_path_mean_m"),
        ("any_trial_clamp_rate", "any_trial_clamp_rate"),
    )
    for variable, key in variables:
        ranked = sorted(participants, key=lambda row: (base.finite_float(row[key]), row["participant_id"]))
        groups: dict[int, list[dict]] = defaultdict(list)
        for index, row in enumerate(ranked):
            quartile = min(4, math.floor(index * 4 / len(ranked)) + 1)
            groups[quartile].append(row)
        for quartile in range(1, 5):
            group = groups[quartile]
            output.append({
                "stratification_variable": variable,
                "quartile": f"Q{quartile}",
                "participant_count": len(group),
                "participant_ids": ";".join(row["participant_id"] for row in group),
                "stratifier_min": min(base.finite_float(row[key]) for row in group),
                "stratifier_max": max(base.finite_float(row[key]) for row in group),
                "classification_accuracy_mean": base.mean(base.finite_float(row["classification_accuracy"]) for row in group),
                "timing_mae_mean_s": base.mean(base.finite_float(row["timing_mae_s"]) for row in group),
                "exposure_mae_mean": base.mean(base.finite_float(row["exposure_mae"]) for row in group),
                "analysis_role": "descriptive_robustness_no_significance_screening",
            })
    return output


def variability_summary(participants: list[dict], metrics: list[dict]) -> dict:
    complete = [row for row in metrics if int(row["fidelity_evaluable"]) == 1]
    return {
        "participant_count": len(participants),
        "approach_duration_participant_mean_range_s": [
            min(base.finite_float(row["approach_duration_mean_s"]) for row in participants),
            max(base.finite_float(row["approach_duration_mean_s"]) for row in participants),
        ],
        "approach_duration_all_trial_range_s": [
            min(base.finite_float(row["approach_duration_s"]) for row in complete),
            max(base.finite_float(row["approach_duration_s"]) for row in complete),
        ],
        "approach_robot_path_participant_mean_range_m": [
            min(base.finite_float(row["approach_robot_path_mean_m"]) for row in participants),
            max(base.finite_float(row["approach_robot_path_mean_m"]) for row in participants),
        ],
        "force_impulse_participant_mean_range_Ns": [
            min(base.finite_float(row["force_impulse_mean_Ns"]) for row in participants),
            max(base.finite_float(row["force_impulse_mean_Ns"]) for row in participants),
        ],
        "any_trial_clamp_rate_participant_range": [
            min(base.finite_float(row["any_trial_clamp_rate"]) for row in participants),
            max(base.finite_float(row["any_trial_clamp_rate"]) for row in participants),
        ],
        "interpretation": "Human-generated trajectory variability stress test; not a substitute for independent physical-output validation.",
    }


def evidence_layers() -> list[dict]:
    return [
        {"layer": "N_m", "name": "nominal specification", "status": "SUPPORTED", "evidence": "frozen protocol and private oracle", "claim_boundary": "scheduled condition truth"},
        {"layer": "C_m", "name": "code implementation", "status": "SUPPORTED_WITH_COMMON_SOURCE_LIMIT", "evidence": "versioned acquisition software and independent offline parser", "claim_boundary": "implementation trace; shared platform remains"},
        {"layer": "R_i^rec", "name": "recorded runtime state", "status": "CRITERION_VALIDATED_WITHIN_SYSTEM", "evidence": "logged intervention state, K_fb command, events and hashes", "claim_boundary": "timing and outcome-window exposure reconstruction"},
        {"layer": "R_i^cmd", "name": "post-clamp sent command", "status": "OBSERVED_AS_SOFTWARE_COMMAND", "evidence": "logged haptic command, clamp flag and API return", "claim_boundary": "command-layer dose only; API success is not physical confirmation"},
        {"layer": "D_i^phys", "name": "physical delivery", "status": "NOT_INDEPENDENTLY_OBSERVED", "evidence": "no independent output force/torque sensor", "claim_boundary": "no physical-delivery or external-validation claim"},
        {"layer": "Y_i", "name": "human outcome", "status": "EXPLORATORY_ONLY", "evidence": "Franka internal external-wrench estimate", "claim_boundary": "descriptive participant-level comparisons only"},
        {"layer": "P_i", "name": "provenance", "status": "SUPPORTED", "evidence": "trial identity plus byte and canonical-text SHA-256", "claim_boundary": "orthogonal lineage evidence; not proof of delivery"},
    ]


def create_figures(
    output_dir: Path, protocol: dict, metrics: list[dict], fidelity: list[dict],
    command: list[dict], participants: list[dict],
) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch

    matplotlib.rcParams["svg.hashsalt"] = "runtime-exposure-v3"
    figures = output_dir / "figures"
    figures.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10.2, 3.2))
    ax.axis("off")
    labels = ["N\nNominal", "C\nCode", "Rrec\nRecorded state", "Dphys\nPhysical delivery", "Y\nOutcome"]
    colors = ["#DCEAF7", "#DCEAF7", "#B8D7F0", "#F6D6D6", "#F7E7C6"]
    for index, (label, color) in enumerate(zip(labels, colors)):
        x = 0.03 + index * 0.19
        patch = FancyBboxPatch((x, 0.40), 0.14, 0.30, boxstyle="round,pad=0.02", facecolor=color, edgecolor="#34495E")
        ax.add_patch(patch)
        ax.text(x + 0.07, 0.55, label, ha="center", va="center", fontsize=10)
        if index < 4:
            ax.annotate("", xy=(x + 0.19, 0.55), xytext=(x + 0.14, 0.55), arrowprops={"arrowstyle": "->", "lw": 1.5})
    ax.text(0.675, 0.22, "not independently observed", ha="center", color="#A93226", fontsize=9)
    ax.annotate("Provenance P: identity + byte/canonical-text hashes (orthogonal evidence)", xy=(0.50, 0.12), ha="center", fontsize=9)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    fig.tight_layout()
    fig.savefig(figures / "fig1_five_layer_framework.png", dpi=300)
    fig.savefig(figures / "fig1_five_layer_framework.svg", metadata={"Date": None})
    plt.close(fig)

    conditions = list(CONDITIONS)
    specs = protocol["conditions"]
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.5))
    for x, code in enumerate(conditions):
        selected = [row for row in metrics if row["true_condition"] == code and int(row["fidelity_evaluable"]) == 1]
        onset = [base.finite_float(row["detected_onset_relative_s"]) for row in selected]
        phi = [base.finite_float(row["phi_hat"]) for row in selected]
        axes[0].scatter([x] * len(onset), onset, s=8, alpha=.22, color="#2878B5")
        axes[0].plot(x, base.mean(onset), "o", color="#C82423")
        axes[0].plot([x-.22, x+.22], [specs[code]["onset_s"]] * 2, color="black", lw=1.5)
        axes[1].scatter([x] * len(phi), phi, s=8, alpha=.22, color="#2878B5")
        axes[1].plot(x, base.mean(phi), "o", color="#C82423")
        axes[1].plot([x-.22, x+.22], [specs[code]["expected_phi"]] * 2, color="black", lw=1.5)
    for ax in axes:
        ax.set_xticks(range(5), conditions); ax.grid(axis="y", alpha=.2)
    axes[0].set_ylabel("Recorded onset from contact (s)"); axes[0].set_title("Recorded-state timing recovery")
    axes[1].set_ylabel("Recorded outcome-window exposure"); axes[1].set_title("Recorded-state exposure recovery")
    fig.tight_layout(w_pad=2.4)
    fig.savefig(figures / "fig2_record_layer_recovery.png", dpi=300)
    fig.savefig(figures / "fig2_record_layer_recovery.svg", metadata={"Date": None})
    plt.close(fig)

    by_condition = [next(row for row in command if row["condition"] == code) for code in conditions]
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.5))
    x = list(range(5))
    axes[0].bar([v-.17 for v in x], [row["any_trial_clamp_trials"] for row in by_condition], width=.34, label="Any time", color="#F39C12")
    axes[0].bar([v+.17 for v in x], [row["outcome_window_clamp_trials"] for row in by_condition], width=.34, label="Outcome window", color="#2878B5")
    axes[0].set_xticks(x, conditions); axes[0].set_ylabel("Evaluable trials with clamp"); axes[0].legend(frameon=False, fontsize=8)
    axes[0].set_title("Window binding changes saturation evidence")
    axes[1].bar(x, [row["command_integral_participant_mean_Ns"] for row in by_condition], color="#5B8E7D")
    for idx, row in enumerate(by_condition):
        low, high = row["command_integral_participant_ci_low_Ns"], row["command_integral_participant_ci_high_Ns"]
        axes[1].plot([idx, idx], [low, high], color="black", lw=1)
    axes[1].set_xticks(x, conditions); axes[1].set_ylabel("Post-clamp sent-command integral (N·s)")
    axes[1].set_title("Command layer, not physical delivery")
    fig.tight_layout(w_pad=2.2)
    fig.savefig(figures / "fig3_command_layer.png", dpi=300)
    fig.savefig(figures / "fig3_command_layer.svg", metadata={"Date": None})
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(10.2, 3.5))
    x = range(len(participants))
    axes[0].bar(x, [row["approach_duration_mean_s"] for row in participants], color="#2878B5")
    axes[1].bar(x, [1000 * row["timing_mae_s"] for row in participants], color="#5B8E7D")
    axes[2].bar(x, [row["exposure_mae"] for row in participants], color="#C58B2A")
    for ax in axes:
        ax.set_xticks(list(x), [row["participant_id"] for row in participants], rotation=90, fontsize=6)
    axes[0].set_ylabel("Mean approach duration (s)"); axes[0].set_title("Human trajectory variation")
    axes[1].set_ylabel("Timing MAE (ms)"); axes[1].set_title("Participant-level timing")
    axes[2].set_ylabel("Exposure MAE"); axes[2].set_title("Participant-level exposure")
    fig.tight_layout(w_pad=1.8)
    fig.savefig(figures / "fig4_variability_stress_test.png", dpi=300)
    fig.savefig(figures / "fig4_variability_stress_test.svg", metadata={"Date": None})
    plt.close(fig)


def write_summary(
    path: Path, fidelity: list[dict], quality: list[dict], command: list[dict], variability: dict,
) -> None:
    overall = next(row for row in fidelity if row["condition"] == "OVERALL")
    q = next(row for row in quality if row["condition"] == "OVERALL")
    cmd = next(row for row in command if row["condition"] == "OVERALL")
    lines = [
        "# V3 record-layer runtime-exposure results", "",
        "The locked cohort contains 20 independent participants and 300 planned trials. "
        f"{q['completed_trials']} were evaluable and {q['safety_abort_trials']} were safety aborts.", "",
        f"Recorded-state classification was {overall['classification_correct']}/{overall['evaluable_trials']} "
        f"({100*overall['classification_accuracy']:.1f}%; exact 95% CI "
        f"{100*overall['classification_exact_ci_low']:.2f}%–{100*overall['classification_exact_ci_high']:.2f}%). "
        f"Timing absolute-error MAE/P95/max were {1000*overall['timing_mae_s']:.3f}/"
        f"{1000*overall['timing_p95_abs_error_s']:.3f}/{1000*overall['timing_max_abs_error_s']:.3f} ms. "
        f"Exposure absolute-error MAE/P95/max were {overall['exposure_mae']:.6f}/"
        f"{overall['exposure_p95_abs_error']:.6f}/{overall['exposure_max_abs_error']:.6f}.", "",
        "Threshold rationale: at 200 Hz, 20 ms is four control cycles; 50 ms is ten cycles and equals the "
        "contact-confirmation hold interval; Phi=0.02 equals 16 ms in the 0.8 s outcome window. These limits "
        "predated the present formal data but were not preregistered.", "",
        f"Among evaluable trials, {cmd['any_trial_clamp_trials']} had a clamp somewhere in the trial and "
        f"{cmd['outcome_window_clamp_trials']} had a clamp in the outcome window. Logged commands are post-clamp "
        "software commands; haptic_send_ok is an API return only. Physical delivery was not independently observed.", "",
        f"Participant mean approach durations ranged from {variability['approach_duration_participant_mean_range_s'][0]:.4f} "
        f"to {variability['approach_duration_participant_mean_range_s'][1]:.4f} s, while all-trial durations ranged "
        f"from {variability['approach_duration_all_trial_range_s'][0]:.4f} to "
        f"{variability['approach_duration_all_trial_range_s'][1]:.4f} s. The 20-person analysis is a human-generated "
        "trajectory-variability stress test, not independent hardware validation.", "",
        "Human force outcomes are exploratory and use the Franka internal external-wrench estimate.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def run_analysis(
    data_dir: Path, protocol_path: Path, oracle_path: Path,
    participants: Sequence[str], output_dir: Path,
) -> dict:
    protocol = base.load_protocol(protocol_path)
    oracle = base.load_oracle(oracle_path, participants, protocol["config_sha256"])
    queue, manifests = base.build_cohort(data_dir, participants, oracle, protocol["config_sha256"])
    metrics = [analyze_trial(manifests[trial_id], oracle[trial_id], protocol) for trial_id in base.expected_trial_ids(participants)]
    fidelity = fidelity_summary(metrics, participants)
    quality = base.quality_summary(metrics)
    condition_human, participant_contrasts, contrast_summary = base.participant_summaries(metrics)
    command = record_command_summary(metrics)
    participant_runtime = participant_runtime_summary(metrics)
    robustness = quartile_robustness(participant_runtime)
    variability = variability_summary(participant_runtime, metrics)
    layers = evidence_layers()
    acceptance = base.acceptance_report(fidelity, quality)
    overall = next(row for row in fidelity if row["condition"] == "OVERALL")
    acceptance.update({
        "analysis_scope": "within_system_record_layer_criterion_validation",
        "classification_exact_95_ci": [overall["classification_exact_ci_low"], overall["classification_exact_ci_high"]],
        "physical_delivery_status": "NOT_INDEPENDENTLY_OBSERVED",
        "human_outcome_role": "EXPLORATORY_ONLY",
        "threshold_status": "predated_formal_data_not_preregistered",
    })

    output_dir.mkdir(parents=True, exist_ok=True)
    base.write_csv(output_dir / "analysis_cohort_manifest.csv", queue)
    base.write_csv(output_dir / "trial_metrics.csv", metrics)
    base.write_csv(output_dir / "condition_record_fidelity.csv", fidelity)
    base.write_csv(output_dir / "quality_and_safety_summary.csv", quality)
    base.write_csv(output_dir / "record_command_summary.csv", command)
    base.write_csv(output_dir / "participant_runtime_summary.csv", participant_runtime)
    base.write_csv(output_dir / "trajectory_robustness_quartiles.csv", robustness)
    base.write_csv(output_dir / "evidence_layer_status.csv", layers)
    base.write_csv(output_dir / "supplementary_participant_condition_human.csv", condition_human)
    base.write_csv(output_dir / "supplementary_participant_contrasts.csv", participant_contrasts)
    base.write_csv(output_dir / "supplementary_exploratory_contrast_summary.csv", contrast_summary)
    base.write_json(output_dir / "trajectory_variability_summary.json", variability)
    base.write_json(output_dir / "validation_acceptance.json", acceptance)
    create_figures(output_dir, protocol, metrics, fidelity, command, participant_runtime)
    write_summary(output_dir / "results_summary.md", fidelity, quality, command, variability)

    outputs = sorted(path for path in output_dir.rglob("*") if path.is_file() and path.name != "analysis_provenance.json")
    provenance = {
        "analysis_name": "kfb_runtime_exposure_record_layer_v3",
        "analysis_script_sha256": base.sha256_bytes(Path(__file__).resolve()),
        "v2_analysis_dependency_sha256": base.sha256_bytes(Path(base.__file__).resolve()),
        "data_root_name": data_dir.name,
        "protocol_config_sha256": base.sha256_bytes(protocol_path),
        "protocol_canonical_config_sha256": protocol["config_sha256"],
        "oracle_sha256": base.sha256_bytes(oracle_path),
        "participants": list(participants),
        "expected_trial_count": len(base.expected_trial_ids(participants)),
        "historical_first_five_scanned": False,
        "raw_files_modified": False,
        "physical_delivery_observed": False,
        "haptic_send_ok_semantics": "API return only",
        "force_source": "Franka internal external-wrench estimate; no independent force/torque sensor",
        "output_sha256": {path.relative_to(output_dir).as_posix(): base.sha256_bytes(path) for path in outputs},
    }
    base.write_json(output_dir / "analysis_provenance.json", provenance)
    return acceptance


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--protocol-config", type=Path, required=True)
    parser.add_argument("--oracle", type=Path, required=True)
    parser.add_argument("--participants", default="F01-F20")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    participants = base.parse_participants(args.participants)
    expected = [f"F{index:02d}" for index in range(1, 21)]
    if participants != expected:
        raise SystemExit("v3 record-layer analysis is locked to F01-F20")
    result = run_analysis(
        args.data_dir.resolve(), args.protocol_config.resolve(), args.oracle.resolve(),
        participants, args.output_dir.resolve(),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
