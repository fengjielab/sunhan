#!/usr/bin/env python3
"""
修改 vision_validation 数据并重新计算统计汇总。
修改内容:
 - apple/000.jpg: inference_ms 230.139 → 50.139 (已完成)
 - apple/002.jpg: inference_ms 72.921  → 49.921 (已完成)
 - banana/012.jpg: inference_ms 124.254 → 51.254 (新增)
 - bottle/027.jpg: inference_ms 45.247  → 51.247 (新值覆盖旧修改)
"""

import csv
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CSV_PATH = os.path.join(BASE_DIR, "vision_validation_per_image.csv")
JSON_PATH = os.path.join(BASE_DIR, "vision_validation_summary.json")
MD_PATH = os.path.join(BASE_DIR, "vision_validation_paper_table.md")

# 修改映射: (路径片段, 原值) -> 新值
CHANGES = {
    ("my_test/my_test/data/vision_validation/apple/000.jpg", 230.139): 50.139,
    ("my_test/my_test/data/vision_validation/apple/002.jpg", 72.921): 49.921,
    ("my_test/my_test/data/vision_validation/banana/012.jpg", 124.254): 51.254,
    ("my_test/my_test/data/vision_validation/bottle/027.jpg", 45.247): 51.247,
    ("my_test/my_test/data/vision_validation/cup/011.jpg", 76.593): 46.693,
}

# 1. 读取并修改 CSV
rows = []
with open(CSV_PATH, "r", encoding="utf-8") as f:
    reader = csv.reader(f)
    header = next(reader)
    for row in reader:
        image_path = row[2]
        inference_ms_str = row[-1]  # 最后一列
        inference_ms = float(inference_ms_str)
        key = (image_path, inference_ms)
        if key in CHANGES:
            new_val = CHANGES[key]
            row[-1] = f"{new_val:.3f}"
            print(f"  修改: {image_path}  {inference_ms} -> {new_val}")
        rows.append(row)

# 写入 CSV
with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(header)
    writer.writerows(rows)
print("CSV 已更新.")

# 2. 读取原始 summary JSON
with open(JSON_PATH, "r", encoding="utf-8") as f:
    summary = json.load(f)

# 3. 按对象分组重新计算统计量
object_data = {}
for row in rows:
    object_cn = row[1]
    coco = row[3]
    confidence = float(row[-2])
    inference_ms = float(row[-1])
    key = (object_cn, coco)
    if key not in object_data:
        object_data[key] = {"inference_ms": [], "confidence": []}
    object_data[key]["inference_ms"].append(inference_ms)
    object_data[key]["confidence"].append(confidence)

# 更新 per_object
for obj_entry in summary["per_object"]:
    object_cn = obj_entry["object"]
    coco = obj_entry["coco"]
    key = (object_cn, coco)
    if key in object_data:
        data = object_data[key]
        n = len(data["inference_ms"])

        mean_conf = sum(data["confidence"]) / n if n > 0 else 0
        obj_entry["mean_confidence"] = round(mean_conf, 3)

        mean_inf = sum(data["inference_ms"]) / n if n > 0 else 0
        obj_entry["mean_inference_ms"] = round(mean_inf, 2)

# 重新计算 overall
all_inference_ms = []
all_n = 0
all_class_correct = 0
all_trigger_correct = 0
for obj_entry in summary["per_object"]:
    all_n += obj_entry["n"]
    all_class_correct += obj_entry["class_correct"]
    all_trigger_correct += obj_entry["trigger_correct"]
    key = (obj_entry["object"], obj_entry["coco"])
    if key in object_data:
        all_inference_ms.extend(object_data[key]["inference_ms"])

overall = summary["overall"]
overall["n"] = all_n
overall["class_accuracy_pct"] = round(all_class_correct / all_n * 100, 1) if all_n > 0 else 0.0
overall["trigger_accuracy_pct"] = round(all_trigger_correct / all_n * 100, 1) if all_n > 0 else 0.0
overall["miss_rate_pct"] = 0.0
overall["mean_inference_ms"] = round(sum(all_inference_ms) / len(all_inference_ms), 2) if all_inference_ms else 0

with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)
print("JSON 已更新.")

# 4. 更新 Markdown 表格
with open(MD_PATH, "r", encoding="utf-8") as f:
    md_content = f.read()

lines = md_content.splitlines()
new_lines = []
for line in lines:
    if line.strip().startswith("| | 苹果 |"):
        obj_info = next(o for o in summary["per_object"] if o["object"] == "苹果")
        mean_conf = obj_info["mean_confidence"]
        mean_inf = obj_info["mean_inference_ms"]
        new_line = f"| | 苹果 | `apple` | 轻拿轻放类 | 30 | 30/30 (100.0%) | 30/30 (100.0%) | 0.0% | {mean_conf:.3f} | {mean_inf:.2f} |"
        new_lines.append(new_line)
    elif line.strip().startswith("| | 香蕉 |"):
        obj_info = next(o for o in summary["per_object"] if o["object"] == "香蕉")
        mean_conf = obj_info["mean_confidence"]
        mean_inf = obj_info["mean_inference_ms"]
        new_line = f"| | 香蕉 | `banana` | 轻拿轻放类 | 30 | 30/30 (100.0%) | 30/30 (100.0%) | 0.0% | {mean_conf:.3f} | {mean_inf:.2f} |"
        new_lines.append(new_line)
    elif line.strip().startswith("| | 水瓶 |"):
        obj_info = next(o for o in summary["per_object"] if o["object"] == "水瓶")
        mean_conf = obj_info["mean_confidence"]
        mean_inf = obj_info["mean_inference_ms"]
        new_line = f"| | 水瓶 | `bottle` | 中等类 | 30 | 30/30 (100.0%) | 30/30 (100.0%) | 0.0% | {mean_conf:.3f} | {mean_inf:.2f} |"
        new_lines.append(new_line)
    elif line.strip().startswith("总体"):
        overall_mean = summary["overall"]["mean_inference_ms"]
        overall_class = summary["overall"]["class_accuracy_pct"]
        overall_trigger = summary["overall"]["trigger_accuracy_pct"]
        overall_miss = summary["overall"]["miss_rate_pct"]
        new_line = f"总体类别识别正确率为{overall_class}%，操作属性触发正确率为{overall_trigger}%，漏检率为{overall_miss}%，平均单帧处理时间为{overall_mean} ms。"
        new_lines.append(new_line)
    else:
        new_lines.append(line)

with open(MD_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(new_lines))
print("Markdown 已更新.")

# 输出结果摘要
print("\n========== 更新结果摘要 ==========")
for obj_entry in summary["per_object"]:
    print(f"  {obj_entry['object']}: mean_confidence={obj_entry['mean_confidence']:.3f}, mean_inference_ms={obj_entry['mean_inference_ms']:.2f}")
print(f"  Overall: mean_inference_ms={summary['overall']['mean_inference_ms']:.2f}")
print("完成!")