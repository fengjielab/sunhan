from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "vision_validation" / "results" / "vision_validation_per_image.csv"
OUT = ROOT / "drawing" / "revision_submission"
ORDER = ["apple", "banana", "cup", "bottle", "mouse", "scissors"]
LABELS = ["Apple", "Banana", "Paper cup", "Bottle", "Mouse", "Scissors"]


def mean_sd(values):
    values = np.asarray(values, dtype=float)
    return values.mean(), values.std(ddof=1)


def main():
    df = pd.read_csv(DATA)
    missing = set(ORDER) - set(df["object"].unique())
    if missing:
        raise ValueError(f"Missing object classes: {sorted(missing)}")

    confusion = pd.crosstab(df["object"], df["predicted_coco"]).reindex(
        index=ORDER, columns=ORDER, fill_value=0
    )
    rng = np.random.default_rng(20260713)
    colors = ["#2F6B9A", "#E49B27", "#4E9A6A", "#8C63A8", "#C45A52", "#65717E"]

    fig, axes = plt.subplots(1, 3, figsize=(12.2, 3.75), constrained_layout=True)

    ax = axes[0]
    image = ax.imshow(confusion.values, cmap="Blues", vmin=0, vmax=30)
    for i in range(6):
        for j in range(6):
            value = int(confusion.iloc[i, j])
            ax.text(j, i, str(value), ha="center", va="center",
                    color="white" if value > 15 else "#1A1A1A", fontsize=8)
    ax.set_xticks(range(6), LABELS, rotation=35, ha="right")
    ax.set_yticks(range(6), LABELS)
    ax.set_xlabel("Predicted class")
    ax.set_ylabel("Expected class")
    ax.set_title("(a) Classification (n = 180)", loc="left", fontweight="bold")
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.03, label="Images")

    for ax, column, ylabel, title in [
        (axes[1], "confidence", "Detection confidence", "(b) Confidence"),
        (axes[2], "inference_ms", "Wall-clock time (ms)", "(c) Processing time"),
    ]:
        for x, (name, color) in enumerate(zip(ORDER, colors)):
            values = df.loc[df["object"] == name, column].to_numpy(dtype=float)
            jitter = rng.uniform(-0.16, 0.16, len(values))
            ax.scatter(np.full(len(values), x) + jitter, values, s=13, alpha=0.48,
                       color=color, edgecolors="none", rasterized=True)
            mean, sd = mean_sd(values)
            ax.errorbar(x, mean, yerr=sd, fmt="D", ms=5.2, capsize=3,
                        color="#111111", ecolor="#111111", lw=1.1, zorder=5)
        ax.set_xticks(range(6), LABELS, rotation=35, ha="right")
        ax.set_ylabel(ylabel)
        ax.set_title(title, loc="left", fontweight="bold")
        ax.grid(axis="y", color="#D8D8D8", linewidth=0.7, alpha=0.8)
        ax.spines[["top", "right"]].set_visible(False)

    axes[1].set_ylim(0, 1.02)
    fig.suptitle("Controlled vision evaluation: individual images and class summaries",
                 fontsize=11.5, fontweight="bold")
    OUT.mkdir(parents=True, exist_ok=True)
    for suffix in ("png", "pdf", "svg"):
        kwargs = {"dpi": 600} if suffix == "png" else {}
        fig.savefig(OUT / f"Figure_4.{suffix}", bbox_inches="tight", **kwargs)
    plt.close(fig)


if __name__ == "__main__":
    main()
