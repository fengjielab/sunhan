#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""提取并分析 C0/C1/W0/W1 补充实验；不改动原始试次文件。"""

from __future__ import annotations

import argparse
import itertools
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


CONDITIONS = ["C0", "C1", "W0", "W1"]
RNG_SEED = 20260806


def event_map(payload: dict) -> dict[str, dict]:
    events = payload if isinstance(payload, list) else payload.get("events", [])
    return {
        item["event"]: item
        for item in events
        if isinstance(item, dict) and item.get("event")
    }


def integrate_excess(time_s: np.ndarray, force_N: np.ndarray,
                     threshold_N: float) -> float:
    if len(time_s) < 2:
        return math.nan
    excess = np.maximum(force_N - threshold_N, 0.0)
    return float(np.trapezoid(excess, time_s))


def first_finite_text(series: pd.Series, default: str = "unknown") -> str:
    for value in series:
        text = str(value).strip()
        if text and text.lower() not in ("nan", "unknown"):
            return text
    return default


def extract_trial(csv_path: Path) -> dict:
    events_path = csv_path.with_name(csv_path.stem + "_events.json")
    summary_path = csv_path.with_name(csv_path.stem + "_summary.json")
    if not events_path.exists() or not summary_path.exists():
        raise FileNotFoundError(f"missing companion JSON for {csv_path}")

    df = pd.read_csv(csv_path)
    required = {
        "system_time", "F_ext_mag", "K_trans", "force_threshold",
        "condition_code", "actual_object", "prior_trust", "trust_config_hash",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{csv_path}: missing columns {sorted(missing)}")

    events = event_map(json.loads(events_path.read_text(encoding="utf-8")))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    experiment = summary.get("experiment", {})
    contact = events.get("contact_onset", {}).get("system_time", math.nan)
    if not np.isfinite(contact):
        contact = experiment.get("event_times", {}).get("contact_onset", math.nan)
    contact = float(contact)

    t = pd.to_numeric(df["system_time"], errors="coerce").to_numpy(float)
    f = pd.to_numeric(df["F_ext_mag"], errors="coerce").to_numpy(float)
    k = pd.to_numeric(df["K_trans"], errors="coerce").to_numpy(float)
    trust = pd.to_numeric(df["prior_trust"], errors="coerce").to_numpy(float)
    threshold_values = pd.to_numeric(df["force_threshold"], errors="coerce")
    threshold = float(threshold_values[np.isfinite(threshold_values)].median())
    rel = t - contact

    adaptive = np.isfinite(rel) & (rel >= 0.05) & (rel <= 0.80)
    initial = np.isfinite(rel) & (rel >= 0.0) & (rel <= 0.20)
    primary = integrate_excess(t[adaptive], f[adaptive], threshold)
    initial_peak = float(np.nanmax(f[initial])) if initial.any() else math.nan
    excess_duration = 0.0
    if adaptive.sum() >= 2:
        dt = np.diff(t[adaptive], prepend=t[adaptive][0])
        excess_duration = float(np.sum(dt[f[adaptive] > threshold]))

    trust_drop_indices = np.flatnonzero(np.isfinite(trust) & (trust < 1.0 - 1e-9))
    trust_drop_latency = (
        float(rel[trust_drop_indices[0]]) if len(trust_drop_indices) else math.nan
    )
    grasp_success_t = events.get("grasp_success", {}).get("system_time", math.nan)
    task_end = events.get("task_end")
    safety_stop = events.get("safety_stop")
    completed = task_end is not None
    task_success = bool(completed and task_end.get("success", True) and safety_stop is None)

    mode_info = summary.get("mode", {})
    participant = experiment.get("subject_id", "unknown")
    trial_id = experiment.get("trial_id", "unknown")
    actual_object = first_finite_text(df["actual_object"])
    condition = first_finite_text(df["condition_code"])
    raw_class = first_finite_text(df.get("raw_vision_class", pd.Series(dtype=str)))

    return {
        "trial_id": trial_id,
        "participant_id": participant,
        "actual_object": actual_object,
        "condition_code": condition,
        "prior_condition": mode_info.get("prior_condition"),
        "posterior_correction": mode_info.get("posterior_correction"),
        "config_hash": first_finite_text(df["trust_config_hash"], "missing"),
        "source_csv": str(csv_path.resolve()),
        "primary_excess_impulse_Ns_0p05_0p80": primary,
        "initial_peak_force_N_0_0p20": initial_peak,
        "excess_duration_s_0p05_0p80": excess_duration,
        "prior_trust_min": float(np.nanmin(trust)),
        "trust_drop_latency_s": trust_drop_latency,
        "stiffness_min_N_per_m": float(np.nanmin(k)),
        "stiffness_max_N_per_m": float(np.nanmax(k)),
        "stiffness_reduction_N_per_m": float(k[0] - np.nanmin(k)),
        "contact_to_grasp_success_s": (
            float(grasp_success_t) - contact
            if np.isfinite(grasp_success_t) and np.isfinite(contact) else math.nan
        ),
        "operation_time_s": experiment.get("operation_time_s", math.nan),
        "task_completed": int(completed),
        "task_success": int(task_success),
        "software_safety_stop": int(safety_stop is not None),
        "raw_vision_class": raw_class,
        "raw_vision_correct": int(raw_class.lower() == actual_object.lower()),
        "contact_event_present": int(np.isfinite(contact)),
        "override_event_present": int("posterior_override_start" in events),
        "stiffness_bounds_ok": int(np.nanmin(k) >= 50 - 1e-6 and np.nanmax(k) <= 200 + 1e-6),
        "trust_monotonic_ok": int(np.nanmax(np.diff(trust)) <= 1e-9),
    }


def holm(values: list[float]) -> list[float]:
    order = np.argsort(values)
    adjusted = np.empty(len(values), dtype=float)
    running = 0.0
    for rank, index in enumerate(order):
        candidate = (len(values) - rank) * values[index]
        running = max(running, candidate)
        adjusted[index] = min(running, 1.0)
    return adjusted.tolist()


def participant_sign_flip_p(values: np.ndarray) -> float:
    values = values[np.isfinite(values)]
    if len(values) == 0:
        return math.nan
    observed = abs(float(np.mean(values)))
    if len(values) <= 16:
        means = [
            abs(float(np.mean(values * np.asarray(signs))))
            for signs in itertools.product((-1.0, 1.0), repeat=len(values))
        ]
        return float((np.sum(np.asarray(means) >= observed - 1e-12)) / len(means))
    rng = np.random.default_rng(RNG_SEED)
    signs = rng.choice((-1.0, 1.0), size=(100000, len(values)))
    means = np.abs(np.mean(signs * values, axis=1))
    return float((np.sum(means >= observed) + 1) / (len(means) + 1))


def participant_bootstrap_ci(values: np.ndarray) -> tuple[float, float]:
    values = values[np.isfinite(values)]
    if len(values) < 2:
        return math.nan, math.nan
    rng = np.random.default_rng(RNG_SEED)
    samples = rng.choice(values, size=(20000, len(values)), replace=True).mean(axis=1)
    return tuple(np.quantile(samples, [0.025, 0.975]).tolist())


def contrast_table(metrics: pd.DataFrame, metric: str) -> pd.DataFrame:
    wide = metrics.pivot_table(
        index=["participant_id", "actual_object"],
        columns="condition_code", values=metric, aggfunc="first",
    ).dropna(subset=CONDITIONS)
    wide["W1-W0"] = wide["W1"] - wide["W0"]
    wide["C1-C0"] = wide["C1"] - wide["C0"]
    wide["interaction"] = wide["W1-W0"] - wide["C1-C0"]
    participant = wide.groupby(level="participant_id")[[
        "W1-W0", "C1-C0", "interaction"
    ]].mean()

    rows = []
    p_values = []
    for name in ("W1-W0", "C1-C0", "interaction"):
        values = participant[name].to_numpy(float)
        mean = float(np.mean(values))
        sd = float(np.std(values, ddof=1)) if len(values) > 1 else math.nan
        ci_low, ci_high = participant_bootstrap_ci(values)
        p_value = participant_sign_flip_p(values)
        p_values.append(p_value)
        rows.append({
            "metric": metric,
            "contrast": name,
            "n_participants": len(values),
            "n_participant_object_blocks": len(wide),
            "mean_difference": mean,
            "sd_participant_difference": sd,
            "dz": mean / sd if np.isfinite(sd) and sd > 0 else math.nan,
            "ci95_low_participant_bootstrap": ci_low,
            "ci95_high_participant_bootstrap": ci_high,
            "p_sign_flip": p_value,
        })
    adjusted = holm(p_values)
    for row, value in zip(rows, adjusted):
        row["p_holm"] = value
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument(
        "--output-dir", type=Path,
        default=Path("my_test/正宫/08_supplement_results"),
    )
    args = parser.parse_args()
    csv_files = sorted(args.data_dir.rglob("trust_experiment_*.csv"))
    if not csv_files:
        raise SystemExit(f"No trust_experiment CSV files found in {args.data_dir}")

    metrics = pd.DataFrame([extract_trial(path) for path in csv_files])
    args.output_dir.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(
        args.output_dir / "trial_metrics_trust.csv", index=False,
        encoding="utf-8-sig",
    )
    balance = metrics.groupby(
        ["participant_id", "actual_object", "condition_code"]
    ).size().rename("n").reset_index()
    balance.to_csv(args.output_dir / "balance_audit.csv", index=False, encoding="utf-8-sig")
    mechanism = metrics[[
        "trial_id", "condition_code", "config_hash", "contact_event_present",
        "override_event_present", "stiffness_bounds_ok", "trust_monotonic_ok",
        "software_safety_stop", "raw_vision_correct",
    ]]
    mechanism.to_csv(
        args.output_dir / "mechanism_audit.csv", index=False,
        encoding="utf-8-sig",
    )

    primary = "primary_excess_impulse_Ns_0p05_0p80"
    contrasts = contrast_table(metrics, primary)
    contrasts.to_csv(
        args.output_dir / "predefined_contrasts.csv", index=False,
        encoding="utf-8-sig",
    )
    print(contrasts.to_string(index=False))


if __name__ == "__main__":
    main()
