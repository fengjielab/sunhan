#!/usr/bin/env python3
"""Generate Figure 2: case system, asynchronous event channels, and provenance."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

from figure_common import parse_root_args, prepare_run, read_clean_csv, record_manifest, write_source_csv
from figure_style import figure_size, save_publication_figure, set_publication_style


STEM = "Fig02_system_and_lineage"
WIDTH_MM = 178.0
HEIGHT_MM = 118.0

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


def arrow(ax: plt.Axes, start: tuple[float, float], end: tuple[float, float], connectionstyle: str = "arc3") -> None:
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=8.0,
            linewidth=0.8,
            color=COLORS["edge"],
            connectionstyle=connectionstyle,
            shrinkA=1.0,
            shrinkB=1.0,
        )
    )


def panel_title(ax: plt.Axes, letter: str, title: str) -> None:
    ax.text(0.0, 1.02, f"({letter})", fontsize=9.2, fontweight="bold", va="bottom")
    ax.text(0.075, 1.02, title, fontsize=8.6, fontweight="bold", va="bottom")


def draw_system(ax: plt.Axes) -> None:
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    panel_title(ax, "A", "Human-in-the-loop teleoperation system")
    y, h = 0.54, 0.18
    nodes = [
        (0.02, 0.16, "Human\noperator", COLORS["neutral"]),
        (0.235, 0.18, "Force Dimension\nOmega.7", COLORS["blue"]),
        (0.475, 0.20, "Supervisory\ncontroller", COLORS["blue"]),
        (0.735, 0.24, "Panda + Hand\nobject/environment", COLORS["green"]),
    ]
    for x, w, text, color in nodes:
        add_box(ax, (x, y), (w, h), text, color, fontsize=6.3, bold=("controller" in text))
    for left, right in zip(nodes[:-1], nodes[1:]):
        arrow(ax, (left[0] + left[1] + 0.004, y + h / 2), (right[0] - 0.004, y + h / 2))
    ax.text(0.37, 0.50, "recorded master command", fontsize=5.6, ha="center", color=COLORS["muted"])
    ax.text(0.63, 0.50, "commanded impedance\n+ gripper command", fontsize=5.6, ha="center", va="top", color=COLORS["muted"])

    add_box(ax, (0.26, 0.12), (0.18, 0.15), "RealSense D435i\nsemantic lock", COLORS["green"], fontsize=6.0)
    arrow(ax, (0.44, 0.195), (0.57, 0.54))
    add_box(ax, (0.735, 0.12), (0.24, 0.15), "Internal estimated wrench\n" + r"$O\_F\_ext\_hat\_K$", COLORS["orange"], fontsize=5.9)
    arrow(ax, (0.855, 0.54), (0.855, 0.27))
    ax.text(0.86, 0.085, "contact detection · logged force · haptic feedback", fontsize=5.4, ha="center", va="top", color=COLORS["muted"])
    arrow(ax, (0.74, 0.16), (0.33, 0.53), connectionstyle="arc3,rad=-0.34")
    ax.text(0.53, 0.315, "haptic feedback", fontsize=5.5, ha="center", color=COLORS["muted"])


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
    panel_title(ax, "C", "Acquisition provenance and inference level")
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
    draw_system(fig.add_axes([0.025, 0.46, 0.54, 0.48]))
    draw_provenance(fig.add_axes([0.60, 0.46, 0.375, 0.48]), counts)
    draw_timeline(fig.add_axes([0.025, 0.055, 0.95, 0.29]))
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
    print(f"Generated {STEM}: system + schematic event channels + exact provenance")


if __name__ == "__main__":
    main()
