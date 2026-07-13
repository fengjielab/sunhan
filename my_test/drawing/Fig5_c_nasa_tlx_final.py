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
    p.add_argument("--nasa-file", type=Path, default=here / "nasa.md")
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
    df = pd.read_csv(args.nasa_file)
    required = {"operator", "mode", "mental_demand", "physical_demand", "temporal_demand", "performance", "effort", "frustration"}
    if missing := required.difference(df.columns):
        raise ValueError(f"Missing columns: {sorted(missing)}")

    op_map = {1: "P01", 2: "P02", 3: "P03", "1": "P01", "2": "P02", "3": "P03"}
    df["operator_id"] = df["operator"].map(op_map)
    dimensions = ["mental_demand", "physical_demand", "temporal_demand", "performance", "effort", "frustration"]
    df["Raw_NASA_TLX"] = df[dimensions].mean(axis=1)
    op_means = df.groupby(["operator_id", "mode"], as_index=False)["Raw_NASA_TLX"].mean()

    fig, ax = plt.subplots(figsize=(3.6, 3.0))
    for op in OPERATORS:
        rows = op_means.loc[op_means["operator_id"] == op].set_index("mode").reindex(MODE_ORDER)
        xs = np.arange(1, 6, dtype=float) + OFFSETS[op]
        ax.plot(xs, rows["Raw_NASA_TLX"].to_numpy(), color="#A8A8A8", linewidth=0.75, alpha=0.60, zorder=1)

    strategy_offsets = np.array([-0.024, 0.0, 0.024])
    for x0, mode in enumerate(MODE_ORDER, start=1):
        for op in OPERATORS:
            y = df.loc[(df["mode"] == mode) & (df["operator_id"] == op), "Raw_NASA_TLX"].to_numpy()
            edge = METHOD_EDGE if mode == "C" else BASE_EDGE
            fill = METHOD_FILL if mode == "C" else BASE_FILL
            x = x0 + OFFSETS[op] + strategy_offsets[: y.size]
            ax.scatter(x, y, marker=MARKERS[op], s=10, facecolors=fill, edgecolors=edge,
                       linewidths=0.40, alpha=0.38, zorder=2)

            mean_value = op_means.loc[(op_means["operator_id"] == op) & (op_means["mode"] == mode), "Raw_NASA_TLX"]
            if not mean_value.empty:
                ax.scatter(x0 + OFFSETS[op], float(mean_value.iloc[0]), marker=MARKERS[op], s=30,
                           facecolors="white", edgecolors=edge, linewidths=0.95, zorder=4)

    ax.set_xlim(0.55, 5.45)
    ax.set_xticks(range(1, 6), MODE_ORDER)
    ax.set_ylabel("Raw NASA-TLX score", fontsize=9)
    ax.set_ylim(35, 80)
    ax.set_yticks(range(35, 81, 5))
    format_axes(ax)
    ax.text(0.015, 0.985, "(c)", transform=ax.transAxes, ha="left", va="top", fontsize=10.5, fontweight="bold")

    handles = [Line2D([0], [0], marker=MARKERS[o], linestyle="none", markerfacecolor="white",
                      markeredgecolor="#6B6B6B", markeredgewidth=0.8, markersize=5.2, label=o) for o in OPERATORS]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 1.18), ncol=3, frameon=False, fontsize=8)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf", "svg"):
        kwargs = {"dpi": args.dpi} if ext == "png" else {}
        fig.savefig(args.output_dir / f"Fig5_c_nasa_tlx_final.{ext}", bbox_inches="tight", facecolor="white", **kwargs)
    plt.close(fig)


if __name__ == "__main__":
    main()
