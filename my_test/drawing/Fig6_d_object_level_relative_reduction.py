import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

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
pivot["delta"] = pivot["C"] - pivot["E"]

obj_map = {'瓶子 (bottle)': 'Bottle', '香蕉 (banana)': 'Banana', '苹果 (apple)': 'Apple', '鼠标 (mouse)': 'Mouse', '纸杯 (paper cup)': 'Paper cup', '剪刀 (scissors)': 'Scissors'}
pivot["object_en"] = pivot["specific_object"].map(obj_map)

rng = np.random.default_rng(42)

def clean_axes(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(labelsize=10)
    ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.35)

object_summary = pivot.groupby("object_en")[["C", "E"]].mean()
object_summary["reduction_pct"] = (object_summary["E"] - object_summary["C"]) / object_summary["E"] * 100
object_summary = object_summary.reindex(["Bottle", "Banana", "Apple", "Mouse", "Paper cup", "Scissors"])

# Color gradient from lighter to deeper blue based on reduction
colors = plt.cm.Blues(np.linspace(0.4, 0.85, len(object_summary)))

fig, ax = plt.subplots(figsize=(7.2, 5.0))
y = np.arange(len(object_summary))
vals = object_summary["reduction_pct"].to_numpy()
bars = ax.barh(y, vals, color=colors, edgecolor="grey", linewidth=0.5)

# Add value labels with dynamic offset
max_val = vals.max()
for yi, v in enumerate(vals):
    offset = 0.5 if v < 5 else 0.4
    ax.text(v + offset, yi, f"{v:.1f}%", va="center", fontsize=10,
            fontweight="bold" if v >= 10 else "normal")

ax.set_yticks(y)
ax.set_yticklabels(object_summary.index)
ax.invert_yaxis()

# Add vertical reference line at 0% and dotted lines at key markers
ax.axvline(0, linestyle="-", linewidth=0.8, color="grey")
ax.set_xlim(-1, max_val + 6)  # leave room for labels

ax.set_xlabel("Relative reduction (%)  →  C is faster", fontsize=11)
ax.set_title("Fig. 6(d) Object-level relative reduction under C compared with E", fontsize=13)
clean_axes(ax)

# Add note in bottom right
ax.text(0.98, 0.06, "Positive → C has lower completion\ntime (faster) than E.",
        transform=ax.transAxes, ha="right", va="bottom", fontsize=10,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#f0f0f0", alpha=0.85))

plt.tight_layout()
plt.savefig("Fig6_d_object_level_relative_reduction.png", dpi=300)
plt.close()
print("Fig6(d) saved: Fig6_d_object_level_relative_reduction.png")