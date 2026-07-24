#!/usr/bin/env python3
"""Reproduce the minimum manuscript-aligned summaries from data/."""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / "data" / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def bootstrap_ci(values: list[float], rng: np.random.RandomState, n: int = 10_000) -> tuple[float, float]:
    array = np.asarray(values, dtype=float)
    samples = np.empty(n)
    for index in range(n):
        samples[index] = rng.choice(array, size=len(array), replace=True).mean()
    return tuple(np.percentile(samples, [2.5, 97.5]))


def main() -> None:
    trials = read_csv("trials.csv")
    assert len(trials) == 135, f"Expected 135 trials, found {len(trials)}"

    blocks: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for row in trials:
        blocks[row["block_id"]][row["mode"]] = row
    assert len(blocks) == 27 and all(set(rows) == set("ABCDE") for rows in blocks.values())

    time_diffs = [float(rows["E"]["completion_time_s"]) - float(rows["C"]["completion_time_s"]) for rows in blocks.values()]
    path_diffs = [float(rows["E"]["trajectory_length_m"]) - float(rows["C"]["trajectory_length_m"]) for rows in blocks.values()]
    rng = np.random.RandomState(42)
    time_ci = bootstrap_ci(time_diffs, rng)
    path_ci = bootstrap_ci(path_diffs, rng)

    times = {mode: [float(row["completion_time_s"]) for row in trials if row["mode"] == mode] for mode in "ABCDE"}
    vision = read_csv("vision_test.csv")
    nasa = read_csv("nasa_tlx.csv")
    assert len(vision) == 180, f"Expected 180 vision records, found {len(vision)}"
    assert len(nasa) == 45, f"Expected 45 NASA-TLX records, found {len(nasa)}"
    vision_mean = np.mean([float(row["inference_ms"]) for row in vision])
    vision_accuracy = np.mean([int(row["class_correct"]) for row in vision])
    nasa_dims = ["mental_demand", "physical_demand", "temporal_demand", "performance", "effort", "frustration"]
    nasa_by_mode: dict[str, list[float]] = defaultdict(list)
    for row in nasa:
        nasa_by_mode[row["mode"]].append(np.mean([float(row[field]) for field in nasa_dims]))

    print(f"Trials: {len(trials)}; matched blocks: {len(blocks)}")
    print(f"C-E mean completion-time difference: {np.mean(time_diffs):.3f} s")
    print(f"Completion-time bootstrap 95% CI: [{time_ci[0]:.3f}, {time_ci[1]:.3f}] s")
    print(f"Trajectory-length bootstrap 95% CI: [{path_ci[0]:.4f}, {path_ci[1]:.4f}] m")
    print("Completion-time means: " + ", ".join(f"{mode}={np.mean(values):.2f} s" for mode, values in times.items()))
    print(f"Vision records: {len(vision)}; class accuracy: {vision_accuracy:.3f}; mean inference: {vision_mean:.6f} ms")
    print(f"NASA-TLX records: {len(nasa)}")
    print("Raw NASA-TLX means: " + ", ".join(f"{mode}={np.mean(values):.2f}" for mode, values in sorted(nasa_by_mode.items())))


if __name__ == "__main__":
    main()
