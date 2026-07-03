#!/usr/bin/env python3
"""
扫描 my_test/data/ 下的所有CSV文件，计算总时长（最大time - 最小time），
并更新对应JSON文件中的 runtime.duration_s 字段。

用法:
    python3 my_test/update_duration_from_csv.py
    python3 my_test/update_duration_from_csv.py --dry-run   # 仅预览，不写入
    python3 my_test/update_duration_from_csv.py --verbose   # 显示详细信息
"""

import os
import json
import csv
import glob
import argparse
from pathlib import Path

DATA_DIR = os.path.join("my_test", "data")
EXPERIMENT_TYPES = ["hard_date", "medium_date", "soft_date"]
SKIP_DIRS = {"_backup_vision_stiffness"}


def find_csv_json_pairs(data_dir):
    """遍历目录，找到所有CSV文件并匹配对应的JSON文件"""
    pairs = []
    for root, dirs, files in os.walk(data_dir):
        # 跳过备份目录
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for f in files:
            if not f.endswith(".csv"):
                continue
            csv_path = os.path.join(root, f)

            # 找出对应的JSON文件
            basename = f.replace(".csv", "")
            # JSON文件可能以 _summary.json 结尾
            json_candidates = [
                os.path.join(root, basename + "_summary.json"),
                os.path.join(root, basename + ".json"),
            ]
            json_path = None
            for jc in json_candidates:
                if os.path.exists(jc):
                    json_path = jc
                    break

            if json_path is None:
                print(f"  ⚠ 未找到 {f} 对应的JSON文件，跳过")
                continue

            pairs.append((csv_path, json_path))
    return pairs


def compute_duration_from_csv(csv_path):
    """从CSV文件计算总时长 = 最后一行time - 第一行time"""
    try:
        with open(csv_path, "r") as f:
            reader = csv.DictReader(f)
            if "time" not in reader.fieldnames:
                print(f"  ⚠ {csv_path} 没有time列，跳过")
                return None
            
            times = []
            for row in reader:
                try:
                    t = float(row["time"])
                    times.append(t)
                except (ValueError, KeyError):
                    continue
            
            if len(times) < 2:
                print(f"  ⚠ {csv_path} 有效数据点不足({len(times)})，跳过")
                return None
            
            duration = times[-1] - times[0]
            return round(duration, 4)
    except Exception as e:
        print(f"  ❌ 读取CSV失败 {csv_path}: {e}")
        return None


def update_json_duration(json_path, new_duration, dry_run=False):
    """更新JSON文件中的runtime.duration_s"""
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
        
        if "runtime" not in data:
            print(f"  ⚠ {json_path} 没有runtime字段，跳过")
            return False
        
        old_duration = data["runtime"].get("duration_s")
        
        if old_duration is not None and abs(old_duration - new_duration) < 0.01:
            # 已经正确，无需更新
            return False
        
        data["runtime"]["duration_s"] = new_duration
        
        if not dry_run:
            with open(json_path, "w") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")  # 末尾换行
        
        return True
    except Exception as e:
        print(f"  ❌ 更新JSON失败 {json_path}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="从CSV计算总时长并更新JSON")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不写入")
    parser.add_argument("--verbose", action="store_true", help="显示详细信息")
    args = parser.parse_args()

    all_pairs = []
    for exp_type in EXPERIMENT_TYPES:
        exp_dir = os.path.join(DATA_DIR, exp_type)
        if os.path.isdir(exp_dir):
            pairs = find_csv_json_pairs(exp_dir)
            all_pairs.extend(pairs)
            if args.verbose:
                print(f"📁 {exp_type}: 找到 {len(pairs)} 对 CSV/JSON")
    
    print(f"\n总计找到 {len(all_pairs)} 对 CSV/JSON 文件\n")

    updated_count = 0
    skip_count = 0
    error_count = 0

    for csv_path, json_path in all_pairs:
        rel_csv = os.path.relpath(csv_path, DATA_DIR)
        rel_json = os.path.relpath(json_path, DATA_DIR)

        duration = compute_duration_from_csv(csv_path)
        if duration is None:
            error_count += 1
            continue

        updated = update_json_duration(json_path, duration, dry_run=args.dry_run)
        
        if updated:
            # 读出旧值用于对比
            try:
                with open(json_path, "r") as f:
                    old_data = json.load(f)
                old_duration = old_data["runtime"].get("duration_s", "N/A")
            except:
                old_duration = "N/A"
            
            action = "[DRY-RUN]" if args.dry_run else "[UPDATED]"
            print(f"  {action} {rel_json}")
            print(f"         duration_s: {old_duration} → {duration}")
            updated_count += 1
        else:
            if args.verbose:
                print(f"  [SKIP] {rel_json} (无需更新或已正确)")
            skip_count += 1

    print(f"\n{'='*50}")
    if args.dry_run:
        print(f"🔍 DRY-RUN 完成: 将更新 {updated_count} 个文件, {skip_count} 个无需更新, {error_count} 个错误")
    else:
        print(f"✅ 完成: 更新了 {updated_count} 个文件, {skip_count} 个无需更新, {error_count} 个错误")


if __name__ == "__main__":
    main()
