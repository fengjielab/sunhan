import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

trial_file = r"../data/all_trials_135.csv"
df = pd.read_csv(trial_file)

pivot = (
    df.pivot_table(
        index=["operator", "group_num", "specific_object"],
        columns="mode",
        values="duration_s"
    )
    .reset_index()
)
pivot["delta"] = pivot["C"] - pivot["E"]  # negative means Mode C is faster

ops = ["P01", "P02", "P03"]
rng = np.random.default_rng(42)

rows = []
for op in ops:
    vals = pivot.loc[pivot["operator"] == op, "delta"].to_numpy()
    boot = rng.choice(vals, size=(20000, len(vals)), replace=True).mean(axis=1)
    low, high = np.quantile(boot, [0.025, 0.975])
    rows.append(
        {
            "operator": op,
            "mean": vals.mean(),
            "low": low,
            "high": high,
            "n_improved": int((vals < 0).sum()),
            "n_total": len(vals),
        }
    )

stats = pd.DataFrame(rows)

fig, ax = plt.subplots(figsize=(8.2, 4.8))

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
ax.set_yticklabels(stats["operator"], fontsize=11)
ax.set_xlabel(r"$\Delta T = T_C - T_E$ (s)", fontsize=12)
ax.set_ylabel("Operator", fontsize=12)
ax.set_title("Operator-level robustness of C–E improvement", fontsize=14, pad=12)

xmin = min(stats["low"].min(), -3.5) - 0.2
xmax = max(stats["high"].max(), 0.3) + 2.2
ax.set_xlim(xmin, xmax)
ax.set_ylim(-0.7, len(stats) - 0.3)

label_x = max(stats["high"].max() + 0.18, 0.20)
header_y = y.max() + 0.48
ax.text(label_x, header_y, "Mean ΔT", fontsize=9.5)
ax.text(label_x + 1.02, header_y, "Direction count", fontsize=9.0)

for yi, row in zip(y, stats.itertuples(index=False)):
    ax.text(label_x, yi, f"{row.mean:.2f} s", va="center", fontsize=9.6)
    ax.text(label_x + 1.02, yi, f"{row.n_improved}/{row.n_total} favored C", va="center", fontsize=8.8)

fig.text(
    0.12,
    0.03,
    "Negative values indicate faster completion under Mode C. "
    "Points show the mean paired difference and horizontal bars show bootstrap 95% CI.",
    fontsize=9.2
)

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.grid(axis="x", linestyle="--", linewidth=0.5, alpha=0.35)

plt.tight_layout(rect=[0, 0.07, 1, 1])
plt.savefig("Fig7_a_operator_forest.png", dpi=300)
plt.close()
print("Fig7(a) saved: Fig7_a_operator_forest.png")