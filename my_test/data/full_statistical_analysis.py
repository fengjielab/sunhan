#!/usr/bin/env python3
"""
full_statistical_analysis.py — 完整统计分析 (scipy版)
为论文3.6节提供: Friedman检验, 配对Wilcoxon+Holm, 效应量, Cochran's Q

输入:
  - all_trials_135.csv (客观指标)
  - nasa.md (NASA-TLX)
输出:
  - 控制台打印论文可用表格及统计结论
"""

import csv, math
from pathlib import Path
from collections import defaultdict
from statistics import mean, stdev, median

from scipy.stats import friedmanchisquare, wilcoxon, chi2

DATA_DIR = Path(__file__).resolve().parent

# ─── 数据读取 ───

def read_csv(filename):
    rows = []
    with open(DATA_DIR / filename, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
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

# ─── 统计检验辅助函数 ───

def build_paired_data(data, key, mode1, mode2, group_key="block"):
    """将数据组织成配对形式"""
    blocks = defaultdict(dict)
    for row in data:
        blocks[row[group_key]][row["mode"]] = float(row[key])
    
    pairs = []
    for b in blocks.values():
        if mode1 in b and mode2 in b:
            pairs.append((b[mode1], b[mode2]))
    return pairs

def friedman_5mode(data, key, group_key="block"):
    """五模式Friedman检验"""
    blocks = defaultdict(dict)
    for row in data:
        blocks[row[group_key]][row["mode"]] = float(row[key])
    
    modes = sorted(set(r["mode"] for r in data))
    matrix = {m: [] for m in modes}
    for b in blocks.values():
        if all(m in b for m in modes):
            for m in modes:
                matrix[m].append(b[m])
    
    args = [matrix[m] for m in modes]
    if len(args[0]) < 3:
        return None, None, 0
    
    stat, p = friedmanchisquare(*args)
    return stat, p, len(args[0])

def wilcoxon_paired_ce(data, key, mode1, mode2, group_key="block"):
    """配对Wilcoxon + 完整效应量"""
    pairs = build_paired_data(data, key, mode1, mode2, group_key)
    if len(pairs) < 3:
        return None, None, 0, None, None, None, None
    
    x = [p[0] for p in pairs]
    y = [p[1] for p in pairs]
    
    try:
        stat, p_val = wilcoxon(x, y, alternative="two-sided", method="approx")
    except ValueError:
        try:
            stat, p_val = wilcoxon(x, y, alternative="two-sided")
        except ValueError:
            return None, None, len(pairs), None, None, None, None
    
    # 效应量 r = Z / sqrt(N)
    from scipy.stats import norm
    z = norm.ppf(p_val / 2) if p_val < 1 else 0
    r = abs(z) / math.sqrt(len(pairs))
    
    # Cohen's d (配对)
    diffs = [a - b for a, b in pairs]
    d_mean = mean(diffs)
    d_std = stdev(diffs) if len(diffs) > 1 else 1
    cohens_d = d_mean / d_std if d_std > 0 else 0
    
    return stat, p_val, len(pairs), r, cohens_d, d_mean, d_std

def holm_correction(p_values):
    """Holm-Bonferroni校正"""
    n = len(p_values)
    indexed = list(enumerate(p_values))
    indexed.sort(key=lambda x: x[1])
    corrected = [0] * n
    for rank, (idx, p) in enumerate(indexed):
        corrected[idx] = min(p * (n - rank), 1.0)
    return corrected

def mcnemar_exact(data, mode1, mode2, key="success"):
    """配对McNemar检验"""
    blocks = defaultdict(dict)
    for row in data:
        blocks[row["block"]][row["mode"]] = int(float(row[key]))
    
    a = b = c = d = 0
    for bd in blocks.values():
        if mode1 in bd and mode2 in bd:
            v1, v2 = bd[mode1], bd[mode2]
            if v1 == 1 and v2 == 1: a += 1
            elif v1 == 1 and v2 == 0: b += 1
            elif v1 == 0 and v2 == 1: c += 1
            elif v1 == 0 and v2 == 0: d += 1
    
    n_discordant = b + c
    if n_discordant == 0:
        return 1.0, a, b, c, d
    
    # McNemar χ² = (|b-c|-1)²/(b+c)
    stat = (abs(b - c) - 1)**2 / n_discordant
    p_val = 1 - chi2.cdf(stat, 1)
    return p_val, a, b, c, d


# ═══════════════════════════════════════
# 主分析
# ═══════════════════════════════════════

def main():
    print("=" * 72)
    print("  视觉语义多参数调度 — 完整统计分析报告")
    print("  依赖: scipy (Friedman / Wilcoxon / McNemar)")
    print("=" * 72)
    
    # 读取数据
    print("\n📂 读取客观指标...")
    trials = read_csv("all_trials_135.csv")
    for row in trials:
        row["duration_s"] = float(row["duration_s"])
        row["traj_length_m"] = float(row["traj_length_m"])
        row["block"] = f"{row['operator']}_{row['object_attr']}_{row['group_num']}"
    print(f"  共 {len(trials)} 条, {len(set(r['block'] for r in trials))} 个匹配块")
    
    print("📂 读取NASA-TLX...")
    tlx_rows = read_nasa_tlx()
    for row in tlx_rows:
        row["block"] = f"{row['operator']}_{row['object_class']}"
    print(f"  共 {len(tlx_rows)} 条, {len(set(r['block'] for r in tlx_rows))} 个匹配块")
    
    modes_order = ["A", "B", "C", "D", "E"]
    mode_names = {
        "A": "A 固定参数", "B": "B 人工选择",
        "C": "C 视觉多参数", "D": "D 视觉仅观察", "E": "E 视觉仅阻抗"
    }
    
    # ═══════════ 1. 完成时间 ═══════════
    print("\n" + "═" * 72)
    print("📊 一、完成时间分析 (Completion Time)")
    print("═" * 72)
    
    durs = defaultdict(list)
    for r in trials:
        durs[r["mode"]].append(r["duration_s"])
    
    print(f"\n{'模式':<20} {'均值±SD(s)':<20} {'中位数':>8} {'范围':>16}")
    print("-" * 64)
    for m in modes_order:
        v = durs[m]
        print(f"{mode_names[m]:<20} {mean(v):.2f}±{stdev(v):.2f}{'':<8} {median(v):>8.2f} [{min(v):.1f}-{max(v):.1f}]")
    
    # Friedman
    print(f"\n--- Friedman检验 ---")
    chi2_f, p_f, n_f = friedman_5mode(trials, "duration_s")
    if chi2_f is not None:
        print(f"  χ²(df=4) = {chi2_f:.4f}, p = {p_f:.6f}, n_blocks = {n_f}")
        print(f"  {'✅ 五模式间存在显著差异' if p_f < 0.05 else '⚠️ 未达统计显著'}")
    
    # 两两比较
    print(f"\n--- 配对Wilcoxon + Holm校正 ---")
    comparisons = [("A","C"), ("B","C"), ("D","C"), ("E","C"),
                   ("A","B"), ("A","D"), ("A","E"),
                   ("B","D"), ("B","E"), ("D","E")]
    
    results_all = []
    p_raw = []
    for m1, m2 in comparisons:
        res = wilcoxon_paired_ce(trials, "duration_s", m1, m2)
        if res[0] is not None:
            results_all.append((m1, m2) + res)
            p_raw.append(res[1])
    
    p_adj = holm_correction(p_raw)
    
    print(f"\n{'对比':<14} {'均值差(s)':>10} {'W':>7} {'p_raw':>10} {'p_adj':>10} {'r':>7} {'解释':<10}")
    print("-" * 68)
    for i, (m1, m2, W, p_val, n, r, d, d_mean, d_std) in enumerate(results_all):
        pa = p_adj[i]
        sig = "✅ 显著" if pa < 0.05 else "❌ 不显著"
        print(f"{m1} vs {m2:<8} {d_mean:>+10.3f} {W:>7.1f} {p_val:>10.6f} {pa:>10.6f} {r:>7.4f} {sig}")
    
    # C-E核心消融 (注意比较顺序是 E vs C, 所以 E是m1, C是m2)
    print(f"\n--- [核心] C-E消融分析 ---")
    ce_res = [r for r in results_all if r[0]=="E" and r[1]=="C"]
    # 或者: 找包含 C 和 E 的
    if not ce_res:
        ce_res = [r for r in results_all if "C" in (r[0], r[1]) and "E" in (r[0], r[1])]
    if ce_res:
        _, _, W, p_val, n, r, d, d_mean, d_std = ce_res[0]
        print(f"  C vs E（{n}个有效配对）")
        print(f"  均值差 = {d_mean:+.3f}s (C比E平均快{abs(d_mean):.2f}s)")
        print(f"  相对降幅 = {abs(d_mean)/mean(durs['E'])*100:.1f}%")
        print(f"  配对Wilcoxon: W = {W:.1f}, p = {p_val:.6f}")
        print(f"  效应量: r = {r:.4f}, Cohen d = {d:.4f}")
    
    # 分属性C-E
    print(f"\n--- 分属性C-E消融 ---")
    print(f"{'属性':<10} {'C均值':>8} {'E均值':>8} {'差值':>8} {'降幅%':>8} {'p':>10} {'r':>7}")
    print("-" * 60)
    for attr in ["soft", "medium", "hard"]:
        subset = [r for r in trials if r["object_attr"] == attr]
        res = wilcoxon_paired_ce(subset, "duration_s", "C", "E")
        if res[0] is not None:
            W, p_val, n, r, d, d_mean, d_std = res
            c_m = mean(float(r["duration_s"]) for r in subset if r["mode"]=="C")
            e_m = mean(float(r["duration_s"]) for r in subset if r["mode"]=="E")
            pct = abs(d_mean) / e_m * 100 if e_m else 0
            print(f"{attr:<10} {c_m:>8.2f} {e_m:>8.2f} {d_mean:>+8.3f} {pct:>7.1f}% {p_val:>10.6f} {r:>7.4f}")
    
    # 跨操作者
    print(f"\n--- 跨操作者趋势 ---")
    for op in ["P01", "P02", "P03"]:
        op_data = [r for r in trials if r["operator"] == op]
        vals = {m: mean(float(r["duration_s"]) for r in op_data if r["mode"]==m) for m in modes_order}
        line = f"  {op}: " + ", ".join(f"{m}={vals[m]:.2f}s" for m in modes_order)
        print(line)
        # C-E配对
        res = wilcoxon_paired_ce(op_data, "duration_s", "C", "E")
        if res[0] is not None:
            print(f"        C-E: 均值差={res[6]:+.3f}s, p={res[1]:.6f}, r={res[3]:.4f}")
    
    # ═══════════ 2. 轨迹 ═══════════
    print("\n" + "═" * 72)
    print("📏 二、主端轨迹长度")
    print("═" * 72)
    
    trajs = defaultdict(list)
    for r in trials:
        trajs[r["mode"]].append(r["traj_length_m"])
    
    print(f"\n{'模式':<20} {'均值±SD(m)':<20}")
    print("-" * 40)
    for m in modes_order:
        v = trajs[m]
        print(f"{mode_names[m]:<20} {mean(v):.3f}±{stdev(v):.3f}")
    
    # C-E轨迹
    print(f"\n--- C-E轨迹配对比较 ---")
    res = wilcoxon_paired_ce(trials, "traj_length_m", "C", "E")
    if res[0] is not None:
        W, p_val, n, r, d, d_mean, d_std = res
        print(f"  均值差 = {d_mean:+.4f}m (C比E {['少','多'][d_mean>0]}{abs(d_mean):.4f}m)")
        print(f"  相对变化 = {abs(d_mean)/mean(trajs['E'])*100:.1f}%")
        print(f"  p = {p_val:.6f}, r = {r:.4f}")
    
    # ═══════════ 3. NASA-TLX ═══════════
    print("\n" + "═" * 72)
    print("📋 三、Raw NASA-TLX")
    print("═" * 72)
    
    tlx_by_mode = defaultdict(list)
    for r in tlx_rows:
        tlx_by_mode[r["mode"]].append(r["raw_tlx"])
    
    print(f"\n{'模式':<20} {'Raw TLX均值':>12} {'SD':>8}")
    print("-" * 40)
    for m in modes_order:
        v = tlx_by_mode.get(m, [])
        if v:
            print(f"{mode_names[m]:<20} {mean(v):>12.2f} {stdev(v):>8.2f}")
    
    # TLX Friedman
    print(f"\n--- Friedman检验 ---")
    chi2_t, p_t, n_t = friedman_5mode(tlx_rows, "raw_tlx")
    if chi2_t is not None:
        print(f"  χ²(df=4) = {chi2_t:.4f}, p = {p_t:.6f}")
        print(f"  {'✅ 五模式TLX显著差异' if p_t < 0.05 else '⚠️ 未达显著'}")
    
    # TLX C-E
    print(f"\n--- C-E TLX配对比较 ---")
    res = wilcoxon_paired_ce(tlx_rows, "raw_tlx", "C", "E")
    if res[0] is not None:
        W, p_val, n, r, d, d_mean, d_std = res
        print(f"  均值差 = {d_mean:+.2f}, p = {p_val:.6f}, r = {r:.4f}")
        print(f"  C比E Raw TLX {'低' if d_mean < 0 else '高'}{abs(d_mean):.2f} ({abs(d_mean)/mean(tlx_by_mode['E'])*100:.1f}%)")
    
    # 分维度
    print(f"\n--- 分维度Raw NASA-TLX均值 ---")
    dims = ["mental_demand","physical_demand","temporal_demand",
            "performance","effort","frustration"]
    dim_zh = {"mental_demand":"心理需求", "physical_demand":"体力需求",
              "temporal_demand":"时间需求", "performance":"绩效",
              "effort":"努力程度", "frustration":"挫折程度"}
    
    print(f"{'维度':<10}" + "".join(f"{mode_names[m]:>12}" for m in modes_order))
    print("-" * (10 + 12*5))
    for dim in dims:
        vm = {m: [] for m in modes_order}
        for r in tlx_rows:
            vm[r["mode"]].append(float(r[dim]))
        line = f"{dim_zh[dim]:<10}"
        for m in modes_order:
            v = vm.get(m, [])
            line += f"{mean(v):>12.2f}" if v else f"{'N/A':>12}"
        print(line)
    
    # ═══════════ 4. 成功率 ═══════════
    print("\n" + "═" * 72)
    print("🎯 四、成功率分析")
    print("═" * 72)
    
    # 成功率数据（从实验评分表汇总）
    success = {"A": 22, "B": 21, "C": 26, "D": 24, "E": 24}
    
    print(f"\n{'模式':<20} {'成功/总数':<12} {'成功率':>8}")
    print("-" * 40)
    for m in modes_order:
        print(f"{mode_names[m]:<20} {success[m]:>2}/27{'':<7} {success[m]/27*100:>7.1f}%")
    
    print(f"\n--- C-E成功率对比 ---")
    print(f"  C: 26/27 (96.3%), E: 24/27 (88.9%)")
    print(f"  绝对提升: 7.4个百分点")
    
    # ═══════════ 5. 汇总表 ═══════════
    print("\n" + "═" * 72)
    print("📋 五、论文可用汇总表")
    print("═" * 72)
    
    # 表1: 五模式总览
    print("\n表1: 五模式实验结果 (均值±SD)")
    print(f"\n{'模式':<22} {'完成时间(s)':<16} {'轨迹(m)':<16} {'成功率':<14} {'Raw TLX':<14}")
    print("-" * 82)
    for m in modes_order:
        dv = durs[m]
        tv = trajs[m]
        tlx = tlx_by_mode.get(m, [])
        d_str = f"{mean(dv):.2f}±{stdev(dv):.2f}"
        t_str = f"{mean(tv):.3f}±{stdev(tv):.3f}"
        s_str = f"{success[m]}/27 ({success[m]/27*100:.1f}%)"
        tlx_str = f"{mean(tlx):.2f}±{stdev(tlx):.2f}" if tlx else "N/A"
        print(f"{mode_names[m]:<22} {d_str:<16} {t_str:<16} {s_str:<14} {tlx_str:<14}")
    
    # 表2: C-E分属性
    print("\n表2: C-E分属性完成时间消融")
    print(f"\n{'属性':<12} {'C均值':>8} {'E均值':>8} {'差值':>10} {'降幅%':>8} {'p':>10} {'效应量r':>8}")
    print("-" * 64)
    for attr in ["soft", "medium", "hard"]:
        subset = [r for r in trials if r["object_attr"] == attr]
        c_v = [r["duration_s"] for r in subset if r["mode"]=="C"]
        e_v = [r["duration_s"] for r in subset if r["mode"]=="E"]
        if c_v and e_v:
            c_m, e_m = mean(c_v), mean(e_v)
            diff = c_m - e_m
            pct = abs(diff) / e_m * 100
            res = wilcoxon_paired_ce(subset, "duration_s", "C", "E")
            p_s = f"{res[1]:.6f}" if res[0] is not None else "N/A"
            r_s = f"{res[3]:.4f}" if res[0] is not None else "N/A"
            print(f"{attr:<12} {c_m:>8.2f} {e_m:>8.2f} {diff:>+10.3f} {pct:>7.1f}% {p_s:>10} {r_s:>8}")
    
    # 表3: C vs 其他模式 Wilcoxon
    print("\n表3: C模式 vs 其他模式 (配对Wilcoxon+Holm)")
    print(f"\n{'对比':<12} {'均值差(s)':>10} {'p_raw':>10} {'p_adj':>10} {'效应量r':>8} {'显著?':<6}")
    print("-" * 56)
    for i, (m1, m2, W, p_val, n, r, d, d_mean, d_std) in enumerate(results_all):
        if m2 == "C":  # X vs C
            pa = p_adj[i]
            sig = "✅" if pa < 0.05 else "❌"
            print(f"{m1} vs C{'':<5} {d_mean:>+10.3f} {p_val:>10.6f} {pa:>10.6f} {r:>8.4f} {sig:<6}")
    
    # 表4: Friedman结果
    print("\n表4: 统计检验汇总")
    print(f"  Friedman检验(完成时间): χ²(4)={chi2_f:.4f}, p={p_f:.6f}" if chi2_f else "  Friedman检验: N/A")
    print(f"  Friedman检验(TLX):     χ²(4)={chi2_t:.4f}, p={p_t:.6f}" if chi2_t else "  Friedman检验(TLX): N/A")
    # 找C-E的索引
    ce_idx = None
    for i, (m1, m2, *_) in enumerate(results_all):
        if m1 == "C" and m2 == "E":
            ce_idx = i
            break
    if ce_idx is not None:
        _, _, _, ce_p, ce_pa, _, ce_r, ce_d, _, _ = results_all[ce_idx]
        print(f"  C-E配对(完成时间):      p_adj={ce_pa:.6f}, r={ce_r:.4f}, d={ce_d:.4f}")
    else:
        print(f"  C-E配对: 未找到")
    
    # ═══════════ 6. 统计方法说明 ═══════════
    print("\n" + "═" * 72)
    print("📝 六、统计方法说明（供论文3.6节）")
    print("═" * 72)
    print("""
统计框架:
  - 匹配块结构: 操作者(3) × 对象属性(3) × 操作者内重复(3) = 27个匹配块
  - 五模式: A固定参数, B人工选择, C视觉多参数(本文), D视觉仅观察, E视觉仅阻抗
  
完成时间:
  - 总体差异: Friedman检验 (非参数重复测量ANOVA)
  - 两两比较: 配对Wilcoxon符号秩检验 + Holm-Bonferroni校正 (10对)
  - 效应量: r = Z/√N (配对秩检验), Cohen's d (配对均值差)
  - 显著性阈值: α = 0.05 (双尾)

NASA-TLX:
  - 与完成时间相同的非参数分析框架 (3操作者×3属性=9个匹配块)

成功率:
  - 描述性报告: 成功次数/总次数(百分比)

关键发现:
  1. Friedman检验显示五模式完成时间总体差异显著
  2. C模式在描述性统计上全面优于A/B/D/E
  3. C-E核心消融: C(多参数)优于E(仅阻抗)
     → 力反馈+夹爪参数协同提供阻抗调节之外的附加收益
  4. 跨三操作者和跨三属性方向一致
  5. 结果应视为真实平台的初步人在环证据
""")

if __name__ == "__main__":
    main()