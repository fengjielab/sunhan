#!/usr/bin/env python3
"""Offline visual-robustness data collector for the revision experiment.

The script uses an Intel RealSense RGB stream and the frozen YOLO model.  It
creates a deterministic 120-episode manifest, prompts the operator for each
physical scene, saves the RGB video and all detections above a low collection
threshold, and appends an episode-level summary after operator acceptance.

The robot is not used by this program.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional

WIDTH = 424
HEIGHT = 240
FPS = 15
PRIMARY_THRESHOLD = 0.25
COLLECTION_THRESHOLD = 0.05
EPISODE_DURATION_S = 10.0
EXPECTED_MODEL_SHA256 = (
    "0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1"
)

# This reproduces the built-in table in vision_physics_mapper.py.
CLASS_TO_STRATEGY = {
    "apple": "soft",
    "banana": "soft",
    "orange": "soft",
    "lemon": "soft",
    "teddy bear": "soft",
    "bottle": "medium",
    "cup": "medium",
    "bowl": "medium",
    "book": "hard",
    "cell phone": "hard",
    "keyboard": "hard",
    "mouse": "hard",
    "scissors": "hard",
}

REPRESENTATIVES = (
    ("banana", "soft"),
    ("bottle", "medium"),
    ("scissors", "hard"),
)

SUMMARY_FIELDS = [
    "episode_id",
    "sequence",
    "condition",
    "object_name",
    "target_class",
    "expected_strategy",
    "instance_id",
    "replicate",
    "distractor",
    "accepted_utc",
    "duration_s",
    "frames_processed",
    "primary_threshold",
    "collection_threshold",
    "autonomous_lock_class",
    "autonomous_lock_strategy",
    "autonomous_lock_confidence",
    "autonomous_lock_latency_s",
    "autonomous_correct_class",
    "autonomous_correct_strategy",
    "target_assisted_lock_found",
    "target_assisted_lock_latency_s",
    "target_assisted_lock_confidence",
    "no_detection_at_primary_threshold",
    "unknown_dangerous_mapped_lock",
    "video_file",
    "detections_file",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def episode_instruction(condition: str, target: str, rep: int, distractor: str) -> str:
    side = "LEFT" if rep % 2 else "RIGHT"
    offset = {
        1: "at the CENTER mark",
        2: "3 cm LEFT of center",
        3: "3 cm RIGHT of center",
        4: "3 cm TOWARD the camera from center",
        5: "3 cm AWAY from the camera from center",
    }[rep]
    base = f"Put {target} in the marked target square, {offset}, in its nominal orientation."
    instructions = {
        "normal": base + " Normal laboratory lighting; no other object in view.",
        "dim": base + " Dim illumination (target approximately 50-100 lux); no distractor.",
        "backlight": base + " Put a bright lamp behind the object, aimed generally toward camera.",
        "occlusion50": base + f" Cover about 50% of its visible silhouette from the {side} with a matte card.",
        "clutter": base + " Place the same three clutter items outside the square: keys, tape roll, and ruler.",
        "multiobject": base + f" Put {distractor} 12-15 cm to the {side}, at the same depth as the target.",
        "new_instance": base + " Use physical instance B (different item of the SAME semantic class).",
        "unknown": f"Put the unknown item '{target}' alone in the marked target square, {offset}.",
    }
    return instructions[condition]


def create_manifest(path: Path) -> None:
    """Create the fixed 120-episode, condition-blocked manifest."""
    rows: List[Dict[str, str]] = []
    rng = random.Random(20260904)
    conditions = [
        "normal",
        "dim",
        "backlight",
        "occlusion50",
        "clutter",
        "multiobject",
        "new_instance",
    ]
    cross_strategy_distractor = {
        "banana": "bottle",
        "bottle": "scissors",
        "scissors": "banana",
    }

    for condition in conditions:
        block = []
        for target_class, strategy in REPRESENTATIVES:
            for rep in range(1, 6):
                distractor = (
                    cross_strategy_distractor[target_class]
                    if condition == "multiobject"
                    else ""
                )
                code = {
                    "normal": "NOR",
                    "dim": "DIM",
                    "backlight": "BKL",
                    "occlusion50": "OCC",
                    "clutter": "CLU",
                    "multiobject": "MUL",
                    "new_instance": "INS",
                }[condition]
                block.append(
                    {
                        "episode_id": f"{code}_{target_class.upper().replace(' ', '-')}_R{rep:02d}",
                        "condition": condition,
                        "object_name": target_class,
                        "target_class": target_class,
                        "expected_strategy": strategy,
                        "instance_id": "B" if condition == "new_instance" else "A",
                        "replicate": str(rep),
                        "distractor": distractor,
                        "instruction": episode_instruction(
                            condition, target_class, rep, distractor
                        ),
                    }
                )
        rng.shuffle(block)
        rows.extend(block)

    unknown_items = ["stapler", "screwdriver", "tape measure", "cardboard box", "sponge"]
    unknown_block = []
    for item in unknown_items:
        for rep in range(1, 4):
            safe_item = item.upper().replace(" ", "-")
            unknown_block.append(
                {
                    "episode_id": f"UNK_{safe_item}_R{rep:02d}",
                    "condition": "unknown",
                    "object_name": item,
                    "target_class": "__unknown__",
                    "expected_strategy": "unknown",
                    "instance_id": "A",
                    "replicate": str(rep),
                    "distractor": "",
                    "instruction": episode_instruction("unknown", item, rep, ""),
                }
            )
    rng.shuffle(unknown_block)
    rows.extend(unknown_block)

    for sequence, row in enumerate(rows, start=1):
        row["sequence"] = str(sequence)

    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "sequence",
        "episode_id",
        "condition",
        "object_name",
        "target_class",
        "expected_strategy",
        "instance_id",
        "replicate",
        "distractor",
        "instruction",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def load_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def completed_episode_ids(summary_path: Path) -> set[str]:
    if not summary_path.exists():
        return set()
    return {row["episode_id"] for row in load_csv(summary_path)}


def append_summary(path: Path, row: Dict[str, object]) -> None:
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow({key: row.get(key, "") for key in SUMMARY_FIELDS})
        handle.flush()
        os.fsync(handle.fileno())


def detections_from_result(result) -> List[Dict[str, object]]:
    detections = []
    for order, box in enumerate(result.boxes):
        cls_id = int(box.cls[0])
        cls_name = str(result.names[cls_id])
        xyxy = [round(float(value), 2) for value in box.xyxy[0].cpu().tolist()]
        detections.append(
            {
                "order": order,
                "class_id": cls_id,
                "class_name": cls_name,
                "confidence": float(box.conf[0]),
                "bbox_xyxy": xyxy,
                "mapped_strategy": CLASS_TO_STRATEGY.get(cls_name, "unknown"),
            }
        )
    return detections


def mapper_choice(detections: Iterable[Dict[str, object]], threshold: float):
    """Reproduce VisionPhysicsMapper.detect_and_map selection semantics."""
    eligible = [d for d in detections if float(d["confidence"]) >= threshold]
    for det in eligible:
        if str(det["class_name"]) in CLASS_TO_STRATEGY:
            return det
    if eligible:
        return max(eligible, key=lambda item: float(item["confidence"]))
    return None


def draw_preview(frame, detections, episode, recording: bool, elapsed: float):
    import cv2

    canvas = frame.copy()
    for det in detections:
        if float(det["confidence"]) < PRIMARY_THRESHOLD:
            continue
        x1, y1, x2, y2 = [int(round(v)) for v in det["bbox_xyxy"]]
        color = (0, 200, 0) if det["class_name"] == episode["target_class"] else (0, 180, 255)
        cv2.rectangle(canvas, (x1, y1), (x2, y2), color, 1)
        label = f"{det['class_name']} {float(det['confidence']):.2f}"
        cv2.putText(canvas, label, (x1, max(14, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

    state = f"REC {elapsed:04.1f}/{EPISODE_DURATION_S:.0f}s" if recording else "SPACE=start  Q=quit"
    cv2.putText(canvas, episode["episode_id"], (8, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
    cv2.putText(canvas, state, (8, HEIGHT - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255) if recording else (255, 255, 255), 1)
    return canvas


def bool_int(value: bool) -> int:
    return 1 if value else 0


def run_episode(pipeline, model, episode, output_root: Path, capture_conf: float):
    import cv2
    import pyrealsense2 as rs

    video_dir = output_root / "videos"
    detection_dir = output_root / "detections"
    video_dir.mkdir(parents=True, exist_ok=True)
    detection_dir.mkdir(parents=True, exist_ok=True)
    final_video = video_dir / f"{episode['episode_id']}.mp4"
    final_jsonl = detection_dir / f"{episode['episode_id']}.jsonl"
    temp_video = video_dir / f"{episode['episode_id']}__tmp.mp4"
    temp_jsonl = detection_dir / f"{episode['episode_id']}__tmp.jsonl"

    print("\n" + "=" * 78)
    print(f"Episode {episode['sequence']}/120: {episode['episode_id']}")
    print(episode["instruction"])
    print("Arrange the scene, wait about 2 s for auto-exposure, then press SPACE.")

    latest_frame = None
    latest_detections = []
    while True:
        frames = pipeline.wait_for_frames()
        color_frame = frames.get_color_frame()
        if not color_frame:
            continue
        import numpy as np

        latest_frame = np.asanyarray(color_frame.get_data())
        preview = draw_preview(latest_frame, latest_detections, episode, False, 0.0)
        cv2.imshow("Offline vision robustness", preview)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            return "quit", None
        if key == 32:
            break

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(temp_video), fourcc, FPS, (WIDTH, HEIGHT))
    if not writer.isOpened():
        raise RuntimeError(f"Cannot open video writer: {temp_video}")

    start = time.perf_counter()
    frame_id = 0
    autonomous_lock = None
    autonomous_lock_latency = None
    target_lock = None
    target_lock_latency = None

    with temp_jsonl.open("w", encoding="utf-8") as jsonl:
        while True:
            now = time.perf_counter()
            elapsed = now - start
            if elapsed >= EPISODE_DURATION_S:
                break
            frames = pipeline.wait_for_frames()
            color_frame = frames.get_color_frame()
            if not color_frame:
                continue
            import numpy as np

            frame = np.asanyarray(color_frame.get_data())
            capture_time = time.perf_counter()
            result = model.predict(frame, conf=capture_conf, verbose=False)[0]
            inference_end = time.perf_counter()
            detections = detections_from_result(result)
            writer.write(frame)

            record = {
                "episode_id": episode["episode_id"],
                "frame_id": frame_id,
                "time_from_start_s": capture_time - start,
                "result_time_from_start_s": inference_end - start,
                "inference_duration_ms": (inference_end - capture_time) * 1000.0,
                "detections": detections,
            }
            jsonl.write(json.dumps(record, ensure_ascii=False) + "\n")

            if autonomous_lock is None:
                choice = mapper_choice(detections, PRIMARY_THRESHOLD)
                if choice is not None:
                    autonomous_lock = choice
                    autonomous_lock_latency = inference_end - start

            if episode["target_class"] != "__unknown__" and target_lock is None:
                candidates = [
                    det
                    for det in detections
                    if det["class_name"] == episode["target_class"]
                    and float(det["confidence"]) >= PRIMARY_THRESHOLD
                ]
                if candidates:
                    target_lock = max(candidates, key=lambda item: float(item["confidence"]))
                    target_lock_latency = inference_end - start

            preview = draw_preview(frame, detections, episode, True, elapsed)
            cv2.imshow("Offline vision robustness", preview)
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord("x")):
                writer.release()
                temp_video.unlink(missing_ok=True)
                temp_jsonl.unlink(missing_ok=True)
                print("Episode aborted. It was not saved.")
                return "retake", None
            frame_id += 1

    writer.release()
    latest_detections = []

    lock_class = str(autonomous_lock["class_name"]) if autonomous_lock else ""
    lock_strategy = CLASS_TO_STRATEGY.get(lock_class, "unknown") if autonomous_lock else ""
    is_unknown = episode["target_class"] == "__unknown__"
    summary = {
        **episode,
        "accepted_utc": datetime.now(timezone.utc).isoformat(),
        "duration_s": round(time.perf_counter() - start, 6),
        "frames_processed": frame_id,
        "primary_threshold": PRIMARY_THRESHOLD,
        "collection_threshold": capture_conf,
        "autonomous_lock_class": lock_class,
        "autonomous_lock_strategy": lock_strategy,
        "autonomous_lock_confidence": round(float(autonomous_lock["confidence"]), 6) if autonomous_lock else "",
        "autonomous_lock_latency_s": round(float(autonomous_lock_latency), 6) if autonomous_lock_latency is not None else "",
        "autonomous_correct_class": "" if is_unknown else bool_int(lock_class == episode["target_class"]),
        "autonomous_correct_strategy": "" if is_unknown else bool_int(lock_strategy == episode["expected_strategy"]),
        "target_assisted_lock_found": "" if is_unknown else bool_int(target_lock is not None),
        "target_assisted_lock_latency_s": "" if target_lock_latency is None else round(float(target_lock_latency), 6),
        "target_assisted_lock_confidence": "" if target_lock is None else round(float(target_lock["confidence"]), 6),
        "no_detection_at_primary_threshold": bool_int(autonomous_lock is None),
        "unknown_dangerous_mapped_lock": bool_int(is_unknown and lock_class in CLASS_TO_STRATEGY),
        "video_file": str(final_video.relative_to(output_root)),
        "detections_file": str(final_jsonl.relative_to(output_root)),
    }

    print("\nEpisode finished:")
    print(
        f"  autonomous lock = {lock_class or 'NONE'} / {lock_strategy or 'NONE'}; "
        f"target-assisted lock = {'YES' if target_lock else 'NO'}"
    )
    while True:
        answer = input("Accept? [Y] yes  [R] retake  [Q] quit without accepting: ").strip().lower()
        if answer in ("y", "yes", ""):
            os.replace(temp_video, final_video)
            os.replace(temp_jsonl, final_jsonl)
            return "accept", summary
        if answer == "r":
            temp_video.unlink(missing_ok=True)
            temp_jsonl.unlink(missing_ok=True)
            return "retake", None
        if answer == "q":
            temp_video.unlink(missing_ok=True)
            temp_jsonl.unlink(missing_ok=True)
            return "quit", None


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        type=Path,
        default=Path("/home/mfj/sunhan/yolo/ultralytics-8.3.163/yolo11n.pt"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/home/mfj/sunhan/vision_robustness_data"),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).with_name("scene_manifest.csv"),
    )
    parser.add_argument("--make-manifest-only", action="store_true")
    parser.add_argument("--episode", help="Run one specified episode ID instead of the next unfinished one.")
    parser.add_argument(
        "--condition",
        choices=["normal", "dim", "backlight", "occlusion50", "clutter", "multiobject", "new_instance", "unknown"],
        help="Run only unfinished episodes from one scene condition.",
    )
    parser.add_argument("--allow-model-mismatch", action="store_true")
    parser.add_argument("--capture-conf", type=float, default=COLLECTION_THRESHOLD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.manifest.exists():
        create_manifest(args.manifest)
        print(f"Created manifest: {args.manifest}")
    manifest = load_csv(args.manifest)
    if len(manifest) != 120:
        raise RuntimeError(f"Manifest must contain 120 episodes, found {len(manifest)}")
    if args.make_manifest_only:
        return 0

    if not args.model.exists():
        print(f"Model not found: {args.model}", file=sys.stderr)
        return 2
    model_hash = sha256_file(args.model)
    if model_hash != EXPECTED_MODEL_SHA256 and not args.allow_model_mismatch:
        print("MODEL HASH MISMATCH. Collection stopped.", file=sys.stderr)
        print(f"Expected: {EXPECTED_MODEL_SHA256}", file=sys.stderr)
        print(f"Actual:   {model_hash}", file=sys.stderr)
        return 3

    args.output.mkdir(parents=True, exist_ok=True)
    summary_path = args.output / "episode_summary.csv"
    snapshot = args.output / "scene_manifest_snapshot.csv"
    if not snapshot.exists():
        shutil.copy2(args.manifest, snapshot)

    completed = completed_episode_ids(summary_path)
    if args.episode:
        candidates = [row for row in manifest if row["episode_id"] == args.episode]
        if not candidates:
            print(f"Unknown episode ID: {args.episode}", file=sys.stderr)
            return 4
        if args.episode in completed:
            print(f"Episode already completed: {args.episode}", file=sys.stderr)
            return 5
        pending = candidates
    else:
        pending = [
            row
            for row in manifest
            if row["episode_id"] not in completed
            and (args.condition is None or row["condition"] == args.condition)
        ]

    if not pending:
        print("All 120 episodes are complete.")
        return 0

    try:
        import cv2
        from ultralytics import YOLO
        import pyrealsense2 as rs
    except ImportError as exc:
        print(f"Missing Python dependency: {exc}", file=sys.stderr)
        return 6

    config_record = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "model_path": str(args.model.resolve()),
        "model_sha256": model_hash,
        "resolution": [WIDTH, HEIGHT],
        "fps": FPS,
        "primary_threshold": PRIMARY_THRESHOLD,
        "collection_threshold": args.capture_conf,
        "episode_duration_s": EPISODE_DURATION_S,
        "opencv_version": cv2.__version__,
    }
    config_path = args.output / "run_config.json"
    if not config_path.exists():
        config_path.write_text(json.dumps(config_record, indent=2), encoding="utf-8")

    print("Loading YOLO model...")
    model = YOLO(str(args.model))
    pipeline = rs.pipeline()
    rs_config = rs.config()
    rs_config.enable_stream(rs.stream.color, WIDTH, HEIGHT, rs.format.bgr8, FPS)
    pipeline.start(rs_config)
    print("Camera started. Warming up auto-exposure for 2 seconds...")
    warmup_end = time.perf_counter() + 2.0
    while time.perf_counter() < warmup_end:
        pipeline.wait_for_frames()

    try:
        index = 0
        while index < len(pending):
            episode = pending[index]
            action, summary = run_episode(
                pipeline, model, episode, args.output, args.capture_conf
            )
            if action == "quit":
                break
            if action == "retake":
                continue
            append_summary(summary_path, summary)
            print(f"Accepted and saved: {episode['episode_id']}")
            index += 1
    finally:
        pipeline.stop()
        cv2.destroyAllWindows()

    print(f"Summary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
