#!/usr/bin/env python3

import argparse
import json
import math
from pathlib import Path

import cv2
import numpy as np


METHODS = {
    "tsai": cv2.CALIB_HAND_EYE_TSAI,
    "park": cv2.CALIB_HAND_EYE_PARK,
    "horaud": cv2.CALIB_HAND_EYE_HORAUD,
    "andreff": cv2.CALIB_HAND_EYE_ANDREFF,
    "daniilidis": cv2.CALIB_HAND_EYE_DANIILIDIS,
}


def normalize_quaternion_xyzw(quat):
    quat = np.asarray(quat, dtype=float).reshape(4)
    norm = np.linalg.norm(quat)
    if norm < 1e-12:
        raise ValueError("Quaternion norm is zero.")
    return quat / norm


def quaternion_xyzw_to_matrix(quat):
    x, y, z, w = normalize_quaternion_xyzw(quat)
    xx = x * x
    yy = y * y
    zz = z * z
    xy = x * y
    xz = x * z
    yz = y * z
    wx = w * x
    wy = w * y
    wz = w * z

    return np.array(
        [
            [1.0 - 2.0 * (yy + zz), 2.0 * (xy - wz), 2.0 * (xz + wy)],
            [2.0 * (xy + wz), 1.0 - 2.0 * (xx + zz), 2.0 * (yz - wx)],
            [2.0 * (xz - wy), 2.0 * (yz + wx), 1.0 - 2.0 * (xx + yy)],
        ],
        dtype=float,
    )


def matrix_to_quaternion_xyzw(rotation):
    rotation = np.asarray(rotation, dtype=float).reshape(3, 3)
    trace = np.trace(rotation)

    if trace > 0.0:
        s = math.sqrt(trace + 1.0) * 2.0
        w = 0.25 * s
        x = (rotation[2, 1] - rotation[1, 2]) / s
        y = (rotation[0, 2] - rotation[2, 0]) / s
        z = (rotation[1, 0] - rotation[0, 1]) / s
    elif rotation[0, 0] > rotation[1, 1] and rotation[0, 0] > rotation[2, 2]:
        s = math.sqrt(1.0 + rotation[0, 0] - rotation[1, 1] - rotation[2, 2]) * 2.0
        w = (rotation[2, 1] - rotation[1, 2]) / s
        x = 0.25 * s
        y = (rotation[0, 1] + rotation[1, 0]) / s
        z = (rotation[0, 2] + rotation[2, 0]) / s
    elif rotation[1, 1] > rotation[2, 2]:
        s = math.sqrt(1.0 + rotation[1, 1] - rotation[0, 0] - rotation[2, 2]) * 2.0
        w = (rotation[0, 2] - rotation[2, 0]) / s
        x = (rotation[0, 1] + rotation[1, 0]) / s
        y = 0.25 * s
        z = (rotation[1, 2] + rotation[2, 1]) / s
    else:
        s = math.sqrt(1.0 + rotation[2, 2] - rotation[0, 0] - rotation[1, 1]) * 2.0
        w = (rotation[1, 0] - rotation[0, 1]) / s
        x = (rotation[0, 2] + rotation[2, 0]) / s
        y = (rotation[1, 2] + rotation[2, 1]) / s
        z = 0.25 * s

    quat = np.array([x, y, z, w], dtype=float)
    return normalize_quaternion_xyzw(quat)


def compose_transform(rotation, translation):
    transform = np.eye(4, dtype=float)
    transform[:3, :3] = np.asarray(rotation, dtype=float).reshape(3, 3)
    transform[:3, 3] = np.asarray(translation, dtype=float).reshape(3)
    return transform


def invert_transform(transform):
    rotation = transform[:3, :3]
    translation = transform[:3, 3]
    inverse = np.eye(4, dtype=float)
    inverse[:3, :3] = rotation.T
    inverse[:3, 3] = -rotation.T @ translation
    return inverse


def transform_from_pose(pose):
    rotation = quaternion_xyzw_to_matrix(pose["quaternion_xyzw"])
    translation = np.asarray(pose["translation"], dtype=float).reshape(3)
    return compose_transform(rotation, translation)


def rotation_angle_deg(rotation):
    rotation = np.asarray(rotation, dtype=float).reshape(3, 3)
    cosine = (np.trace(rotation) - 1.0) / 2.0
    cosine = float(np.clip(cosine, -1.0, 1.0))
    return math.degrees(math.acos(cosine))


def load_samples(path):
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)

    samples = payload.get("samples", [])
    if len(samples) < 3:
        raise ValueError("At least 3 samples are required; 15+ is recommended.")

    base_gripper = []
    camera_target = []
    sample_names = []

    for index, sample in enumerate(samples, start=1):
        if "gripper_wrt_base" not in sample or "target_wrt_camera" not in sample:
            raise ValueError(
                f"Sample #{index} must contain gripper_wrt_base and target_wrt_camera."
            )
        base_gripper.append(transform_from_pose(sample["gripper_wrt_base"]))
        camera_target.append(transform_from_pose(sample["target_wrt_camera"]))
        sample_names.append(sample.get("name", f"pose_{index:03d}"))

    return sample_names, base_gripper, camera_target


def prepare_handeye_inputs(base_gripper_list, camera_target_list, mode):
    rotations_robot = []
    translations_robot = []
    rotations_target = []
    translations_target = []

    for base_gripper, camera_target in zip(base_gripper_list, camera_target_list):
        if mode == "eye_in_hand":
            robot_transform = base_gripper
        elif mode == "eye_to_hand":
            robot_transform = invert_transform(base_gripper)
        else:
            raise ValueError(f"Unsupported mode: {mode}")

        rotations_robot.append(robot_transform[:3, :3])
        translations_robot.append(robot_transform[:3, 3].reshape(3, 1))
        rotations_target.append(camera_target[:3, :3])
        translations_target.append(camera_target[:3, 3].reshape(3, 1))

    return rotations_robot, translations_robot, rotations_target, translations_target


def evaluate_solution(base_gripper_list, camera_target_list, solved_transform, mode):
    estimated_constants = []

    for base_gripper, camera_target in zip(base_gripper_list, camera_target_list):
        if mode == "eye_in_hand":
            estimated_constant = base_gripper @ solved_transform @ camera_target
        elif mode == "eye_to_hand":
            estimated_constant = invert_transform(base_gripper) @ solved_transform @ camera_target
        else:
            raise ValueError(f"Unsupported mode: {mode}")
        estimated_constants.append(estimated_constant)

    reference = estimated_constants[0]
    translation_errors = []
    rotation_errors = []

    for current in estimated_constants[1:]:
        delta = invert_transform(reference) @ current
        translation_errors.append(float(np.linalg.norm(delta[:3, 3])))
        rotation_errors.append(rotation_angle_deg(delta[:3, :3]))

    if not translation_errors:
        translation_errors = [0.0]
        rotation_errors = [0.0]

    return {
        "translation_mean_m": float(np.mean(translation_errors)),
        "translation_max_m": float(np.max(translation_errors)),
        "rotation_mean_deg": float(np.mean(rotation_errors)),
        "rotation_max_deg": float(np.max(rotation_errors)),
    }


def solve_handeye(base_gripper_list, camera_target_list, mode, method_name):
    rotations_robot, translations_robot, rotations_target, translations_target = prepare_handeye_inputs(
        base_gripper_list,
        camera_target_list,
        mode,
    )
    rotation, translation = cv2.calibrateHandEye(
        rotations_robot,
        translations_robot,
        rotations_target,
        translations_target,
        method=METHODS[method_name],
    )
    solved_transform = compose_transform(rotation, translation.reshape(3))
    metrics = evaluate_solution(base_gripper_list, camera_target_list, solved_transform, mode)
    return solved_transform, metrics


def result_label(mode):
    if mode == "eye_in_hand":
        return "T_gripper_camera"
    if mode == "eye_to_hand":
        return "T_base_camera"
    raise ValueError(f"Unsupported mode: {mode}")


def serialize_result(transform, metrics, mode, method_name):
    rotation = transform[:3, :3]
    translation = transform[:3, 3]
    quaternion = matrix_to_quaternion_xyzw(rotation)
    return {
        "mode": mode,
        "method": method_name,
        "result_name": result_label(mode),
        "transform_4x4": transform.round(9).tolist(),
        "translation_xyz_m": translation.round(9).tolist(),
        "quaternion_xyzw": quaternion.round(9).tolist(),
        "consistency_metrics": metrics,
    }


def print_result(result):
    print("=" * 80)
    print(f"mode: {result['mode']}")
    print(f"method: {result['method']}")
    print(f"result: {result['result_name']}")
    print("transform_4x4:")
    for row in result["transform_4x4"]:
        print("  ", row)
    print(f"translation_xyz_m: {result['translation_xyz_m']}")
    print(f"quaternion_xyzw: {result['quaternion_xyzw']}")
    print("consistency_metrics:")
    for key, value in result["consistency_metrics"].items():
        print(f"  {key}: {value:.9f}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Solve D435i-Panda hand-eye calibration from recorded samples."
    )
    parser.add_argument(
        "--samples",
        type=Path,
        required=True,
        help="Path to the JSON file containing calibration samples.",
    )
    parser.add_argument(
        "--mode",
        choices=["eye_in_hand", "eye_to_hand"],
        default="eye_in_hand",
        help="Calibration configuration. For wrist-mounted camera use eye_in_hand.",
    )
    parser.add_argument(
        "--method",
        choices=["all", *METHODS.keys()],
        default="all",
        help="OpenCV hand-eye solver to use.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path to save result JSON. If --method all is used, a list is saved.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    sample_names, base_gripper_list, camera_target_list = load_samples(args.samples)
    print(f"Loaded {len(sample_names)} samples from {args.samples}")

    method_names = list(METHODS.keys()) if args.method == "all" else [args.method]
    results = []

    for method_name in method_names:
        transform, metrics = solve_handeye(
            base_gripper_list,
            camera_target_list,
            args.mode,
            method_name,
        )
        result = serialize_result(transform, metrics, args.mode, method_name)
        print_result(result)
        results.append(result)

    if args.output:
        payload = results if args.method == "all" else results[0]
        with open(args.output, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
        print(f"Saved result to {args.output}")


if __name__ == "__main__":
    main()
