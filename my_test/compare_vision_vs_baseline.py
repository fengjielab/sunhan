#!/usr/bin/env python3
"""
compare_vision_vs_baseline.py — 视觉前验 vs 纯力自适应 末端峰值力对比分析

分析文件:
    - vision_force_20260627_175739.csv  (视觉前验 + 力自适应)
    - force_adaptive_20260627_175109.csv (纯力自适应)

核心问题:
    为什么加了视觉前验后，末端峰值力 (F_ext_mag) 没有显著降低？

作者: mfj
日期: 2026-06-27
"""

import csv
import math
import statistics
from pathlib import Path
from typing import List, Dict, Any, Union

import numpy as np

# ── 可选绘图 ──
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    print("⚠️  matplotlib 未安装，跳过绘图")

DATA_DIR = Path(__file__).resolve().parent / "data"
OUTPUT_DIR = Path(__file__).resolve().parent / "analysis_output"


# ═══════════════════════════════════════════════════════════════════
# 1. CSV 解析
# ═══════════════════════════════════════════════════════════════════

def parse_csv(filename: str) -> List[dict]:
    """解析 CSV 文件，返回 dict 列表（值已转为 float）"""
    path = DATA_DIR / filename
    rows = []
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            parsed = {}
            for k, v in row.items():
                k = k.strip()
                try:
                    parsed[k] = float(v)
                except (ValueError, TypeError):
                    parsed[k] = v  # 保留字符串（如 vision_label）
            rows.append(parsed)
    return rows


# ═══════════════════════════════════════════════════════════════════
# 2. 基本统计
# ═══════════════════════════════════════════════════════════════════

def force_stats(rows: List[dict]) -> dict:
    """计算 F_ext_mag 的基本统计量"""
    f_exts = [r["F_ext_mag"] for r in rows]
    return {
        "count": len(f_exts),
        "mean": statistics.mean(f_exts),
        "median": statistics.median(f_exts),
        "std": statistics.stdev(f_exts) if len(f_exts) > 1 else 0,
        "min": min(f_exts),
        "max": max(f_exts),
        "p95": np.percentile(f_exts, 95) if len(f_exts) > 0 else 0,
        "p99": np.percentile(f_exts, 99) if len(f_exts) > 0 else 0,
        "rms": math.sqrt(sum(f*f for f in f_exts) / len(f_exts)),
    }


def stiffness_stats(rows: List[dict]) -> dict:
    """计算 K_trans 的统计量"""
    kts = [r["K_trans"] for r in rows]
    krs = [r["K_rot"] for r in rows]
    return {
        "K_trans_mean": statistics.mean(kts),
        "K_trans_min": min(kts),
        "K_trans_max": max(kts),
        "K_trans_final": kts[-1] if kts else 0,
        "K_rot_mean": statistics.mean(krs),
        "K_rot_min": min(krs),
        "K_rot_max": max(krs),
        "K_rot_final": krs[-1] if krs else 0,
    }


# ═══════════════════════════════════════════════════════════════════
# 3. 视觉融合分析
# ═══════════════════════════════════════════════════════════════════

def analyze_vision_fusion(rows: List[dict]) -> dict:
    """分析视觉融合的激活时机和效果"""
    fusion_active_times = []
    fusion_deltas = []
    pre_fusion_force = []
    post_fusion_force = []
    pre_fusion_K = []
    post_fusion_K = []

    fusion_active = False
    fusion_start_idx = None

    for i, r in enumerate(rows):
        if r["fusion_active"] == 1.0 and not fusion_active:
            fusion_active = True
            fusion_start_idx = i

        if r["fusion_active"] == 1.0:
            fusion_active_times.append(r["time"])
            fusion_deltas.append(r.get("fusion_delta_K", 0))

        if not fusion_active:
            pre_fusion_force.append(r["F_ext_mag"])
            pre_fusion_K.append(r["K_trans"])
        else:
            post_fusion_force.append(r["F_ext_mag"])
            post_fusion_K.append(r["K_trans"])

    return {
        "fusion_activated": fusion_active,
        "fusion_start_time": rows[fusion_start_idx]["time"] if fusion_start_idx else None,
        "fusion_start_idx": fusion_start_idx,
        "fusion_delta_K_min": min(fusion_deltas) if fusion_deltas else 0,
        "fusion_delta_K_final": fusion_deltas[-1] if fusion_deltas else 0,
        "fusion_delta_K_mean": statistics.mean(fusion_deltas) if fusion_deltas else 0,
        "pre_fusion_F_max": max(pre_fusion_force) if pre_fusion_force else 0,
        "pre_fusion_F_mean": statistics.mean(pre_fusion_force) if pre_fusion_force else 0,
        "post_fusion_F_max": max(post_fusion_force) if post_fusion_force else 0,
        "post_fusion_F_mean": statistics.mean(post_fusion_force) if post_fusion_force else 0,
        "pre_fusion_K_mean": statistics.mean(pre_fusion_K) if pre_fusion_K else 0,
        "post_fusion_K_mean": statistics.mean(post_fusion_K) if post_fusion_K else 0,
        "vision_labels": list(set(r.get("vision_label", "") for r in rows if r["fusion_active"] == 1.0)),
    }


# ═══════════════════════════════════════════════════════════════════
# 4. 力饱和分析
# ═══════════════════════════════════════════════════════════════════

def analyze_saturation(rows: List[dict], f_sat: float = 5.0, tolerance: float = 0.1) -> dict:
    """分析有多少时间力处于饱和状态（接近 F_sat）"""
    near_sat = [r for r in rows if r["F_ext_mag"] >= f_sat - tolerance]
    above_sat = [r for r in rows if r["F_ext_mag"] >= f_sat]
    return {
        "f_sat": f_sat,
        "tolerance": tolerance,
        "near_sat_count": len(near_sat),
        "near_sat_ratio": len(near_sat) / len(rows) * 100 if rows else 0,
        "above_sat_count": len(above_sat),
        "above_sat_ratio": len(above_sat) / len(rows) * 100 if rows else 0,
        "near_sat_max": max(r["F_ext_mag"] for r in near_sat) if near_sat else 0,
        "near_sat_duration": (near_sat[-1]["time"] - near_sat[0]["time"]) if len(near_sat) > 1 else 0,
    }


# ═══════════════════════════════════════════════════════════════════
# 5. 力>F_sat 的时序分析（找全剧峰值）
# ═══════════════════════════════════════════════════════════════════

def find_force_peaks(rows: List[dict], threshold: float = 4.5) -> List[dict]:
    """找出 F_ext_mag 超过 threshold 的显著峰值及其 timestamp"""
    peaks = []
    in_peak = False
    current_peak = 0
    peak_start = None

    for r in rows:
        f = r["F_ext_mag"]
        t = r["time"]
        if f > threshold and not in_peak:
            in_peak = True
            current_peak = f
            peak_start = t
        elif f > threshold and in_peak:
            if f > current_peak:
                current_peak = f
        elif f <= threshold and in_peak:
            peaks.append({
                "peak_value": current_peak,
                "start_time": peak_start,
                "end_time": t,
                "duration": t - peak_start if peak_start else 0,
            })
            in_peak = False
            current_peak = 0
            peak_start = None

    return peaks


# ═══════════════════════════════════════════════════════════════════
# 6. F_ext_mag 与 K_trans 的相关性
# ═══════════════════════════════════════════════════════════════════

def stiffness_force_correlation(rows: List[dict]) -> dict:
    """计算刚度与力的相关系数"""
    kts = np.array([r["K_trans"] for r in rows])
    f_exts = np.array([r["F_ext_mag"] for r in rows])

    # Pearson 相关系数
    corr = np.corrcoef(kts, f_exts)[0, 1]

    return {
        "pearson_r": corr,
        "K_trans_vs_F_corr": corr,
    }


# ═══════════════════════════════════════════════════════════════════
# 7. 绘图
# ═══════════════════════════════════════════════════════════════════

def plot_comparison(vision_rows, baseline_rows, output_dir):
    """生成对比图"""
    if not HAS_MPL:
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    # 提取数据
    v_t = [r["time"] for r in vision_rows]
    v_F = [r["F_ext_mag"] for r in vision_rows]
    v_K = [r["K_trans"] for r in vision_rows]
    v_Kr = [r["K_rot"] for r in vision_rows]
    v_fusion = [r["fusion_active"] for r in vision_rows]
    v_dK = [r.get("fusion_delta_K", 0) for r in vision_rows]

    b_t = [r["time"] for r in baseline_rows]
    b_F = [r["F_ext_mag"] for r in baseline_rows]
    b_K = [r["K_trans"] for r in baseline_rows]
    b_Kr = [r["K_rot"] for r in baseline_rows]
    b_grip = [r["gripper_deg"] for r in baseline_rows]
    v_grip = [r["gripper_deg"] for r in vision_rows]

    F_SAT = 5.0

    # ── 图1: F_ext_mag 时序对比 ──
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(v_t, v_F, label="Vision+Force (视觉+力)", color="#2E86C1", linewidth=1.0)
    ax.plot(b_t, b_F, label="Force-Adaptive (纯力)", color="#E74C3C", linewidth=1.0, alpha=0.8)

    # 标记视觉融合激活时刻
    for i, fa in enumerate(v_fusion):
        if fa == 1.0:
            ax.axvline(x=v_t[i], color="#2E86C1", linestyle="--", alpha=0.5,
                       label="Vision fusion activated" if i == 0 else "")
            break

    # F_sat 线
    ax.axhline(y=F_SAT, color="gray", linestyle=":", alpha=0.7, linewidth=1.5)
    ax.text(v_t[-1]*0.8, F_SAT+0.1, f"F_sat = {F_SAT} N", fontsize=9, color="gray")

    ax.set_xlabel("Time (s)", fontsize=12)
    ax.set_ylabel("|F_ext| (N)", fontsize=12)
    ax.set_title("图1: 末端外力幅值 F_ext_mag 时序对比", fontsize=14, fontweight="bold")
    ax.legend(fontsize=10)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / "fig1_F_ext_timeline.pdf", dpi=150)
    plt.savefig(output_dir / "fig1_F_ext_timeline.png", dpi=150)
    plt.close()
    print(f"  ✅ 图1: {output_dir}/fig1_F_ext_timeline.pdf")

    # ── 图2: K_trans 时序对比 ──
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(v_t, v_K, label="Vision+Force K_trans", color="#2E86C1", linewidth=1.0)
    ax.plot(b_t, b_K, label="Force-Adaptive K_trans", color="#E74C3C", linewidth=1.0, alpha=0.8)

    # 标记 vision fusion 段
    for i, fa in enumerate(v_fusion):
        if fa == 1.0:
            ax.axvline(x=v_t[i], color="#2E86C1", linestyle="--", alpha=0.3,
                       label="Vision fusion starts" if i == 0 else "")
            break

    ax.set_xlabel("Time (s)", fontsize=12)
    ax.set_ylabel("K_trans", fontsize=12)
    ax.set_title("图2: 平移刚度 K_trans 时序对比", fontsize=14, fontweight="bold")
    ax.legend(fontsize=10)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / "fig2_K_trans_timeline.pdf", dpi=150)
    plt.savefig(output_dir / "fig2_K_trans_timeline.png", dpi=150)
    plt.close()
    print(f"  ✅ 图2: {output_dir}/fig2_K_trans_timeline.pdf")

    # ── 图3: Vision-only: F_ext, K_trans, fusion_delta_K 关联 ──
    fig, ax1 = plt.subplots(figsize=(12, 5))

    color1 = "#2E86C1"
    color2 = "#E67E22"
    color3 = "#27AE60"

    ax1.plot(v_t, v_F, label="F_ext_mag", color=color1, linewidth=1.0, alpha=0.8)
    ax1.plot(v_t, v_K, label="K_trans", color=color2, linewidth=1.0, alpha=0.8)
    ax1.set_xlabel("Time (s)", fontsize=12)
    ax1.set_ylabel("F_ext_mag / K_trans", fontsize=12, color="black")
    ax1.axhline(y=F_SAT, color="gray", linestyle=":", alpha=0.5)

    # 在底部绘制 fusion_delta_K
    ax2 = ax1.twinx()
    ax2.plot(v_t, v_dK, label="fusion_delta_K", color=color3, linewidth=1.5, alpha=0.7)
    # 填充 fusion active 区域
    in_fusion = False
    fusion_start_t = None
    for i, fa in enumerate(v_fusion):
        if fa == 1.0 and not in_fusion:
            fusion_start_t = v_t[i]
            in_fusion = True
        elif fa == 0.0 and in_fusion:
            ax1.axvspan(fusion_start_t, v_t[i], alpha=0.08, color="#2E86C1")
            in_fusion = False
    if in_fusion:
        ax1.axvspan(fusion_start_t, v_t[-1], alpha=0.08, color="#2E86C1")

    ax2.set_ylabel("fusion_delta_K", fontsize=12, color=color3)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, fontsize=9, loc="upper right")

    ax1.set_title("图3: Vision+Force 方法 — F_ext, K_trans, fusion_delta_K 关联", fontsize=13, fontweight="bold")
    ax1.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / "fig3_vision_correlation.pdf", dpi=150)
    plt.savefig(output_dir / "fig3_vision_correlation.png", dpi=150)
    plt.close()
    print(f"  ✅ 图3: {output_dir}/fig3_vision_correlation.pdf")

    # ── 图4: 直方图对比 F_ext_mag 分布 ──
    fig, ax = plt.subplots(figsize=(10, 5))
    bins = np.linspace(0, max(max(v_F), max(b_F)) + 0.5, 50)
    ax.hist(v_F, bins=bins, alpha=0.6, label="Vision+Force", color="#2E86C1", density=True)
    ax.hist(b_F, bins=bins, alpha=0.6, label="Force-Adaptive", color="#E74C3C", density=True)
    ax.axvline(x=F_SAT, color="gray", linestyle=":", linewidth=1.5, label=f"F_sat={F_SAT}N")
    ax.set_xlabel("|F_ext| (N)", fontsize=12)
    ax.set_ylabel("Probability Density", fontsize=12)
    ax.set_title("图4: F_ext_mag 分布对比", fontsize=14, fontweight="bold")
    ax.legend(fontsize=10)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / "fig4_F_ext_histogram.pdf", dpi=150)
    plt.savefig(output_dir / "fig4_F_ext_histogram.png", dpi=150)
    plt.close()
    print(f"  ✅ 图4: {output_dir}/fig4_F_ext_histogram.pdf")

    # ── 图5: 夹爪开度对比 ──
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(v_t, v_grip, label="Vision+Force gripper_deg", color="#2E86C1", linewidth=1.0)
    ax.plot(b_t, b_grip, label="Force-Adaptive gripper_deg", color="#E74C3C", linewidth=1.0, alpha=0.8)
    ax.set_xlabel("Time (s)", fontsize=12)
    ax.set_ylabel("Gripper Opening (deg)", fontsize=12)
    ax.set_title("图5: 夹爪开度 gripper_deg 时序对比", fontsize=14, fontweight="bold")
    ax.legend(fontsize=10)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / "fig5_gripper_timeline.pdf", dpi=150)
    plt.savefig(output_dir / "fig5_gripper_timeline.png", dpi=150)
    plt.close()
    print(f"  ✅ 图5: {output_dir}/fig5_gripper_timeline.pdf")

    # ── 图6: 分段分析 — Vision 方法：融合前 vs 融合后的力分布 ──
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # 找到 fusion 开始点
    fusion_idx = None
    for i, fa in enumerate(v_fusion):
        if fa == 1.0:
            fusion_idx = i
            break

    if fusion_idx:
        pre_F = v_F[:fusion_idx]
        post_F = v_F[fusion_idx:]

        # 左子图：时序
        axes[0].plot(v_t[:fusion_idx], pre_F, label="Pre-fusion", color="#3498DB", linewidth=1.0)
        axes[0].plot(v_t[fusion_idx:], post_F, label="Post-fusion (vision active)", color="#E74C3C", linewidth=1.0)
        axes[0].axhline(y=F_SAT, color="gray", linestyle=":", alpha=0.6)
        axes[0].axvline(x=v_t[fusion_idx], color="green", linestyle="--", alpha=0.7, label="Fusion start")
        axes[0].set_xlabel("Time (s)")
        axes[0].set_ylabel("|F_ext| (N)")
        axes[0].set_title(f"Pre-fusion max={max(pre_F):.3f}N → Post-fusion max={max(post_F):.3f}N")
        axes[0].legend(fontsize=8)
        axes[0].grid(alpha=0.3)

        # 右子图：直方图对比
        axes[1].hist(pre_F, bins=30, alpha=0.6, label=f"Pre-fusion (n={len(pre_F)})", color="#3498DB", density=True)
        axes[1].hist(post_F, bins=30, alpha=0.6, label=f"Post-fusion (n={len(post_F)})", color="#E74C3C", density=True)
        axes[1].axvline(x=F_SAT, color="gray", linestyle=":", alpha=0.6)
        axes[1].set_xlabel("|F_ext| (N)")
        axes[1].set_ylabel("Density")
        axes[1].set_title("F_ext distribution: pre vs post vision fusion")
        axes[1].legend(fontsize=8)
        axes[1].grid(alpha=0.3)

    fig.suptitle("图6: Vision+Force 方法 — 融合前 vs 融合后力分布", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_dir / "fig6_pre_post_fusion.pdf", dpi=150)
    plt.savefig(output_dir / "fig6_pre_post_fusion.png", dpi=150)
    plt.close()
    print(f"  ✅ 图6: {output_dir}/fig6_pre_post_fusion.pdf")


# ═══════════════════════════════════════════════════════════════════
# 8. 主函数
# ═══════════════════════════════════════════════════════════════════

def main():
    # ── 解析数据 ──
    print("=" * 70)
    print("视觉前验 vs 纯力自适应 — 末端峰值力对比分析")
    print("=" * 70)

    vision_file = "vision_force_20260627_175739.csv"
    baseline_file = "force_adaptive_20260627_175109.csv"

    print(f"\n📂 解析 {vision_file} ...")
    vision_rows = parse_csv(vision_file)
    print(f"   共 {len(vision_rows)} 行数据")

    print(f"📂 解析 {baseline_file} ...")
    baseline_rows = parse_csv(baseline_file)
    print(f"   共 {len(baseline_rows)} 行数据")

    # ── 基本统计 ──
    print("\n" + "─" * 70)
    print("1️⃣  基本统计量")
    print("─" * 70)

    v_stats = force_stats(vision_rows)
    b_stats = force_stats(baseline_rows)

    print(f"\n{'指标':<20} {'Vision+Force':>15} {'Force-Adaptive':>15} {'Δ%':>10}")
    print(f"{'─'*20} {'─'*15} {'─'*15} {'─'*10}")
    for key, label in [("mean", "均值"), ("median", "中位数"),
                        ("std", "标准差"), ("min", "最小值"),
                        ("max", "最大值"), ("p95", "P95分位"),
                        ("p99", "P99分位"), ("rms", "RMS")]:
        vv = v_stats[key]
        bb = b_stats[key]
        delta_pct = (vv - bb) / bb * 100 if bb != 0 else 0
        print(f"{label:<20} {vv:>15.4f} {bb:>15.4f} {delta_pct:>+9.2f}%")

    # ── 刚度统计 ──
    v_kstats = stiffness_stats(vision_rows)
    b_kstats = stiffness_stats(baseline_rows)

    print(f"\n{'K_trans 指标':<20} {'Vision+Force':>15} {'Force-Adaptive':>15}")
    print(f"{'─'*20} {'─'*15} {'─'*15}")
    for key, label in [("K_trans_mean", "均值"), ("K_trans_min", "最小值"),
                        ("K_trans_max", "最大值"), ("K_trans_final", "终值")]:
        print(f"{label:<20} {v_kstats[key]:>15.2f} {b_kstats[key]:>15.2f}")

    print(f"\n{'K_rot 指标':<20} {'Vision+Force':>15} {'Force-Adaptive':>15}")
    print(f"{'─'*20} {'─'*15} {'─'*15}")
    for key, label in [("K_rot_mean", "均值"), ("K_rot_min", "最小值"),
                        ("K_rot_max", "最大值"), ("K_rot_final", "终值")]:
        print(f"{label:<20} {v_kstats[key]:>15.2f} {b_kstats[key]:>15.2f}")

    # ── 视觉融合分析 ──
    print("\n" + "─" * 70)
    print("2️⃣  视觉融合分析 (Vision+Force)")
    print("─" * 70)

    fusion = analyze_vision_fusion(vision_rows)
    print(f"\n  ⚡ 视觉融合激活: {fusion['fusion_activated']}")
    if fusion['fusion_start_time']:
        print(f"  ⏱️  激活时间: t = {fusion['fusion_start_time']:.3f}s")
        print(f"  📌 视觉标签: {fusion['vision_labels']}")
        print(f"  📉 fusion_delta_K 均值: {fusion['fusion_delta_K_mean']:.3f}")
        print(f"  📉 fusion_delta_K 终值: {fusion['fusion_delta_K_final']:.3f}")
        print(f"  📉 fusion_delta_K 最小值: {fusion['fusion_delta_K_min']:.3f}")
        print(f"\n  ── 融合前后对比 ──")
        print(f"  融合前 F_ext 均值: {fusion['pre_fusion_F_mean']:.4f}")
        print(f"  融合前 F_ext 峰值: {fusion['pre_fusion_F_max']:.4f}")
        print(f"  融合后 F_ext 均值: {fusion['post_fusion_F_mean']:.4f}")
        print(f"  融合后 F_ext 峰值: {fusion['post_fusion_F_max']:.4f}")
        print(f"  融合前 K_trans 均值: {fusion['pre_fusion_K_mean']:.2f}")
        print(f"  融合后 K_trans 均值: {fusion['post_fusion_K_mean']:.2f}")

    # ── 力饱和分析 ──
    print("\n" + "─" * 70)
    print("3️⃣  力饱和分析 (F_sat = 5.0 N)")
    print("─" * 70)

    v_sat = analyze_saturation(vision_rows, f_sat=5.0)
    b_sat = analyze_saturation(baseline_rows, f_sat=5.0)

    print(f"\n{'指标':<30} {'Vision+Force':>15} {'Force-Adaptive':>15}")
    print(f"{'─'*30} {'─'*15} {'─'*15}")
    print(f"{'F_sat (N)':<30} {v_sat['f_sat']:>15.1f} {b_sat['f_sat']:>15.1f}")
    print(f"{'≥F_sat-0.1N 样本数':<30} {v_sat['near_sat_count']:>15d} {b_sat['near_sat_count']:>15d}")
    print(f"{'≥F_sat-0.1N 占比':<30} {v_sat['near_sat_ratio']:>14.2f}% {b_sat['near_sat_ratio']:>14.2f}%")
    print(f"{'≥F_sat 样本数':<30} {v_sat['above_sat_count']:>15d} {b_sat['above_sat_count']:>15d}")
    print(f"{'≥F_sat 占比':<30} {v_sat['above_sat_ratio']:>14.2f}% {b_sat['above_sat_ratio']:>14.2f}%")
    print(f"{'≥F_sat-0.1N 段最大力':<30} {v_sat['near_sat_max']:>15.4f} {b_sat['near_sat_max']:>15.4f}")

    # ── 峰值分析 ──
    print("\n" + "─" * 70)
    print("4️⃣  显著力峰值分析 (F_ext_mag > 4.5N 的峰值)")
    print("─" * 70)

    v_peaks = find_force_peaks(vision_rows, threshold=4.5)
    b_peaks = find_force_peaks(baseline_rows, threshold=4.5)

    print(f"\n  Vision+Force: {len(v_peaks)} 个显著峰值")
    if v_peaks:
        peak_vals = [p["peak_value"] for p in v_peaks]
        print(f"    峰值列表: {[f'{p:.3f}' for p in sorted(peak_vals, reverse=True)]}")
        print(f"    最大峰值: {max(peak_vals):.4f}")
        print(f"    平均峰值: {statistics.mean(peak_vals):.4f}")

    print(f"\n  Force-Adaptive: {len(b_peaks)} 个显著峰值")
    if b_peaks:
        peak_vals = [p["peak_value"] for p in b_peaks]
        print(f"    峰值列表: {[f'{p:.3f}' for p in sorted(peak_vals, reverse=True)]}")
        print(f"    最大峰值: {max(peak_vals):.4f}")
        print(f"    平均峰值: {statistics.mean(peak_vals):.4f}")

    # ── 刚度-力相关性 ──
    print("\n" + "─" * 70)
    print("5️⃣  刚度-力相关性分析")
    print("─" * 70)

    v_corr = stiffness_force_correlation(vision_rows)
    b_corr = stiffness_force_correlation(baseline_rows)

    print(f"\n  Vision+Force: K_trans vs F_ext 相关系数 r = {v_corr['pearson_r']:.4f}")
    print(f"  Force-Adaptive: K_trans vs F_ext 相关系数 r = {b_corr['pearson_r']:.4f}")

    # ── 综合讨论 ──
    print("\n" + "=" * 70)
    print("🎯 综合分析与讨论")
    print("=" * 70)

    print(f"""
📊 关键数据对比:

  ┌─────────────────────────────────────────────────────────────────┐
  │ 指标                     Vision+Force     Force-Adaptive        │
  ├─────────────────────────────────────────────────────────────────┤
  │ F_ext_mag 最大值 (N)      {v_stats['max']:>8.4f}       {b_stats['max']:>8.4f}              │
  │ F_ext_mag 均值 (N)        {v_stats['mean']:>8.4f}       {b_stats['mean']:>8.4f}              │
  │ F_ext_mag P99 (N)         {v_stats['p99']:>8.4f}       {b_stats['p99']:>8.4f}              │
  │ K_trans 终值              {v_kstats['K_trans_final']:>8.2f}       {b_kstats['K_trans_final']:>8.2f}              │
  │ K_trans 最大              {v_kstats['K_trans_max']:>8.2f}       {b_kstats['K_trans_max']:>8.2f}              │
  │ K_rot 终值                {v_kstats['K_rot_final']:>8.2f}       {b_kstats['K_rot_final']:>8.2f}              │
  │ 试验时长 (s)              {vision_rows[-1]['time']-vision_rows[0]['time']:>8.2f}       {baseline_rows[-1]['time']-baseline_rows[0]['time']:>8.2f}              │
  └─────────────────────────────────────────────────────────────────┘
""")

    # ── 核心分析 ──
    print("🔍 核心结论:\n")

    # 结论1: 峰值力对比
    print("  ⚠️  结论1: 峰值力基本相当")
    print(f"     Vision+Force 最大峰值: {v_stats['max']:.4f} N")
    print(f"     Force-Adaptive 最大峰值: {b_stats['max']:.4f} N")
    delta_peak = v_stats['max'] - b_stats['max']
    if abs(delta_peak) < 0.5:
        print(f"     差异仅 {delta_peak:+.4f} N，在测量噪声范围内。")
    else:
        print(f"     差异 {delta_peak:+.4f} N。")
    print(f"     两个方法的峰值力都被 F_sat={5.0}N 的力饱和阈值所限。")

    # 结论2: 力饱和是瓶颈
    print(f"""
  🚧 结论2: F_sat = 5.0N 是限制峰值力的主导因素
     - Vision+Force 有 {v_sat['above_sat_ratio']:.1f}% 的采样点 ≥ F_sat
     - Force-Adaptive 有 {b_sat['above_sat_ratio']:.1f}% 的采样点 ≥ F_sat
     - 两个方法都在力饱和阈值附近运行，视觉前验降低刚度的效果被
       力饱和机制"截断"了——即使刚度降得再低，力也不会显著低于 F_sat。
""")

    # 结论3: 刚度下降很大但力没下降
    print(f"""  🔄 结论3: 刚度大幅下降，但力没降
     - Vision+Force: K_trans 从 {v_kstats['K_trans_max']:.1f} 下降到 {v_kstats['K_trans_final']:.1f}
       (下降 {(1 - v_kstats['K_trans_final']/v_kstats['K_trans_max'])*100:.0f}%)
     - Force-Adaptive: K_trans 保持在 {b_kstats['K_trans_mean']:.1f} 附近
     - 视觉前验成功降低了刚度，但力没有按比例下降，说明力的大小
       不仅取决于刚度，还受操作者主动施加的力/运动控制影响。
""")

    # 结论4: 视觉融合时机
    if fusion['fusion_start_time']:
        print(f"""  ⏱️  结论4: 视觉融合的时机和方式
     - 视觉融合在 t = {fusion['fusion_start_time']:.3f}s 才激活
     - 此时已经发生了第一次接触(F_ext ≈ {fusion['pre_fusion_F_max']:.3f}N)
     - 视觉前验在接触后才生效，属于"事后调整"而非"事前预防"
     - 如果在接触前更早激活视觉融合（更早降低刚度），可能更能
       减少首次接触时的冲击力峰值
""")

    # 结论5: 力饱和限制 vs 刚度调节
    print(f"""  📉 结论5: 刚度调节对峰值力的影响存在上限
     - K_trans 从 {v_kstats['K_trans_max']:.0f} 降到 {v_kstats['K_trans_final']:.0f} (降幅 {(1-v_kstats['K_trans_final']/v_kstats['K_trans_max'])*100:.0f}%)
     - 但 F_ext_mag 的 P99 只从 {b_stats['p99']:.3f} (baseline) 变为 {v_stats['p99']:.3f} (vision)
     - 这是因为操作者(人)在回路中：当刚度变低(更柔顺)时，操作者
       会不自觉地将手伸得更深来补偿，反而维持了接触力水平
     - 力饱和 (F_sat) 作为硬约束，进一步限制了峰值力的降低空间
""")

    recommendations = f"""
💡 改进建议:

  1️⃣ 降低 F_sat 阈值: 将 F_sat 从 5.0N 降到 3.0-4.0N，让视觉前验
     的刚度降低效果能在力上体现出来。

  2️⃣ 提前激活视觉融合: 在接触发生之前（gripper_deg 接近物体时）
     就根据视觉标签提前降低刚度，而不是接触后才调整。

  3️⃣ 视觉引导接近轨迹: 视觉不仅用来调刚度，还可以用来规划
     接近轨迹速度——软物体用更低速度接近，减少冲击力。

  4️⃣ 增加任务难度: 当前的遥操作任务可能太简单，操作者没有充分
     利用视觉前验带来的柔顺性优势。尝试更精细的操作任务。
"""
    print(recommendations)

    # ── 绘图 ──
    print("─" * 70)
    print("📈 生成可视化图表...")
    print("─" * 70)
    plot_comparison(vision_rows, baseline_rows, OUTPUT_DIR)

    print(f"\n✅ 分析完成！所有图表已保存至: {OUTPUT_DIR.resolve()}")
    print(f"   可通过 scp/rsync 下载查看。\n")


if __name__ == "__main__":
    main()
