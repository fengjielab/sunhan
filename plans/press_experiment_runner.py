#!/usr/bin/env python3
"""
press_experiment_runner.py — 按压实验专用运行器
=================================================

实验设计:
    3 模式 (A/B/C) × 3 材质 (soft/medium/hard) × 10 次重复 = 90 次按压/人
    操作者戴眼罩（盲测），通过 Omega.7 控制 Panda 末端垂直按压物体

使用方法:
    python3 press_experiment_runner.py --operator 1
    python3 press_experiment_runner.py --operator 2 --dry-run
    python3 press_experiment_runner.py --operator 3 --mode b --material hard

数据输出:
    data/press_YYYYMMDD_HHMMSS/operator_{id}/
    ├── trial_001_modea_soft.csv
    ├── trial_001_modea_soft_meta.yaml
    ├── trial_002_modea_soft.csv
    ├── ...
    └── summary.md

作者: mfj
日期: 2026-06
"""

import argparse
import csv
import os
import random
import re
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════
# 实验配置
# ═══════════════════════════════════════════════════════════════

MODES = ["a", "b", "c"]

# 按压实验使用的三种材质
# 使用 vision_physics_mapper.py 中已有的 class 名称，确保 YOLO 可识别
# 若使用 --material-preset 手动指定材质级别，则跳过 YOLO 检测
MATERIALS = [
    # (显示名, YOLO class / preset名, label, 物理描述)
    ("海绵", "teddy bear", "soft", "软质: K=30 N/m, K_trans=0.6"),
    ("硅胶", "bottle", "medium", "中质: K=150 N/m, K_trans=0.6"),
    ("木板", "book", "hard", "硬质: K=300 N/m, K_trans=0.85"),
]

# 材质预设（用于跳过 YOLO 检测，手动指定软硬程度）
MATERIAL_PRESETS = {
    "soft":   {"admittance_K": 30,  "K_trans": 0.6,  "deadband": 0.5, "label": "soft"},
    "medium": {"admittance_K": 150, "K_trans": 0.6,  "deadband": 0.4, "label": "medium"},
    "hard":   {"admittance_K": 300, "K_trans": 0.85, "deadband": 0.5, "label": "hard"},
}

TRIALS_PER_COMBO = 10          # 每种 (模式, 材质) 的按压次数
TRIAL_TIMEOUT = 30             # 单次按压超时 (秒)
PRESS_SAMPLES = 100            # 每次按压要采集的最少周期数
MATERIAL_CHANGE_DELAY = 5.0    # 换材质等待时间 (秒)
MODE_CHANGE_DELAY = 5.0        # 换模式等待时间 (秒)

DATA_DIR = Path("data")
SHARED_CONTROL_SCRIPT = str(
    Path(__file__).resolve().parent / "shared_control_node.py"
)


# ═══════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════

def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def latin_square_order(operator_id: int) -> List[str]:
    """用拉丁方确定三种模式的执行顺序"""
    orders = [
        ["a", "b", "c"],  # 操作员1: A→B→C
        ["b", "c", "a"],  # 操作员2: B→C→A
        ["c", "a", "b"],  # 操作员3: C→A→B
    ]
    idx = (operator_id - 1) % len(orders)
    return orders[idx]


def mode_name(mode: str) -> str:
    return {"a": "A-传统遥操作", "b": "B-固定增益", "c": "C-自适应"}.get(mode, mode)


# ═══════════════════════════════════════════════════════════════
# 数据采集器
# ═══════════════════════════════════════════════════════════════

class PressDataCollector:
    """从 shared_control_node 的 stdout 中采集按压数据"""

    # 新 CSV 格式 header
    CSV_HEADER = [
        "timestamp", "cycle", "object", "label",
        "detection_class", "detection_label",
        "K_trans", "admittance_K", "deadband",
        "F_ext_x", "F_ext_y", "F_ext_z",
        "F_fb_x", "F_fb_y", "F_fb_z",
        "target_pos_x", "target_pos_y", "target_pos_z",
        "actual_pos_x", "actual_pos_y", "actual_pos_z",
        "pos_error_x", "pos_error_y", "pos_error_z",
        "grip", "omega_grip_norm", "user_intent",
    ]

    def __init__(self, output_dir: Path, mode: str, material_name: str,
                 trial_id: int):
        self.output_dir = output_dir
        self.mode = mode
        self.material_name = material_name
        self.trial_id = trial_id
        self.rows: List[dict] = []
        self.start_time = time.time()

        # CSV 文件
        csv_name = f"trial_{trial_id:03d}_mode{mode}_{material_name}.csv"
        self.csv_path = output_dir / csv_name
        self.csv_file = open(self.csv_path, "w", newline="")
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(self.CSV_HEADER)

    def feed_line(self, line: str):
        """解析 shared_control_node 的一行输出"""
        try:
            if "F_ext=" not in line or "F_fb=" not in line:
                return

            # 解析 cycle 编号
            parts = line.strip().split("]")
            if len(parts) < 2:
                return
            cycle_str = parts[0].strip("[ ")
            try:
                cycle = int(cycle_str)
            except ValueError:
                return

            # ── 解析所有字段 ──
            row = {
                "timestamp": f"{time.time() - self.start_time:.3f}",
                "cycle": cycle,
            }

            # 物体/标签
            row["detection_class"] = self._parse_field(line, "物体=", full=True)
            row["detection_label"] = self._parse_field(line, "label=", full=True)

            # 标准化 object/label（兼容原有格式）
            row["object"] = row["detection_class"]
            row["label"] = row["detection_label"]

            # F_ext
            fext = self._parse_vector(line, "F_ext=")
            row["F_ext_x"] = f"{fext[0]:.4f}"
            row["F_ext_y"] = f"{fext[1]:.4f}"
            row["F_ext_z"] = f"{fext[2]:.4f}"

            # F_fb
            ffb = self._parse_vector(line, "F_fb=")
            row["F_fb_x"] = f"{ffb[0]:.4f}"
            row["F_fb_y"] = f"{ffb[1]:.4f}"
            row["F_fb_z"] = f"{ffb[2]:.4f}"

            # grip
            row["grip"] = self._parse_field(line, "grip=")

            # 扩展字段: Kt, Ka, db
            row["K_trans"] = self._parse_field(line, "Kt=")
            row["admittance_K"] = self._parse_field(line, "Ka=")
            row["deadband"] = self._parse_field(line, "db=")

            # 位置数据: tgt_z, act_z, err_z
            row["target_pos_x"] = "0.0"
            row["target_pos_y"] = "0.0"
            row["target_pos_z"] = self._parse_field(line, "tgt_z=")

            row["actual_pos_x"] = "0.0"
            row["actual_pos_y"] = "0.0"
            row["actual_pos_z"] = self._parse_field(line, "act_z=")

            row["pos_error_x"] = "0.0"
            row["pos_error_y"] = "0.0"
            row["pos_error_z"] = self._parse_field(line, "err_z=")

            # Omega 状态
            row["omega_grip_norm"] = self._parse_field(line, "Omega_norm=")

            # 用户意图
            intent_raw = self._parse_field(line, "意图=", full=True)
            row["user_intent"] = intent_raw

            self.rows.append(row)

            # 写入 CSV
            self.csv_writer.writerow([row.get(h, "0.0") for h in self.CSV_HEADER])

        except Exception:
            # 单行解析失败不影响后续
            pass

    def _parse_field(self, line: str, prefix: str, full: bool = False) -> str:
        """解析单值字段"""
        if prefix not in line:
            return "0.0"
        after = line.split(prefix)[1].strip()
        if full:
            # 返回直到下一个空格/结尾的完整内容
            return after.split()[0].strip() if after else "N/A"
        # 数值字段
        val = after.split()[0].strip() if after else "0.0"
        # 去除非数值字符（如 Unicode 符号）
        val = val.replace("🔒", "").replace("⏸", "").replace("⚠️", "").replace("回退默认", "0")
        return val

    def _parse_vector(self, line: str, prefix: str) -> Tuple[float, float, float]:
        """解析 (x, y, z) 格式向量"""
        try:
            if prefix not in line:
                return (0.0, 0.0, 0.0)
            after = line.split(prefix)[1].strip()
            if not after.startswith("("):
                return (0.0, 0.0, 0.0)
            end = after.find(")")
            vec_str = after[1:end]
            parts = [float(p.strip()) for p in vec_str.split(",")]
            if len(parts) >= 3:
                return (parts[0], parts[1], parts[2])
            return (0.0, 0.0, 0.0)
        except Exception:
            return (0.0, 0.0, 0.0)

    def close(self):
        self.csv_file.close()

    def summary(self) -> dict:
        """计算本轮按压数据统计"""
        if not self.rows:
            return {"samples": 0, "error": "no data"}

        try:
            fext_z = [float(r.get("F_ext_z", 0)) for r in self.rows]
            ffb_z = [float(r.get("F_fb_z", 0)) for r in self.rows]
            err_z = [float(r.get("pos_error_z", 0)) for r in self.rows]
            adm = [float(r.get("admittance_K", 100)) for r in self.rows]

            def stats(vals):
                if not vals:
                    return {"mean": 0, "std": 0, "max": 0, "min": 0}
                arr = [v for v in vals if abs(v) < 1e6]  # 剔除异常值
                if not arr:
                    return {"mean": 0, "std": 0, "max": 0, "min": 0}
                n = len(arr)
                mean = sum(arr) / n
                var = sum((v - mean)**2 for v in arr) / n
                return {
                    "mean": round(mean, 4),
                    "std": round(var**0.5, 4),
                    "max": round(max(arr), 4),
                    "min": round(min(arr), 4),
                }
        except Exception:
            return {"samples": len(self.rows)}

        return {
            "samples": len(self.rows),
            "F_ext_z": stats(fext_z),
            "F_fb_z": stats(ffb_z),
            "pos_error_z": stats(err_z),
            "admittance_K": stats(adm),
            "max_F_ext_z": max(abs(v) for v in fext_z) if fext_z else 0,
            "max_F_fb_z": max(abs(v) for v in ffb_z) if ffb_z else 0,
        }


# ═══════════════════════════════════════════════════════════════
# 实验计划生成
# ═══════════════════════════════════════════════════════════════

def build_experiment_plan(operator_id: int) -> List[dict]:
    """生成完整按压实验计划（拉丁方 + 随机化）"""
    mode_order = latin_square_order(operator_id)
    plan = []

    for mode in mode_order:
        # 每种模式下，材质顺序打乱
        shuffled = list(MATERIALS)
        random.shuffle(shuffled)
        for mat_display, mat_yolo, mat_label, mat_desc in shuffled:
            for trial in range(1, TRIALS_PER_COMBO + 1):
                plan.append({
                    "mode": mode,
                    "mat_display": mat_display,
                    "mat_yolo": mat_yolo,
                    "mat_label": mat_label,
                    "mat_desc": mat_desc,
                    "trial": trial,
                    "force_label": None,  # 默认使用 YOLO，字段由 build_manual_plan 设置
                })

    return plan


def print_plan(plan: List[dict]):
    """打印实验计划"""
    print("=" * 70)
    print("按压实验计划")
    print("=" * 70)
    print(f"模式顺序: {' → '.join(mode_name(m) for m in latin_square_order(1))}")
    print(f"材质: {', '.join(m[0] for m in MATERIALS)}")
    print(f"每组合重复: {TRIALS_PER_COMBO} 次")
    print(f"总按压次数: {len(plan)}")
    print("-" * 70)

    current_mode = None
    for i, exp in enumerate(plan, 1):
        if exp["mode"] != current_mode:
            current_mode = exp["mode"]
            print(f"\n  ── 模式 {mode_name(current_mode)} ──")
        print(f"  [{i:3d}] {exp['mat_display']:4s} (YOLO: {exp['mat_yolo']:<10}) "
              f"trial {exp['trial']:2d}/{TRIALS_PER_COMBO}")
    print("\n" + "=" * 70)


# ═══════════════════════════════════════════════════════════════
# 单次按压执行
# ═══════════════════════════════════════════════════════════════

def build_manual_plan(operator_id: int, material_preset: str) -> List[dict]:
    """生成使用手动材质预设的实验计划（跳过 YOLO 检测）"""
    mode_order = latin_square_order(operator_id)
    plan = []
    for mode in mode_order:
        # 所有 trial 使用同一种手动材质
        for trial in range(1, TRIALS_PER_COMBO + 1):
            plan.append({
                "mode": mode,
                "mat_display": material_preset.capitalize(),
                "mat_yolo": material_preset,  # 直接用 preset 名
                "mat_label": material_preset,
                "mat_desc": (f"{material_preset}: "
                             f"K={MATERIAL_PRESETS[material_preset]['admittance_K']} N/m, "
                             f"K_trans={MATERIAL_PRESETS[material_preset]['K_trans']}"),
                "trial": trial,
                "force_label": material_preset,  # 传给 --force-label
            })
    return plan


def run_single_press(exp: dict, data_dir: Path, operator_id: int) -> Optional[dict]:
    """执行单次按压并采集数据

    流程:
        1. 启动 shared_control_node --mode X 子进程
        2. 等待 stdout 中出现 F_ext 信号（说明接触发生）
        3. 采集 PRESS_SAMPLES 个周期数据
        4. 提示操作者抬起
        5. 保存 CSV 和元数据
    """
    mode = exp["mode"]
    mat_display = exp["mat_display"]
    mat_yolo = exp["mat_yolo"]
    mat_label = exp["mat_label"]
    trial = exp["trial"]

    print(f"\n{'─' * 60}")
    print(f"按压 #{trial}/{TRIALS_PER_COMBO} | "
          f"模式 {mode_name(mode)} | "
          f"物体: {mat_display}")
    print(f"{'─' * 60}")

    input("  ⏺ 准备好后按 Enter 开始本次按压...")

    # 操作者提示
    print(f"\n   📋 操作提示:")
    print(f"      - 本次物体: {mat_display} (戴好眼罩)")
    print(f"      - 垂直下压约 2cm，然后抬起")
    print(f"      - 感受末端硬度")
    print(f"      - 超时 {TRIAL_TIMEOUT}s 自动停止")
    print(f"      - 开始!\n")

    # 创建数据收集器
    collector = PressDataCollector(data_dir, mode, mat_yolo, trial)

    # 启动 shared_control_node（如果指定了 force_label，跳过 YOLO 检测）
    cmd = [sys.executable, SHARED_CONTROL_SCRIPT, "--mode", mode]
    if exp.get("force_label"):
        cmd += ["--force-label", exp["force_label"]]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    metadata = {
        "operator": operator_id,
        "mode": mode,
        "material_display": mat_display,
        "material_yolo": mat_yolo,
        "material_label": mat_label,
        "trial": trial,
        "total_trials": TRIALS_PER_COMBO,
        "timestamp": timestamp(),
        "status": "running",
        "result": "",
    }

    try:
        t_start = time.time()
        contact_detected = False
        contact_cycle = 0

        for line in iter(proc.stdout.readline, ""):
            # 回显到终端
            print(line, end="")

            # 采集数据
            collector.feed_line(line)

            # 检测接触：F_ext_z 超过阈值
            if not contact_detected and "F_ext=" in line:
                try:
                    after = line.split("F_ext=")[1].strip()
                    if after.startswith("("):
                        end = after.find(")")
                        vec_str = after[1:end]
                        parts = [float(p.strip()) for p in vec_str.split(",")]
                        if len(parts) >= 3 and abs(parts[2]) > 0.5:
                            contact_detected = True
                            contact_cycle = len(collector.rows)
                            print(f"\n  ✅ 接触检测到! F_ext_z={parts[2]:.2f}N\n")
                except Exception:
                    pass

            # 超时检查
            elapsed = time.time() - t_start
            if elapsed > TRIAL_TIMEOUT:
                print(f"\n  ⏰ 超时 ({TRIAL_TIMEOUT}s)，停止采集")
                metadata["result"] = "timeout"
                break

            # 采集足够数据后自动停止
            if contact_detected:
                post_contact = len(collector.rows) - contact_cycle
                if post_contact >= PRESS_SAMPLES:
                    print(f"\n  ✅ 已采集 {PRESS_SAMPLES} 个接触后周期，停止")
                    metadata["result"] = "completed"
                    break

    except KeyboardInterrupt:
        print(f"\n  ⏹ 用户中断")
        metadata["result"] = "interrupted"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        collector.close()

    # 计算统计
    stats = collector.summary()
    metadata["stats"] = stats

    # 保存元数据
    import yaml
    meta_path = data_dir / f"trial_{trial:03d}_mode{mode}_{mat_yolo}_meta.yaml"
    with open(meta_path, "w") as f:
        yaml.dump(metadata, f)

    print(f"\n  💾 数据保存: {collector.csv_path}")
    if stats and "samples" in stats:
        print(f"     采集样本: {stats['samples']}")
        print(f"     F_ext_z max: {stats.get('max_F_ext_z', 0):.2f} N")
        print(f"     F_fb_z max: {stats.get('max_F_fb_z', 0):.2f} N")

    return metadata


# ═══════════════════════════════════════════════════════════════
# 主观评分记录
# ═══════════════════════════════════════════════════════════════

def record_subjective_scores(output_dir: Path, mode: str, operator_id: int):
    """记录盲测主观评分（每次按压后口述）

    三围度:
        1. 感知硬度 (Perceived Hardness): 1(很软) ~ 10(很硬)
        2. 触觉阻力 (Haptic Resistance): 1(无阻力) ~ 10(阻力很大)
        3. 末端顺从性 (End-effector Compliance): 1(僵硬) ~ 10(很顺从)
    """
    import yaml

    print(f"\n  📝 盲测主观评分 (模式 {mode_name(mode)})")
    print(f"    请在 1-10 分制内回答以下 3 个问题:\n")

    questions = [
        ("perceived_hardness", "感知硬度", "1=很软(像海绵), 10=很硬(像木板)"),
        ("haptic_resistance", "触觉阻力", "1=无阻力, 10=阻力很大"),
        ("end_effector_compliance", "末端顺从性", "1=僵硬不动, 10=很顺从"),
    ]

    scores = {"mode": mode, "operator": operator_id, "timestamp": timestamp()}

    for key, name, hint in questions:
        while True:
            try:
                val = input(f"    {name} ({hint}): ")
                score = int(val.strip())
                if 1 <= score <= 10:
                    scores[key] = score
                    break
                else:
                    print("      ⚠️ 请输入 1-10 之间的整数")
            except (ValueError, TypeError):
                print("      ⚠️ 请输入有效数字")

    # 保存
    score_path = output_dir / f"scores_mode{mode}.yaml"
    if score_path.exists():
        with open(score_path, "r") as f:
            existing = yaml.safe_load(f) or []
    else:
        existing = []
    existing.append(scores)
    with open(score_path, "w") as f:
        yaml.dump(existing, f)

    print(f"  ✅ 评分已保存到 {score_path}")
    return scores


# ═══════════════════════════════════════════════════════════════
# 完整实验运行
# ═══════════════════════════════════════════════════════════════

def run_full_experiment(operator_id: int, dry_run: bool = False,
                        preset_override: Optional[str] = None):
    """运行完整的按压实验

    流程:
        for each mode (拉丁方顺序):
            for each material (随机顺序):
                for trial in 1..10:
                    1. 操作者戴眼罩
                    2. 按压物体
                    3. 采集数据
                    4. 口述主观评分
            NASA-TLX 问卷（纸质）

    拉丁方示例:
        操作员1: A→B→C (每模式下材质内部随机)
        操作员2: B→C→A
        操作员3: C→A→B
    """
    if preset_override:
        plan = build_manual_plan(operator_id, preset_override)
    else:
        plan = build_experiment_plan(operator_id)

    print("\n" + "=" * 70)
    print(f"  按压实验 — 操作员 {operator_id}")
    print(f"  模式顺序: {' → '.join(mode_name(m) for m in latin_square_order(operator_id))}")
    print(f"  物体材质: {', '.join(m[0] for m in MATERIALS)}")
    print(f"  总按压次数: {len(plan)} ({3}模式 × {3}材质 × {TRIALS_PER_COMBO}次)")
    print("  操作者需戴眼罩（盲测）")
    print("=" * 70)

    if dry_run:
        print_plan(plan)
        return

    # 创建实验目录
    exp_ts = timestamp()
    exp_dir = ensure_dir(DATA_DIR / f"press_{exp_ts}" / f"operator_{operator_id}")

    # 保存实验配置
    import yaml
    config = {
        "experiment_type": "press",
        "operator": operator_id,
        "modes": MODES,
        "materials": [{"display": d, "yolo": y, "label": l}
                      for d, y, l, _ in MATERIALS],
        "trials_per_combo": TRIALS_PER_COMBO,
        "mode_order": latin_square_order(operator_id),
        "timestamp": exp_ts,
    }
    with open(exp_dir / "config.yaml", "w") as f:
        yaml.dump(config, f)

    # 执行实验
    current_mode = None
    all_results = []

    for i, exp in enumerate(plan, 1):
        # 模式切换提示
        if exp["mode"] != current_mode:
            if current_mode is not None:
                # 当前模式结束后，记录主观评分
                record_subjective_scores(exp_dir, current_mode, operator_id)
                print(f"\n  休息 {MODE_CHANGE_DELAY}s 后切换到下一模式...")
                time.sleep(MODE_CHANGE_DELAY)
            current_mode = exp["mode"]
            print(f"\n{'=' * 60}")
            print(f"  开始模式 {mode_name(current_mode)}")
            print(f"{'=' * 60}")

        # 材质切换提示
        if i == 1 or (i > 1 and exp["mat_yolo"] != plan[i-2]["mat_yolo"]):
            print(f"\n  🔄 换材质为: {exp['mat_display']} ({exp['mat_desc']})")
            input("  准备好后按 Enter 继续...")
        elif i > 1:
            # 同材质内，短等待即可
            time.sleep(1.0)

        # 执行单次按压
        result = run_single_press(exp, exp_dir, operator_id)
        if result:
            all_results.append(result)

        print(f"\n  进度: [{i}/{len(plan)}] "
              f"({i/len(plan)*100:.0f}%)")

    # 最后一种模式结束后记录评分
    record_subjective_scores(exp_dir, current_mode, operator_id)

    # 生成总结
    summary_path = generate_summary(all_results, exp_dir, operator_id)

    print(f"\n{'=' * 70}")
    print(f"  ✅ 所有实验完成!")
    print(f"  数据目录: {exp_dir}")
    print(f"  总结报告: {summary_path}")
    print(f"{'=' * 70}")


# ═══════════════════════════════════════════════════════════════
# 总结生成
# ═══════════════════════════════════════════════════════════════

def generate_summary(results: List[dict], output_dir: Path,
                     operator_id: int) -> Path:
    """生成 Markdown 总结报告"""
    path = output_dir / "summary.md"

    with open(path, "w") as f:
        f.write(f"# 按压实验总结\n\n")
        f.write(f"**操作员**: {operator_id}\n\n")
        f.write(f"**生成时间**: {timestamp()}\n\n")

        # 按模式汇总
        f.write("## 按模式统计\n\n")
        f.write("| 模式 | 物体 | 次数 | max_F_ext_z(N) | max_F_fb_z(N) | K_eff(N/m) |\n")
        f.write("|------|------|------|---------------|---------------|------------|\n")

        by_mode_mat = defaultdict(list)
        for r in results:
            key = (r.get("mode", "?"), r.get("material_display", "?"))
            by_mode_mat[key].append(r)

        for key in sorted(by_mode_mat.keys()):
            mode, mat = key
            group = by_mode_mat[key]
            n = len(group)
            max_fext = max(r.get("stats", {}).get("max_F_ext_z", 0) for r in group)
            max_ffb = max(r.get("stats", {}).get("max_F_fb_z", 0) for r in group)

            # 计算等效刚度均值
            keff_list = []
            for r in group:
                s = r.get("stats", {})
                fext_m = s.get("F_ext_z", {}).get("mean", 0)
                err_m = s.get("pos_error_z", {}).get("mean", 0)
                if abs(err_m) > 0.001:
                    keff_list.append(abs(fext_m / err_m))
            avg_keff = sum(keff_list) / len(keff_list) if keff_list else 0

            f.write(f"| {mode_name(mode)} | {mat} | {n} | "
                    f"{max_fext:.2f} | {max_ffb:.2f} | {avg_keff:.1f} |\n")

        # 整体统计
        f.write("\n## 总体对比\n\n")
        for mode in ["a", "b", "c"]:
            mode_results = [r for r in results if r.get("mode") == mode]
            if not mode_results:
                continue
            avg_ffb = sum(
                r.get("stats", {}).get("max_F_fb_z", 0) for r in mode_results
            ) / len(mode_results)
            avg_fext = sum(
                r.get("stats", {}).get("max_F_ext_z", 0) for r in mode_results
            ) / len(mode_results)
            f.write(f"- **{mode_name(mode)}**: "
                    f"平均 max_F_fb_z={avg_ffb:.2f}N, "
                    f"平均 max_F_ext_z={avg_fext:.2f}N\n")

    return path


# ═══════════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="按压实验运行器")
    parser.add_argument("--operator", type=int, default=1,
                        help="操作员编号 (默认 1)")
    parser.add_argument("--mode", choices=MODES,
                        help="仅运行指定模式")
    parser.add_argument("--material", choices=[m[1] for m in MATERIALS],
                        help="仅运行指定材质 (YOLO class)")
    parser.add_argument("--material-preset", choices=list(MATERIAL_PRESETS.keys()),
                        help="手动指定材质级别 soft/medium/hard，跳过 YOLO 检测")
    parser.add_argument("--dry-run", action="store_true",
                        help="仅打印实验计划，不执行")
    parser.add_argument("--full", action="store_true", default=True,
                        help="运行完整实验 (默认)")

    args = parser.parse_args()

    # ── 手动材质预设模式（跳过 YOLO）──
    if args.material_preset:
        print(f"\n  🔧 手动材质模式: {args.material_preset}")
        print(f"     参数: K={MATERIAL_PRESETS[args.material_preset]['admittance_K']} N/m, "
              f"K_trans={MATERIAL_PRESETS[args.material_preset]['K_trans']}")
        plan = build_manual_plan(args.operator, args.material_preset)
        if not args.dry_run:
            print(f"\n  即将执行 {len(plan)} 次按压（3 模式 × {TRIALS_PER_COMBO} 次重复）")
            input("  准备好后按 Enter 开始...")
        run_full_experiment(args.operator, dry_run=args.dry_run,
                            preset_override=args.material_preset)
        return

    # ── 原有 YOLO 检测模式 ──
    if args.mode or args.material:
        plan = build_experiment_plan(args.operator)
        filtered = [e for e in plan
                    if (not args.mode or e["mode"] == args.mode)
                    and (not args.material or e["mat_yolo"] == args.material)]

        if not filtered:
            print(f"未找到匹配: mode={args.mode}, material={args.material}")
            sys.exit(1)

        exp_ts = timestamp()
        data_dir = ensure_dir(
            DATA_DIR / f"press_{exp_ts}" / f"operator_{args.operator}"
        )
        run_single_press(filtered[0], data_dir, args.operator)
    else:
        run_full_experiment(args.operator, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
