#!/usr/bin/env python3
"""
run_control_profiling.py — 控制循环实时性 profiling（真实硬件，5 分钟）
=====================================================================
在 interactive_teleop.py 的基础上，在每个控制周期记录 perf_counter 时间戳，
输出 CSV 供论文 Table 1b 使用。

运行方式:
    python my_test/run_control_profiling.py --duration 300
    # 可选: --mode vision  开启视觉线程

要求:
    - Omega.7 已连接
    - Franka Panda 已连接并处于控制模式
    - (可选) RealSense D435i 已连接（若使用 --mode vision）
"""
import sys
import os
import time
import csv
import argparse
import threading
import numpy as np
from pathlib import Path

# 把 my_test 加入 path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from interactive_teleop import TeleopController  # 你的核心类

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


class ProfilingController(TeleopController):
    """继承 TeleopController，在控制循环中偷偷记录 perf_counter"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._profiling_periods = []   # 存储每个周期的 dt (秒)
        self._profiling_timestamps = []  # 每个周期的 perf_counter 时间戳

    def run_profiling(self, duration_s: float):
        """运行 profiling 模式（与 run() 类似但记录周期数据）"""
        self.running = True

        dt = 1.0 / 200.0  # 5 ms
        dt_gripper = 1.0 / 10.0
        dt_status = 1.0 / 5.0
        dt_keyboard = 1.0 / 30.0

        t_start_profiling = time.perf_counter()
        t_end_profiling = t_start_profiling + duration_s

        # 启动键盘线程
        kb_thread = threading.Thread(target=self._keyboard_loop, daemon=True)
        kb_thread.start()
        self._print_help()

        # 初始化预设
        self._set_preset("standard")

        print(f"\n[profiling] Recording {duration_s}s of control loop timing...")
        print(f"[profiling] Nominal dt = {dt*1000:.1f} ms")
        print(f"[profiling] Vision {'enabled' if self._vision_enabled else 'disabled'}\n")

        next_status_time = time.perf_counter()
        last_gripper_time = 0.0
        last_gripper_ctrl_time = 0.0
        last_gripper_measure_time = 0.0
        last_kb_time = 0.0
        last_cycle_perf = time.perf_counter()
        vision_start_time = time.time() + 3.0
        vision_start_announced = False

        try:
            while self.running:
                t_start = time.perf_counter()
                now = time.time()
                now_perf = t_start

                # ── 记录实际控制周期 ──
                cycle_dt = now_perf - last_cycle_perf
                self._profiling_periods.append(cycle_dt)
                self._profiling_timestamps.append(now_perf)
                last_cycle_perf = now_perf

                # 检查是否超时
                if now_perf >= t_end_profiling:
                    print("[profiling] Duration reached, stopping...")
                    self.running = False
                    break

                # ── 标准遥操作逻辑（从 interactive_teleop.run() 提取）──
                # 视觉启动
                if self._vision_enabled and not self._vision_active:
                    if now >= vision_start_time:
                        self._start_vision_thread()
                    elif not vision_start_announced:
                        print("[profiling] Vision thread will start in 3s...")
                        vision_start_announced = True

                # Omega.7 读取
                pos_ret = self._read_omega()
                if pos_ret < 0:
                    time.sleep(0.001)
                    continue

                # 增量位置映射 + Franka 控制
                self._update_slave_position()
                self._update_impedance_control()

                # 力反馈
                self._update_force_feedback()

                # 夹爪控制（降频）
                if now - last_gripper_ctrl_time >= dt_gripper:
                    self._update_gripper()
                    last_gripper_ctrl_time = now

                # 状态打印
                if now_perf - next_status_time >= 0:
                    elapsed = now - self._trajectory_start_time if hasattr(self, '_trajectory_start_time') else 0
                    n_cycles = len(self._profiling_periods)
                    mean_dt = np.mean(self._profiling_periods[-100:]) * 1000 if n_cycles > 0 else 0
                    print(f"\r  [profiling] cycles={n_cycles:>6d}  mean_dt(last100)={mean_dt:.2f}ms", end="", flush=True)
                    next_status_time = now_perf + 2.0

                # ── 周期同步 ──
                elapsed = time.perf_counter() - t_start
                sleep_time = dt - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except KeyboardInterrupt:
            print("\n[profiling] Interrupted by user")
        finally:
            self.running = False
            # 安全停止
            try:
                self._stop_robot()
            except Exception:
                pass

        # ── 统计 ──
        periods_arr = np.array(self._profiling_periods[20:])  # 跳过前 20 个周期（启动抖动）
        mean_ms = np.mean(periods_arr) * 1000
        std_ms = np.std(periods_arr) * 1000
        median_ms = np.median(periods_arr) * 1000
        max_ms = np.max(periods_arr) * 1000
        min_ms = np.min(periods_arr) * 1000
        n_total = len(periods_arr)
        over_10ms = np.sum(periods_arr > 0.010)

        print("\n")
        print("=" * 60)
        print("  Control Loop Profiling Results (REAL HARDWARE)")
        print("=" * 60)
        print(f"  Nominal period:            5.00 ms")
        print(f"  Mean measured period:      {mean_ms:.2f} ms")
        print(f"  Median period:             {median_ms:.2f} ms")
        print(f"  Standard deviation:        {std_ms:.2f} ms")
        print(f"  Min period:                {min_ms:.2f} ms")
        print(f"  Max period:                {max_ms:.2f} ms")
        print(f"  Total cycles:              {n_total}")
        print(f"  Cycles > 10 ms (2×):       {over_10ms} ({over_10ms/n_total*100:.2f}%)")
        print(f"  Vision enabled:            {self._vision_enabled}")
        print()

        # ── 保存 CSV ──
        csv_path = DATA_DIR / "control_loop_profile.csv"
        with open(csv_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["cycle_index", "timestamp_perf", "period_s", "period_ms"])
            for i, (ts, p) in enumerate(zip(self._profiling_timestamps[20:], periods_arr)):
                w.writerow([i, f"{ts:.6f}", f"{p:.6f}", f"{p*1000:.3f}"])
        print(f"  Raw data saved to: {csv_path}")

        # ── 论文 Table 1b ──
        print()
        print("─" * 60)
        print("  📊 Paper-ready Table")
        print("─" * 60)
        print(f"  | Metric                  | Value              |")
        print(f"  |--------------------------|--------------------|")
        print(f"  | Nominal control period   | 5.00 ms            |")
        print(f"  | Mean measured period     | {mean_ms:.2f} ms            |")
        print(f"  | Median period            | {median_ms:.2f} ms            |")
        print(f"  | Standard deviation       | {std_ms:.2f} ms            |")
        print(f"  | Minimum period           | {min_ms:.2f} ms            |")
        print(f"  | Maximum period           | {max_ms:.2f} ms            |")
        print(f"  | Cycles > 10 ms           | {over_10ms} / {n_total}       |")
        print(f"  | Total cycles             | {n_total}              |")
        print(f"  | Vision enabled           | {str(self._vision_enabled):<20} |")

        return mean_ms, std_ms, median_ms, max_ms, over_10ms, n_total


def main():
    parser = argparse.ArgumentParser(description="Control loop jitter profiling")
    parser.add_argument("--duration", type=float, default=300,
                        help="Profiling duration in seconds (default: 300)")
    parser.add_argument("--mode", type=str, default="default",
                        choices=["default", "vision"],
                        help="Teleop mode: default or vision")
    args = parser.parse_args()

    print("=" * 60)
    print("  Mechatronic System Control Loop Profiling")
    print(f"  Duration: {args.duration}s | Mode: {args.mode}")
    print("=" * 60)
    print()
    print("  Ensure hardware is connected before proceeding:")
    print("    - Omega.7 force-feedback master")
    print("    - Franka Panda robot arm (in control mode)")
    if args.mode == "vision":
        print("    - Intel RealSense D435i camera")
    print()

    controller = ProfilingController(mode=args.mode)
    controller.run_profiling(duration_s=args.duration)


if __name__ == "__main__":
    main()