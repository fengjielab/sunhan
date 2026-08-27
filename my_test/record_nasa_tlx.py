#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
record_nasa_tlx.py — NASA-TLX 问卷交互式录入工具
=================================================

用法:
    python3 my_test/record_nasa_tlx.py

录入后数据保存到: my_test/nasa_tlx_data.json
供 plans/experiment_analysis.py 读取生成图表

NASA-TLX 六个维度 (Raw TLX, 0-20):
  1. 脑力需求 (Mental Demand)     — 思考/决策/记忆的要求
  2. 体力需求 (Physical Demand)   — 推拉/操作/移动的要求
  3. 时间需求 (Temporal Demand)   — 任务节奏紧迫感
  4. 努力程度 (Effort)            — 完成任务需要多努力
  5. 任务表现 (Performance)       — 自己认为完成得多好 (0=完美, 20=失败)
  6. 挫败感 (Frustration)         — 操作中的烦躁/压力程度
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# 模式名称映射
MODES = {
    "default": "模式A-传统(default)",
    "hard_obj": "模式B-硬物体(hard_obj)",
    "vision": "模式C-视觉(vision)",
    "vision_observe": "模式D-视觉观察(vision_observe)",
    "a": "模式A-传统",
    "b": "模式B-固定增益",
    "c": "模式C-本文方法",
}

TLX_DIMS = [
    ("脑力需求 (Mental Demand)", "任务对脑力/知觉/思考/决策的要求有多高？"),
    ("体力需求 (Physical Demand)", "任务对体力/推拉/移动/操作的要求有多高？"),
    ("时间需求 (Temporal Demand)", "任务的节奏是快是慢？是否感到时间紧迫？"),
    ("努力程度 (Effort)", "完成任务需要付出多大努力？"),
    ("任务表现 (Performance)", "您认为自己完成得有多好？(0=完美, 20=完全失败)"),
    ("挫败感 (Frustration)", "操作中感到烦躁/压抑/紧张的程度？"),
]


def input_score(dim_name: str, hint: str, default: float = 10.0) -> float:
    """交互式输入单个维度评分 (0-20)"""
    while True:
        try:
            raw = input(f"  [{dim_name}]\n    {hint}\n    评分 (0-20) [{default}]: ").strip()
            if raw == "":
                return default
            val = float(raw)
            if 0 <= val <= 20:
                return val
            print("    ❌ 请输入 0-20 之间的数值")
        except ValueError:
            print("    ❌ 请输入有效数字")


def main():
    print("=" * 60)
    print("  📋 NASA-TLX 任务负荷指数 — 交互式录入")
    print("=" * 60)
    print()
    print("  请为每种模式填写 Raw TLX 六个维度评分 (0-20)")
    print()

    # ── 操作员信息 ──
    operator = input("操作员编号 (1/2/3): ").strip()
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    print()
    print("=" * 60)
    print("  请依次录入每种模式的评分")
    print("  直接回车使用括号内的默认值")
    print("=" * 60)

    all_data = {}

    for mode_key, mode_name in MODES.items():
        print(f"\n{'─' * 60}")
        print(f"  📝 {mode_name}")
        print(f"{'─' * 60}")

        scores = []
        for dim_name, hint in TLX_DIMS:
            default = 10.0 if dim_name != "任务表现 (Performance)" else 10.0
            score = input_score(dim_name, hint, default)
            scores.append(score)

        all_data[mode_key] = {
            "mode_name": mode_name,
            "scores": scores,
            "dims": [d[0] for d in TLX_DIMS],
            "raw_tlx_mean": sum(scores) / len(scores),
        }

        print(f"\n  ✅ {mode_name} 录入完成")
        print(f"     Raw TLX 均值: {all_data[mode_key]['raw_tlx_mean']:.1f}")

    # ── 保存 ──
    output_path = Path(__file__).resolve().parent / "nasa_tlx_data.json"
    output = {
        "operator": operator,
        "date": date_str,
        "note": "Raw TLX 评分 (0-20), 6维度: [脑力, 体力, 时间, 努力, 表现, 挫败]",
        "data": all_data,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f"  ✅ 所有数据已保存")
    print(f"     文件: {output_path}")
    print()
    print("  📊 评分汇总:")
    print(f"  {'模式':<20} {'均值':>6}  {'脑力':>5} {'体力':>5} {'时间':>5} {'努力':>5} {'表现':>5} {'挫败':>5}")
    print(f"  {'-'*56}")
    for mk, md in all_data.items():
        s = md["scores"]
        print(f"  {MODES.get(mk, mk):<20} {md['raw_tlx_mean']:>6.1f}  {s[0]:>5.0f} {s[1]:>5.0f} {s[2]:>5.0f} {s[3]:>5.0f} {s[4]:>5.0f} {s[5]:>5.0f}")

    print(f"\n{'=' * 60}")
    print(f"  后续步骤:")
    print(f"  1. 运行分析脚本生成图表:")
    print(f"     python3 plans/experiment_analysis.py \\")
    print(f"       my_test/hard_date/ --tlx-data my_test/nasa_tlx_data.json")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
