from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

MODE_ORDER = ["A", "B", "C", "D", "E"]
SUCCESS_COUNTS = {"A": 22, "B": 21, "C": 26, "D": 24, "E": 24}
N_ATTEMPTS = 27
BASE_EDGE, METHOD_EDGE, METHOD_FILL = "#5B8DB8", "#6A3D9A", "#D9C7F0"

plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"], "pdf.fonttype": 42, "svg.fonttype": "none"})


def parse_args():
    here = Path(__file__).resolve().parent
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", type=Path, default=here / "outputs")
    p.add_argument("--dpi", type=int, default=600)
    return p.parse_args()


def format_axes(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(0.8)
    ax.spines["bottom"].set_linewidth(0.8)
    ax.tick_params(axis="both", labelsize=8, width=0.8, length=3)
    ax.grid(axis="y", linestyle="--", linewidth=0.5, color="#B7B7B7", alpha=0.35)
    ax.set_axisbelow(True)


def main():
    args = parse_args()
    fig, ax = plt.subplots(figsize=(3.6, 3.0))
    xs = np.arange(1, 6)
    rates = np.array([SUCCESS_COUNTS[m] / N_ATTEMPTS * 100 for m in MODE_ORDER])

    for x, mode, rate in zip(xs, MODE_ORDER, rates):
        edge = METHOD_EDGE if mode == "C" else BASE_EDGE
        face = METHOD_FILL if mode == "C" else "white"
        ax.vlines(x, 0, rate, color=edge, linewidth=1.65, zorder=1)
        ax.scatter(x, rate, s=100, facecolors=face, edgecolors=edge, linewidths=1.05, zorder=3)
        ax.text(x, rate + 2.5, f"{SUCCESS_COUNTS[mode]}/{N_ATTEMPTS}\n({rate:.1f}%)",
                ha="center", va="bottom", fontsize=7.4, linespacing=0.95)

    ax.set_xlim(0.55, 5.45)
    ax.set_xticks(xs, MODE_ORDER)
    ax.set_ylabel("Task success rate (%)", fontsize=9)
    ax.set_ylim(0, 112)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    format_axes(ax)
    ax.text(0.015, 0.985, "(d)", transform=ax.transAxes, ha="left", va="top", fontsize=10.5, fontweight="bold")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf", "svg"):
        kwargs = {"dpi": args.dpi} if ext == "png" else {}
        fig.savefig(args.output_dir / f"Fig5_d_success_rate_final.{ext}", bbox_inches="tight", facecolor="white", **kwargs)
    plt.close(fig)


if __name__ == "__main__":
    main()
