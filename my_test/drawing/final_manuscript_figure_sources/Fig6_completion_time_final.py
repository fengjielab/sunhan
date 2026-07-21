from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

MODE_ORDER = ["A", "B", "C", "D", "E"]
BASE_EDGE = "#5B8DB8"
METHOD_EDGE = "#6A3D9A"

plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"], "pdf.fonttype": 42, "svg.fonttype": "none"})


def parse_args():
    here = Path(__file__).resolve().parent
    drawing_root = here.parent
    p = argparse.ArgumentParser()
    p.add_argument(
        "--trial-file",
        type=Path,
        default=drawing_root / "Fig5_final_source_and_outputs" / "mnt" / "data" / "Fig5_final_package" / "all_trials_135.csv",
    )
    p.add_argument("--output-dir", type=Path, default=drawing_root / "outputs" / "final_manuscript_figures")
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
    required = {"mode", "duration_s"}
    if missing := required.difference(df.columns):
        raise ValueError(f"Missing columns: {sorted(missing)}")

    fig, ax = plt.subplots(figsize=(3.6, 3.0))
    rng = np.random.default_rng(7)
    for y, mode in enumerate(MODE_ORDER):
        values = df.loc[df["mode"] == mode, "duration_s"].dropna().to_numpy(float)
        q1, median, q3 = np.percentile(values, [25, 50, 75])
        iqr = q3 - q1
        lower_fence, upper_fence = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        inliers = values[(values >= lower_fence) & (values <= upper_fence)]
        outliers = values[(values < lower_fence) | (values > upper_fence)]
        whisker_low, whisker_high = float(inliers.min()), float(inliers.max())
        color = METHOD_EDGE if mode == "C" else BASE_EDGE

        # A compact horizontal interval plot: Tukey whisker, IQR, and median.
        ax.hlines(y, whisker_low, whisker_high, color=color, linewidth=1.15, zorder=1)
        ax.vlines([whisker_low, whisker_high], y - 0.12, y + 0.12, color=color, linewidth=1.15, zorder=1)
        ax.hlines(y, q1, q3, color=color, linewidth=5.0, zorder=2)
        ax.scatter(median, y, s=42, marker="o", facecolors=color, edgecolors="white", linewidths=1.0, zorder=3)
        if outliers.size:
            ax.scatter(
                outliers,
                y + rng.uniform(-0.10, 0.10, outliers.size),
                s=22,
                marker="o",
                facecolors="white",
                edgecolors=color,
                linewidths=0.95,
                zorder=4,
            )

    ax.set_xlim(15, 27)
    ax.set_xticks([16, 18, 20, 22, 24, 26])
    ax.set_ylim(len(MODE_ORDER) - 0.5, -0.5)
    ax.set_yticks(range(len(MODE_ORDER)), MODE_ORDER)
    ax.set_xlabel("Task execution duration (s)", fontsize=9)
    ax.set_ylabel("Experimental mode", fontsize=9)
    format_axes(ax)
    ax.grid(axis="x", linestyle="--", linewidth=0.5, color="#B7B7B7", alpha=0.35)
    ax.grid(axis="y", visible=False)
    fig.tight_layout(pad=0.45)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf", "svg"):
        kwargs = {"dpi": args.dpi} if ext == "png" else {}
        fig.savefig(args.output_dir / f"Fig6_completion_time_final.{ext}", bbox_inches="tight", facecolor="white", **kwargs)
    plt.close(fig)


if __name__ == "__main__":
    main()
