#!/usr/bin/env python3
"""undo_episode.py —— 把某一条录错的 episode 从“已完成”中安全退回。

背景：每条正式数据由 3 部分组成，断点续采只认 episode_summary.csv：
  - output/episode_summary.csv 中的一行
  - output/videos/<episode_id>.mp4
  - output/detections/<episode_id>.jsonl

本工具做“可逆回退”，不真删数据：
  1. 把 videos/ 与 detections/ 下该 episode 的数据文件【移动】到
     output/_undo_<episode_id>_<时间戳>/ 备份目录；
  2. 把该行从 episode_summary.csv 中移除（其余行顺序不变）；
  3. 被移除的原始行会存到备份目录 removed_rows.csv，便于日后核对。

回退后，重跑 environment_runner.py 会自动把它当作“唯一未完成的条目”补录。

用法：
  python3 undo_episode.py OCC_SCISSORS_R05                     # 正式执行前会要求输入全名确认
  python3 undo_episode.py OCC_SCISSORS_R05 --yes              # 跳过交互确认
  python3 undo_episode.py OCC_SCISSORS_R05 --dry-run          # 只预览要做什么
  python3 undo_episode.py OCC_SCISSORS_R05 --output <数据目录>
"""

import argparse
import csv
import datetime
import shutil
import sys
from pathlib import Path

DEFAULT_OUTPUT = Path("/home/mfj/sunhan/vision_robustness_data")


def read_rows(summary_path: Path):
    """读取 summary，返回 (fieldnames, rows)。行与表头顺序完全保留。"""
    with summary_path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames, list(reader)


def write_rows(summary_path: Path, fieldnames, rows) -> None:
    """原子写回 summary（保持表头 BOM 与列顺序）。"""
    tmp = summary_path.with_name(summary_path.name + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    tmp.replace(summary_path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("episode_id", help="要退回的 episode_id，例如 OCC_SCISSORS_R05")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--dry-run", action="store_true", help="只打印将执行的动作，不改动任何文件")
    parser.add_argument("--yes", action="store_true", help="跳过全名输入确认（数据只移动不删除，仍可恢复）")
    args = parser.parse_args()

    target = args.episode_id.strip()
    summary_path = args.output / "episode_summary.csv"
    if not summary_path.exists():
        print(f"找不到 summary：{summary_path}", file=sys.stderr)
        return 2

    fieldnames, rows = read_rows(summary_path)
    if not fieldnames or "episode_id" not in fieldnames:
        print(f"summary 格式异常：缺少 episode_id 列：{summary_path}", file=sys.stderr)
        return 2

    removed = [row for row in rows if row.get("episode_id") == target]
    if not removed:
        print(f"summary 中没有找到 {target}（说明它尚未正式保存，无需回退）。", file=sys.stderr)
        return 3
    if len(removed) > 1:
        print(f"警告：summary 中存在 {len(removed)} 条 {target}，将一并移除。", file=sys.stderr)

    video_file = args.output / "videos" / f"{target}.mp4"
    detection_file = args.output / "detections" / f"{target}.jsonl"
    leftovers = sorted(
        list(args.output.glob(f"videos/{target}__tmp*"))
        + list(args.output.glob(f"detections/{target}__tmp*"))
    )
    present = [p for p in [video_file, detection_file] + leftovers if p.exists()]

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = args.output / f"_undo_{target}_{stamp}"

    print("=" * 72)
    print(f"目标 episode：{target}")
    print(f"  summary 行：{len(removed)} 条")
    print(f"  将移动的数据文件：")
    if present:
        for p in present:
            print(f"    -> {backup_dir.name}/{p.name}")
    else:
        print("    （无 —— videos/detections 中没有对应文件）")
    print(f"  备份目录：{backup_dir}")
    if not present and not leftovers:
        print("  注意：数据文件缺失，仅会移除 summary 行。")

    if args.dry_run:
        print("\n[dry-run] 以上为预览，未做任何改动。")
        return 0

    if not args.yes:
        answer = input(f"确认退回 {target}？输入完整 episode_id 以确认： ").strip()
        if answer != target:
            print("输入不一致，已取消，未做任何改动。", file=sys.stderr)
            return 4

    backup_dir.mkdir(parents=True, exist_ok=True)
    for p in present:
        shutil.move(str(p), str(backup_dir / p.name))
        print(f"  moved  {p.relative_to(args.output)}")

    # 把被移除的原始行备份到 removed_rows.csv，便于日后核对。
    with (backup_dir / "removed_rows.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in removed:
            writer.writerow(row)

    remaining = [row for row in rows if row.get("episode_id") != target]
    write_rows(summary_path, fieldnames, remaining)

    print("-" * 72)
    print(f"完成：{target} 已从已完成集合退回。")
    print(f"  剩余记录数：{len(remaining)}（原 {len(rows)}）")
    print(f"  备份目录（确认新数据无误前请保留）：{backup_dir}")
    print("下一步：退出所有采集程序后，重跑 environment_runner.py 即可只补录这一条。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
