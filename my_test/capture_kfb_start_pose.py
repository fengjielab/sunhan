#!/usr/bin/env python3
"""Capture and freeze the manually established fixed-target start pose.

This utility never commands robot motion.  A qualified operator must position
the robot with the laboratory's approved procedure before running it.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import panda_py


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--robot-ip", default="192.168.1.51")
    parser.add_argument("--pad-width-mm", type=float, required=True)
    parser.add_argument("--pad-height-mm", type=float, required=True)
    parser.add_argument("--pad-thickness-mm", type=float, required=True)
    parser.add_argument("--pad-distance-mm", type=float, default=30.0)
    parser.add_argument(
        "--fixed-target-checked", action="store_true",
        help="attest that the pad is rigidly fixed and does not bottom out at 5 N",
    )
    args = parser.parse_args()

    if args.output.exists():
        parser.error(f"refusing to overwrite existing file: {args.output}")
    if not args.fixed_target_checked:
        parser.error("--fixed-target-checked is required")
    if args.pad_width_mm < 60 or args.pad_height_mm < 60 or args.pad_thickness_mm < 10:
        parser.error("pad must be at least 60 x 60 x 10 mm")
    if abs(args.pad_distance_mm - 30.0) > 2.0:
        parser.error("start pose must be 30±2 mm from the pad")

    panda = panda_py.Panda(args.robot_ip)
    state = panda.get_state()
    position = [float(state.O_T_EE[index]) for index in (12, 13, 14)]
    orientation = [float(value) for value in panda.get_orientation()]
    payload = {
        "schema_version": 1,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "robot_ip": args.robot_ip,
        "position_m": position,
        "orientation_xyzw": orientation,
        "orientation_source": "panda_py.Panda.get_orientation native ordering",
        "pad_distance_m": args.pad_distance_mm / 1000.0,
        "pad_dimensions_mm": [
            args.pad_width_mm,
            args.pad_height_mm,
            args.pad_thickness_mm,
        ],
        "fixed_target_checked": True,
        "attestation": "rigidly fixed and no bottoming or movement at 5 N",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

