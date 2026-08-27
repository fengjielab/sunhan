from __future__ import annotations

import json
import math
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats


ROOT = Path(__file__).resolve().parents[2]
PAPER_ROOT = ROOT / "paper2_sci"
OUT = Path(__file__).resolve().parent
FIG = OUT / "figures"
TAB = OUT / "tables"
RAW_ROOT = ROOT / "data" / "ral_date"

METRICS_PATH = PAPER_ROOT / "03_processed_data" / "trial_metrics_main_180.csv"
MANIFEST_PATH = PAPER_ROOT / "02_audit" / "trial_manifest_180.csv"

MODE_ORDER = ["default", "force_only", "vision", "vision_force"]
MODE_CODE = {
    "default": "A",
    "force_only": "G",
    "vision": "E",
    "vision_force": "F",
}
COLORS = {
    "default": "#4D4D4D",
    "force_only": "#7A5195",
    "vision": "#2F6BFF",
    "vision_force": "#00A6A6",
}
GRID = np.arange(-0.20, 1.201, 0.01)
RNG = np.random.default_rng(20260808)


def mean_ci(x: pd.Series | np.ndarray) -> tuple[float, float, float]:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    mean = float(np.mean(x))
    if len(x) < 2:
        return mean, float("nan"), float("nan")
    q = stats.t.ppf(0.975, len(x) - 1)
    half = q * np.std(x, ddof=1) / math.sqrt(len(x))
    return mean, mean - half, mean + half


def paired_contrast(
    data: pd.DataFrame, metric: str, mode_a: str, mode_b: str
) -> dict:
    wide = data.pivot(index="block_id", columns="mode", values=metric).dropna()
    diff = wide[mode_a] - wide[mode_b]
    mean, lo, hi = mean_ci(diff)
    dz = mean / diff.std(ddof=1)
    return {
        "metric": metric,
        "contrast": f"{MODE_CODE[mode_a]}-{MODE_CODE[mode_b]}",
        "mode_a": mode_a,
        "mode_b": mode_b,
        "n_blocks": int(len(diff)),
        "mean_difference": mean,
        "ci95_low": lo,
        "ci95_high": hi,
        "paired_dz": float(dz),
        "p_t": float(stats.ttest_1samp(diff, 0).pvalue),
    }


def first_active_time(raw: pd.DataFrame, column: str, contact: float) -> float:
    if column not in raw.columns:
        return float("nan")
    active = pd.to_numeric(raw[column], errors="coerce").fillna(0).to_numpy()
    idx = np.flatnonzero(active > 0)
    if not len(idx):
        return float("nan")
    t = pd.to_numeric(raw["system_time"], errors="coerce").to_numpy(float)
    return float(t[idx[0]] - contact)


def cluster_segments(mask: np.ndarray, statistic: np.ndarray) -> list[tuple[int, int, float]]:
    clusters: list[tuple[int, int, float]] = []
    start = None
    for i, value in enumerate(mask):
        if value and start is None:
            start = i
        if start is not None and (not value or i == len(mask) - 1):
            end = i if value and i == len(mask) - 1 else i - 1
            clusters.append((start, end, float(np.sum(np.abs(statistic[start : end + 1])))))
            start = None
    return clusters


def paired_cluster_test(
    curves: dict[tuple[str, str], np.ndarray],
    blocks: list[str],
    mode_a: str,
    mode_b: str,
    permutations: int = 10000,
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, np.ndarray]:
    diff = np.stack([curves[(block, mode_a)] - curves[(block, mode_b)] for block in blocks])
    n = np.sum(np.isfinite(diff), axis=0)
    mean = np.nanmean(diff, axis=0)
    sd = np.nanstd(diff, axis=0, ddof=1)
    t_stat = mean / (sd / np.sqrt(n))
    threshold = stats.t.ppf(0.975, len(blocks) - 1)
    observed = cluster_segments(np.abs(t_stat) > threshold, t_stat)

    null_max = np.zeros(permutations)
    for b in range(permutations):
        signs = RNG.choice([-1.0, 1.0], size=(len(blocks), 1))
        perm = diff * signs
        perm_t = np.nanmean(perm, axis=0) / (np.nanstd(perm, axis=0, ddof=1) / np.sqrt(n))
        clusters = cluster_segments(np.abs(perm_t) > threshold, perm_t)
        null_max[b] = max((c[2] for c in clusters), default=0.0)

    rows = []
    for start, end, mass in observed:
        p_value = (1 + np.sum(null_max >= mass)) / (permutations + 1)
        rows.append(
            {
                "contrast": f"{MODE_CODE[mode_a]}-{MODE_CODE[mode_b]}",
                "start_s": GRID[start],
                "end_s": GRID[end],
                "cluster_mass": mass,
                "p_cluster": p_value,
                "mean_difference_within_cluster_N": float(np.nanmean(diff[:, start : end + 1])),
                "significant_0p05": int(p_value < 0.05),
            }
        )
    q = stats.t.ppf(0.975, len(blocks) - 1)
    half = q * np.nanstd(diff, axis=0, ddof=1) / np.sqrt(n)
    return pd.DataFrame(rows), mean, mean - half, mean + half


def within_block_order_adjusted(
    data: pd.DataFrame, metric: str, bootstrap_reps: int = 10000
) -> pd.DataFrame:
    work = data.copy()
    work["G"] = (work["mode"] == "force_only").astype(float)
    work["E"] = (work["mode"] == "vision").astype(float)
    work["F"] = (work["mode"] == "vision_force").astype(float)
    for position in [2, 3, 4]:
        work[f"O{position}"] = (work["within_block_order"] == position).astype(float)
    columns = ["G", "E", "F", "O2", "O3", "O4"]
    X = work[columns] - work.groupby("block_id")[columns].transform("mean")
    y = work[metric] - work.groupby("block_id")[metric].transform("mean")
    Xn, yn = X.to_numpy(), y.to_numpy()
    beta = np.linalg.lstsq(Xn, yn, rcond=None)[0]

    blocks = work["block_id"].unique()
    indices = {block: np.flatnonzero((work["block_id"] == block).to_numpy()) for block in blocks}
    boot = np.zeros((bootstrap_reps, len(beta)))
    for b in range(bootstrap_reps):
        sampled = RNG.choice(blocks, size=len(blocks), replace=True)
        idx = np.concatenate([indices[block] for block in sampled])
        boot[b] = np.linalg.lstsq(Xn[idx], yn[idx], rcond=None)[0]

    contrast_vectors = {
        "G-A": np.array([1, 0, 0, 0, 0, 0], dtype=float),
        "E-A": np.array([0, 1, 0, 0, 0, 0], dtype=float),
        "F-E": np.array([0, -1, 1, 0, 0, 0], dtype=float),
        "F-G": np.array([-1, 0, 1, 0, 0, 0], dtype=float),
        "order 2 vs 1": np.array([0, 0, 0, 1, 0, 0], dtype=float),
        "order 3 vs 1": np.array([0, 0, 0, 0, 1, 0], dtype=float),
        "order 4 vs 1": np.array([0, 0, 0, 0, 0, 1], dtype=float),
    }
    rows = []
    for name, vector in contrast_vectors.items():
        estimate = float(vector @ beta)
        samples = boot @ vector
        p_boot = min(1.0, 2 * min(np.mean(samples <= 0), np.mean(samples >= 0)))
        rows.append(
            {
                "metric": metric,
                "contrast": name,
                "estimate": estimate,
                "ci95_low": float(np.quantile(samples, 0.025)),
                "ci95_high": float(np.quantile(samples, 0.975)),
                "p_bootstrap": float(p_boot),
                "bootstrap_reps": bootstrap_reps,
            }
        )
    return pd.DataFrame(rows)


def set_plot_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "legend.fontsize": 8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.dpi": 150,
            "savefig.dpi": 300,
        }
    )


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    TAB.mkdir(parents=True, exist_ok=True)
    data = pd.read_csv(METRICS_PATH)
    manifest = pd.read_csv(MANIFEST_PATH)
    data["within_block_order"] = data.groupby("block_id")["timestamp"].rank(method="first").astype(int)
    data["approach_s"] = data["contact_onset_system_s"] - data["task_start_system_s"]
    data["grasp_close_s"] = data["contact_to_grasp_success_s"] - data["contact_to_grasp_start_s"]
    data["visual_lock_delay_s"] = np.where(
        data["mode"].isin(["vision", "vision_force"]),
        data["vision_lock_system_s"] - data["task_start_system_s"],
        0.0,
    )
    data["post_policy_ready_time_s"] = data["operation_time_s"] - data["visual_lock_delay_s"]

    curves: dict[tuple[str, str], np.ndarray] = {}
    exposure_rows = []
    for row in manifest.itertuples(index=False):
        metric = data.loc[data["trial_key"] == row.trial_key].iloc[0]
        raw_path = RAW_ROOT / Path(row.csv_source)
        raw = pd.read_csv(raw_path)
        t_abs = pd.to_numeric(raw["system_time"], errors="coerce").to_numpy(float)
        force = pd.to_numeric(raw["F_ext_mag"], errors="coerce").to_numpy(float)
        stiffness = pd.to_numeric(raw["K_trans"], errors="coerce").to_numpy(float)
        contact = float(metric["contact_onset_system_s"])
        start = float(metric["task_start_system_s"])
        valid = np.isfinite(t_abs) & np.isfinite(force) & np.isfinite(stiffness)
        t_abs, force, stiffness = t_abs[valid], force[valid], stiffness[valid]
        order = np.argsort(t_abs)
        t_abs, force, stiffness = t_abs[order], force[order], stiffness[order]
        t_rel = t_abs - contact
        excess = np.maximum(force - float(metric["force_threshold_N"]), 0.0)
        curves[(metric["block_id"], metric["mode"])] = np.interp(
            GRID, t_rel, excess, left=np.nan, right=np.nan
        )

        k_start = float(np.interp(start, t_abs, stiffness))
        k_contact = float(np.interp(contact, t_abs, stiffness))
        k_contact_1s = float(np.interp(contact + 1.0, t_abs, stiffness))
        after_start = np.flatnonzero((t_abs >= start) & (np.abs(stiffness - k_start) > 2.0))
        k_change = float(t_abs[after_start[0]] - contact) if len(after_start) else float("nan")
        exposure_rows.append(
            {
                "trial_key": row.trial_key,
                "block_id": metric["block_id"],
                "participant": metric["participant"],
                "material": metric["material"],
                "mode": metric["mode"],
                "mode_code": MODE_CODE[metric["mode"]],
                "task_start_rel_contact_s": start - contact,
                "vision_lock_rel_contact_s": (
                    float(metric["vision_lock_system_s"] - contact)
                    if np.isfinite(metric["vision_lock_system_s"])
                    else float("nan")
                ),
                "vision_lock_delay_s": float(metric["vision_lock_system_s"] - start)
                if np.isfinite(metric["vision_lock_system_s"])
                else float("nan"),
                "force_active_rel_contact_s": first_active_time(raw, "force_adapt_active", contact),
                "fusion_active_rel_contact_s": first_active_time(raw, "fusion_active", contact),
                "first_K_change_after_task_start_rel_contact_s": k_change,
                "K_task_start_N_m": k_start,
                "K_contact_N_m": k_contact,
                "K_contact_plus_1s_N_m": k_contact_1s,
            }
        )

    exposure = pd.DataFrame(exposure_rows)
    exposure.to_csv(TAB / "realized_intervention_timing_180.csv", index=False)

    mode_metrics = [
        "primary_excess_impulse_Ns_0p2_1p0",
        "initial_peak_force_N_0_0p2",
        "operation_time_s",
        "approach_s",
        "contact_to_grasp_success_s",
        "grasp_to_release_s",
        "release_duration_s",
        "post_policy_ready_time_s",
    ]
    descriptive = data.groupby("mode")[mode_metrics].agg(["mean", "std"]).reset_index()
    descriptive.columns = [
        col[0] if not col[1] else f"{col[0]}_{col[1]}"
        for col in descriptive.columns.to_flat_index()
    ]
    descriptive.to_csv(TAB / "mode_descriptives_latency_safety.csv", index=False)

    contrasts = []
    pairs = [
        ("vision", "default"),
        ("force_only", "default"),
        ("vision", "force_only"),
        ("vision_force", "vision"),
        ("vision_force", "force_only"),
    ]
    for metric in [
        "primary_excess_impulse_Ns_0p2_1p0",
        "initial_peak_force_N_0_0p2",
        "operation_time_s",
        "approach_s",
        "post_policy_ready_time_s",
    ]:
        contrasts.extend(paired_contrast(data, metric, a, b) for a, b in pairs)
    contrast_df = pd.DataFrame(contrasts)
    contrast_df.to_csv(TAB / "paired_contrasts_latency_safety.csv", index=False)

    order_adjusted = within_block_order_adjusted(
        data, "primary_excess_impulse_Ns_0p2_1p0", bootstrap_reps=10000
    )
    order_adjusted.to_csv(TAB / "order_adjusted_primary.csv", index=False)

    cluster_frames = []
    cluster_curves = {}
    blocks = sorted(data["block_id"].unique())
    for mode_a, mode_b in [
        ("vision", "default"),
        ("force_only", "default"),
        ("vision_force", "vision"),
        ("vision_force", "force_only"),
    ]:
        frame, mean, lo, hi = paired_cluster_test(
            curves, blocks, mode_a, mode_b, permutations=10000
        )
        cluster_frames.append(frame)
        cluster_curves[f"{MODE_CODE[mode_a]}-{MODE_CODE[mode_b]}"] = (mean, lo, hi)
    cluster_df = pd.concat(cluster_frames, ignore_index=True)
    cluster_df.to_csv(TAB / "functional_cluster_results.csv", index=False)

    aligned_rows = []
    for mode in MODE_ORDER:
        matrix = np.stack([curves[(block, mode)] for block in blocks])
        mean = np.nanmean(matrix, axis=0)
        half = stats.t.ppf(0.975, len(blocks) - 1) * np.nanstd(matrix, axis=0, ddof=1) / np.sqrt(len(blocks))
        for t, m, h in zip(GRID, mean, half):
            aligned_rows.append(
                {
                    "mode": mode,
                    "mode_code": MODE_CODE[mode],
                    "t_rel_contact_s": t,
                    "mean_excess_force_N": m,
                    "ci95_low_N": m - h,
                    "ci95_high_N": m + h,
                }
            )
    pd.DataFrame(aligned_rows).to_csv(TAB / "aligned_excess_force_curves.csv", index=False)

    tail_rows = []
    for mode, group in data.groupby("mode"):
        x = group["primary_excess_impulse_Ns_0p2_1p0"].to_numpy(float)
        threshold = np.quantile(x, 0.80)
        tail_rows.append(
            {
                "mode": mode,
                "mode_code": MODE_CODE[mode],
                "n": len(x),
                "q80_Ns": float(threshold),
                "worst_20pct_mean_Ns": float(np.mean(x[x >= threshold])),
                "maximum_Ns": float(np.max(x)),
            }
        )
    tail_df = pd.DataFrame(tail_rows)
    tail_df.to_csv(TAB / "upper_tail_risk.csv", index=False)

    material_rows = []
    participant_rows = []
    for material, group in data.groupby("material"):
        result = paired_contrast(group, "primary_excess_impulse_Ns_0p2_1p0", "vision", "default")
        result["material"] = material
        material_rows.append(result)
    for participant, group in data.groupby("participant"):
        result = paired_contrast(group, "primary_excess_impulse_Ns_0p2_1p0", "vision", "default")
        result["participant"] = participant
        participant_rows.append(result)
    pd.DataFrame(material_rows).to_csv(TAB / "material_specific_E_minus_A.csv", index=False)
    pd.DataFrame(participant_rows).to_csv(TAB / "participant_specific_E_minus_A.csv", index=False)

    order_counts = pd.crosstab(data["mode"], data["within_block_order"]).reindex(MODE_ORDER)
    order_counts.to_csv(TAB / "mode_order_counts.csv")

    set_plot_style()

    # Figure 1: realized timing and stiffness exposure.
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0), constrained_layout=True)
    timing_sets = [
        ("E visual lock", -data.loc[data["mode"] == "vision", "vision_lead_to_contact_s"], COLORS["vision"]),
        ("F visual lock", -data.loc[data["mode"] == "vision_force", "vision_lead_to_contact_s"], COLORS["vision_force"]),
        ("G force active", exposure.loc[exposure["mode"] == "force_only", "force_active_rel_contact_s"], COLORS["force_only"]),
        ("F fusion active", exposure.loc[exposure["mode"] == "vision_force", "fusion_active_rel_contact_s"], "#008B8B"),
    ]
    positions = np.arange(len(timing_sets))
    for pos, (label, values, color) in zip(positions, timing_sets):
        values = np.asarray(values.dropna(), dtype=float)
        axes[0].boxplot(
            values,
            positions=[pos],
            widths=0.55,
            patch_artist=True,
            boxprops={"facecolor": color, "alpha": 0.28, "edgecolor": color},
            medianprops={"color": color, "linewidth": 1.7},
            whiskerprops={"color": color},
            capprops={"color": color},
            flierprops={"marker": "o", "markersize": 2.5, "markerfacecolor": color, "markeredgecolor": color},
        )
        jitter = RNG.normal(0, 0.035, size=len(values))
        axes[0].scatter(np.full(len(values), pos) + jitter, values, s=8, color=color, alpha=0.40, linewidths=0)
    axes[0].axhline(0, color="#B22222", linestyle="--", linewidth=1, label="logged contact")
    axes[0].set_xticks(positions, [x[0] for x in timing_sets], rotation=18, ha="right")
    axes[0].set_ylabel("Event time relative to contact (s)")
    axes[0].set_title("(a) Realized intervention timing")
    axes[0].legend(frameon=False, loc="upper left")

    checkpoints = ["K_task_start_N_m", "K_contact_N_m", "K_contact_plus_1s_N_m"]
    labels = ["Task start", "Contact", "Contact + 1 s"]
    x = np.arange(3)
    for mode in MODE_ORDER:
        group = exposure[exposure["mode"] == mode]
        means = group[checkpoints].mean().to_numpy(float)
        sem = group[checkpoints].std(ddof=1).to_numpy(float) / math.sqrt(len(group))
        axes[1].errorbar(
            x,
            means,
            yerr=1.96 * sem,
            marker="o",
            linewidth=1.6,
            capsize=2,
            color=COLORS[mode],
            label=MODE_CODE[mode],
        )
    axes[1].set_xticks(x, labels)
    axes[1].set_ylabel("Translational stiffness (N/m)")
    axes[1].set_title("(b) Logged stiffness exposure")
    axes[1].legend(frameon=False, ncol=4, loc="lower left")
    fig.savefig(FIG / "fig1_realized_timing_and_stiffness.png", bbox_inches="tight")
    fig.savefig(FIG / "fig1_realized_timing_and_stiffness.pdf", bbox_inches="tight")
    plt.close(fig)

    # Figure 2: functional force inference.
    fig, axes = plt.subplots(2, 1, figsize=(7.2, 5.1), sharex=True, constrained_layout=True)
    aligned = pd.DataFrame(aligned_rows)
    for mode in MODE_ORDER:
        group = aligned[aligned["mode"] == mode]
        axes[0].plot(group["t_rel_contact_s"], group["mean_excess_force_N"], color=COLORS[mode], label=MODE_CODE[mode], linewidth=1.7)
        axes[0].fill_between(group["t_rel_contact_s"], group["ci95_low_N"], group["ci95_high_N"], color=COLORS[mode], alpha=0.13, linewidth=0)
    axes[0].axvline(0, color="#B22222", linestyle="--", linewidth=1)
    axes[0].axvspan(0.2, 1.0, color="#E9EEF6", alpha=0.5, zorder=-2)
    axes[0].set_ylabel("Excess force (N)")
    axes[0].set_title("(a) Contact-aligned excess-force trajectories")
    axes[0].legend(frameon=False, ncol=4)

    for contrast, color in [("E-A", COLORS["vision"]), ("F-G", COLORS["vision_force"])]:
        mean, lo, hi = cluster_curves[contrast]
        axes[1].plot(GRID, mean, color=color, linewidth=1.7, label=contrast)
        axes[1].fill_between(GRID, lo, hi, color=color, alpha=0.15, linewidth=0)
        sig = cluster_df[(cluster_df["contrast"] == contrast) & (cluster_df["significant_0p05"] == 1)]
        for row in sig.itertuples(index=False):
            ybar = -0.92 if contrast == "E-A" else -0.82
            axes[1].plot([row.start_s, row.end_s], [ybar, ybar], color=color, linewidth=4, solid_capstyle="butt")
    axes[1].axhline(0, color="#777777", linewidth=0.8)
    axes[1].axvline(0, color="#B22222", linestyle="--", linewidth=1)
    axes[1].set_xlabel("Time relative to logged contact (s)")
    axes[1].set_ylabel("Paired difference (N)")
    axes[1].set_title("(b) Paired functional contrasts; thick bars: cluster p < 0.05")
    axes[1].legend(frameon=False, ncol=2)
    fig.savefig(FIG / "fig2_functional_force_inference.png", bbox_inches="tight")
    fig.savefig(FIG / "fig2_functional_force_inference.pdf", bbox_inches="tight")
    plt.close(fig)

    # Figure 3: safety-efficiency and phase decomposition.
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.1), constrained_layout=True)
    for mode in MODE_ORDER:
        group = data[data["mode"] == mode]
        tx, txlo, txhi = mean_ci(group["operation_time_s"])
        fy, fylo, fyhi = mean_ci(group["primary_excess_impulse_Ns_0p2_1p0"])
        axes[0].errorbar(
            tx,
            fy,
            xerr=[[tx - txlo], [txhi - tx]],
            yerr=[[fy - fylo], [fyhi - fy]],
            fmt="o",
            color=COLORS[mode],
            capsize=3,
            markersize=6,
        )
        axes[0].annotate(MODE_CODE[mode], (tx, fy), xytext=(5, 5), textcoords="offset points", color=COLORS[mode], fontweight="bold")
    axes[0].set_xlabel("Total operation time (s)")
    axes[0].set_ylabel("Excess-force impulse, 0.2-1.0 s (N s)")
    axes[0].set_title("(a) Safety-efficiency plane")

    phase_cols = ["approach_s", "contact_to_grasp_success_s", "grasp_to_release_s", "release_duration_s"]
    phase_labels = ["Approach", "Contact-to-grasp", "Transport", "Release"]
    phase_colors = ["#A6CEE3", "#1F78B4", "#B2DF8A", "#33A02C"]
    bottom = np.zeros(len(MODE_ORDER))
    for phase, label, color in zip(phase_cols, phase_labels, phase_colors):
        values = data.groupby("mode")[phase].mean().reindex(MODE_ORDER).to_numpy(float)
        axes[1].bar(np.arange(len(MODE_ORDER)), values, bottom=bottom, label=label, color=color, edgecolor="white", linewidth=0.5)
        bottom += values
    axes[1].set_xticks(np.arange(len(MODE_ORDER)), [MODE_CODE[m] for m in MODE_ORDER])
    axes[1].set_ylabel("Mean phase duration (s)")
    axes[1].set_title("(b) Dual-clock phase decomposition")
    axes[1].legend(frameon=False, fontsize=7, ncol=2)
    fig.savefig(FIG / "fig3_safety_efficiency_dual_clock.png", bbox_inches="tight")
    fig.savefig(FIG / "fig3_safety_efficiency_dual_clock.pdf", bbox_inches="tight")
    plt.close(fig)

    # Figure 4: order robustness.
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2), constrained_layout=True)
    primary_unadjusted = contrast_df[
        (contrast_df["metric"] == "primary_excess_impulse_Ns_0p2_1p0")
        & (contrast_df["contrast"].isin(["E-A", "G-A", "F-E", "F-G"]))
    ].copy()
    adjusted = order_adjusted[order_adjusted["contrast"].isin(["E-A", "G-A", "F-E", "F-G"])].copy()
    labels = ["E-A", "G-A", "F-E", "F-G"]
    y = np.arange(len(labels))
    for offset, frame, label, marker, color in [
        (-0.11, primary_unadjusted, "Paired", "o", "#555555"),
        (0.11, adjusted.rename(columns={"estimate": "mean_difference"}), "Order-adjusted", "s", "#B22222"),
    ]:
        frame = frame.set_index("contrast").reindex(labels)
        est = frame["mean_difference"].to_numpy(float)
        lo = frame["ci95_low"].to_numpy(float)
        hi = frame["ci95_high"].to_numpy(float)
        axes[0].errorbar(est, y + offset, xerr=[est - lo, hi - est], fmt=marker, color=color, capsize=2, label=label)
    axes[0].axvline(0, color="#777777", linewidth=0.8)
    axes[0].set_yticks(y, labels)
    axes[0].invert_yaxis()
    axes[0].set_xlabel("Difference in impulse (N s); negative favors first mode")
    axes[0].set_title("(a) Primary contrasts and order adjustment")
    axes[0].legend(frameon=False)

    width = 0.19
    positions = np.arange(1, 5)
    for i, mode in enumerate(MODE_ORDER):
        values = order_counts.loc[mode, positions].to_numpy(float)
        axes[1].bar(positions + (i - 1.5) * width, values, width=width, color=COLORS[mode], label=MODE_CODE[mode])
    axes[1].set_xticks(positions)
    axes[1].set_xlabel("Within-block trial position")
    axes[1].set_ylabel("Number of trials")
    axes[1].set_title("(b) Incomplete order balance")
    axes[1].legend(frameon=False, ncol=4)
    fig.savefig(FIG / "fig4_order_robustness.png", bbox_inches="tight")
    fig.savefig(FIG / "fig4_order_robustness.pdf", bbox_inches="tight")
    plt.close(fig)

    e_a_operation = contrast_df[
        (contrast_df["metric"] == "operation_time_s") & (contrast_df["contrast"] == "E-A")
    ].iloc[0]
    e_a_approach = contrast_df[
        (contrast_df["metric"] == "approach_s") & (contrast_df["contrast"] == "E-A")
    ].iloc[0]
    e_a_post_ready = contrast_df[
        (contrast_df["metric"] == "post_policy_ready_time_s") & (contrast_df["contrast"] == "E-A")
    ].iloc[0]
    summary = {
        "dataset": {
            "n_trials": int(len(data)),
            "n_blocks": int(data["block_id"].nunique()),
            "n_participants": int(data["participant"].nunique()),
            "successes": int(data["success"].sum()),
        },
        "visual_lock": {
            "E_delay_after_task_start_mean_s": float(data.loc[data["mode"] == "vision", "visual_lock_delay_s"].mean()),
            "F_delay_after_task_start_mean_s": float(data.loc[data["mode"] == "vision_force", "visual_lock_delay_s"].mean()),
            "E_lead_before_contact_mean_s": float(data.loc[data["mode"] == "vision", "vision_lead_to_contact_s"].mean()),
            "F_lead_before_contact_mean_s": float(data.loc[data["mode"] == "vision_force", "vision_lead_to_contact_s"].mean()),
        },
        "force_activation_audit": {
            "G_active_before_task_start": int(
                (
                    exposure.loc[exposure["mode"] == "force_only", "force_active_rel_contact_s"]
                    < exposure.loc[exposure["mode"] == "force_only", "task_start_rel_contact_s"]
                ).sum()
            ),
            "G_active_before_contact": int(
                (exposure.loc[exposure["mode"] == "force_only", "force_active_rel_contact_s"] < 0).sum()
            ),
            "F_fusion_median_rel_contact_s": float(
                exposure.loc[exposure["mode"] == "vision_force", "fusion_active_rel_contact_s"].median()
            ),
        },
        "dual_clock_E_minus_A": {
            "operation_time_difference_s": float(e_a_operation["mean_difference"]),
            "operation_time_ci": [float(e_a_operation["ci95_low"]), float(e_a_operation["ci95_high"])],
            "approach_difference_s": float(e_a_approach["mean_difference"]),
            "approach_ci": [float(e_a_approach["ci95_low"]), float(e_a_approach["ci95_high"])],
            "post_policy_ready_difference_s": float(e_a_post_ready["mean_difference"]),
            "post_policy_ready_ci": [float(e_a_post_ready["ci95_low"]), float(e_a_post_ready["ci95_high"])],
        },
        "cluster_permutation": cluster_df.to_dict(orient="records"),
        "order_adjusted": order_adjusted.to_dict(orient="records"),
        "upper_tail": tail_df.to_dict(orient="records"),
    }
    with open(OUT / "analysis_summary_latency_aware.json", "w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
