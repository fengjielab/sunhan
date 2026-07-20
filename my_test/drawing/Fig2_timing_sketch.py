"""Preview a compact timing schematic for manuscript Fig. 2.

This preview is intentionally separate from the paper assets until approved.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle


NAVY = "#174A7E"
BLUE = "#4F86A6"
BLUE_FILL = "#EAF2F8"
GREEN = "#2E8B57"
GREEN_FILL = "#EAF7EF"
GREY = "#64707A"
GRID = "#D7DDE3"


def arrow(ax: plt.Axes, start: tuple[float, float], end: tuple[float, float], color: str, *, dashed: bool = False) -> None:
    ax.add_patch(
        FancyArrowPatch(
            start, end, arrowstyle="-|>", mutation_scale=10, linewidth=1.2,
            linestyle=(0, (3, 2)) if dashed else "solid", color=color,
            shrinkA=0, shrinkB=0,
        )
    )


def block(ax: plt.Axes, x0: float, x1: float, y: float, h: float, label: str, color: str, fill: str, *, fontsize: float = 7.4) -> None:
    ax.add_patch(Rectangle((x0, y), x1 - x0, h, facecolor=fill, edgecolor=color, linewidth=1.0, zorder=2))
    ax.text((x0 + x1) / 2, y + h / 2, label, ha="center", va="center", fontsize=fontsize,
            color="#17232D", linespacing=1.05, zorder=3)


def main() -> None:
    here = Path(__file__).resolve().parent
    output = here / "outputs" / "fig2_timing_sketch"
    output.mkdir(parents=True, exist_ok=True)

    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
        }
    )
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    ax.set_xlim(-56, 410)
    ax.set_ylim(-0.18, 4.45)
    ax.axis("off")

    ax.text(-54, 4.26, "Asynchronous perception--control timing (illustrative)",
            fontsize=10.5, fontweight="bold", color="#111820", va="center")
    ax.text(407, 4.26, "Time (ms)", fontsize=7.0, color=GREY, ha="right", va="center")

    ticks = [0, 66.7, 133.3, 200, 350]
    for tick in ticks:
        ax.vlines(tick, 0.05, 3.95, color=GRID, linewidth=0.7, zorder=0)
        ax.text(tick, 4.02, f"{tick:g}", ha="center", va="bottom", fontsize=6.7, color=GREY)

    lanes = [
        (3.38, "Vision worker\n15 fps"),
        (2.50, "Bounded latest-result\nqueue"),
        (1.62, "200-Hz supervisor\nnon-blocking poll"),
        (0.64, "Operator motion\n+ strategy state"),
    ]
    for y, label in lanes:
        ax.hlines(y, 0, 400, color=GRID, linewidth=0.8, zorder=0)
        ax.text(-10, y, label, ha="right", va="center", fontsize=7.0, color="#27333D", linespacing=1.08)

    # One representative image enters the independent inference worker; later
    # frames are only marks, not repeated visual clutter.
    for tick in [0, 66.7, 133.3, 200]:
        ax.plot(tick, 3.38, marker="s", markersize=4.4, markerfacecolor="white", markeredgecolor=NAVY, zorder=3)
    ax.text(177, 3.59, "frames continue at 15 fps", ha="center", va="bottom", fontsize=6.6, color=GREY)
    block(ax, 0, 48.19, 3.08, 0.42, "YOLO11n inference\nmean 48.19 ms/image", NAVY, BLUE_FILL, fontsize=6.5)

    block(ax, 48.19, 76, 2.30, 0.42, "latest result", NAVY, BLUE_FILL, fontsize=6.6)
    arrow(ax, (48.19, 3.08), (48.19, 2.72), NAVY, dashed=True)

    # The supervisor keeps polling; the first valid result is read at one poll.
    arrow(ax, (0, 1.62), (400, 1.62), BLUE)
    ax.text(210, 1.83, "polls every 5 ms; never waits for inference", ha="center", va="bottom", fontsize=6.8, color=BLUE)
    event_t = 53
    ax.vlines(event_t, 0.15, 2.72, color=GREEN, linewidth=1.2, linestyle=(0, (3, 2)))
    ax.plot(event_t, 1.62, marker="o", markersize=5.4, markerfacecolor=GREEN, markeredgecolor=GREEN, zorder=4)
    ax.text(82, 2.82, "first valid result read", ha="left", va="bottom", fontsize=6.5, color=GREEN)

    # Operator motion is continuous; the only configuration transition is
    # triggered once and becomes locked after the 300-ms smooth transition.
    arrow(ax, (0, 0.95), (400, 0.95), NAVY)
    ax.text(200, 1.14, "operator motion proceeds continuously", ha="center", va="bottom", fontsize=6.8, color=NAVY)
    block(ax, event_t, event_t + 22, 0.25, 0.38, "one-shot $\\Theta(c)$", GREEN, GREEN_FILL, fontsize=6.3)
    block(ax, event_t + 22, event_t + 322, 0.25, 0.38, "enabled impedance transition (300 ms)", GREEN, GREEN_FILL, fontsize=6.5)
    arrow(ax, (event_t + 322, 0.44), (400, 0.44), GREEN)
    ax.text(377, 0.63, "strategy locked", ha="center", va="bottom", fontsize=6.6, color=GREEN)

    ax.text(0, -0.04, "Representative timing only; the diagram does not reconstruct a trial-level event trace.",
            ha="left", va="bottom", fontsize=6.3, color=GREY)
    fig.subplots_adjust(left=0.035, right=0.99, bottom=0.08, top=0.96)
    stem = output / "Fig2_timing_sketch"
    fig.savefig(stem.with_suffix(".png"), dpi=600, facecolor="white")
    fig.savefig(stem.with_suffix(".pdf"), facecolor="white")
    fig.savefig(stem.with_suffix(".svg"), facecolor="white")
    plt.close(fig)
    print(f"Saved sketch to: {output.resolve()}")


if __name__ == "__main__":
    main()
