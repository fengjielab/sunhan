#!/usr/bin/env python3
"""
generate_figures.py — 为论文生成关键结果图
图5: 五模式完成时间/轨迹/成功率/Raw TLX对比（配对散点图）
图6: C-E分属性消融（配对散点图）
图4: 视觉识别结果
NASA-TLX雷达图（含E模式）
跨操作者完成时间对比
"""

import csv
from pathlib import Path
from collections import defaultdict
from statistics import mean, stdev

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
from scipy.stats import wilcoxon

# ═══ 全局字体设置 ═══
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

plt.rcParams.update({
    'font.size': 11,
    'axes.titlesize': 13,
    'axes.labelsize': 11,
    'legend.fontsize': 9,
    'figure.dpi': 150,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
})

DATA_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = DATA_DIR / "fig"

MODES = ["A", "B", "C", "D", "E"]
MODE_LABELS = ["A 固定参数", "B 人工选择", "C 视觉多参数", "D 视觉仅观察", "E 视觉仅阻抗"]
COLORS = ["#E74C3C", "#F39C12", "#27AE60", "#3498DB", "#9B59B6"]
MODE_LABELS_SHORT = ["A 固定", "B 选择", "C 视觉", "D 观察", "E 阻抗"]
ATTR_LABELS = {"soft": "轻拿轻放", "medium": "中等", "hard": "硬质"}
SUCCESS_COUNTS = {"A": 22, "B": 21, "C": 26, "D": 24, "E": 24}

# ─── 数据读取 ───
def read_trials():
    rows = []
    with open(DATA_DIR / "all_trials_135.csv", "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            row["duration_s"] = float(row["duration_s"])
            row["traj_length_m"] = float(row["traj_length_m"])
            row["block"] = f"{row['operator']}_{row['object_attr']}_{row['group_num']}"
            rows.append(row)
    return rows

def read_nasa_tlx():
    rows = []
    with open(DATA_DIR / "nasa_tlx_results" / "nasa.md", "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            dims = ["mental_demand","physical_demand","temporal_demand",
                    "performance","effort","frustration"]
            row["raw_tlx"] = mean(float(row[d]) for d in dims)
            rows.append(row)
    return rows


# ═══ 图5: 五模式对比 ═══
def fig5_five_mode_comparison(trials):
    durs = defaultdict(list)
    trajs = defaultdict(list)
    for r in trials:
        durs[r["mode"]].append(r["duration_s"])
        trajs[r["mode"]].append(r["traj_length_m"])

    tlx_rows = read_nasa_tlx()
    tlx_by_mode = defaultdict(list)
    for r in tlx_rows:
        tlx_by_mode[r["mode"]].append(r["raw_tlx"])

    fig, axes = plt.subplots(2, 2, figsize=(13, 10))
    
    # (a) 完成时间 - 配对散点图
    ax = axes[0, 0]
    blocks = defaultdict(dict)
    for r in trials:
        blocks[r["block"]][r["mode"]] = r["duration_s"]
    for b in blocks.values():
        if all(m in b for m in MODES):
            ax.plot(range(len(MODES)), [b[m] for m in MODES], 
                    color="gray", alpha=0.15, linewidth=0.5)
    for i, m in enumerate(MODES):
        vals = durs[m]
        mu, sd = mean(vals), stdev(vals)
        np.random.seed(42 + i)
        jitter = np.random.uniform(-0.1, 0.1, len(vals))
        ax.scatter([i + j for j in jitter], vals, color=COLORS[i], 
                   alpha=0.3, s=22, edgecolors='white', linewidth=0.3, zorder=3)
        ax.errorbar(i, mu, yerr=sd, color=COLORS[i], capsize=6, capthick=2,
                    marker='s', markersize=10, markerfacecolor=COLORS[i],
                    markeredgecolor='white', markeredgewidth=1.5, zorder=5)
    ax.set_xticks(range(len(MODES)))
    ax.set_xticklabels(MODE_LABELS, rotation=12, fontsize=9)
    ax.set_ylabel("完成时间 (s)", fontsize=11)
    ax.set_title("(a) 完成时间", fontsize=12, fontweight="bold")
    ax.grid(axis='y', alpha=0.3)
    ax.set_ylim(15, 28)

    # (b) 主端轨迹
    ax = axes[0, 1]
    for i, m in enumerate(MODES):
        vals = trajs[m]
        mu, sd = mean(vals), stdev(vals)
        ax.bar(i, mu, width=0.6, color=COLORS[i], alpha=0.8, yerr=sd, capsize=4)
        ax.scatter([i]*len(vals), vals, color=COLORS[i], alpha=0.2, s=15, zorder=3)
    ax.set_xticks(range(len(MODES)))
    ax.set_xticklabels(MODE_LABELS, rotation=12, fontsize=9)
    ax.set_ylabel("主端轨迹长度 (m)", fontsize=11)
    ax.set_title("(b) 主端轨迹长度", fontsize=12, fontweight="bold")
    ax.grid(axis='y', alpha=0.3)

    # (c) 成功率
    ax = axes[1, 0]
    success_rates = [SUCCESS_COUNTS[m]/27*100 for m in MODES]
    bars = ax.bar(range(len(MODES)), success_rates, width=0.6, color=COLORS, alpha=0.85)
    for bar, m in zip(bars, MODES):
        h = bar.get_height()
        ax.text(bar.get_x()+bar.get_width()/2, h+1, f'{h:.1f}%', 
                ha='center', va='bottom', fontsize=9, fontweight='bold')
        ax.text(bar.get_x()+bar.get_width()/2, h-5, f'{SUCCESS_COUNTS[m]}/27', 
                ha='center', va='top', fontsize=8, color='white', fontweight='bold')
    ax.set_xticks(range(len(MODES)))
    ax.set_xticklabels(MODE_LABELS, rotation=12, fontsize=9)
    ax.set_ylabel("成功率 (%)", fontsize=11)
    ax.set_title("(c) 成功率", fontsize=12, fontweight="bold")
    ax.set_ylim(0, 110)
    ax.grid(axis='y', alpha=0.3)

    # (d) Raw NASA-TLX
    ax = axes[1, 1]
    for i, m in enumerate(MODES):
        vals = tlx_by_mode.get(m, [0])
        if vals:
            mu, sd = mean(vals), stdev(vals)
            ax.bar(i, mu, width=0.6, color=COLORS[i], alpha=0.8, yerr=sd, capsize=4)
            ax.text(i, mu+1, f'{mu:.1f}', ha='center', va='bottom', fontsize=9, fontweight='bold')
    ax.set_xticks(range(len(MODES)))
    ax.set_xticklabels(MODE_LABELS, rotation=12, fontsize=9)
    ax.set_ylabel("Raw NASA-TLX", fontsize=11)
    ax.set_title("(d) Raw NASA-TLX", fontsize=12, fontweight="bold")
    ax.grid(axis='y', alpha=0.3)
    ax.set_ylim(0, 75)

    plt.suptitle("图5: 五模式实验结果对比", fontsize=14, fontweight="bold", y=1.01)
    plt.tight_layout()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUTPUT_DIR / "fig5_five_mode_comparison.png", dpi=300)
    plt.savefig(OUTPUT_DIR / "fig5_five_mode_comparison.svg")
    plt.close()
    print("✅ 图5: 五模式对比图")


# ═══ 图6: C-E分属性消融 ═══
def fig6_ce_ablation(trials):
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    
    for idx, attr in enumerate(["soft", "medium", "hard"]):
        ax = axes[idx]
        block_data = defaultdict(dict)
        for r in trials:
            if r["object_attr"] == attr:
                block_data[r["block"]][r["mode"]] = r["duration_s"]
        
        c_vals = []
        e_vals = []
        for b in block_data.values():
            if "C" in b and "E" in b:
                c_vals.append(b["C"])
                e_vals.append(b["E"])
                ax.plot([0, 1], [b["C"], b["E"]], color="gray", alpha=0.3, linewidth=0.8)
        
        if c_vals:
            np.random.seed(42)
            jc = np.random.normal(0, 0.03, len(c_vals))
            je = np.random.normal(0, 0.03, len(e_vals))
            ax.scatter([0+j for j in jc], c_vals, color="#27AE60", alpha=0.4, s=30, zorder=3)
            ax.scatter([1+j for j in je], e_vals, color="#9B59B6", alpha=0.4, s=30, zorder=3)
            ax.errorbar(0, mean(c_vals), yerr=stdev(c_vals), color="#27AE60", 
                        capsize=6, capthick=2, marker='s', markersize=10, zorder=5)
            ax.errorbar(1, mean(e_vals), yerr=stdev(e_vals), color="#9B59B6", 
                        capsize=6, capthick=2, marker='s', markersize=10, zorder=5)
            
            if len(c_vals) >= 3:
                try:
                    _, p_val = wilcoxon(c_vals, e_vals, alternative="two-sided")
                    ax.text(0.5, ax.get_ylim()[1]*0.93, f'p = {p_val:.4f}', 
                            ha='center', fontsize=10, style='italic',
                            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
                except:
                    pass
        
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["C 视觉多参数", "E 视觉仅阻抗"], fontsize=9)
        ax.set_ylabel("完成时间 (s)", fontsize=11)
        ax.set_title(f"{ATTR_LABELS[attr]}对象", fontsize=12, fontweight="bold")
        ax.grid(axis='y', alpha=0.3)
    
    plt.suptitle("图6: C-E分属性完成时间消融", fontsize=14, fontweight="bold", y=1.02)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "fig6_ce_ablation.png", dpi=300)
    plt.savefig(OUTPUT_DIR / "fig6_ce_ablation.svg")
    plt.close()
    print("✅ 图6: C-E消融图")


# ═══ 图4: 视觉识别验证 ═══
def fig4_vision_validation():
    objects = ["苹果", "香蕉", "水瓶", "杯", "鼠标", "剪刀"]
    confidence = [0.771, 0.948, 0.726, 0.820, 0.914, 0.938]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # 准确率（全100%）
    bars = ax1.barh(range(len(objects)), [100]*6, color="#27AE60", height=0.6)
    for i, bar in enumerate(bars):
        ax1.text(50, bar.get_y()+bar.get_height()/2, '100%', 
                 ha='center', va='center', fontsize=13, fontweight='bold', color='white')
    ax1.set_yticks(range(len(objects)))
    ax1.set_yticklabels(objects, fontsize=11)
    ax1.set_xlim(0, 110)
    ax1.set_xlabel("准确率 (%)", fontsize=11)
    ax1.set_title("(a) 类别识别与属性触发准确率", fontsize=12, fontweight="bold")
    ax1.grid(axis='x', alpha=0.3)
    
    # 置信度
    colors_conf = ["#3498DB", "#2980B9", "#2E86C1", "#5DADE2", "#85C1E9", "#AED6F1"]
    bars = ax2.barh(range(len(objects)), [c*100 for c in confidence], 
                    color=colors_conf, height=0.6)
    for bar, c in zip(bars, confidence):
        ax2.text(bar.get_width()+1, bar.get_y()+bar.get_height()/2,
                f'{c:.3f}', ha='left', va='center', fontsize=10, fontweight='bold')
    ax2.set_yticks(range(len(objects)))
    ax2.set_yticklabels(objects, fontsize=11)
    ax2.set_xlim(0, 110)
    ax2.set_xlabel("平均置信度", fontsize=11)
    ax2.set_title("(b) 检测置信度", fontsize=12, fontweight="bold")
    ax2.grid(axis='x', alpha=0.3)
    
    plt.suptitle("图4: 视觉识别验证结果", fontsize=14, fontweight="bold", y=1.02)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "fig4_vision_validation.png", dpi=300)
    plt.savefig(OUTPUT_DIR / "fig4_vision_validation.svg")
    plt.close()
    print("✅ 图4: 视觉识别验证图")


# ═══ NASA-TLX雷达图 ═══
def fig_tlx_radar():
    tlx_rows = read_nasa_tlx()
    dims = ["mental_demand", "physical_demand", "temporal_demand",
            "performance", "effort", "frustration"]
    dim_labels = ["心理需求", "体力需求", "时间需求", "绩效", "努力程度", "挫折程度"]
    mode_labels_map = {"A":"A 固定参数", "B":"B 人工选择", "C":"C 视觉多参数",
                       "D":"D 视觉仅观察", "E":"E 视觉仅阻抗"}
    
    values_by_mode = {}
    for m in MODES:
        vals = {dim: [] for dim in dims}
        for r in tlx_rows:
            if r["mode"] == m:
                for dim in dims:
                    vals[dim].append(float(r[dim]))
        values_by_mode[m] = [mean(vals[dim]) for dim in dims]
    
    angles = np.linspace(0, 2*np.pi, len(dims), endpoint=False).tolist()
    closed_angles = angles + angles[:1]
    
    fig, ax = plt.subplots(figsize=(8, 7.5), subplot_kw={"polar": True})
    
    for i, m in enumerate(MODES):
        values = values_by_mode[m]
        closed_values = values + values[:1]
        ax.plot(closed_angles, closed_values, color=COLORS[i], linewidth=2,
                label=mode_labels_map[m], marker='o', markersize=5)
        ax.fill(closed_angles, closed_values, alpha=0.05, color=COLORS[i])
    
    ax.set_xticks(angles)
    ax.set_xticklabels(dim_labels, fontsize=10)
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=8, color="gray")
    ax.set_title("Raw NASA-TLX六维评分（五模式对比）", fontsize=13, fontweight="bold", pad=25)
    ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.12), fontsize=9)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "fig_tlx_radar.png", dpi=300)
    plt.savefig(OUTPUT_DIR / "fig_tlx_radar.svg")
    plt.close()
    print("✅ TLX雷达图")


# ═══ 跨操作者完成时间 ═══
def fig_operator_comparison(trials):
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    for idx, op in enumerate(["P01", "P02", "P03"]):
        ax = axes[idx]
        op_data = [r for r in trials if r["operator"] == op]
        op_vals = {m: [] for m in MODES}
        for r in op_data:
            op_vals[r["mode"]].append(r["duration_s"])
        
        means = [mean(op_vals[m]) for m in MODES]
        sds = [stdev(op_vals[m]) if len(op_vals[m])>1 else 0 for m in MODES]
        
        bars = ax.bar(range(len(MODES)), means, width=0.6, color=COLORS, alpha=0.85, 
                      yerr=sds, capsize=4)
        for bar, mu in zip(bars, means):
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.3,
                    f'{mu:.2f}', ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        ax.set_xticks(range(len(MODES)))
        ax.set_xticklabels(MODE_LABELS_SHORT, fontsize=8)
        ax.set_ylabel("完成时间 (s)", fontsize=10)
        ax.set_title(f"操作者 {op}", fontsize=12, fontweight="bold")
        ax.set_ylim(15, 26)
        ax.grid(axis='y', alpha=0.3)
    
    plt.suptitle("跨操作者五模式完成时间对比", fontsize=14, fontweight="bold", y=1.02)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "fig_operator_comparison.png", dpi=300)
    plt.savefig(OUTPUT_DIR / "fig_operator_comparison.svg")
    plt.close()
    print("✅ 操作者对比图")


# ═══ 主函数 ═══
def main():
    print("=" * 60)
    print("  论文结果图生成（中文修复版）")
    print("=" * 60)
    
    trials = read_trials()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    fig4_vision_validation()
    fig5_five_mode_comparison(trials)
    fig6_ce_ablation(trials)
    fig_tlx_radar()
    fig_operator_comparison(trials)
    
    print(f"\n✅ 所有图片已生成到: {OUTPUT_DIR}/")
    for f in sorted(OUTPUT_DIR.glob("fig*.png")):
        print(f"   {f.name}")
    print("\n💡 注意: SVG文件可能仍需在浏览器中正确渲染中文字体（取决于系统字体）")
    print("   论文投稿建议直接使用PNG格式。")

if __name__ == "__main__":
    main()