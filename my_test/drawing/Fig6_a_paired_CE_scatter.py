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

fig, ax = plt.subplots(figsize=(6.8, 5.0))
ax.scatter(pivot["E"], pivot["C"], s=28)
mn = min(pivot["E"].min(), pivot["C"].min()) - 1
mx = max(pivot["E"].max(), pivot["C"].max()) + 1
ax.plot([mn, mx], [mn, mx], linestyle="--", linewidth=1.2)
ax.set_xlim(mn, mx)
ax.set_ylim(mn, mx)
ax.set_xlabel("Mode E completion time $T_E$ (s)", fontsize=11)
ax.set_ylabel("Mode C completion time $T_C$ (s)", fontsize=11)
ax.set_title("Fig. 6(a) Paired C–E completion-time scatter across 27 matched blocks", fontsize=13)
clean_axes(ax)
ax.text(0.97, 0.05, "Points below $y=x$\nindicate C is faster",
        transform=ax.transAxes, ha="right", va="bottom", fontsize=10,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.85))
plt.tight_layout()
plt.savefig("Fig6_a_paired_CE_scatter.png", dpi=300)
plt.close()
print("Fig6(a) saved: Fig6_a_paired_CE_scatter.png")