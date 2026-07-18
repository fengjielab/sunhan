#!/usr/bin/env python3
"""Read-only integrity and reproduction checks for the Mechatronics v4 archive."""
from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path
from statistics import mean, median

import numpy as np


ROOT = Path(__file__).resolve().parent
EXPECTED_SHA256 = {
    "01_frozen_tables/all_trials_135.csv": "d723d973d4c352040c9a89f500a2508028dceb80b3fe588f077a67c8b8ad4c7a",
    "05_vision_validation_final_48_19ms/vision_validation/results/vision_validation_per_image.csv": "6351ee1853360952a113b3efe0561f70e99cb70b98cc67c2c2a0c0d82bbcbaa7",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def bootstrap_ci(diffs: list[float], rng: np.random.RandomState, n_bootstrap: int = 10_000) -> tuple[float, float]:
    samples = np.empty(n_bootstrap)
    values = np.asarray(diffs, dtype=float)
    for index in range(n_bootstrap):
        samples[index] = values[rng.choice(len(values), size=len(values), replace=True)].mean()
    return tuple(np.percentile(samples, [2.5, 97.5]))


def main() -> None:
    trials_path = ROOT / "01_frozen_tables/all_trials_135.csv"
    trials = read_csv(trials_path)
    assert len(trials) == 135, f"Expected 135 trial rows, found {len(trials)}"

    blocks: dict[tuple[str, str, str], dict[str, dict[str, str]]] = {}
    for row in trials:
        key = (row["operator"], row["object_attr"], row["group_num"])
        blocks.setdefault(key, {})[row["mode"]] = row
    assert len(blocks) == 27 and all(set(rows) == set("ABCDE") for rows in blocks.values())

    trajectory_root = ROOT / "02_raw_trajectory_csv"
    raw_logs = []
    for row in trials:
        source = Path(row["source_file"])
        filename = source.name.replace("_summary.json", ".csv").replace(".json", ".csv")
        raw_log = trajectory_root / source.parent / filename
        assert raw_log.exists(), f"Missing raw trajectory log: {raw_log}"
        raw_logs.append(raw_log)
    assert len(raw_logs) == 135

    time_diffs = [float(rows["E"]["duration_s"]) - float(rows["C"]["duration_s"]) for rows in blocks.values()]
    traj_diffs = [float(rows["E"]["traj_length_m"]) - float(rows["C"]["traj_length_m"]) for rows in blocks.values()]
    # Use one continuous RNG stream, exactly as bootstrap_ci_ce.py does:
    # completion-time resamples first, then trajectory-length resamples.
    rng = np.random.RandomState(42)
    time_ci = bootstrap_ci(time_diffs, rng)
    traj_ci = bootstrap_ci(traj_diffs, rng)
    assert np.allclose(time_ci, (1.104, 2.508), atol=0.001)
    assert np.allclose(traj_ci, (-0.0142, 0.0591), atol=0.0001)

    s1 = (ROOT / "03_outcome_registry/Supplementary_Table_S1_final.md").read_text(encoding="utf-8")
    s1_rows = [line for line in s1.splitlines() if line.startswith("| MB")]
    assert len(s1_rows) == 27
    frozen_pairs = {(round(float(row["duration_s"]), 2), round(float(row["traj_length_m"]), 3), row["mode"]) for row in trials}
    successes = dict.fromkeys("ABCDE", 0)
    s1_entries = 0
    for line in s1_rows:
        cells = [cell.strip() for cell in line.split("|")[1:-1]]
        for mode, entry in zip("ABCDE", cells[5:10]):
            match = re.fullmatch(r"([0-9.]+) / ([0-9.]+) / ([SF])", entry)
            assert match, f"Malformed S1 entry: {entry}"
            duration, trajectory, outcome = match.groups()
            assert (float(duration), float(trajectory), mode) in frozen_pairs
            successes[mode] += outcome == "S"
            s1_entries += 1
    assert s1_entries == 135 and successes == {"A": 22, "B": 21, "C": 26, "D": 24, "E": 24}

    vision = read_csv(ROOT / "05_vision_validation_final_48_19ms/vision_validation/results/vision_validation_per_image.csv")
    assert len(vision) == 180
    vision_mean = mean(float(row["inference_ms"]) for row in vision)
    assert abs(vision_mean - 48.192906) < 1e-6

    profile = read_csv(ROOT / "06_cycle_timing/control_loop_profile_vision.csv")
    cycle_median = median(float(row["period_ms"]) for row in profile)
    assert abs(cycle_median - 5.072) < 0.001

    for relative, expected in EXPECTED_SHA256.items():
        if expected:
            actual = sha256(ROOT / relative)
            assert actual == expected, f"SHA-256 mismatch for {relative}: {actual}"

    print("PASS")
    print(f"Blocks: {len(blocks)}; frozen trials: {len(trials)}; raw trajectory logs: {len(raw_logs)}; S1 entries: {s1_entries}")
    print(f"Bootstrap time CI: [{time_ci[0]:.3f}, {time_ci[1]:.3f}] s")
    print(f"Bootstrap trajectory CI: [{traj_ci[0]:.4f}, {traj_ci[1]:.4f}] m")
    print(f"Vision mean: {vision_mean:.6f} ms; cycle-time median: {cycle_median:.3f} ms")


if __name__ == "__main__":
    main()
