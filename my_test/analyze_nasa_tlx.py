"""Validate and summarize the 36-condition Raw NASA-TLX dataset.

The script never imputes missing values. It only produces outputs after all
3 operators x 3 object classes x 4 modes have valid six-dimension ratings.
"""

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev


DIMENSIONS = (
    "mental_demand",
    "physical_demand",
    "temporal_demand",
    "performance",
    "effort",
    "frustration",
)
DIMENSION_ZH = {
    "mental_demand": "心理需求",
    "physical_demand": "体力需求",
    "temporal_demand": "时间需求",
    "performance": "绩效",
    "effort": "努力程度",
    "frustration": "挫折程度",
}
OPERATORS = {"1", "2", "3"}
OBJECTS = {"soft", "medium", "hard"}
MODES = {"A", "B", "C", "D"}


def parse_args() -> argparse.Namespace:
    base = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Raw NASA-TLX 数据校验、汇总与绘图")
    parser.add_argument(
        "--input", type=Path, default=base / "data" / "nasa_tlx_data.csv"
    )
    parser.add_argument(
        "--output-dir", type=Path, default=base / "data" / "nasa_tlx_results"
    )
    return parser.parse_args()


def load_and_validate(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        raise ValueError(f"数据文件不存在：{path}")

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"operator", "object_class", "mode", *DIMENSIONS}
        missing_columns = required.difference(reader.fieldnames or [])
        if missing_columns:
            raise ValueError(f"缺少列：{', '.join(sorted(missing_columns))}")
        source_rows = list(reader)

    errors: list[str] = []
    rows: list[dict[str, object]] = []
    seen: set[tuple[str, str, str]] = set()
    expected = {(o, obj, mode) for o in OPERATORS for obj in OBJECTS for mode in MODES}

    for line_number, source in enumerate(source_rows, start=2):
        operator = source["operator"].strip()
        object_class = source["object_class"].strip().lower()
        mode = source["mode"].strip().upper()
        key = (operator, object_class, mode)

        if operator not in OPERATORS:
            errors.append(f"第{line_number}行 operator 应为1、2或3")
        if object_class not in OBJECTS:
            errors.append(f"第{line_number}行 object_class 应为soft、medium或hard")
        if mode not in MODES:
            errors.append(f"第{line_number}行 mode 应为A、B、C或D")
        if key in seen:
            errors.append(f"第{line_number}行条件重复：{key}")
        seen.add(key)

        row: dict[str, object] = {
            "operator": operator,
            "object_class": object_class,
            "mode": mode,
        }
        ratings: list[float] = []
        missing_ratings: list[str] = []
        for dimension in DIMENSIONS:
            raw = source[dimension].strip()
            if raw == "":
                missing_ratings.append(dimension)
                continue
            try:
                value = float(raw)
            except ValueError:
                errors.append(f"第{line_number}行 {dimension} 不是数值：{raw}")
                continue
            if not 0 <= value <= 100:
                errors.append(f"第{line_number}行 {dimension} 超出0～100：{value:g}")
            if not math.isclose(value % 5, 0.0, abs_tol=1e-9):
                errors.append(f"第{line_number}行 {dimension} 不是5的倍数：{value:g}")
            row[dimension] = value
            ratings.append(value)
        if missing_ratings:
            errors.append(
                f"第{line_number}行缺少评分：{', '.join(missing_ratings)}"
            )
        if len(ratings) == len(DIMENSIONS):
            row["raw_tlx"] = mean(ratings)
        rows.append(row)

    missing_conditions = expected.difference(seen)
    extra_conditions = seen.difference(expected)
    if len(source_rows) != 36:
        errors.append(f"应有36条记录，实际为{len(source_rows)}条")
    if missing_conditions:
        errors.append(f"缺少条件：{sorted(missing_conditions)}")
    if extra_conditions:
        errors.append(f"存在无效条件：{sorted(extra_conditions)}")
    if errors:
        raise ValueError("数据校验未通过，不生成结果：\n- " + "\n- ".join(errors))
    return rows


def sample_sd(values: list[float]) -> float:
    return stdev(values) if len(values) > 1 else 0.0


def summarize(rows: list[dict[str, object]], group_fields: tuple[str, ...]):
    groups: dict[tuple[str, ...], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        key = tuple(str(row[field]) for field in group_fields)
        groups[key].append(row)

    output: list[dict[str, object]] = []
    for key in sorted(groups):
        group = groups[key]
        record: dict[str, object] = dict(zip(group_fields, key))
        record["n_records"] = len(group)
        record["n_operators"] = len({str(item["operator"]) for item in group})
        for metric in (*DIMENSIONS, "raw_tlx"):
            values = [float(item[metric]) for item in group]
            record[f"{metric}_mean"] = mean(values)
            record[f"{metric}_sd"] = sample_sd(values)
        output.append(record)
    return output


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {key: f"{value:.2f}" if isinstance(value, float) else value for key, value in row.items()}
            )


def write_markdown(path: Path, mode_summary: list[dict[str, object]]) -> None:
    lines = [
        "| 模式 | 心理需求 | 体力需求 | 时间需求 | 绩效 | 努力程度 | 挫折程度 | Raw TLX |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in mode_summary:
        cells = [str(row["mode"])]
        for metric in (*DIMENSIONS, "raw_tlx"):
            cells.append(f'{row[f"{metric}_mean"]:.2f}±{row[f"{metric}_sd"]:.2f}')
        lines.append("| " + " | ".join(cells) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_plots(output_dir: Path, mode_summary: list[dict[str, object]]) -> None:
    try:
        import matplotlib.pyplot as plt
        import numpy as np
        from matplotlib.font_manager import FontProperties
    except ImportError as exc:
        raise RuntimeError("绘图需要 matplotlib 和 numpy；统计CSV已生成。") from exc

    chinese_font = FontProperties(fname=r"C:\Windows\Fonts\msyh.ttc")
    labels = [DIMENSION_ZH[item] for item in DIMENSIONS]
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    closed_angles = angles + angles[:1]
    fig, ax = plt.subplots(figsize=(7.2, 6.2), subplot_kw={"polar": True})
    for row in mode_summary:
        values = [float(row[f"{item}_mean"]) for item in DIMENSIONS]
        ax.plot(closed_angles, values + values[:1], linewidth=1.8, label=str(row["mode"]))
    ax.set_xticks(angles, labels, fontproperties=chinese_font)
    ax.set_ylim(0, 100)
    ax.set_title("不同模式的Raw NASA-TLX六维评分", fontproperties=chinese_font)
    ax.legend(loc="upper right", bbox_to_anchor=(1.2, 1.12))
    fig.tight_layout()
    fig.savefig(output_dir / "nasa_tlx_radar.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    modes = [str(row["mode"]) for row in mode_summary]
    means = [float(row["raw_tlx_mean"]) for row in mode_summary]
    sds = [float(row["raw_tlx_sd"]) for row in mode_summary]
    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    ax.bar(modes, means, yerr=sds, capsize=4, color="#4C78A8")
    ax.set_xlabel("模式", fontproperties=chinese_font)
    ax.set_ylabel("Raw TLX（0～100）", fontproperties=chinese_font)
    ax.set_ylim(0, 100)
    ax.set_title("不同模式的Raw NASA-TLX综合负荷", fontproperties=chinese_font)
    fig.tight_layout()
    fig.savefig(output_dir / "nasa_tlx_raw_score.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    rows = load_and_validate(args.input)
    mode_summary = summarize(rows, ("mode",))
    object_mode_summary = summarize(rows, ("object_class", "mode"))
    write_csv(args.output_dir / "nasa_tlx_by_mode.csv", mode_summary)
    write_csv(args.output_dir / "nasa_tlx_by_object_and_mode.csv", object_mode_summary)
    write_markdown(args.output_dir / "paper_table_8.md", mode_summary)
    make_plots(args.output_dir, mode_summary)
    print(f"校验通过：36条记录；结果已写入 {args.output_dir}")
    print("注意：3名操作者的重复测量仅作描述性统计，不可视为36个独立样本。")


if __name__ == "__main__":
    main()
