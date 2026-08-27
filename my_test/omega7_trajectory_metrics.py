#!/usr/bin/env python3
"""
omega7_trajectory_metrics.py — Omega.7 主端轨迹长度 & 完成时间分析
==================================================================

功能:
    1. 离线分析: 加载 interactive_teleop.py 录制的轨迹 CSV，计算主端 Omega.7:
       - 轨迹总长度 (累计 3D 欧氏距离)
       - 完成时间 (总时长)
       - 平均速度 / 最大速度
    2. 在线运行: 以「标准模式」运行遥操作，结束后自动分析

用法:
    # 离线分析已有轨迹
    python3 my_test/omega7_trajectory_metrics.py --load data/trajectory_*.csv

    # 在线运行 + 自动分析 (标准模式)
    python3 my_test/omega7_trajectory_metrics.py --run

    # 在线运行 + 指定参数文件
    python3 my_test/omega7_trajectory_metrics.py --run --params my_params.json

    # 指定轨迹输出目录
    python3 my_test/omega7_trajectory_metrics.py --run --trajectory-dir data/

输出:
    data/trajectory_YYYYMMDD_HHMMSS.csv              # 原始轨迹 (由 teleop 录制)
    data/trajectory_YYYYMMDD_HHMMSS_metrics.txt       # 轨迹指标报告

指标说明:
    ┌─────────────────┬──────────────────────────────────────────┐
    │ 轨迹总长度       │ Omega.7 手柄在 3D 空间中移动的累计距离    │
    │ 完成时间         │ 从开始到结束的总耗时 (秒)                 │
    │ 平均速度         │ 轨迹长度 / 完成时间                       │
    │ 最大速度         │ 相邻采样点间的最大瞬时速度                 │
    │ 路径效率         │ 首尾直线距离 / 实际轨迹长度 (越接近 1 越直) │
    │ 平均位移         │ 各轴的平均偏移量                           │
    └─────────────────┴──────────────────────────────────────────┘

作者: mfj
日期: 2026-06
"""

import argparse
import csv
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import numpy as np


# ═══════════════════════════════════════════════════════
# 指标计算
# ═══════════════════════════════════════════════════════


def compute_trajectory_metrics(
    pos: np.ndarray,
    t: np.ndarray,
) -> dict:
    """
    计算 Omega.7 主端轨迹的核心指标

    Args:
        pos: 位置序列 (N, 3), 单位 m
        t:   时间序列 (N,), 单位 s

    Returns:
        dict: {
            "trajectory_length":  轨迹总长度 (m)
            "duration":           完成时间 (s)
            "avg_speed":          平均速度 (m/s)
            "max_speed":          最大瞬时速度 (m/s)
            "path_efficiency":    路径效率 (首尾直线/实际路径)
            "displacement":       首尾位移向量 (3,) (m)
            "mean_pos":           位置均值 (3,) (m)
            "n_samples":          采样点数
            "sample_freq":        实际采样频率 (Hz)
        }
    """
    n = len(pos)
    if n < 2:
        return {"error": "数据点不足 (<2)，无法计算轨迹长度"}

    # ── 逐点欧氏距离 → 累计轨迹长度 ──
    deltas = np.diff(pos, axis=0)                # (N-1, 3)
    step_distances = np.linalg.norm(deltas, axis=1)  # (N-1,)
    trajectory_length = float(np.sum(step_distances))

    # ── 时间 ──
    duration = float(t[-1] - t[0])
    avg_freq = (n - 1) / duration if duration > 0 else 0.0

    # ── 瞬时速度 (中心差分) ──
    dt = duration / (n - 1) if n > 1 else 1.0
    speeds = np.zeros(n)
    if n >= 3:
        speeds[1:-1] = step_distances[:-1] + step_distances[1:]  # 近似
        # 更精确: 用 deltas / 实际 dt
        actual_dt = np.diff(t)
        speeds[1:-1] = (step_distances[:-1] / actual_dt[:-1] +
                        step_distances[1:] / actual_dt[1:]) / 2.0
    # 端点
    if n >= 2:
        speeds[0] = step_distances[0] / (t[1] - t[0] + 1e-10)
        speeds[-1] = step_distances[-1] / (t[-1] - t[-2] + 1e-10)

    avg_speed = float(np.mean(speeds))
    max_speed = float(np.max(speeds))

    # ── 路径效率 ──
    straight_line = float(np.linalg.norm(pos[-1] - pos[0]))
    path_efficiency = straight_line / (trajectory_length + 1e-10)

    # ── 位移统计 ──
    displacement = pos[-1] - pos[0]
    mean_pos = np.mean(pos, axis=0)

    return {
        "trajectory_length": trajectory_length,
        "duration": duration,
        "avg_speed": avg_speed,
        "max_speed": max_speed,
        "path_efficiency": path_efficiency,
        "straight_line": straight_line,
        "displacement": displacement.tolist(),
        "mean_pos": mean_pos.tolist(),
        "n_samples": n,
        "sample_freq": avg_freq,
    }


# ═══════════════════════════════════════════════════════
# CSV 加载
# ═══════════════════════════════════════════════════════


def load_trajectory_csv(filepath: str) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], dict]:
    """
    加载 interactive_teleop.py 录制的轨迹 CSV

    Returns:
        pos: (N, 3) ndarray
        t:   (N,) ndarray
        meta: dict 含 filepath, n_samples, duration, freq, params
    """
    print(f"  📂 加载轨迹: {filepath}")

    records = []
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append({
                "t": float(row["time"]),
                "x": float(row["x"]),
                "y": float(row["y"]),
                "z": float(row["z"]),
                "K_trans": float(row.get("K_trans", 0)),
                "K_rot": float(row.get("K_rot", 0)),
                "damping_ratio": float(row.get("damping_ratio", 0)),
                "K_fb": float(row.get("K_fb", 0)),
                "deadband": float(row.get("deadband", 0)),
                "scale": float(row.get("scale", 0)),
            })

    n = len(records)
    if n < 2:
        print("  ❌ 数据点太少 (<2)，无法分析")
        return None, None, {}

    t = np.array([r["t"] for r in records])
    pos = np.column_stack([
        np.array([r["x"] for r in records]),
        np.array([r["y"] for r in records]),
        np.array([r["z"] for r in records]),
    ])

    # 参数摘要
    params = {}
    for key in ["K_trans", "K_rot", "damping_ratio", "K_fb", "deadband", "scale"]:
        vals = [r[key] for r in records]
        unique_vals = set(f"{v:.2f}" for v in vals)
        if len(unique_vals) <= 3:
            params[key] = vals[0]
        else:
            params[key] = (float(np.min(vals)), float(np.max(vals)))

    duration = t[-1] - t[0]
    avg_freq = n / duration if duration > 0 else 0

    meta = {
        "filepath": filepath,
        "n_samples": n,
        "duration": duration,
        "avg_freq": avg_freq,
        "params": params,
    }

    print(f"     {n} 点, {duration:.1f}s, {avg_freq:.0f} Hz")
    return pos, t, meta


# ═══════════════════════════════════════════════════════
# 报告生成
# ═══════════════════════════════════════════════════════


def generate_report(metrics: dict, meta: dict = None) -> str:
    """生成轨迹指标报告文本"""
    lines = []
    lines.append("=" * 60)
    lines.append("  🎯 Omega.7 主端轨迹指标报告")
    lines.append("=" * 60)
    lines.append("")

    # ── 数据源 ──
    if meta:
        lines.append(f"  数据源:    {meta.get('filepath', 'N/A')}")
        lines.append(f"  采样点数:  {meta.get('n_samples', 0)}")
        lines.append(f"  采样频率:  {meta.get('avg_freq', 0):.1f} Hz")
        if "params" in meta and meta["params"]:
            p = meta["params"]
            parts = []
            for key, label in [("K_trans", "刚度 Kt"),
                               ("damping_ratio", "阻尼比 ζ"),
                               ("K_fb", "力反馈 Kfb"),
                               ("scale", "映射比例")]:
                if key in p:
                    val = p[key]
                    if isinstance(val, tuple):
                        parts.append(f"{label}={val[0]:.1f}~{val[1]:.1f}")
                    else:
                        parts.append(f"{label}={val:.2f}")
            if parts:
                lines.append(f"  操作参数:  {', '.join(parts)}")
        lines.append("")

    # ── 核心指标 ──
    if "error" in metrics:
        lines.append(f"  ❌ {metrics['error']}")
        return "\n".join(lines)

    lines.append("─" * 60)
    lines.append("  📊 核心轨迹指标")
    lines.append("─" * 60)

    # 轨迹长度 — 主指标
    length = metrics["trajectory_length"]
    lines.append(f"")
    lines.append(f"  🏃 轨迹总长度:   {length:>8.3f}  m")
    if length < 0.5:
        lines.append(f"       └─ 操作范围很小 (精细操作)")
    elif length < 2.0:
        lines.append(f"       └─ 中等操作范围")
    elif length < 5.0:
        lines.append(f"       └─ 较大范围操作")
    else:
        lines.append(f"       └─ 大幅度操作")

    # 完成时间
    duration = metrics["duration"]
    lines.append(f"  ⏱️  完成时间:     {duration:>8.1f}  s")
    if duration < 10:
        lines.append(f"       └─ 短时操作")
    elif duration < 30:
        lines.append(f"       └─ 中等时长操作")
    elif duration < 60:
        lines.append(f"       └─ 较长操作 (建议注意疲劳)")
    else:
        lines.append(f"       └─ 长时间操作 (>1分钟, 注意休息)")

    lines.append(f"")

    # ── 速度指标 ──
    lines.append(f"  📈 速度指标")
    lines.append(f"  ├─ 平均速度:     {metrics['avg_speed']:>8.3f}  m/s")
    lines.append(f"  └─ 最大速度:     {metrics['max_speed']:>8.3f}  m/s")

    lines.append(f"")

    # ── 路径指标 ──
    eff = metrics["path_efficiency"]
    straight = metrics["straight_line"]
    lines.append(f"  🗺️  路径效率")
    lines.append(f"  ├─ 首尾直线距离: {straight:>8.3f}  m")
    lines.append(f"  └─ 路径效率:     {eff:>8.3f}")
    if eff > 0.9:
        lines.append(f"       └─ 近乎直线运动，路径效率极高")
    elif eff > 0.7:
        lines.append(f"       └─ 路径较直，效率良好")
    elif eff > 0.5:
        lines.append(f"       └─ 有一定绕路")
    else:
        lines.append(f"       └─ 路径弯曲较多")

    lines.append(f"")

    # ── 位移统计 ──
    disp = metrics["displacement"]
    mean_p = metrics["mean_pos"]
    lines.append(f"  📍 位移统计")
    lines.append(f"  ├─ ΔX: {disp[0]:>+8.3f}  m   (均值 X: {mean_p[0]:.3f} m)")
    lines.append(f"  ├─ ΔY: {disp[1]:>+8.3f}  m   (均值 Y: {mean_p[1]:.3f} m)")
    lines.append(f"  └─ ΔZ: {disp[2]:>+8.3f}  m   (均值 Z: {mean_p[2]:.3f} m)")

    lines.append(f"")
    lines.append("─" * 60)
    lines.append("  报告生成时间: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    lines.append("=" * 60)

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════
# 运行 teleop + 自动分析
# ═══════════════════════════════════════════════════════


def run_teleop_and_analyze(trajectory_dir: str = "data"):
    """
    以标准模式运行遥操作，结束后自动分析最新轨迹

    工作流程:
        1. 调用 interactive_teleop.py (标准模式)
        2. 等待结束 (Ctrl+C)
        3. 找到最新录制的 CSV
        4. 计算轨迹指标并保存报告
    """
    script_dir = Path(__file__).parent
    teleop_script = script_dir / "interactive_teleop.py"

    if not teleop_script.exists():
        print(f"❌ 找不到遥操作脚本: {teleop_script}")
        sys.exit(1)

    print("=" * 60)
    print("  🚀 启动遥操作 (标准模式) — 结束后自动分析轨迹")
    print("=" * 60)
    print(f"  轨迹保存目录: {trajectory_dir}/")
    print(f"  提示: 结束后按 Ctrl+C 停止")
    print()

    # ── 启动 teleop ──
    # teleop 默认启动标准模式 (见 _set_preset("standard"))
    cmd = [
        sys.executable,
        str(teleop_script),
        "--trajectory-dir", trajectory_dir,
    ]

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n\n  ⏹️  遥操作已终止")
    except Exception as e:
        print(f"\n  ❌ 遥操作异常: {e}")

    # ── 给文件系统一点时间 ──
    time.sleep(0.5)

    # ── 找最新轨迹文件 ──
    data_path = Path(trajectory_dir)
    csv_files = sorted(data_path.glob("trajectory_*.csv"))
    if not csv_files:
        print("❌ 未找到轨迹 CSV 文件，可能未录制轨迹")
        print("  提示: 请确保 teleop 启动时未使用 --no-trajectory 参数")
        sys.exit(1)

    latest_csv = str(csv_files[-1])
    print(f"\n  🔍 检测到最新轨迹: {latest_csv}")

    # ── 分析 ──
    analyze_csv(latest_csv)


def find_latest_trajectory(data_dir: str = "data") -> Optional[str]:
    """查找最新的轨迹 CSV 文件"""
    path = Path(data_dir)
    if not path.exists():
        return None
    csv_files = sorted(path.glob("trajectory_*.csv"))
    return str(csv_files[-1]) if csv_files else None


def analyze_csv(csv_path: str, save_report: bool = True):
    """加载 CSV 并计算/显示轨迹指标"""
    if not os.path.exists(csv_path):
        print(f"❌ 文件不存在: {csv_path}")
        sys.exit(1)

    pos, t, meta = load_trajectory_csv(csv_path)
    if pos is None:
        sys.exit(1)

    metrics = compute_trajectory_metrics(pos, t)
    report = generate_report(metrics, meta)

    print("\n" + report)

    # ── 保存报告 ──
    if save_report:
        report_path = csv_path.replace(".csv", "_metrics.txt")
        with open(report_path, "w") as f:
            f.write(report)
        print(f"\n  📄 报告已保存: {report_path}")

    # ── 简易摘要 (用于快速查看) ──
    print()
    print("─" * 60)
    print(f"  📋 快速摘要:")
    print(f"  轨迹长度: {metrics['trajectory_length']:.3f} m  |  "
          f"完成时间: {metrics['duration']:.1f} s  |  "
          f"平均速度: {metrics['avg_speed']:.3f} m/s")
    print("─" * 60)


# ═══════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════


def main():
    parser = argparse.ArgumentParser(
        description="Omega.7 主端轨迹长度 & 完成时间分析"
    )

    # 互斥: --load / --run / --latest
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--load", "-l", type=str, default=None,
        metavar="CSV_PATH",
        help="加载已有轨迹 CSV 文件进行分析",
    )
    group.add_argument(
        "--run", "-r", action="store_true",
        help="运行遥操作 (标准模式)，结束后自动分析轨迹",
    )
    group.add_argument(
        "--latest", action="store_true",
        help="自动分析 data/ 目录下最新的轨迹文件",
    )

    parser.add_argument(
        "--trajectory-dir", type=str, default="data",
        help="轨迹 CSV 目录 (默认: data/)",
    )
    parser.add_argument(
        "--no-save", action="store_true",
        help="不保存报告文件，仅打印到终端",
    )

    args = parser.parse_args()

    # ── 分支 ──
    if args.run:
        run_teleop_and_analyze(trajectory_dir=args.trajectory_dir)

    elif args.latest:
        csv_path = find_latest_trajectory(args.trajectory_dir)
        if csv_path is None:
            print(f"❌ {args.trajectory_dir}/ 目录下未找到 trajectory_*.csv 文件")
            sys.exit(1)
        print(f"  🔍 自动检测最新轨迹: {csv_path}")
        analyze_csv(csv_path, save_report=not args.no_save)

    elif args.load:
        analyze_csv(args.load, save_report=not args.no_save)

    else:
        parser.print_help()
        print("\n💡 用法示例:")
        print(f"  {sys.argv[0]} --run                    # 运行遥操作 → 自动分析")
        print(f"  {sys.argv[0]} --latest                 # 分析最新轨迹")
        print(f"  {sys.argv[0]} --load data/trajectory_*.csv  # 加载已有轨迹分析")
        sys.exit(0)


if __name__ == "__main__":
    main()
