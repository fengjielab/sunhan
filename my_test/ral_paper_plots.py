#!/usr/bin/env python3
"""
ral_paper_plots.py — RAL论文自动化数据分析+出图脚本
=====================================================

功能: 从实验数据目录读取所有trial，自动生成RAL论文所需的全部图表

用法:
    # 分析已有数据
    python3 my_test/ral_paper_plots.py --data-dir data/ral_experiment --output ./paper_figures

    # 也可以分析分散存放的数据（自动搜索）
    python3 my_test/ral_paper_plots.py --data-dir data/ --recursive --output ./paper_figures

输出:
    paper_figures/
    ├── fig1_completion_time.pdf       # 完成时间柱状图
    ├── fig2_force_peak.pdf            # 外力峰值对比
    ├── fig3_fusion_process_curve.pdf  # F模式过程曲线
    ├── fig3_fusion_process_curve.png
    ├── fig4_nasa_tlx_radar.pdf        # NASA-TLX雷达图
    ├── fig5_success_rate.pdf          # 成功率
    ├── fig6_force_comparison.pdf      # F模式 vs E模式 时序对比
    ├── fig7_stiffness_scatter.pdf     # K_trans vs F_ext_mag 散点图
    ├── fig8_force_distribution.pdf    # 外力分布直方图
    ├── table_results.tex              # LaTeX 汇总表
    └── statistics.txt                 # 统计检验结果
"""

import argparse
import csv
import glob
import json
import os
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    print("⚠️  matplotlib 未安装，跳过绘图")

try:
    from scipy import stats as scipy_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    print("⚠️  scipy 未安装，跳过统计检验")

# ═══════════════════════════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════════════════════════

MODE_NAMES = {
    "A": "A 固定参数",
    "B": "B 人工选择",
    "C": "C 视觉前馈",
    "D": "D 视觉消融",
    "E": "E 力反馈自适应",
    "F": "F 融合方法",
}

MODE_COLORS = {
    "A": "#7F8C8D",  # 灰
    "B": "#F39C12",  # 橙
    "C": "#3498DB",  # 蓝
    "D": "#95A5A6",  # 浅灰
    "E": "#E74C3C",  # 红
    "F": "#2ECC71",  # 绿
}

MODE_ORDER = ["A", "B", "C", "D", "E", "F"]
OBJECT_ORDER = ["soft", "medium", "hard"]
OBJECT_NAMES = {"soft": "软物体", "medium": "中物体", "hard": "硬物体"}
OBJECT_NAMES_EN = {"soft": "Soft", "medium": "Medium", "hard": "Hard"}

# NASA-TLX 维度
TLX_DIMS = ["脑力需求", "体力需求", "时间需求", "努力程度", "任务表现", "挫败感"]
TLX_DIMS_EN = ["Mental", "Physical", "Temporal", "Effort", "Performance", "Frustration"]

F_SAT_LINE = 5.0  # 外力饱和参考线


# ═══════════════════════════════════════════════════════════════════
# 数据加载
# ═══════════════════════════════════════════════════════════════════

def parse_mode(filename: str) -> str:
    """从文件名推断模式"""
    name = filename.lower()
    if "vision_force" in name or "fusion" in name or "_F_" in name:
        return "F"
    if "force_adaptive" in name or "_E_" in name:
        return "E"
    if "vision_observe" in name or "_D_" in name:
        return "D"
    if "vision" in name or "_C_" in name or "soft_obj" in name:
        return "C"
    if "default" in name or "_A_" in name or "fixed" in name:
        return "A"
    if "_B_" in name or "human" in name:
        return "B"
    return "unknown"


def parse_object_label(row: dict) -> str:
    """从CSV行推断物体类别"""
    # 尝试从 vision_label 列读
    if "vision_label" in row:
        v = str(row["vision_label"]).strip().lower()
        if v in ("soft", "medium", "hard"):
            return v
    # 从 JSON 的 object 字段读
    return "unknown"


def load_trials(data_dir: Path, recursive: bool = False) -> List[dict]:
    """
    扫描目录，加载所有 trial 的 JSON 汇总 + CSV 轨迹

    返回: list[dict], 每个包含:
        - mode: str (A/B/C/D/E/F)
        - object: str (soft/medium/hard)
        - operator: str
        - metrics: dict (来自 JSON)
        - csv_rows: list[dict] (来自 CSV)
    """
    trials = []

    # 搜索所有 JSON 文件
    if recursive:
        json_files = sorted(data_dir.rglob("*summary.json"))
        json_files += sorted(data_dir.rglob("*.json"))
    else:
        json_files = sorted(data_dir.glob("*summary.json"))
        json_files += sorted(data_dir.glob("*.json"))

    # 去重
    seen = set()
    unique_json = []
    for jf in json_files:
        if str(jf) not in seen:
            seen.add(str(jf))
            unique_json.append(jf)

    for json_path in unique_json:
        try:
            with open(json_path, "r") as f:
                meta = json.load(f)
        except (json.JSONDecodeError, IOError):
            continue

        # 找对应的 CSV 文件
        stem = json_path.stem
        # 尝试几种命名模式
        csv_candidates = [
            json_path.with_name(stem.replace("_summary", "") + ".csv"),
            json_path.with_name(stem.replace("_summary", "_trajectory.csv")),
            json_path.with_suffix(".csv"),
        ]
        # 也搜索同目录下的所有CSV，匹配时间戳
        timestamp = stem.split("_")[-1] if "_" in stem else ""
        csv_path = None
        for cand in csv_candidates:
            if cand.exists():
                csv_path = cand
                break
        if csv_path is None and timestamp:
            # 模糊匹配时间戳
            for f in json_path.parent.glob(f"*{timestamp}*.csv"):
                csv_path = f
                break

        # 解析 JSON 中的元数据
        mode = meta.get("mode", {}).get("mode", parse_mode(json_path.name))
        # 规范化模式名
        mode_map = {
            "default": "A", "experiment_fixed_a": "A", "a": "A",
            "soft_obj": "B", "b": "B",
            "vision": "C", "c": "C",
            "vision_observe": "D", "d": "D",
            "force_adaptive": "E", "e": "E",
            "vision_force": "F", "f": "F", "F": "F",
        }
        mode = mode_map.get(mode.lower() if isinstance(mode, str) else "", mode)

        runtime = meta.get("runtime", {})
        force_info = meta.get("external_force", {})

        # 获取物体类别 - 尝试从多个来源
        obj_label = meta.get("object", "").lower()
        if not obj_label or obj_label == "unknown":
            obj_label = meta.get("mode", {}).get("vision_label", "unknown")

        operator = meta.get("operator", "unknown")

        # 加载 CSV
        csv_rows = []
        if csv_path and csv_path.exists():
            try:
                with open(csv_path, "r") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        parsed = {}
                        for k, v in row.items():
                            k = k.strip()
                            try:
                                parsed[k] = float(v)
                            except (ValueError, TypeError):
                                parsed[k] = v
                        csv_rows.append(parsed)
            except Exception:
                pass

        # 构建 metrics
        metrics = {
            "duration_s": runtime.get("duration_s", 0),
            "traj_length_m": runtime.get("traj_length_m", 0),
            "mean_speed_ms": runtime.get("mean_speed_ms", 0),
            "max_speed_ms": runtime.get("max_speed_ms", 0),
            "speed_std_ms": runtime.get("speed_std_ms", 0),
            "F_ext_peak_N": force_info.get("F_ext_peak_N", 0),
            "F_ext_peak_time_s": force_info.get("F_ext_peak_time_s", 0),
            "F_ext_mean_N": force_info.get("F_ext_mean_N", 0),
            "n_samples": force_info.get("n_samples", 0),
            "success": meta.get("success", 1),
            "nasa_tlx": meta.get("nasa_tlx", 50),
            "damage_score": meta.get("damage_score", 0),
            "human_score": meta.get("human_score", 3),
        }

        # 如果CSV有数据，从CSV重新计算精确指标
        if csv_rows:
            f_exts = [r["F_ext_mag"] for r in csv_rows]
            metrics["F_ext_peak_N"] = max(f_exts)
            metrics["F_ext_mean_N"] = statistics.mean(f_exts)
            metrics["F_ext_std_N"] = statistics.stdev(f_exts) if len(f_exts) > 1 else 0
            metrics["F_ext_p95_N"] = np.percentile(f_exts, 95) if f_exts else 0
            metrics["F_ext_p99_N"] = np.percentile(f_exts, 99) if f_exts else 0
            kts = [r["K_trans"] for r in csv_rows]
            metrics["K_trans_mean"] = statistics.mean(kts)
            metrics["K_trans_min"] = min(kts)
            metrics["K_trans_max"] = max(kts)
            metrics["K_trans_final"] = kts[-1] if kts else 0

        # 从CSV推断物体类别（基于gripper_deg或vision_label）
        if obj_label == "unknown" and csv_rows:
            # 看vision_label
            labels = set()
            for r in csv_rows:
                if "vision_label" in r:
                    lbl = str(r["vision_label"]).strip().lower()
                    if lbl in ("soft", "medium", "hard"):
                        labels.add(lbl)
            if labels:
                obj_label = list(labels)[0]

        trials.append({
            "mode": mode,
            "object": obj_label,
            "operator": operator,
            "path": json_path,
            "meta": meta,
            "metrics": metrics,
            "csv_rows": csv_rows,
        })

    return trials


def build_summary(trials: List[dict]) -> dict:
    """
    按 (mode, object) 分组汇总
    """
    groups = defaultdict(list)
    for t in trials:
        key = (t["mode"], t["object"])
        groups[key].append(t)

    summary = {}
    for key, group in groups.items():
        mode, obj = key
        n = len(group)
        successes = [t["metrics"]["success"] for t in group]
        f_peaks = [t["metrics"]["F_ext_peak_N"] for t in group]
        f_means = [t["metrics"]["F_ext_mean_N"] for t in group]
        durations = [t["metrics"]["duration_s"] for t in group]
        traj_lens = [t["metrics"]["traj_length_m"] for t in group]
        tlxs = [t["metrics"]["nasa_tlx"] for t in group]
        damages = [t["metrics"]["damage_score"] for t in group]
        human_scores = [t["metrics"]["human_score"] for t in group]

        def m(s): return statistics.mean(s) if s else 0
        def s(s): return statistics.stdev(s) if len(s) > 1 else 0

        summary[key] = {
            "mode": mode, "object": obj, "n": n,
            "success_rate": sum(successes) / n * 100 if n > 0 else 0,
            "success_count": sum(successes), "total_count": n,
            "F_ext_peak_mean": m(f_peaks), "F_ext_peak_std": s(f_peaks),
            "F_ext_mean": m(f_means), "F_ext_std": s(f_means),
            "duration_mean": m(durations), "duration_std": s(durations),
            "traj_length_mean": m(traj_lens), "traj_length_std": s(traj_lens),
            "tlx_mean": m(tlxs), "tlx_std": s(tlxs),
            "damage_mean": m(damages), "damage_std": s(damages),
            "human_score_mean": m(human_scores), "human_score_std": s(human_scores),
        }
    return summary


# ═══════════════════════════════════════════════════════════════════
# 图1: 完成时间分组柱状图
# ═══════════════════════════════════════════════════════════════════

def plot_completion_time(summary: dict, output_dir: Path):
    """图1: 6模式×3物体 完成时间"""
    if not HAS_MPL:
        return

    fig, ax = plt.subplots(figsize=(10, 5.5))
    x = np.arange(len(OBJECT_ORDER))
    width = 0.12

    for i, mode in enumerate(MODE_ORDER):
        means = []
        errs = []
        for obj in OBJECT_ORDER:
            key = (mode, obj)
            s = summary.get(key, {})
            means.append(s.get("duration_mean", 0))
            errs.append(s.get("duration_std", 0))
        bars = ax.bar(x + i * width, means, width, yerr=errs, capsize=3,
                      label=MODE_NAMES[mode], color=MODE_COLORS[mode], alpha=0.85)

    ax.set_ylabel("完成时间 (s)", fontsize=13)
    ax.set_title("图1: 六模式完成时间对比", fontsize=14, fontweight="bold")
    ax.set_xticks(x + width * 2.5)
    ax.set_xticklabels([OBJECT_NAMES[o] for o in OBJECT_ORDER], fontsize=12)
    ax.legend(fontsize=9, ncol=2, loc="upper right")
    ax.grid(axis="y", alpha=0.3)

    # 标注F模式p值
    plt.tight_layout()
    plt.savefig(output_dir / "fig1_completion_time.pdf", dpi=150)
    plt.savefig(output_dir / "fig1_completion_time.png", dpi=150)
    plt.close()
    print(f"  ✅ 图1: {output_dir}/fig1_completion_time.pdf")


# ═══════════════════════════════════════════════════════════════════
# 图2: 末端外力峰值对比
# ═══════════════════════════════════════════════════════════════════

def plot_force_peak(summary: dict, output_dir: Path):
    """图2: 6模式末端外力峰值对比"""
    if not HAS_MPL:
        return

    fig, axes = plt.subplots(1, 3, figsize=(12, 4.5), sharey=True)

    for idx, obj in enumerate(OBJECT_ORDER):
        ax = axes[idx]
        modes_present = []
        means = []
        errs = []
        for mode in MODE_ORDER:
            key = (mode, obj)
            s = summary.get(key, {})
            if s.get("n", 0) > 0:
                modes_present.append(mode)
                means.append(s.get("F_ext_peak_mean", 0))
                errs.append(s.get("F_ext_peak_std", 0))

        x = np.arange(len(modes_present))
        bars = ax.bar(x, means, yerr=errs, capsize=4,
                      color=[MODE_COLORS[m] for m in modes_present],
                      alpha=0.85, width=0.6)

        # F_sat 参考线
        ax.axhline(y=F_SAT_LINE, color="gray", linestyle=":", alpha=0.6, linewidth=1.2)
        if idx == 2:
            ax.text(len(modes_present)-0.5, F_SAT_LINE+0.2, f"F_sat={F_SAT_LINE}N",
                    fontsize=8, color="gray", ha="right")

        ax.set_title(OBJECT_NAMES[obj], fontsize=12)
        ax.set_xticks(x)
        ax.set_xticklabels(modes_present, fontsize=11)
        ax.set_ylabel("|F_ext| 峰值 (N)" if idx == 0 else "")
        ax.grid(axis="y", alpha=0.3)

    fig.suptitle("图2: 六模式末端外力峰值对比 (均値±标准差)", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_dir / "fig2_force_peak.pdf", dpi=150)
    plt.savefig(output_dir / "fig2_force_peak.png", dpi=150)
    plt.close()
    print(f"  ✅ 图2: {output_dir}/fig2_force_peak.pdf")


# ═══════════════════════════════════════════════════════════════════
# 图3: F模式过程曲线
# ═══════════════════════════════════════════════════════════════════

def plot_fusion_process(trials: List[dict], output_dir: Path):
    """图3: F模式的F_ext_mag, K_trans, fusion_delta_K 过程曲线"""
    if not HAS_MPL:
        return

    # 找F模式的典型trial（每个物体类别选第一个）
    selected = {}
    for t in trials:
        if t["mode"] == "F" and t["object"] in OBJECT_ORDER:
            key = t["object"]
            if key not in selected and len(t["csv_rows"]) > 100:
                selected[key] = t

    if not selected:
        print("  ⚠️  图3: 无F模式数据，跳过")
        return

    fig, axes = plt.subplots(len(selected), 1, figsize=(12, 4.5 * len(selected)),
                             sharex=False)

    if len(selected) == 1:
        axes = [axes]

    for idx, (obj, trial) in enumerate(selected.items()):
        ax = axes[idx]
        rows = trial["csv_rows"]
        times = [r["time"] for r in rows]
        f_ext = [r["F_ext_mag"] for r in rows]
        k_trans = [r["K_trans"] for r in rows]
        dK = [r.get("fusion_delta_K", 0) for r in rows]
        fusion_active = [r.get("fusion_active", 0) for r in rows]

        color1 = "#2E86C1"
        color2 = "#E67E22"
        color3 = "#27AE60"

        ax.plot(times, f_ext, label="|F_ext| (外力)", color=color1, linewidth=1.0)
        ax.plot(times, k_trans, label="K_trans (刚度)", color=color2, linewidth=1.0)
        ax.axhline(y=F_SAT_LINE, color="gray", linestyle=":", alpha=0.5)

        # 标注 fusion active 区域
        in_fusion = False
        fusion_start = None
        for i, fa in enumerate(fusion_active):
            if fa == 1.0 and not in_fusion:
                fusion_start = times[i]
                in_fusion = True
            elif fa == 0.0 and in_fusion:
                ax.axvspan(fusion_start, times[i], alpha=0.08, color="#2ECC71")
                in_fusion = False
        if in_fusion:
            ax.axvspan(fusion_start, times[-1], alpha=0.08, color="#2ECC71")

        # 双y轴画 fusion_delta_K
        ax2 = ax.twinx()
        ax2.plot(times, dK, label="ΔK_f (融合修正)", color=color3, linewidth=1.5, alpha=0.7,
                 linestyle="--")
        ax2.set_ylabel("ΔK_f", fontsize=10, color=color3)

        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, fontsize=8, loc="upper right")

        ax.set_xlabel("时间 (s)", fontsize=11)
        ax.set_ylabel("|F_ext| / K_trans", fontsize=11)
        ax.set_title(f"F模式 — {OBJECT_NAMES[obj]} (操作者{trial['operator']})", fontsize=12)
        ax.grid(alpha=0.3)

    fig.suptitle("图3: 视觉-力融合模式(F)过程曲线", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_dir / "fig3_fusion_process_curve.pdf", dpi=150)
    plt.savefig(output_dir / "fig3_fusion_process_curve.png", dpi=150)
    plt.close()
    print(f"  ✅ 图3: {output_dir}/fig3_fusion_process_curve.pdf")


# ═══════════════════════════════════════════════════════════════════
# 图4: NASA-TLX 雷达图
# ═══════════════════════════════════════════════════════════════════

def plot_nasa_tlx(trials: List[dict], output_dir: Path):
    """图4: NASA-TLX 六模式雷达图"""
    if not HAS_MPL:
        return

    # 按模式汇总TLX各维度
    # 这里假设 TLX 数据在 meta 中是6维数组
    mode_tlx = defaultdict(lambda: defaultdict(list))
    for t in trials:
        meta = t.get("meta", {})
        tlx_dims = meta.get("tlx_dims", None)
        if tlx_dims and isinstance(tlx_dims, list) and len(tlx_dims) == 6:
            for i, val in enumerate(tlx_dims):
                mode_tlx[t["mode"]][i].append(float(val))

    # 计算每模式每维度的均值
    mode_means = {}
    for mode in MODE_ORDER:
        if mode in mode_tlx:
            means = []
            for i in range(6):
                vals = mode_tlx[mode][i]
                means.append(statistics.mean(vals) if vals else 50)
            mode_means[mode] = means

    if not mode_means:
        print("  ⚠️  图4: 无TLX维度数据，检查tlx_dims字段")
        # 退化为使用总分
        return _plot_nasa_tlx_total(trials, output_dir)

    N = len(TLX_DIMS)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw={"projection": "polar"})

    for mode in MODE_ORDER:
        if mode not in mode_means:
            continue
        values = mode_means[mode] + mode_means[mode][:1]
        ax.plot(angles, values, "o-", linewidth=2,
                label=MODE_NAMES[mode], color=MODE_COLORS[mode])
        ax.fill(angles, values, alpha=0.08, color=MODE_COLORS[mode])

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(TLX_DIMS, fontsize=11)
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=9)
    ax.set_title("图4: NASA-TLX 六模式雷达图 (越低越好)", fontsize=14, fontweight="bold", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.1), fontsize=9)

    plt.tight_layout()
    plt.savefig(output_dir / "fig4_nasa_tlx_radar.pdf", dpi=150)
    plt.savefig(output_dir / "fig4_nasa_tlx_radar.png", dpi=150)
    plt.close()
    print(f"  ✅ 图4: {output_dir}/fig4_nasa_tlx_radar.pdf")


def _plot_nasa_tlx_total(trials: List[dict], output_dir: Path):
    """TLX总分柱状图（回退方案）"""
    mode_tlx = defaultdict(list)
    for t in trials:
        mode_tlx[t["mode"]].append(t["metrics"]["nasa_tlx"])

    fig, ax = plt.subplots(figsize=(8, 5))
    modes = [m for m in MODE_ORDER if m in mode_tlx]
    means = [statistics.mean(mode_tlx[m]) for m in modes]
    stds = [statistics.stdev(mode_tlx[m]) if len(mode_tlx[m]) > 1 else 0 for m in modes]

    bars = ax.bar(modes, means, yerr=stds, capsize=5,
                  color=[MODE_COLORS[m] for m in modes], alpha=0.85)

    for bar, mean in zip(bars, means):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f"{mean:.0f}", ha="center", fontsize=10)

    ax.set_ylabel("NASA-TLX 总分 (0-100, 越低越好)", fontsize=12)
    ax.set_title("图4: NASA-TLX 六模式对比", fontsize=14, fontweight="bold")
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / "fig4_nasa_tlx_total.pdf", dpi=150)
    plt.savefig(output_dir / "fig4_nasa_tlx_total.png", dpi=150)
    plt.close()
    print(f"  ✅ 图4 (TLX总分): {output_dir}/fig4_nasa_tlx_total.pdf")


# ═══════════════════════════════════════════════════════════════════
# 图5: 成功率和损伤评分
# ═══════════════════════════════════════════════════════════════════

def plot_success_rate(summary: dict, output_dir: Path):
    """图5: 成功率和损伤评分"""
    if not HAS_MPL:
        return

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # 左：成功率
    ax = axes[0]
    x = np.arange(len(OBJECT_ORDER))
    width = 0.12

    for i, mode in enumerate(MODE_ORDER):
        rates = []
        for obj in OBJECT_ORDER:
            key = (mode, obj)
            s = summary.get(key, {})
            rates.append(s.get("success_rate", 0))
        ax.bar(x + i * width, rates, width, label=MODE_NAMES[mode],
               color=MODE_COLORS[mode], alpha=0.85)

    ax.set_ylabel("成功率 (%)", fontsize=12)
    ax.set_title("成功率", fontsize=13)
    ax.set_xticks(x + width * 2.5)
    ax.set_xticklabels([OBJECT_NAMES[o] for o in OBJECT_ORDER], fontsize=11)
    ax.set_ylim(0, 110)
    ax.legend(fontsize=8, ncol=2)
    ax.grid(axis="y", alpha=0.3)

    # 右：损伤评分
    ax = axes[1]
    for i, mode in enumerate(MODE_ORDER):
        damages = []
        errs = []
        for obj in OBJECT_ORDER:
            key = (mode, obj)
            s = summary.get(key, {})
            damages.append(s.get("damage_mean", 0))
            errs.append(s.get("damage_std", 0))
        ax.bar(x + i * width, damages, width, yerr=errs, capsize=3,
               label=MODE_NAMES[mode], color=MODE_COLORS[mode], alpha=0.85)

    ax.set_ylabel("损伤评分 (1-5, 越低越好)", fontsize=12)
    ax.set_title("物体损伤评分", fontsize=13)
    ax.set_xticks(x + width * 2.5)
    ax.set_xticklabels([OBJECT_NAMES[o] for o in OBJECT_ORDER], fontsize=11)
    ax.legend(fontsize=8, ncol=2)
    ax.grid(axis="y", alpha=0.3)

    fig.suptitle("图5: 成功率与损伤评分", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_dir / "fig5_success_damage.pdf", dpi=150)
    plt.savefig(output_dir / "fig5_success_damage.png", dpi=150)
    plt.close()
    print(f"  ✅ 图5: {output_dir}/fig5_success_damage.pdf")


# ═══════════════════════════════════════════════════════════════════
# 图6: F模式 vs E模式 外力时序对比
# ═══════════════════════════════════════════════════════════════════

def plot_force_comparison_timeline(trials: List[dict], output_dir: Path):
    """图6: F模式 vs E模式 相同物体下的外力时序对比"""
    if not HAS_MPL:
        return

    # 按物体分组，每组选一个F和一个E的trial
    f_trials = {}
    e_trials = {}
    for t in trials:
        if t["mode"] == "F" and t["object"] in OBJECT_ORDER and len(t["csv_rows"]) > 100:
            if t["object"] not in f_trials:
                f_trials[t["object"]] = t
        if t["mode"] == "E" and t["object"] in OBJECT_ORDER and len(t["csv_rows"]) > 100:
            if t["object"] not in e_trials:
                e_trials[t["object"]] = t

    common_objects = [o for o in OBJECT_ORDER if o in f_trials and o in e_trials]
    if not common_objects:
        print("  ⚠️  图6: 缺少F或E模式数据，跳过")
        return

    fig, axes = plt.subplots(len(common_objects), 1, figsize=(12, 4 * len(common_objects)))

    if len(common_objects) == 1:
        axes = [axes]

    for idx, obj in enumerate(common_objects):
        ax = axes[idx]

        f_rows = f_trials[obj]["csv_rows"]
        e_rows = e_trials[obj]["csv_rows"]

        f_t = [r["time"] for r in f_rows]
        f_F = [r["F_ext_mag"] for r in f_rows]

        e_t = [r["time"] for r in e_rows]
        e_F = [r["F_ext_mag"] for r in e_rows]

        ax.plot(f_t, f_F, label="F 融合方法", color="#2ECC71", linewidth=1.2)
        ax.plot(e_t, e_F, label="E 力反馈自适应", color="#E74C3C", linewidth=1.0, alpha=0.8)
        ax.axhline(y=F_SAT_LINE, color="gray", linestyle=":", alpha=0.5)

        ax.set_xlabel("时间 (s)", fontsize=11)
        ax.set_ylabel("|F_ext| (N)", fontsize=11)
        ax.set_title(f"F vs E — {OBJECT_NAMES[obj]}", fontsize=12)
        ax.legend(fontsize=10)
        ax.grid(alpha=0.3)

    fig.suptitle("图6: 融合模式(F) vs 力反馈自适应模式(E) 外力时序对比",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_dir / "fig6_force_timeline_comparison.pdf", dpi=150)
    plt.savefig(output_dir / "fig6_force_timeline_comparison.png", dpi=150)
    plt.close()
    print(f"  ✅ 图6: {output_dir}/fig6_force_timeline_comparison.pdf")


# ═══════════════════════════════════════════════════════════════════
# 图7: 刚度-力散点图
# ═══════════════════════════════════════════════════════════════════

def plot_stiffness_force_scatter(trials: List[dict], output_dir: Path):
    """图7: K_trans vs F_ext_mag 散点图（每模式不同颜色）"""
    if not HAS_MPL:
        return

    fig, axes = plt.subplots(1, 3, figsize=(14, 5))

    for idx, obj in enumerate(OBJECT_ORDER):
        ax = axes[idx]

        for mode in MODE_ORDER:
            # 找该模式+物体的第一个trial
            trial = None
            for t in trials:
                if t["mode"] == mode and t["object"] == obj and len(t["csv_rows"]) > 50:
                    trial = t
                    break
            if trial is None:
                continue

            rows = trial["csv_rows"]
            # 降采样（最多取2000个点）
            step = max(1, len(rows) // 2000)
            sampled = rows[::step]

            kts = [r["K_trans"] for r in sampled]
            f_exts = [r["F_ext_mag"] for r in sampled]

            ax.scatter(kts, f_exts, s=1, alpha=0.3, color=MODE_COLORS[mode],
                       label=MODE_NAMES[mode] if idx == 2 else "")

        ax.set_xlabel("K_trans (N/m)", fontsize=11)
        ax.set_ylabel("|F_ext| (N)" if idx == 0 else "", fontsize=11)
        ax.set_title(OBJECT_NAMES[obj], fontsize=12)
        ax.grid(alpha=0.3)
        if idx == 2:
            ax.legend(fontsize=8, markerscale=5)

    fig.suptitle("图7: 刚度-外力散点图", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_dir / "fig7_stiffness_force_scatter.pdf", dpi=150)
    plt.savefig(output_dir / "fig7_stiffness_force_scatter.png", dpi=150)
    plt.close()
    print(f"  ✅ 图7: {output_dir}/fig7_stiffness_force_scatter.pdf")


# ═══════════════════════════════════════════════════════════════════
# 图8: 外力分布直方图
# ═══════════════════════════════════════════════════════════════════

def plot_force_distribution(trials: List[dict], output_dir: Path):
    """图8: 外力分布直方图"""
    if not HAS_MPL:
        return

    fig, axes = plt.subplots(1, 3, figsize=(14, 5))

    for idx, obj in enumerate(OBJECT_ORDER):
        ax = axes[idx]

        for mode in MODE_ORDER:
            all_f = []
            for t in trials:
                if t["mode"] == mode and t["object"] == obj:
                    all_f.extend([r["F_ext_mag"] for r in t["csv_rows"]])
            if all_f:
                ax.hist(all_f, bins=50, alpha=0.35, color=MODE_COLORS[mode],
                        label=MODE_NAMES[mode], density=True)

        ax.axvline(x=F_SAT_LINE, color="gray", linestyle=":", alpha=0.5)
        ax.set_xlabel("|F_ext| (N)", fontsize=11)
        ax.set_ylabel("密度" if idx == 0 else "", fontsize=11)
        ax.set_title(OBJECT_NAMES[obj], fontsize=12)
        ax.set_xlim(0, max(8, F_SAT_LINE + 3))
        ax.grid(alpha=0.3)
        if idx == 2:
            ax.legend(fontsize=8)

    fig.suptitle("图8: 末端外力分布对比", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_dir / "fig8_force_distribution.pdf", dpi=150)
    plt.savefig(output_dir / "fig8_force_distribution.png", dpi=150)
    plt.close()
    print(f"  ✅ 图8: {output_dir}/fig8_force_distribution.pdf")


# ═══════════════════════════════════════════════════════════════════
# LaTeX 表格生成
# ═══════════════════════════════════════════════════════════════════

def generate_latex_tables(summary: dict, output_dir: Path):
    """生成论文LaTeX表格"""
    lines = [
        "% RAL论文结果表格 — 由 ral_paper_plots.py 自动生成",
        "",
    ]

    # 表2: 完成时间 + 外力峰值 + 成功率 汇总表
    lines.append("% === 表2: 主要指标汇总 ===")
    lines.append("\\begin{table}[t]")
    lines.append("\\centering")
    lines.append("\\caption{六模式实验结果汇总}")
    lines.append("\\label{tab:results}")
    lines.append("\\begin{tabular}{lccccc}")
    lines.append("\\toprule")
    lines.append("模式 & 物体 & 完成时间(s) & |F_ext|峰值(N) & 成功率(\\%) \\\\")
    lines.append("\\midrule")

    for mode in MODE_ORDER:
        mode_first = True
        for obj in OBJECT_ORDER:
            key = (mode, obj)
            s = summary.get(key, {})
            dt = f"{s.get('duration_mean', 0):.1f}$\\pm${s.get('duration_std', 0):.1f}"
            fp = f"{s.get('F_ext_peak_mean', 0):.2f}$\\pm${s.get('F_ext_peak_std', 0):.2f}"
            sr = f"{s.get('success_rate', 0):.0f}"
            mode_cell = f"\\multirow{{3}}{{*}}{{{MODE_NAMES[mode]}}}" if mode_first else ""
            mode_first = False
            lines.append(f"{mode_cell} & {OBJECT_NAMES_EN[obj]} & {dt} & {fp} & {sr}\\\\")
        if mode != MODE_ORDER[-1]:
            lines.append("\\midrule")

    lines.extend([
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table}",
        "",
    ])

    # 表3: NASA-TLX 汇总
    mode_tlx = defaultdict(list)
    for t in trials:
        mode_tlx[t["mode"]].append(t["metrics"]["nasa_tlx"])

    lines.append("% === 表3: NASA-TLX ===")
    lines.append("\\begin{table}[t]")
    lines.append("\\centering")
    lines.append("\\caption{NASA-TLX 主观工作负荷 (0-100, 越低越好)}")
    lines.append("\\label{tab:tlx}")
    lines.append("\\begin{tabular}{lcccc}")
    lines.append("\\toprule")
    lines.append("模式 & 均值 & 标准差 & 最小值 & 最大值 \\\\")
    lines.append("\\midrule")
    for mode in MODE_ORDER:
        if mode in mode_tlx:
            vals = mode_tlx[mode]
            m = statistics.mean(vals)
            s = statistics.stdev(vals) if len(vals) > 1 else 0
            mn = min(vals)
            mx = max(vals)
            lines.append(f"{MODE_NAMES[mode]} & {m:.1f} & {s:.1f} & {mn:.0f} & {mx:.0f} \\\\")
    lines.extend([
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table}",
    ])

    tex_path = output_dir / "table_results.tex"
    with open(tex_path, "w") as f:
        f.write("\n".join(lines))
    print(f"  ✅ LaTeX表格: {tex_path}")


# ═══════════════════════════════════════════════════════════════════
# 统计检验
# ═══════════════════════════════════════════════════════════════════

def run_statistics(trials: List[dict], summary: dict, output_dir: Path):
    """执行统计检验"""
    if not HAS_SCIPY:
        return

    lines = ["# 统计分析结果\n"]
    from datetime import datetime
    lines.append(f"生成时间: {datetime.now().isoformat()}\n")

    # 1. 完成时间 ANOVA-like 分析
    lines.append("## 完成时间分析\n")
    lines.append(f"{'模式':<10} {'均值(s)':<12} {'标准差':<10} {'n':<6}\n")
    lines.append(f"{'-'*40}\n")
    mode_durations = defaultdict(list)
    for t in trials:
        mode_durations[t["mode"]].append(t["metrics"]["duration_s"])
    for mode in MODE_ORDER:
        if mode in mode_durations:
            vals = mode_durations[mode]
            m = statistics.mean(vals)
            s = statistics.stdev(vals) if len(vals) > 1 else 0
            lines.append(f"{MODE_NAMES[mode]:<10} {m:<12.2f} {s:<10.2f} {len(vals):<6}\n")

    # Kruskal-Wallis 检验（多组非参数）
    groups = [mode_durations[m] for m in MODE_ORDER if m in mode_durations and len(mode_durations[m]) >= 2]
    if len(groups) >= 3:
        h_stat, p_val = scipy_stats.kruskal(*groups)
        lines.append(f"\nKruskal-Wallis H检验: H={h_stat:.4f}, p={p_val:.6f}\n")
        lines.append(f"{'✅ p<0.05 显著差异' if p_val < 0.05 else '❌ p≥0.05 无显著差异'}\n")

        # 事后 Mann-Whitney U 检验
        lines.append("\n### 事后两两比较 (Mann-Whitney U, Bonferroni校正)\n")
        modes_list = [m for m in MODE_ORDER if m in mode_durations and len(mode_durations[m]) >= 2]
        for i in range(len(modes_list)):
            for j in range(i+1, len(modes_list)):
                m1, m2 = modes_list[i], modes_list[j]
                u_stat, p_val = scipy_stats.mannwhitneyu(
                    mode_durations[m1], mode_durations[m2], alternative='two-sided')
                p_corrected = p_val * len(modes_list)  # Bonferroni
                sig = "✅" if p_corrected < 0.05 else "❌"
                lines.append(f"  {MODE_NAMES[m1]} vs {MODE_NAMES[m2]}: "
                             f"U={u_stat:.1f}, p_raw={p_val:.6f}, "
                             f"p_bonf={p_corrected:.6f} {sig}\n")

    # 2. 外力峰值分析
    lines.append("\n## 末端外力峰值分析\n")
    mode_peaks = defaultdict(list)
    for t in trials:
        mode_peaks[t["mode"]].append(t["metrics"]["F_ext_peak_N"])
    for mode in MODE_ORDER:
        if mode in mode_peaks:
            vals = mode_peaks[mode]
            m = statistics.mean(vals)
            s = statistics.stdev(vals) if len(vals) > 1 else 0
            lines.append(f"{MODE_NAMES[mode]:<10} {m:<12.3f} {s:<10.3f} {len(vals):<6}\n")

    groups = [mode_peaks[m] for m in MODE_ORDER if m in mode_peaks and len(mode_peaks[m]) >= 2]
    if len(groups) >= 3:
        h_stat, p_val = scipy_stats.kruskal(*groups)
        lines.append(f"\nKruskal-Wallis H检验: H={h_stat:.4f}, p={p_val:.6f}\n")
        lines.append(f"{'✅ p<0.05 显著差异' if p_val < 0.05 else '❌ p≥0.05 无显著差异'}\n")

    stats_path = output_dir / "statistics.txt"
    with open(stats_path, "w") as f:
        f.writelines(lines)
    print(f"  ✅ 统计结果: {stats_path}")


# ═══════════════════════════════════════════════════════════════════
# 主函数
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="RAL论文实验数据分析与出图")
    parser.add_argument("--data-dir", type=str, default="data/ral_experiment",
                        help="数据目录路径")
    parser.add_argument("--output", "-o", type=str, default="./paper_figures",
                        help="输出目录")
    parser.add_argument("--recursive", "-r", action="store_true",
                        help="递归搜索子目录")
    parser.add_argument("--no-plot", action="store_true",
                        help="跳过绘图")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n🔍 扫描数据目录: {data_dir}")
    trials = load_trials(data_dir, recursive=args.recursive)
    print(f"   共找到 {len(trials)} 个 trial")

    if not trials:
        print("❌ 未找到任何实验数据")
        sys.exit(1)

    # 打印数据概况
    mode_counts = defaultdict(int)
    obj_counts = defaultdict(int)
    for t in trials:
        mode_counts[t["mode"]] += 1
        obj_counts[t["object"]] += 1

    print(f"\n📊 数据概况:")
    print(f"  模式分布: {dict(mode_counts)}")
    print(f"  物体分布: {dict(obj_counts)}")
    print(f"  操作者: {set(t['operator'] for t in trials)}")

    # 生成汇总
    summary = build_summary(trials)

    print(f"\n📈 汇总统计:")
    for key in sorted(summary.keys()):
        s = summary[key]
        print(f"  {MODE_NAMES[s['mode']]:<12} {s['object']:<8} "
              f"n={s['n']:>2}  T={s['duration_mean']:>6.2f}s  "
              f"F_peak={s['F_ext_peak_mean']:>6.3f}N  "
              f"成功率={s['success_rate']:>5.1f}%")

    # 绘图
    if HAS_MPL and not args.no_plot:
        print("\n🎨 生成论文图表...")
        plot_completion_time(summary, output_dir)
        plot_force_peak(summary, output_dir)
        plot_fusion_process(trials, output_dir)
        plot_nasa_tlx(trials, output_dir)
        plot_success_rate(summary, output_dir)
        plot_force_comparison_timeline(trials, output_dir)
        plot_stiffness_force_scatter(trials, output_dir)
        plot_force_distribution(trials, output_dir)

    # LaTeX 表格
    print("\n📋 生成LaTeX表格...")
    generate_latex_tables(summary, output_dir)

    # 统计
    print("\n📐 执行统计分析...")
    run_statistics(trials, summary, output_dir)

    print(f"\n✅ 分析完成！所有输出在 {output_dir.resolve()}")
    print(f"   图表: {output_dir}/*.pdf")
    print(f"   表格: {output_dir}/table_results.tex")
    print(f"   统计: {output_dir}/statistics.txt")


if __name__ == "__main__":
    main()
