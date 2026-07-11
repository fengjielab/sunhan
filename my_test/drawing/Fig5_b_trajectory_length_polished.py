import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

trial_file = r"../data/all_trials_135.csv"

mode_order = ["A", "B", "C", "D", "E"]
mode_labels = ["A\nFixed", "B\nManual", "C\nVision\nmulti-param", "D\nVision\nobserve", "E\nVision\nimpedance-only"]

def add_panel_tag(ax, tag):
    ax.text(0.01, 0.98, tag, transform=ax.transAxes, ha="left", va="top", fontsize=13, fontweight="bold")

def format_axes(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(1.0)
    ax.spines["bottom"].set_linewidth(1.0)
    ax.tick_params(axis="both", labelsize=10, width=1.0)
    ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.35)

def draw_box_scatter(ax, data, column, ylabel, panel_tag, best_note=None, ylim=None):
    values = [data.loc[data["mode"] == m, column].dropna().values for m in mode_order]
    bp = ax.boxplot(
        values, patch_artist=True, widths=0.56, showfliers=False,
        medianprops=dict(color="black", linewidth=1.5),
        whiskerprops=dict(color="#4D4D4D", linewidth=1.1),
        capprops=dict(color="#4D4D4D", linewidth=1.1),
        boxprops=dict(linewidth=1.2),
    )
    for i, patch in enumerate(bp["boxes"]):
        if mode_order[i] == "C":
            patch.set_facecolor("#D9C7F0")
            patch.set_edgecolor("#6A3D9A")
        else:
            patch.set_facecolor("#DCEAF5")
            patch.set_edgecolor("#5B8DB8")
    rng = np.random.default_rng(7)
    for i, m in enumerate(mode_order, start=1):
        y = data.loc[data["mode"] == m, column].dropna().values
        x = rng.normal(i, 0.05, size=len(y))
        edge = "#6A3D9A" if m == "C" else "#5B8DB8"
        ax.scatter(x, y, s=20, facecolors="white", edgecolors=edge, linewidths=0.8, zorder=3)

    ax.set_xticks(range(1, 6))
    ax.set_xticklabels(mode_labels)
    ax.set_ylabel(ylabel, fontsize=11)
    if ylim is not None:
        ax.set_ylim(*ylim)
    format_axes(ax)
    add_panel_tag(ax, panel_tag)

    if best_note is not None:
        c_vals = data.loc[data["mode"] == "C", column]
        y_pos = np.max(c_vals) + (ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.06
        ax.text(3, y_pos, best_note, ha="center", va="bottom", fontsize=9.2, color="#6A3D9A", fontweight="bold")

    means = data.groupby("mode")[column].mean().reindex(mode_order)
    stds = data.groupby("mode")[column].std().reindex(mode_order)
    y0, y1 = ax.get_ylim()
    y_text = y0 + (y1 - y0) * 0.015
    for i, m in enumerate(mode_order, start=1):
        ax.text(i, y_text, f"{means[m]:.2f}±{stds[m]:.2f}", ha="center", va="bottom", fontsize=8.2)

    ax.text(
        0.5, -0.22,
        "Boxes: 25–75% IQR; center line: median; whiskers: 1.5×IQR; dots: individual matched blocks; bottom text: mean±SD",
        transform=ax.transAxes, ha="center", va="top", fontsize=8.2
    )

df = pd.read_csv(trial_file)
fig, ax = plt.subplots(figsize=(6.8, 4.8))
draw_box_scatter(ax, df, "traj_length_m", "Master trajectory length (m)", "(b)", None, (0.5, 1.1))
plt.tight_layout()
plt.savefig("Fig5_b_trajectory_length.png", dpi=300)
plt.close()
print("Fig5(b) saved: Fig5_b_trajectory_length.png")