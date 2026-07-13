from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

MODE_ORDER = ["A", "B", "C", "D", "E"]
OPERATORS = ["P01", "P02", "P03"]
MARKERS = {"P01": "o", "P02": "^", "P03": "s"}
OFFSETS = {"P01": -0.11, "P02": 0.00, "P03": 0.11}
BASE_EDGE, BASE_FILL = "#5B8DB8", "#DCEAF5"
METHOD_EDGE, METHOD_FILL = "#6A3D9A", "#D9C7F0"

plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"], "pdf.fonttype": 42, "svg.fonttype": "none"})


def parse_args():
    here = Path(__file__).resolve().parent
    p = argparse.ArgumentParser()
    p.add_argument("--trial-file", type=Path, default=here / "all_trials_135.csv")
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
    df = pd.read_csv(args.trial_file)
    required = {"operator", "mode", "traj_length_m"}
    if missing := required.difference(df.columns):
        raise ValueError(f"Missing columns: {sorted(missing)}")

    fig, ax = plt.subplots(figsize=(3.6, 3.0))
    values = [df.loc[df["mode"] == m, "traj_length_m"].dropna().to_numpy() for m in MODE_ORDER]
    bp = ax.boxplot(values, widths=0.46, patch_artist=True, showfliers=False,
                    medianprops={"color": "#333333", "linewidth": 1.35},
                    whiskerprops={"color": "#5A5A5A", "linewidth": 0.8},
                    capprops={"color": "#5A5A5A", "linewidth": 0.8},
                    boxprops={"linewidth": 0.9})
    for mode, patch in zip(MODE_ORDER, bp["boxes"]):
        patch.set_facecolor(METHOD_FILL if mode == "C" else BASE_FILL)
        patch.set_edgecolor(METHOD_EDGE if mode == "C" else BASE_EDGE)
        patch.set_alpha(0.16)

    rng = np.random.default_rng(11)
    for x0, mode in enumerate(MODE_ORDER, start=1):
        for op in OPERATORS:
            y = df.loc[(df["mode"] == mode) & (df["operator"] == op), "traj_length_m"].dropna().to_numpy()
            x = x0 + OFFSETS[op] + rng.uniform(-0.012, 0.012, size=y.size)
            edge = METHOD_EDGE if mode == "C" else BASE_EDGE
            ax.scatter(x, y, marker=MARKERS[op], s=13, facecolors="white", edgecolors=edge,
                       linewidths=0.65, alpha=0.68, zorder=3)

    ax.set_xlim(0.55, 5.45)
    ax.set_xticks(range(1, 6), MODE_ORDER)
    ax.set_ylabel("Master-side trajectory length (m)", fontsize=9)
    ax.set_ylim(0.5, 1.1)
    ax.set_yticks([0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1])
    format_axes(ax)
    ax.text(0.015, 0.985, "(b)", transform=ax.transAxes, ha="left", va="top", fontsize=10.5, fontweight="bold")

    handles = [Line2D([0], [0], marker=MARKERS[o], linestyle="none", markerfacecolor="white",
                      markeredgecolor="#6B6B6B", markeredgewidth=0.8, markersize=5.2, label=o) for o in OPERATORS]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 1.18), ncol=3, frameon=False, fontsize=8)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf", "svg"):
        kwargs = {"dpi": args.dpi} if ext == "png" else {}
        fig.savefig(args.output_dir / f"Fig5_b_trajectory_length_final.{ext}", bbox_inches="tight", facecolor="white", **kwargs)
    plt.close(fig)


if __name__ == "__main__":
    main()
