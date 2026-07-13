import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from matplotlib.lines import Line2D

CSV_PATH = Path("../data/vision_validation/results/vision_validation_per_image.csv")

CLASS_ORDER = ["apple", "banana", "cup", "bottle", "mouse", "scissors"]
DISPLAY_NAMES = ["Apple", "Banana", "Paper cup", "Bottle", "Mouse", "Scissors"]

MM_TO_INCH = 1 / 25.4
FIG_SIZE = (180 * MM_TO_INCH, 92 * MM_TO_INCH)
DPI = 300

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "DejaVu Sans"],
    "font.size": 9,
    "axes.labelsize": 10,
    "axes.titlesize": 11,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 8,
    "axes.linewidth": 0.8,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "svg.fonttype": "none",
})

df = pd.read_csv(CSV_PATH)
required_cols = ["expected_coco", "inference_ms"]
missing = [c for c in required_cols if c not in df.columns]
if missing:
    raise ValueError(f"Missing required columns: {missing}")

data = [df.loc[df["expected_coco"] == cls, "inference_ms"].dropna().to_numpy(dtype=float)
        for cls in CLASS_ORDER]
positions = np.arange(1, len(CLASS_ORDER) + 1)
means = np.array([np.mean(v) for v in data])
sds = np.array([np.std(v, ddof=1) for v in data])
overall_mean = float(df["inference_ms"].mean())

rng = np.random.default_rng(2026)
fig, ax = plt.subplots(figsize=FIG_SIZE, dpi=DPI)

for i, values in enumerate(data, start=1):
    x = np.full_like(values, i, dtype=float) + rng.normal(0, 0.045, len(values))
    ax.scatter(x, values, s=18, facecolors="none", linewidths=0.75, alpha=0.90, zorder=2)

ax.errorbar(positions, means, yerr=sds, fmt="s", markersize=6, capsize=5,
            linewidth=1.2, elinewidth=1.2, label="Mean ± SD", zorder=4)

ax.axhline(overall_mean, linestyle="--", linewidth=1.3, label=f"Overall mean = {overall_mean:.2f} ms")

ax.text(0.98, 0.95, "10 Hz reference: 100 ms/frame\n(all class means are below 50 ms)",
        transform=ax.transAxes, ha="right", va="top", fontsize=8.5,
        bbox=dict(boxstyle="round,pad=0.35", facecolor="white", edgecolor="0.6", linewidth=0.8))

ax.text(0.5, 1.06, "(c)", transform=ax.transAxes, ha="center", va="bottom",
        fontsize=11, fontweight="bold")
ax.set_xlabel("Class")
ax.set_ylabel("Processing time (ms)")
ax.set_xticks(positions)
ax.set_xticklabels(DISPLAY_NAMES)
ax.set_xlim(0.5, len(CLASS_ORDER) + 0.5)
ax.set_ylim(42, 56)

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.tick_params(axis="both", direction="out", length=3.5, width=0.8)

scatter_handle = Line2D([0], [0], marker="o", linestyle="none", markerfacecolor="none",
                        markersize=4.8, label="Individual frames (n = 30/class)")
handles, labels = ax.get_legend_handles_labels()
handles = [scatter_handle, handles[0], handles[1]]
labels = [h.get_label() for h in handles]
ax.legend(handles=handles, labels=labels, loc="upper left", frameon=True)

fig.tight_layout()
fig.savefig("Fig4_c_processing_time.png", dpi=DPI, bbox_inches="tight")
plt.close(fig)

print(f"Overall mean processing time: {overall_mean:.2f} ms")
for name, mean, sd in zip(DISPLAY_NAMES, means, sds):
    print(f"{name}: {mean:.2f} ± {sd:.2f} ms")
print("Fig4(c) saved: Fig4_c_processing_time.png")