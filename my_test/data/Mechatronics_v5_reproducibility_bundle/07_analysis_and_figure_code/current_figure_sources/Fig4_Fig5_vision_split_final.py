"""Create the split visual-validation figures for the manuscript.

Fig. 4 contains the controlled-test confusion matrix.  Fig. 5 combines
class-wise detection confidence and per-image processing time.  Both figures
are regenerated directly from the frozen 180-image validation table.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd


ORDER = ["apple", "banana", "cup", "bottle", "mouse", "scissors"]
LABELS = ["Apple", "Banana", "Paper\ncup", "Bottle", "Mouse", "Scissors"]
BLUE = "#22577A"
BLUE_MID = "#4F86A6"
BLUE_LIGHT = "#DCEAF2"
GRID = "#D8DDE2"
GRAY = "#525A61"
RED = "#A33A3A"
THRESHOLD = 0.25


def parse_args() -> argparse.Namespace:
    here = Path(__file__).resolve().parent
    root = here.parents[1]
    parser = argparse.ArgumentParser(description="Generate the split Fig. 4 and Fig. 5 vision-validation figures.")
    parser.add_argument(
        "--data-file",
        type=Path,
        default=root / "05_vision_validation_final_48_19ms" / "vision_validation" / "results" / "vision_validation_per_image.csv",
    )
    parser.add_argument("--output-dir", type=Path, default=root / "reproduced_figures")
    parser.add_argument("--dpi", type=int, default=600)
    return parser.parse_args()


def configure_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "font.size": 8,
            "axes.titlesize": 9,
            "axes.labelsize": 8.5,
            "xtick.labelsize": 7.4,
            "ytick.labelsize": 7.4,
            "axes.linewidth": 0.8,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
        }
    )


def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"expected_coco", "predicted_coco", "confidence", "inference_ms"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    counts = df["expected_coco"].value_counts().reindex(ORDER, fill_value=0)
    if not (counts == 30).all():
        raise ValueError(f"Expected 30 images per class, found {counts.to_dict()}")
    if len(df) != 180:
        raise ValueError(f"Expected 180 images, found {len(df)}")
    return df


def style_axis(ax: plt.Axes, grid_axis: str = "y") -> None:
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.65, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#333333")
    ax.tick_params(colors="#333333")


def draw_confusion_matrix(ax: plt.Axes, df: pd.DataFrame) -> None:
    matrix = pd.crosstab(df["expected_coco"], df["predicted_coco"]).reindex(
        index=ORDER, columns=ORDER, fill_value=0
    )
    for row in range(len(ORDER)):
        for col in range(len(ORDER)):
            value = int(matrix.iloc[row, col])
            ax.add_patch(
                Rectangle(
                    (col - 0.5, row - 0.5),
                    1,
                    1,
                    facecolor=BLUE if value else "#F4F7F9",
                    edgecolor="white",
                    linewidth=1.1,
                )
            )
            ax.text(
                col,
                row,
                str(value),
                ha="center",
                va="center",
                fontsize=8.0,
                fontweight="bold" if value else "normal",
                color="white" if value else "#7B858D",
            )
    ax.set_xlim(-0.5, len(ORDER) - 0.5)
    ax.set_ylim(len(ORDER) - 0.5, -0.5)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks(np.arange(len(ORDER)), LABELS, rotation=35, ha="right")
    ax.set_yticks(np.arange(len(ORDER)), LABELS)
    ax.set_xlabel("Predicted class")
    ax.set_ylabel("True class")
    ax.set_title("Confusion matrix ($n$ = 180)", loc="left", fontweight="bold", pad=5)


def draw_confidence(ax: plt.Axes, df: pd.DataFrame) -> None:
    values = [df.loc[df["expected_coco"] == item, "confidence"].to_numpy(float) for item in ORDER]
    means = np.array([value.mean() for value in values])
    sds = np.array([value.std(ddof=1) for value in values])
    positions = np.arange(len(ORDER))
    overall = float(df["confidence"].mean())

    ax.barh(
        positions,
        means,
        xerr=sds,
        height=0.58,
        color=BLUE_LIGHT,
        edgecolor=BLUE_MID,
        linewidth=0.9,
        error_kw={"ecolor": "#202020", "elinewidth": 1.0, "capsize": 3.0, "capthick": 1.0},
        zorder=2,
    )
    for y, mean in zip(positions, means):
        ax.text(0.025, y, f"{mean:.3f}", ha="left", va="center", fontsize=7.1, fontweight="bold", color="#18394E")
    ax.axvline(overall, color=RED, linewidth=1.0, linestyle="--", zorder=1)
    ax.axvline(THRESHOLD, color=GRAY, linewidth=0.9, linestyle=":", zorder=1)
    ax.text(overall, 1.025, f"Overall mean {overall:.3f}", transform=ax.get_xaxis_transform(), ha="center", va="bottom", fontsize=6.8, color=RED)
    ax.text(THRESHOLD + 0.012, 4.5, "Threshold 0.25", ha="left", va="center", fontsize=6.8, color=GRAY)
    ax.set_xlim(0, 1.01)
    ax.set_ylim(len(ORDER) - 0.5, -0.5)
    ax.set_yticks(positions, LABELS)
    ax.set_xlabel("Detection confidence")
    ax.set_title("(a) Detection confidence", loc="left", fontweight="bold", pad=4)
    style_axis(ax, grid_axis="x")


def draw_runtime(ax: plt.Axes, df: pd.DataFrame) -> None:
    values = [df.loc[df["expected_coco"] == item, "inference_ms"].to_numpy(float) for item in ORDER]
    positions = np.arange(len(ORDER))

    # Horizontal raincloud: half violin below the category baseline, raw
    # observations above it, and a compact IQR/median summary at the baseline.
    violins = ax.violinplot(
        values,
        positions=positions,
        vert=False,
        widths=0.72,
        showmeans=False,
        showmedians=False,
        showextrema=False,
    )
    for position, body in zip(positions, violins["bodies"]):
        vertices = body.get_paths()[0].vertices
        vertices[:, 1] = np.maximum(vertices[:, 1], position)
        body.set_facecolor(BLUE_LIGHT)
        body.set_edgecolor(BLUE_MID)
        body.set_linewidth(0.8)
        body.set_alpha(0.95)
        body.set_zorder(1)

    rng = np.random.default_rng(20260713)
    for x, group in zip(positions, values):
        q1, median, q3 = np.percentile(group, [25, 50, 75])
        ax.scatter(
            group,
            x + rng.uniform(-0.24, -0.06, len(group)),
            s=11,
            color=BLUE_MID,
            edgecolor="white",
            linewidth=0.25,
            alpha=0.72,
            zorder=3,
        )
        ax.hlines(x, q1, q3, color="#151515", linewidth=2.0, zorder=5)
        ax.scatter(median, x, s=22, marker="o", facecolor="white", edgecolor="#151515", linewidth=0.9, zorder=6)

    overall = float(df["inference_ms"].mean())
    lo, hi = float(df["inference_ms"].min()), float(df["inference_ms"].max())
    margin = max(0.70, 0.045 * (hi - lo))
    ax.axvline(overall, color=RED, linewidth=1.0, linestyle="--", zorder=1)
    ax.text(
        0.98,
        0.96,
        f"Overall mean {overall:.2f} ms",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=6.8,
        color=RED,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.86, "pad": 0.7},
    )
    ax.set_xlim(lo - margin, hi + margin)
    ax.set_ylim(len(ORDER) - 0.5, -0.5)
    ax.set_yticks(positions, LABELS)
    ax.set_xlabel("Wall-clock time (ms)")
    ax.set_title("(b) Per-image processing time", loc="left", fontweight="bold", pad=4)
    style_axis(ax, grid_axis="x")


def save(fig: plt.Figure, output_dir: Path, stem: str, dpi: int) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for suffix in ("png", "pdf", "svg"):
        kwargs = {"dpi": dpi} if suffix == "png" else {}
        fig.savefig(output_dir / f"{stem}.{suffix}", bbox_inches="tight", facecolor="white", **kwargs)


def main() -> None:
    args = parse_args()
    configure_style()
    df = load_data(args.data_file)

    fig4, ax4 = plt.subplots(figsize=(3.45, 3.45), facecolor="white")
    draw_confusion_matrix(ax4, df)
    fig4.tight_layout()
    save(fig4, args.output_dir, "Fig4_classification_final", args.dpi)
    plt.close(fig4)

    fig5, axes = plt.subplots(1, 2, figsize=(7.2, 3.1), facecolor="white")
    draw_confidence(axes[0], df)
    draw_runtime(axes[1], df)
    fig5.subplots_adjust(left=0.08, right=0.985, bottom=0.18, top=0.88, wspace=0.34)
    save(fig5, args.output_dir, "Fig5_confidence_runtime_final", args.dpi)
    plt.close(fig5)

    print(f"Input: {args.data_file.resolve()}")
    print(f"Saved: {args.output_dir.resolve()}/Fig4_classification_final.*")
    print(f"Saved: {args.output_dir.resolve()}/Fig5_confidence_runtime_final.*")


if __name__ == "__main__":
    main()
