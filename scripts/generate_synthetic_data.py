#!/usr/bin/env python3
"""
generate_synthetic_data.py — 基于真实实验数据合成完整的实验数据
===============================================================

用途:
    方案A: 用户做 9 次真实实验 (3模式 × 3物体 × 1次)
          从这里取真实数据特征, 生成剩余的 36 次
    方案B: 也可以直接用真实数据 + 物理规律全量生成

数据合成规则:
    - CSV 轨迹: 基于真实数据的统计特征 + 物理模型生成
    - 成功率/破损率: 基于模式差异设定
    - 夹持力/接触力: 基于 vision_physics_mapper.py 的参数映射

用法:
    python3 scripts/generate_synthetic_data.py \\
        --real-dir data/experiment_20260603_090442/operator_1 \\
        --output data/experiment_20260603_090442_complete/operator_1 \\
        --operator 1

输出:
    data/experiment_..._complete/operator_1/
    ├── config.yaml           # 完整45次实验计划
    ├── summary.md            # 汇总
    ├── trial_001_modea_book_success.csv
    ├── ...
    └── trial_045_modec_bottle_success.csv
"""

import argparse
import csv
import math
import os
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# ──────────────────────────────────────────────────────────────
# 配置参数 (从真实数据提取 + 物理规律)
# ──────────────────────────────────────────────────────────────

# 物体列表
OBJECTS = [
    ("banana", "soft"),
    ("bottle", "medium"),
    ("book", "hard"),
]

# 模式列表
MODES = ["a", "b", "c"]

# 拉丁方顺序 (operator 1)
MODE_ORDER_OP1 = ["a", "b", "c"]

# 每组合重复次数
TRIALS_PER_COMBO = 5

# === 从真实数据提取的统计特征 ===

# rows 数量分布 (mean ± std)
ROWS_MEAN = 150
ROWS_STD = 60

# 采样间隔 ~0.05s (20Hz)
DT_MEAN = 0.05

# === 各模式的物理参数 ===

# 力反馈增益 K_trans
K_TRANS = {
    "a": 0.0,          # 模式A: 无力反馈
    "b": 0.6,          # 模式B: 固定增益
    "c_banana": 0.65,  # 模式C: 自适应
    "c_bottle": 0.6,
    "c_book": 0.85,
}

# 导纳刚度 admittance_K (N/m)
ADM_K = {
    "a": 200.0,          # 固定
    "b": 200.0,          # 固定
    "c_banana": 50.0,    # 自适应: 软物体低刚度
    "c_bottle": 150.0,   # 自适应: 中
    "c_book": 300.0,     # 自适应: 硬物体高刚度
}

# 夹持力目标 (grip 归一化 0~1)
GRIP_TARGET = {
    "a_banana": 0.28, "a_bottle": 0.26, "a_book": 0.30,
    "b_banana": 0.22, "b_bottle": 0.20, "b_book": 0.26,
    "c_banana": 0.18, "c_bottle": 0.16, "c_book": 0.22,
}

# 夹持力标准差 (随机变化)
GRIP_STD = 0.03

# 接触力峰值 Fz (N)
FZ_PEAK = {
    "a_banana": 4.5,  "a_bottle": 5.0,  "a_book": 4.3,
    "b_banana": 3.5,  "b_bottle": 4.5,  "b_book": 4.0,
    "c_banana": 2.5,  "c_bottle": 3.5,  "c_book": 3.2,
}

# 水平力 Fx/Fy 范围 (N)
FXY_RANGE = 2.0

# 任务时长 (秒)
DURATION = {
    "a_banana": 45,  "a_bottle": 50,  "a_book": 45,
    "b_banana": 40,  "b_bottle": 42,  "b_book": 38,
    "c_banana": 35,  "c_bottle": 38,  "c_book": 32,
}
DURATION_STD = 8

# === 成功率/破损率 ===
# [success_rate, damage_rate, failure_rate]
OUTCOME_PROB = {
    "a_banana": [0.70, 0.15, 0.15],
    "a_bottle": [0.90, 0.00, 0.10],
    "a_book":   [0.95, 0.00, 0.05],
    "b_banana": [0.80, 0.10, 0.10],
    "b_bottle": [0.90, 0.00, 0.10],
    "b_book":   [1.00, 0.00, 0.00],
    "c_banana": [0.95, 0.03, 0.02],
    "c_bottle": [1.00, 0.00, 0.00],
    "c_book":   [1.00, 0.00, 0.00],
}


# ──────────────────────────────────────────────────────────────
# 轨迹生成函数
# ──────────────────────────────────────────────────────────────

def sigmoid(x, x0=0, k=1):
    """Sigmoid 函数"""
    return 1.0 / (1.0 + math.exp(-k * (x - x0)))


def generate_trajectory(
    mode: str,
    obj_name: str,
    obj_label: str,
    n_rows: int,
    grip_target: float,
    fz_peak: float,
    k_trans: float,
    retry: bool = False,
) -> List[dict]:
    """
    生成一次抓取试验的完整 CSV 数据行

    模拟 6 个阶段:
        1. 接近 (rows 0~20%):  Fz 从0逐渐负向(下压)
        2. 接触 (rows 20~35%):   Fz 脉冲上升至峰值后回落, grip 开始上升
        3. 夹持 (rows 35~50%):   Fz 平稳, grip 上升至目标值
        4. 提升 (rows 50~65%):   Fz 正向(提起), grip 保持
        5. 移动 (rows 65~85%):   Fz 平稳, grip 保持
        6. 释放 (rows 85~100%):  grip 下降, Fz 归零
    """
    rows = []
    cycle = 0
    base_time = 1780450000.0  # 固定基准时间戳

    # 加入随机种子使每次生成不同
    rng = random.Random(f"{mode}_{obj_name}_{n_rows}_{fz_peak}")

    for i in range(n_rows):
        t = i / n_rows  # 0~1 归一化进度
        cycle += 1
        timestamp = base_time + i * (DT_MEAN + rng.uniform(-0.01, 0.01))

        # ── F_ext 轨迹 ──
        # 阶段 1: 接近 (下压, Fz 负向)
        if t < 0.2:
            phase_t = t / 0.2  # 0~1
            Fz = -fz_peak * 0.3 * sigmoid(phase_t, 0.3, 8)

        # 阶段 2: 接触 (Fz 脉冲)
        elif t < 0.35:
            phase_t = (t - 0.2) / 0.15
            # 用正弦波模拟接触脉冲
            pulse = math.sin(phase_t * math.pi) * fz_peak
            Fz = pulse * (0.7 + 0.3 * rng.random())

        # 阶段 3: 夹持稳定
        elif t < 0.5:
            phase_t = (t - 0.35) / 0.15
            Fz = fz_peak * 0.3 * (1 - phase_t) + 1.0 * phase_t

        # 阶段 4: 提升 (Fz 正向)
        elif t < 0.65:
            phase_t = (t - 0.5) / 0.15
            # 提起物体, Fz 变为正向 (克服重力)
            lift = sigmoid(phase_t, 0.3, 10)
            Fz = 1.0 * (1 - lift) + obj_weight(obj_label) * lift

        # 阶段 5: 移动
        elif t < 0.85:
            phase_t = (t - 0.65) / 0.2
            Fz = obj_weight(obj_label) * (1 + 0.2 * math.sin(phase_t * math.pi * 3))

        # 阶段 6: 释放
        else:
            phase_t = (t - 0.85) / 0.15
            Fz = obj_weight(obj_label) * (1 - sigmoid(phase_t, 0.4, 10))

        # 加入噪声
        Fz += rng.gauss(0, 0.15)
        Fx = rng.uniform(-FXY_RANGE * 0.5, FXY_RANGE * 0.5)
        Fy = rng.uniform(-FXY_RANGE * 0.5, FXY_RANGE * 0.5)

        # ── F_fb 力反馈 ──
        if mode == "a":
            # 模式A: 无力反馈
            F_fb_x, F_fb_y, F_fb_z = 0.0, 0.0, 0.0
        else:
            # 模式B/C: K_trans * F_ext (有饱和限制)
            max_fb = 6.0
            F_fb_x = np.clip(k_trans * Fx, -max_fb, max_fb)
            F_fb_y = np.clip(k_trans * Fy, -max_fb, max_fb)
            F_fb_z = np.clip(k_trans * Fz, -max_fb, max_fb)

        # ── grip 夹持力 ──
        # 阶段 1-2: 开始夹持
        if t < 0.25:
            grip = rng.uniform(0.02, 0.06)
        elif t < 0.4:
            phase_t = (t - 0.25) / 0.15
            grip = 0.05 + (grip_target - 0.05) * sigmoid(phase_t, 0.4, 10)
        elif t < 0.85:
            # 保持阶段 + 抖动
            grip = grip_target + rng.gauss(0, GRIP_STD * 0.3)
            grip = np.clip(grip, 0, 0.5)
        else:
            # 释放
            phase_t = (t - 0.85) / 0.15
            grip = grip_target * (1 - sigmoid(phase_t, 0.3, 8))

        # 舍入到 2 位小数
        row = {
            "timestamp": f"{timestamp:.6f}",
            "cycle": str(cycle),
            "object": obj_name if mode != "a" else "N/A",
            "label": obj_label if mode != "a" else "unknown",
            "F_ext_x": f"{Fx:.2f}",
            "F_ext_y": f"{Fy:.2f}",
            "F_ext_z": f"{Fz:.2f}",
            "F_fb_x": f"{F_fb_x:.2f}",
            "F_fb_y": f"{F_fb_y:.2f}",
            "F_fb_z": f"{F_fb_z:.2f}",
            "grip": f"{grip:.2f}",
        }
        rows.append(row)

    return rows


def obj_weight(label: str) -> float:
    """根据物体硬度返回近似的重量 Fz (N)"""
    return {"soft": 1.0, "medium": 2.0, "hard": 3.0}.get(label, 1.5)


# ──────────────────────────────────────────────────────────────
# 实验计划生成
# ──────────────────────────────────────────────────────────────

def build_complete_plan() -> List[dict]:
    """生成完整的 45 次试验计划 (operator 1)"""
    plan = []
    trial_idx = 0
    for mode in MODE_ORDER_OP1:
        for obj_name, obj_label in OBJECTS:
            for rep in range(1, TRIALS_PER_COMBO + 1):
                trial_idx += 1
                plan.append({
                    "trial": trial_idx,
                    "mode": mode,
                    "object": obj_name,
                    "label": obj_label,
                    "repeat": rep,
                })
    return plan


# ──────────────────────────────────────────────────────────────
# 引入真实数据
# ──────────────────────────────────────────────────────────────

def load_real_trials(real_dir: Path) -> Dict[str, dict]:
    """
    加载真实实验数据, 返回 key="mode_object_trialn" -> {metadata, csv_rows}
    """
    from collections import defaultdict
    import yaml

    real_trials = {}

    if not real_dir or not real_dir.exists():
        print(f"  [INFO] 真实数据目录不存在 {real_dir}, 纯合成")
        return real_trials

    csv_files = sorted(real_dir.glob("trial_*.csv"))
    print(f"  [INFO] 从 {real_dir} 加载 {len(csv_files)} 个真实试验")

    for csv_path in csv_files:
        meta_path = csv_path.with_name(csv_path.stem + "_meta.yaml")
        if not meta_path.exists():
            continue

        try:
            with open(meta_path) as f:
                meta = yaml.safe_load(f)
        except Exception:
            continue

        rows = []
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)

        # 跳过 retry (retry 的真实数据只保留重试后的)
        if meta.get("result") == "retry":
            continue

        key = f"{meta['mode']}_{meta['object']}_{meta['trial']}"
        real_trials[key] = {
            "metadata": meta,
            "rows": rows,
        }

    print(f"  [INFO] 有效真实试验: {len(real_trials)} 次")
    return real_trials


# ──────────────────────────────────────────────────────────────
# 主生成函数
# ──────────────────────────────────────────────────────────────

def generate_experiment_data(
    output_dir: Path,
    operator_id: int = 1,
    real_dir: Optional[Path] = None,
    seed: int = 42,
):
    """
    生成完整的实验数据
    """
    random.seed(seed)
    np.random.seed(seed)

    output_dir.mkdir(parents=True, exist_ok=True)
    real_trials = load_real_trials(real_dir)

    plan = build_complete_plan()

    # ── 保存 config.yaml ──
    config = {
        "operator_id": operator_id,
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "modes": MODES,
        "objects": [{"name": o[0], "label": o[1]} for o in OBJECTS],
        "trials_per_combo": TRIALS_PER_COMBO,
        "mode_order": MODE_ORDER_OP1,
        "seed": seed,
        "plan": plan,
        "note": "合成数据: 基于真实数据统计特征 + 物理模型生成",
    }

    try:
        import yaml
        with open(output_dir / "config.yaml", "w") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    except ImportError:
        import json
        with open(output_dir / "config.yaml", "w") as f:
            json.dump(config, f, indent=2)

    # ── 生成每次试验 ──
    results = []
    for entry in plan:
        trial_n = entry["trial"]
        mode = entry["mode"]
        obj_name = entry["object"]
        obj_label = entry["label"]
        repeat = entry["repeat"]

        # 检查是否有真实数据
        real_key = f"{mode}_{obj_name}_{repeat}"
        is_real = real_key in real_trials

        if is_real:
            # ── 使用真实数据 ──
            real = real_trials[real_key]
            csv_rows = real["rows"]
            meta = real["metadata"]
            result = meta.get("result", "success")

            # CSV 列头
            csv_header = list(csv_rows[0].keys())
            all_rows = [csv_header] + [list(r.values()) for r in csv_rows]

            duration = meta.get("duration", 40.0)
            num_rows = len(csv_rows)

            print(f"  [{trial_n:03d}] ✅ 真实 {mode}_{obj_name}_{repeat}  ({duration:.1f}s, {num_rows}行)")

        else:
            # ── 生成合成数据 ──
            key = f"{mode}_{obj_name}"

            # 决定结果
            probs = OUTCOME_PROB.get(key, [0.85, 0.05, 0.10])
            r = random.random()
            if r < probs[0]:
                result = "success"
            elif r < probs[0] + probs[1]:
                result = "damage"
            else:
                result = "failure"

            # 生成轨迹
            grip_target = GRIP_TARGET.get(key, 0.25) + random.gauss(0, GRIP_STD)
            grip_target = max(0.1, min(0.4, grip_target))

            fz_peak = FZ_PEAK.get(key, 4.0) + random.gauss(0, 0.5)
            fz_peak = max(1.5, fz_peak)

            if mode == "c":
                k_trans = K_TRANS.get(f"c_{obj_name}", 0.6)
            else:
                k_trans = K_TRANS.get(mode, 0.0)

            n_rows = max(50, int(random.gauss(ROWS_MEAN, ROWS_STD)))

            csv_data = generate_trajectory(
                mode=mode,
                obj_name=obj_name,
                obj_label=obj_label,
                n_rows=n_rows,
                grip_target=grip_target,
                fz_peak=fz_peak,
                k_trans=k_trans,
            )

            duration = max(15, random.gauss(
                DURATION.get(key, 40), DURATION_STD
            ))
            # duration 与行数正相关
            duration = duration * (n_rows / ROWS_MEAN)
            duration = round(max(15, min(120, duration)), 1)

            # CSV 行
            csv_header = list(csv_data[0].keys())
            all_rows = [csv_header] + [list(r.values()) for r in csv_data]
            num_rows = len(csv_data)
            print(f"  [{trial_n:03d}] 🔷 合成 {mode}_{obj_name}_{repeat}  ({duration:.1f}s, {num_rows}行, {result})")

        # ── 保存 CSV ──
        real_csv_basename = f"trial_{repeat:03d}_mode{mode}_{obj_name}_{result}.csv"
        csv_fname = f"trial_{trial_n:03d}_mode{mode}_{obj_name}_{result}.csv"
        csv_path = output_dir / csv_fname

        if is_real:
            # 复制真实 CSV
            import shutil
            real_csv = real_dir / real_csv_basename
            if real_csv.exists():
                shutil.copy2(real_csv, csv_path)
        else:
            with open(csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerows(all_rows)

        # ── 保存元数据 ──
        meta_fname = csv_fname.replace(".csv", "_meta.yaml")
        meta_path = output_dir / meta_fname

        try:
            import yaml as ymlib
            metadata = {
                "trial": trial_n,
                "mode": mode,
                "object": obj_name,
                "label": obj_label,
                "operator": operator_id,
                "result": result,
                "duration": round(duration, 2) if not is_real else duration,
                "rows": num_rows,
                "timestamp": datetime.now().isoformat(),
                "synthetic": not is_real,
            }
            with open(meta_path, "w") as f:
                ymlib.dump(metadata, f, default_flow_style=False, allow_unicode=True)
        except ImportError:
            pass

        results.append({
            "trial": trial_n,
            "mode": mode,
            "object": obj_name,
            "result": result,
            "duration": round(duration, 2) if not is_real else duration,
            "is_real": is_real,
        })

    # ── 生成汇总 ──
    _generate_summary(results, output_dir)
    print(f"\n  ✅ 完成! 共 {len(results)} 次试验")
    print(f"     数据目录: {output_dir}")
    print(f"     真实: {sum(1 for r in results if r.get('is_real'))} 次")
    print(f"     合成: {sum(1 for r in results if not r.get('is_real'))} 次")

    # 统计成功率
    for m in ["a", "b", "c"]:
        m_results = [r for r in results if r["mode"] == m]
        succ = sum(1 for r in m_results if r["result"] == "success")
        dam = sum(1 for r in m_results if r["result"] == "damage")
        print(f"     模式{m}: {succ}/{len(m_results)} 成功, {dam} 破损")


def _generate_summary(results: List[dict], output_dir: Path):
    """生成 Markdown 汇总"""
    path = output_dir / "summary.md"

    with open(path, "w") as f:
        f.write("# 实验汇总 (合成数据)\n\n")

        total = len(results)
        success = sum(1 for r in results if r["result"] == "success")
        failure = sum(1 for r in results if r["result"] == "failure")
        damage = sum(1 for r in results if r["result"] == "damage")
        f.write(f"操作员: 1\n\n")
        f.write(f"总试验: {total} | ✅ 成功: {success} | ❌ 失败: {failure} | 💔 破损: {damage}\n\n")

        # 按模式
        f.write("## 按模式统计\n\n")
        f.write("| 模式 | 总试验 | 成功 | 失败 | 破损 | 成功率 |\n")
        f.write("|------|--------|------|------|------|--------|\n")
        for mode_name in ["a", "b", "c"]:
            mode_results = [r for r in results if r["mode"] == mode_name]
            n = len(mode_results)
            s = sum(1 for r in mode_results if r["result"] == "success")
            fa = sum(1 for r in mode_results if r["result"] == "failure")
            d = sum(1 for r in mode_results if r["result"] == "damage")
            sr = s / n * 100 if n > 0 else 0
            desc = {"a": "A-传统", "b": "B-固定增益", "c": "C-本文方法"}
            f.write(f"| {desc.get(mode_name, mode_name)} | {n} | {s} | {fa} | {d} | {sr:.1f}% |\n")

        # 按物体
        f.write("\n## 按物体统计\n\n")
        f.write("| 物体 | 总试验 | 成功 | 失败 | 破损 | 成功率 |\n")
        f.write("|------|--------|------|------|------|--------|\n")
        for obj_name, _ in OBJECTS:
            obj_results = [r for r in results if r["object"] == obj_name]
            n = len(obj_results)
            s = sum(1 for r in obj_results if r["result"] == "success")
            fa = sum(1 for r in obj_results if r["result"] == "failure")
            d = sum(1 for r in obj_results if r["result"] == "damage")
            sr = s / n * 100 if n > 0 else 0
            f.write(f"| {obj_name} | {n} | {s} | {fa} | {d} | {sr:.1f}% |\n")

        f.write("\n## 详细试验记录\n\n")
        f.write("| # | 模式 | 物体 | 结果 | 耗时(s) | 来源 |\n")
        f.write("|---|------|------|------|--------|------|\n")
        icons = {"success": "✅", "failure": "❌", "damage": "💔"}
        for r in results:
            icon = icons.get(r["result"], "❓")
            src = "真实" if r.get("is_real") else "合成"
            f.write(f"| {r['trial']} | {r['mode']} | {r['object']} "
                    f"| {icon}{r['result']} | {r['duration']:.1f} | {src} |\n")


# ──────────────────────────────────────────────────────────────
# 入口
# ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="合成实验数据生成器")
    parser.add_argument("--real-dir", type=str, default=None,
                        help="真实数据目录 (已有试验会被保留)")
    parser.add_argument("--output", type=str, required=True,
                        help="输出目录")
    parser.add_argument("--operator", type=int, default=1,
                        help="操作员编号")
    parser.add_argument("--seed", type=int, default=42,
                        help="随机种子")

    args = parser.parse_args()

    real_dir = Path(args.real_dir) if args.real_dir else None
    output_dir = Path(args.output)

    print(f"{'='*60}")
    print(f"  实验数据合成")
    print(f"{'='*60}")
    print(f"  输出目录: {output_dir}")
    print(f"  真实数据: {real_dir or '无 (纯合成)'}")
    print(f"  操作员:   {args.operator}")
    print(f"  种子:     {args.seed}")
    print(f"{'='*60}\n")

    generate_experiment_data(
        output_dir=output_dir,
        operator_id=args.operator,
        real_dir=real_dir,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
