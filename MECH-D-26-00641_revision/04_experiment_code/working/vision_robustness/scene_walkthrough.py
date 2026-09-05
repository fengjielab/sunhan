#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""逐条场景检查向导（vision_robustness scene walkthrough / checklist）。

读取同目录的 scene_manifest.csv（120 条场景任务），在终端一次显示一条：
现场摆放完成后按【回车】确认 -> 记录进度 -> 自动跳到下一条。

本脚本只读 CSV、不连接相机、不运行 YOLO、不录像，用于在现场逐条核对
摆放并记录进度。进度默认保存到同目录 scene_walkthrough_done.csv，
按 Q 随时退出，下次运行时自动跳过已完成条目、从断点继续。

用法示例：
    python3 scene_walkthrough.py                        # 全部 120 条
    python3 scene_walkthrough.py --condition normal     # 只走 normal 的 15 条
    python3 scene_walkthrough.py --condition occlusion50 --start 50
    python3 scene_walkthrough.py --list                 # 只打印任务表
"""

from __future__ import annotations

import argparse
import csv
import sys
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence

CONDITIONS = [
    "normal",
    "dim",
    "backlight",
    "occlusion50",
    "clutter",
    "multiobject",
    "new_instance",
    "unknown",
]

CONDITION_ZH = {
    "normal": "正常光照",
    "dim": "弱光",
    "backlight": "背光",
    "occlusion50": "约50%遮挡",
    "clutter": "固定杂物",
    "multiobject": "两个已知物体",
    "new_instance": "同类别新实物",
    "unknown": "未知物体",
}

OBJECT_ZH = {
    "banana": "香蕉",
    "bottle": "瓶子",
    "scissors": "剪刀",
    "stapler": "订书机",
    "screwdriver": "螺丝刀",
    "tape measure": "卷尺",
    "cardboard box": "小纸盒",
    "sponge": "海绵",
}

STRATEGY_ZH = {
    "soft": "软质",
    "medium": "中硬",
    "hard": "硬质",
    "unknown": "未知",
}

POSITION_ZH = {
    1: "R01 · 中心",
    2: "R02 · 中心左侧 3 cm",
    3: "R03 · 中心右侧 3 cm",
    4: "R04 · 中心向相机方向 3 cm",
    5: "R05 · 中心远离相机方向 3 cm",
}

INSTANCE_ZH = {
    "A": "实物 A（原实验所用物品）",
    "B": "实物 B（与 A 同语义类别的另一件实物）",
}

STATE_FIELDS = ["episode_id", "sequence", "condition", "confirmed_at"]
WIDTH = 78
def condition_hint(row: Dict[str, str]) -> str:
    condition = row["condition"]
    rep = int(row["replicate"])
    target = row["object_name"]
    target_zh = OBJECT_ZH.get(target, target)
    if condition == "normal":
        return (
            f"只放本行指定的一个目标物（{target_zh}），放在中央目标区内指定位置，"
            "保持原实验朝向；正常实验室光照，画面内不要出现其他物体。"
        )
    if condition == "dim":
        return (
            f"目标物位置、朝向不变。关闭主灯或调暗照明，使物体表面约 50-100 lux；"
            "该组各轮保持相同弱光设置，确认前不要再调灯。"
        )
    if condition == "backlight":
        return (
            f"目标物位置、朝向不变。把台灯放在物体后方约 30-50 cm，灯大致朝向相机，"
            "让物体形成明显背光；台灯和灯架不能遮挡目标物。"
        )
    if condition == "occlusion50":
        side = "左侧" if rep % 2 == 1 else "右侧"
        return (
            f"用不反光的灰色/黑色遮挡卡遮住目标可见轮廓约一半；本轮 R{rep:02d} 为"
            f"{'奇数重复，遮挡卡放目标' if rep % 2 == 1 else '偶数重复，遮挡卡放目标'}{side}。"
            "遮挡卡在整个确认过程中不得移动。"
        )
    if condition == "clutter":
        return (
            f"目标（{target_zh}）放在中央目标区内指定位置；钥匙放目标左侧、胶带卷放"
            "右侧、直尺放后方，三件杂物都在目标区外且不遮挡目标。全程使用同一组杂物。"
        )
    if condition == "multiobject":
        distractor = row.get("distractor", "")
        distractor_zh = OBJECT_ZH.get(distractor, distractor) if distractor else "另一已知物体"
        side = "左侧" if rep % 2 == 1 else "右侧"
        return (
            f"目标（{target_zh}）放在中央目标区内 R{rep:02d} 位置；{distractor_zh}放"
            f"在目标{side} 12-15 cm，两个物体深度保持一致，互不遮挡。"
        )
    if condition == "new_instance":
        return (
            f"只放一个目标物，但必须使用同语义类别的 B 实物（{target_zh}B 仍须是"
            "同类真实物，不能换成别的类别）。位置和朝向按 R01-R05 执行。"
        )
    if condition == "unknown":
        return (
            f"只放本行指定的未知物体（{target_zh}）；未知物体只用 R01-R03（中心/左/右）。"
            "若后续被识别成已知类别也属于有效结果，不要因此重做。"
        )
    return "按现场操作说明布置。"


# --------------------------------------------------------------------------- #
# CSV / 进度文件读写
# --------------------------------------------------------------------------- #

def load_manifest(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        raise SystemExit(
            f"找不到任务清单：{path}\n"
            "请先运行：python3 offline_vision_capture.py --make-manifest-only"
        )
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def load_state(path: Path) -> Dict[str, Dict[str, str]]:
    """读取进度文件，返回 {episode_id: record}。"""
    records: Dict[str, Dict[str, str]] = {}
    if not path.exists():
        return records
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            if row.get("episode_id"):
                records[row["episode_id"]] = row
    return records


def save_state(path: Path, done: Dict[str, Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(done.values(), key=lambda r: int(r["sequence"]))
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=STATE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
        handle.flush()


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def mark_done(
    state_path: Path, done: Dict[str, Dict[str, str]], row: Dict[str, str]
) -> bool:
    """把某条记入进度；已存在则返回 False（不产生重复记录）。"""
    episode_id = row["episode_id"]
    if episode_id in done:
        return False
    done[episode_id] = {
        "episode_id": episode_id,
        "sequence": row["sequence"],
        "condition": row["condition"],
        "confirmed_at": now_text(),
    }
    save_state(state_path, done)
    return True


def unmark_done(
    state_path: Path, done: Dict[str, Dict[str, str]], episode_id: str
) -> bool:
    if episode_id not in done:
        return False
    del done[episode_id]
    save_state(state_path, done)
    return True


# --------------------------------------------------------------------------- #
# 显示
# --------------------------------------------------------------------------- #

def clear_screen() -> None:
    if sys.stdout.isatty():
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()


def wrap_block(text: str, width: int, indent: str) -> str:
    lines = textwrap.wrap(
        text, width=width, break_long_words=False, break_on_hyphens=False
    )
    return "\n".join(indent + line for line in lines) if lines else indent
def show_help() -> None:
    print("-" * WIDTH)
    print("  操作键说明：")
    print("    [回车] 确认本条摆放完成 -> 记进度并跳到下一条")
    print("    n      跳过本条（不标记）")
    print("    p      回看上一条")
    print("    d      撤销当前这一条的“已完成”标记（误按回车或想重做时用）")
    print("    j      跳到某条（输入全表序号或 Episode ID）")
    print("    q      保存进度并退出")
    print("    h      显示本帮助")
    print("-" * WIDTH)


def show_episode(
    row: Dict[str, str],
    idx: int,
    scope_count: int,
    done: Dict[str, Dict[str, str]],
    done_in_scope: int,
) -> None:
    episode_id = row["episode_id"]
    condition = row["condition"]
    target = row["object_name"]
    target_zh = OBJECT_ZH.get(target, target)
    strategy = row["expected_strategy"]
    strategy_zh = STRATEGY_ZH.get(strategy, strategy)
    rep = int(row["replicate"])
    position_zh = POSITION_ZH.get(rep, f"R{rep:02d}")
    instance = row.get("instance_id", "A")
    instruction = row["instruction"]

    print("=" * WIDTH)
    print(f"  第 {row['sequence']} 条 / 全表 · 本范围 {idx + 1}/{scope_count}")
    print(f"  本范围已完成 {done_in_scope}/{scope_count}"
          + ("    （本条已标记完成，重做请按 d 撤销）" if episode_id in done else ""))
    print("=" * WIDTH)
    print(f"  Episode   : {episode_id}")
    print(f"  条件      : {condition}（{CONDITION_ZH.get(condition, '')}）")
    print(f"  目标物体  : {target}（{target_zh}）  实例 {instance}："
          f"{INSTANCE_ZH.get(instance, '')}")
    print(f"  摆放位置  : {position_zh}")
    print(f"  刚度类别  : {strategy}（{strategy_zh}）")
    distractor = row.get("distractor", "")
    if distractor:
        print(f"  旁边物体  : {distractor}（{OBJECT_ZH.get(distractor, distractor)}）")
    print("  摆放说明  :")
    print(wrap_block(instruction, WIDTH - 14, "              "))
    print("-" * WIDTH)
    print("  [条件布置提示]")
    for line in textwrap.wrap(condition_hint(row), width=WIDTH - 4):
        print("    " + line)
    print("=" * WIDTH)
    print("  [回车] 确认完成并下一   [n]跳过   [p]上一条   [d]撤销完成标记")
    print("  [j]跳转   [q]保存退出   [h]帮助")
    print()
# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #

def choose_scope(
    manifest: Sequence[Dict[str, str]], condition: Optional[str]
) -> List[Dict[str, str]]:
    if condition is None:
        return list(manifest)
    return [row for row in manifest if row["condition"] == condition]


def find_index(pending: Sequence[Dict[str, str]], target: str) -> Optional[int]:
    target = target.strip().lower()
    for i, row in enumerate(pending):
        if row["episode_id"].lower() == target or str(row["sequence"]) == target:
            return i
    return None


def scope_label(condition: Optional[str]) -> str:
    if condition is None:
        return "全部 8 个条件 · 120 条"
    return f"{condition}（{CONDITION_ZH.get(condition, '')}）· 15 条"


def list_scope(pending: Sequence[Dict[str, str]], done: Dict[str, Dict[str, str]]) -> None:
    print(f"{'序号':<4} {'episode_id':<22} {'condition':<11} {'object_name':<13} "
          f"{'R':<3} {'实例':<3} 状态")
    print("-" * WIDTH)
    for row in pending:
        status = "完成" if row["episode_id"] in done else ""
        print(f"{row['sequence']:<4} {row['episode_id']:<22} {row['condition']:<11} "
              f"{row['object_name']:<13} R{row['replicate']:<2} "
              f"{row.get('instance_id', 'A'):<3} {status}")
    print("-" * WIDTH)
    done_in_scope = sum(1 for r in pending if r["episode_id"] in done)
    print(f"共 {len(pending)} 条，其中已标记完成 {done_in_scope} 条。")
def run_wizard(
    pending: Sequence[Dict[str, str]],
    done: Dict[str, Dict[str, str]],
    state_path: Path,
    start_index: int,
    no_clear: bool,
) -> int:
    pos = start_index
    newly_confirmed = 0
    first = True
    while pos < len(pending):
        row = pending[pos]
        done_in_scope = sum(1 for r in pending if r["episode_id"] in done)
        if not no_clear and not first:
            clear_screen()
        first = False
        show_episode(row, pos, len(pending), done, done_in_scope)

        while True:
            try:
                command = input("> ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                command = "q"
                print()
            if command in ("", "y", "yes", "ok", "完成", "确认"):
                added = mark_done(state_path, done, row)
                if added:
                    newly_confirmed += 1
                pos += 1
                break
            if command in ("n", "s", "skip", "next", "跳过"):
                pos += 1
                break
            if command in ("p", "b", "back", "prev", "上一条"):
                if pos == 0:
                    print("  已在第一条，没有上一条。")
                else:
                    pos -= 1
                break
            if command in ("d", "undo", "撤销"):
                if unmark_done(state_path, done, row["episode_id"]):
                    print(f"  已撤销 “{row['episode_id']}” 的完成标记，可重新确认。")
                else:
                    print("  当前条还没有“已完成”标记，无需撤销。")
                break
            if command in ("q", "quit", "exit", "x", "退出"):
                print()
                return 0
            if command in ("j", "jump", "跳转"):
                try:
                    target = input("  跳转到（全表序号或 Episode ID）: ").strip()
                except (EOFError, KeyboardInterrupt):
                    continue
                hit = find_index(pending, target)
                if hit is None:
                    print(f"  未找到：{target}")
                else:
                    pos = hit
                break
            if command in ("h", "help", "帮助"):
                show_help()
                continue
            print("  无法识别，输入 h 查看操作键说明。")

    done_in_scope = sum(1 for r in pending if r["episode_id"] in done)
    print()
    print("=" * WIDTH)
    if done_in_scope == len(pending):
        print(f"  本范围全部完成：{done_in_scope}/{len(pending)} 条。")
    else:
        print(f"  本范围已浏览完；已标记完成 {done_in_scope}/{len(pending)} 条。")
    print(f"  本次新确认 {newly_confirmed} 条；进度已保存到 {state_path}")
    print("=" * WIDTH)
    return 0
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="vision_robustness 逐条场景检查向导")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).with_name("scene_manifest.csv"),
        help="任务清单 CSV（默认与脚本同目录的 scene_manifest.csv）",
    )
    parser.add_argument(
        "--state",
        type=Path,
        default=Path(__file__).with_name("scene_walkthrough_done.csv"),
        help="进度记录文件（默认 scene_walkthrough_done.csv）",
    )
    parser.add_argument(
        "--condition",
        choices=CONDITIONS,
        help="只处理某一个条件（例如 normal / dim / unknown）",
    )
    parser.add_argument(
        "--start",
        default=None,
        help="从指定起点开始：全表序号（1-120）或 Episode ID，例如 50 或 OCC_BOTTLE_R01",
    )
    parser.add_argument("--list", action="store_true", help="只打印本次范围内的任务表后退出")
    parser.add_argument("--no-clear", action="store_true", help="切换场景时不清屏")
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (ValueError, OSError):
            pass

    args = parse_args()
    manifest = load_manifest(args.manifest)
    pending = choose_scope(manifest, args.condition)
    if not pending:
        print("本次范围内没有任务。")
        return 1

    done = load_state(args.state)

    if args.list:
        list_scope(pending, done)
        return 0

    # 起点：显式 --start 优先，否则自动跳到第一条未完成
    if args.start:
        hit = find_index(pending, args.start)
        if hit is None:
            print(f"未找到起点：{args.start}（不在本次范围内）")
            return 2
        start_index = hit
    else:
        start_index = 0
        while start_index < len(pending) and pending[start_index]["episode_id"] in done:
            start_index += 1

    if start_index >= len(pending):
        print(f"本次范围已全部完成（{len(pending)}/{len(pending)} 条）。")
        return 0

    done_in_scope = sum(1 for r in pending if r["episode_id"] in done)
    print("=" * WIDTH)
    print("  场景逐条检查向导（不连相机、不录像，仅逐条核对并记录进度）")
    print("=" * WIDTH)
    print(f"  任务清单 : {args.manifest.name}")
    print(f"  进度文件 : {args.state}")
    print(f"  本次范围 : {scope_label(args.condition)}，共 {len(pending)} 条")
    print(f"  已有进度 : 本范围内已完成 {done_in_scope} 条")
    print(f"  从第     : {pending[start_index]['sequence']} 条 "
          f"{pending[start_index]['episode_id']} 开始")
    print("            （自动跳过已标记完成的条目，按 q 可随时保存退出）")
    print()

    try:
        run_wizard(pending, done, args.state, start_index, args.no_clear)
    except KeyboardInterrupt:
        print("\n收到中断，进度已即时保存，重跑即可续采。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())





