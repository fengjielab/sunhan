"""Shared publication style for the final manuscript figures."""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt


MM_TO_INCH = 1.0 / 25.4

MODE_ORDER = ["A", "G", "E", "F"]
MODE_COLORS = {
    "A": "#4D4D4D",
    "G": "#0072B2",
    "E": "#009E73",
    "F": "#D55E00",
}
MODE_MARKERS = {"A": "o", "G": "s", "E": "^", "F": "D"}
MODE_LINESTYLES = {"A": "-", "G": "--", "E": "-", "F": "-."}
EXPOSURE_COLORS = {"Full": "#5B8C5A", "Partial": "#E69F00", "Zero": "#B3B3B3"}
PARTICIPANT_MARKERS = {"P01": "o", "P02": "s", "P03": "^", "P04": "D", "P05": "P"}


def set_publication_style() -> None:
    """Apply a restrained, editable, journal-oriented Matplotlib style."""
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "font.size": 8.0,
            "axes.labelsize": 8.5,
            "axes.titlesize": 9.0,
            "axes.titleweight": "normal",
            "xtick.labelsize": 7.5,
            "ytick.labelsize": 7.5,
            "legend.fontsize": 7.5,
            "axes.linewidth": 0.7,
            "lines.linewidth": 1.2,
            "lines.markersize": 4.5,
            "xtick.major.width": 0.7,
            "ytick.major.width": 0.7,
            "xtick.major.size": 3.0,
            "ytick.major.size": 3.0,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.facecolor": "white",
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
            "legend.frameon": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
        }
    )


def figure_size(width_mm: float, height_mm: float) -> tuple[float, float]:
    return width_mm * MM_TO_INCH, height_mm * MM_TO_INCH


def panel_label(ax: plt.Axes, label: str, x: float = -0.13, y: float = 1.06) -> None:
    ax.text(
        x,
        y,
        f"({label})",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9.5,
        fontweight="bold",
        clip_on=False,
    )


def light_horizontal_grid(ax: plt.Axes) -> None:
    ax.grid(axis="y", which="major", color="#D9D9D9", linewidth=0.55, alpha=0.55)
    ax.set_axisbelow(True)


def save_publication_figure(fig: plt.Figure, output_dir: Path, stem: str, dpi: int = 600) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = [output_dir / f"{stem}.pdf", output_dir / f"{stem}.svg", output_dir / f"{stem}.png"]
    fig.savefig(outputs[0], bbox_inches="tight", pad_inches=0.02)
    fig.savefig(outputs[1], bbox_inches="tight", pad_inches=0.02)
    fig.savefig(outputs[2], dpi=dpi, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    return outputs
