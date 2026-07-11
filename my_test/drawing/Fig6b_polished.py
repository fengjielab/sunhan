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

delta = (pivot["C"] - pivot["E"]).to_numpy()

mean_delta = float(np.mean(delta))
median_delta = float(np.median(delta))
median_c = float(np.median(pivot["C"]))
median_e = float(np.median(pivot["E"]))
relative_reduction = float((pivot["E"].mean() - pivot["C"].mean()) / pivot["E"].mean() * 100)

rng = np.random.default_rng(42)
boot = rng.choice(delta, size=(30000, len(delta)), replace=True).mean(axis=1)
ci_low, ci_high = np.quantile(boot, [0.025, 0.975])

fig, ax = plt.subplots(figsize=(7.2, 5.0))  # slightly wider to prevent text cutoff

ax.violinplot(
    [delta],
    positions=[1.0],
    widths=0.48,
    showmeans=False,
    showmedians=False,
    showextrema=False
)

x = rng.normal(1.0, 0.035, len(delta))
ax.scatter(x, delta, s=28, zorder=3)

ax.axhline(0, linestyle="--", linewidth=1.0, color="grey")
ax.hlines(median_delta, 0.84, 1.16, linewidth=1.8, color="C0")
ax.hlines(mean_delta, 0.84, 1.16, linewidth=1.8, linestyle=":", color="C3")

x_ci = 1.23
ax.vlines(x_ci, ci_low, ci_high, linewidth=2.2, color="C3")
ax.scatter([x_ci], [mean_delta], s=32, zorder=4, color="C3")

# ★ left-aligned stats text below the violin area
stats_text = (
    f"Mean ΔT = {mean_delta:.2f} s\n"
    f"95% CI [{ci_low:.2f}, {ci_high:.2f}] s\n"
    f"Relative reduction ≈ {relative_reduction:.1f}%"
)
ax.text(
    0.03, 0.50, stats_text,
    transform=ax.transAxes,
    ha="left", va="top", fontsize=9.5,
    bbox=dict(boxstyle="round,pad=0.4", facecolor="#f0f0f0", alpha=0.9)
)

# ★ median info at bottom-left
median_note = (
    f"Median ΔT = {median_delta:.2f} s\n"
    f"Median T_C = {median_c:.2f} s\n"
    f"Median T_E = {median_e:.2f} s"
)
ax.text(
    0.03, 0.03, median_note,
    transform=ax.transAxes,
    ha="left", va="bottom", fontsize=8.8,
    bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.85)
)

ymin = min(delta.min(), ci_low) - 0.8
ymax = max(delta.max(), ci_high) + 0.8
ax.set_ylim(ymin, ymax)
ax.set_xlim(0.72, 2.00)  # more space on right
ax.set_xticks([1.0])
ax.set_xticklabels(["27 matched blocks"], fontsize=11)
ax.set_ylabel(r"$\Delta T = T_C - T_E$ (s)", fontsize=12)
ax.set_title("Paired completion-time improvement (C–E)", fontsize=13)

ax.text(
    0.03, 0.94,
    "Negative ΔT indicates faster completion under Mode C.",
    transform=ax.transAxes, fontsize=9.2
)

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.35)

plt.tight_layout()
plt.savefig("Fig6_b_paired_delta_violin.png", dpi=300)
plt.close()
print("Fig6(b) saved: Fig6_b_paired_delta_violin.png")