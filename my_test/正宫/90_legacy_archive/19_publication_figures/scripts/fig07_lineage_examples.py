#!/usr/bin/env python3
"""Generate Figure 7: lineage repair and deterministic implementation-deviation examples."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from figure_common import parse_root_args, prepare_run, read_clean_csv, record_manifest, write_source_csv
from figure_style import MODE_COLORS, figure_size, panel_label, save_publication_figure, set_publication_style


STEM = "Fig07_lineage_trace_examples"


def nearest_record(frame: pd.DataFrame, column: str, target: float) -> str:
    ranked = frame.assign(distance=(frame[column] - target).abs()).sort_values(["distance", "record_id"], kind="stable")
    return str(ranked.iloc[0]["record_id"])


def trace_panel(ax, trace, events, title, letter, event_name, event_time, nominal_time=None):
    x = trace["t_rel_contact_s"].to_numpy(float)
    force = trace["excess_force_N"].to_numpy(float)
    stiffness = trace["stiffness_trans_N_m"].to_numpy(float)
    force_line = ax.plot(x, force, color="#0072B2", linewidth=1.15, label="Excess force")[0]
    ax.axvline(0, color="#222222", linewidth=0.75, linestyle="--")
    ax.axvline(event_time, color=MODE_COLORS[events["mode_code"]], linewidth=1.0)
    if nominal_time is not None:
        ax.axvline(nominal_time, color="#8C2D04", linewidth=0.85, linestyle=":")
    ax.set_xlim(-0.5, 1.5)
    ax.set_xlabel("Time relative to contact (s)")
    ax.set_ylabel("Excess force (N)", color="#0072B2")
    ax.tick_params(axis="y", colors="#0072B2")
    ax2 = ax.twinx()
    stiffness_line = ax2.plot(x, stiffness, color="#009E73", linewidth=1.05, linestyle="--", label="Commanded stiffness")[0]
    ax2.set_ylabel("Stiffness (N/m)", color="#009E73")
    ax2.tick_params(axis="y", colors="#009E73")
    ax2.spines["right"].set_visible(True)
    ax.set_title(title, loc="left")
    ax.text(0.03, 0.96, f"{event_name}: {event_time:+.3f} s", transform=ax.transAxes, va="top", fontsize=7.0)
    ax.legend([force_line, stiffness_line], ["Excess force", "Commanded stiffness"], loc="upper right")
    panel_label(ax, letter)


def main() -> None:
    args = parse_root_args(__doc__ or "")
    project_root, clean_dir, figures_dir, source_dir = prepare_run(args, __file__)
    manifest_path = clean_dir / "master_trial_manifest.csv"
    timing_path = clean_dir / "timing_audit.csv"
    trajectories_path = clean_dir / "contact_aligned_trajectories.csv"
    manifest = read_clean_csv(clean_dir, manifest_path.name, ["record_id", "trial_key", "timestamp", "duplicate_count", "analysis_role", "included_main_clean"])
    timing = read_clean_csv(clean_dir, timing_path.name, ["record_id", "participant", "material", "block", "mode_code", "force_activation_minus_task_start_s", "force_activation_minus_contact_s", "vision_lock_minus_contact_s"])
    trajectories = read_clean_csv(clean_dir, trajectories_path.name, ["record_id", "mode_code", "t_rel_contact_s", "excess_force_N", "stiffness_trans_N_m"])

    duplicates = manifest[manifest["duplicate_count"].gt(1)].copy().sort_values(["trial_key", "timestamp"], kind="stable")
    g = timing[timing["mode_code"].eq("G")].dropna(subset=["force_activation_minus_contact_s"])
    f = timing[timing["mode_code"].eq("F")].dropna(subset=["force_activation_minus_contact_s"])
    post_vision = timing[timing["mode_code"].isin(["E", "F"]) & timing["vision_lock_minus_contact_s"].gt(0)].dropna(subset=["vision_lock_minus_contact_s"])
    g_id = nearest_record(g, "force_activation_minus_contact_s", float(g["force_activation_minus_contact_s"].median()))
    f_id = nearest_record(f, "force_activation_minus_contact_s", float(f["force_activation_minus_contact_s"].median()))
    v_id = nearest_record(post_vision, "vision_lock_minus_contact_s", float(post_vision["vision_lock_minus_contact_s"].median()))
    selected = timing[timing["record_id"].isin([g_id, f_id, v_id])].copy()

    duplicate_source = duplicates.copy()
    duplicate_source.insert(0, "row_type", "lineage_record")
    selection_source = selected.copy()
    selection_source.insert(0, "row_type", "representative_selection")
    selection_source["selection_rule"] = np.where(selection_source["record_id"].eq(g_id), "nearest G class median contact offset", np.where(selection_source["record_id"].eq(f_id), "nearest F class median contact offset", "nearest pooled post-contact E/F vision-lock median"))
    trace_source = trajectories[trajectories["record_id"].isin([f_id, v_id])].copy()
    trace_source.insert(0, "row_type", "representative_trajectory")
    source = pd.concat([duplicate_source, selection_source, trace_source], ignore_index=True, sort=False)
    source_path = write_source_csv(source, source_dir / "figure07_source_data.csv")

    set_publication_style()
    fig = plt.figure(figsize=figure_size(190, 132))
    grid = fig.add_gridspec(2, 2, hspace=0.43, wspace=0.35)
    ax = fig.add_subplot(grid[0, 0])
    pairs = list(duplicates.groupby("trial_key", sort=True))
    y = np.arange(len(pairs))
    for index, (trial_key, rows) in enumerate(pairs):
        rows = rows.sort_values("timestamp", kind="stable")
        excluded = rows[rows["analysis_role"].eq("excluded_known_error")].iloc[0]
        selected_row = rows[rows["included_main_clean"].eq(1)].iloc[0]
        ax.plot([0, 1], [index, index], color="#A0A0A0", linewidth=0.8)
        ax.scatter(0, index, s=28, marker="x", color="#8C2D04", linewidth=1.0)
        ax.scatter(1, index, s=30, marker="o", facecolor="#009E73", edgecolor="white", linewidth=0.5)
    ax.set_yticks(y, [f"Replacement {i + 1}" for i in range(len(pairs))])
    ax.set_xticks([0, 1], ["20260729\nretained, excluded", "20260730\nselected replacement"])
    ax.set_xlim(-0.25, 1.25); ax.invert_yaxis()
    ax.set_title("Exact acquisition lineage repair", loc="left")
    panel_label(ax, "A")

    ax = fig.add_subplot(grid[0, 1])
    g_row = selected[selected["record_id"].eq(g_id)].iloc[0]
    event_names = ["G activation", "Task start", "Contact"]
    event_times = [float(g_row["force_activation_minus_contact_s"]), -float(g_row["force_activation_minus_task_start_s"] - g_row["force_activation_minus_contact_s"]), 0.0]
    ax.hlines(0, min(event_times) - 0.15, 0.15, color="#777777", linewidth=0.8)
    for value, label, marker, color in zip(event_times, event_names, ["s", "o", "|"], [MODE_COLORS["G"], "#4D4D4D", "#111111"]):
        ax.scatter(value, 0, s=42, marker=marker, color=color, zorder=3)
        ax.annotate(label, (value, 0), xytext=(0, 10 if label != "Task start" else -16), textcoords="offset points", ha="center", va="bottom" if label != "Task start" else "top", fontsize=7.0)
    ax.set_ylim(-0.45, 0.45); ax.set_yticks([])
    ax.set_xlabel("Time relative to contact (s)")
    ax.set_title("Representative G pre-activation", loc="left")
    ax.text(0.02, 0.93, "Deterministic nearest-to-median selection", transform=ax.transAxes, va="top", fontsize=6.9)
    panel_label(ax, "B")

    f_row = selected[selected["record_id"].eq(f_id)].iloc[0]
    trace_panel(fig.add_subplot(grid[1, 0]), trajectories[trajectories["record_id"].eq(f_id)], f_row, "Representative F early activation", "C", "F activation", float(f_row["force_activation_minus_contact_s"]), nominal_time=0.20)
    v_row = selected[selected["record_id"].eq(v_id)].iloc[0]
    trace_panel(fig.add_subplot(grid[1, 1]), trajectories[trajectories["record_id"].eq(v_id)], v_row, "Representative post-contact vision lock", "D", "Vision lock", float(v_row["vision_lock_minus_contact_s"]))
    fig.text(0.5, 0.012, "Representative records were selected by frozen nearest-to-median rules with record_id tie-breaking; no trial was chosen for visual extremity.", ha="center", fontsize=7.2, fontstyle="italic")
    fig.subplots_adjust(left=0.09, right=0.91, top=0.96, bottom=0.09)
    outputs = save_publication_figure(fig, figures_dir, STEM, args.dpi)
    record_manifest(project_root / "19_publication_figures", project_root, STEM, Path(__file__), [manifest_path, timing_path, trajectories_path], source_path, outputs)
    print(f"Generated {STEM}")


if __name__ == "__main__":
    main()
