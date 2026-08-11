#!/usr/bin/env python3
"""Generate Figures 1--6 for the manuscript from 03_clean_analysis only.

The script is intentionally read-only with respect to the clean-analysis directory.
It writes publication figures, figure-source CSV files, and run metadata under
18_manuscript_v1. Representative trials in Figure 6 are selected by a frozen,
deterministic nearest-to-class-median rule.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np
import pandas as pd
import scipy


MODE_ORDER = ["A", "G", "E", "F"]
MODE_COLORS = {
    "A": "#343A40",
    "G": "#D55E00",
    "E": "#0072B2",
    "F": "#009E73",
}
PARTICIPANT_COLORS = {
    "P01": "#4E79A7",
    "P02": "#F28E2B",
    "P03": "#E15759",
    "P04": "#76B7B2",
    "P05": "#59A14F",
}
PRIMARY_METRIC = "primary_excess_impulse_Ns_0p2_1p0"


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    manuscript_dir = script_dir.parent
    project_dir = manuscript_dir.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--clean-dir",
        type=Path,
        default=project_dir / "03_clean_analysis",
        help="Directory containing the frozen clean-analysis CSV files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=manuscript_dir / "figures",
        help="Destination for PNG and PDF figures.",
    )
    parser.add_argument(
        "--source-data-dir",
        type=Path,
        default=manuscript_dir / "figure_source_data",
        help="Destination for the exact source-data extracts used by the figures.",
    )
    parser.add_argument("--dpi", type=int, default=300, help="PNG resolution.")
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_inputs(clean_dir: Path) -> dict[str, pd.DataFrame]:
    names = [
        "master_trial_manifest.csv",
        "data_lineage_audit.csv",
        "participant_level_metrics.csv",
        "statistics_summary.csv",
        "leave_one_participant_out.csv",
        "timing_audit.csv",
        "contact_aligned_summary.csv",
        "contact_aligned_trajectories.csv",
        "trial_level_metrics.csv",
    ]
    missing = [name for name in names if not (clean_dir / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Missing clean-analysis inputs: {missing}")
    return {name: pd.read_csv(clean_dir / name) for name in names}


def validate_inputs(data: dict[str, pd.DataFrame]) -> None:
    manifest = data["master_trial_manifest.csv"]
    timing = data["timing_audit.csv"]
    participant = data["participant_level_metrics.csv"]
    stats = data["statistics_summary.csv"]
    trajectories = data["contact_aligned_trajectories.csv"]

    assert len(manifest) == 186, "Expected 186 archived records."
    assert int(manifest["included_main_clean"].sum()) == 180, "Expected 180 selected trials."
    assert len(timing) == 180 and len(data["trial_level_metrics.csv"]) == 180
    assert participant["participant"].nunique() == 5
    assert participant.groupby("mode_code").size().to_dict() == {"A": 5, "E": 5, "F": 5, "G": 5}
    assert timing.groupby("mode_code").size().to_dict() == {"A": 45, "E": 45, "F": 45, "G": 45}
    assert trajectories["record_id"].nunique() == 180

    expected = {
        "E-A": -0.348902,
        "G-A": -0.074218,
        "F-E": -0.021161,
        "F-G": -0.295845,
    }
    primary = stats[stats["metric"].eq(PRIMARY_METRIC)].set_index("contrast")
    for contrast, target in expected.items():
        actual = float(primary.loc[contrast, "raw_mean_difference"])
        if not np.isclose(actual, target, atol=5e-7):
            raise AssertionError(f"Frozen {contrast} value changed: {actual} != {target}")


def set_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "legend.frameon": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(-0.12, 1.06, label, transform=ax.transAxes, fontweight="bold", fontsize=11, va="top")


def save_figure(fig: plt.Figure, output_dir: Path, stem: str, dpi: int) -> None:
    fig.savefig(output_dir / f"{stem}.png", dpi=dpi, bbox_inches="tight")
    fig.savefig(output_dir / f"{stem}.pdf", bbox_inches="tight")
    plt.close(fig)


def draw_box(
    ax: plt.Axes,
    xy: tuple[float, float],
    width: float,
    height: float,
    text: str,
    facecolor: str,
    edgecolor: str = "#3F4A56",
    fontsize: float = 9,
) -> FancyBboxPatch:
    x, y = xy
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.012,rounding_size=0.018",
        linewidth=1.2,
        edgecolor=edgecolor,
        facecolor=facecolor,
    )
    ax.add_patch(patch)
    ax.text(x + width / 2, y + height / 2, text, ha="center", va="center", fontsize=fontsize)
    return patch


def arrow(ax: plt.Axes, start: tuple[float, float], end: tuple[float, float], color: str = "#59636E") -> None:
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=12,
            linewidth=1.25,
            color=color,
            shrinkA=2,
            shrinkB=2,
        )
    )


def figure1_framework(data: dict[str, pd.DataFrame], out: Path, source: Path, dpi: int) -> None:
    manifest = data["master_trial_manifest.csv"]
    lineage = data["data_lineage_audit.csv"]
    participant = data["participant_level_metrics.csv"]
    counts = pd.DataFrame(
        [
            ("archived_records", len(manifest)),
            ("verified_triplets", int(lineage["all_triplet_files_verified"].sum())),
            ("selected_main_trials", int(manifest["included_main_clean"].sum())),
            ("known_error_records_retained", int((manifest["analysis_role"] == "excluded_known_error").sum())),
            ("independent_participants", participant["participant"].nunique()),
        ],
        columns=["quantity", "value"],
    )
    counts.to_csv(source / "figure1_framework_counts.csv", index=False)

    fig, ax = plt.subplots(figsize=(12.0, 7.0))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.02, 0.95, "A. Human–robot acquisition", fontweight="bold", fontsize=12)
    b1 = draw_box(ax, (0.03, 0.75), 0.15, 0.10, "Human\noperator", "#EAF2F8")
    b2 = draw_box(ax, (0.24, 0.75), 0.16, 0.10, "Teleoperation +\nhaptic interface", "#EAF2F8")
    b3 = draw_box(ax, (0.47, 0.75), 0.18, 0.10, "Supervisory\ncontroller", "#FFF2CC")
    b4 = draw_box(ax, (0.74, 0.75), 0.18, 0.10, "Robot, object,\nand contact", "#E2F0D9")
    bv = draw_box(ax, (0.47, 0.89), 0.18, 0.06, "Vision process (E/F)", "#FCE4D6", fontsize=8.5)
    arrow(ax, (0.18, 0.80), (0.24, 0.80))
    arrow(ax, (0.40, 0.80), (0.47, 0.80))
    arrow(ax, (0.65, 0.80), (0.74, 0.80))
    arrow(ax, (0.56, 0.89), (0.56, 0.85))
    arrow(ax, (0.74, 0.77), (0.65, 0.77), color="#8C6D31")
    ax.text(0.69, 0.74, "force/state", fontsize=7.5, ha="center", color="#6D551F")

    ax.text(0.02, 0.64, "B. Three intervention descriptions retained", fontweight="bold", fontsize=12)
    n = draw_box(ax, (0.04, 0.47), 0.22, 0.11, "Nominal mode\nsource-code intention", "#F2F2F2")
    c = draw_box(ax, (0.39, 0.47), 0.22, 0.11, "Commanded state\nrow-level parameters", "#FFF2CC")
    r = draw_box(ax, (0.74, 0.47), 0.22, 0.11, "Realized logged intervention\nevents + trajectories", "#DDEBF7")
    arrow(ax, (0.26, 0.525), (0.39, 0.525))
    arrow(ax, (0.61, 0.525), (0.74, 0.525))
    ax.text(0.325, 0.548, "implemented by", ha="center", fontsize=7.5)
    ax.text(0.675, 0.548, "reconstructed as", ha="center", fontsize=7.5)
    ax.text(
        0.50,
        0.42,
        "Mode labels were not assumed to equal trial-level realized exposure.",
        ha="center",
        fontsize=9.5,
        fontweight="bold",
        color="#9C2F2F",
    )

    ax.text(0.02, 0.33, "C. Read-only provenance and clean analysis", fontweight="bold", fontsize=12)
    d1 = draw_box(ax, (0.03, 0.12), 0.20, 0.13, "CSV + events + summary\nSHA-256 verified\n186 / 186 records", "#F2F2F2")
    d2 = draw_box(ax, (0.29, 0.12), 0.18, 0.13, "Master manifest\n180 selected trials\n6 errors retained", "#FCE4D6")
    d3 = draw_box(ax, (0.53, 0.12), 0.18, 0.13, "Timing, metrics, and\ncontact-aligned\nreconstruction", "#E2F0D9")
    d4 = draw_box(ax, (0.77, 0.12), 0.19, 0.13, "Participant means\nindependent unit n = 5\npaired contrasts", "#DDEBF7")
    arrow(ax, (0.23, 0.185), (0.29, 0.185))
    arrow(ax, (0.47, 0.185), (0.53, 0.185))
    arrow(ax, (0.71, 0.185), (0.77, 0.185))
    ax.text(0.50, 0.035, "Original acquisition files remain read-only; all plotted values derive from 03_clean_analysis.", ha="center", fontsize=8.5)
    save_figure(fig, out, "figure1_reconstruction_framework", dpi)


def participant_y_positions(frame: pd.DataFrame, value_col: str) -> tuple[np.ndarray, list[str]]:
    values = []
    labels = []
    for participant in sorted(frame["participant"].unique()):
        rows = frame[frame["participant"].eq(participant)].sort_values([value_col, "record_id"])
        offsets = np.linspace(-0.24, 0.24, len(rows)) if len(rows) > 1 else np.array([0.0])
        for offset in offsets:
            values.append(sorted(frame["participant"].unique()).index(participant) + offset)
        labels.extend([participant] * len(rows))
    return np.asarray(values), labels


def plot_timing_points(
    ax: plt.Axes,
    frame: pd.DataFrame,
    value_col: str,
    title: str,
    zero_label: str,
    annotation: str,
    mode_markers: dict[str, str] | None = None,
    intended_gate: float | None = None,
) -> None:
    participants = sorted(frame["participant"].unique())
    for participant in participants:
        rows = frame[frame["participant"].eq(participant)].sort_values([value_col, "record_id"])
        offsets = np.linspace(-0.24, 0.24, len(rows)) if len(rows) > 1 else np.array([0.0])
        y = participants.index(participant) + offsets
        if mode_markers:
            for mode_code, sub in rows.groupby("mode_code", sort=False):
                row_indices = rows.index.get_indexer(sub.index)
                ax.scatter(
                    sub[value_col],
                    y[row_indices],
                    s=28,
                    marker=mode_markers[mode_code],
                    facecolor=MODE_COLORS[mode_code],
                    edgecolor="white",
                    linewidth=0.4,
                    alpha=0.85,
                )
        else:
            mode_code = str(rows["mode_code"].iloc[0])
            ax.scatter(
                rows[value_col],
                y,
                s=25,
                color=PARTICIPANT_COLORS[participant],
                edgecolor="white",
                linewidth=0.35,
                alpha=0.85,
            )
    median = float(frame[value_col].median())
    ax.axvline(0, color="#444444", linestyle="--", linewidth=1.0, label=zero_label)
    ax.axvline(median, color="#111111", linewidth=2.0, alpha=0.85)
    if intended_gate is not None:
        ax.axvline(intended_gate, color="#B22222", linestyle=":", linewidth=1.8)
    ax.set_yticks(range(len(participants)), participants)
    ax.set_ylim(len(participants) - 0.55, -0.55)
    ax.set_xlabel("Time offset (s)")
    ax.set_title(title, loc="left")
    ax.grid(axis="x", alpha=0.18)
    ax.text(
        0.02,
        0.98,
        annotation,
        transform=ax.transAxes,
        va="top",
        fontsize=8,
        bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": "#CCCCCC", "alpha": 0.9},
    )


def figure2_timing(data: dict[str, pd.DataFrame], out: Path, source: Path, dpi: int) -> None:
    timing = data["timing_audit.csv"].copy()
    extracts = []
    specs = [
        ("A", timing[timing["mode_code"].eq("G")], "force_activation_minus_task_start_s"),
        ("B", timing[timing["mode_code"].eq("G")], "force_activation_minus_contact_s"),
        ("C", timing[timing["mode_code"].eq("F")], "force_activation_minus_contact_s"),
        ("D", timing[timing["mode_code"].isin(["E", "F"])], "vision_lock_minus_contact_s"),
    ]
    for panel, frame, value in specs:
        extract = frame[["record_id", "participant", "material", "block", "mode_code", value]].copy()
        extract.insert(0, "panel", panel)
        extract = extract.rename(columns={value: "time_offset_s"})
        extracts.append(extract)
    pd.concat(extracts, ignore_index=True).to_csv(source / "figure2_timing_points.csv", index=False)

    fig, axes = plt.subplots(2, 2, figsize=(11.2, 7.4))
    plot_timing_points(
        axes[0, 0],
        specs[0][1],
        specs[0][2],
        "G activation relative to task start",
        "task start",
        "42/45 before task start\nmedian = −0.379 s",
    )
    panel_label(axes[0, 0], "A")
    plot_timing_points(
        axes[0, 1],
        specs[1][1],
        specs[1][2],
        "G activation relative to logged contact",
        "contact",
        "43/45 before contact\nmedian = −1.214 s",
    )
    panel_label(axes[0, 1], "B")
    plot_timing_points(
        axes[1, 0],
        specs[2][1],
        specs[2][2],
        "F activation relative to logged contact",
        "contact",
        "42/45 before nominal +0.20 s\nmedian = +0.053 s",
        intended_gate=0.20,
    )
    panel_label(axes[1, 0], "C")
    plot_timing_points(
        axes[1, 1],
        specs[3][1],
        specs[3][2],
        "Vision lock relative to logged contact",
        "contact",
        "post-contact lock: E 5/45; F 3/45\nmedians: E −0.755 s; F −0.941 s",
        mode_markers={"E": "o", "F": "s"},
    )
    panel_label(axes[1, 1], "D")
    handles = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=MODE_COLORS["E"], label="E", markersize=6),
        Line2D([0], [0], marker="s", color="none", markerfacecolor=MODE_COLORS["F"], label="F", markersize=6),
        Line2D([0], [0], color="#111111", linewidth=2, label="median"),
        Line2D([0], [0], color="#444444", linestyle="--", label="event zero"),
        Line2D([0], [0], color="#B22222", linestyle=":", label="nominal F gate"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=5, bbox_to_anchor=(0.5, -0.01))
    fig.suptitle("Nominal versus realized logged intervention timing", y=1.01, fontsize=12, fontweight="bold")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    save_figure(fig, out, "figure2_realized_timing_audit", dpi)


def figure3_ea_tradeoff(data: dict[str, pd.DataFrame], out: Path, source: Path, dpi: int) -> None:
    participant = data["participant_level_metrics.csv"].copy()
    stats = data["statistics_summary.csv"].copy()
    metrics = [
        (PRIMARY_METRIC, "Threshold-referenced excess-force\nimpulse, 0.20–1.00 s (N·s)", "N·s"),
        ("approach_time_s", "Task-start-to-contact time (s)", "s"),
        ("total_task_time_s", "Total task time (s)", "s"),
    ]
    source_rows = []
    fig, axes = plt.subplots(3, 2, figsize=(9.6, 9.2), gridspec_kw={"width_ratios": [1.35, 1]})
    for row_index, (metric, label, unit) in enumerate(metrics):
        wide = participant.pivot(index="participant", columns="mode_code", values=metric)[["A", "E"]]
        stat = stats[(stats["metric"].eq(metric)) & (stats["contrast"].eq("E-A"))].iloc[0]
        ax_pair = axes[row_index, 0]
        for participant_id, values in wide.iterrows():
            color = PARTICIPANT_COLORS[participant_id]
            ax_pair.plot([0, 1], values.to_numpy(float), color=color, marker="o", linewidth=1.5, markersize=5)
            for mode_code in ["A", "E"]:
                source_rows.append(
                    {
                        "metric": metric,
                        "participant": participant_id,
                        "mode_code": mode_code,
                        "participant_mean": float(values[mode_code]),
                        "contrast": "E-A",
                        "raw_mean_difference": float(stat["raw_mean_difference"]),
                        "ci95_low": float(stat["ci95_low"]),
                        "ci95_high": float(stat["ci95_high"]),
                    }
                )
        ax_pair.set_xticks([0, 1], ["A\nfixed logged", "E\nvision-enabled bundle"])
        ax_pair.set_xlim(-0.25, 1.25)
        ax_pair.set_ylabel(label)
        ax_pair.grid(axis="y", alpha=0.20)
        if row_index == 0:
            ax_pair.set_title("Paired participant means (n = 5)", loc="left")
        panel_label(ax_pair, chr(ord("A") + row_index * 2))

        ax_diff = axes[row_index, 1]
        diff = float(stat["raw_mean_difference"])
        low = float(stat["ci95_low"])
        high = float(stat["ci95_high"])
        ax_diff.axvline(0, color="#555555", linestyle="--", linewidth=1)
        ax_diff.errorbar(
            diff,
            0,
            xerr=np.array([[diff - low], [high - diff]]),
            fmt="D",
            color="#111111",
            markerfacecolor=MODE_COLORS["E"],
            markersize=7,
            capsize=4,
            linewidth=1.8,
        )
        ax_diff.set_yticks([])
        ax_diff.set_ylim(-0.8, 0.8)
        pad = max(abs(low), abs(high), 1e-9) * 0.30
        ax_diff.set_xlim(min(low, 0) - pad, max(high, 0) + pad)
        ax_diff.set_xlabel(f"E − A mean difference ({unit})")
        ax_diff.grid(axis="x", alpha=0.20)
        ax_diff.text(
            0.02,
            0.92,
            f"{diff:+.4f} [{low:+.4f}, {high:+.4f}]",
            transform=ax_diff.transAxes,
            va="top",
            fontsize=8.5,
            bbox={"boxstyle": "round,pad=0.18", "facecolor": "white", "edgecolor": "none", "alpha": 0.92},
        )
        if row_index == 0:
            ax_diff.set_title("Mean difference and t-based 95% CI", loc="left")
        panel_label(ax_diff, chr(ord("B") + row_index * 2))

    pd.DataFrame(source_rows).to_csv(source / "figure3_ea_participant_means_and_contrasts.csv", index=False)
    handles = [
        Line2D([0], [0], color=color, marker="o", label=participant, markersize=5)
        for participant, color in PARTICIPANT_COLORS.items()
    ]
    fig.legend(handles=handles, loc="lower center", ncol=5, bbox_to_anchor=(0.5, -0.005), title="Participant")
    fig.suptitle("E–A force-exposure and timing pattern", y=1.005, fontsize=12, fontweight="bold")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    save_figure(fig, out, "figure3_ea_safety_efficiency", dpi)


def figure4_trajectories(data: dict[str, pd.DataFrame], out: Path, source: Path, dpi: int) -> None:
    summary = data["contact_aligned_summary.csv"].copy()
    columns = [
        "mode_code",
        "t_rel_contact_s",
        "n_participants",
        "excess_force_N_mean",
        "excess_force_N_ci95_low",
        "excess_force_N_ci95_high",
        "stiffness_trans_N_m_mean",
        "stiffness_trans_N_m_ci95_low",
        "stiffness_trans_N_m_ci95_high",
    ]
    summary[columns].to_csv(source / "figure4_contact_aligned_summary.csv", index=False)

    fig, axes = plt.subplots(2, 1, figsize=(10.0, 7.2), sharex=True)
    for mode_code in MODE_ORDER:
        group = summary[summary["mode_code"].eq(mode_code)].sort_values("t_rel_contact_s")
        x = group["t_rel_contact_s"].to_numpy(float)
        fmean = group["excess_force_N_mean"].to_numpy(float)
        flow = group["excess_force_N_ci95_low"].to_numpy(float)
        fhigh = group["excess_force_N_ci95_high"].to_numpy(float)
        kmean = group["stiffness_trans_N_m_mean"].to_numpy(float)
        klow = group["stiffness_trans_N_m_ci95_low"].to_numpy(float)
        khigh = group["stiffness_trans_N_m_ci95_high"].to_numpy(float)
        axes[0].plot(x, fmean, color=MODE_COLORS[mode_code], linewidth=2, label=mode_code)
        axes[0].fill_between(x, flow, fhigh, color=MODE_COLORS[mode_code], alpha=0.13, linewidth=0)
        axes[1].plot(x, kmean, color=MODE_COLORS[mode_code], linewidth=2, label=mode_code)
        axes[1].fill_between(x, klow, khigh, color=MODE_COLORS[mode_code], alpha=0.13, linewidth=0)
    for ax in axes:
        ax.axvline(0, color="#444444", linestyle="--", linewidth=1)
        ax.grid(alpha=0.18)
    axes[0].axvspan(0.20, 1.00, color="#6C757D", alpha=0.08, label="0.20–1.00-s metric window")
    axes[0].set_ylabel("Threshold-referenced\nexcess force (N)")
    axes[1].set_ylabel("Logged commanded translational\nstiffness (N/m)")
    axes[1].set_xlabel("Time from logged contact (s)")
    axes[0].set_title("Participant-aggregated force trajectories", loc="left")
    axes[1].set_title("Participant-aggregated commanded-stiffness trajectories", loc="left")
    panel_label(axes[0], "A")
    panel_label(axes[1], "B")
    axes[0].legend(ncol=5, loc="upper right")
    fig.suptitle("Contact-aligned realized logged trajectories (mean and pointwise 95% CI; n = 5)", y=1.01, fontsize=12, fontweight="bold")
    fig.tight_layout()
    save_figure(fig, out, "figure4_contact_aligned_trajectories", dpi)


def forest_axis(ax: plt.Axes, full: pd.Series, lopo: pd.DataFrame, title: str) -> None:
    rows = [
        ("Full sample", float(full["raw_mean_difference"]), float(full["ci95_low"]), float(full["ci95_high"]), True)
    ]
    for _, row in lopo.sort_values("left_out_participant").iterrows():
        rows.append(
            (
                f"Without {row['left_out_participant']}",
                float(row["lopo_mean_difference"]),
                float(row["lopo_ci95_low"]),
                float(row["lopo_ci95_high"]),
                False,
            )
        )
    y = np.arange(len(rows))[::-1]
    for ypos, (label, mean, low, high, is_full) in zip(y, rows):
        ax.errorbar(
            mean,
            ypos,
            xerr=np.array([[mean - low], [high - mean]]),
            fmt="D" if is_full else "o",
            color="#111111" if is_full else "#5F6B75",
            markerfacecolor="#111111" if is_full else "white",
            capsize=3,
            markersize=6 if is_full else 5,
            linewidth=1.6 if is_full else 1.1,
        )
    ax.axvline(0, color="#B22222", linestyle="--", linewidth=1)
    ax.set_yticks(y, [row[0] for row in rows])
    ax.set_xlabel("Mean difference (N·s)")
    ax.set_title(title, loc="left")
    ax.grid(axis="x", alpha=0.18)


def figure5_lopo(data: dict[str, pd.DataFrame], out: Path, source: Path, dpi: int) -> None:
    participant = data["participant_level_metrics.csv"].copy()
    stats = data["statistics_summary.csv"].copy()
    lopo = data["leave_one_participant_out.csv"].copy()
    wide = participant.pivot(index="participant", columns="mode_code", values=PRIMARY_METRIC)
    individual = pd.DataFrame(
        {
            "participant": wide.index,
            "E_minus_A_Ns": wide["E"] - wide["A"],
            "F_minus_E_Ns": wide["F"] - wide["E"],
        }
    ).reset_index(drop=True)
    full = stats[stats["metric"].eq(PRIMARY_METRIC)].copy()
    lopo_primary = lopo[lopo["metric"].eq(PRIMARY_METRIC)].copy()
    source_full = full[
        ["metric", "contrast", "n_participants", "raw_mean_difference", "ci95_low", "ci95_high"]
    ].copy()
    source_full.insert(2, "estimate_set", "full_sample")
    source_lopo = lopo_primary.rename(
        columns={
            "n_remaining": "n_participants",
            "lopo_mean_difference": "raw_mean_difference",
            "lopo_ci95_low": "ci95_low",
            "lopo_ci95_high": "ci95_high",
        }
    )[["metric", "contrast", "left_out_participant", "n_participants", "raw_mean_difference", "ci95_low", "ci95_high", "same_direction_as_full"]]
    individual.to_csv(source / "figure5_individual_differences.csv", index=False)
    source_full.to_csv(source / "figure5_full_estimates.csv", index=False)
    source_lopo.to_csv(source / "figure5_lopo_estimates.csv", index=False)

    fig, axes = plt.subplots(1, 3, figsize=(13.2, 5.3), gridspec_kw={"width_ratios": [0.9, 1.25, 1.25]})
    ind = individual.sort_values("participant")
    y = np.arange(len(ind))[::-1]
    axes[0].axvline(0, color="#B22222", linestyle="--", linewidth=1)
    axes[0].scatter(ind["E_minus_A_Ns"], y, color=[PARTICIPANT_COLORS[p] for p in ind["participant"]], s=55, zorder=3)
    for ypos, value in zip(y, ind["E_minus_A_Ns"]):
        axes[0].plot([0, value], [ypos, ypos], color="#AAB1B7", linewidth=1.2, zorder=1)
    axes[0].set_yticks(y, ind["participant"])
    axes[0].set_xlabel("E − A difference (N·s)")
    axes[0].set_title("Individual participant differences", loc="left")
    axes[0].grid(axis="x", alpha=0.18)
    panel_label(axes[0], "A")

    ea_full = full[full["contrast"].eq("E-A")].iloc[0]
    ea_lopo = lopo_primary[lopo_primary["contrast"].eq("E-A")]
    forest_axis(axes[1], ea_full, ea_lopo, "E–A full and LOPO estimates")
    panel_label(axes[1], "B")

    fe_full = full[full["contrast"].eq("F-E")].iloc[0]
    fe_lopo = lopo_primary[lopo_primary["contrast"].eq("F-E")]
    forest_axis(axes[2], fe_full, fe_lopo, "F–E full and LOPO estimates")
    panel_label(axes[2], "C")
    fig.suptitle("Participant consistency and leave-one-participant-out stability", y=1.02, fontsize=12, fontweight="bold")
    fig.tight_layout()
    save_figure(fig, out, "figure5_participant_lopo_stability", dpi)


CHINESE_NUMERALS = {
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
    "十一": 11,
    "十二": 12,
    "十三": 13,
    "十四": 14,
    "十五": 15,
}


def block_number(text: str) -> str:
    match = re.search(r"第(.+?)(?:组实验|次实验)", str(text))
    return f"B{CHINESE_NUMERALS.get(match.group(1), match.group(1)):02}" if match else str(text)


def nearest_to_median(frame: pd.DataFrame, value_col: str) -> pd.Series:
    eligible = frame[frame[value_col].notna()].copy()
    median = float(eligible[value_col].median())
    eligible["distance_to_class_median"] = (eligible[value_col] - median).abs()
    return eligible.sort_values(["distance_to_class_median", "record_id"]).iloc[0]


def plot_trace(
    ax: plt.Axes,
    trajectory: pd.DataFrame,
    event_time: float,
    event_label: str,
    title: str,
    intended_gate: float | None = None,
) -> None:
    trajectory = trajectory.sort_values("t_rel_contact_s")
    x = trajectory["t_rel_contact_s"].to_numpy(float)
    force = trajectory["force_estimated_N"].to_numpy(float)
    stiffness = trajectory["stiffness_trans_N_m"].to_numpy(float)
    ax.plot(x, force, color="#4E79A7", linewidth=1.8, label="estimated force")
    ax.axvline(0, color="#444444", linestyle="--", linewidth=1, label="contact")
    ax.axvline(event_time, color="#B22222", linewidth=1.6, label=event_label)
    if intended_gate is not None:
        ax.axvline(intended_gate, color="#B22222", linestyle=":", linewidth=1.5, label="nominal +0.20 s")
    ax.set_xlabel("Time from logged contact (s)")
    ax.set_ylabel("Estimated force (N)", color="#4E79A7")
    ax.tick_params(axis="y", labelcolor="#4E79A7")
    ax.grid(alpha=0.15)
    ax2 = ax.twinx()
    ax2.plot(x, stiffness, color="#59A14F", linewidth=1.5, label="commanded stiffness")
    ax2.set_ylabel("Logged stiffness (N/m)", color="#39733F")
    ax2.tick_params(axis="y", labelcolor="#39733F")
    ax.set_title(title, loc="left", fontsize=9.5)


def figure6_lineage_examples(data: dict[str, pd.DataFrame], out: Path, source: Path, dpi: int) -> None:
    manifest = data["master_trial_manifest.csv"].copy()
    timing = data["timing_audit.csv"].copy()
    trajectories = data["contact_aligned_trajectories.csv"].copy()
    mapping = manifest[manifest["duplicate_count"].eq(2)].sort_values(["trial_key", "duplicate_rank"]).copy()
    mapping.to_csv(source / "figure6_error_replacement_mapping.csv", index=False)

    g = nearest_to_median(timing[timing["mode_code"].eq("G")], "force_activation_minus_contact_s")
    f = nearest_to_median(timing[timing["mode_code"].eq("F")], "force_activation_minus_contact_s")
    vision_eligible = timing[timing["mode_code"].isin(["E", "F"]) & (timing["vision_lock_minus_contact_s"] >= 0)]
    vision = nearest_to_median(vision_eligible, "vision_lock_minus_contact_s")
    selections = pd.DataFrame(
        [
            {"example": "G_nearest_class_median_activation_contact", **g.to_dict()},
            {"example": "F_nearest_class_median_activation_contact", **f.to_dict()},
            {"example": "post_contact_vision_nearest_class_median", **vision.to_dict()},
        ]
    )
    selections.to_csv(source / "figure6_representative_trial_selection.csv", index=False)
    selected_ids = selections["record_id"].tolist()
    trajectories[trajectories["record_id"].isin(selected_ids)].to_csv(source / "figure6_representative_trajectories.csv", index=False)

    fig = plt.figure(figsize=(13.0, 8.0))
    grid = fig.add_gridspec(2, 2, width_ratios=[1.08, 1], hspace=0.38, wspace=0.34)
    ax_a = fig.add_subplot(grid[0, 0])
    ax_b = fig.add_subplot(grid[0, 1])
    ax_c = fig.add_subplot(grid[1, 0])
    ax_d = fig.add_subplot(grid[1, 1])

    ax_a.axis("off")
    ax_a.set_xlim(0, 1)
    ax_a.set_ylim(0, 1)
    panel_label(ax_a, "A")
    ax_a.set_title("Known-error records retained and replaced deterministically", loc="left", fontsize=9.5)
    ax_a.text(0.10, 0.92, "Trial key", ha="center", fontweight="bold", color="#343A40")
    ax_a.text(0.40, 0.92, "Excluded 20260729", ha="center", fontweight="bold", color="#9C2F2F")
    ax_a.text(0.83, 0.92, "Selected 20260730", ha="center", fontweight="bold", color="#2E6E3E")
    pairs = []
    for trial_key, group in mapping.groupby("trial_key", sort=True):
        err = group[group["analysis_role"].eq("excluded_known_error")].iloc[0]
        rep = group[group["analysis_role"].eq("main_valid_replacement")].iloc[0]
        pairs.append((err, rep))
    for idx, (err, rep) in enumerate(pairs):
        y = 0.80 - idx * 0.125
        mode_code = {"default": "A", "force_only": "G", "vision": "E", "vision_force": "F"}[err["mode"]]
        key_label = f"{err['participant']}/{err['material']}/{block_number(err['block'])}/{mode_code}"
        err_time = str(err["timestamp"])[-6:]
        rep_time = str(rep["timestamp"])[-6:]
        err_time = f"{err_time[:2]}:{err_time[2:4]}:{err_time[4:]}"
        rep_time = f"{rep_time[:2]}:{rep_time[2:4]}:{rep_time[4:]}"
        ax_a.text(0.01, y, key_label, va="center", fontsize=7.4)
        ax_a.text(0.40, y, err_time, va="center", ha="center", fontsize=7.6, color="#9C2F2F")
        ax_a.annotate("", xy=(0.69, y), xytext=(0.51, y), arrowprops={"arrowstyle": "-|>", "color": "#68737D", "lw": 1.1})
        ax_a.text(0.83, y, rep_time, va="center", ha="center", fontsize=7.6, color="#2E6E3E")
    ax_a.text(0.50, 0.03, "Both record identities and hashes remain in the master manifest.", ha="center", fontsize=7.8)

    g_activation_contact = float(g["force_activation_minus_contact_s"])
    g_activation_task = float(g["force_activation_minus_task_start_s"])
    g_task_contact = g_activation_contact - g_activation_task
    g_activation_baseline = float(g["force_activation_minus_baseline_ready_s"])
    g_baseline_contact = g_activation_contact - g_activation_baseline
    ax_b.set_title("G example nearest median pre-contact activation", loc="left", fontsize=9.5)
    panel_label(ax_b, "B")
    ax_b.axvline(0, color="#444444", linestyle="--", linewidth=1)
    events = [
        (g_baseline_contact, "baseline ready", "#7A7A7A"),
        (g_task_contact, "task start", "#4E79A7"),
        (g_activation_contact, "G activation", "#D55E00"),
        (0.0, "contact", "#111111"),
    ]
    for row, (xvalue, label, color) in enumerate(events[::-1]):
        ypos = row
        ax_b.scatter(xvalue, ypos, s=58, color=color, zorder=3)
        ax_b.plot([min(xvalue, 0), max(xvalue, 0)], [ypos, ypos], color="#CCD1D5", linewidth=1)
        ax_b.text(xvalue, ypos + 0.18, f"{xvalue:+.3f} s", ha="center", fontsize=7.5)
    ax_b.set_yticks(range(4), [e[1] for e in events[::-1]])
    ax_b.set_xlabel("Time from logged contact (s)")
    ax_b.grid(axis="x", alpha=0.18)
    ax_b.text(
        0.02,
        0.04,
        f"raw force at activation = {float(g['raw_estimated_force_at_activation_N']):.3f} N\n"
        f"trial contact threshold = {float(g['contact_detection_threshold_N']):.3f} N",
        transform=ax_b.transAxes,
        fontsize=7.8,
        bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": "#CCCCCC"},
    )

    f_trace = trajectories[trajectories["record_id"].eq(f["record_id"])]
    plot_trace(
        ax_c,
        f_trace,
        float(f["force_activation_minus_contact_s"]),
        "F first activation",
        f"F example nearest median activation ({f['participant']}, {f['material']}, {block_number(f['block'])})",
        intended_gate=0.20,
    )
    panel_label(ax_c, "C")

    v_trace = trajectories[trajectories["record_id"].eq(vision["record_id"])]
    plot_trace(
        ax_d,
        v_trace,
        float(vision["vision_lock_minus_contact_s"]),
        "vision lock",
        f"Post-contact vision-lock example nearest median ({vision['mode_code']}, {vision['participant']}, {vision['material']}, {block_number(vision['block'])})",
    )
    panel_label(ax_d, "D")
    fig.suptitle("Data-lineage repair and deterministic implementation-deviation examples", y=0.99, fontsize=12, fontweight="bold")
    save_figure(fig, out, "figure6_lineage_trace_examples", dpi)


def write_metadata(clean_dir: Path, out: Path, source: Path, dpi: int) -> None:
    input_names = [
        "master_trial_manifest.csv",
        "data_lineage_audit.csv",
        "participant_level_metrics.csv",
        "statistics_summary.csv",
        "leave_one_participant_out.csv",
        "timing_audit.csv",
        "contact_aligned_summary.csv",
        "contact_aligned_trajectories.csv",
        "trial_level_metrics.csv",
    ]
    metadata = {
        "script": str(Path(__file__).resolve()),
        "clean_analysis_directory": str(clean_dir.resolve()),
        "output_directory": str(out.resolve()),
        "source_data_directory": str(source.resolve()),
        "dpi": dpi,
        "python": sys.version,
        "platform": platform.platform(),
        "packages": {
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "matplotlib": matplotlib.__version__,
            "scipy": scipy.__version__,
        },
        "input_sha256": {name: sha256(clean_dir / name) for name in input_names},
        "figure_output_sha256": {
            path.name: sha256(path)
            for path in sorted(out.glob("figure[1-6]_*.png")) + sorted(out.glob("figure[1-6]_*.pdf"))
        },
        "figure_source_data_sha256": {
            path.name: sha256(path) for path in sorted(source.glob("figure*.csv"))
        },
        "selection_rule_figure6": "minimum absolute distance to the eligible class median; record_id breaks ties",
    }
    (source / "figure_generation_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    clean_dir = args.clean_dir.resolve()
    output_dir = args.output_dir.resolve()
    source_data_dir = args.source_data_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    source_data_dir.mkdir(parents=True, exist_ok=True)
    data = load_inputs(clean_dir)
    validate_inputs(data)
    set_style()
    figure1_framework(data, output_dir, source_data_dir, args.dpi)
    figure2_timing(data, output_dir, source_data_dir, args.dpi)
    figure3_ea_tradeoff(data, output_dir, source_data_dir, args.dpi)
    figure4_trajectories(data, output_dir, source_data_dir, args.dpi)
    figure5_lopo(data, output_dir, source_data_dir, args.dpi)
    figure6_lineage_examples(data, output_dir, source_data_dir, args.dpi)
    write_metadata(clean_dir, output_dir, source_data_dir, args.dpi)
    print(f"Generated Figures 1--6 in: {output_dir}")
    print(f"Wrote figure source data in: {source_data_dir}")


if __name__ == "__main__":
    main()
