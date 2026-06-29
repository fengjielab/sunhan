#!/usr/bin/env python3
"""Stage-aware metrics and plots for teleoperation experiment CSV files."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np


def _float(value, default=math.nan):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _column(rows: Sequence[Dict], name: str, default=math.nan) -> np.ndarray:
    return np.asarray([_float(row.get(name), default) for row in rows], dtype=float)


def _json_safe(value):
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, (float, np.floating)) and not np.isfinite(value):
        return None
    if isinstance(value, np.integer):
        return int(value)
    return value


def _event_times(rows: Sequence[Dict], time_key: str) -> Dict[str, float]:
    events: Dict[str, float] = {}
    for row in rows:
        t = _float(row.get(time_key))
        for name in str(row.get("event", "")).split("|"):
            name = name.strip()
            if name and name not in events and np.isfinite(t):
                events[name] = t
    return events


def _duration_by_phase(rows: Sequence[Dict], t: np.ndarray) -> Dict[str, float]:
    result: Dict[str, float] = {}
    if len(t) < 2:
        return result
    dt = np.diff(t, append=t[-1])
    finite_dt = dt[np.isfinite(dt) & (dt > 0)]
    fallback = float(np.median(finite_dt)) if finite_dt.size else 0.0
    dt[-1] = fallback
    for phase in sorted({str(row.get("phase", "")) for row in rows if row.get("phase")}):
        mask = np.asarray([str(row.get("phase", "")) == phase for row in rows])
        result[phase] = float(np.sum(dt[mask & np.isfinite(dt)]))
    return result


def _trajectory_length(rows: Sequence[Dict], mask: np.ndarray) -> float:
    names = ("omega_x", "omega_y", "omega_z")
    if not all(name in rows[0] for name in names):
        names = ("x", "y", "z")
    pos = np.column_stack([_column(rows, name) for name in names])
    pos = pos[mask & np.all(np.isfinite(pos), axis=1)]
    return float(np.sum(np.linalg.norm(np.diff(pos, axis=0), axis=1))) if len(pos) > 1 else math.nan


def _window_metrics(t: np.ndarray, force: np.ndarray, start: float,
                    duration: float, baseline: float, threshold: float) -> Dict:
    mask = (t >= start) & (t <= start + duration) & np.isfinite(force)
    tw, fw = t[mask], force[mask]
    prefix = f"contact_{duration:g}s"
    if len(fw) < 2:
        return {f"{prefix}_valid": False}
    excess = np.maximum(fw - baseline, 0.0)
    impulse = float(np.trapezoid(excess, tw))
    gradient = np.gradient(fw, tw)
    above = fw > threshold
    above_duration = float(np.trapezoid(above.astype(float), tw))
    return {
        f"{prefix}_valid": True,
        f"{prefix}_impulse_Ns": impulse,
        f"{prefix}_F95_N": float(np.percentile(fw, 95)),
        f"{prefix}_peak_N": float(np.max(fw)),
        f"{prefix}_force_rate95_Ns": float(np.percentile(np.abs(gradient), 95)),
        f"{prefix}_above_threshold_s": above_duration,
        f"{prefix}_n_samples": int(len(fw)),
    }


def _settling_time(t: np.ndarray, force: np.ndarray, contact: float) -> float:
    """Time until force remains near its late-contact median for 0.3 s."""
    mask = (t >= contact) & (t <= contact + 3.0) & np.isfinite(force)
    tw, fw = t[mask], force[mask]
    if len(fw) < 10:
        return math.nan
    tail = fw[tw >= max(contact, tw[-1] - 0.5)]
    target = float(np.median(tail))
    tolerance = max(0.5, 0.15 * max(abs(target), 1.0))
    for i in range(len(tw)):
        j = int(np.searchsorted(tw, tw[i] + 0.3, side="left"))
        if j > i + 1 and np.all(np.abs(fw[i:j] - target) <= tolerance):
            return float(tw[i] - contact)
    return math.nan


def analyze_csv(csv_path: str, output_dir: Optional[str] = None,
                save_plot: bool = True) -> Dict:
    path = Path(csv_path)
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) < 2:
        raise ValueError(f"CSV数据不足: {path}")

    is_segmented = "system_time" in rows[0] and "phase" in rows[0]
    time_key = "system_time" if is_segmented else "time"
    t = _column(rows, time_key)
    force = _column(rows, "F_ext_mag")
    events = _event_times(rows, time_key) if is_segmented else {}
    mode = rows[0].get("mode") or path.stem.split("_")[0]
    finite_force = force[np.isfinite(force)]

    metrics = {
        "schema_version": 2 if is_segmented else 1,
        "data_status": "segmented" if is_segmented else "legacy_unsegmented",
        "source_csv": str(path),
        "mode": mode,
        "subject_id": rows[0].get("subject_id", "unknown"),
        "object_id": rows[0].get("object_id", "unknown"),
        "trial_id": rows[0].get("trial_id", "unknown"),
        "n_samples": len(rows),
        "recording_duration_s": float(t[-1] - t[0]),
        "force_peak_full_trial_N": float(np.max(finite_force)) if finite_force.size else math.nan,
        "force_mean_full_trial_N": float(np.mean(finite_force)) if finite_force.size else math.nan,
    }

    if is_segmented:
        task_start = events.get("task_start", math.nan)
        task_end = events.get("task_end", math.nan)
        first_frame = events.get("first_frame", math.nan)
        vision_lock = events.get("vision_lock", math.nan)
        contact = events.get("contact_onset", math.nan)
        operation_mask = ((t >= task_start) & (t <= task_end)) if (
            np.isfinite(task_start) and np.isfinite(task_end)
        ) else np.zeros(len(t), dtype=bool)
        baseline_vals = _column(rows, "force_baseline_mean")
        threshold_vals = _column(rows, "force_threshold")
        baseline = float(baseline_vals[np.isfinite(baseline_vals)][-1]) if np.any(np.isfinite(baseline_vals)) else 0.0
        threshold = float(threshold_vals[np.isfinite(threshold_vals)][-1]) if np.any(np.isfinite(threshold_vals)) else max(1.0, baseline)
        metrics.update({
            "completed": "task_end" in events,
            "recognition_time_s": vision_lock - first_frame if np.isfinite(first_frame) and np.isfinite(vision_lock) else math.nan,
            "operation_time_s": task_end - task_start if np.isfinite(task_start) and np.isfinite(task_end) else math.nan,
            "phase_duration_s": _duration_by_phase(rows, t),
            "operation_trajectory_length_m": _trajectory_length(rows, operation_mask),
            "contact_onset_system_time_s": contact,
            "force_baseline_mean_N": baseline,
            "force_threshold_N": threshold,
            "contact_settling_time_s": _settling_time(t, force, contact) if np.isfinite(contact) else math.nan,
            "events": events,
        })
        if np.isfinite(contact):
            metrics.update(_window_metrics(t, force, contact, 0.5, baseline, threshold))
            metrics.update(_window_metrics(t, force, contact, 1.0, baseline, threshold))
            K = _column(rows, "K_trans")
            pre = (t >= contact - 0.2) & (t < contact) & np.isfinite(K)
            metrics["precontact_K_trans_median_Nm"] = float(np.median(K[pre])) if np.any(pre) else math.nan
    else:
        mask = np.isfinite(t)
        metrics["legacy_trajectory_length_m"] = _trajectory_length(rows, mask)
        metrics["note"] = "旧数据缺少事件与阶段，不参与分阶段统计。"

    out_dir = Path(output_dir) if output_dir else path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = out_dir / f"{path.stem}_metrics.json"
    with metrics_path.open("w", encoding="utf-8") as f:
        json.dump(_json_safe(metrics), f, ensure_ascii=False, indent=2, allow_nan=False)
    metrics["metrics_json"] = str(metrics_path)

    if save_plot and is_segmented:
        plot_path = out_dir / f"{path.stem}_phases.png"
        _plot(rows, t, force, events, plot_path)
        metrics["phase_plot"] = str(plot_path)
    return metrics


def _plot(rows: Sequence[Dict], t: np.ndarray, force: np.ndarray,
          events: Dict[str, float], output: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    K = _column(rows, "K_trans")
    delta = _column(rows, "fusion_delta_K")
    phases = [str(row.get("phase", "")) for row in rows]
    phase_names = [p for p in ("PREP", "READY", "APPROACH", "GRASP", "TRANSPORT", "RELEASE", "COMPLETE") if p in phases]
    phase_ids = np.asarray([phase_names.index(p) if p in phase_names else math.nan for p in phases])
    fig, axes = plt.subplots(3, 1, figsize=(10, 7), sharex=True)
    axes[0].plot(t, force, color="#d62728", lw=1, label="|F_ext|")
    threshold = _column(rows, "force_threshold")
    if np.any(np.isfinite(threshold)):
        axes[0].plot(t, threshold, "--", color="gray", lw=1, label="contact threshold")
    axes[0].set_ylabel("Force (N)")
    axes[0].legend(loc="upper right")
    axes[1].plot(t, K, color="#1f77b4", lw=1.2, label="K_trans")
    if np.any(np.isfinite(delta)):
        axes[1].plot(t, delta, color="#9467bd", lw=1, label="delta K")
    axes[1].set_ylabel("Stiffness")
    axes[1].legend(loc="upper right")
    axes[2].step(t, phase_ids, where="post", color="#2ca02c")
    axes[2].set_yticks(range(len(phase_names)), phase_names)
    axes[2].set_ylabel("Phase")
    axes[2].set_xlabel("System time (s)")
    for ax in axes:
        for name in ("task_start", "contact_onset", "grasp_start", "grasp_success", "release_start", "task_end"):
            if name in events:
                ax.axvline(events[name], color="black", alpha=0.22, lw=0.8)
        ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="分阶段遥操作指标分析")
    parser.add_argument("--load", nargs="+", required=True, help="一个或多个轨迹CSV")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--no-plot", action="store_true")
    args = parser.parse_args()
    for filename in args.load:
        result = analyze_csv(filename, args.output_dir, save_plot=not args.no_plot)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=True))


if __name__ == "__main__":
    main()
