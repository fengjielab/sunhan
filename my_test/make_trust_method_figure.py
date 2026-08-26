#!/usr/bin/env python3
"""Create the manuscript-ready mechanism/ablation figure for the trust loop."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np

from trust_correction import (
    TrustCorrectionConfig,
    TrustCorrectionState,
    update_trust_correction,
)


OUT = Path(__file__).resolve().parent / "正宫" / "05_figures"
BLUE = "#2563EB"
ORANGE = "#D97706"
GREEN = "#059669"
RED = "#DC2626"
DARK = "#1F2937"
MUTED = "#6B7280"
LIGHT = "#F3F4F6"


def rounded_box(ax, xy, width, height, text, color, fontsize=9):
    box = FancyBboxPatch(
        xy, width, height,
        boxstyle="round,pad=0.015,rounding_size=0.025",
        facecolor=color + "18", edgecolor=color, linewidth=1.4,
    )
    ax.add_patch(box)
    ax.text(
        xy[0] + width / 2, xy[1] + height / 2, text,
        ha="center", va="center", color=DARK, fontsize=fontsize,
    )
    return box


def arrow(ax, start, end, color=DARK, connectionstyle="arc3"):
    ax.add_patch(FancyArrowPatch(
        start, end, arrowstyle="-|>", mutation_scale=12,
        linewidth=1.35, color=color, connectionstyle=connectionstyle,
    ))


def simulate(prior_K: float, force: float, duration: float = 1.5):
    cfg = TrustCorrectionConfig()
    state = TrustCorrectionState()
    current = prior_K
    ts, trusts, stiffness = [0.0], [1.0], [prior_K]
    for index in range(1, int(duration / cfg.update_interval_s) + 1):
        sample_time = index * cfg.update_interval_s
        if cfg.contact_delay_s <= sample_time <= cfg.posterior_window_s:
            result = update_trust_correction(
                state,
                force_mag_N=force,
                force_threshold_N=1.0,
                current_K=current,
                prior_K=prior_K,
                config=cfg,
            )
            state = result.state
            current = result.command_K
        ts.append(sample_time)
        trusts.append(state.trust)
        stiffness.append(current)
    return np.asarray(ts), np.asarray(trusts), np.asarray(stiffness)


def panel_loop(ax):
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    rounded_box(ax, (0.02, 0.63), 0.20, 0.18, "Visual semantic\nprior  $K_v$", BLUE)
    rounded_box(ax, (0.29, 0.63), 0.20, 0.18, "Applied robot\nimpedance  $K_k$", GREEN)
    rounded_box(ax, (0.56, 0.63), 0.20, 0.18, "Physical contact\nresponse  $|F_k|$", ORANGE)
    rounded_box(ax, (0.56, 0.22), 0.20, 0.18, "Smoothed contact\nrisk  $\\bar r_k$", RED)
    rounded_box(ax, (0.29, 0.22), 0.20, 0.18, "Prior trust\n$\\tau_{k+1}\\leq\\tau_k$", BLUE)
    rounded_box(
        ax, (0.02, 0.22), 0.20, 0.18,
        "Bounded target\n$K_k^*=\\tau K_v$\n$+(1-\\tau)K_s$", GREEN, 7.4,
    )
    arrow(ax, (0.22, 0.72), (0.29, 0.72))
    arrow(ax, (0.49, 0.72), (0.56, 0.72))
    arrow(ax, (0.66, 0.63), (0.66, 0.40), ORANGE)
    arrow(ax, (0.56, 0.31), (0.49, 0.31), RED)
    arrow(ax, (0.29, 0.31), (0.22, 0.31), BLUE)
    arrow(ax, (0.12, 0.40), (0.32, 0.63), GREEN, "arc3,rad=-0.25")
    ax.text(0.12, 0.50, "20 Hz update", ha="center", color=MUTED, fontsize=8)
    ax.text(0.02, 0.95, "a  Closed-loop prior correction", color=DARK, fontsize=11, fontweight="bold")
    ax.text(
        0.02, 0.05,
        "Raw vision is logged separately in the counterfactual experiment;\n"
        "contact risk reduces trust but does not relabel the material.",
        color=MUTED, fontsize=8, va="bottom",
    )


def panel_response(ax):
    t_w, trust_w, k_w = simulate(200.0, 4.0)
    t_c, trust_c, k_c = simulate(120.0, 2.0)
    ax.plot(t_w, k_w, color=RED, linewidth=2.2, label="W1: overstiff prior, 4 N")
    ax.plot(t_c, k_c, color=BLUE, linewidth=2.2, label="C1: mouse prior, 2 N")
    ax.axhline(50, color=GREEN, linewidth=1.2, linestyle="--", label="Safe anchor")
    ax.axvline(0.80, color=MUTED, linewidth=1.1, linestyle="--", label="Window end")
    ax.set_xlim(0, 1.5)
    ax.set_ylim(45, 205)
    ax.set_xlabel("Time after contact onset (s)")
    ax.set_ylabel("Translational stiffness (N/m)")
    ax.grid(axis="y", color="#D1D5DB", linewidth=0.6)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    trust_ax = ax.twinx()
    trust_ax.plot(t_w, trust_w, color=RED, linewidth=1.1, linestyle=":")
    trust_ax.plot(t_c, trust_c, color=BLUE, linewidth=1.1, linestyle=":")
    trust_ax.set_ylim(-0.02, 1.02)
    trust_ax.set_ylabel("Prior trust (dotted)")
    trust_ax.spines["top"].set_visible(False)
    ax.text(-0.12, 1.08, "b  Auditable bounded response", transform=ax.transAxes,
            color=DARK, fontsize=11, fontweight="bold")


def panel_ablation(ax):
    ax.set_xlim(0, 2)
    ax.set_ylim(0, 2)
    ax.set_xticks([0.5, 1.5], ["Correction off", "Correction on"])
    ax.set_yticks([0.5, 1.5], ["Overstiff prior", "Correct prior"])
    ax.tick_params(length=0)
    ax.set_aspect("equal")
    cells = [
        (0, 1, "C0", "Correct baseline", BLUE),
        (1, 1, "C1", "Over-intervention\ncheck", GREEN),
        (0, 0, "W0", "Error\ncounterfactual", ORANGE),
        (1, 0, "W1", "Closed-loop\ncorrection", RED),
    ]
    for x, y, code, desc, color in cells:
        rect = FancyBboxPatch(
            (x + 0.05, y + 0.08), 0.90, 0.84,
            boxstyle="round,pad=0.02,rounding_size=0.04",
            facecolor=color + "18", edgecolor=color, linewidth=1.5,
        )
        ax.add_patch(rect)
        ax.text(x + 0.5, y + 0.60, code, ha="center", va="center",
                fontsize=15, color=DARK, fontweight="bold")
        ax.text(x + 0.5, y + 0.34, desc, ha="center", va="center",
                fontsize=7.0, color=MUTED)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.text(-0.25, 2.12, "c  Counterfactual 2×2 test", color=DARK,
            fontsize=11, fontweight="bold")
    ax.text(
        1.0, -0.24,
        "Primary interaction: (W1−W0) − (C1−C0)",
        ha="center", va="top", fontsize=9, color=DARK,
    )


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(13.2, 4.2), constrained_layout=True)
    grid = fig.add_gridspec(1, 3, width_ratios=[1.35, 1.2, 0.85])
    panel_loop(fig.add_subplot(grid[0, 0]))
    panel_response(fig.add_subplot(grid[0, 1]))
    panel_ablation(fig.add_subplot(grid[0, 2]))
    stem = OUT / "fig7_prior_trust_loop_and_counterfactual_design"
    fig.savefig(stem.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".png"), dpi=600, bbox_inches="tight")
    plt.close(fig)
    print(stem)


if __name__ == "__main__":
    main()
