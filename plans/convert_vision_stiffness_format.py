#!/usr/bin/env python3
"""
convert_vision_stiffness_format.py
===================================
自动发现所有组中的 vision_stiffness v2 格式文件，
将其转换为与其他模式一致的 v1 格式（12列CSV + 基础JSON）。

转换前会自动备份原始文件到 _backup_vision_stiffness/ 目录。
"""

import csv
import json
import shutil
import sys
import re
from pathlib import Path

# ── 搜索路径 ──
SEARCH_BASES = [
    "my_test/data/hard_date",
    "my_test/data/medium_date",
    "my_test/data/soft_date",
]

# ── v1 CSV header（与其他模式一致） ──
V1_CSV_HEADER = [
    "time", "x", "y", "z", "gripper_deg", "button",
    "K_trans", "K_rot", "damping_ratio", "K_fb", "deadband", "scale",
]

# ── v2 → v1 列名映射 ──
COLUMN_MAP = {
    "time": "system_time",
    "x": "robot_x",
    "y": "robot_y",
    "z": "robot_z",
    "gripper_deg": "gripper_deg",
    "button": "button",
    "K_trans": "K_trans",
    "K_rot": "K_rot",
    "damping_ratio": "damping_ratio",
    "K_fb": "K_fb",
    "deadband": "deadband",
    "scale": "scale",
}


def discover_trials(base_path: Path) -> list:
    """
    在 base_path 下所有子目录中，自动发现 vision_stiffness 的 trial 文件。
    
    返回: list of (group_dir, csv_path, summary_path, events_path)
    """
    trials = []
    # 正则匹配：vision_stiffness_YYYYMMDD_HHMMSS.csv
    pattern = re.compile(r"^vision_stiffness_\d{8}_\d{6}\.csv$")
    
    for group_dir in sorted(base_path.iterdir()):
        if not group_dir.is_dir():
            continue
        # 跳过备份目录
        if group_dir.name.startswith("_"):
            continue
        for f in group_dir.iterdir():
            if f.is_file() and pattern.match(f.name):
                stem = f.stem  # vision_stiffness_YYYYMMDD_HHMMSS
                csv_path = f
                summary_path = group_dir / f"{stem}_summary.json"
                events_path = group_dir / f"{stem}_events.json"
                trials.append((group_dir, csv_path, summary_path, events_path))
    return trials


def backup_file(src_path: Path, backup_dir: Path) -> bool:
    if not src_path.exists():
        print(f"  ⚠️  未找到: {src_path.name}，跳过备份")
        return False
    backup_dir.mkdir(parents=True, exist_ok=True)
    dst = backup_dir / src_path.name
    shutil.copy2(src_path, dst)
    print(f"  ✅ 已备份: {src_path.name}")
    return True


def convert_csv(csv_path: Path) -> bool:
    if not csv_path.exists():
        print(f"  ⚠️  CSV 文件不存在: {csv_path}")
        return False

    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        v2_fieldnames = reader.fieldnames
        if not v2_fieldnames:
            print(f"  ❌  无法读取CSV header: {csv_path}")
            return False

        # 如果已经是 v1 格式，跳过
        if len(v2_fieldnames) == 12 and v2_fieldnames == V1_CSV_HEADER:
            print(f"  ⏭️  已经是 v1 格式，跳过")
            return True

        rows = list(reader)

    # 检查必需列是否存在
    missing_cols = [v2 for v1, v2 in COLUMN_MAP.items() if v2 not in v2_fieldnames]
    if missing_cols:
        print(f"  ❌  缺少列 {missing_cols}，无法转换")
        return False

    v1_rows = [
        {v1_col: row.get(v2_col, "") for v1_col, v2_col in COLUMN_MAP.items()}
        for row in rows
    ]

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=V1_CSV_HEADER)
        writer.writeheader()
        writer.writerows(v1_rows)

    print(f"  ✅ CSV 转换完成 ({len(v1_rows)} 行, {len(V1_CSV_HEADER)} 列)")
    return True


def convert_summary_json(json_path: Path, csv_path: Path) -> bool:
    if not json_path.exists():
        print(f"  ⚠️  JSON 不存在: {json_path.name}")
        return False

    with open(json_path, "r") as f:
        data = json.load(f)

    # 已经是 v1 格式（没有 experiment 块）则跳过
    if "experiment" not in data:
        print(f"  ⏭️  已经是 v1 格式，跳过")
        return True

    # ── 从 CSV 计算真实的 duration_s（CSV time 范围） ──
    duration_from_csv = data.get("runtime", {}).get("duration_s", 0.0)
    if csv_path.exists():
        try:
            with open(csv_path, "r", newline="") as cf:
                reader = csv.DictReader(cf)
                times = [float(r["time"]) for r in reader if r.get("time")]
            if times:
                duration_from_csv = round(times[-1] - times[0], 2)
        except Exception:
            pass

    # mode: 精简
    mode_v2 = data.get("mode", {})
    mode_v1 = {
        "mode": mode_v2.get("mode", "vision_stiffness"),
        "vision_enabled": mode_v2.get("vision_enabled", True),
    }

    # final_params: 去掉 vision_base_* 和 fusion_delta_K_final
    fp_v2 = data.get("final_params", {})
    final_params = {
        "K_trans": fp_v2.get("K_trans", 150.0),
        "K_rot": fp_v2.get("K_rot", 10.0),
        "damping_ratio": fp_v2.get("damping_ratio", 1.0),
        "K_fb": fp_v2.get("K_fb", 0.5),
        "deadband": fp_v2.get("deadband", 0.3),
        "scale": fp_v2.get("scale", 3.0),
    }

    # 用 CSV 计算的 duration 替换 runtime 中的 duration_s
    runtime = dict(data.get("runtime", {}))
    runtime["duration_s"] = duration_from_csv

    v1_data = {
        "timestamp": data.get("timestamp", ""),
        "saved_at": data.get("saved_at", ""),
        "mode": mode_v1,
        "runtime": runtime,
        "trajectory": data.get("trajectory", {}),
        "final_params": final_params,
    }

    with open(json_path, "w") as f:
        json.dump(v1_data, f, indent=2, ensure_ascii=False)

    print(f"  ✅ JSON 转换完成")
    return True


def delete_events_json(events_path: Path) -> bool:
    if not events_path.exists():
        print(f"  ⏭️  事件文件不存在，跳过删除")
        return False
    events_path.unlink()
    print(f"  🗑️  已删除: {events_path.name}")
    return True


def verify_conversion(csv_path: Path, json_path: Path) -> bool:
    ok = True

    # 验证 CSV
    if csv_path.exists():
        with open(csv_path, "r", newline="") as f:
            header = next(csv.reader(f), None)
        if header != V1_CSV_HEADER:
            print(f"  ❌  CSV header 不匹配")
            print(f"     期望: {V1_CSV_HEADER}")
            print(f"     实际: {header}")
            ok = False
        else:
            print(f"  ✅ CSV header 验证通过")
    else:
        print(f"  ❌  CSV 文件不存在")
        ok = False

    # 验证 JSON
    if json_path.exists():
        with open(json_path, "r") as f:
            data = json.load(f)
        assert_keys = ["timestamp", "saved_at", "mode", "runtime", "trajectory", "final_params"]
        unexpected_keys = ["external_force", "fusion_config", "experiment"]
        for k in assert_keys:
            if k not in data:
                print(f"  ❌  JSON 缺少键: {k}")
                ok = False
        for k in unexpected_keys:
            if k in data:
                print(f"  ❌  JSON 包含不应有的键: {k}")
                ok = False
        if ok:
            print(f"  ✅ JSON 结构验证通过")
    else:
        print(f"  ❌  JSON 文件不存在")
        ok = False

    return ok


def process_trial(group_dir: Path, csv_path: Path, summary_path: Path, events_path: Path) -> bool:
    print(f"\n{'='*60}")
    print(f"📁 {group_dir.parent.name} / {group_dir.name} / {csv_path.name}")
    print(f"{'='*60}")

    backup_dir = group_dir / "_backup_vision_stiffness"

    # 1. 备份
    print(f"\n📦 备份...")
    found = False
    for fp in [csv_path, summary_path, events_path]:
        if fp.exists():
            found = True
            backup_file(fp, backup_dir)
    if not found:
        print(f"  ⚠️  没有需要备份的文件")
        return False

    # 2. 转换 CSV
    print(f"\n🔄 CSV...")
    csv_ok = convert_csv(csv_path)

    # 3. 转换 JSON
    print(f"\n🔄 JSON...")
    json_ok = convert_summary_json(summary_path, csv_path)

    # 4. 删除 events
    print(f"\n🗑️  清理...")
    delete_events_json(events_path)

    # 5. 验证
    print(f"\n🔍 验证...")
    verify_ok = verify_conversion(csv_path, summary_path)

    return csv_ok and json_ok and verify_ok


def main():
    base_dir = Path(__file__).resolve().parent.parent
    overall_ok = True
    total = 0

    for base_rel in SEARCH_BASES:
        base_path = base_dir / base_rel
        if not base_path.exists():
            print(f"⚠️  目录不存在: {base_path}")
            continue

        print(f"\n📂 扫描: {base_rel}/")
        trials = discover_trials(base_path)
        print(f"   找到 {len(trials)} 个 vision_stiffness trial")

        for group_dir, csv_path, summary_path, events_path in trials:
            ok = process_trial(group_dir, csv_path, summary_path, events_path)
            overall_ok = overall_ok and ok
            if not ok:
                print(f"  ❌  处理失败!")
            total += 1

    print(f"\n{'='*60}")
    print(f"总计处理: {total} 个 trial")
    if overall_ok:
        print("✅ 全部转换成功！")
    else:
        print("⚠️  部分转换失败，请查看上面的错误信息")
    print(f"{'='*60}")

    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
