#!/usr/bin/env python3
"""Generate Figure 6: participant consistency and leave-one-participant-out stability."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from figure_common import parse_root_args, prepare_run, read_clean_csv, record_manifest, write_source_csv
from figure_style import MODE_COLORS, figure_size, panel_label, save_publication_figure, set_publication_style


STEM = "Fig06_participant_lopo_stability"
METRIC = "primary_excess_impulse_Ns_0p2_1p0"


def estimate_panel(ax, source, contrast, letter):
    stat = source[(source["row_type"].eq("full_estimate")) & (source["contrast"].eq(contrast))].iloc[0]
    lopo = source[(source["row_type"].eq("lopo_estimate")) & (source["contrast"].eq(contrast))].sort_values("left_out_participant", kind="stable")
    labels = ["Full sample"] + [f"Without {value}" for value in lopo["left_out_participant"]]
    means = [float(stat["raw_mean_difference"])] + lopo["lopo_mean_difference"].astype(float).tolist()
    lows = [float(stat["ci95_low"])] + lopo["lopo_ci95_low"].astype(float).tolist()
    highs = [float(stat["ci95_high"])] + lopo["lopo_ci95_high"].astype(float).tolist()
    y = np.arange(len(labels))
    ax.axvline(0, color="#555555", linewidth=0.75, linestyle="--")
    for index, (mean, low, high) in enumerate(zip(means, lows, highs)):
        ax.errorbar(mean, index, xerr=np.array([[mean - low], [high - mean]]), fmt="D" if index == 0 else "o", markersize=5.5 if index == 0 else 4.2, markerfacecolor=MODE_COLORS["E"] if contrast == "E-A" else MODE_COLORS["F"], markeredgecolor="white", color="#333333", linewidth=0.95, capsize=2.5)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlabel(f"{contrast} impulse difference (N·s)")
    ax.grid(axis="x", color="#D9D9D9", linewidth=0.5, alpha=0.55)
    ax.set_axisbelow(True)
    ax.set_title(f"{contrast}: full sample and LOPO estimates", loc="center", pad=7)
    panel_label(ax, letter, x=-0.14, y=1.08)


def main() -> None:
    args = parse_root_args(__doc__ or "")
    project_root, clean_dir, figures_dir, source_dir = prepare_run(args, __file__)
    participant_path = clean_dir / "participant_level_metrics.csv"
    stats_path = clean_dir / "statistics_summary.csv"
    lopo_path = clean_dir / "leave_one_participant_out.csv"
    participant = read_clean_csv(clean_dir, participant_path.name, ["participant", "mode_code", METRIC])
    stats = read_clean_csv(clean_dir, stats_path.name, ["metric", "contrast", "raw_mean_difference", "ci95_low", "ci95_high"])
    lopo = read_clean_csv(clean_dir, lopo_path.name, ["metric", "contrast", "left_out_participant", "lopo_mean_difference", "lopo_ci95_low", "lopo_ci95_high"])

    wide = participant.pivot(index="participant", columns="mode_code", values=METRIC)
    individual_rows = []
    for contrast, positive, negative in [("E-A", "E", "A"), ("F-E", "F", "E")]:
        for participant_id, value in (wide[positive] - wide[negative]).items():
            individual_rows.append({"row_type": "individual_difference", "metric": METRIC, "contrast": contrast, "participant": participant_id, "participant_difference": float(value)})
    full = stats[(stats["metric"].eq(METRIC)) & (stats["contrast"].isin(["E-A", "F-E"]))].copy()
    full.insert(0, "row_type", "full_estimate")
    lopo_source = lopo[(lopo["metric"].eq(METRIC)) & (lopo["contrast"].isin(["E-A", "F-E"]))].copy()
    lopo_source.insert(0, "row_type", "lopo_estimate")
    source = pd.concat([pd.DataFrame(individual_rows), full, lopo_source], ignore_index=True, sort=False)
    source_path = write_source_csv(source, source_dir / "figure06_source_data.csv")

    set_publication_style()
    fig, axes = plt.subplots(1, 3, figsize=figure_size(190, 82), gridspec_kw={"width_ratios": [0.75, 1.15, 1.15]})
    individual = source[(source["row_type"].eq("individual_difference")) & (source["contrast"].eq("E-A"))].sort_values("participant", kind="stable")
    ax = axes[0]
    ax.axvline(0, color="#555555", linewidth=0.75, linestyle="--")
    y = np.arange(len(individual))
    ax.scatter(individual["participant_difference"], y, s=31, marker="o", facecolor="white", edgecolor=MODE_COLORS["E"], linewidth=1.0)
    ax.set_yticks(y, individual["participant"])
    ax.invert_yaxis()
    ax.set_xlabel("E − A impulse\ndifference (N·s)")
    ax.set_title("Individual differences", loc="center", pad=7)
    ax.grid(axis="x", color="#D9D9D9", linewidth=0.5, alpha=0.55)
    ax.set_axisbelow(True)
    panel_label(ax, "A", x=-0.14, y=1.08)
    estimate_panel(axes[1], source, "E-A", "B")
    estimate_panel(axes[2], source, "F-E", "C")
    fig.text(0.5, 0.012, "LOPO intervals are stability diagnostics, not additional independent confirmatory tests; participant is the inference unit.", ha="center", fontsize=7.2, fontstyle="italic")
    fig.subplots_adjust(left=0.075, right=0.99, top=0.90, bottom=0.21, wspace=0.43)
    outputs = save_publication_figure(fig, figures_dir, STEM, args.dpi)
    record_manifest(project_root / "19_publication_figures", project_root, STEM, Path(__file__), [participant_path, stats_path, lopo_path], source_path, outputs)
    print(f"Generated {STEM}")


if __name__ == "__main__":
    main()
