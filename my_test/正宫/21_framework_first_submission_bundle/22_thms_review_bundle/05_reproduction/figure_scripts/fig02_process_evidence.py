#!/usr/bin/env python3
"""Generate a data-grounded event-to-outcome process figure and optional setup composite."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

from figure_common import prepare_run, read_clean_csv, record_manifest, write_source_csv
from figure_style import (
    MODE_COLORS,
    MODE_LINESTYLES,
    MODE_ORDER,
    figure_size,
    light_horizontal_grid,
    panel_label,
    save_publication_figure,
    set_publication_style,
)


PROCESS_STEM = "Fig02_process_evidence"
COMPOSITE_STEM = "Fig02_experimental_setup_and_process"
OUTCOME_WINDOW = (0.20, 1.00)
EVENT_VIEW = (-2.0, 1.20)
EVENT_COLORS = {
    "vision_lock": "#009E73",
    "transition_complete": "#4E9D85",
    "force_activation": "#D55E00",
}

SUMMARY_COLUMNS = [
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
TRIAL_COLUMNS = [
    "record_id",
    "participant",
    "mode_code",
    "vision_lock_system_s",
    "transition_complete_system_s",
    "adaptation_activation_system_s",
    "contact_system_s",
]


def build_event_source(trials: pd.DataFrame) -> pd.DataFrame:
    f = trials.loc[trials["mode_code"].eq("F")].copy()
    specs = [
        ("vision_lock", "vision_lock_system_s"),
        ("transition_complete", "transition_complete_system_s"),
        ("force_activation", "adaptation_activation_system_s"),
    ]
    rows: list[pd.DataFrame] = []
    for event, column in specs:
        frame = f[["record_id", "participant", column, "contact_system_s"]].copy()
        frame["row_type"] = "event"
        frame["event"] = event
        frame["t_rel_contact_s"] = frame[column] - frame["contact_system_s"]
        rows.append(frame[["row_type", "record_id", "participant", "event", "t_rel_contact_s"]])
    return pd.concat(rows, ignore_index=True)


def build_source(summary: pd.DataFrame, trials: pd.DataFrame) -> pd.DataFrame:
    curves = summary[SUMMARY_COLUMNS].copy()
    curves.insert(0, "row_type", "trajectory_summary")
    events = build_event_source(trials)
    return pd.concat([events, curves], ignore_index=True, sort=False)


def run_qa(summary: pd.DataFrame, trials: pd.DataFrame, events: pd.DataFrame) -> list[tuple[str, object, object, bool]]:
    checks: list[tuple[str, object, object, bool]] = []
    counts = summary.groupby("mode_code").size().to_dict()
    checks.append(("trajectory rows per mode", counts, {mode: 201 for mode in MODE_ORDER}, counts == {mode: 201 for mode in MODE_ORDER}))
    n_values = sorted(set(summary["n_participants"].astype(int)))
    checks.append(("participant count at each trajectory point", n_values, [5], n_values == [5]))
    f = trials.loc[trials["mode_code"].eq("F")]
    checks.append(("F trial identities", f["record_id"].nunique(), 45, f["record_id"].nunique() == 45))
    event_counts = events.groupby("event").size().to_dict()
    expected_event_counts = {"force_activation": 45, "transition_complete": 45, "vision_lock": 45}
    checks.append(("F event observations", event_counts, expected_event_counts, event_counts == expected_event_counts))
    medians = events.groupby("event")["t_rel_contact_s"].median().round(4).to_dict()
    expected_medians = {"force_activation": 0.0533, "transition_complete": -0.5449, "vision_lock": -0.9411}
    checks.append(("frozen F event medians", medians, expected_medians, medians == expected_medians))
    return checks


def write_qa(path: Path, checks: list[tuple[str, object, object, bool]]) -> bool:
    passed = all(item[3] for item in checks)
    lines = [
        "Figure 2 process evidence QA",
        f"STATUS: {'PASS' if passed else 'FAIL'}",
        "",
        "Checks:",
    ]
    for name, actual, expected, ok in checks:
        lines.append(f"[{'PASS' if ok else 'FAIL'}] {name} | actual={actual} | expected={expected}")
    lines.extend(
        [
            "",
            "The event panel uses all 45 F trials; medians and IQRs are descriptive.",
            "Trajectory curves are frozen participant-level means and pointwise t-based 95% CIs (n=5).",
            "No representative trial is selected and no smoothing or pointwise testing is introduced.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return passed


def draw_event_panel(ax: plt.Axes, events: pd.DataFrame, letter: str = "A", compact: bool = False) -> None:
    labels = [
        ("vision_lock", "Vision lock"),
        ("transition_complete", "Parameter transition complete"),
        ("force_activation", "Force-rule activation"),
    ]
    y_lookup = {event: 2 - index for index, (event, _) in enumerate(labels)}
    ax.axvspan(*OUTCOME_WINDOW, color="#E7E7E7", alpha=0.75, zorder=0)
    ax.axvline(0.0, color="#333333", linewidth=0.9, zorder=1)
    ax.axvline(OUTCOME_WINDOW[0], color="#777777", linewidth=0.65, linestyle=(0, (2, 2)), zorder=1)
    for event, label in labels:
        frame = events.loc[events["event"].eq(event)].sort_values("t_rel_contact_s", kind="stable")
        values = frame["t_rel_contact_s"].to_numpy(dtype=float)
        y = y_lookup[event]
        inside = values[(values >= EVENT_VIEW[0]) & (values <= EVENT_VIEW[1])]
        jitter = np.linspace(-0.13, 0.13, len(inside)) if len(inside) else np.array([])
        ax.scatter(inside, y + jitter, s=9 if compact else 12, color=EVENT_COLORS[event], alpha=0.38, edgecolor="none", zorder=2)
        q1, median, q3 = np.quantile(values, [0.25, 0.50, 0.75])
        ax.hlines(y, q1, q3, color=EVENT_COLORS[event], linewidth=3.0, zorder=4)
        marker = "D" if event == "force_activation" else "s"
        ax.scatter([median], [y], s=28 if compact else 36, marker=marker, color=EVENT_COLORS[event], edgecolor="white", linewidth=0.45, zorder=5)
        left_count = int((values < EVENT_VIEW[0]).sum())
        right_count = int((values > EVENT_VIEW[1]).sum())
        if left_count:
            ax.scatter([EVENT_VIEW[0] + 0.015], [y], s=18, marker="<", color=EVENT_COLORS[event], zorder=5)
            ax.text(EVENT_VIEW[0] + 0.045, y + 0.20, f"{left_count} outside", fontsize=4.8 if compact else 5.2, color=EVENT_COLORS[event], ha="left")
        if right_count:
            ax.scatter([EVENT_VIEW[1] - 0.015], [y], s=18, marker=">", color=EVENT_COLORS[event], zorder=5)
            ax.text(EVENT_VIEW[1] - 0.045, y + 0.20, f"{right_count} outside", fontsize=4.8 if compact else 5.2, color=EVENT_COLORS[event], ha="right")
        ax.text(median, y - 0.25, f"median {median:+.3f} s", fontsize=5.0 if compact else 5.5, color=EVENT_COLORS[event], ha="center", va="top")

    medians = events.groupby("event")["t_rel_contact_s"].median()
    sequence_x = [medians["vision_lock"], medians["transition_complete"], 0.0, medians["force_activation"], 0.60]
    sequence_y = [2, 1, 0.50, 0, -0.42]
    ax.plot(sequence_x, sequence_y, color="#666666", linewidth=0.7, linestyle=(0, (2, 2)), zorder=1)
    ax.text(0.0, 2.42, "contact = 0 s", fontsize=5.4 if compact else 5.9, ha="center", fontweight="bold")
    ax.text(0.60, 2.42, "analysis window", fontsize=5.2 if compact else 5.7, ha="center", color="#555555")
    ax.set_xlim(*EVENT_VIEW)
    ax.set_ylim(-0.52, 2.62)
    ax.set_yticks([2, 1, 0], [label for _, label in labels])
    ax.set_xlabel("" if compact else "Time relative to recorded contact (s)")
    event_title = (
        "Delivered F sequence and outcome-window entry"
        if compact
        else "Delivered F sequence: perception → transition → contact → activation → outcome"
    )
    ax.set_title(
        event_title,
        loc="left",
        pad=4 if compact else 5,
        fontsize=7.0 if compact else None,
    )
    panel_label(ax, letter, x=-0.18 if compact else -0.11, y=1.12)
    if compact:
        ax.tick_params(axis="both", labelsize=6.2)
        ax.tick_params(axis="y", pad=2)
        ax.set_yticklabels([label for _, label in labels], fontsize=6.1)
    ax.grid(axis="x", color="#D5D5D5", linewidth=0.45, alpha=0.65)
    ax.set_axisbelow(True)


def draw_trajectory_panel(
    ax: plt.Axes,
    summary: pd.DataFrame,
    prefix: str,
    title: str,
    ylabel: str,
    letter: str,
    compact: bool = False,
) -> None:
    ax.axvspan(*OUTCOME_WINDOW, color="#E7E7E7", alpha=0.70, zorder=0)
    endpoints: dict[str, float] = {}
    for mode in MODE_ORDER:
        frame = summary.loc[summary["mode_code"].eq(mode)].sort_values("t_rel_contact_s", kind="stable")
        x = frame["t_rel_contact_s"].to_numpy(dtype=float)
        mean = frame[f"{prefix}_mean"].to_numpy(dtype=float)
        low = frame[f"{prefix}_ci95_low"].to_numpy(dtype=float)
        high = frame[f"{prefix}_ci95_high"].to_numpy(dtype=float)
        ax.fill_between(x, low, high, color=MODE_COLORS[mode], alpha=0.08, linewidth=0, zorder=1)
        ax.plot(x, mean, color=MODE_COLORS[mode], linestyle=MODE_LINESTYLES[mode], linewidth=1.05 if compact else 1.2, zorder=3)
        endpoints[mode] = float(mean[-1])
    ax.axvline(0.0, color="#333333", linewidth=0.8, zorder=4)
    ax.set_xlim(-0.50, 1.64 if prefix == "stiffness_trans_N_m" else 1.50)
    ax.set_xlabel("" if compact and prefix == "excess_force_N" else "Time from contact (s)")
    ax.set_ylabel(ylabel)
    ax.set_title(title, loc="left", pad=3 if compact else 5, fontsize=7.0 if compact else None)
    light_horizontal_grid(ax)
    panel_label(ax, letter, x=-0.17 if compact else -0.15, y=1.12)
    if compact:
        ax.tick_params(axis="both", labelsize=6.2)
        ax.xaxis.label.set_size(6.8)
        ax.yaxis.label.set_size(6.8)
    if prefix == "stiffness_trans_N_m":
        for mode in MODE_ORDER:
            ax.text(1.535, endpoints[mode], mode, color=MODE_COLORS[mode], fontsize=5.4 if compact else 6.2, fontweight="bold", va="center", ha="left")


def mode_legend() -> list[Line2D]:
    return [
        Line2D([], [], color=MODE_COLORS[mode], linestyle=MODE_LINESTYLES[mode], linewidth=1.2, label=mode)
        for mode in MODE_ORDER
    ]


def create_process_figure(summary: pd.DataFrame, events: pd.DataFrame) -> plt.Figure:
    set_publication_style()
    fig = plt.figure(figsize=figure_size(178.0, 110.0))
    draw_event_panel(fig.add_axes([0.16, 0.61, 0.82, 0.29]), events, "A")
    draw_trajectory_panel(fig.add_axes([0.09, 0.17, 0.40, 0.31]), summary, "excess_force_N", "Realized excess-force exposure", "Excess force (N)", "B")
    draw_trajectory_panel(fig.add_axes([0.59, 0.17, 0.39, 0.31]), summary, "stiffness_trans_N_m", "Commanded stiffness trajectory", r"$K_t$ (N/m)", "C")
    fig.text(0.53, 0.055, "All 45 F trials are shown in the event panel; curves are participant-level means with pointwise 95% CIs (n=5). Shading marks contact +0.20 to +1.00 s.", ha="center", fontsize=6.1, fontstyle="italic", color="#303030")
    return fig


def create_composite_figure(summary: pd.DataFrame, events: pd.DataFrame, photo_path: Path) -> plt.Figure:
    set_publication_style()
    image = mpimg.imread(photo_path)
    fig = plt.figure(figsize=figure_size(178.0, 118.0))
    ax_photo = fig.add_axes([0.02, 0.285, 0.43, 0.53])
    ax_photo.imshow(image)
    ax_photo.axis("off")
    ax_photo.text(-0.02, 1.055, "(A)", transform=ax_photo.transAxes, fontsize=8.8, fontweight="bold", ha="left", va="bottom")
    ax_photo.text(0.075, 1.055, "Experimental setup and task workspace", transform=ax_photo.transAxes, fontsize=7.8, fontweight="bold", ha="left", va="bottom")
    draw_event_panel(fig.add_axes([0.565, 0.705, 0.415, 0.22]), events, "B", compact=True)
    draw_trajectory_panel(fig.add_axes([0.565, 0.405, 0.415, 0.205]), summary, "excess_force_N", "Force exposure entering the outcome window", "Excess force (N)", "C", compact=True)
    draw_trajectory_panel(fig.add_axes([0.565, 0.115, 0.415, 0.195]), summary, "stiffness_trans_N_m", "Logged command trajectory", r"$K_t$ (N/m)", "D", compact=True)
    fig.text(0.235, 0.245, "Real experimental photograph; supplied annotations retained without generative editing.", ha="center", fontsize=5.5, fontstyle="italic", color="#444444")
    fig.text(
        0.235,
        0.155,
        "Process panels: all 45 F trials; trajectories are participant-level means\n"
        "with pointwise 95% CIs (n=5); gray bands: contact +0.20 to +1.00 s.",
        ha="center",
        fontsize=5.2,
        fontstyle="italic",
        color="#444444",
        linespacing=1.05,
    )
    return fig


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--dpi", type=int, default=600)
    parser.add_argument("--setup-photo", type=Path, default=None, help="Original experimental setup image; it is embedded without generative editing.")
    args = parser.parse_args()
    if args.dpi < 600:
        parser.error("--dpi must be at least 600")
    project_root, clean_dir, figures_dir, source_dir = prepare_run(args, __file__)
    publication_root = project_root / "19_publication_figures"
    summary_path = clean_dir / "contact_aligned_summary.csv"
    trials_path = clean_dir / "trial_level_fidelity_metrics.csv"
    summary = read_clean_csv(clean_dir, summary_path.name, SUMMARY_COLUMNS)
    trials = read_clean_csv(clean_dir, trials_path.name, TRIAL_COLUMNS)
    events = build_event_source(trials)
    checks = run_qa(summary, trials, events)
    qa_path = publication_root / "figure02_process_qa.txt"
    if not write_qa(qa_path, checks):
        for item in checks:
            if not item[3]:
                print(f"QA FAIL: {item}", file=sys.stderr)
        raise SystemExit(1)
    source_path = write_source_csv(build_source(summary, trials), source_dir / "figure02_process_source_data.csv")
    outputs = save_publication_figure(create_process_figure(summary, events), figures_dir, PROCESS_STEM, args.dpi)
    record_manifest(publication_root, project_root, PROCESS_STEM, Path(__file__), [summary_path, trials_path], source_path, [*outputs, qa_path])
    packaged_photo = Path(__file__).resolve().parents[1] / "assets" / "experimental_setup.jpg"
    photo_path = args.setup_photo.resolve() if args.setup_photo is not None else packaged_photo
    if args.setup_photo is not None and not photo_path.is_file():
        raise FileNotFoundError(f"Setup photo not found: {photo_path}")
    if photo_path.is_file():
        composite_outputs = save_publication_figure(create_composite_figure(summary, events, photo_path), figures_dir, COMPOSITE_STEM, args.dpi)
        record_manifest(publication_root, project_root, COMPOSITE_STEM, Path(__file__), [summary_path, trials_path, photo_path], source_path, composite_outputs)
        print(f"Generated {COMPOSITE_STEM} with unmodified setup photo: {photo_path}")
    print(f"Generated {PROCESS_STEM}; process QA PASS ({sum(item[3] for item in checks)}/{len(checks)})")


if __name__ == "__main__":
    main()
