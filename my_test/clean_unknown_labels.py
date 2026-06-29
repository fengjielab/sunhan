#!/usr/bin/env python3
"""
修复被损坏的 CSV 文件（所有行合并成一行），然后删除 vision_label 列。
损坏原因：Set-Content -NoNewline 将多行合并成了一行，
导致每行的最后一个字段和下一行的第一个字段粘在一起。

修复策略：
  1. 读取所有逗号分隔的值
  2. 识别出合并的边界（如 "vision_label0.0019" → "vision_label" + "0.0019"）
  3. 按每行 16 列重组
  4. 删除 vision_label 列
"""
import os, csv, json, re

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# 已知的 16 列 header
HEADER = [
    "time", "x", "y", "z", "gripper_deg", "button",
    "K_trans", "K_rot", "damping_ratio", "K_fb", "deadband", "scale",
    "F_ext_mag", "fusion_delta_K", "fusion_active", "vision_label"
]
NCOLS = len(HEADER)

# vision_label 的可能取值
LABELS = {"vision_label", "unknown", "soft", "medium", "hard"}

csv_fixed = 0
csv_no_vision = 0
json_cleaned = 0

for root, dirs, files in os.walk(DATA_DIR):
    for fname in files:
        fpath = os.path.join(root, fname)

        # ══════════════════════════════════════
        # CSV 修复 + 删除 vision_label 列
        # ══════════════════════════════════════
        if fname.endswith(".csv"):
            raw = open(fpath, "rb").read()

            # 检测编码
            for enc in ["utf-8-sig", "utf-16-le", "utf-8"]:
                try:
                    text = raw.decode(enc)
                    break
                except (UnicodeDecodeError,):
                    continue
            else:
                text = raw.decode("utf-8", errors="replace")

            values = text.strip().split(",")

            # 检查是否包含 "vision_label" 字段
            # 可能是精确匹配或与下一行第一个值合并（如 "vision_label0.0019"）
            has_vision = any("vision_label" in v for v in values)
            if not has_vision:
                continue  # 没有 vision_label，跳过

            # 获取原始行数，尝试修复合并的边界
            # 原始结构: 1 header + N data rows, 每行 16 列
            # 合并后: 第 i 行末列与第 i+1 行首列粘合
            # pattern: "unknown0.0069", "vision_label0.0019", "soft0.0123" 等

            repaired = []
            i = 0
            values_len = len(values)
            row_count = 0

            while i < values_len:
                # 尝试按照 16 列取一行
                if i + NCOLS <= values_len:
                    row = values[i:i + NCOLS]
                    last = row[-1]
                    # 检查最后一列是否和下一行的第一列合并了
                    # 合并特征: last 以已知 label 开头，后面跟着数字
                    for label in sorted(LABELS, key=len, reverse=True):
                        if last.startswith(label):
                            rest = last[len(label):]
                            if rest and (rest[0].isdigit() or rest[0] == '-' or rest[0] == '.'):
                                # 合并了！拆开
                                row[-1] = label
                                # 把 rest 插入到下一行的开始
                                values.insert(i + NCOLS, rest)
                                values_len += 1
                                break
                    repaired.append(row)
                    i += NCOLS
                else:
                    # 剩余值不够一行，忽略
                    break

            if not repaired:
                continue

            # 验证 header
            header = repaired[0]
            try:
                vidx = header.index("vision_label")
            except ValueError:
                continue  # header 中无 vision_label

            # 删除 vision_label 列
            for row in repaired:
                if len(row) > vidx:
                    del row[vidx]

            # 写回
            with open(fpath, "w", encoding="utf-8", newline="") as f:
                csv.writer(f).writerows(repaired)
            csv_fixed += 1
            print(f"  CSV: {fpath} ({len(repaired)-1} data rows)")

        # ══════════════════════════════════════
        # JSON 清理 vision_label
        # ══════════════════════════════════════
        elif fname.endswith(".json"):
            with open(fpath, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            mode = data.get("mode")
            if mode and "vision_label" in mode:
                del mode["vision_label"]
                json_cleaned += 1
                with open(fpath, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    f.write("\n")
                print(f"  JSON: {fpath}")

print(f"\nCSV 修复并删除 vision_label 列: {csv_fixed}")
print(f"JSON 删除 vision_label 字段: {json_cleaned}")
