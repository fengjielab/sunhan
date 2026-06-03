#!/usr/bin/env python3
"""
experiment_trial_runner.py — 基于单次抓取试验的实验运行器
============================================================

设计目标:
    1. 每次试验 = 1 次完整的"接近→抓取→提升→移动→释放"过程
    2. 人工记录每次试验的结果（成功/失败/破损）
    3. 支持多操作员、拉丁方随机化、NASA-TLX 问卷提示
    4. 数据文件规范: trial_{n:03d}_{mode}_{obj}_{result}.csv

依赖:
    - shared_control_node.py (通过 subprocess 启动)
    - vision_physics_mapper.py (物体列表)

用法:
    python3 experiment_trial_runner.py --operator 1 --mode a --obj banana --trial 1
    python3 experiment_trial_runner.py --full --operator 1          # 完整实验
    python3 experiment_trial_runner.py --full --operator 1 --dry-run  # 打印计划

作者: mfj
日期: 2026-05
"""

import argparse
import csv
import os
import random
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# ═══════════════════════════════════════════════════════════════
# 实验配置
# ═══════════════════════════════════════════════════════════════

# 模式
MODES = ["a", "b", "c"]

# 物体列表（与 vision_physics_mapper.py 保持一致）
OBJECTS_CONFIG = [
    # ("apple",      "soft"),    # 暂缺
    ("banana",     "soft"),
    ("bottle",     "medium"),
    ("book",       "hard"),
    # ("cell phone", "hard"),    # 暂缺
]

# 每种 (模式, 物体) 组合的重复试验次数
TRIALS_PER_COMBO = 5

# 试验超时时间 (秒)
TRIAL_TIMEOUT = 60

# 物体更换/休息间隔 (秒)
OBJECT_CHANGE_DELAY = 3.0
MODE_CHANGE_DELAY = 5.0

# 数据根目录
DATA_DIR = Path("data")

# shared_control_node 脚本路径
SHARED_CONTROL_SCRIPT = str(
    Path(__file__).resolve().parent / "shared_control_node.py"
)


# ═══════════════════════════════════════════════════════════════
# 实验计划生成
# ═══════════════════════════════════════════════════════════════

def latin_square_order(operator_id: int) -> List[str]:
    """用拉丁方确定三种模式的执行顺序"""
    orders = [
        ["a", "b", "c"],  # 操作员1: A→B→C
        ["b", "c", "a"],  # 操作员2: B→C→A
        ["c", "a", "b"],  # 操作员3: C→A→B
    ]
    idx = (operator_id - 1) % len(orders)
    return orders[idx]


def build_trial_plan(
    operator_id: int,
    trials: int = TRIALS_PER_COMBO,
    seed: Optional[int] = None,
) -> List[dict]:
    """
    生成完整的试验计划，包含拉丁方顺序和随机化

    Returns:
        list[dict]: 每个 dict 包含 mode, obj, label, trial_n
    """
    mode_order = latin_square_order(operator_id)

    plan = []
    for mode in mode_order:
        # 每种模式下，所有物体的 trials 次试验
        for obj_name, label in OBJECTS_CONFIG:
            for t in range(1, trials + 1):
                plan.append({
                    "mode": mode,
                    "obj": obj_name,
                    "label": label,
                    "trial_n": t,
                })

    # 在每个模式内随机化物体顺序（保持模式顺序）
    rng = random.Random(seed)
    mode_groups = {}
    for entry in plan:
        mode_groups.setdefault(entry["mode"], []).append(entry)

    randomized = []
    for mode in mode_order:
        group = mode_groups[mode]
        rng.shuffle(group)
        randomized.extend(group)

    return randomized


def print_plan(plan: List[dict]):
    """打印试验计划"""
    print("=" * 70)
    print("                                  试验计划")
    print("=" * 70)

    current_mode = None
    for i, trial in enumerate(plan, 1):
        if trial["mode"] != current_mode:
            current_mode = trial["mode"]
            mode_desc = {"a": "A-传统", "b": "B-固定增益", "c": "C-本文方法"}
            print(f"\n  ── 模式 {mode_desc[current_mode]} ──")

        label = trial["label"]
        print(f"  [{i:3d}] 模式{trial['mode']} | {trial['obj']:<12} {label:<8} "
              f"| 重复 {trial['trial_n']}/{TRIALS_PER_COMBO}")

    print("\n" + "=" * 70)
    print(f"  总试验数: {len(plan)}")
    print(f"  每操作员预计耗时: ~30-40 分钟（含休息）")
    print("=" * 70)


# ═══════════════════════════════════════════════════════════════
# 试验执行
# ═══════════════════════════════════════════════════════════════

def run_single_trial(
    trial_info: dict,
    data_dir: Path,
    operator_id: int,
) -> dict:
    """
    执行单次抓取试验

    工作流程:
        1. 操作员准备物体
        2. 启动 shared_control_node --mode X
        3. 操作员完成任务
        4. 人工输入结果（成功/失败/破损）
        5. 保存 CSV + 元数据

    Args:
        trial_info: {mode, obj, label, trial_n}
        data_dir: 实验数据目录
        operator_id: 操作员编号

    Returns:
        包含试验结果的字典
    """
    mode = trial_info["mode"]
    obj = trial_info["obj"]
    label = trial_info["label"]
    trial_n = trial_info["trial_n"]

    print(f"\n{'─' * 60}")
    print(f"  试验 [{trial_info['_index']}/{trial_info['_total']}]")
    print(f"  模式: {mode} | 物体: {obj} ({label}) | 重复: {trial_n}/{TRIALS_PER_COMBO}")
    print(f"{'─' * 60}")

    # ── 1. 准备物体 ──
    input(f"\n  🔸 请将「{obj}」放置在桌面标记位置，然后按 Enter 开始...")

    # ── 2. 启动 shared_control_node 子进程 ──
    print(f"\n  启动 shared_control_node --mode {mode} --visualize ...")
    cmd = [sys.executable, SHARED_CONTROL_SCRIPT, "--mode", mode, "--visualize"]

    # 使用进程组：确保 terminate → SIGTERM 传播到 YOLO 孙进程
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        preexec_fn=os.setpgrp,
    )

    # ── 3. 实时显示 stdout，同时保存 ──
    csv_rows = []
    start_time = time.time()

    # CSV 列头（与 shared_control_node._print_status 输出格式匹配）
    csv_header = [
        "timestamp", "cycle", "object", "label",
        "F_ext_x", "F_ext_y", "F_ext_z",
        "F_fb_x", "F_fb_y", "F_fb_z",
        "grip",
    ]
    csv_rows.append(csv_header)

    print(f"\n  ⏱  请在 {TRIAL_TIMEOUT}s 内完成任务")
    print(f"  操作: 移动手柄 → 接近物体 → 夹持 → 提升 → 移至托盘 → 释放\n")

    try:
        for line in iter(proc.stdout.readline, ""):
            # 实时显示
            print(f"    {line}", end="")

            # 解析数据行
            parsed = _parse_status_line(line)
            if parsed:
                csv_rows.append(parsed)

            # 检查超时
            if time.time() - start_time > TRIAL_TIMEOUT:
                print(f"\n  ⚠️  超时 ({TRIAL_TIMEOUT}s)，强制停止")
                break

    except KeyboardInterrupt:
        print(f"\n  ⏹  用户中断")
    finally:
        # 向整个进程组发 SIGTERM（确保 YOLO 孙进程也被终止）
        try:
            pgid = os.getpgid(proc.pid)
            os.killpg(pgid, signal.SIGTERM)
        except Exception:
            proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(pgid, signal.SIGKILL)
            except Exception:
                proc.kill()

    # ── 4. 人工判定结果 ──
    print(f"\n{'─' * 40}")
    print(f"  判定抓取结果:")
    print(f"    [s]  ✅ 成功 — 物体被夹持、提起、移至托盘、释放，全程无问题")
    print(f"    [f]  ❌ 失败 — 抓取掉落/夹持不稳/操作超时")
    print(f"    [d]  💔 破损 — 物体（软物体）被夹破/压坏/掉落摔坏")
    print(f"    [r]  🔄 重试 — 意外情况，本次作废重试")
    print(f"{'─' * 40}")

    result = input("  结果 (s/f/d/r): ").strip().lower()
    while result not in ("s", "f", "d", "r"):
        result = input("  请输入 s/f/d/r: ").strip().lower()

    result_map = {"s": "success", "f": "failure", "d": "damage", "r": "retry"}

    # ── 5. 保存数据 ──
    trial_result = {
        "operator": operator_id,
        "mode": mode,
        "object": obj,
        "label": label,
        "trial": trial_n,
        "result": result_map[result],
        "duration": round(time.time() - start_time, 2),
        "rows": len(csv_rows) - 1,  # 减去 header
        "timestamp": datetime.now().isoformat(),
    }

    # CSV 文件名
    csv_fname = f"trial_{trial_n:03d}_mode{mode}_{obj}_{result_map[result]}.csv"
    csv_path = data_dir / csv_fname
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(csv_rows)

    # 元数据
    meta_path = data_dir / csv_fname.replace(".csv", "_meta.yaml")
    with open(meta_path, "w") as f:
        import yaml
        yaml.dump(trial_result, f, default_flow_style=False, allow_unicode=True)

    print(f"\n  ✅ 数据已保存:")
    print(f"    CSV: {csv_path}")
    print(f"    元数据: {meta_path}")

    return trial_result


def _parse_status_line(line: str) -> Optional[list]:
    """
    解析 shared_control_node 的状态打印行

    示例输入:
        [   123] 物体=book         label=hard     F_ext=(-1.23,+0.45,+2.34) F_fb=(-0.50,+0.10,+1.00) grip=0.15

    Returns:
        list: [timestamp, cycle, object, label, Fx, Fy, Fz, FFx, FFy, FFz, grip]
        或 None（不是数据行）
    """
    try:
        if "F_ext=" not in line or "F_fb=" not in line:
            return None

        parts = line.strip().split("]")
        if len(parts) < 2:
            return None

        cycle_str = parts[0].strip("[ ")
        cycle = int(cycle_str)

        obj_part = parts[1] if len(parts) > 1 else ""

        # 解析 object
        obj = "N/A"
        if "物体=" in obj_part:
            obj = obj_part.split("物体=")[1].split()[0].strip()

        # 解析 label
        label = "unknown"
        if "label=" in obj_part:
            label = obj_part.split("label=")[1].split()[0].strip()

        # 解析 F_ext
        fext = _parse_vector(line, "F_ext=")

        # 解析 F_fb
        ffb = _parse_vector(line, "F_fb=")

        # 解析 grip
        grip = 0.0
        if "grip=" in line:
            grip_str = line.split("grip=")[-1].split()[0].strip()
            if grip_str != "N/A":
                grip = float(grip_str)

        return [
            time.time(), cycle, obj, label,
            fext[0], fext[1], fext[2],
            ffb[0], ffb[1], ffb[2],
            grip,
        ]

    except Exception:
        return None


def _parse_vector(line: str, prefix: str) -> tuple:
    """解析 (x, y, z) 格式向量"""
    try:
        if prefix not in line:
            return (0.0, 0.0, 0.0)
        after = line.split(prefix)[1].strip()
        if not after or after[0] != "(":
            return (0.0, 0.0, 0.0)
        end = after.find(")")
        if end < 0:
            return (0.0, 0.0, 0.0)
        vec_str = after[1:end]
        parts = [float(p.strip()) for p in vec_str.split(",")]
        if len(parts) == 3:
            return tuple(parts)
        return (0.0, 0.0, 0.0)
    except Exception:
        return (0.0, 0.0, 0.0)


# ═══════════════════════════════════════════════════════════════
# 完整实验流程
# ═══════════════════════════════════════════════════════════════

def run_full_experiment(operator_id: int, dry_run: bool = False):
    """执行完整实验，包含 NASA-TLX 问卷提示"""

    # ── 1. 生成实验计划 ──
    plan = build_trial_plan(operator_id)
    total = len(plan)

    # 给每个 trial 加上索引信息
    for i, trial in enumerate(plan, 1):
        trial["_index"] = i
        trial["_total"] = total

    print_plan(plan)

    if dry_run:
        return

    # ── 2. 创建实验目录 ──
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    data_dir = DATA_DIR / f"experiment_{timestamp}" / f"operator_{operator_id}"
    data_dir.mkdir(parents=True, exist_ok=True)

    # 保存配置
    config = {
        "operator_id": operator_id,
        "timestamp": timestamp,
        "modes": MODES,
        "objects": [{"name": o[0], "label": o[1]} for o in OBJECTS_CONFIG],
        "trials_per_combo": TRIALS_PER_COMBO,
        "mode_order": latin_square_order(operator_id),
        "plan": [
            {"trial": t["_index"], "mode": t["mode"],
             "object": t["obj"], "label": t["label"],
             "repeat": t["trial_n"]}
            for t in plan
        ],
    }
    import yaml
    with open(data_dir / "config.yaml", "w") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

    # ── 3. 逐条执行试验 ──
    results = []
    current_mode = None

    for trial in plan:
        mode = trial["mode"]

        # 模式切换时提示休息
        if mode != current_mode:
            current_mode = mode
            if len(results) > 0:
                print(f"\n{'=' * 60}")
                print(f"  🛑 模式切换完成！请填写 NASA-TLX 问卷")
                print(f"  请打开: plans/nasa_tlx_template.md")
                print(f"  或者使用纸质版问卷")
                print(f"{'=' * 60}")
                input(f"\n  按 Enter 继续下一模式 (模式 {mode}) ...")

            print(f"\n{'=' * 60}")
            print(f"  开始模式 {mode}")
            print(f"{'=' * 60}")
            time.sleep(MODE_CHANGE_DELAY)

        # 执行单次试验
        result = run_single_trial(trial, data_dir, operator_id)

        # 如果是重试，重新加入队列（插到下一个位置）
        if result["result"] == "retry":
            print(f"\n  🔄 重试本次试验，将重新排入队列...")
            # 简单处理：不加入 results，马上重试
            retry_trial = trial.copy()
            retry_trial["_index"] = trial["_index"]  # 保持原编号
            result = run_single_trial(retry_trial, data_dir, operator_id)

        results.append(result)

        # 物体切换间隔
        if trial["_index"] < total:
            next_trial = plan[trial["_index"]]  # 下一个（0-index 注意）
            if next_trial["obj"] != trial["obj"]:
                print(f"\n  换物体: {trial['obj']} → {next_trial['obj']}")
                time.sleep(OBJECT_CHANGE_DELAY)

    # ── 4. 最后一张 NASA-TLX ──
    print(f"\n{'=' * 60}")
    print(f"  ✅ 所有模式完成！请填写最后一份 NASA-TLX 问卷")
    print(f"  请打开: plans/nasa_tlx_template.md")
    print(f"{'=' * 60}")
    input("\n  按 Enter 继续...")

    # ── 5. 生成汇总 ──
    summary_path = _generate_summary(results, data_dir)
    print(f"\n{'=' * 60}")
    print(f"  🎉 实验完成！")
    print(f"  数据目录: {data_dir}")
    print(f"  汇总报告: {summary_path}")
    print(f"{'=' * 60}")


def _generate_summary(results: List[dict], output_dir: Path) -> Path:
    """生成 Markdown 格式的试验结果汇总"""
    path = output_dir / "summary.md"

    # 统计
    from collections import Counter

    total = len(results)
    success = sum(1 for r in results if r["result"] == "success")
    failure = sum(1 for r in results if r["result"] == "failure")
    damage = sum(1 for r in results if r["result"] == "damage")

    with open(path, "w") as f:
        f.write("# 实验汇总\n\n")
        f.write(f"操作员: {results[0]['operator'] if results else '?'}\n\n")
        f.write(f"总试验: {total} | ✅ 成功: {success} | ❌ 失败: {failure} | 💔 破损: {damage}\n\n")

        # 按模式统计
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

        # 按物体统计
        f.write("\n## 按物体统计\n\n")
        f.write("| 物体 | 总试验 | 成功 | 失败 | 破损 | 成功率 |\n")
        f.write("|------|--------|------|------|------|--------|\n")
        for obj_name, _ in OBJECTS_CONFIG:
            obj_results = [r for r in results if r["object"] == obj_name]
            n = len(obj_results)
            s = sum(1 for r in obj_results if r["result"] == "success")
            fa = sum(1 for r in obj_results if r["result"] == "failure")
            d = sum(1 for r in obj_results if r["result"] == "damage")
            sr = s / n * 100 if n > 0 else 0
            f.write(f"| {obj_name} | {n} | {s} | {fa} | {d} | {sr:.1f}% |\n")

        # 详细表格
        f.write("\n## 详细试验记录\n\n")
        f.write("| # | 模式 | 物体 | 重复 | 结果 | 耗时(s) |\n")
        f.write("|---|------|------|------|------|--------|\n")
        for i, r in enumerate(results, 1):
            icon = {"success": "✅", "failure": "❌", "damage": "💔", "retry": "🔄"}
            f.write(f"| {i} | {r['mode']} | {r['object']} | {r['trial']} "
                    f"| {icon.get(r['result'], '❓')}{r['result']} | {r['duration']:.1f} |\n")

    return path


# ═══════════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="三模式 × 5物体 对比实验运行器（单次抓取试验）")
    parser.add_argument("--operator", type=int, required=True, help="操作员编号 (1, 2, 3)")
    parser.add_argument("--full", action="store_true", help="执行完整实验（含拉丁方随机化 + NASA-TLX）")
    parser.add_argument("--dry-run", action="store_true", help="仅打印计划，不执行")
    parser.add_argument("--mode", type=str, choices=MODES, help="单次试验模式")
    parser.add_argument("--obj", type=str, help="单次试验物体")
    parser.add_argument("--trial", type=int, default=1, help="单次试验重复编号")

    args = parser.parse_args()

    if args.full or args.dry_run:
        run_full_experiment(args.operator, dry_run=args.dry_run)
    elif args.mode and args.obj:
        # 单次试验
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        data_dir = DATA_DIR / f"test_{timestamp}" / f"operator_{args.operator}"
        data_dir.mkdir(parents=True, exist_ok=True)

        # 查找 label
        label = "unknown"
        for name, lbl in OBJECTS_CONFIG:
            if name == args.obj:
                label = lbl
                break

        trial_info = {
            "mode": args.mode,
            "obj": args.obj,
            "label": label,
            "trial_n": args.trial,
            "_index": 0,
            "_total": 1,
        }
        run_single_trial(trial_info, data_dir, args.operator)
    else:
        parser.print_help()
        print("\n请指定 --full 执行完整实验，或 --mode + --obj 执行单次试验")


if __name__ == "__main__":
    main()
