#!/usr/bin/env python3
"""六类实验对象的视觉识别与操作属性触发验证。

采集示例（每个对象重复执行一次）：
  python3 my_test/validate_vision_recognition.py capture --object apple --output data/vision_validation

离线评价：
  python3 my_test/validate_vision_recognition.py evaluate \
    --dataset data/vision_validation \
    --model yolo/ultralytics-8.3.163/yolo11n.pt
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import time
from collections import defaultdict
from pathlib import Path


OBJECTS = {
    "apple": {"display": "苹果", "coco": "apple", "property": "轻拿轻放类"},
    "banana": {"display": "香蕉", "coco": "banana", "property": "轻拿轻放类"},
    "bottle": {"display": "水瓶", "coco": "bottle", "property": "中等类"},
    "cup": {"display": "硬纸杯", "coco": "cup", "property": "中等类"},
    "mouse": {"display": "鼠标", "coco": "mouse", "property": "硬质类"},
    "scissors": {"display": "剪刀", "coco": "scissors", "property": "硬质类"},
}

COCO_TO_PROPERTY = {
    "apple": "轻拿轻放类",
    "banana": "轻拿轻放类",
    "bottle": "中等类",
    "cup": "中等类",
    "mouse": "硬质类",
    "scissors": "硬质类",
}
DEFAULT_PROPERTY = "中等类"


def capture(args: argparse.Namespace) -> None:
    try:
        import cv2
        import pyrealsense2 as rs
    except ImportError as exc:
        raise SystemExit(f"采集需要 opencv-python 和 pyrealsense2：{exc}")

    target = Path(args.output) / args.object
    target.mkdir(parents=True, exist_ok=True)
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.color, args.width, args.height, rs.format.bgr8, 30)
    pipeline.start(config)

    print(f"对象：{OBJECTS[args.object]['display']}；目标采集 {args.frames} 帧")
    print("请依次改变3种摆放姿态；按空格保存，按q退出。")
    saved = len(list(target.glob("*.jpg")))
    try:
        while saved < args.frames:
            frames = pipeline.wait_for_frames()
            color = frames.get_color_frame()
            if not color:
                continue
            import numpy as np

            image = np.asanyarray(color.get_data())
            preview = image.copy()
            cv2.putText(
                preview,
                f"{args.object}: {saved}/{args.frames}  SPACE=save  q=quit",
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2,
            )
            cv2.imshow("vision validation capture", preview)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == 32:
                path = target / f"{saved:03d}.jpg"
                cv2.imwrite(str(path), image)
                saved += 1
                print(f"已保存 {path}")
    finally:
        pipeline.stop()
        cv2.destroyAllWindows()
    print(f"完成：{target}，共 {saved} 帧")


def best_detection(result, conf_threshold: float):
    candidates = []
    for box in result.boxes:
        confidence = float(box.conf[0])
        if confidence >= conf_threshold:
            class_name = result.names[int(box.cls[0])]
            candidates.append((confidence, class_name))
    return max(candidates, default=None)


def evaluate(args: argparse.Namespace) -> None:
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit(f"评价需要 ultralytics：{exc}")

    dataset = Path(args.dataset)
    output = Path(args.output) if args.output else dataset / "results"
    output.mkdir(parents=True, exist_ok=True)
    model = YOLO(args.model)
    rows = []

    for object_key, meta in OBJECTS.items():
        images = sorted((dataset / object_key).glob("*.jpg"))
        images += sorted((dataset / object_key).glob("*.png"))
        if not images:
            print(f"警告：{object_key} 没有图像")
        for image_path in images:
            start = time.perf_counter()
            result = model(str(image_path), imgsz=args.imgsz, verbose=False)[0]
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            detection = best_detection(result, args.conf)
            predicted = detection[1] if detection else ""
            confidence = detection[0] if detection else 0.0
            triggered_property = COCO_TO_PROPERTY.get(predicted, DEFAULT_PROPERTY)
            rows.append(
                {
                    "object": object_key,
                    "object_cn": meta["display"],
                    "image": str(image_path),
                    "expected_coco": meta["coco"],
                    "predicted_coco": predicted,
                    "expected_property": meta["property"],
                    "triggered_property": triggered_property,
                    "detected": int(bool(detection)),
                    "class_correct": int(predicted == meta["coco"]),
                    "trigger_correct": int(triggered_property == meta["property"]),
                    "confidence": round(confidence, 6),
                    "inference_ms": round(elapsed_ms, 3),
                }
            )

    if not rows:
        raise SystemExit(f"未在 {dataset} 下找到验证图像")

    csv_path = output / "vision_validation_per_image.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    grouped = defaultdict(list)
    for row in rows:
        grouped[row["object"]].append(row)

    summary = []
    for object_key in OBJECTS:
        values = grouped.get(object_key, [])
        if not values:
            continue
        n = len(values)
        detected = sum(v["detected"] for v in values)
        class_correct = sum(v["class_correct"] for v in values)
        trigger_correct = sum(v["trigger_correct"] for v in values)
        detected_conf = [v["confidence"] for v in values if v["detected"]]
        summary.append(
            {
                "object": OBJECTS[object_key]["display"],
                "coco": OBJECTS[object_key]["coco"],
                "property": OBJECTS[object_key]["property"],
                "n": n,
                "class_correct": class_correct,
                "class_accuracy_pct": round(class_correct / n * 100, 1),
                "trigger_correct": trigger_correct,
                "trigger_accuracy_pct": round(trigger_correct / n * 100, 1),
                "miss_rate_pct": round((n - detected) / n * 100, 1),
                "mean_confidence": round(statistics.mean(detected_conf), 3) if detected_conf else 0.0,
                "mean_inference_ms": round(statistics.mean(v["inference_ms"] for v in values), 2),
            }
        )

    totals = {
        "n": len(rows),
        "class_correct": sum(r["class_correct"] for r in rows),
        "trigger_correct": sum(r["trigger_correct"] for r in rows),
        "detected": sum(r["detected"] for r in rows),
    }
    report = {
        "model": args.model,
        "imgsz": args.imgsz,
        "confidence_threshold": args.conf,
        "per_object": summary,
        "overall": {
            "n": totals["n"],
            "class_accuracy_pct": round(totals["class_correct"] / totals["n"] * 100, 1),
            "trigger_accuracy_pct": round(totals["trigger_correct"] / totals["n"] * 100, 1),
            "miss_rate_pct": round((totals["n"] - totals["detected"]) / totals["n"] * 100, 1),
            "mean_inference_ms": round(statistics.mean(r["inference_ms"] for r in rows), 2),
        },
    }
    (output / "vision_validation_summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    md = [
        "Table: 实验场景下的视觉识别与属性触发结果",
        "",
        "| 对象 | COCO标签 | 操作属性 | 图像数 | 类别识别正确率 | 属性触发正确率 | 漏检率 | 平均置信度 | 单帧时间/ms |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for item in summary:
        md.append(
            f"| {item['object']} | `{item['coco']}` | {item['property']} | {item['n']} | "
            f"{item['class_correct']}/{item['n']} ({item['class_accuracy_pct']:.1f}%) | "
            f"{item['trigger_correct']}/{item['n']} ({item['trigger_accuracy_pct']:.1f}%) | "
            f"{item['miss_rate_pct']:.1f}% | {item['mean_confidence']:.3f} | "
            f"{item['mean_inference_ms']:.2f} |"
        )
    overall = report["overall"]
    md.extend(
        [
            "",
            f"总体类别识别正确率为{overall['class_accuracy_pct']:.1f}%，"
            f"操作属性触发正确率为{overall['trigger_accuracy_pct']:.1f}%，"
            f"漏检率为{overall['miss_rate_pct']:.1f}%，"
            f"平均单帧处理时间为{overall['mean_inference_ms']:.2f} ms。",
        ]
    )
    md_path = output / "vision_validation_paper_table.md"
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"逐图结果：{csv_path}")
    print(f"汇总结果：{output / 'vision_validation_summary.json'}")
    print(f"论文表格：{md_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    capture_parser = sub.add_parser("capture", help="使用RealSense采集验证图像")
    capture_parser.add_argument("--object", required=True, choices=OBJECTS)
    capture_parser.add_argument("--output", default="my_test/data/vision_validation")
    capture_parser.add_argument("--frames", type=int, default=30)
    capture_parser.add_argument("--width", type=int, default=640)
    capture_parser.add_argument("--height", type=int, default=480)
    capture_parser.set_defaults(func=capture)

    evaluate_parser = sub.add_parser("evaluate", help="离线运行YOLO并生成统计结果")
    evaluate_parser.add_argument("--dataset", default="my_test/data/vision_validation")
    evaluate_parser.add_argument("--model", default="yolo/ultralytics-8.3.163/yolo11n.pt")
    evaluate_parser.add_argument("--output", default=None)
    evaluate_parser.add_argument("--conf", type=float, default=0.25)
    evaluate_parser.add_argument("--imgsz", type=int, default=640)
    evaluate_parser.set_defaults(func=evaluate)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
