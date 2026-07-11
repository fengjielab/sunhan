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

operator_means = pivot.groupby("operator")[["C", "E"]].mean()
operator_sems = pivot.groupby("operator")[["C", "E"]].sem()
operator_reduction = (operator_means["E"] - operator_means["C"]) / operator_means["E"] * 100

fig, ax = plt.subplots(figsize=(6.8, 5.0))
ops = ["P01", "P02", "P03"]
x = np.arange(len(ops))
w = 0.34
c_means = operator_means.loc[ops, "C"].to_numpy()
e_means = operator_means.loc[ops, "E"].to_numpy()
c_sems = operator_sems.loc[ops, "C"].to_numpy()
e_sems = operator_sems.loc[ops, "E"].to_numpy()

ax.bar(x - w/2, c_means, width=w, yerr=c_sems, capsize=4, label="Mode C (full multi-channel)")
ax.bar(x + w/2, e_means, width=w, yerr=e_sems, capsize=4, label="Mode E (impedance-only)")
for i, op in enumerate(ops):
    ax.text(x[i] - w/2, c_means[i] + c_sems[i] + 0.35, f"{c_means[i]:.2f}", ha="center", fontsize=10)
    ax.text(x[i] + w/2, e_means[i] + e_sems[i] + 0.35, f"{e_means[i]:.2f}", ha="center", fontsize=10)
    ax.text(x[i], max(c_means[i], e_means[i]) * 0.55, f"-{operator_reduction.loc[op]:.1f}%", ha="center", fontsize=10,
            bbox=dict(boxstyle="round,pad=0.25", facecolor="white", alpha=0.85))
ax.set_xticks(x)
ax.set_xticklabels([f"{op}\n(n = 9 blocks)" for op in ops])
ax.set_ylabel("Completion time (s)", fontsize=11)
ax.set_title("Fig. 6(c) Operator-level aggregated comparison", fontsize=13)
ax.legend(frameon=False, fontsize=9)
clean_axes(ax)
ax.text(0.5, -0.18, "Error bars denote SEM across 9 matched blocks per operator.",
        transform=ax.transAxes, ha="center", va="top", fontsize=9)
plt.tight_layout()
plt.savefig("Fig6_c_operator_aggregated_comparison.png", dpi=300)
plt.close()
print("Fig6(c) saved: Fig6_c_operator_aggregated_comparison.png")