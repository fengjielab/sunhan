"""Preview a compact non-blocking execution schematic for Fig. 2."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


NAVY = "#174A7E"
BLUE_FILL = "#EAF2F8"
GREEN = "#2E8B57"
GREEN_FILL = "#EAF7EF"
GREY = "#62707C"


def box(ax: plt.Axes, x: float, y: float, w: float, h: float, text: str, *, edge: str, fill: str, fontsize: float = 8.0) -> None:
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.22,rounding_size=0.75",
                                linewidth=1.15, edgecolor=edge, facecolor=fill, zorder=2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize,
            color="#17232D", fontweight="bold", linespacing=1.08, zorder=3)


def arrow(ax: plt.Axes, start: tuple[float, float], end: tuple[float, float], *, color: str, dashed: bool = False, width: float = 1.2) -> None:
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=10, linewidth=width,
                                 linestyle=(0, (3, 2)) if dashed else "solid", color=color,
                                 shrinkA=1.5, shrinkB=1.5, zorder=1))


def main() -> None:
    here = Path(__file__).resolve().parent
    output = here / "outputs" / "fig2_nonblocking_schematic_preview"
    output.mkdir(parents=True, exist_ok=True)

    plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
                         "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none"})
    fig, ax = plt.subplots(figsize=(7.2, 2.55))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 55)
    ax.axis("off")

    ax.text(3, 51.2, "Non-blocking, event-triggered execution", ha="left", va="center",
            fontsize=11.0, fontweight="bold", color="#111820")
    ax.text(97, 51.2, "Illustrative mechanism", ha="right", va="center", fontsize=7.0, color=GREY)

    # The upper sequence only describes the asynchronous side path.
    ax.text(3, 43.6, "Asynchronous vision path", fontsize=8.6, color=GREEN, fontweight="bold", va="center")
    box(ax, 5, 31, 20, 10, "Camera + YOLO11n\nindependent, 15 fps", edge=NAVY, fill=BLUE_FILL, fontsize=7.9)
    box(ax, 32, 31, 16, 10, "Bounded\nlatest-result queue", edge=NAVY, fill=BLUE_FILL, fontsize=7.7)
    box(ax, 55, 31, 18, 10, "200-Hz supervisor\nnon-blocking poll", edge=NAVY, fill=BLUE_FILL, fontsize=7.5)
    box(ax, 80, 31, 15, 10, "First valid\nmapped result", edge=GREEN, fill=GREEN_FILL, fontsize=7.7)
    arrow(ax, (25, 36), (32, 36), color=GREEN, dashed=True)
    arrow(ax, (48, 36), (55, 36), color=GREEN, dashed=True)
    arrow(ax, (73, 36), (80, 36), color=GREEN, dashed=True)
    ax.text(50, 26.7, "Perception updates the latest result; the supervisor never waits for inference.",
            ha="center", va="center", fontsize=7.2, color=GREY)

    # A single unbroken control spine is the main claim of the figure.
    ax.text(3, 19.8, "Continuous human control", fontsize=8.6, color=NAVY, fontweight="bold", va="center")
    arrow(ax, (5, 14), (95, 14), color=NAVY, width=2.0)
    ax.text(50, 16.8, "Operator motion and nominal 200-Hz control continue throughout", ha="center", va="bottom",
            fontsize=8.0, color=NAVY)

    # Only the first valid result crosses from the upper asynchronous branch to
    # the strategy state, and it does so once.
    arrow(ax, (87.5, 31), (87.5, 22), color=GREEN, dashed=True)
    box(ax, 64, 20, 31, 5.4, "one event $\\Theta(c)$  $\\rightarrow$  ~300-ms transition  $\\rightarrow$  lock",
        edge=GREEN, fill=GREEN_FILL, fontsize=6.5)
    ax.text(50, 4.0, "Dashed green: asynchronous result path and one strategy event.  Solid blue: control is never gated.",
            ha="center", va="center", fontsize=6.7, color=GREY)

    fig.subplots_adjust(left=0.02, right=0.985, top=0.97, bottom=0.08)
    stem = output / "Fig2_nonblocking_schematic_preview"
    fig.savefig(stem.with_suffix(".png"), dpi=600, facecolor="white")
    fig.savefig(stem.with_suffix(".pdf"), facecolor="white")
    fig.savefig(stem.with_suffix(".svg"), facecolor="white")
    plt.close(fig)
    print(f"Saved preview to: {output.resolve()}")


if __name__ == "__main__":
    main()
