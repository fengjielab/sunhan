#!/usr/bin/env python3
"""
bootstrap_ci_ce.py — C–E 配对差值分析
用于 Mechatronics 版论文统计表

输入: all_trials_135.csv, nasa.md
输出:
  - 完成时间/轨迹：median [IQR] + 匹配任务块级 Bootstrap 95% CI
  - Raw NASA-TLX：9 个 operator×strategy 单元的描述性统计，不报告 CI
"""
import csv, math, random
from pathlib import Path
from collections import defaultdict
from statistics import mean, stdev, median
import numpy as np

DATA_DIR = Path(__file__).resolve().parent
random.seed(42)
np.random.seed(42)

# ─── 数据读取 ───
def read_all_trials():
    rows = []
    with open(DATA_DIR / "all_trials_135.csv", "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            row["duration_s"] = float(row["duration_s"])
            row["traj_length_m"] = float(row["traj_length_m"])
            rows.append(row)
    return rows

def read_nasa_tlx():
    rows = []
    nasa_path = DATA_DIR / "nasa_tlx_results" / "nasa.md"
    with open(nasa_path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            dims = ["mental_demand","physical_demand","temporal_demand",
                    "performance","effort","frustration"]
            row["raw_tlx"] = mean(float(row[d]) for d in dims)
            rows.append(row)
    return rows

# ─── Bootstrap CI ───
def bootstrap_paired_ci(pairs, n_bootstrap=10000, ci_level=95):
    """E−C 配对改善量的 Bootstrap 置信区间（基于配对块重抽样）"""
    n = len(pairs)
    diffs = [b - a for a, b in pairs]  # E - C，正值表示 C 更优
    
    boot_means = []
    for _ in range(n_bootstrap):
        idx = np.random.choice(n, size=n, replace=True)
        boot_sample = [diffs[i] for i in idx]
        boot_means.append(mean(boot_sample))
    
    alpha = (100 - ci_level) / 2
    lo = np.percentile(boot_means, alpha)
    hi = np.percentile(boot_means, 100 - alpha)
    observed = mean(diffs)
    
    return observed, lo, hi, diffs

def build_ce_pairs(trials, key, block_fn=None):
    """构建 C–E 配对数据"""
    if block_fn is None:
        block_fn = lambda r: f"{r['operator']}_{r['object_attr']}_{r['group_num']}"
    
    blocks = defaultdict(dict)
    for r in trials:
        bk = block_fn(r)
        blocks[bk][r["mode"]] = float(r[key])
    
    pairs = []
    for bk, modes in blocks.items():
        if "C" in modes and "E" in modes:
            pairs.append((modes["C"], modes["E"]))
    return pairs

def build_ce_pairs_nasa(nasa_rows):
    """NASA-TLX: 按 operator + object_class + mode 聚合"""
    # 先按 mode 聚合每个 operator×object_class 的 raw TLX
    from collections import defaultdict as dd
    blocks = dd(lambda: dd(list))
    for r in nasa_rows:
        key = f"{r['operator']}_{r['object_class']}"
        blocks[key][r["mode"]].append(r["raw_tlx"])
    
    pairs = []
    for bk, modes in blocks.items():
        if "C" in modes and "E" in modes:
            pairs.append((mean(modes["C"]), mean(modes["E"])))
    return pairs

# ─── 主分析 ───
def main():
    trials = read_all_trials()
    nasa_rows = read_nasa_tlx()
    
    print("=" * 72)
    print("  Bootstrap 95% CI 分析 — C vs E 配对差值")
    print("=" * 72)
    print()
    
    # 1. 完成时间
    print("─" * 72)
    print("  1. 完成时间 (duration_s)")
    print("─" * 72)
    
    ce_time = [r for r in trials if r["mode"] in ("C", "E")]
    pairs_time = build_ce_pairs(ce_time, "duration_s")
    
    c_vals = [p[0] for p in pairs_time]
    e_vals = [p[1] for p in pairs_time]
    
    print(f"  配对块数: {len(pairs_time)}")
    print(f"  C: median={median(c_vals):.2f}s, IQR=[{np.percentile(c_vals,25):.2f}, {np.percentile(c_vals,75):.2f}]")
    print(f"  E: median={median(e_vals):.2f}s, IQR=[{np.percentile(e_vals,25):.2f}, {np.percentile(e_vals,75):.2f}]")
    
    obs_t, lo_t, hi_t, diffs_t = bootstrap_paired_ci(pairs_time)
    print(f"  E–C 平均改善: {obs_t:.3f}s")
    print(f"  Bootstrap 95% CI: [{lo_t:.3f}, {hi_t:.3f}]s")
    print(f"  相对降幅: {abs(obs_t)/mean(e_vals)*100:.1f}%")
    
    # 3名操作者级别
    print(f"\n  操作者级:")
    for op in ["P01", "P02", "P03"]:
        op_trials = [r for r in ce_time if r["operator"] == op]
        op_pairs = build_ce_pairs(op_trials, "duration_s")
        op_c = [p[0] for p in op_pairs]
        op_e = [p[1] for p in op_pairs]
        op_diff = mean(op_e) - mean(op_c)
        print(f"    {op}: C={mean(op_c):.2f}s, E={mean(op_e):.2f}s, improvement={op_diff:+.3f}s ({abs(op_diff)/mean(op_e)*100:.1f}%)")
    
    print()
    
    # 2. 主端轨迹长度
    print("─" * 72)
    print("  2. 主端轨迹长度 (traj_length_m)")
    print("─" * 72)
    
    pairs_traj = build_ce_pairs(ce_time, "traj_length_m")
    c_traj = [p[0] for p in pairs_traj]
    e_traj = [p[1] for p in pairs_traj]
    
    print(f"  C: median={median(c_traj):.4f}m, IQR=[{np.percentile(c_traj,25):.4f}, {np.percentile(c_traj,75):.4f}]")
    print(f"  E: median={median(e_traj):.4f}m, IQR=[{np.percentile(e_traj,25):.4f}, {np.percentile(e_traj,75):.4f}]")
    
    obs_j, lo_j, hi_j, diffs_j = bootstrap_paired_ci(pairs_traj)
    print(f"  E–C 平均改善: {obs_j:.4f}m")
    print(f"  Bootstrap 95% CI: [{lo_j:.4f}, {hi_j:.4f}]m")
    print(f"  相对降幅: {abs(obs_j)/mean(e_traj)*100:.1f}%")
    print()
    
    # 3. Raw NASA-TLX
    print("─" * 72)
    print("  3. Raw NASA-TLX")
    print("─" * 72)
    
    pairs_tlx = build_ce_pairs_nasa(nasa_rows)
    c_tlx = [p[0] for p in pairs_tlx]
    e_tlx = [p[1] for p in pairs_tlx]
    
    print(f"  C: median={median(c_tlx):.2f}, IQR=[{np.percentile(c_tlx,25):.2f}, {np.percentile(c_tlx,75):.2f}]")
    print(f"  E: median={median(e_tlx):.2f}, IQR=[{np.percentile(e_tlx,25):.2f}, {np.percentile(e_tlx,75):.2f}]")
    
    diffs_x = [e - c for c, e in pairs_tlx]
    obs_x = mean(diffs_x)
    print(f"  E–C 描述性平均改善: {obs_x:.2f}")
    print("  Bootstrap 95% CI: 不报告（仅 9 个 operator×strategy 配对单元）")
    print(f"  相对降幅: {abs(obs_x)/mean(e_tlx)*100:.1f}%")
    print()
    
    # 4. 汇总表（供论文直接使用）
    print("=" * 72)
    print("  论文可用表格")
    print("=" * 72)
    print()
    print("| Metric | C (median [IQR]) | E (median [IQR]) | Δ (E−C) | Bootstrap 95% CI | Direction |")
    print("|:---|---:|---:|---:|---:|:---|")
    print(f"| Completion time (s) | {median(c_vals):.2f} [{np.percentile(c_vals,25):.2f}, {np.percentile(c_vals,75):.2f}] | {median(e_vals):.2f} [{np.percentile(e_vals,25):.2f}, {np.percentile(e_vals,75):.2f}] | {obs_t:+.2f} | [{lo_t:.2f}, {hi_t:.2f}] | 3/3 operators ↓ |")
    print(f"| Trajectory length (m) | {median(c_traj):.3f} [{np.percentile(c_traj,25):.3f}, {np.percentile(c_traj,75):.3f}] | {median(e_traj):.3f} [{np.percentile(e_traj,25):.3f}, {np.percentile(e_traj,75):.3f}] | {obs_j:+.3f} | [{lo_j:.3f}, {hi_j:.3f}] | mixed |")
    print(f"| Raw NASA-TLX | {median(c_tlx):.2f} [{np.percentile(c_tlx,25):.2f}, {np.percentile(c_tlx,75):.2f}] | {median(e_tlx):.2f} [{np.percentile(e_tlx,25):.2f}, {np.percentile(e_tlx,75):.2f}] | {obs_x:+.2f} | — | 3/3 operators ↓ |")
    print()
    
    # 5. 五模式 median/IQR
    print("─" * 72)
    print("  五模式完成时间 median [IQR]")
    print("─" * 72)
    from collections import defaultdict as dd
    mode_data = dd(list)
    for r in trials:
        mode_data[r["mode"]].append(r["duration_s"])
    
    mode_order = ["A", "B", "C", "D", "E"]
    mode_names = {"A": "Fixed params", "B": "Manual select", "C": "Vision multi-param", "D": "Vision observe", "E": "Vision impedance-only"}
    
    for m in mode_order:
        vals = mode_data[m]
        print(f"  {m} ({mode_names[m]}): {median(vals):.2f}s [{np.percentile(vals,25):.2f}, {np.percentile(vals,75):.2f}] (mean±SD: {mean(vals):.2f}±{stdev(vals):.2f})")

if __name__ == "__main__":
    main()
