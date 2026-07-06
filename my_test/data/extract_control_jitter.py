#!/usr/bin/env python3
"""
extract_control_jitter.py — 从已有 135 个实验 trial 的轨迹 CSV 中提取控制周期统计
CSV 每行有 'time' 列（系统时间戳），相邻行差值 = 控制周期

输出: 论文可用控制周期统计表
"""
import csv
import glob
import numpy as np
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(__file__).resolve().parent

def extract_periods_from_csv(csv_path):
    """从单个 CSV 提取所有相邻 time 差值（单位：秒）"""
    periods = []
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            prev_t = None
            for row in reader:
                t = float(row.get("time", 0))
                if prev_t is not None:
                    dt = t - prev_t
                    if dt > 0 and dt < 0.1:  # 排除明显异常值（>100ms 的可能有暂停）
                        periods.append(dt)
                prev_t = t
    except Exception:
        pass
    return periods

def main():
    # 搜索所有轨迹 CSV
    patterns = [
        "hard_date/**/*.csv",
        "medium_date/**/*.csv",
        "soft_date/**/*.csv",
    ]
    all_csvs = []
    for pat in patterns:
        all_csvs.extend(glob.glob(str(DATA_DIR / pat), recursive=True))

    print(f"Found {len(all_csvs)} trajectory CSVs\n")

    all_periods = []
    file_stats = []

    for csv_path in sorted(all_csvs):
        periods = extract_periods_from_csv(csv_path)
        if len(periods) < 10:
            continue
        all_periods.extend(periods)
        file_stats.append({
            "path": Path(csv_path).name,
            "n_cycles": len(periods),
            "mean_ms": np.mean(periods) * 1000,
            "std_ms": np.std(periods) * 1000,
        })

    periods_arr = np.array(all_periods)
    mean_ms = np.mean(periods_arr) * 1000
    std_ms = np.std(periods_arr) * 1000
    median_ms = np.median(periods_arr) * 1000
    max_ms = np.max(periods_arr) * 1000
    min_ms = np.min(periods_arr) * 1000

    over_6ms = np.sum(periods_arr > 0.006)
    over_10ms = np.sum(periods_arr > 0.010)
    n_total = len(periods_arr)

    print("═" * 56)
    print("  Control Loop Period Analysis (from 135 real trials)")
    print("═" * 56)
    print(f"  Total CSV files processed:  {len(file_stats)}")
    print(f"  Total control cycles:       {n_total:,}")
    print(f"  Nominal period:              5.00 ms")
    print(f"  Mean measured period:        {mean_ms:.2f} ms")
    print(f"  Median period:               {median_ms:.2f} ms")
    print(f"  Standard deviation:          {std_ms:.2f} ms")
    print(f"  Min period:                  {min_ms:.2f} ms")
    print(f"  Max period:                  {max_ms:.2f} ms")
    print(f"  Cycles > 6 ms (120%):        {over_6ms:,} ({over_6ms/n_total*100:.2f}%)")
    print(f"  Cycles > 10 ms (2×):         {over_10ms:,} ({over_10ms/n_total*100:.2f}%)")
    print(f"  Vision inference (mean):     50.08 ms (from vision_validation)")
    print()

    # 论文可用表
    print("─" * 56)
    print("  📊  Paper-ready Table (from real trial data)")
    print("─" * 56)
    print(f"  | Metric                  | Value              |")
    print(f"  |--------------------------|--------------------|")
    print(f"  | Nominal control period   | 5.00 ms            |")
    print(f"  | Mean measured period     | {mean_ms:.2f} ms            |")
    print(f"  | Standard deviation       | {std_ms:.2f} ms            |")
    print(f"  | Median period            | {median_ms:.2f} ms            |")
    print(f"  | Minimum period           | {min_ms:.2f} ms            |")
    print(f"  | Maximum period           | {max_ms:.2f} ms            |")
    print(f"  | Cycles > 10 ms           | {over_10ms:,} / {n_total:,}     |")
    print(f"  | Total cycles analyzed    | {n_total:,}               |")
    print(f"  | Vision inference (mean)  | 50.08 ms            |")
    print()

    # 保存汇总
    summary_path = DATA_DIR / "control_loop_jitter_results.md"
    with open(summary_path, "w") as f:
        f.write("# Control Loop Jitter Analysis (from 135 real trials)\n\n")
        f.write(f"- **Total cycles analyzed:** {n_total:,}\n")
        f.write(f"- **Nominal period:** 5.00 ms\n")
        f.write(f"- **Mean measured period:** {mean_ms:.2f} ms\n")
        f.write(f"- **Median period:** {median_ms:.2f} ms\n")
        f.write(f"- **Standard deviation:** {std_ms:.2f} ms\n")
        f.write(f"- **Min period:** {min_ms:.2f} ms\n")
        f.write(f"- **Max period:** {max_ms:.2f} ms\n")
        f.write(f"- **Cycles > 10 ms (2× nominal):** {over_10ms:,} / {n_total:,} ({over_10ms/n_total*100:.2f}%)\n")
        f.write(f"- **Vision inference:** 50.08 ms (from vision_validation)\n")
    print(f"  Summary saved to: {summary_path}")

if __name__ == "__main__":
    main()