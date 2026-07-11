import numpy as np
import matplotlib.pyplot as plt

mode_order = ["A", "B", "C", "D", "E"]
mode_labels = ["A\nFixed", "B\nManual", "C\nVision\nmulti-param", "D\nVision\nobserve", "E\nVision\nimpedance-only"]
# Data source: ../data/实验评分表.md - 汇总统计 (rows 195-199)
success_counts = {'A': 22, 'B': 21, 'C': 26, 'D': 24, 'E': 24}
success_rates = {k: v/27*100 for k, v in success_counts.items()}

def add_panel_tag(ax, tag):
    ax.text(0.01, 0.98, tag, transform=ax.transAxes, ha="left", va="top", fontsize=13, fontweight="bold")

def format_axes(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(1.0)
    ax.spines["bottom"].set_linewidth(1.0)
    ax.tick_params(axis="both", labelsize=10, width=1.0)
    ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.35)

fig, ax = plt.subplots(figsize=(6.8, 4.8))
x = np.arange(1, 6)
rates = [success_rates[m] for m in mode_order]
for xi, m, rate in zip(x, mode_order, rates):
    line_color = "#6A3D9A" if m == "C" else "#5B8DB8"
    fill_color = "#D9C7F0" if m == "C" else "#DCEAF5"
    ax.vlines(xi, 0, rate, color=line_color, linewidth=2.0)
    ax.scatter([xi], [rate], s=160, facecolors=fill_color, edgecolors=line_color, linewidths=1.2, zorder=3)
    ax.text(xi, rate + 2.6, f"{success_counts[m]}/27\n({rate:.1f}%)", ha="center", va="bottom", fontsize=8.8)

ax.set_xticks(x)
ax.set_xticklabels(mode_labels)
ax.set_ylabel("Success rate (%)", fontsize=11)
ax.set_ylim(0, 108)
format_axes(ax)
add_panel_tag(ax, "(d)")
ax.text(3, rates[2] + 11, "Highest success rate", ha="center", va="bottom",
        fontsize=9.2, color="#6A3D9A", fontweight="bold")
ax.text(0.5, -0.18, "Dots indicate success-rate summary for each mode (successful trials / 27).",
        transform=ax.transAxes, ha="center", va="top", fontsize=8.2)
plt.tight_layout()
plt.savefig("Fig5_d_success_rate.png", dpi=300)
plt.close()
print("Fig5(d) saved: Fig5_d_success_rate.png")