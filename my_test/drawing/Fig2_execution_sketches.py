"""Generate two high-information preview alternatives for manuscript Fig. 2.

The previews are not copied into the LaTeX manuscript until selected.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon


NAVY = "#174A7E"
BLUE = "#4F86A6"
BLUE_FILL = "#EAF2F8"
GREEN = "#2E8B57"
GREEN_FILL = "#EAF7EF"
GREY = "#64707A"
LIGHT = "#D9E0E6"


def arrow(ax, start, end, *, color=NAVY, dashed=False, width=1.05, size=8):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=size,
                                 linewidth=width, linestyle=(0, (3, 2)) if dashed else "solid",
                                 color=color, shrinkA=1.2, shrinkB=1.2, zorder=2))


def rounded(ax, x, y, w, h, text, *, edge=NAVY, fill=BLUE_FILL, fontsize=7.2, weight="normal"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.2,rounding_size=0.5",
                                linewidth=1.0, edgecolor=edge, facecolor=fill, zorder=2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize,
            color="#17232D", fontweight=weight, linespacing=1.07, zorder=3)


def save(fig, output: Path, stem: str):
    fig.savefig(output / f"{stem}.png", dpi=600, facecolor="white")
    fig.savefig(output / f"{stem}.pdf", facecolor="white")
    fig.savefig(output / f"{stem}.svg", facecolor="white")
    plt.close(fig)


def sequence_diagram(output: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    ax.text(3, 96, "(a) Multi-rate execution sequence", fontsize=10.4, fontweight="bold", color="#111820")
    ax.text(97, 96, "Time increases downward", ha="right", fontsize=6.8, color=GREY)

    cols = [9, 25, 40, 56, 72, 89]
    labels = ["Camera", "Frame queue\n(1 slot)", "YOLO11n\nworker", "Result queue\n(2 slots)", "200-Hz\nsupervisor", "Robot / haptics\n/ gripper"]
    for x, label in zip(cols, labels):
        rounded(ax, x - 6.3, 83, 12.6, 7.8, label, fontsize=6.7, weight="bold")
        ax.vlines(x, 10, 83, color=LIGHT, linewidth=0.85, linestyle=(0, (2, 2)), zorder=0)

    ax.text(3, 76, r"$t_0$", fontsize=6.8, color=GREY)
    ax.hlines(75, 6, 93, color=LIGHT, linewidth=0.7)

    # Representative asynchronous exchange; messages are concrete but not a
    # trial-level timestamp reconstruction.
    arrow(ax, (9, 75), (25, 75), color=NAVY)
    ax.text(17, 77, "write latest RGB frame\n(15 fps)", ha="center", va="bottom", fontsize=6.0, color=NAVY)
    arrow(ax, (25, 68), (40, 68), color=NAVY)
    ax.text(32.5, 70, "read latest frame", ha="center", va="bottom", fontsize=6.0, color=NAVY)
    arrow(ax, (72, 62), (56, 62), color=BLUE, dashed=True)
    ax.text(64, 64, "poll() every 5 ms\nreturns immediately", ha="center", va="bottom", fontsize=6.0, color=BLUE)
    arrow(ax, (56, 57), (72, 57), color=BLUE, dashed=True)
    ax.text(64, 54.5, "latest result or empty", ha="center", va="top", fontsize=6.0, color=BLUE)
    arrow(ax, (40, 49), (56, 49), color=NAVY)
    ax.text(48, 51, "write class $c$, confidence $p$\n(mean inference 48.19 ms/image)", ha="center", va="bottom", fontsize=5.9, color=NAVY)
    arrow(ax, (72, 42), (56, 42), color=BLUE, dashed=True)
    ax.text(64, 44, "next non-blocking poll", ha="center", va="bottom", fontsize=6.0, color=BLUE)
    arrow(ax, (56, 37), (72, 37), color=GREEN, dashed=True)
    ax.text(64, 34.6, "first $p\\geq0.25$ result\nwith a valid mapping", ha="center", va="top", fontsize=6.0, color=GREEN)
    arrow(ax, (72, 28), (89, 28), color=GREEN)
    ax.text(80.5, 30, "one-shot $\\Theta(c)$\napply enabled channels", ha="center", va="bottom", fontsize=6.0, color=GREEN)

    # Continuous control is deliberately shown throughout the visual exchange.
    ax.add_patch(FancyBboxPatch((5, 13), 90, 8.5, boxstyle="round,pad=0.25,rounding_size=0.6",
                                linewidth=1.0, edgecolor=NAVY, facecolor="#F8FBFD", zorder=0))
    arrow(ax, (9, 17.2), (89, 17.2), color=NAVY, width=1.45)
    ax.text(49, 19.2, "Continuous master / robot control and haptic feedback proceed throughout", ha="center",
            va="bottom", fontsize=6.8, color=NAVY)
    ax.text(49, 7.2, "Illustrative message sequence; queue capacity, rates, and event conditions match the implementation.",
            ha="center", va="center", fontsize=6.2, color=GREY)
    fig.subplots_adjust(left=0.02, right=0.985, bottom=0.035, top=0.98)
    save(fig, output, "Fig2a_multirate_sequence_sketch")


def state_machine(output: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 3.65))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 72)
    ax.axis("off")
    ax.text(3, 67.8, "(b) Strategy-event and locking state machine", fontsize=10.4, fontweight="bold", color="#111820")
    ax.text(97, 67.8, "Modes C--E", ha="right", fontsize=6.8, color=GREY)

    rounded(ax, 4, 43, 18, 10, "Initialize mode-specific\nsettings ($\\Theta_0$)", fontsize=7.4, weight="bold")
    rounded(ax, 29, 43, 18, 10, "Poll latest result\n(non-blocking)", fontsize=7.4, weight="bold")
    ax.add_patch(Polygon([[59, 53], [68, 48], [59, 43], [50, 48]], closed=True,
                         edgecolor=NAVY, facecolor=BLUE_FILL, linewidth=1.0, zorder=2))
    ax.text(59, 48, "Valid\nmapped\nresult?", ha="center", va="center", fontsize=6.4, fontweight="bold", color="#17232D", zorder=3)
    rounded(ax, 75, 43, 19, 10, "Apply mode-enabled\nstrategy event $\\Theta(c)$", edge=GREEN,
            fill=GREEN_FILL, fontsize=7.2, weight="bold")

    arrow(ax, (22, 48), (29, 48))
    arrow(ax, (47, 48), (50, 48))
    arrow(ax, (68, 48), (75, 48), color=GREEN)
    ax.text(71.5, 50.5, "yes", ha="center", va="bottom", fontsize=6.3, color=GREEN)
    arrow(ax, (59, 43), (38, 35), color=GREY)
    ax.text(48, 38.5, "no / low confidence", ha="center", va="bottom", fontsize=6.0, color=GREY)
    arrow(ax, (38, 35), (38, 43), color=GREY)
    ax.text(17, 34.5, "Retain initialized state; continue polling", fontsize=6.4, color=GREY, ha="left")

    rounded(ax, 18, 17, 25, 10, "Parameter transition\n$K_t,K_r,\\zeta$: smoothstep ~300 ms\n$K_f,d,v_g,F_g$: update if enabled",
            edge=GREEN, fill=GREEN_FILL, fontsize=6.6, weight="bold")
    rounded(ax, 56, 17, 24, 10, "Strategy locked for the trial\nignore subsequent detections", edge=GREEN,
            fill=GREEN_FILL, fontsize=7.0, weight="bold")
    arrow(ax, (84.5, 43), (30.5, 27), color=GREEN)
    arrow(ax, (43, 22), (56, 22), color=GREEN)
    ax.text(49.5, 24.3, "transition complete", ha="center", va="bottom", fontsize=6.2, color=GREEN)

    # The mode-specific and fallback handling are explicit without turning the
    # diagram into a duplicate of Table 3.
    rounded(ax, 4, 4, 30, 7.2, "Unmapped class $\\rightarrow$ balanced strategy before $\\Theta(c)$", edge=GREY,
            fill="#F7F8FA", fontsize=6.5)
    rounded(ax, 41, 4, 25, 7.2, "Mode D: show cue, retain $\\Theta_0$", edge=GREY, fill="#F7F8FA", fontsize=6.5)
    rounded(ax, 73, 4, 22, 7.2, "Task end $\\rightarrow$ reset next trial", edge=GREY, fill="#F7F8FA", fontsize=6.5)
    ax.text(50, 0.9, "State machine formalizes one-shot update, fallback behavior, and intra-trial locking.",
            ha="center", va="bottom", fontsize=6.2, color=GREY)
    fig.subplots_adjust(left=0.02, right=0.985, bottom=0.025, top=0.98)
    save(fig, output, "Fig2b_strategy_locking_sketch")


def main() -> None:
    output = Path(__file__).resolve().parent / "outputs" / "fig2_execution_sketches"
    output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
                         "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none"})
    sequence_diagram(output)
    state_machine(output)
    print(f"Saved sketches to: {output.resolve()}")


if __name__ == "__main__":
    main()
