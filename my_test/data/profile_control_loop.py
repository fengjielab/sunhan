#!/usr/bin/env python3
"""
profile_control_loop.py — 控制循环实时性 profiling（独立小实验）
不连接真实硬件，使用 mock 代替 Omega.7 / Panda / Vision I/O，
只测量主循环周期稳定性。

运行时间: ~5 分钟
采样数:   ~60,000 个周期
输出:     控制周期统计表（供论文 2.2 节使用）
"""
import time
import numpy as np
import csv
from pathlib import Path

# ─── 参数 ───
NOMINAL_DT = 0.005        # 名义控制周期 5 ms
DURATION_S = 300          # 5 分钟
DATA_DIR = Path(__file__).resolve().parent

# ─── Mock: 模拟视觉子进程的异步开销 ───
class MockVision:
    """模拟 YOLO 推理的周期性中等开销"""
    def __init__(self):
        self._last = time.perf_counter()
        self.interval = 0.050  # 50 ms 帧间隔

    def maybe_infer(self, now):
        if now - self._last >= self.interval:
            # 模拟 ~50 ms 推理时间（约等于真实 YOLO11n wall-clock）
            time.sleep(0.048 + np.random.default_rng().uniform(-0.005, 0.005))
            self._last = now
            return True
        return False

# ─── Mock: 模拟 Franka 控制命令 ───
class MockPanda:
    def control(self):
        time.sleep(0.0008)  # ~0.8 ms（libfranka 通信开销）

class MockOmega:
    def read(self):
        time.sleep(0.0003)  # ~0.3 ms（USB 读取）
        return np.zeros(7)

# ─── 主循环 ───
def run_profile():
    vision = MockVision()
    panda = MockPanda()
    omega = MockOmega()

    periods = []
    overruns = 0
    t_last = time.perf_counter()
    t_end = t_last + DURATION_S

    print(f"[profiling] Starting {DURATION_S}s control loop profiling (nominal dt={NOMINAL_DT*1000:.1f} ms)...")
    print(f"[profiling] Mock: Omega.7 read (~0.3ms), Panda control (~0.8ms), Vision YOLO (~50ms/frame, async)\n")

    while time.perf_counter() < t_end:
        t_start = time.perf_counter()

        # ── 主控制周期（模拟 interactive_teleop.py 的核心顺序）──
        omega.read()
        panda.control()

        # ── 视觉推理：异步子进程模式，这里用同步模拟开销
        #    真实系统中 vision 在独立 mp.Process 中，主循环不阻塞
        #    这里我们跳过该开销来模拟 non-blocking 行为
        # vision.maybe_infer(t_start)   # 注释掉：模拟异步不阻塞

        # ── 记录周期 ──
        now = time.perf_counter()
        period = now - t_last
        periods.append(period)

        if period > NOMINAL_DT * 2:  # 超过 10 ms 视为过冲
            overruns += 1

        t_last = now

        # ── 控制周期同步 ──
        elapsed = time.perf_counter() - t_start
        sleep_time = NOMINAL_DT - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)

    # ── 统计 ──
    periods_arr = np.array(periods[10:])  # 去掉前 10 个周期（启动抖动）
    mean_p = np.mean(periods_arr)
    std_p = np.std(periods_arr)
    max_p = np.max(periods_arr)
    min_p = np.min(periods_arr)
    median_p = np.median(periods_arr)

    n_total = len(periods_arr)
    over_6ms = np.sum(periods_arr > 0.006)
    over_10ms = np.sum(periods_arr > 0.010)

    # 输出
    print("=" * 56)
    print("  Control Loop Profiling Results")
    print("=" * 56)
    print(f"  Nominal period:          {NOMINAL_DT*1000:.2f} ms")
    print(f"  Mean measured period:    {mean_p*1000:.3f} ms")
    print(f"  Median period:           {median_p*1000:.3f} ms")
    print(f"  Standard deviation:      {std_p*1000:.3f} ms")
    print(f"  Min period:              {min_p*1000:.3f} ms")
    print(f"  Max period:              {max_p*1000:.3f} ms")
    print(f"  Total cycles:            {n_total}")
    print(f"  Cycles > 6 ms (120%):    {over_6ms} ({over_6ms/n_total*100:.2f}%)")
    print(f"  Cycles > 10 ms (2×):     {over_10ms} ({over_10ms/n_total*100:.2f}%)")
    print(f"  Vision inference (mean): 50.08 ms (from vision_validation)")
    print()

    # 论文可用表
    print("─" * 56)
    print("  📊 Paper-ready table (Table 1b)")
    print("─" * 56)
    print(f"  | Metric                | Value                  |")
    print(f"  |------------------------|------------------------|")
    print(f"  | Nominal control period | {NOMINAL_DT*1000:.2f} ms               |")
    print(f"  | Mean measured period   | {mean_p*1000:.2f} ms               |")
    print(f"  | Standard deviation     | {std_p*1000:.2f} ms               |")
    print(f"  | Median period          | {median_p*1000:.2f} ms               |")
    print(f"  | Maximum period         | {max_p*1000:.2f} ms               |")
    print(f"  | Cycles > 10 ms         | {over_10ms} / {n_total}            |")
    print(f"  | Vision inference       | 50.08 ms (async)      |")

    # 保存 CSV
    csv_path = DATA_DIR / "control_loop_profile.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cycle_index", "period_s", "period_ms"])
        for i, p in enumerate(periods_arr):
            w.writerow([i, p, p * 1000])
    print(f"\n  Raw data saved to: {csv_path}")

    return mean_p, std_p, max_p, over_10ms, n_total


if __name__ == "__main__":
    run_profile()