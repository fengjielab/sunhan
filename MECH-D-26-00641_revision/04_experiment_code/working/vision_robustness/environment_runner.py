#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分环境正式采集驱动脚本（vision_robustness environment runner）。

本脚本不自己录像，只负责“调度 + 环境交接”：
  按 fixed 顺序（normal -> dim -> backlight -> occlusion50 -> clutter
  -> multiobject -> new_instance -> unknown）逐个环境调用同目录的
  offline_vision_capture.py 做正式采集（RealSense + YOLO，每轮录 10 秒）。

每次进入一个新环境之前，先大字打印该环境需要的现场改动清单，等操作员按
回车确认现场已改好，再启动该环境的采集。运行期间照旧使用原采集程序的
SPACE（开始录像）/ Y（接受保存）/ R（重做）/ Q（退出）。

同类连续录制：默认在同一光照（条件）内把同一物体（object_name）的条目排
在一起连续录制，减少操作员反复换物体；分组是稳定排序，组内保持
scene_manifest.csv 的相对顺序。如要严格按清单原伪随机顺序录，加
--manifest-order。

断点续采：读取 output/episode_summary.csv，已全部录完的环境自动跳过；
录到一半退出后重跑，会从该环境第一条未录的开始（分组序下不会漏/重录）。

用法示例：
    python3 environment_runner.py                                # 8 个环境从头到尾（同类连续）
    python3 environment_runner.py --only dim,backlight           # 只做指定环境
    python3 environment_runner.py --manifest-order               # 按清单原顺序录制
    python3 environment_runner.py --dry-run                      # 只打印流程与命令，不启动采集
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set

WIDTH = 78

# 环境执行顺序（与 scene_manifest.csv 的分块顺序一致）
ENV_ORDER = [
    "normal",
    "dim",
    "backlight",
    "occlusion50",
    "clutter",
    "multiobject",
    "new_instance",
    "unknown",
]

ENV_ZH = {
    "normal": "正常光照",
    "dim": "弱光",
    "backlight": "背光",
    "occlusion50": "约50%遮挡",
    "clutter": "固定杂物",
    "multiobject": "两个已知物体",
    "new_instance": "同类别新实物",
    "unknown": "未知物体",
}

ENV_SETUP = {
    "normal": [
        "恢复并保持正常实验室照明；中央目标区内只放指令指定的那 1 个目标物。",
        "使用原实验物品：香蕉 A / 瓶子 A / 剪刀 A（不要用 B）。",
        "每轮看清指令里的 R01-R05 位置再摆放，保持原实验朝向。",
    ],
    "dim": [
        "关闭主灯或把照明调暗，使物体表面约为 50-100 lux（无照度计时用手机 App 估）。",
        "画面内除目标物外不要有其他物体；物体朝向不要改变。",
        "本环境 15 轮期间保持相同的弱光设置，录完前不要再调灯。",
    ],
    "backlight": [
        "主灯恢复正常照明；把台灯放到目标物体后方约 30-50 cm。",
        "台灯灯头大致朝向相机，让目标形成明显背光；台灯和灯架不能遮挡目标。",
        "本环境 15 轮期间台灯位置固定，不要移动。",
    ],
    "occlusion50": [
        "撤掉台灯（若刚从背光过来），恢复正常照明。",
        "准备不反光的灰色/黑色遮挡卡。",
        "遮挡卡遮住目标可见轮廓约一半：奇数重复 R01/R03/R05 遮左侧，"
        "偶数重复 R02/R04 遮右侧（程序每条会提示）。",
        "录像期间遮挡卡不能移动。",
    ],
    "clutter": [
        "撤掉遮挡卡（若刚从 occlusion50 过来）。",
        "目标物放中央目标区内；钥匙放目标左侧、胶带卷放右侧、直尺放后方。",
        "三件杂物都在目标区外且不遮挡目标；全程使用同一组三件杂物。",
    ],
    "multiobject": [
        "撤掉三件杂物（若刚从 clutter 过来）。",
        "目标物放中央目标区 R01-R05 位置；另一个已知物体放目标左/右 12-15 cm，"
        "深度一致，程序每条会提示放哪个物体、放哪一侧。",
        "两个物体都不能互相遮挡。",
    ],
    "new_instance": [
        "撤掉旁边物体（若刚从 multiobject 过来），每组只放 1 个目标物。",
        "必须使用同语义类别的 B 实物：香蕉 B / 瓶子 B / 剪刀 B（仍是真实同类物）。",
        "位置和朝向按程序指令执行。",
    ],
    "unknown": [
        "把已知目标物（香蕉、瓶子、剪刀的 A/B 实物）全部收出画面。",
        "只放指令指定的未知物体：订书机、螺丝刀、卷尺、小纸盒、海绵（只用 R01-R03）。",
        "未知物被识别成已知类别也是有效结果，不要因此重做。",
    ],
}

GENERAL_NOTE = (
    "（相机、桌面 15cm 目标区和 R01-R05 标记全程不要移动；机械臂保持静止且不入画）"
)
# --------------------------------------------------------------------------- #
# CSV / 进度工具
# --------------------------------------------------------------------------- #

def load_manifest(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        raise SystemExit(
            f"找不到任务清单：{path}\n"
            "请先运行：python3 offline_vision_capture.py --make-manifest-only"
        )
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def completed_episode_ids(summary_path: Path) -> Set[str]:
    """读取正式采集的 episode_summary.csv，返回已接受保存的 episode_id 集合。"""
    if not summary_path.exists():
        return set()
    ids: Set[str] = set()
    with summary_path.open("r", newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            if row.get("episode_id"):
                ids.add(row["episode_id"])
    return ids


def env_rows(
    manifest: Sequence[Dict[str, str]], condition: str
) -> List[Dict[str, str]]:
    return [row for row in manifest if row["condition"] == condition]


def count_done(rows: Sequence[Dict[str, str]], completed: Set[str]) -> int:
    return sum(1 for r in rows if r["episode_id"] in completed)


# --------------------------------------------------------------------------- #
# 显示与交互
# --------------------------------------------------------------------------- #

def show_env_banner(
    env: str,
    seq_idx: int,
    seq_total: int,
    done: int,
    total: int,
    grouped: bool = True,
) -> None:
    zh = ENV_ZH.get(env, env)
    print()
    print("=" * WIDTH)
    print(f"  [环境交接 {seq_idx}/{seq_total}]  下一步环境：{env}（{zh}）")
    print(f"  该环境进度：已正式保存 {done}/{total} 条"
          + (f"，将自动从第 {done + 1} 条未录的继续" if done < total else ""))
    print("-" * WIDTH)
    print(f"  请把现场从上一个环境改成「{zh}」：")
    for step in ENV_SETUP[env]:
        print("    · " + step)
    print(f"  {GENERAL_NOTE}")
    if grouped:
        print("  同类连续：本光照内先录完同一物体（组内顺序同清单）再换下一物体，"
              "换物体时采集程序会打印 ▸ 提示。")
    print("-" * WIDTH)


def read_choice(prompt: str, accepts: Dict[str, str]) -> str:
    """读取一个单字符选择并返回归一化键。accepts: {输入字符: 返回动作}。"""
    while True:
        try:
            raw = input(prompt).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return "q"
        if raw in accepts:
            return accepts[raw]
        print("  无法识别，请重新输入。")

# --------------------------------------------------------------------------- #
# 调用正式采集程序
# --------------------------------------------------------------------------- #

def capture_script_path() -> Path:
    script = Path(__file__).resolve().parent / "offline_vision_capture.py"
    if not script.exists():
        raise SystemExit(
            f"找不到正式采集程序：{script}\n"
            "environment_runner.py 必须与 offline_vision_capture.py 放在同一目录。"
        )
    return script


def _disp_w(text: str) -> int:
    """按终端等宽字体计算显示宽度：中日韩全角字符按 2 计。"""
    import unicodedata
    return sum(
        2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
        for ch in text
    )


def _pad_zh(text: str, width: int = 12) -> str:
    """把中英文混排文本补齐到指定显示宽度（不足补空格）。"""
    pad = width - _disp_w(text)
    return text + " " * pad if pad > 0 else text


def build_command(args: argparse.Namespace, condition: str) -> List[str]:
    cmd = [
        sys.executable,
        str(capture_script_path()),
        "--model",
        str(args.model),
        "--output",
        str(args.output),
        "--condition",
        condition,
    ]
    if getattr(args, "allow_model_mismatch", False):
        cmd.append("--allow-model-mismatch")
    if not getattr(args, "manifest_order", False):
        cmd.append("--group-by-object")
    return cmd


def run_capture(args: argparse.Namespace, condition: str) -> int:
    cmd = build_command(args, condition)
    print()
    print("-" * WIDTH)
    print(f"  正在启动「{condition}（{ENV_ZH.get(condition, condition)}）」环境的正式采集")
    print(f"  命令：python3 offline_vision_capture.py --condition {condition}")
    print(f"  画面里操作照旧：按空格开始录像，录完按 Y 保存 / R 重做 / Q 退出")
    print("-" * WIDTH)
    print()
    result = subprocess.run(cmd)
    return result.returncode


def show_summary(
    env_map: Dict[str, List[Dict[str, str]]],
    completed: Set[str],
    output: Path,
) -> None:
    total = 0
    done_total = 0
    print()
    print("=" * WIDTH)
    print("  本次运行结束，各环境进度汇总：")
    print("-" * WIDTH)
    for env in ENV_ORDER:
        rows = env_map.get(env, [])
        done = count_done(rows, completed)
        total += len(rows)
        done_total += done
        mark = " 完成" if done == len(rows) and rows else ""
        flag = "✔" if done == len(rows) and rows else " "
        zh = _pad_zh(ENV_ZH.get(env, ""), 12)
        print(f"    {env:<14} {zh} {done:>2}/{len(rows):<2} {mark}{flag}")
    print("-" * WIDTH)
    print(f"    总计：已正式保存 {done_total}/{total} 条")
    if done_total < total:
        print("    还有未完成的环境：重跑本脚本会自动从它们继续，已保存的数据不会丢。")
    print(f"    正式数据目录：{output}（记录保存在 {output / 'episode_summary.csv'}）")
    print("=" * WIDTH)

# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #

def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    # 与 offline_vision_capture.py 的默认值保持一致：
    # 模型默认取 offline_vision_capture.py 同款
    # /home/mfj/sunhan/yolo/ultralytics-8.3.163/yolo11n.pt（能通过哈希校验）
    default_output = Path("/home/mfj/sunhan/vision_robustness_data")
    default_model = Path(
        "/home/mfj/sunhan/yolo/ultralytics-8.3.163/yolo11n.pt"
    )
    default_manifest = Path(__file__).resolve().parent / "scene_manifest.csv"

    parser = argparse.ArgumentParser(
        description="分环境正式采集驱动：按 8 个环境顺序调度 offline_vision_capture.py，"
                    "环境交接时打印现场改动清单并等确认。"
    )
    parser.add_argument("--model", type=Path, default=default_model,
                        help="YOLO 模型权重路径（默认与采集程序一致）")
    parser.add_argument("--output", type=Path, default=default_output,
                        help="正式数据输出目录（默认 %(default)s）")
    parser.add_argument("--manifest", type=Path, default=default_manifest,
                        help="任务清单 CSV（默认 %(default)s）")
    parser.add_argument("--only", type=str, default=None,
                        help="只做这些环境，逗号分隔，例如 dim,backlight")
    parser.add_argument("--allow-model-mismatch", action="store_true",
                        help="透传给采集程序：容忍模型哈希校验不一致")
    parser.add_argument("--manifest-order", action="store_true",
                        help="不按物体分组，保持 scene_manifest.csv 的清单原顺序录制"
                             "（默认：同一光照内同类物体连续录制，类内保持清单相对顺序）")
    parser.add_argument("--dry-run", action="store_true",
                        help="只打印每个环境的改动清单和将要执行的命令，不启动采集")
    return parser.parse_args(argv)


def resolve_only(args: argparse.Namespace) -> Set[str]:
    if not args.only:
        return set(ENV_ORDER)
    names = {part.strip() for part in args.only.split(",") if part.strip()}
    bad = names - set(ENV_ORDER)
    if bad:
        raise SystemExit(
            f"无法识别的环境名：{', '.join(sorted(bad))}\n"
            f"可选：{', '.join(ENV_ORDER)}"
        )
    return names


def dry_run_flow(args: argparse.Namespace) -> int:
    manifest = load_manifest(args.manifest)
    env_map: Dict[str, List[Dict[str, str]]] = {
        env: env_rows(manifest, env) for env in ENV_ORDER
    }
    completed = completed_episode_ids(args.output / "episode_summary.csv")
    want = resolve_only(args)
    pending = [
        env for env in ENV_ORDER if env in want
        and count_done(env_map[env], completed) < len(env_map[env])
    ]
    if not pending:
        print("所有目标环境都已录完，无需动作。")
        show_summary(env_map, completed, args.output)
        return 0
    for i, env in enumerate(pending, start=1):
        show_env_banner(env, i, len(pending),
                        count_done(env_map[env], completed), len(env_map[env]),
                        grouped=not args.manifest_order)
        shown = " ".join(str(part) for part in build_command(args, env))
        print("  [dry-run] 将执行：")
        print(f"    {shown}")
    print()
    print("  [dry-run] 以上为预演输出，未启动任何采集。")
    show_summary(env_map, completed, args.output)
    return 0

def run_flow(args: argparse.Namespace) -> int:
    manifest = load_manifest(args.manifest)
    env_map: Dict[str, List[Dict[str, str]]] = {
        env: env_rows(manifest, env) for env in ENV_ORDER
    }
    summary_path = args.output / "episode_summary.csv"
    want = resolve_only(args)
    targets = [env for env in ENV_ORDER if env in want]

    completed = completed_episode_ids(summary_path)
    done_envs = sum(
        1 for env in targets
        if env_map[env]
        and count_done(env_map[env], completed) == len(env_map[env])
    )
    if done_envs:
        print(f"  [跳过] 已全部录完的环境：{done_envs} 个，无需重复采集。")

    pending_envs = [env for env in targets if
                    count_done(env_map[env], completed) < len(env_map[env])]
    if not pending_envs:
        show_summary(env_map, completed, args.output)
        return 0
    print(f"  本次将处理 {len(pending_envs)} 个未完成环境。\n")

    quit_all = False
    for seq_idx, env in enumerate(pending_envs, start=1):
        rows = env_map[env]
        first_entry = True
        while True:
            if first_entry:
                done = count_done(rows, completed)
                show_env_banner(env, seq_idx, len(pending_envs), done, len(rows),
                                grouped=not args.manifest_order)
                print(f"  现场已按上面改成「{ENV_ZH.get(env, env)}」后："
                      "[回车] 开始本环境采集   [s] 跳过本环境   [q] 退出")
                action = read_choice("  > ", {
                    "": "start", "y": "start", "yes": "start",
                    "s": "skip", "n": "skip",
                    "q": "quit", "exit": "quit",
                })
                if action == "quit":
                    quit_all = True
                    break
                if action == "skip":
                    print(f"  [跳过] {env}（{ENV_ZH.get(env, env)}）本次不录。")
                    break
                first_entry = False

            rc = run_capture(args, env)
            if rc != 0:
                print()
                print("!" * WIDTH)
                print(f"  采集程序异常退出（返回码 {rc}）。已停止，请先解决问题再重跑。")
                print("  常见原因：模型文件不存在 / 模型哈希校验不一致（可加")
                print("  --allow-model-mismatch）/ RealSense 相机未连接 / 依赖缺失。")
                print("!" * WIDTH)
                completed = completed_episode_ids(summary_path)
                show_summary(env_map, completed, args.output)
                return rc

            completed = completed_episode_ids(summary_path)
            done = count_done(rows, completed)
            if done == len(rows):
                print()
                print(f"  ✔ 环境 {env}（{ENV_ZH.get(env, env)}）"
                      f"已全部录完 {done}/{len(rows)} 条。")
                break

            print()
            print("-" * WIDTH)
            print(f"  环境 {env}（{ENV_ZH.get(env, env)}）还剩 {len(rows) - done} 条未正式保存"
                  f"（已保存 {done}/{len(rows)}）。")
            print("  [r] 继续录本环境   [n] 跳到下一个环境   [q] 退出")
            again = read_choice("  > ", {
                "r": "rerun", "": "rerun", "y": "rerun",
                "n": "next", "s": "next", "skip": "next",
                "q": "quit", "exit": "quit",
            })
            if again == "rerun":
                continue  # 环境未变，直接再次启动采集，不再弹横幅
            if again == "next":
                break
            quit_all = True
            break
        if quit_all:
            break

    completed = completed_episode_ids(summary_path)
    show_summary(env_map, completed, args.output)
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    args.output = Path(args.output).expanduser().resolve()
    args.manifest = Path(args.manifest).expanduser().resolve()
    args.model = Path(args.model).expanduser().resolve()
    if not args.manifest.exists():
        raise SystemExit(f"找不到任务清单：{args.manifest}")
    if args.dry_run:
        return dry_run_flow(args)
    return run_flow(args)


if __name__ == "__main__":
    sys.exit(main())

