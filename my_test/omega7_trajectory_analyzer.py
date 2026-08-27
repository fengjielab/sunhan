#!/usr/bin/env python3
"""
omega7_trajectory_analyzer.py — Omega.7 轨迹离线疲劳分析工具
===============================================================

从交互式遥操作脚本录制的 CSV 轨迹文件中读取数据，
分析操作员的**劳累程度（疲劳度）**并提供量化报告。

核心原理:
    疲劳 → 神经肌肉控制能力下降 → 操作运动特征明显变化:
    ┌──────────────────────────────────────────────────────────┐
    │ 📉 运动平滑度 ↓    (jerk 增大, SPARC 减小)               │
    │ 📉 运动速度 ↓      (平均/峰值速度降低)                    │
    │ 📈 高频震颤 ↑      (8-15Hz 生理震颤能量增加)              │
    │ 📈 停顿时间 ↑      (操作中无意识停顿增多)                  │
    │ 📉 路径效率 ↓      (轨迹更弯曲/绕路)                      │
    │ 📈 运动不规则性 ↑  (速度/加速度标准差增大, 节奏紊乱)      │
    └──────────────────────────────────────────────────────────┘

数据来源:
    由 interactive_teleop.py 自动录制到 data/trajectory_*.csv
    轨迹包含: 时间, 位置(xyz), 夹爪角度, 按钮, 当前参数(K,ζ,Kfb,scale)

用法:
    # 分析单条轨迹
    python3 my_test/omega7_trajectory_analyzer.py --load data/trajectory_*.csv

    # 分析 + 生成图表
    python3 my_test/omega7_trajectory_analyzer.py --load data/trajectory_*.csv --save-plot

    # 批量分析最新轨迹
    python3 my_test/omega7_trajectory_analyzer.py --latest

    # 从交互式遥操作录制后使用:
    python3 my_test/interactive_teleop.py                              # 终端1: 遥操作(自动录轨迹)
    python3 my_test/omega7_trajectory_analyzer.py --load data/trajectory_*.csv  # 离线分析

输出:
    data/
    ├── trajectory_YYYYMMDD_HHMMSS.csv            # 原始轨迹 (由 interactive_teleop.py 生成)
    └── trajectory_YYYYMMDD_HHMMSS_analysis.txt   # 疲劳分析报告
    └── trajectory_YYYYMMDD_HHMMSS_analysis.png   # 分析图表 (--save-plot)

作者: mfj
日期: 2026-06
"""

import argparse
import csv
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# ── 可选依赖 ──
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

try:
    from scipy import signal as scipy_signal
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

# ═══════════════════════════════════════════
# 默认配置
# ═══════════════════════════════════════════

DATA_DIR = Path("data")

# 分析窗口 (秒)
ANALYSIS_WINDOW = 5.0       # 滑动窗口大小
WINDOW_OVERLAP = 0.5        # 窗口重叠率 (50%)

# 信号处理参数
TREMOR_BAND = (8.0, 15.0)     # 生理震颤频带 (Hz)
MOVEMENT_BAND = (0.1, 5.0)    # 主动运动频带 (Hz)
PAUSE_SPEED_THRESHOLD = 0.005 # 停顿速度阈值 (m/s)

# 疲劳指标权重（综合指数 = Σ wi · 归一化指标）
# 注意 key 必须与 compute_fatigue_scores() 返回的字典 key 一致
FATIGUE_WEIGHTS = {
    "jerk_score": 0.25,            # 运动平滑度
    "tremor_score": 0.20,          # 高频震颤
    "speed_score": 0.20,           # 运动速度 (负相关)
    "pause_score": 0.15,           # 停顿比例
    "irregularity_score": 0.10,    # 运动不规则性
    "path_score": 0.10,            # 路径效率
}

# 各指标基线 (放松值, 疲劳值) — 用于归一化到 0~100
BASELINES = {
    "jerk_mean":   (0.5, 5.0),      # 平均 jerk [m/s³]
    "tremor_ratio": (0.1, 0.6),     # 震颤能量 / 运动能量比
    "speed_mean":  (0.15, 0.03),    # 平均速度 [m/s] (反向: 越小越疲劳)
    "pause_ratio": (0.05, 0.35),    # 停顿时间占比
    "speed_cv":    (0.3, 1.5),      # 速度变异系数 (CV=σ/μ)
    "path_curve":  (1.2, 4.0),      # 路径弯曲度 (实际/直线)
}


# ═══════════════════════════════════════════════════════
# CSV 加载
# ═══════════════════════════════════════════════════════

def load_trajectory_csv(filepath: str) -> dict:
    """
    加载 interactive_teleop.py 录制的轨迹 CSV

    CSV 格式:
        time, x, y, z, gripper_deg, button, K_trans, K_rot, damping_ratio, K_fb, deadband, scale

    Returns:
        dict: {
            "t": ndarray(N),
            "pos": ndarray(N, 3),
            "gripper": ndarray(N),
            "button": ndarray(N),
            "params": dict of arrays (K_trans, K_rot, etc.),
            "meta": {"filepath", "duration", "n_samples", "freq"},
        }
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
                "gripper": float(row.get("gripper_deg", 0)),
                "button": int(row.get("button", 0)),
                "K_trans": float(row.get("K_trans", 0)),
                "K_rot": float(row.get("K_rot", 0)),
                "damping_ratio": float(row.get("damping_ratio", 0)),
                "K_fb": float(row.get("K_fb", 0)),
                "deadband": float(row.get("deadband", 0)),
                "scale": float(row.get("scale", 0)),
            })

    if len(records) < 10:
        print("  ❌ 数据点太少 (<10)，无法分析")
        return None

    n = len(records)
    t = np.array([r["t"] for r in records])
    pos = np.column_stack([
        np.array([r["x"] for r in records]),
        np.array([r["y"] for r in records]),
        np.array([r["z"] for r in records]),
    ])
    gripper = np.array([r["gripper"] for r in records])
    button = np.array([r["button"] for r in records])

    duration = t[-1] - t[0]
    avg_freq = n / duration if duration > 0 else 0

    # 参数记录
    params = {}
    for key in ["K_trans", "K_rot", "damping_ratio", "K_fb", "deadband", "scale"]:
        vals = np.array([r[key] for r in records])
        # 只记录有变化的参数
        if np.std(vals) > 1e-6:
            params[key] = vals
        else:
            params[key] = np.array([vals[0]])

    meta = {
        "filepath": filepath,
        "n_samples": n,
        "duration": duration,
        "avg_freq": avg_freq,
    }

    print(f"     {n} 点, {duration:.1f}s, {avg_freq:.0f} Hz")

    return {
        "t": t, "pos": pos, "gripper": gripper, "button": button,
        "params": params, "meta": meta,
    }


# ═══════════════════════════════════════════════════════
# 疲劳分析引擎
# ═══════════════════════════════════════════════════════

class FatigueAnalyzer:
    """
    Omega.7 轨迹疲劳分析引擎

    输入: 时间序列 [t, x, y, z]
    输出: 多维度疲劳指标 + 综合疲劳指数 (0~100)
    """

    def __init__(self, sample_freq: float = 200.0):
        self.fs = sample_freq
        self.dt = 1.0 / sample_freq

    # ═══════════════════════════════════════════
    # 运动学计算
    # ═══════════════════════════════════════════

    def compute_kinematics(
        self, pos: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        计算速度、加速度、jerk (中心差分)

        Returns:
            vel:   (N, 3) [m/s]
            acc:   (N, 3) [m/s²]
            jerk:  (N, 3) [m/s³]
        """
        n = len(pos)
        vel = np.zeros_like(pos)
        acc = np.zeros_like(pos)
        jerk = np.zeros_like(pos)

        # 一阶导数: 速度
        if n >= 3:
            vel[1:-1] = (pos[2:] - pos[:-2]) / (2.0 * self.dt)
        vel[0] = (pos[1] - pos[0]) / self.dt if n > 1 else 0
        vel[-1] = (pos[-1] - pos[-2]) / self.dt if n > 1 else 0

        # 二阶导数: 加速度
        if n >= 3:
            acc[1:-1] = (vel[2:] - vel[:-2]) / (2.0 * self.dt)
        acc[0] = (vel[1] - vel[0]) / self.dt if n > 1 else 0
        acc[-1] = (vel[-1] - vel[-2]) / self.dt if n > 1 else 0

        # 三阶导数: jerk
        if n >= 3:
            jerk[1:-1] = (acc[2:] - acc[:-2]) / (2.0 * self.dt)
        jerk[0] = (acc[1] - acc[0]) / self.dt if n > 1 else 0
        jerk[-1] = (acc[-1] - acc[-2]) / self.dt if n > 1 else 0

        return vel, acc, jerk

    @staticmethod
    def magnitude(vec: np.ndarray) -> np.ndarray:
        """各向量的模长"""
        return np.linalg.norm(vec, axis=1)

    # ═══════════════════════════════════════════
    # 频谱分析
    # ═══════════════════════════════════════════

    def compute_psd(self, signal_1d: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """功率谱密度"""
        if HAS_SCIPY and len(signal_1d) >= 64:
            freqs, psd = scipy_signal.welch(
                signal_1d, fs=self.fs,
                nperseg=min(256, len(signal_1d)),
                window="hann",
            )
            return freqs, psd
        else:
            n = len(signal_1d)
            freqs = np.fft.rfftfreq(n, d=self.dt)
            fft_vals = np.fft.rfft(signal_1d - np.mean(signal_1d))
            psd = np.abs(fft_vals) ** 2 / n
            return freqs, psd

    @staticmethod
    def band_energy(freqs: np.ndarray, psd: np.ndarray, band: Tuple[float, float]) -> float:
        """频带能量"""
        mask = (freqs >= band[0]) & (freqs <= band[1])
        return float(np.trapz(psd[mask], freqs[mask]))

    def tremor_ratio(self, pos: np.ndarray) -> float:
        """
        震颤能量比: 8-15Hz / 0.1-5Hz

        疲劳时手部生理震颤 (8-15Hz) 能量相对于主动运动 (0.1-5Hz) 增加。
        """
        ratios = []
        for dim in range(3):
            p = pos[:, dim]
            # 去趋势 (去除低频漂移)
            if HAS_SCIPY:
                b, a = scipy_signal.butter(2, 0.1, btype="high", fs=self.fs)
                p_filt = scipy_signal.filtfilt(b, a, p)
            else:
                p_filt = p - np.polyval(
                    np.polyfit(np.arange(len(p)), p, 3), np.arange(len(p))
                )

            freqs, psd = self.compute_psd(p_filt)
            move_energy = self.band_energy(freqs, psd, MOVEMENT_BAND)
            tremor_energy = self.band_energy(freqs, psd, TREMOR_BAND)
            ratios.append(tremor_energy / (move_energy + 1e-10))

        return float(np.mean(ratios))

    # ═══════════════════════════════════════════
    # 运动特征提取
    # ═══════════════════════════════════════════

    def detect_pauses(self, speed: np.ndarray) -> Tuple[float, int, List[float]]:
        """
        检测停顿

        Returns:
            pause_ratio: 停顿时间占比
            pause_count: 停顿次数
            pause_durations: 每次停顿的时长列表 (秒)
        """
        is_pause = speed < PAUSE_SPEED_THRESHOLD
        pause_ratio = float(np.mean(is_pause))

        # 连续停顿段
        padded = np.concatenate([[0], is_pause.astype(float), [0]])
        changes = np.diff(padded)
        starts = np.where(changes == 1)[0]
        ends = np.where(changes == -1)[0]
        durations = (ends - starts) * self.dt

        return pause_ratio, len(durations), durations.tolist()

    def path_curvature(self, pos: np.ndarray) -> float:
        """路径弯曲度: 实际路径长度 / 首尾直线距离 (越接近1越直)"""
        displacements = np.diff(pos, axis=0)
        path_len = float(np.sum(np.linalg.norm(displacements, axis=1)))
        straight = float(np.linalg.norm(pos[-1] - pos[0]))
        return path_len / (straight + 1e-10)

    def speed_cv(self, speed: np.ndarray) -> float:
        """速度变异系数 CV = σ/μ (疲劳时节奏紊乱, CV 增大)"""
        mu = float(np.mean(speed))
        sigma = float(np.std(speed))
        return sigma / (mu + 1e-10)

    def spectral_arc_length(self, speed: np.ndarray) -> float:
        """
        SPARC: 频谱弧长 — 频域运动平滑度指标

        越小 → 越平滑; 越大 → 越粗糙 (疲劳)
        Reference: Balasubramanian et al. (2015)
        """
        if not HAS_SCIPY or len(speed) < 64:
            return 0.0

        v = (speed - np.mean(speed)) / (np.std(speed) + 1e-10)
        n = len(v)
        freqs = np.fft.rfftfreq(n, d=self.dt)
        mag = np.abs(np.fft.rfft(v)) / n
        mag = mag / (np.max(mag) + 1e-10)

        idx = np.where(mag > 0.05)[0]
        if len(idx) < 2:
            return 0.0

        d_omega = np.diff(freqs[idx])
        d_amp = np.diff(mag[idx])
        return float(np.sum(np.sqrt(d_omega ** 2 + d_amp ** 2)))

    # ═══════════════════════════════════════════
    # 滑动窗口分析
    # ═══════════════════════════════════════════

    def sliding_window_analysis(
        self, pos: np.ndarray, window: float = ANALYSIS_WINDOW
    ) -> List[dict]:
        """
        滑动窗口，每个窗口提取一组运动特征

        Returns:
            list[dict]: 每个窗口含 jerk_mean, tremor_ratio, speed_mean, pause_ratio, ...
        """
        win_samples = int(window * self.fs)
        step = int(win_samples * (1.0 - WINDOW_OVERLAP))
        if step < 1:
            step = 1

        vel, acc, jerk = self.compute_kinematics(pos)
        speed = self.magnitude(vel)
        jerk_mag = self.magnitude(jerk)
        acc_mag = self.magnitude(acc)

        n = len(pos)
        results = []

        for start in range(0, n - win_samples + 1, step):
            end = start + win_samples
            sl = slice(start, end)

            pos_win = pos[sl]
            speed_win = speed[sl]
            jerk_win = jerk_mag[sl]
            acc_win = acc_mag[sl]

            # 1. 运动平滑度
            jerk_mean = float(np.mean(jerk_win))
            jerk_95p = float(np.percentile(jerk_win, 95))

            # 2. 频谱震颤
            tremor_r = self.tremor_ratio(pos_win)

            # 3. 速度统计
            speed_mean = float(np.mean(speed_win))
            speed_std = float(np.std(speed_win))
            speed_max = float(np.max(speed_win))

            # 4. 停顿
            pause_ratio, pause_count, pause_durs = self.detect_pauses(speed_win)
            avg_pause = float(np.mean(pause_durs)) if pause_durs else 0.0

            # 5. 不规则性
            cv = self.speed_cv(speed_win)

            # 6. 路径弯曲度
            curvature = self.path_curvature(pos_win)

            # 7. 加速度抖动
            acc_std = float(np.std(acc_win))

            # 8. SPARC
            sparc = self.spectral_arc_length(speed_win)

            results.append({
                "jerk_mean": jerk_mean,
                "jerk_95p": jerk_95p,
                "tremor_ratio": tremor_r,
                "speed_mean": speed_mean,
                "speed_std": speed_std,
                "speed_max": speed_max,
                "pause_ratio": pause_ratio,
                "pause_count": pause_count,
                "avg_pause_dur": avg_pause,
                "speed_cv": cv,
                "path_curvature": curvature,
                "acc_std": acc_std,
                "sparc": sparc,
                "t_start": start / self.fs,
                "t_end": end / self.fs,
            })

        return results

    # ═══════════════════════════════════════════
    # 疲劳指数
    # ═══════════════════════════════════════════

    @staticmethod
    def _normalize(value: float, baseline: Tuple[float, float], invert: bool = False) -> float:
        """
        归一化到 0~100

        Args:
            value: 原始值
            baseline: (放松时的值, 疲劳时的值)
            invert: True = 值越大越放松 (如速度)
        """
        relaxed, fatigued = baseline
        if invert:
            if value >= relaxed:
                return 0.0
            elif value <= fatigued:
                return 100.0
            return (relaxed - value) / (relaxed - fatigued) * 100.0
        else:
            if value <= relaxed:
                return 0.0
            elif value >= fatigued:
                return 100.0
            return (value - relaxed) / (fatigued - relaxed) * 100.0

    def compute_fatigue_scores(self, metrics: dict) -> dict:
        """
        从单窗口的运动特征计算各维度疲劳分数 (0~100)

        Returns:
            dict 含 jerk_score, tremor_score, speed_score, pause_score, ...
        """
        return {
            "jerk_score": self._normalize(metrics["jerk_mean"], BASELINES["jerk_mean"]),
            "tremor_score": self._normalize(metrics["tremor_ratio"], BASELINES["tremor_ratio"]),
            "speed_score": self._normalize(metrics["speed_mean"], BASELINES["speed_mean"], invert=True),
            "pause_score": self._normalize(metrics["pause_ratio"], BASELINES["pause_ratio"]),
            "irregularity_score": self._normalize(metrics["speed_cv"], BASELINES["speed_cv"]),
            "path_score": self._normalize(metrics["path_curvature"], BASELINES["path_curve"]),
        }

    @staticmethod
    def composite_fatigue(scores: dict) -> Tuple[float, str, str]:
        """综合疲劳指数 + 等级"""
        composite = sum(FATIGUE_WEIGHTS[k] * scores[k] for k in FATIGUE_WEIGHTS)

        if composite < 15:
            level = ("放松", "🟢 完全放松 — 操作轻盈流畅")
        elif composite < 30:
            level = ("轻微", "🔵 轻微疲劳 — 操作略有迟钝")
        elif composite < 50:
            level = ("中等", "🟡 中等疲劳 — 建议短暂休息")
        elif composite < 70:
            level = ("较重", "🟠 较重疲劳 — 操作精度下降明显")
        else:
            level = ("极度", "🔴 极度疲劳 — 强烈建议立即休息")

        return composite, level[0], level[1]

    # ═══════════════════════════════════════════
    # 完整分析
    # ═══════════════════════════════════════════

    def analyze(
        self, pos: np.ndarray, window: float = ANALYSIS_WINDOW
    ) -> dict:
        """
        完整疲劳分析管道

        Args:
            pos: 位置 (N, 3)
            window: 分析窗口 (秒)

        Returns:
            dict: 总体和逐窗口的疲劳评估
        """
        n = len(pos)
        required = int(window * self.fs)
        if n < required:
            print(f"  ⚠️  数据量不足: {n} 点 < 最少需要 {required} 点 ({window:.0f}s)")
            print(f"     将使用全部数据进行分析，结果仅供参考")

        # 滑动窗口分析
        windows = self.sliding_window_analysis(pos, window)
        print(f"     分析窗口: {len(windows)} 个 "
              f"({window:.0f}s 窗, {int(WINDOW_OVERLAP*100)}% 重叠)")

        if not windows:
            return {"error": "no windows"}

        # 各窗口疲劳指数
        fatigue_windows = []
        for w in windows:
            scores = self.compute_fatigue_scores(w)
            composite, level_name, level_desc = self.composite_fatigue(scores)
            fatigue_windows.append({
                "t_start": w["t_start"],
                "t_end": w["t_end"],
                **scores,
                "composite": composite,
                "level_name": level_name,
                "level_desc": level_desc,
            })

        # 总体统计
        composites = [fw["composite"] for fw in fatigue_windows]
        overall = float(np.mean(composites))
        peak = float(np.max(composites))
        _, overall_level_name, overall_level_desc = self.composite_fatigue(
            {k: np.mean([fw[k] for fw in fatigue_windows]) for k in FATIGUE_WEIGHTS}
        )

        # 趋势
        trend = self._trend_analysis(composites)

        print(f"\n  📊 疲劳分析结果:")
        print(f"     ├─ 综合疲劳指数: {overall:.1f}/100  {overall_level_name}")
        print(f"     ├─ 峰值疲劳:     {peak:.1f}/100")
        print(f"     ├─ 疲劳趋势:     {trend}")
        print(f"     └─ {overall_level_desc}")

        return {
            "overall_score": overall,
            "peak_score": peak,
            "overall_level_name": overall_level_name,
            "overall_level_desc": overall_level_desc,
            "trend": trend,
            "num_windows": len(windows),
            "windows": fatigue_windows,
            "raw_metrics": windows,
        }

    @staticmethod
    def _trend_analysis(scores: List[float]) -> str:
        """疲劳趋势分析"""
        if len(scores) < 3:
            return "数据不足"
        x = np.arange(len(scores))
        slope = np.polyfit(x, scores, 1)[0]
        if slope > 0.5:
            return "📈 持续上升 — 操作者越来越疲劳"
        elif slope < -0.5:
            return "📉 持续下降 — 操作者已适应或恢复"
        else:
            return "➡️  稳定 — 疲劳水平保持平稳"

    # ═══════════════════════════════════════════
    # 绘图
    # ═══════════════════════════════════════════

    def plot(self, t: np.ndarray, pos: np.ndarray, result: dict,
             save_path: str = None):
        """生成分析图表 (6 面板)"""
        if not HAS_MPL:
            print("  ⚠️  matplotlib 未安装，跳过绘图")
            return

        vel, acc, jerk = self.compute_kinematics(pos)
        speed = self.magnitude(vel)
        jerk_mag = self.magnitude(jerk)
        acc_mag = self.magnitude(acc)

        fig, axes = plt.subplots(6, 1, figsize=(14, 16), sharex=True)

        # ── 图1: 3D 轨迹 (俯视图: XY) ──
        ax = axes[0]
        sc = ax.scatter(pos[:, 0], pos[:, 1], c=t, cmap="viridis",
                        s=1.5, alpha=0.6)
        ax.plot(pos[0, 0], pos[0, 1], "go", markersize=10, label="起点")
        ax.plot(pos[-1, 0], pos[-1, 1], "ro", markersize=10, label="终点")
        ax.set_xlabel("X (m)")
        ax.set_ylabel("Y (m)")
        ax.set_title("Omega.7 手柄 2D 轨迹 (颜色=时间)")
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.axis("equal")
        cbar = plt.colorbar(sc, ax=ax)
        cbar.set_label("时间 (s)")

        # ── 图2: 速度 + 停顿检测 ──
        ax = axes[1]
        ax.plot(t, speed, "b-", lw=0.8, alpha=0.7)
        ax.axhline(PAUSE_SPEED_THRESHOLD, color="r", ls="--", lw=0.8,
                   alpha=0.5, label=f"停顿阈值 ({PAUSE_SPEED_THRESHOLD} m/s)")
        ax.fill_between(t, 0, speed, where=(speed < PAUSE_SPEED_THRESHOLD),
                         color="r", alpha=0.1, label="停顿段")
        ax.set_ylabel("速度 (m/s)")
        ax.set_title("运动速度 — 红色区域 = 停顿")
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)

        # ── 图3: Jerk (运动平滑度) ──
        ax = axes[2]
        ax.plot(t, jerk_mag, "r-", lw=0.5, alpha=0.6)
        ax.set_ylabel("Jerk (m/s³)")
        ax.set_title("运动平滑度 (Jerk) — 值越大越不平滑")
        ax.grid(True, alpha=0.3)

        # ── 图4: 功率谱 (取中段) ──
        ax = axes[3]
        mid = len(pos) // 2
        half = min(256, len(pos) // 4)
        colors = ["r", "g", "b"]
        labels = ["X 轴", "Y 轴", "Z 轴"]
        for dim in range(3):
            freqs, psd = self.compute_psd(pos[mid-half:mid+half, dim])
            ax.semilogy(freqs, psd, color=colors[dim], alpha=0.6,
                        lw=0.8, label=labels[dim])
        ax.axvspan(TREMOR_BAND[0], TREMOR_BAND[1], color="r", alpha=0.08,
                    label=f"震颤频带 {TREMOR_BAND[0]}-{TREMOR_BAND[1]}Hz")
        ax.axvspan(MOVEMENT_BAND[0], MOVEMENT_BAND[1], color="b", alpha=0.05,
                    label=f"运动频带 {MOVEMENT_BAND[0]}-{MOVEMENT_BAND[1]}Hz")
        ax.set_xlim(0, 20)
        ax.set_xlabel("频率 (Hz)")
        ax.set_ylabel("功率谱密度")
        ax.set_title("功率谱 — 8-15Hz 能量反映疲劳震颤")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

        # ── 图5: 疲劳时序 ──
        ax = axes[4]
        win_data = result.get("windows", [])
        if win_data:
            win_t = [(w["t_start"] + w["t_end"]) / 2 for w in win_data]
            composites = [w["composite"] for w in win_data]

            ax.plot(win_t, composites, "k-", lw=2, label="综合疲劳指数")
            ax.fill_between(win_t, composites, 0, alpha=0.12, color="red")

            # 等级分界线
            for level, color, y in [("放松", "green", 15),
                                     ("轻微", "blue", 30),
                                     ("中等", "gold", 50),
                                     ("较重", "orange", 70)]:
                ax.axhline(y, color=color, ls="--", lw=0.8, alpha=0.4)
                ax.text(t[-1] * 0.97, y + 1.5, level, fontsize=8,
                        color=color, alpha=0.6, ha="right")

        ax.set_ylabel("疲劳指数 (0-100)")
        ax.set_ylim(0, 105)
        ax.set_title("疲劳指数时序")
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)

        # ── 图6: 疲劳维度雷达图 ──
        ax = axes[5]
        if win_data:
            last = win_data[-1]
            dim_keys = ["jerk_score", "tremor_score", "speed_score",
                        "pause_score", "irregularity_score", "path_score"]
            dim_labels = ["平滑度", "震颤", "速度", "停顿", "不规则", "路径"]
            values = [last.get(k, 0) for k in dim_keys]

            angles = np.linspace(0, 2 * np.pi, len(dim_labels), endpoint=False).tolist()
            values_closed = values + values[:1]
            angles_closed = angles + angles[:1]
            labels_closed = dim_labels + dim_labels[:1]

            ax.plot(angles_closed, values_closed, "o-", color="red", lw=2)
            ax.fill(angles_closed, values_closed, alpha=0.25, color="red")
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(dim_labels, fontsize=10)
            ax.set_ylim(0, 100)
            ax.set_title(f"疲劳维度雷达 (综合: {last['composite']:.0f}/100)")
            ax.grid(True, alpha=0.3)

        plt.xlabel("时间 (s)")
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            print(f"  📈 分析图已保存: {save_path}")
        plt.close()

    # ═══════════════════════════════════════════
    # 报告生成
    # ═══════════════════════════════════════════

    def generate_report(self, result: dict, data: dict = None) -> str:
        """生成文本分析报告"""
        lines = []
        lines.append("=" * 65)
        lines.append("  🧠 Omega.7 轨迹疲劳分析报告")
        lines.append("=" * 65)
        lines.append("")

        # 数据源
        if data and "meta" in data:
            m = data["meta"]
            lines.append(f"  数据源:  {m.get('filepath', 'N/A')}")
            lines.append(f"  采样数:  {m.get('n_samples', 0)} 点")
            lines.append(f"  时长:    {m.get('duration', 0):.1f} 秒")
            lines.append(f"  频率:    {m.get('avg_freq', 0):.0f} Hz")

        # 操作参数（如果有）
        if data and "params" in data:
            p = data["params"]
            param_strs = []
            for key, label in [("K_trans", "刚度"), ("damping_ratio", "阻尼比"),
                               ("K_fb", "力反馈增益"), ("scale", "映射比例")]:
                if key in p and len(p[key]) > 0:
                    val = p[key][0]
                    param_strs.append(f"{label}={val:.1f}")
            if param_strs:
                lines.append(f"  操作参数: {', '.join(param_strs)}")

        lines.append("")

        # 总体评估
        lines.append("─" * 65)
        lines.append("  📊 总体疲劳评估")
        lines.append("─" * 65)
        lines.append(f"  综合疲劳指数: {result['overall_score']:.1f} / 100")
        lines.append(f"  峰值疲劳:     {result['peak_score']:.1f} / 100")
        lines.append(f"  疲劳等级:     {result['overall_level_name']}")
        lines.append(f"  疲劳描述:     {result['overall_level_desc']}")
        lines.append(f"  疲劳趋势:     {result['trend']}")
        lines.append("")

        # 各维度明细
        if result.get("windows"):
            lines.append("─" * 65)
            lines.append("  📋 各维度疲劳明细 (全时段平均)")
            lines.append("─" * 65)

            dims = [
                ("jerk_score", "运动平滑度 (Jerk)", "越小越平滑"),
                ("tremor_score", "生理震颤能量", "越大手抖越明显"),
                ("speed_score", "运动速度 (反向)", "越大速度越慢"),
                ("pause_score", "停顿时间占比", "越大停顿越多"),
                ("irregularity_score", "运动不规则性", "越大节奏越乱"),
                ("path_score", "路径弯曲度", "越大路径越绕"),
            ]

            for key, name, desc in dims:
                vals = [w.get(key, 0) for w in result["windows"]]
                avg = float(np.mean(vals))
                p95 = float(np.percentile(vals, 95))
                bar_len = max(1, int(avg / 100 * 28))
                bar = "█" * bar_len + "░" * (28 - bar_len)
                lines.append(f"  {name:20s} {bar} {avg:5.1f}  (P95={p95:.0f})  — {desc}")

            lines.append("")

            # 时序
            lines.append("─" * 65)
            lines.append("  📈 疲劳时序 (每窗口变化)")
            lines.append("─" * 65)
            for w in result["windows"]:
                t_start = w["t_start"]
                comp = w["composite"]
                bar_len = max(1, int(comp / 100 * 20))
                bar = "▓" * bar_len + "░" * (20 - bar_len)
                lines.append(f"  t={t_start:>6.1f}s  {bar}  {comp:5.1f}  {w['level_name']}")

        lines.append("")
        lines.append("─" * 65)
        lines.append("  💡 建议")
        lines.append("─" * 65)
        overall = result["overall_score"]
        if overall < 15:
            lines.append("  ✅ 操作者状态良好，继续当前操作节奏")
        elif overall < 30:
            lines.append("  🔵 轻微疲劳，建议每 20 分钟休息 1 分钟")
        elif overall < 50:
            lines.append("  🟡 中等疲劳，建议每 10 分钟休息 2 分钟")
            lines.append("  💡 可尝试降低阻尼比 ζ 或提高映射比例，减轻操作负担")
        elif overall < 70:
            lines.append("  🟠 较重疲劳，操作精度已下降")
            lines.append("  💡 建议立即休息 5 分钟")
            lines.append("  💡 可减小力反馈增益 K_fb 以降低操作负荷")
        else:
            lines.append("  🔴 极度疲劳，建议停止操作并休息")
            lines.append("  💡 过度疲劳下操作可能损坏工件或导致安全事故")

        lines.append("")
        lines.append("=" * 65)
        lines.append("  报告结束")
        lines.append("=" * 65)

        return "\n".join(lines)


# ═══════════════════════════════════════════════════════
# 主函数
# ═══════════════════════════════════════════════════════

def find_latest_trajectory(data_dir: str = "data") -> Optional[str]:
    """查找最新的轨迹 CSV 文件"""
    path = Path(data_dir)
    if not path.exists():
        return None
    csv_files = sorted(path.glob("trajectory_*.csv"))
    return str(csv_files[-1]) if csv_files else None


def main():
    parser = argparse.ArgumentParser(
        description="Omega.7 轨迹离线疲劳分析工具"
    )
    parser.add_argument(
        "--load", "-l", type=str, default=None,
        help="加载轨迹 CSV 文件",
    )
    parser.add_argument(
        "--latest", action="store_true",
        help="自动分析 data/ 目录下最新的轨迹文件",
    )
    parser.add_argument(
        "--save-plot", action="store_true",
        help="生成分析图表 (PNG)",
    )
    parser.add_argument(
        "--window", type=float, default=ANALYSIS_WINDOW,
        help=f"分析窗口大小 (秒), 默认 {ANALYSIS_WINDOW}s",
    )
    args = parser.parse_args()

    # ── 确定输入文件 ──
    csv_path = None
    if args.load:
        csv_path = args.load
    elif args.latest:
        csv_path = find_latest_trajectory()
        if csv_path:
            print(f"  🔍 自动检测最新轨迹: {csv_path}")
        else:
            print("❌ data/ 目录下未找到 trajectory_*.csv 文件")
            sys.exit(1)
    else:
        parser.print_help()
        print("\n💡 用法示例:")
        print("   python3 my_test/omega7_trajectory_analyzer.py --load data/trajectory_*.csv")
        print("   python3 my_test/omega7_trajectory_analyzer.py --latest --save-plot")
        sys.exit(1)

    if not os.path.exists(csv_path):
        print(f"❌ 文件不存在: {csv_path}")
        sys.exit(1)

    print("=" * 65)
    print("  🧠 Omega.7 轨迹疲劳分析")
    print("=" * 65)

    # ── 加载数据 ──
    data = load_trajectory_csv(csv_path)
    if data is None:
        sys.exit(1)

    # ── 确定采样频率 ──
    t = data["t"]
    pos = data["pos"]
    dt_median = float(np.median(np.diff(t))) if len(t) > 1 else 0.005
    fs = 1.0 / dt_median if dt_median > 0 else 200.0
    print(f"     采样间隔: {dt_median*1000:.1f} ms → {fs:.0f} Hz")

    # ── 分析 ──
    analyzer = FatigueAnalyzer(sample_freq=fs)
    result = analyzer.analyze(pos, window=args.window)

    if "error" in result:
        print(f"  ❌ 分析失败: {result['error']}")
        sys.exit(1)

    # ── 报告 ──
    report = analyzer.generate_report(result, data)
    print("\n" + report)

    report_path = csv_path.replace(".csv", "_analysis.txt")
    with open(report_path, "w") as f:
        f.write(report)
    print(f"\n  📄 报告已保存: {report_path}")

    # ── 图表 ──
    if args.save_plot and HAS_MPL:
        plot_path = csv_path.replace(".csv", "_analysis.png")
        analyzer.plot(t, pos, result, save_path=plot_path)

    print("\n✅ 分析完成")


if __name__ == "__main__":
    main()
