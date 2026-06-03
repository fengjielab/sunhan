#!/usr/bin/env python3
from __future__ import annotations
"""实验运行器 — 自动化执行三模式 × 5物体对比实验

使用方法:
  python3 experiment_runner.py                    # 运行全部实验（需要3次硬件启动）
  python3 experiment_runner.py --mode a --obj book  # 单次指定实验
  python3 experiment_runner.py --dry-run            # 仅打印实验计划

输出:
  data/experiment_YYYYMMDD_HHMMSS/
    ├── config.yaml              # 实验配置
    ├── summary.md               # 人工阅读总结
    ├── mode_a_book.csv          # 每周期数据
    ├── mode_a_book_metadata.yaml
    ├── mode_b_banana.csv
    ├── ...
    └── plots/                   # 可视化
        ├── force_comparison.png
        ├── grip_comparison.png
        └── trajectory.png
"""

import argparse
import csv
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


# ═══════════════════════════════════════════════════════════════
# 实验配置
# ═══════════════════════════════════════════════════════════════

# 三种模式
MODES = ["a", "b", "c"]

# 5种物体（按 YOLO 检测顺序放置；N/A 为无物体基线）
OBJECTS = [
    ("无物体",    "N/A"),       # baseline（无物体放置）
    ("瓶子",      "bottle"),    # 中等硬度
    ("香蕉",      "banana"),    # 软质
    ("书",        "book"),      # 硬质
    ("杯子",      "cup"),       # 软质
    ("钟",        "clock"),     # 未知硬度
]

# 每轮采集周期数
CYCLES_PER_RUN = 500

# 物体更换间隔（秒）
OBJECT_CHANGE_DELAY = 5.0

# 实验数据目录
DATA_DIR = Path("data")

# 共享控制节点脚本路径
SHARED_CONTROL_SCRIPT = str(Path(__file__).resolve().parent / "shared_control_node.py")


# ═══════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════

def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


# ═══════════════════════════════════════════════════════════════
# 实验配置生成
# ═══════════════════════════════════════════════════════════════

def build_experiment_plan(cycles_per_run: int = CYCLES_PER_RUN) -> List[dict]:
    """生成完整实验计划"""
    plan = []
    for mode in MODES:
        for obj_display, obj_yolo in OBJECTS:
            plan.append({
                "mode": mode,
                "obj_display": obj_display,
                "obj_yolo": obj_yolo,
                "cycles": cycles_per_run,
            })
    return plan


def print_plan(plan: List[dict]):
    """打印实验计划"""
    print("=" * 60)
    print("实验计划")
    print("=" * 60)
    print(f"模式: {', '.join(MODES)}")
    print(f"物体: {', '.join(o[0] for o in OBJECTS)}")
    print(f"每轮周期: {CYCLES_PER_RUN}")
    print(f"总实验数: {len(plan)}")
    print("-" * 60)
    for i, exp in enumerate(plan, 1):
        print(f"  [{i:2d}] 模式{exp['mode']} — {exp['obj_display']:4s} (YOLO: {exp['obj_yolo']})"
              f"  {exp['cycles']} cycles")
    print("=" * 60)


# ═══════════════════════════════════════════════════════════════
# 数据采集器（解析 shared_control_node 输出）
# ═══════════════════════════════════════════════════════════════

class DataCollector:
    """从 shared_control_node 的 stdout 中提取结构化数据"""

    def __init__(self, output_dir: Path, mode: str, obj_name: str):
        self.output_dir = output_dir
        self.mode = mode
        self.obj_name = obj_name
        self.rows: List[dict] = []
        self.start_time = time.time()

        # CSV 文件
        csv_name = f"mode_{mode}_{obj_name}.csv"
        self.csv_path = output_dir / csv_name
        self.csv_file = open(self.csv_path, "w", newline="")
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow([
            "timestamp", "cycle", "object", "label",
            "F_ext_x", "F_ext_y", "F_ext_z",
            "F_fb_x", "F_fb_y", "F_fb_z",
            "grip",
        ])

    def feed_line(self, line: str):
        """解析 shared_control_node 的一行输出"""
        try:
            # 示例: [  123] 物体=book         label=hard     F_ext=(-1.23,+0.45,+2.34) F_fb=(-0.50,+0.10,+1.00) grip=0.15
            if "F_ext=" not in line or "F_fb=" not in line:
                return

            # 解析 cycle
            parts = line.strip().split("]")
            if len(parts) < 2:
                return
            cycle_str = parts[0].strip("[ ")
            cycle = int(cycle_str)

            # 解析物体
            obj_part = parts[1] if len(parts) > 1 else ""
            obj = "N/A"
            if "物体=" in obj_part:
                obj = obj_part.split("物体=")[1].split()[0].strip()

            # 解析 label
            label = "unknown"
            if "label=" in obj_part:
                label = obj_part.split("label=")[1].split()[0].strip()

            # 解析 F_ext
            fext = self._parse_vector(line, "F_ext=")
            # 解析 F_fb
            ffb = self._parse_vector(line, "F_fb=")

            # 解析 grip
            grip = 0.0
            if "grip=" in line:
                grip_str = line.split("grip=")[-1].split()[0].strip()
                if grip_str != "N/A":
                    grip = float(grip_str)

            row = {
                "timestamp": time.time() - self.start_time,
                "cycle": cycle,
                "object": obj,
                "label": label,
                "F_ext_x": fext[0], "F_ext_y": fext[1], "F_ext_z": fext[2],
                "F_fb_x": ffb[0], "F_fb_y": ffb[1], "F_fb_z": ffb[2],
                "grip": grip,
            }
            self.rows.append(row)

            self.csv_writer.writerow([
                f"{row['timestamp']:.3f}", row["cycle"], row["object"], row["label"],
                *[f"{v:.4f}" for v in [row["F_ext_x"], row["F_ext_y"], row["F_ext_z"],
                                        row["F_fb_x"], row["F_fb_y"], row["F_fb_z"]]],
                f"{row['grip']:.4f}",
            ])

        except Exception as e:
            # 日志记录但继续
            pass

    def _parse_vector(self, line: str, prefix: str) -> tuple:
        """解析 (x, y, z) 格式向量"""
        try:
            if prefix not in line:
                return (0.0, 0.0, 0.0)
            after = line.split(prefix)[1].strip()
            if after[0] != "(":
                return (0.0, 0.0, 0.0)
            end = after.find(")")
            vec_str = after[1:end]
            parts = [float(p.strip()) for p in vec_str.split(",")]
            if len(parts) == 3:
                return tuple(parts)
            return (0.0, 0.0, 0.0)
        except:
            return (0.0, 0.0, 0.0)

    def close(self):
        self.csv_file.close()

    def summary(self) -> dict:
        """计算本轮统计数据"""
        if not self.rows:
            return {"cycles": 0, "error": "no data"}

        fext_x = [r["F_ext_x"] for r in self.rows]
        fext_y = [r["F_ext_y"] for r in self.rows]
        fext_z = [r["F_ext_z"] for r in self.rows]
        ffb_x = [r["F_fb_x"] for r in self.rows]
        ffb_y = [r["F_fb_y"] for r in self.rows]
        ffb_z = [r["F_fb_z"] for r in self.rows]
        grips = [r["grip"] for r in self.rows]

        def stats(vals):
            return {
                "mean": sum(vals) / len(vals),
                "std": (sum((v - sum(vals)/len(vals))**2 for v in vals) / len(vals))**0.5,
                "min": min(vals),
                "max": max(vals),
            }

        return {
            "mode": self.mode,
            "object": self.obj_name,
            "cycles": len(self.rows),
            "F_ext_x": stats(fext_x),
            "F_ext_y": stats(fext_y),
            "F_ext_z": stats(fext_z),
            "F_fb_x": stats(ffb_x),
            "F_fb_y": stats(ffb_y),
            "F_fb_z": stats(ffb_z),
            "grip": stats(grips),
        }


# ═══════════════════════════════════════════════════════════════
# 单次实验执行
# ═══════════════════════════════════════════════════════════════

def run_single_experiment(exp: dict, data_dir: Path) -> dict:
    """启动 shared_control_node 子进程，实时采集 stdout 数据

    工作流程:
      1. 启动 shared_control_node --mode X 作为子进程
      2. 逐行读取 stdout，喂给 DataCollector 解析
      3. 达到目标周期数后自动停止（或 Ctrl+C 中断）
      4. 保存 CSV 和元数据
    """
    mode = exp["mode"]
    obj_yolo = exp["obj_yolo"]
    obj_display = exp["obj_display"]
    cycles = exp["cycles"]

    print(f"\n{'=' * 60}")
    print(f"实验: 模式{modes_desc(mode)} | 物体: {obj_display} (YOLO: {obj_yolo})")
    print(f"周期: {cycles}")
    print(f"{'=' * 60}")

    # 准备输出目录
    ensure_dir(data_dir / f"mode_{mode}_{obj_yolo}")

    # 创建数据收集器
    collector = DataCollector(data_dir, mode, obj_yolo)

    # 元数据
    metadata = {
        "mode": mode,
        "object_display": obj_display,
        "object_yolo": obj_yolo,
        "requested_cycles": cycles,
        "timestamp": timestamp(),
        "status": "running",
    }

    # 启动 shared_control_node 子进程（自动继承当前环境）
    cmd = [
        sys.executable, SHARED_CONTROL_SCRIPT,
        "--mode", mode,
    ]
    print(f"\n启动: {' '.join(cmd)}")
    print(f"将物体「{obj_display}」放在相机前")
    print(f"操作 Omega.7 进行遥操作，{cycles} 周期后自动停止")
    print(f"或按 Ctrl+C 提前中断\n")

    # 启动子进程并实时读取 stdout
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,          # 行缓冲
    )

    try:
        for line in iter(proc.stdout.readline, ""):
            print(line, end="")                    # 回显到终端
            collector.feed_line(line)              # 解析并写入 CSV

            # 达到目标周期数 → 自动停止
            if len(collector.rows) >= cycles:
                print(f"\n✅ 已采集 {cycles} 周期，停止...")
                break
    except KeyboardInterrupt:
        print(f"\n⏹ 用户中断")
    finally:
        # 清理子进程
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        collector.close()

    # 计算统计
    stats = collector.summary()

    # 保存元数据
    import yaml
    meta_path = data_dir / f"mode_{mode}_{obj_yolo}_metadata.yaml"
    with open(meta_path, "w") as f:
        yaml.dump({**metadata, "status": "completed", "stats": stats}, f)

    print(f"\n✅ 完成: {meta_path}")
    print(f"   数据文件: {collector.csv_path}")

    return stats


def modes_desc(mode: str) -> str:
    desc = {"a": "A-零力(传统遥操作)", "b": "B-固定增益", "c": "C-自适应"}
    return desc.get(mode, mode)


# ═══════════════════════════════════════════════════════════════
# 完整实验运行
# ═══════════════════════════════════════════════════════════════

def run_all_experiments():
    """按顺序运行所有实验"""

    plan = build_experiment_plan()
    print_plan(plan)

    # 创建实验目录
    exp_ts = timestamp()
    data_dir = ensure_dir(DATA_DIR / f"experiment_{exp_ts}")

    # 保存实验计划
    import yaml
    plan_path = data_dir / "config.yaml"
    with open(plan_path, "w") as f:
        yaml.dump({
            "timestamp": exp_ts,
            "modes": MODES,
            "objects": [{"display": d, "yolo": y} for d, y in OBJECTS],
            "cycles_per_run": CYCLES_PER_RUN,
            "plan": [{
                "mode": e["mode"],
                "object_display": e["obj_display"],
                "object_yolo": e["obj_yolo"],
                "cycles": e["cycles"],
            } for e in plan],
        }, f)

    all_results = []

    for i, exp in enumerate(plan, 1):
        print(f"\n{'#' * 60}")
        print(f"# 实验 [{i}/{len(plan)}]")
        print(f"{'#' * 60}")

        input(f"按 Enter 开始实验 [{i}/{len(plan)}]（或 Ctrl+C 停止）...")

        result = run_single_experiment(exp, data_dir)
        all_results.append(result)

        if i < len(plan):
            print(f"\n等待 {OBJECT_CHANGE_DELAY}s 更换物体...")
            time.sleep(OBJECT_CHANGE_DELAY)

    # 生成总结
    summary_path = generate_summary(all_results, data_dir)

    print(f"\n{'=' * 60}")
    print(f"所有实验完成！")
    print(f"数据目录: {data_dir}")
    print(f"总结: {summary_path}")
    print(f"{'=' * 60}")


# ═══════════════════════════════════════════════════════════════
# 总结生成
# ═══════════════════════════════════════════════════════════════

def generate_summary(results: List[dict], output_dir: Path) -> Path:
    """生成 Markdown 总结"""
    path = output_dir / "summary.md"

    with open(path, "w") as f:
        f.write("# 实验总结\n\n")
        f.write(f"生成时间: {timestamp()}\n\n")
        f.write("## 对比表\n\n")
        f.write("| 模式 | 物体 | 周期 | F_fb_x均值 | F_fb_y均值 | F_fb_z均值 | grip均值 |\n")
        f.write("|------|------|------|-----------|-----------|-----------|---------|\n")

        for r in results:
            mode = modes_desc(r.get("mode", "?"))
            obj = r.get("object", "?")
            cycles = r.get("cycles", 0)
            ffx = f"{r.get('F_fb_x', {}).get('mean', 0):.3f}"
            ffy = f"{r.get('F_fb_y', {}).get('mean', 0):.3f}"
            ffz = f"{r.get('F_fb_z', {}).get('mean', 0):.3f}"
            grip = f"{r.get('grip', {}).get('mean', 0):.3f}"
            f.write(f"| {mode} | {obj} | {cycles} | {ffx} | {ffy} | {ffz} | {grip} |\n")

        f.write("\n## 关键对比指标\n\n")

        # 计算三种模式的 F_fb 总体均值和 grip 均值
        for m in ["a", "b", "c"]:
            mode_results = [r for r in results if r.get("mode") == m]
            if not mode_results:
                continue

            total_fb_x = sum(
                abs(r.get("F_fb_x", {}).get("mean", 0)) for r in mode_results
            )
            total_fb_y = sum(
                abs(r.get("F_fb_y", {}).get("mean", 0)) for r in mode_results
            )
            total_fb_z = sum(
                abs(r.get("F_fb_z", {}).get("mean", 0)) for r in mode_results
            )
            avg_grip = sum(
                abs(r.get("grip", {}).get("mean", 0)) for r in mode_results
            ) / len(mode_results)

            f.write(f"- **模式{modes_desc(m).split('-')[0]}**: "
                    f"Σ|F_fb| = ({total_fb_x:.3f}, {total_fb_y:.3f}, {total_fb_z:.3f}) N, "
                    f"avg grip = {avg_grip:.3f}\n")

    return path


# ═══════════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="三模式 × 5物体 共享控制实验运行器")
    parser.add_argument("--mode", choices=MODES, help="仅运行指定模式")
    parser.add_argument("--obj", help="仅运行指定物体 (YOLO class name)")
    parser.add_argument("--dry-run", action="store_true", help="仅打印实验计划，不执行")
    parser.add_argument("--cycles", type=int, default=CYCLES_PER_RUN, help="每轮周期数")

    args = parser.parse_args()

    cycles = args.cycles if args.cycles else CYCLES_PER_RUN

    if args.dry_run:
        plan = build_experiment_plan(cycles_per_run=cycles)
        print_plan(plan)
        return

    if args.mode or args.obj:
        # 单次指定实验
        plan = build_experiment_plan(cycles_per_run=cycles)
        filtered = [e for e in plan
                    if (not args.mode or e["mode"] == args.mode)
                    and (not args.obj or e["obj_yolo"] == args.obj)]
        if not filtered:
            print(f"未找到匹配的实验: mode={args.mode}, obj={args.obj}")
            sys.exit(1)

        exp_ts = timestamp()
        data_dir = ensure_dir(DATA_DIR / f"experiment_{exp_ts}")
        result = run_single_experiment(filtered[0], data_dir)
    else:
        run_all_experiments()


if __name__ == "__main__":
    main()
