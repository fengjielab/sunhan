"""Generate publication-ready Fig. 4 from the frozen per-image vision data.

The figure is sized for a two-column journal layout and contains only quantities
that can be reproduced from ``vision_validation_per_image.csv``.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "vision_validation" / "results" / "vision_validation_per_image.csv"
OUT = ROOT / "drawing" / "revision_submission"

ORDER = ["apple", "banana", "cup", "bottle", "mouse", "scissors"]
LABELS = ["Apple", "Banana", "Paper\ncup", "Bottle", "Mouse", "Scissors"]

BLUE = "#22577A"
BLUE_MID = "#4F86A6"
BLUE_LIGHT = "#DCEAF2"
GRAY = "#525A61"
GRID = "#D8DDE2"
RED = "#A33A3A"


def configure_style():
    """Use conservative typography and editable vector text."""
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "DejaVu Sans"],
            "font.size": 8.0,
            "axes.titlesize": 9.0,
            "axes.labelsize": 8.5,
            "xtick.labelsize": 7.3,
            "ytick.labelsize": 7.3,
            "axes.linewidth": 0.8,
            "xtick.major.width": 0.8,
            "ytick.major.width": 0.8,
            "xtick.major.size": 3.0,
            "ytick.major.size": 3.0,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
        }
    )


def validate_data(df):
    required = {
        "object",
        "expected_coco",
        "predicted_coco",
        "class_correct",
        "trigger_correct",
        "confidence",
        "inference_ms",
    }
    missing_columns = required - set(df.columns)
    if missing_columns:
        raise ValueError(f"Missing columns: {sorted(missing_columns)}")

    missing_classes = set(ORDER) - set(df["object"].unique())
    if missing_classes:
        raise ValueError(f"Missing object classes: {sorted(missing_classes)}")

    counts = df.groupby("object", observed=False).size().reindex(ORDER)
    if not (counts == 30).all():
        raise ValueError(f"Expected 30 images per class, obtained {counts.to_dict()}")


def style_distribution_axis(ax):
    ax.grid(axis="y", color=GRID, linewidth=0.65, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#333333")
    ax.tick_params(colors="#333333")


def grouped_distribution(ax, df, column, ylabel, panel_title, rng):
    values_by_class = [
        df.loc[df["object"] == name, column].to_numpy(dtype=float) for name in ORDER
    ]
    positions = np.arange(len(ORDER))

    bp = ax.boxplot(
        values_by_class,
        positions=positions,
        widths=0.48,
        patch_artist=True,
        showfliers=False,
        whis=1.5,
        medianprops={"color": "#1B1B1B", "linewidth": 1.2},
        boxprops={"facecolor": BLUE_LIGHT, "edgecolor": BLUE_MID, "linewidth": 0.9},
        whiskerprops={"color": BLUE_MID, "linewidth": 0.9},
        capprops={"color": BLUE_MID, "linewidth": 0.9},
    )
    for patch in bp["boxes"]:
        patch.set_zorder(1)

    for x, values in zip(positions, values_by_class):
        jitter = rng.uniform(-0.17, 0.17, len(values))
        ax.scatter(
            np.full(len(values), x) + jitter,
            values,
            s=10,
            facecolor=BLUE_MID,
            edgecolor="white",
            linewidth=0.25,
            alpha=0.62,
            zorder=2,
        )
        mean = values.mean()
        sd = values.std(ddof=1)
        ax.errorbar(
            x,
            mean,
            yerr=sd,
            fmt="D",
            markersize=4.2,
            markerfacecolor="white",
            markeredgecolor="#111111",
            markeredgewidth=0.9,
            color="#111111",
            ecolor="#111111",
            elinewidth=1.0,
            capsize=2.8,
            capthick=1.0,
            zorder=4,
        )

    ax.set_xticks(positions, LABELS)
    ax.set_xlim(-0.55, len(ORDER) - 0.45)
    ax.set_ylabel(ylabel)
    ax.set_title(panel_title, loc="left", fontweight="bold", pad=4)
    style_distribution_axis(ax)


def confidence_summary(ax, df, overall_confidence, threshold):
    """Horizontal class-mean bars with SD uncertainty for confidence."""
    positions = np.arange(len(ORDER))
    values_by_class = [
        df.loc[df["object"] == name, "confidence"].to_numpy(dtype=float)
        for name in ORDER
    ]
    means = np.array([values.mean() for values in values_by_class])
    sds = np.array([values.std(ddof=1) for values in values_by_class])

    ax.barh(
        positions,
        means,
        xerr=sds,
        height=0.58,
        color=BLUE_LIGHT,
        edgecolor=BLUE_MID,
        linewidth=0.9,
        error_kw={
            "ecolor": "#202020",
            "elinewidth": 1.0,
            "capsize": 3.0,
            "capthick": 1.0,
        },
        zorder=2,
    )
    for y, mean in zip(positions, means):
        ax.text(
            0.025,
            y,
            f"{mean:.3f}",
            ha="left",
            va="center",
            fontsize=7.1,
            fontweight="bold",
            color="#18394E",
            zorder=4,
        )

    ax.axvline(overall_confidence, color=RED, linewidth=1.0, linestyle="--", zorder=1)
    ax.axvline(threshold, color=GRAY, linewidth=0.9, linestyle=":", zorder=1)
    ax.set_xlim(0.0, 1.01)
    ax.set_ylim(len(ORDER) - 0.5, -0.5)
    ax.set_yticks(positions, LABELS)
    ax.set_xlabel("Detection confidence")
    ax.set_title("(b) Detection confidence", loc="left", fontweight="bold", pad=4)
    ax.grid(axis="x", color=GRID, linewidth=0.65, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#333333")
    ax.tick_params(colors="#333333")
    ax.text(
        overall_confidence,
        1.025,
        f"Overall mean {overall_confidence:.3f}",
        transform=ax.get_xaxis_transform(),
        ha="center",
        va="bottom",
        fontsize=6.8,
        color=RED,
        clip_on=False,
    )
    ax.text(
        threshold + 0.012,
        4.5,
        "Threshold 0.25",
        ha="left",
        va="center",
        fontsize=6.8,
        color=GRAY,
    )


def main():
    configure_style()
    df = pd.read_csv(DATA)
    validate_data(df)

    confusion = pd.crosstab(df["expected_coco"], df["predicted_coco"]).reindex(
        index=ORDER, columns=ORDER, fill_value=0
    )
    overall_confidence = float(df["confidence"].mean())
    overall_time = float(df["inference_ms"].mean())
    threshold = 0.25

    fig = plt.figure(figsize=(7.2, 4.55), facecolor="white")
    gs = fig.add_gridspec(
        2,
        2,
        width_ratios=[1.02, 1.42],
        height_ratios=[1, 1],
        left=0.085,
        right=0.985,
        bottom=0.12,
        top=0.96,
        wspace=0.38,
        hspace=0.48,
    )
    ax_cm = fig.add_subplot(gs[:, 0])
    ax_conf = fig.add_subplot(gs[0, 1])
    ax_time = fig.add_subplot(gs[1, 1])

    # (a) Confusion matrix. The compact two-color scale avoids an unnecessary
    # colorbar when every diagonal count is 30 and every off-diagonal count is 0.
    for i in range(len(ORDER)):
        for j in range(len(ORDER)):
            value = int(confusion.iloc[i, j])
            ax_cm.add_patch(
                Rectangle(
                    (j - 0.5, i - 0.5),
                    1,
                    1,
                    facecolor=BLUE if value else "#F4F7F9",
                    edgecolor="white",
                    linewidth=1.1,
                )
            )
    ax_cm.set_xlim(-0.5, len(ORDER) - 0.5)
    ax_cm.set_ylim(len(ORDER) - 0.5, -0.5)
    ax_cm.set_aspect("equal", adjustable="box")
    ax_cm.set_anchor("N")
    for i in range(len(ORDER)):
        for j in range(len(ORDER)):
            value = int(confusion.iloc[i, j])
            ax_cm.text(
                j,
                i,
                str(value),
                ha="center",
                va="center",
                fontsize=7.7,
                fontweight="bold" if value else "normal",
                color="white" if value >= 15 else "#7B858D",
            )
    ax_cm.set_xticks(np.arange(len(ORDER)), LABELS, rotation=38, ha="right")
    ax_cm.set_yticks(np.arange(len(ORDER)), LABELS)
    ax_cm.set_xlabel("Predicted class")
    ax_cm.set_ylabel("True class")
    ax_cm.set_title("(a) Confusion matrix ($n$ = 180)", loc="left", fontweight="bold", pad=5)

    rng = np.random.default_rng(20260713)
    confidence_summary(ax_conf, df, overall_confidence, threshold)

    grouped_distribution(
        ax_time,
        df,
        "inference_ms",
        "Wall-clock time (ms)",
        "(c) Per-image processing time",
        rng,
    )
    time_min = float(df["inference_ms"].min())
    time_max = float(df["inference_ms"].max())
    margin = max(1.0, 0.08 * (time_max - time_min))
    ax_time.set_ylim(time_min - margin, time_max + margin)
    ax_time.axhline(overall_time, color=RED, linewidth=1.0, linestyle="--", zorder=1)
    ax_time.text(
        0.98,
        0.94,
        f"Overall mean {overall_time:.2f} ms",
        transform=ax_time.transAxes,
        ha="right",
        va="top",
        fontsize=7.0,
        color=RED,
    )

    OUT.mkdir(parents=True, exist_ok=True)
    for suffix in ("png", "pdf", "svg"):
        kwargs = {"dpi": 600} if suffix == "png" else {}
        fig.savefig(
            OUT / f"Figure_4.{suffix}",
            bbox_inches="tight",
            facecolor="white",
            **kwargs,
        )
    plt.close(fig)

    print(f"Saved Figure_4.png/.pdf/.svg to {OUT}")
    print(f"Overall confidence: {overall_confidence:.6f}")
    print(f"Overall processing time: {overall_time:.6f} ms")


if __name__ == "__main__":
    main()
