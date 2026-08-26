#!/usr/bin/env python3
"""Generate Figure 1: generic realized-intervention fidelity framework."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

from figure_common import parse_root_args, prepare_run, record_manifest, write_source_csv
from figure_style import figure_size, save_publication_figure, set_publication_style


STEM = "Fig01_realized_intervention_framework"
WIDTH_MM = 178.0
HEIGHT_MM = 88.0

COLORS = {
    "nominal": "#F1F1F1",
    "executable": "#DCE8F2",
    "realized": "#DDECE4",
    "outcome": "#F2E1D5",
    "final": "#FFFFFF",
    "edge": "#505050",
    "muted": "#5D5D5D",
    "failure": "#8A4C2E",
    "window": "#ECECEC",
    "vision": "#0072B2",
    "activation": "#D55E00",
}

LAYERS = [
    ("N_m", "Documented nominal\nintervention", ["parameters", "guards and timing", "intended exposure"], "nominal"),
    ("C_m", "Executable\nimplementation", ["literal guards", "clock domains", "update logic"], "executable"),
    ("R_i", "Realized logged\nintervention", ["event timestamps", "activation states", "command trajectories"], "realized"),
    ("Y_i", "Windowed\noutcome", ["event-aligned window", "derived metric", "independent unit"], "outcome"),
]


def arrow(ax: plt.Axes, start: tuple[float, float], end: tuple[float, float]) -> None:
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=9,
            linewidth=0.9,
            color=COLORS["edge"],
            shrinkA=1.5,
            shrinkB=1.5,
        )
    )


def box(
    ax: plt.Axes,
    x: float,
    y: float,
    width: float,
    height: float,
    title: str,
    symbol: str | None,
    lines: list[str],
    facecolor: str,
) -> None:
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            width,
            height,
            boxstyle="round,pad=0.006,rounding_size=0.012",
            facecolor=facecolor,
            edgecolor=COLORS["edge"],
            linewidth=0.85,
        )
    )
    ax.text(x + 0.012, y + height - 0.024, title, fontsize=7.8, fontweight="bold", va="top", linespacing=1.0)
    cursor = y + height - 0.102
    if symbol:
        ax.text(x + 0.012, cursor, rf"${symbol}$", fontsize=8.4, va="top")
        cursor -= 0.055
    ax.text(x + 0.012, cursor, "\n".join(lines), fontsize=6.4, va="top", linespacing=1.16)


def create_figure() -> plt.Figure:
    set_publication_style()
    fig, ax = plt.subplots(figsize=figure_size(WIDTH_MM, HEIGHT_MM))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.018, 0.955, "(A)", fontsize=8.8, fontweight="bold", va="top")
    ax.text(0.064, 0.955, "From nominal specification to an evidence-admissible claim", fontsize=8.3, fontweight="bold", va="top")

    x_positions = [0.025, 0.218, 0.411, 0.604]
    layer_width, layer_y, layer_height = 0.145, 0.555, 0.315
    for x, (symbol, title, lines, color_key) in zip(x_positions, LAYERS):
        box(ax, x, layer_y, layer_width, layer_height, title, symbol, lines, COLORS[color_key])

    final_x, final_width = 0.797, 0.178
    box(
        ax,
        final_x,
        layer_y,
        final_width,
        layer_height,
        "Evidence-admissible\nclaim",
        None,
        ["narrowest supported", "contrast and unit", "causality not assumed"],
        COLORS["final"],
    )

    chain_y = layer_y + layer_height / 2
    interfaces = [
        ("N ≠ C", "guard / clock"),
        ("C ≠ R", "logged delivery"),
        ("R ≠ W", "window exposure"),
    ]
    for index, (label, failure) in enumerate(interfaces):
        left = x_positions[index] + layer_width + 0.004
        right = x_positions[index + 1] - 0.004
        arrow(ax, (left, chain_y), (right, chain_y))
        center = (left + right) / 2
        ax.text(
            center,
            0.885,
            label,
            fontsize=6.4,
            fontweight="bold",
            ha="center",
            va="bottom",
            color=COLORS["failure"],
            bbox={"boxstyle": "round,pad=0.22", "facecolor": "#FFF7F2", "edgecolor": "#D9B8A6", "linewidth": 0.55},
        )
        ax.text(center, 0.535, failure, fontsize=5.5, color=COLORS["failure"], ha="center", va="top")
    arrow(ax, (x_positions[-1] + layer_width + 0.004, chain_y), (final_x - 0.004, chain_y))

    ax.plot([0.02, 0.98], [0.475, 0.475], color="#D0D0D0", linewidth=0.55)
    ax.text(0.018, 0.438, "(B)", fontsize=8.8, fontweight="bold", va="top")
    ax.text(0.064, 0.438, "Asynchronous channels determine what reaches the analysis window", fontsize=8.3, fontweight="bold", va="top")
    x0, x1 = 0.205, 0.955
    y_rows = [0.335, 0.275, 0.215, 0.155, 0.095]
    labels = ["Human input $H_i(t)$", "Vision lock", "Controller activation", "Contact", "Outcome window $W_i$"]
    for y, label in zip(y_rows, labels):
        ax.text(0.185, y, label, fontsize=6.5, ha="right", va="center")
        ax.plot([x0, x1], [y, y], color="#B0B0B0", linewidth=0.55)
    ax.text(x0, 0.035, "earlier", fontsize=5.8, color=COLORS["muted"], ha="center")
    ax.text(x1, 0.035, "later", fontsize=5.8, color=COLORS["muted"], ha="center")
    arrow(ax, (x0, 0.052), (x1, 0.052))

    ax.plot([0.30, 0.36, 0.43, 0.51], [0.335, 0.354, 0.320, 0.335], color=COLORS["edge"], linewidth=1.1)
    ax.scatter([0.47], [0.275], s=23, marker="s", color=COLORS["vision"], zorder=4)
    ax.scatter([0.39], [0.215], s=24, marker="D", color=COLORS["activation"], edgecolor="white", linewidth=0.4, zorder=4)
    ax.scatter([0.58], [0.155], s=28, marker="|", color="#202020", linewidth=1.4, zorder=4)
    ax.add_patch(Rectangle((0.66, 0.075), 0.22, 0.040, facecolor=COLORS["window"], edgecolor="#777777", linewidth=0.7))
    ax.text(0.77, 0.095, "samples contributing to $Y_i$", fontsize=5.9, ha="center", va="center")
    for x, text, y in [(0.47, "perception", 0.255), (0.39, "activation before contact", 0.195), (0.58, "contact", 0.135)]:
        ax.text(x, y, text, fontsize=5.5, ha="center", va="top", color=COLORS["muted"])

    ax.text(
        0.975,
        0.006,
        r"Acquisition provenance is an orthogonal prerequisite for the $R_i\leftrightarrow Y_i$ linkage (Section III-C; Fig. S3).",
        fontsize=5.9,
        ha="right",
        va="bottom",
        color=COLORS["muted"],
        fontstyle="italic",
    )
    fig.subplots_adjust(left=0.005, right=0.995, top=0.985, bottom=0.015)
    return fig


def main() -> None:
    args = parse_root_args(__doc__ or "")
    project_root, _, figures_dir, source_dir = prepare_run(args, __file__)
    publication_root = project_root / "19_publication_figures"
    source = pd.DataFrame(
        [
            {"element_type": "layer", "id": symbol, "label": title.replace("\n", " "), "meaning": "; ".join(lines)}
            for symbol, title, lines, _ in LAYERS
        ]
        + [
            {"element_type": "timeline_channel", "id": identifier, "label": label, "meaning": "schematic asynchronous event channel"}
            for identifier, label in [
                ("H_i", "Human input"),
                ("vision_lock", "Vision lock"),
                ("controller_activation", "Controller activation"),
                ("contact", "Contact"),
                ("W_i", "Outcome window"),
            ]
        ]
    )
    source_path = write_source_csv(source, source_dir / "figure01_source_data.csv")
    outputs = save_publication_figure(create_figure(), figures_dir, STEM, args.dpi)
    record_manifest(publication_root, project_root, STEM, Path(__file__), [], source_path, outputs)
    print(f"Generated {STEM}: framework chain plus asynchronous timeline; provenance excluded")


if __name__ == "__main__":
    main()
