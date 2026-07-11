import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

df = pd.read_csv(r"../data/all_trials_135.csv")

pivot = (
    df.pivot_table(
        index=["operator", "group_num", "specific_object"],
        columns="mode",
        values="duration_s"
    )
    .reset_index()
)
pivot["delta"] = pivot["C"] - pivot["E"]

obj_map = {
    "苹果 (apple)": "Apple",
    "香蕉 (banana)": "Banana",
    "纸杯 (paper cup)": "Paper cup",
    "瓶子 (bottle)": "Bottle",
    "鼠标 (mouse)": "Mouse",
    "剪刀 (scissors)": "Scissors",
}
pivot["object_en"] = pivot["specific_object"].map(obj_map)

objects = ["Bottle", "Banana", "Apple", "Mouse", "Paper cup", "Scissors"]

rng = np.random.default_rng(42)
rows = []
for obj in objects:
    vals = pivot.loc[pivot["object_en"] == obj, "delta"].to_numpy()
    boot = rng.choice(vals, size=(20000, len(vals)), replace=True).mean(axis=1)
    low, high = np.quantile(boot, [0.025, 0.975])
    rows.append(
        {
            "object": obj,
            "mean": vals.mean(),
            "low": low,
            "high": high,
            "n_improved": int((vals < 0).sum()),
            "n_total": len(vals),
        }
    )

stats = pd.DataFrame(rows)
stats = stats.sort_values("mean", ascending=True).reset_index(drop=True)

fig, ax = plt.subplots(figsize=(8.4, 5.6))

y = np.arange(len(stats))[::-1]

for yi, row in zip(y, stats.itertuples(index=False)):
    ax.errorbar(
        row.mean,
        yi,
        xerr=[[row.mean - row.low], [row.high - row.mean]],
        fmt="o",
        capsize=4,
        markersize=7,
        linewidth=1.6,
        zorder=3
    )

ax.axvline(0, linestyle="--", linewidth=1)

ax.set_yticks(y)
ax.set_yticklabels(stats["object"], fontsize=11)
ax.set_xlabel(r"$\Delta T = T_C - T_E$ (s)", fontsize=12)
ax.set_ylabel("Object", fontsize=12)
ax.set_title("Object-level robustness of C–E improvement\n(sorted by improvement magnitude)", fontsize=14, pad=10)

xmin = min(stats["low"].min(), -4.6) - 0.2
xmax = max(stats["high"].max(), 0.3) + 1.7
ax.set_xlim(xmin, xmax)

for yi, row in zip(y, stats.itertuples(index=False)):
    label_x = max(row.high + 0.16, 0.18)
    ax.text(label_x, yi + 0.11, f"{row.mean:.2f} s", va="center", fontsize=9.5)
    ax.text(label_x, yi - 0.16, f"{row.n_improved}/{row.n_total} favored C", va="center", fontsize=8.5)

header_x = max(stats["high"].max() + 0.16, 0.18)
ax.text(header_x, y.max() + 0.72, "Mean ΔT", fontsize=9.3)
ax.text(header_x, y.max() + 0.46, "Direction count", fontsize=8.6)

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.grid(axis="x", linestyle="--", linewidth=0.5, alpha=0.35)

fig.text(
    0.13,
    0.02,
    "Objects are ordered from larger C–E improvement to smaller improvement. "
    "Negative values indicate faster completion under Mode C; bars show bootstrap 95% CI.",
    fontsize=9.2
)

plt.tight_layout(rect=[0, 0.06, 1, 1])
plt.savefig("Fig7_b_object_forest.png", dpi=300)
plt.close()
print("Fig7(b) saved: Fig7_b_object_forest.png")