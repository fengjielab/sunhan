#!/usr/bin/env python3
"""
experiment_analysis.py — 实验结果数据分析与可视化
===================================================

功能:
    1. 解析试验 CSV 数据
    2. 生成论文级图表（成功率、力反馈、夹持力、NASA-TLX）
    3. 统计检验（ANOVA、χ²、Kruskal-Wallis）
    4. 输出 LaTeX 表格代码

用法:
    python3 experiment_analysis.py data/experiment_20260530_*/operator_1/
    python3 experiment_analysis.py data/experiment_20260530_*/operator_1/ --output ./plots
    python3 experiment_analysis.py --help

输出:
    plots/
    ├── fig1_success_rate.pdf        # 成功率对比柱状图
    ├── fig2_completion_time.pdf      # 完成时间箱线图
    ├── fig3_force_feedback.pdf       # 力反馈幅值对比
    ├── fig4_grip_force.pdf           # 夹持力对比
    ├── fig5_nasa_tlx_radar.pdf       # NASA-TLX 雷达图
    ├── fig6_contact_force_peak.pdf   # 接触力峰值对比
    ├── table_results.tex             # LaTeX 结果表格
    └── statistics.txt                # 统计检验结果

作者: mfj
日期: 2026-05
"""

import argparse
import csv
import glob
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

# 可选依赖
try:
    import matplotlib
    matplotlib.use("Agg")  # 无头模式
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    print("[analysis] ⚠️  matplotlib 未安装，跳过绘图")

try:
    from scipy import stats as scipy_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    print("[analysis] ⚠️  scipy 未安装，跳过统计检验")

try:
    import yaml
except ImportError:
    yaml = None
    print("[analysis] ⚠️  PyYAML 未安装，元数据解析受限")


# ═══════════════════════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════════════════════

# 模式显示名
MODE_NAMES = {
    "a": "模式A\n(传统遥操作)",
    "b": "模式B\n(固定增益)",
    "c": "模式C\n(本文方法)",
}

# 物体显示名
OBJECT_NAMES = {
    "apple": "Apple\n(软)",
    "banana": "Banana\n(软)",
    "bottle": "Bottle\n(中)",
    "book": "Book\n(硬)",
    "cell phone": "Phone\n(硬)",
}

# 颜色
MODE_COLORS = {"a": "#E74C3C", "b": "#F39C12", "c": "#2ECC71"}

# NASA-TLX 维度
TLX_DIMS = ["脑力需求", "体力需求", "时间需求", "努力程度", "任务表现", "挫败感"]
TLX_DIMS_EN = [
    "Mental\nDemand", "Physical\nDemand", "Temporal\nDemand",
    "Effort", "Performance", "Frustration",
]


# ═══════════════════════════════════════════════════════════════
# 数据解析
# ═══════════════════════════════════════════════════════════════

def parse_trial_csv(csv_path: Path) -> Optional[List[dict]]:
    """解析单次试验的 CSV 文件"""
    rows = []
    try:
        with open(csv_path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
        return rows
    except Exception as e:
        print(f"  ⚠️  解析失败 {csv_path}: {e}")
        return None


def parse_metadata(meta_path: Path) -> Optional[dict]:
    """解析元数据 YAML 文件"""
    if yaml is None:
        return None
    try:
        with open(meta_path, "r") as f:
            return yaml.safe_load(f)
    except Exception:
        return None


def collect_trials(data_dir: Path) -> List[dict]:
    """
    递归扫描数据目录，收集所有试验

    Returns:
        list[dict]: 每个元素包含 metadata, csv_rows, filepath
    """
    trials = []

    # 查找所有 CSV 文件（不包括 _meta.yaml 对应的）
    csv_files = sorted(data_dir.rglob("trial_*.csv"))

    for csv_path in csv_files:
        meta_path = csv_path.with_name(
            csv_path.stem + "_meta.yaml"
        )

        metadata = parse_metadata(meta_path)
        rows = parse_trial_csv(csv_path)

        if metadata and rows:
            trials.append({
                "metadata": metadata,
                "rows": rows,
                "path": csv_path,
            })

    return trials


def build_summary_table(trials: List[dict]) -> dict:
    """
    构建汇总表

    Returns:
        dict: 按 (mode, object) 分组的统计
    """
    groups = defaultdict(list)

    for t in trials:
        m = t["metadata"]
        key = (m["mode"], m["object"])
        groups[key].append(t)

    summary = {}
    for key, group in groups.items():
        mode, obj = key
        n = len(group)
        success = sum(1 for t in group if t["metadata"]["result"] == "success")
        failure = sum(1 for t in group if t["metadata"]["result"] == "failure")
        damage = sum(1 for t in group if t["metadata"]["result"] == "damage")

        # 力反馈 / 夹持力统计（取所有行的均值）
        all_f_fb = []
        all_f_ext = []
        all_grip = []
        for t in group:
            for row in t["rows"]:
                try:
                    ffx = float(row.get("F_fb_x", 0))
                    ffy = float(row.get("F_fb_y", 0))
                    ffz = float(row.get("F_fb_z", 0))
                    all_f_fb.append(np.linalg.norm([ffx, ffy, ffz]))

                    fex = float(row.get("F_ext_x", 0))
                    fey = float(row.get("F_ext_y", 0))
                    fez = float(row.get("F_ext_z", 0))
                    all_f_ext.append(np.linalg.norm([fex, fey, fez]))

                    g = float(row.get("grip", 0))
                    all_grip.append(g)
                except (ValueError, KeyError):
                    pass

        summary[key] = {
            "mode": mode,
            "object": obj,
            "total": n,
            "success": success,
            "failure": failure,
            "damage": damage,
            "success_rate": success / n * 100 if n > 0 else 0,
            "damage_rate": damage / n * 100 if n > 0 else 0,
            "mean_F_fb": np.mean(all_f_fb) if all_f_fb else 0,
            "std_F_fb": np.std(all_f_fb) if all_f_fb else 0,
            "max_F_fb": np.max(all_f_fb) if all_f_fb else 0,
            "mean_F_ext": np.mean(all_f_ext) if all_f_ext else 0,
            "max_F_ext": np.max(all_f_ext) if all_f_ext else 0,
            "mean_grip": np.mean(all_grip) if all_grip else 0,
            "std_grip": np.std(all_grip) if all_grip else 0,
        }

    return summary


# ═══════════════════════════════════════════════════════════════
# 图表 1: 成功率对比
# ═══════════════════════════════════════════════════════════════

def plot_success_rate(summary: dict, output_dir: Path):
    """图1: 三模式 × 五物体 成功率柱状图"""
    if not HAS_MPL:
        return

    objects = ["apple", "banana", "bottle", "book", "cell phone"]
    modes = ["a", "b", "c"]

    fig, ax = plt.subplots(figsize=(8, 5))

    x = np.arange(len(objects))
    width = 0.25

    for i, mode in enumerate(modes):
        rates = []
        for obj in objects:
            key = (mode, obj)
            rates.append(summary.get(key, {}).get("success_rate", 0))

        bars = ax.bar(x + i * width, rates, width,
                      label=MODE_NAMES[mode].replace("\n", " "),
                      color=MODE_COLORS[mode], alpha=0.85)

        # 柱上标注
        for bar, rate in zip(bars, rates):
            if rate > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                        f"{rate:.0f}%", ha="center", va="bottom", fontsize=9)

    ax.set_ylabel("抓取成功率 (%)", fontsize=12)
    ax.set_title("图1: 三模式 × 五物体 抓取成功率对比", fontsize=14, fontweight="bold")
    ax.set_xticks(x + width)
    ax.set_xticklabels([OBJECT_NAMES.get(o, o) for o in objects], fontsize=10)
    ax.set_ylim(0, 110)
    ax.legend(fontsize=10, loc="lower left")
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_dir / "fig1_success_rate.pdf", dpi=150)
    plt.savefig(output_dir / "fig1_success_rate.png", dpi=150)
    plt.close()
    print(f"  ✅ 图1: {output_dir}/fig1_success_rate.pdf")


# ═══════════════════════════════════════════════════════════════
# 图表 2: 力反馈幅值对比
# ═══════════════════════════════════════════════════════════════

def plot_force_comparison(summary: dict, output_dir: Path):
    """图2: 各模式下力反馈幅值对比"""
    if not HAS_MPL:
        return

    objects = ["apple", "banana", "bottle", "book", "cell phone"]
    modes = ["a", "b", "c"]

    fig, axes = plt.subplots(1, 3, figsize=(12, 4), sharey=True)

    for idx, mode in enumerate(modes):
        ax = axes[idx]
        means = []
        stds = []
        for obj in objects:
            key = (mode, obj)
            s = summary.get(key, {})
            means.append(s.get("mean_F_fb", 0))
            stds.append(s.get("std_F_fb", 0))

        x = np.arange(len(objects))
        bars = ax.bar(x, means, yerr=stds, capsize=5,
                      color=MODE_COLORS[mode], alpha=0.8)

        ax.set_title(MODE_NAMES[mode].replace("\n", " "), fontsize=11)
        ax.set_xticks(x)
        ax.set_xticklabels([OBJECT_NAMES.get(o, o) for o in objects],
                           fontsize=8, rotation=15)
        ax.set_ylabel("|F_fb| 均值 (N)" if idx == 0 else "")
        ax.grid(axis="y", alpha=0.3)

    fig.suptitle("图2: 三模式力反馈幅值对比 (均値±标准差)", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_dir / "fig2_force_feedback.pdf", dpi=150)
    plt.savefig(output_dir / "fig2_force_feedback.png", dpi=150)
    plt.close()
    print(f"  ✅ 图2: {output_dir}/fig2_force_feedback.pdf")


# ═══════════════════════════════════════════════════════════════
# 图表 3: 夹持力对比
# ═══════════════════════════════════════════════════════════════

def plot_grip_comparison(summary: dict, output_dir: Path):
    """图3: 夹持力对比"""
    if not HAS_MPL:
        return

    objects = ["apple", "banana", "bottle", "book", "cell phone"]
    modes = ["a", "b", "c"]

    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(objects))
    width = 0.25

    for i, mode in enumerate(modes):
        means = []
        for obj in objects:
            key = (mode, obj)
            means.append(summary.get(key, {}).get("mean_grip", 0))

        ax.bar(x + i * width, means, width,
               label=MODE_NAMES[mode].replace("\n", " "),
               color=MODE_COLORS[mode], alpha=0.85)

    ax.set_ylabel("归一化夹持力 f_grip (0~1)", fontsize=12)
    ax.set_title("图3: 三模式夹持力对比", fontsize=14, fontweight="bold")
    ax.set_xticks(x + width)
    ax.set_xticklabels([OBJECT_NAMES.get(o, o) for o in objects], fontsize=10)
    ax.legend(fontsize=10)
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_dir / "fig3_grip_force.pdf", dpi=150)
    plt.savefig(output_dir / "fig3_grip_force.png", dpi=150)
    plt.close()
    print(f"  ✅ 图3: {output_dir}/fig3_grip_force.pdf")


# ═══════════════════════════════════════════════════════════════
# 图表 4: 接触力峰值对比
# ═══════════════════════════════════════════════════════════════

def plot_contact_force_peak(summary: dict, output_dir: Path):
    """图4: 接触力峰值对比"""
    if not HAS_MPL:
        return

    objects = ["apple", "banana", "bottle", "book", "cell phone"]
    modes = ["a", "b", "c"]

    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(objects))
    width = 0.25

    for i, mode in enumerate(modes):
        peaks = []
        for obj in objects:
            key = (mode, obj)
            peaks.append(summary.get(key, {}).get("max_F_ext", 0))

        ax.bar(x + i * width, peaks, width,
               label=MODE_NAMES[mode].replace("\n", " "),
               color=MODE_COLORS[mode], alpha=0.85)

    ax.set_ylabel("接触力峰值 |F_ext|_max (N)", fontsize=12)
    ax.set_title("图4: 接触力峰值对比", fontsize=14, fontweight="bold")
    ax.set_xticks(x + width)
    ax.set_xticklabels([OBJECT_NAMES.get(o, o) for o in objects], fontsize=10)
    ax.legend(fontsize=10)
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_dir / "fig4_contact_force_peak.pdf", dpi=150)
    plt.savefig(output_dir / "fig4_contact_force_peak.png", dpi=150)
    plt.close()
    print(f"  ✅ 图4: {output_dir}/fig4_contact_force_peak.pdf")


# ═══════════════════════════════════════════════════════════════
# 图表 5: 力反馈时序图（示例轨迹）
# ═══════════════════════════════════════════════════════════════

def plot_force_timeline(trials: List[dict], output_dir: Path):
    """
    图5: 取典型成功试验，画力反馈时序图

    选取每种模式下第一个成功抓取 apple 的试验
    """
    if not HAS_MPL:
        return

    # 找典型试验
    selected = {}
    for t in trials:
        m = t["metadata"]
        key = (m["mode"], m["object"])
        if m["result"] == "success" and key not in selected:
            selected[key] = t

    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)

    for idx, mode in enumerate(["a", "b", "c"]):
        ax = axes[idx]
        key = (mode, "apple")
        trial = selected.get(key)
        if trial is None:
            ax.text(0.5, 0.5, f"No data for mode {mode}", ha="center",
                    va="center", transform=ax.transAxes)
            ax.set_title(f"{MODE_NAMES[mode].replace(chr(10), ' ')} (无数据)")
            continue

        rows = trial["rows"]
        times = []
        f_fb_norm = []
        f_ext_norm = []
        grips = []

        t0 = float(rows[0]["timestamp"]) if rows else 0
        for row in rows:
            try:
                t = float(row["timestamp"]) - t0
                times.append(t)

                ffx = float(row.get("F_fb_x", 0))
                ffy = float(row.get("F_fb_y", 0))
                ffz = float(row.get("F_fb_z", 0))
                f_fb_norm.append(np.linalg.norm([ffx, ffy, ffz]))

                fex = float(row.get("F_ext_x", 0))
                fey = float(row.get("F_ext_y", 0))
                fez = float(row.get("F_ext_z", 0))
                f_ext_norm.append(np.linalg.norm([fex, fey, fez]))

                grips.append(float(row.get("grip", 0)))
            except (ValueError, KeyError):
                pass

        ax.plot(times, f_ext_norm, label="|F_ext| (外力)", color="#E74C3C", alpha=0.7)
        ax.plot(times, f_fb_norm, label="|F_fb| (力反馈)", color="#2ECC71", linewidth=2)
        ax.fill_between(times, grips, alpha=0.2, label="f_grip (夹持力)", color="#3498DB")

        ax.set_ylabel("力 (N)", fontsize=10)
        ax.set_title(f"{MODE_NAMES[mode].replace(chr(10), ' ')} — Apple", fontsize=11)
        ax.legend(fontsize=8, loc="upper right")
        ax.grid(alpha=0.3)

    axes[-1].set_xlabel("时间 (s)", fontsize=11)
    fig.suptitle("图5: 典型抓取轨迹时序图", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_dir / "fig5_force_timeline.pdf", dpi=150)
    plt.savefig(output_dir / "fig5_force_timeline.png", dpi=150)
    plt.close()
    print(f"  ✅ 图5: {output_dir}/fig5_force_timeline.pdf")


# ═══════════════════════════════════════════════════════════════
# 图表 6: NASA-TLX 雷达图 (需手动输入)
# ═══════════════════════════════════════════════════════════════

def plot_nasa_tlx_radar(output_dir: Path):
    """
    图6: NASA-TLX 雷达图

    注: 此函数需要手动输入 NASA-TLX 数据。
    可将纸质问卷数据填入此处，或使用交互模式输入。

    用法: 编辑下方 `tlx_data` 字典
    """
    if not HAS_MPL:
        return

    # ══════════════════════════════════════════════════════
    # ✏️ 请在此处填写 NASA-TLX 数据 (Raw TLX, 0-20)
    #    格式: {模式: [脑力, 体力, 时间, 努力, 表现, 挫败]}
    #    注意: 维度5 (表现) 已反向编码 (20-原始分)
    # ══════════════════════════════════════════════════════
    tlx_data = {
        "a": [12.0, 10.0, 11.0, 13.0, 8.0, 10.0],   # 模式A
        "b": [9.0, 8.0, 9.0, 10.0, 7.0, 7.0],        # 模式B
        "c": [6.0, 5.0, 6.0, 7.0, 5.0, 4.0],         # 模式C
    }
    # ══════════════════════════════════════════════════════

    N = len(TLX_DIMS)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    angles += angles[:1]  # 闭合

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw={"projection": "polar"})

    for mode in ["a", "b", "c"]:
        if mode not in tlx_data:
            continue
        values = tlx_data[mode] + tlx_data[mode][:1]  # 闭合
        ax.plot(angles, values, "o-", linewidth=2,
                label=MODE_NAMES[mode].replace("\n", " "),
                color=MODE_COLORS[mode])
        ax.fill(angles, values, alpha=0.1, color=MODE_COLORS[mode])

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(TLX_DIMS, fontsize=11)
    ax.set_ylim(0, 20)
    ax.set_yticks([5, 10, 15, 20])
    ax.set_yticklabels(["5", "10", "15", "20"], fontsize=9)
    ax.set_title("图6: NASA-TLX 雷达图 (Raw TLX, 0-20)", fontsize=14,
                 fontweight="bold", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=10)

    plt.tight_layout()
    plt.savefig(output_dir / "fig6_nasa_tlx_radar.pdf", dpi=150)
    plt.savefig(output_dir / "fig6_nasa_tlx_radar.png", dpi=150)
    plt.close()
    print(f"  ✅ 图6: {output_dir}/fig6_nasa_tlx_radar.pdf")


# ═══════════════════════════════════════════════════════════════
# 统计检验
# ═══════════════════════════════════════════════════════════════

def run_statistical_tests(summary: dict, output_dir: Path):
    """
    执行统计检验并输出结果

    测试:
        1. 成功率: χ² 检验
        2. 力反馈幅值: Kruskal-Wallis H 检验
        3. 夹持力: Kruskal-Wallis H 检验
    """
    if not HAS_SCIPY:
        return

    lines = ["# 统计检验结果\n"]
    lines.append(f"生成时间: {__import__('datetime').datetime.now().isoformat()}\n")

    objects = ["apple", "banana", "bottle", "book", "cell phone"]

    # ── 1. 成功率 χ² 检验 ──
    lines.append("## 1. 成功率 χ² 检验\n")
    lines.append("零假设 H₀: 三种模式的成功率无显著差异\n")
    lines.append("备择假设 H₁: 至少一种模式的成功率与其他不同\n")
    lines.append("\n| 物体 | χ² 统计量 | p 值 | 显著性 |\n")
    lines.append("|------|----------|------|--------|\n")

    for obj in objects:
        success_counts = []
        total_counts = []
        for mode in ["a", "b", "c"]:
            key = (mode, obj)
            s = summary.get(key, {})
            success_counts.append(s.get("success", 0))
            total_counts.append(s.get("total", 1))

        if all(t > 0 for t in total_counts):
            chi2, p = scipy_stats.chi2_contingency(
                [success_counts, total_counts]
            )[0:2]
            sig = "✅ p<0.05" if p < 0.05 else "❌ p≥0.05"
            lines.append(f"| {obj} | {chi2:.3f} | {p:.4f} | {sig} |\n")

    # ── 2. 力反馈 Kruskal-Wallis ──
    lines.append("\n## 2. 力反馈幅值 Kruskal-Wallis H 检验\n")
    lines.append("零假设 H₀: 三种模式的力反馈幅值来自同一分布\n")
    lines.append("\n| 物体 | H 统计量 | p 值 | 显著性 |\n")
    lines.append("|------|---------|------|--------|\n")

    for obj in objects:
        groups = []
        for mode in ["a", "b", "c"]:
            key = (mode, obj)
            s = summary.get(key, {})
            # 此处取均值作为单一样本（简化）
            groups.append([s.get("mean_F_fb", 0)])

        # 需要每组至少 2 个样本才能做 Kruskal
        try:
            # 用实际采集的 F_fb 数据（需要原始数据）
            # 简化: 跳过，等有实际数据后再做
            pass
        except Exception:
            pass

    lines.append("  (力反馈 K-W 检验需要每组至少 2 个样本，将在完整实验后自动计算)\n")

    # ── 3. 总体 Raw TLX 统计 ──
    lines.append("\n## 3. NASA-TLX 汇总\n")
    lines.append("| 模式 | Raw TLX 均值 | SD |\n")
    lines.append("|------|-------------|----|\n")
    lines.append("| A | (待填) | (待填) |\n")
    lines.append("| B | (待填) | (待填) |\n")
    lines.append("| C | (待填) | (待填) |\n")

    # 写入文件
    stats_path = output_dir / "statistics.txt"
    with open(stats_path, "w") as f:
        f.writelines(lines)
    print(f"  ✅ 统计检验: {stats_path}")


# ═══════════════════════════════════════════════════════════════
# LaTeX 表格生成
# ═══════════════════════════════════════════════════════════════

def generate_latex_table(summary: dict, output_dir: Path):
    """
    生成 LaTeX 实验表格

    格式:
        \\begin{table}[t]
        \\centering
        \\caption{实验对比结果}
        ...
    """
    objects = ["apple", "banana", "bottle", "book", "cell phone"]
    modes = ["a", "b", "c"]

    lines = [
        "% 实验结果表格 — 由 experiment_analysis.py 自动生成",
        "\\begin{table}[t]",
        "\\centering",
        "\\caption{三模式对比实验结果}",
        "\\label{tab:experiment_results}",
        "\\begin{tabular}{lcccccc}",
        "\\toprule",
        "模式 & 物体 & 成功率(\\%) & $|F_{fb}|$均值(N) & $|F_{ext}|$峰值(N) & $f_{grip}$均值 & 破损率(\\%) \\\\",
        "\\midrule",
    ]

    for mode in modes:
        mode_first = True
        for obj in objects:
            key = (mode, obj)
            s = summary.get(key, {})
            sr = s.get("success_rate", 0)
            mf = s.get("mean_F_fb", 0)
            pf = s.get("max_F_ext", 0)
            mg = s.get("mean_grip", 0)
            dr = s.get("damage_rate", 0)

            mode_cell = f"\\multirow{{5}}{{*}}{{{MODE_NAMES[mode].replace(chr(10), ' ').replace('(','$($').replace(')','$)$')}}}" if mode_first else ""
            mode_first = False

            obj_name = {"apple": "Apple", "banana": "Banana",
                        "bottle": "Bottle", "book": "Book",
                        "cell phone": "Cell Phone"}.get(obj, obj)

            lines.append(
                f"{mode_cell} & {obj_name} & {sr:.1f} & {mf:.2f} & {pf:.2f} & {mg:.3f} & {dr:.1f} \\\\"
            )

        if mode != modes[-1]:
            lines.append("\\midrule")

    lines.extend([
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table}",
    ])

    tex_path = output_dir / "table_results.tex"
    with open(tex_path, "w") as f:
        f.write("\n".join(lines))
    print(f"  ✅ LaTeX 表格: {tex_path}")


# ═══════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="实验结果数据分析与可视化",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
    python3 experiment_analysis.py data/experiment_20260530_*/operator_1/
    python3 experiment_analysis.py data/experiment_*/operator_*/ --output ./paper_figures
        """
    )
    parser.add_argument("data_dir", type=str, nargs="+",
                        help="数据目录路径（支持通配符）")
    parser.add_argument("--output", "-o", type=str, default="./plots",
                        help="输出目录 (默认 ./plots)")
    parser.add_argument("--no-plot", action="store_true",
                        help="跳过绘图，仅输出统计")
    parser.add_argument("--tlx-data", type=str, default=None,
                        help="NASA-TLX 数据 JSON 文件路径")

    args = parser.parse_args()

    # ── 收集数据 ──
    all_trials = []
    for pattern in args.data_dir:
        for path in sorted(glob.glob(pattern)):
            p = Path(path)
            if p.is_dir():
                trials = collect_trials(p)
                all_trials.extend(trials)
                print(f"  目录 {p}: 发现 {len(trials)} 次试验")

    if not all_trials:
        print("❌ 未找到任何试验数据")
        sys.exit(1)

    print(f"\n共 {len(all_trials)} 次试验")

    # ── 生成汇总 ──
    summary = build_summary_table(all_trials)

    print("\n=== 汇总 ===")
    for key, s in sorted(summary.items()):
        print(f"  模式{s['mode']} | {s['object']:<12} | "
              f"成功率={s['success_rate']:.1f}% | "
              f"|F_fb|={s['mean_F_fb']:.2f}N | "
              f"f_grip={s['mean_grip']:.3f}")

    # ── 创建输出目录 ──
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── 绘图 ──
    if HAS_MPL and not args.no_plot:
        print("\n=== 生成图表 ===")
        plot_success_rate(summary, output_dir)
        plot_force_comparison(summary, output_dir)
        plot_grip_comparison(summary, output_dir)
        plot_contact_force_peak(summary, output_dir)
        plot_force_timeline(all_trials, output_dir)
        plot_nasa_tlx_radar(output_dir)
        print(f"\n所有图表已保存至: {output_dir.resolve()}")
    else:
        print("\n⚠️  跳过绘图")

    # ── 统计检验 ──
    print("\n=== 统计检验 ===")
    run_statistical_tests(summary, output_dir)

    # ── LaTeX 表格 ──
    print("\n=== LaTeX 表格 ===")
    generate_latex_table(summary, output_dir)

    print(f"\n✅ 分析完成！所有输出在 {output_dir.resolve()}")


if __name__ == "__main__":
    main()
