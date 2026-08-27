#!/usr/bin/env python3
"""Generate Figure 2: case system architecture and acquisition provenance."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Rectangle

from figure_common import parse_root_args, prepare_run, read_clean_csv, record_manifest, write_source_csv
from figure_style import figure_size, save_publication_figure, set_publication_style


STEM = "Fig02_system_and_lineage"
WIDTH_MM = 178.0
HEIGHT_MM = 84.0

COLORS = {
    "neutral": "#F1F1F1",
    "blue": "#DCE8F2",
    "green": "#DDECE4",
    "orange": "#F2E1D5",
    "edge": "#505050",
    "muted": "#5D5D5D",
    "window": "#ECECEC",
    "g": "#0072B2",
    "f": "#D55E00",
}


def add_box(ax: plt.Axes, xy: tuple[float, float], size: tuple[float, float], text: str, color: str, fontsize: float = 6.4, bold: bool = False) -> None:
    x, y = xy
    width, height = size
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            width,
            height,
            boxstyle="round,pad=0.006,rounding_size=0.012",
            facecolor=color,
            edgecolor=COLORS["edge"],
            linewidth=0.75,
        )
    )
    ax.text(x + width / 2, y + height / 2, text, fontsize=fontsize, ha="center", va="center", fontweight="bold" if bold else "normal", linespacing=1.05)


def arrow(
    ax: plt.Axes,
    start: tuple[float, float],
    end: tuple[float, float],
    connectionstyle: str = "arc3",
    color: str | None = None,
    linewidth: float = 0.8,
) -> None:
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=8.0,
            linewidth=linewidth,
            color=color or COLORS["edge"],
            connectionstyle=connectionstyle,
            shrinkA=1.0,
            shrinkB=1.0,
        )
    )


def panel_title(ax: plt.Axes, letter: str, title: str) -> None:
    ax.text(0.0, 1.02, f"({letter})", fontsize=9.2, fontweight="bold", va="bottom")
    ax.text(0.095, 1.02, title, fontsize=8.6, fontweight="bold", va="bottom")


def draw_system(ax: plt.Axes) -> None:
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    panel_title(ax, "A", "Coupled system and audited signal paths")

    # Light scene cards provide visual hierarchy without implying unavailable photographs.
    ax.add_patch(FancyBboxPatch((0.01, 0.15), 0.25, 0.70, boxstyle="round,pad=0.008,rounding_size=0.02", facecolor="#F8F8F8", edgecolor="#D2D2D2", linewidth=0.65))
    ax.add_patch(FancyBboxPatch((0.35, 0.15), 0.25, 0.70, boxstyle="round,pad=0.008,rounding_size=0.02", facecolor="#F4F8FB", edgecolor="#C8D7DF", linewidth=0.65))
    ax.add_patch(FancyBboxPatch((0.69, 0.15), 0.30, 0.70, boxstyle="round,pad=0.008,rounding_size=0.02", facecolor="#F4F9F6", edgecolor="#C9DACE", linewidth=0.65))
    ax.text(0.135, 0.81, "HUMAN / MASTER", fontsize=5.7, fontweight="bold", ha="center", color=COLORS["muted"])
    ax.text(0.475, 0.81, "SUPERVISORY LAYER", fontsize=5.7, fontweight="bold", ha="center", color=COLORS["muted"])
    ax.text(0.84, 0.81, "ROBOT / TASK", fontsize=5.7, fontweight="bold", ha="center", color=COLORS["muted"])

    # Operator and Omega.7 pictograms.
    ax.add_patch(Circle((0.075, 0.64), 0.030, facecolor="white", edgecolor=COLORS["edge"], linewidth=0.8))
    ax.plot([0.075, 0.075], [0.61, 0.50], color=COLORS["edge"], linewidth=1.0)
    ax.plot([0.075, 0.040], [0.575, 0.525], color=COLORS["edge"], linewidth=0.9)
    ax.plot([0.075, 0.122], [0.575, 0.535], color=COLORS["edge"], linewidth=0.9)
    ax.plot([0.075, 0.045], [0.50, 0.43], color=COLORS["edge"], linewidth=0.9)
    ax.plot([0.075, 0.105], [0.50, 0.43], color=COLORS["edge"], linewidth=0.9)
    ax.add_patch(Circle((0.165, 0.515), 0.037, facecolor=COLORS["blue"], edgecolor=COLORS["edge"], linewidth=0.8))
    ax.plot([0.165, 0.205], [0.515, 0.56], color=COLORS["edge"], linewidth=1.2)
    ax.add_patch(Circle((0.205, 0.56), 0.010, facecolor="#FFFFFF", edgecolor=COLORS["edge"], linewidth=0.7))
    ax.text(0.135, 0.25, "Operator + Omega.7\nrecorded master motion", fontsize=6.2, ha="center", va="center")

    add_box(ax, (0.385, 0.55), (0.18, 0.15), "Supervisory\ncontroller", COLORS["blue"], fontsize=6.5, bold=True)
    add_box(ax, (0.385, 0.29), (0.18, 0.13), "RealSense D435i\nsemantic lock", COLORS["green"], fontsize=5.8)

    # Stylized Panda arm, hand, and contact surface.
    joints = [(0.74, 0.36), (0.76, 0.54), (0.82, 0.66), (0.89, 0.57), (0.92, 0.45)]
    for start, end in zip(joints[:-1], joints[1:]):
        ax.plot([start[0], end[0]], [start[1], end[1]], color="#4B4B4B", linewidth=4.0, solid_capstyle="round", zorder=2)
    for x, y in joints:
        ax.add_patch(Circle((x, y), 0.021, facecolor="white", edgecolor="#4B4B4B", linewidth=0.9, zorder=3))
    ax.plot([0.92, 0.955], [0.45, 0.41], color="#4B4B4B", linewidth=2.0)
    ax.plot([0.945, 0.970], [0.405, 0.405], color=COLORS["f"], linewidth=1.8)
    ax.add_patch(Rectangle((0.80, 0.30), 0.18, 0.035, facecolor="#D9D9D9", edgecolor="#777777", linewidth=0.6))
    ax.text(0.84, 0.235, "Panda + Hand\nobject / environment", fontsize=6.2, ha="center", va="center")

    # Three distinct audited pathways.
    arrow(ax, (0.23, 0.66), (0.38, 0.66), color=COLORS["g"], linewidth=1.15)
    arrow(ax, (0.57, 0.66), (0.71, 0.66), color=COLORS["g"], linewidth=1.15)
    ax.text(0.47, 0.735, "recorded command → impedance / gripper command", fontsize=5.4, ha="center", color=COLORS["g"])
    arrow(ax, (0.57, 0.355), (0.71, 0.42), color="#009E73", linewidth=1.05)
    ax.text(0.64, 0.325, "vision-configured parameters", fontsize=5.2, ha="center", color="#007C60")
    arrow(ax, (0.73, 0.34), (0.23, 0.38), connectionstyle="arc3,rad=-0.18", color=COLORS["f"], linewidth=1.05)
    ax.text(0.49, 0.18, "estimated wrench → contact detection, logged force, haptic feedback", fontsize=5.4, ha="center", color="#A84C00")


def draw_timeline(ax: plt.Axes) -> None:
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    panel_title(ax, "B", "Asynchronous event channels (schematic, not one representative trial)")
    x0, x1 = 0.24, 0.96
    rows = [
        (0.78, "system ready / task_start"),
        (0.63, "recorded human-master input"),
        (0.48, "E/F vision lock → transition"),
        (0.33, "G activation pattern"),
        (0.18, "F activation pattern"),
    ]
    for y, label in rows:
        ax.text(0.22, y, label, fontsize=6.0, ha="right", va="center")
        ax.plot([x0, x1], [y, y], color="#B0B0B0", linewidth=0.55)
    contact_x, gate_x = 0.62, 0.75
    ax.axvline(contact_x, ymin=0.09, ymax=0.88, color="#333333", linewidth=0.85)
    ax.text(contact_x, 0.05, "contact", fontsize=5.7, ha="center", va="top")
    ax.axvline(gate_x, ymin=0.09, ymax=0.31, color=COLORS["f"], linewidth=0.8, linestyle=(0, (3, 2)))
    ax.text(gate_x, 0.05, "nominal F +0.20 s", fontsize=5.4, ha="center", va="top", color=COLORS["f"])
    ax.add_patch(Rectangle((gate_x, 0.86), 0.17, 0.06, facecolor=COLORS["window"], edgecolor="#777777", linewidth=0.6))
    ax.text(gate_x + 0.085, 0.89, "outcome window", fontsize=5.5, ha="center", va="center")

    ax.scatter([0.34], [0.78], marker="|", s=80, color="#444444", linewidth=1.2)
    ax.plot([0.37, 0.43, 0.50, 0.57], [0.63, 0.67, 0.60, 0.64], color="#4A4A4A", linewidth=1.0)
    ax.scatter([0.45], [0.48], marker="s", s=24, color="#009E73", edgecolor="white", linewidth=0.4)
    ax.plot([0.45, 0.56], [0.48, 0.48], color="#009E73", linewidth=3.0, alpha=0.35)
    ax.scatter([0.48], [0.33], marker="o", s=25, color=COLORS["g"], edgecolor="white", linewidth=0.4)
    ax.text(0.48, 0.275, "often before contact", fontsize=5.2, ha="center", color=COLORS["muted"])
    ax.scatter([0.665], [0.18], marker="D", s=25, color=COLORS["f"], edgecolor="white", linewidth=0.4)
    ax.text(0.665, 0.125, "often before nominal gate", fontsize=5.2, ha="center", color=COLORS["muted"])


def draw_provenance(ax: plt.Axes, counts: dict[str, int]) -> None:
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    panel_title(ax, "B", "Acquisition provenance and inference level")
    add_box(ax, (0.08, 0.82), (0.84, 0.11), "Experimental acquisition", COLORS["neutral"], fontsize=6.4, bold=True)
    add_box(ax, (0.04, 0.64), (0.27, 0.11), "Raw CSV", COLORS["blue"], fontsize=6.0)
    add_box(ax, (0.365, 0.64), (0.27, 0.11), "Event JSON", COLORS["blue"], fontsize=6.0)
    add_box(ax, (0.69, 0.64), (0.27, 0.11), "Summary JSON", COLORS["blue"], fontsize=6.0)
    for x in [0.175, 0.50, 0.825]:
        arrow(ax, (0.50, 0.82), (x, 0.75))
    add_box(ax, (0.08, 0.46), (0.84, 0.11), "Exact logical key + timestamped acquisition ID\nSHA-256 verified manifest", COLORS["green"], fontsize=5.8, bold=True)
    for x in [0.175, 0.50, 0.825]:
        arrow(ax, (x, 0.64), (0.50, 0.57))
    add_box(ax, (0.08, 0.28), (0.84, 0.11), f"{counts['archived']} archived acquisitions → {counts['selected']} selected\n{counts['files']} selected source files verified", COLORS["neutral"], fontsize=5.8, bold=True)
    arrow(ax, (0.50, 0.46), (0.50, 0.39))
    add_box(ax, (0.04, 0.06), (0.43, 0.14), f"Trial-level fidelity\nn = {counts['selected']} observations", COLORS["green"], fontsize=5.9, bold=True)
    add_box(ax, (0.53, 0.06), (0.43, 0.14), f"Human outcome inference\nn = {counts['participants']} participants", COLORS["orange"], fontsize=5.9, bold=True)
    arrow(ax, (0.50, 0.28), (0.255, 0.20))
    arrow(ax, (0.50, 0.28), (0.745, 0.20))
    ax.text(0.50, 0.012, "180 trials are not 180 independent human samples", fontsize=5.6, fontweight="bold", ha="center", color="#8A4C2E")


def create_figure(counts: dict[str, int]) -> plt.Figure:
    set_publication_style()
    fig = plt.figure(figsize=figure_size(WIDTH_MM, HEIGHT_MM))
    draw_system(fig.add_axes([0.025, 0.08, 0.55, 0.84]))
    draw_provenance(fig.add_axes([0.61, 0.08, 0.365, 0.84]), counts)
    return fig


def main() -> None:
    args = parse_root_args(__doc__ or "")
    project_root, clean_dir, figures_dir, source_dir = prepare_run(args, __file__)
    publication_root = project_root / "19_publication_figures"
    lineage_path = clean_dir / "data_lineage_audit.csv"
    participant_path = clean_dir / "participant_level_metrics.csv"
    lineage = read_clean_csv(clean_dir, lineage_path.name, ["record_id", "included_main_clean", "csv_hash_verified", "events_hash_verified", "summary_hash_verified"])
    participant = read_clean_csv(clean_dir, participant_path.name, ["participant", "mode_code"])
    selected = lineage.loc[lineage["included_main_clean"].eq(1)]
    counts = {
        "archived": int(lineage["record_id"].nunique()),
        "selected": int(selected["record_id"].nunique()),
        "files": int(selected[["csv_hash_verified", "events_hash_verified", "summary_hash_verified"]].to_numpy(dtype=int).sum()),
        "participants": int(participant["participant"].nunique()),
    }
    expected = {"archived": 186, "selected": 180, "files": 540, "participants": 5}
    if counts != expected:
        raise RuntimeError(f"Figure 2 frozen-count QA failed: actual={counts}; expected={expected}")
    source = pd.DataFrame([{"quantity": key, "value": value, "clean_source": lineage_path.name if key != "participants" else participant_path.name} for key, value in counts.items()])
    source_path = write_source_csv(source, source_dir / "figure02_source_data.csv")
    outputs = save_publication_figure(create_figure(counts), figures_dir, STEM, args.dpi)
    record_manifest(publication_root, project_root, STEM, Path(__file__), [lineage_path, participant_path], source_path, outputs)
    print(f"Generated {STEM}: system architecture + exact provenance")


if __name__ == "__main__":
    main()
