#!/usr/bin/env python3
"""
extract_all_trials.py — 从所有实验目录的 summary.json 提取客观指标
输出: all_trials_135.csv (135行, 含操作者/对象属性/模式/完成时间/轨迹长度)
"""

import json, csv, os, re, sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent
OUTPUT_CSV = DATA_DIR / "all_trials_135.csv"

# 模式名映射: 目录文件名 → 论文模式名
MODE_MAP = {
    "default":         "A",  # 固定参数
    "soft_obj":        "B",  # 人工选择(软)
    "medium_obj":      "B",  # 人工选择(中)
    "hard_obj":        "B",  # 人工选择(硬)
    "vision":          "C",  # 视觉多参数
    "vision_observe":  "D",  # 视觉仅观察
    "vision_stiffness":"E",  # 视觉仅阻抗
}

# 操作者映射
OPERATOR_MAP = {
    "第一实验员": "P01",
    "第二实验员": "P02",
    "第三实验员": "P03",
}

# 对象属性目录映射
OBJECT_DIR_MAP = {
    "soft_date":   "soft",
    "medium_date": "medium",
    "hard_date":   "hard",
}

def get_summary_file(trial_dir):
    """查找目录中的 summary JSON 文件"""
    # 优先找 _summary.json
    files = list(trial_dir.glob("*_summary.json"))
    if files:
        return files[0]
    # 其次找 .json (不含 summary)
    files = list(trial_dir.glob("*.json"))
    # 排除 _experiment_objects.md？实际上这是.md不是.json
    # 排除任何以 _backup 开头的目录
    files = [f for f in files if not f.name.startswith("_")]
    if files:
        return files[0]
    return None

def main():
    rows = []
    errors = []
    trial_count = 0

    # 遍历三个对象属性目录
    for obj_dir_name in sorted(OBJECT_DIR_MAP.keys()):
        obj_attr = OBJECT_DIR_MAP[obj_dir_name]
        obj_dir = DATA_DIR / obj_dir_name
        
        if not obj_dir.exists():
            errors.append(f"目录不存在: {obj_dir}")
            continue
        
        # 遍历三个实验员目录
        for operator_dir in sorted(obj_dir.iterdir()):
            if not operator_dir.is_dir():
                continue
            operator_name = operator_dir.name
            operator_id = OPERATOR_MAP.get(operator_name, operator_name)
            
            # 遍历每个组次目录
            for group_dir in sorted(operator_dir.iterdir()):
                if not group_dir.is_dir():
                    continue
                # 跳过 _backup 目录
                if group_dir.name.startswith("_"):
                    continue
                    
                # 读取 _experiment_objects.md 获取具体对象信息
                obj_md = group_dir / "_experiment_objects.md"
                specific_object = "unknown"
                if obj_md.exists():
                    content = obj_md.read_text(encoding="utf-8")
                    m = re.search(r"操作物体:\s*(.+)", content)
                    if m:
                        specific_object = m.group(1).strip()
                    # 读取组号
                    # 从目录名提取组号
                
                # 提取组号
                group_match = re.search(r"第([一二三四五六七八九十\d]+)组", group_dir.name)
                if group_match:
                    group_num_str = group_match.group(1)
                    # 中文数字映射
                    cn_num_map = {
                        "一":1, "二":2, "三":3, "四":4, "五":5, 
                        "六":6, "七":7, "八":8, "九":9, "十":10
                    }
                    if group_num_str.isdigit():
                        group_num = int(group_num_str)
                    else:
                        group_num = cn_num_map.get(group_num_str, 0)
                else:
                    group_num = 0

                # 遍历目录下所有模式对应的 summary 文件
                for file in sorted(group_dir.iterdir()):
                    if not file.is_file():
                        continue
                    
                    fname = file.name
                    # 识别模式: 从文件名提取前缀
                    # e.g. default_summary.json, vision.csv, vision_stiffness_summary.json
                    mode_key = None
                    for key in sorted(MODE_MAP.keys(), key=len, reverse=True):
                        if fname.startswith(key) and (fname.endswith("_summary.json") or fname.endswith(".json")):
                            mode_key = key
                            break
                    
                    if mode_key is None:
                        continue
                    
                    # 只处理 JSON 文件
                    if not (fname.endswith("_summary.json") or fname.endswith(".json")):
                        continue
                    
                    # 跳过非 summary 文件（只保留 summary 的）
                    # 但有的目录只有 .json 没有 _summary.json
                    # 优先使用 _summary.json
                    is_summary = fname.endswith("_summary.json")
                    if not is_summary:
                        # 如果同时存在 _summary.json 和 .json，则跳过 .json
                        summary_ver = group_dir / f"{mode_key}_summary.json"
                        if summary_ver.exists():
                            continue
                    
                    try:
                        data = json.loads(file.read_text(encoding="utf-8"))
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        errors.append(f"JSON解析失败: {file} - {e}")
                        continue
                    
                    # 提取 runtime 信息
                    runtime = data.get("runtime", data.get("trajectory", {}))
                    if "runtime" in data:
                        duration = data["runtime"].get("duration_s", None)
                        traj_len = data["runtime"].get("traj_length_m", None)
                    elif "duration_s" in data:
                        duration = data.get("duration_s", None)
                        traj_len = None
                    else:
                        duration = None
                        traj_len = None
                    
                    if duration is None:
                        # 尝试从 trajectory 里找
                        traj = data.get("trajectory", {})
                        if "n_samples" in traj:
                            duration = None  # 无法从轨迹推算时间
                    
                    mode_label = MODE_MAP.get(mode_key, mode_key)
                    
                    # 对于 B 模式，记录具体选择了什么对象属性
                    b_subtype = ""
                    if mode_key in ("soft_obj", "medium_obj", "hard_obj"):
                        b_subtype = mode_key.replace("_obj", "")
                    
                    rows.append({
                        "operator": operator_id,
                        "group_num": group_num,
                        "object_attr": obj_attr,
                        "specific_object": specific_object,
                        "mode": mode_label,
                        "b_subtype": b_subtype,
                        "duration_s": duration if duration is not None else "",
                        "traj_length_m": traj_len if traj_len is not None else "",
                        "source_file": str(file.relative_to(DATA_DIR)),
                    })
                    trial_count += 1

    # 写入 CSV
    fieldnames = [
        "operator", "group_num", "object_attr", "specific_object",
        "mode", "b_subtype", "duration_s", "traj_length_m", "source_file"
    ]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    
    # 打印汇总
    print(f"✅ 共提取 {trial_count} 次试验数据 → {OUTPUT_CSV}")
    print(f"\n各模式计数:")
    mode_counts = {}
    for r in rows:
        mode_counts[r["mode"]] = mode_counts.get(r["mode"], 0) + 1
    for m in sorted(mode_counts.keys()):
        print(f"  模式 {m}: {mode_counts[m]} 次")
    
    print(f"\n各操作者计数:")
    op_counts = {}
    for r in rows:
        op_counts[r["operator"]] = op_counts.get(r["operator"], 0) + 1
    for o in sorted(op_counts.keys()):
        print(f"  {o}: {op_counts[o]} 次")
    
    if errors:
        print(f"\n⚠️  警告: 存在 {len(errors)} 个错误:")
        for e in errors:
            print(f"  - {e}")
    
    # 检查缺失数值
    missing_dur = sum(1 for r in rows if r["duration_s"] == "")
    missing_traj = sum(1 for r in rows if r["traj_length_m"] == "")
    if missing_dur:
        print(f"\n⚠️  缺失 duration_s: {missing_dur} 条")
    if missing_traj:
        print(f"\n⚠️  缺失 traj_length_m: {missing_traj} 条")

if __name__ == "__main__":
    main()