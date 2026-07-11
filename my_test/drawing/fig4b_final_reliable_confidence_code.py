import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from matplotlib.lines import Line2D

# ============================================================
# Fig. 4(b): Detection confidence across object classes
# ============================================================

CSV_PATH = Path("../data/vision_validation/results/vision_validation_per_image.csv")

CLASS_ORDER = ["apple", "banana", "cup", "bottle", "mouse", "scissors"]
DISPLAY_NAMES = ["Apple", "Banana", "Paper cup", "Bottle", "Mouse", "Scissors"]
DETECTION_THRESHOLD = 0.25

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
required_cols = ["expected_coco", "confidence"]
missing_cols = [c for c in required_cols if c not in df.columns]
if missing_cols:
    raise ValueError(f"Missing required columns: {missing_cols}")

data = []
for cls in CLASS_ORDER:
    values = df.loc[df["expected_coco"] == cls, "confidence"].dropna().to_numpy(dtype=float)
    if len(values) == 0:
        raise ValueError(f"No confidence data found for class: {cls}")
    data.append(values)

positions = np.arange(1, len(CLASS_ORDER) + 1)
means = np.array([np.mean(v) for v in data])
sds = np.array([np.std(v, ddof=1) for v in data])
overall_mean = float(df["confidence"].mean())

rng = np.random.default_rng(2026)

fig, ax = plt.subplots(figsize=FIG_SIZE, dpi=DPI)

ax.bar(positions, means, yerr=sds, width=0.58, capsize=4, linewidth=0.9, alpha=0.40, label="Mean ± SD")

for i, values in enumerate(data, start=1):
    x = np.full_like(values, i, dtype=float) + rng.normal(0, 0.045, len(values))
    ax.scatter(x, values, s=18, facecolors="none", linewidths=0.75, alpha=0.90, zorder=3)

ax.axhline(overall_mean, linestyle="--", linewidth=1.3, label=f"Overall mean = {overall_mean:.3f}")
ax.axhline(DETECTION_THRESHOLD, linestyle=":", linewidth=1.4, label=f"Detection threshold = {DETECTION_THRESHOLD:.2f}")

ax.set_title("Detection confidence across object classes under controlled conditions")
ax.set_xlabel("Class")
ax.set_ylabel("Detection confidence")
ax.set_xticks(positions)
ax.set_xticklabels(DISPLAY_NAMES)
ax.set_ylim(0.2, 1.02)
ax.set_xlim(0.5, len(CLASS_ORDER) + 0.5)

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.tick_params(axis="both", direction="out", length=3.5, width=0.8)

scatter_handle = Line2D([0], [0], marker="o", linestyle="none", markerfacecolor="none",
                        markersize=4.8, label="Individual detections (n = 30/class)")
handles, labels = ax.get_legend_handles_labels()
handles = [handles[0], scatter_handle, handles[1], handles[2]]
labels = [h.get_label() for h in handles]
ax.legend(handles=handles, labels=labels, loc="lower right", frameon=True)

fig.tight_layout()
fig.savefig("Fig4_b_detection_confidence.png", dpi=DPI, bbox_inches="tight")
plt.close(fig)

print(f"Overall mean confidence: {overall_mean:.3f}")
print("Mean ± SD by class:")
for name, mean, sd in zip(DISPLAY_NAMES, means, sds):
    print(f"{name}: {mean:.3f} ± {sd:.3f}")
print("Fig4(b) saved: Fig4_b_detection_confidence.png")