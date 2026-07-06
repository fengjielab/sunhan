#!/usr/bin/env python3
"""
generate_mechatronics_figures.py — 为 Mechatronics 版论文生成升级图表
- fig5: 五模式 boxplot + scatter（完成时间 / 轨迹 / TLX 三分面）
- fig6: C–E 27配对散点 + 操作者分面 + 对象分层
- fig7: 系统时序图
"""
import csv
from pathlib import Path
from collections import defaultdict
from statistics import mean, median

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

DATA_DIR = Path(__file__).resolve().parent
FIG_DIR = DATA_DIR / "fig"
FIG_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family": "serif", "font.size": 9,
    "axes.labelsize": 10, "axes.titlesize": 11,
    "legend.fontsize": 8, "figure.dpi": 150, "savefig.dpi": 300,
    "savefig.bbox": "tight",
})

MODE_ORDER = ["A", "B", "C", "D", "E"]
MODE_SHORT = {"A": "Fixed\n(A)", "B": "Manual\n(B)", "C": "Multi-param\n(C)",
              "D": "Observe\n(D)", "E": "Impedance\n(E)"}
MODE_COLORS = {"A": "#bdbdbd", "B": "#fdb462", "C": "#80b1d3", "D": "#b3de69", "E": "#fb8072"}
ATTR_LABELS = {"soft": "Fragility", "medium": "Balanced", "hard": "Stability"}
ATTR_COLORS = {"soft": "#66c2a5", "medium": "#fc8d62", "hard": "#8da0cb"}
OP_COLORS = {"P01": "#1b9e77", "P02": "#d95f02", "P03": "#7570b3"}


def read_trials():
    rows = []
    with open(DATA_DIR / "all_trials_135.csv", "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            row["duration_s"] = float(row["duration_s"])
            row["traj_length_m"] = float(row["traj_length_m"])
            rows.append(row)
    return rows


def read_nasa():
    rows = []
    with open(DATA_DIR / "nasa_tlx_results" / "nasa.md", "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            dims = ["mental_demand","physical_demand","temporal_demand",
                    "performance","effort","frustration"]
            row["raw_tlx"] = mean(float(row[d]) for d in dims)
            rows.append(row)
    return rows


# ═══════════════════════════════════════════
# 图5: 五模式 boxplot + scatter 三分面
# ═══════════════════════════════════════════
def fig5(trials, nasa_rows):
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    rng = np.random.default_rng(42)

    # ── (a) Completion time ──
    ax = axes[0]
    data = [[r["duration_s"] for r in trials if r["mode"] == m] for m in MODE_ORDER]
    bp = ax.boxplot(data, positions=range(5), widths=0.55, patch_artist=True,
                    showfliers=False, medianprops={"color":"black","linewidth":1.5})
    for i, m in enumerate(MODE_ORDER):
        bp["boxes"][i].set_facecolor(MODE_COLORS[m]); bp["boxes"][i].set_alpha(0.7)
        ys = data[i]
        ax.scatter(np.full(len(ys), i) + rng.uniform(-0.18, 0.18, len(ys)), ys,
                   s=15, c=MODE_COLORS[m], edgecolors="white", linewidth=0.3, alpha=0.7, zorder=3)
    ax.set_xticks(range(5)); ax.set_xticklabels([MODE_SHORT[m] for m in MODE_ORDER], fontsize=7)
    ax.set_ylabel("Completion time (s)"); ax.set_title("(a) Completion time")
    # significance bracket
    ax.plot([1.8, 1.8, 2.2, 2.2], [19.2, 18.8, 18.8, 19.2], "k-", linewidth=0.8)
    ax.text(2, 19.3, "***", ha="center", fontsize=14, fontweight="bold")

    # ── (b) Trajectory length ──
    ax = axes[1]
    data = [[r["traj_length_m"] for r in trials if r["mode"] == m] for m in MODE_ORDER]
    bp = ax.boxplot(data, positions=range(5), widths=0.55, patch_artist=True,
                    showfliers=False, medianprops={"color":"black","linewidth":1.5})
    for i, m in enumerate(MODE_ORDER):
        bp["boxes"][i].set_facecolor(MODE_COLORS[m]); bp["boxes"][i].set_alpha(0.7)
        ys = data[i]
        ax.scatter(np.full(len(ys), i) + rng.uniform(-0.18, 0.18, len(ys)), ys,
                   s=15, c=MODE_COLORS[m], edgecolors="white", linewidth=0.3, alpha=0.7, zorder=3)
    ax.set_xticks(range(5)); ax.set_xticklabels([MODE_SHORT[m] for m in MODE_ORDER], fontsize=7)
    ax.set_ylabel("Trajectory length (m)"); ax.set_title("(b) Master trajectory")

    # ── (c) Raw NASA-TLX ──
    ax = axes[2]
    tlx_map = defaultdict(list)
    for r in nasa_rows:
        tlx_map[r["mode"]].append(r["raw_tlx"])
    data = [tlx_map[m] for m in MODE_ORDER]
    bp = ax.boxplot(data, positions=range(5), widths=0.55, patch_artist=True,
                    showfliers=False, medianprops={"color":"black","linewidth":1.5})
    for i, m in enumerate(MODE_ORDER):
        bp["boxes"][i].set_facecolor(MODE_COLORS[m]); bp["boxes"][i].set_alpha(0.7)
        ys = data[i]
        ax.scatter(np.full(len(ys), i) + rng.uniform(-0.18, 0.18, len(ys)), ys,
                   s=15, c=MODE_COLORS[m], edgecolors="white", linewidth=0.3, alpha=0.7, zorder=3)
    ax.set_xticks(range(5)); ax.set_xticklabels([MODE_SHORT[m] for m in MODE_ORDER], fontsize=7)
    ax.set_ylabel("Raw NASA-TLX"); ax.set_title("(c) Raw NASA-TLX")

    fig.suptitle("Fig. 5. Five-mode performance comparison (boxplot + individual block data points)",
                 y=1.02, fontsize=12, fontweight="bold")
    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig5_five_mode_boxplot.svg")
    fig.savefig(FIG_DIR / "fig5_five_mode_boxplot.png")
    plt.close(fig)
    print("✅ fig5 saved")


# ═══════════════════════════════════════════
# 图6: C–E 27配对散点 + 操作者分面 + 对象分层
# ═══════════════════════════════════════════
def fig6(trials):
    # Build C-E pairs
    blocks = defaultdict(dict)
    for r in trials:
        if r["mode"] in ("C", "E"):
            key = f"{r['operator']}_{r['object_attr']}_{r['group_num']}"
            blocks[key][r["mode"]] = (r["duration_s"], r["operator"], r["object_attr"], r["specific_object"])

    pairs = []
    for k, v in blocks.items():
        if "C" in v and "E" in v:
            pairs.append((v["C"], v["E"]))

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))

    # ── (a) 27-pair scatter ──
    ax = axes[0]
    c_vals = [p[0][0] for p in pairs]
    e_vals = [p[1][0] for p in pairs]
    attrs = [p[0][2] for p in pairs]
    max_val = max(max(c_vals), max(e_vals)) + 1
    min_val = min(min(c_vals), min(e_vals)) - 0.5

    for i, (c, e) in enumerate(zip(c_vals, e_vals)):
        ax.plot([c, e], [i, i], color="gray", alpha=0.3, linewidth=0.6, zorder=1)
    for (c, _, attr, _), (e, _, _, _) in pairs:
        ax.scatter(c, c_vals.index(c) if False else None, s=0)  # dummy

    # Re-do with proper indexing
    for i, (c_data, e_data) in enumerate(pairs):
        c = c_data[0]; e = e_data[0]; attr = c_data[2]
        ax.scatter(c, i, s=40, c=ATTR_COLORS[attr], edgecolors="white", linewidth=0.5, zorder=3, marker="o")
        ax.scatter(e, i, s=40, c=ATTR_COLORS[attr], edgecolors="black", linewidth=0.5, zorder=2, marker="s")

    ax.axvline(x=median(c_vals), color="#80b1d3", linestyle="--", alpha=0.6, linewidth=1)
    ax.axvline(x=median(e_vals), color="#fb8072", linestyle="--", alpha=0.6, linewidth=1)
    ax.set_xlabel("Completion time (s)"); ax.set_ylabel("Block index")
    ax.set_title("(a) C–E paired blocks (n=27)\n● C mode  ■ E mode")
    ax.set_xlim(min_val, max_val)

    legend_elements = [mpatches.Patch(facecolor=ATTR_COLORS[a], label=ATTR_LABELS[a]) for a in ["soft","medium","hard"]]
    ax.legend(handles=legend_elements, fontsize=7, loc="lower right")

    # ── (b) Operator subpanels ──
    ax = axes[1]
    op_data = defaultdict(lambda: {"C": [], "E": []})
    for p in pairs:
        op = p[0][1]
        op_data[op]["C"].append(p[0][0])
        op_data[op]["E"].append(p[1][0])

    x_pos = []
    for idx, op in enumerate(["P01", "P02", "P03"]):
        x_c = idx * 2.5; x_e = idx * 2.5 + 0.7
        x_pos.extend([x_c, x_e])
        c_vals_op = op_data[op]["C"]; e_vals_op = op_data[op]["E"]
        # boxplot mini
        bp_c = ax.boxplot([c_vals_op], positions=[x_c], widths=0.45, patch_artist=True,
                          showfliers=False, medianprops={"color":"black","linewidth":1})
        bp_e = ax.boxplot([e_vals_op], positions=[x_e], widths=0.45, patch_artist=True,
                          showfliers=False, medianprops={"color":"black","linewidth":1})
        bp_c["boxes"][0].set_facecolor("#80b1d3"); bp_c["boxes"][0].set_alpha(0.7)
        bp_e["boxes"][0].set_facecolor("#fb8072"); bp_e["boxes"][0].set_alpha(0.7)
        # scatter
        rng = np.random.default_rng(idx)
        ax.scatter(np.full(len(c_vals_op), x_c)+rng.uniform(-0.1,0.1,len(c_vals_op)), c_vals_op,
                   s=12, c="#80b1d3", edgecolors="white", linewidth=0.2, alpha=0.7, zorder=3)
        ax.scatter(np.full(len(e_vals_op), x_e)+rng.uniform(-0.1,0.1,len(e_vals_op)), e_vals_op,
                   s=12, c="#fb8072", edgecolors="white", linewidth=0.2, alpha=0.7, zorder=3)
        # connect means
        ax.plot([x_c, x_e], [mean(c_vals_op), mean(e_vals_op)], "k-", linewidth=1.2, alpha=0.5)

    ax.set_xticks([i*2.5+0.35 for i in range(3)])
    ax.set_xticklabels([f"P0{i+1}\n(C vs E)" for i in range(3)], fontsize=8)
    ax.set_ylabel("Completion time (s)")
    ax.set_title("(b) Operator-level C vs E")
    ax.legend(handles=[mpatches.Patch(facecolor="#80b1d3", label="C (multi-param)"),
                        mpatches.Patch(facecolor="#fb8072", label="E (impedance-only)")], fontsize=7)

    fig.suptitle("Fig. 6. Core C–E ablation: paired block comparison", y=1.02, fontsize=12, fontweight="bold")
    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig6_ce_paired.svg")
    fig.savefig(FIG_DIR / "fig6_ce_paired.png")
    plt.close(fig)
    print("✅ fig6 saved")


# ═══════════════════════════════════════════
# 图7: 系统时序图
# ═══════════════════════════════════════════
def fig7():
    fig, ax = plt.subplots(figsize=(14, 5))

    modules = [
        "RGB-D Camera",
        "Vision sub-process\n(YOLO11n, ~20 Hz)",
        "Strategy Scheduler\n(event-based)",
        "Master Input\n(Omega.7, 200 Hz)",
        "Slave Control\n(Panda, 200 Hz)",
        "Haptic Rendering\n(200 Hz)",
        "Gripper\n(event-based)",
    ]

    colors = ["#8dd3c7", "#ffffb3", "#bebada", "#fb8072", "#80b1d3", "#fdb462", "#b3de69"]

    # Timeline phases (ms)
    t_start = 0
    t_camera1 = 100; t_camera2 = 145
    t_detect1 = 105; t_detect2 = 155
    t_lock = 150
    t_scheduler = 155; t_scheduler_end = 160
    t_ctrl_start = 0; t_ctrl_end = 500
    t_haptic_start = 160; t_haptic_end = 500
    t_grip1 = 300; t_grip2 = 320

    y_positions = list(range(len(modules)))

    # Horizontal bars
    ax.barh(0, t_camera2-t_camera1, left=t_camera1, height=0.5, color=colors[0], alpha=0.6)  # camera frame
    ax.barh(0, t_camera2+50-t_camera2, left=t_camera2, height=0.5, color=colors[0], alpha=0.3)
    ax.text(t_camera1, 0.3, "frame capture", fontsize=6, va="bottom")

    ax.barh(1, t_detect2-t_detect1, left=t_detect1, height=0.5, color=colors[1], alpha=0.8)
    ax.text(t_detect1, 1.3, "YOLO infer\n~50 ms", fontsize=6, va="bottom")

    # Lock marker
    ax.axvline(x=t_lock, color="red", linestyle="--", alpha=0.5, linewidth=1)
    ax.text(t_lock, 3.7, "vision\nlocked", fontsize=7, color="red", ha="center", fontweight="bold")

    ax.barh(2, t_scheduler_end-t_scheduler, left=t_scheduler, height=0.5, color=colors[2], alpha=0.9)
    ax.text(t_scheduler, 2.3, "schedule Θ(c)", fontsize=6, va="bottom")

    # Control loop
    for i in range(10):
        ax.barh(4, 4, left=i*50, height=0.5, color=colors[4], alpha=0.4)
    ax.text(0, 4.3, "200 Hz control loop (5 ms cycles)", fontsize=7, va="bottom")

    # Haptic
    ax.barh(5, t_haptic_end-t_haptic_start, left=t_haptic_start, height=0.5, color=colors[5], alpha=0.6)
    ax.text(t_haptic_start, 5.3, "haptic rendering with Θ(c) params", fontsize=6, va="bottom")

    # Gripper
    ax.barh(6, t_grip2-t_grip1, left=t_grip1, height=0.5, color=colors[6], alpha=0.8)
    ax.text(t_grip1, 6.3, "grasp", fontsize=6, va="bottom")

    ax.barh(3, t_ctrl_end, left=0, height=0.5, color=colors[3], alpha=0.3)
    ax.text(0, 3.3, "master input (200 Hz, continuous)", fontsize=6, va="bottom")

    # Phase labels at top
    phases = [
        ("Pre-contact\n(visual init)", 0, 160),
        ("Contact &\nGrasp", 160, 350),
        ("Transport &\nRelease", 350, 500),
    ]
    for label, s, e in phases:
        ax.axvspan(s, e, alpha=0.05, color="gray")
        ax.text((s+e)/2, len(modules)-0.7, label, ha="center", fontsize=7, fontstyle="italic")

    ax.set_yticks(y_positions)
    ax.set_yticklabels(modules, fontsize=7)
    ax.set_xlabel("Time (ms)")
    ax.set_title("Fig. 7. Mechatronic system timeline: perception–control–execution coordination",
                 fontsize=12, fontweight="bold")
    ax.set_xlim(0, 520)
    ax.invert_yaxis()

    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig7_system_timeline.svg")
    fig.savefig(FIG_DIR / "fig7_system_timeline.png")
    plt.close(fig)
    print("✅ fig7 saved")


# ═══════════════════════════════════════════
if __name__ == "__main__":
    trials = read_trials()
    nasa_rows = read_nasa()
    print(f"Read {len(trials)} trials, {len(nasa_rows)} TLX rows")
    fig5(trials, nasa_rows)
    fig6(trials)
    fig7()
    print("\n🎉 All figures generated in", FIG_DIR)