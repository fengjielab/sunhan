from __future__ import annotations

import hashlib
import itertools
import json
import math
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats


ROOT = Path(r"F:\sun\sunhan\my_test")
PAPER_ROOT = ROOT / "paper2_sci"
RAW_ROOT = ROOT / "data" / "ral_date"
OUT = PAPER_ROOT / "03_clean_analysis"
FIG = OUT / "figures"
TAB = OUT / "tables"
SOURCE_MANIFEST = PAPER_ROOT / "02_audit" / "trial_manifest_186.csv"
OLD_METRICS = PAPER_ROOT / "03_processed_data" / "trial_metrics_main_180.csv"
COLLECTION_COMMIT = "09c13e0b679905f14f770d820af00841546cb4cc"

MODE_ORDER = ["default", "force_only", "vision", "vision_force"]
MODE_CODE = {"default": "A", "force_only": "G", "vision": "E", "vision_force": "F"}
MODE_COLORS = {
    "default": "#4D4D4D",
    "force_only": "#7A5195",
    "vision": "#2F6BFF",
    "vision_force": "#00A6A6",
}
GRID = np.round(np.arange(-0.50, 1.5001, 0.01), 2)

# User-confirmed on 2026-08-09: these six 20260729 records are known erroneous
# records. Their paired 20260730 records are valid replacements.
INVALID_CONFIRMED_RECORDS = {
    "hard|P01|第二组实验|vision_force": "20260729_172153",
    "soft|P01|第一组实验|vision": "20260729_145520",
    "soft|P01|第一组实验|vision_force": "20260729_150205",
    "soft|P03|第九组实验|vision": "20260729_154853",
    "soft|P03|第九组实验|vision_force": "20260729_154714",
    "soft|P03|第八组实验|vision": "20260729_155013",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def event_lookup(payload: dict, name: str) -> dict:
    for item in payload.get("events", []):
        if item.get("event") == name:
            return dict(item)
    return {}


def event_time(payload: dict, name: str) -> float:
    item = event_lookup(payload, name)
    value = item.get("system_time")
    return float(value) if value is not None else float("nan")


def first_active_time(df: pd.DataFrame, column: str) -> float:
    if column not in df:
        return float("nan")
    active = pd.to_numeric(df[column], errors="coerce").fillna(0).to_numpy(float)
    idx = np.flatnonzero(active > 0)
    if not len(idx):
        return float("nan")
    return float(pd.to_numeric(df["system_time"], errors="coerce").to_numpy(float)[idx[0]])


def first_active_index(df: pd.DataFrame, column: str) -> int | None:
    if column not in df:
        return None
    active = pd.to_numeric(df[column], errors="coerce").fillna(0).to_numpy(float)
    idx = np.flatnonzero(active > 0)
    return int(idx[0]) if len(idx) else None


def integrate_window(t: np.ndarray, y: np.ndarray, lo: float, hi: float) -> float:
    mask = np.isfinite(t) & np.isfinite(y) & (t >= lo) & (t <= hi)
    if mask.sum() < 2:
        return float("nan")
    return float(np.trapezoid(y[mask], t[mask]))


def mean_ci_t(values: np.ndarray) -> tuple[float, float, float]:
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    mean = float(np.mean(x))
    if len(x) < 2:
        return mean, float("nan"), float("nan")
    half = float(stats.t.ppf(0.975, len(x) - 1) * np.std(x, ddof=1) / np.sqrt(len(x)))
    return mean, mean - half, mean + half


def exact_sign_flip_p(diff: np.ndarray) -> float:
    x = np.asarray(diff, dtype=float)
    x = x[np.isfinite(x)]
    if not len(x):
        return float("nan")
    observed = abs(float(np.mean(x)))
    perm = []
    for signs in itertools.product((-1.0, 1.0), repeat=len(x)):
        perm.append(abs(float(np.mean(x * np.asarray(signs)))))
    perm = np.asarray(perm)
    return float(np.mean(perm >= observed - 1e-15))


def holm(pvalues: pd.Series) -> pd.Series:
    p = pvalues.to_numpy(float)
    out = np.full(len(p), np.nan)
    valid = np.flatnonzero(np.isfinite(p))
    if not len(valid):
        return pd.Series(out, index=pvalues.index)
    order = valid[np.argsort(p[valid])]
    running = 0.0
    m = len(order)
    for rank, idx in enumerate(order):
        adjusted = min(1.0, (m - rank) * p[idx])
        running = max(running, adjusted)
        out[idx] = running
    return pd.Series(out, index=pvalues.index)


def build_master_manifest() -> tuple[pd.DataFrame, pd.DataFrame]:
    source = pd.read_csv(SOURCE_MANIFEST, dtype=str).fillna("")
    if len(source) != 186 or source["trial_key"].nunique() != 180:
        raise RuntimeError("Source manifest is not the expected 186-record/180-key dataset")

    rows = []
    audit_rows = []
    for row in source.to_dict("records"):
        key = row["trial_key"]
        timestamp = row["timestamp"]
        duplicate_count = int(row["duplicate_count"])
        if key in INVALID_CONFIRMED_RECORDS and timestamp == INVALID_CONFIRMED_RECORDS[key]:
            validity = "user_confirmed_error"
            role = "excluded_known_error"
            include = 0
            reason = "User confirmed the 20260729 record was erroneous"
        elif key in INVALID_CONFIRMED_RECORDS:
            validity = "valid_replacement"
            role = "main_valid_replacement"
            include = 1
            reason = "20260730 valid replacement for user-confirmed erroneous record"
        else:
            validity = "normal_valid"
            role = "main_unique"
            include = 1
            reason = "Only valid record for trial key"

        paths = {
            "csv": RAW_ROOT / row["csv_source"],
            "events": RAW_ROOT / row["events_source"],
            "summary": RAW_ROOT / row["summary_source"],
        }
        exists = {name: path.is_file() for name, path in paths.items()}
        hashes = {name: sha256(path) if exists[name] else "" for name, path in paths.items()}
        hash_match = {
            "csv": hashes["csv"] == row["csv_sha256"],
            "events": hashes["events"] == row["events_sha256"],
            "summary": hashes["summary"] == row["summary_sha256"],
        }
        record_id = f"{key}|{timestamp}"
        master = {
            "record_id": record_id,
            "trial_key": key,
            "participant": row["participant"],
            "material": row["material"],
            "block": row["block"],
            "mode": row["mode"],
            "timestamp": timestamp,
            "duplicate_count": duplicate_count,
            "duplicate_rank": int(row["duplicate_rank"]),
            "record_validity": validity,
            "analysis_role": role,
            "included_main_clean": include,
            "selection_reason": reason,
            "csv_source": row["csv_source"],
            "events_source": row["events_source"],
            "summary_source": row["summary_source"],
            "csv_sha256": row["csv_sha256"],
            "events_sha256": row["events_sha256"],
            "summary_sha256": row["summary_sha256"],
            "collection_code_commit": COLLECTION_COMMIT,
        }
        rows.append(master)
        audit_rows.append(
            {
                **master,
                "csv_exists": int(exists["csv"]),
                "events_exists": int(exists["events"]),
                "summary_exists": int(exists["summary"]),
                "csv_hash_verified": int(hash_match["csv"]),
                "events_hash_verified": int(hash_match["events"]),
                "summary_hash_verified": int(hash_match["summary"]),
                "all_triplet_files_verified": int(all(exists.values()) and all(hash_match.values())),
            }
        )

    master = pd.DataFrame(rows).sort_values(
        ["participant", "material", "block", "mode", "timestamp"]
    )
    audit = pd.DataFrame(audit_rows).sort_values(
        ["participant", "material", "block", "mode", "timestamp"]
    )
    selected = master[master["included_main_clean"].eq(1)]
    if len(selected) != 180 or selected["trial_key"].nunique() != 180:
        raise RuntimeError("Clean main selection is not one record per 180 trial keys")
    if (audit["all_triplet_files_verified"] != 1).any():
        raise RuntimeError("At least one source triplet failed existence/hash verification")
    if (master["analysis_role"].eq("excluded_known_error").sum() != 6 or
            master["analysis_role"].eq("main_valid_replacement").sum() != 6):
        raise RuntimeError("Expected exactly six excluded errors and six valid replacements")
    return master, audit


def load_one_trial(row: pd.Series) -> tuple[dict, pd.DataFrame, dict]:
    csv_path = RAW_ROOT / row["csv_source"]
    events_path = RAW_ROOT / row["events_source"]
    summary_path = RAW_ROOT / row["summary_source"]
    events = json.loads(events_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    usecols = [
        "system_time", "operation_time", "F_ext_mag", "K_trans", "control_dt",
        "vision_locked", "fusion_active", "force_adapt_active", "fusion_delta_K",
        "force_adapt_delta_K", "force_adapt_ratio", "force_baseline_mean",
        "force_baseline_std", "force_threshold",
    ]
    raw = pd.read_csv(csv_path, usecols=lambda c: c in usecols)
    for col in usecols:
        if col not in raw:
            raw[col] = np.nan
        raw[col] = pd.to_numeric(raw[col], errors="coerce")
    original_time = raw["system_time"].to_numpy(float)
    time_monotonic = int(np.all(np.diff(original_time[np.isfinite(original_time)]) >= 0))
    raw = raw.dropna(subset=["system_time", "F_ext_mag", "K_trans"]).sort_values("system_time")
    t = raw["system_time"].to_numpy(float)
    force = raw["F_ext_mag"].to_numpy(float)
    stiffness = raw["K_trans"].to_numpy(float)

    task_start = event_time(events, "task_start")
    baseline_ready = event_time(events, "force_baseline_ready")
    contact = event_time(events, "contact_onset")
    vision_lock = event_time(events, "vision_lock")
    task_end = event_time(events, "task_end")
    grasp_start = event_time(events, "grasp_start")
    grasp_success = event_time(events, "grasp_success")
    release_start = event_time(events, "release_start")
    if not np.isfinite(task_start) or not np.isfinite(contact):
        raise RuntimeError(f"Missing task/contact event for {row['record_id']}")

    threshold = events.get("force_threshold_N")
    threshold = float(threshold) if threshold is not None else float("nan")
    baseline_mean = events.get("force_baseline_mean_N")
    baseline_std = events.get("force_baseline_std_N")
    baseline_mean = float(baseline_mean) if baseline_mean is not None else float("nan")
    baseline_std = float(baseline_std) if baseline_std is not None else float("nan")
    if not np.isfinite(threshold):
        pre = force[(t >= contact - 0.5) & (t < contact)]
        threshold = max(1.0, float(np.nanmean(pre) + 3 * np.nanstd(pre)))
    rel = t - contact
    excess = np.maximum(force - threshold, 0.0)
    init = (rel >= 0.0) & (rel <= 0.2)

    mode = row["mode"]
    if mode == "vision_force":
        force_activation = first_active_time(raw, "fusion_active")
        activation_column = "fusion_active"
    elif mode == "force_only":
        force_activation = first_active_time(raw, "force_adapt_active")
        activation_column = "force_adapt_active"
    else:
        force_activation = float("nan")
        activation_column = "not_applicable"
    activation_index = first_active_index(raw, activation_column)
    force_at_activation = (
        float(raw["F_ext_mag"].iloc[activation_index]) if activation_index is not None else float("nan")
    )
    vision_activation_csv = first_active_time(raw, "vision_locked")

    completed = bool(events.get("completed", False))
    grasp_event = event_lookup(events, "grasp_success")
    end_event = event_lookup(events, "task_end")
    grasp_flag = bool(grasp_event.get("grasp_success", completed))
    end_flag = bool(end_event.get("success", completed))
    success = int(completed and grasp_flag and end_flag)

    operation_event = task_end - task_start if np.isfinite(task_end) else float("nan")
    metric = {
        "record_id": row["record_id"],
        "trial_key": row["trial_key"],
        "participant": row["participant"],
        "material": row["material"],
        "block": row["block"],
        "block_id": "|".join([row["participant"], row["material"], row["block"]]),
        "mode": mode,
        "mode_code": MODE_CODE[mode],
        "timestamp": row["timestamp"],
        "analysis_role": row["analysis_role"],
        "csv_source": row["csv_source"],
        "events_source": row["events_source"],
        "summary_source": row["summary_source"],
        "baseline_force_mean_N": baseline_mean,
        "baseline_force_std_N": baseline_std,
        "force_threshold_N": threshold,
        "baseline_corrected_excess_force_impulse_Ns_0p2_1p0": integrate_window(rel, excess, 0.2, 1.0),
        "primary_excess_impulse_Ns_0p2_1p0": integrate_window(rel, excess, 0.2, 1.0),
        "initial_peak_force_N_0_0p2": float(np.nanmax(force[init])) if init.any() else float("nan"),
        "initial_peak_excess_force_N_0_0p2": float(np.nanmax(excess[init])) if init.any() else float("nan"),
        "approach_time_s": contact - task_start,
        "total_task_time_s": operation_event,
        "operation_time_s": operation_event,
        "success": success,
        "task_start_system_s": task_start,
        "force_baseline_ready_system_s": baseline_ready,
        "contact_onset_system_s": contact,
        "vision_lock_system_s": vision_lock,
        "force_activation_system_s": force_activation,
        "vision_lock_minus_task_start_s": vision_lock - task_start if np.isfinite(vision_lock) else float("nan"),
        "vision_lock_minus_contact_s": vision_lock - contact if np.isfinite(vision_lock) else float("nan"),
        "force_activation_minus_task_start_s": force_activation - task_start if np.isfinite(force_activation) else float("nan"),
        "force_activation_minus_contact_s": force_activation - contact if np.isfinite(force_activation) else float("nan"),
        "grasp_start_system_s": grasp_start,
        "grasp_success_system_s": grasp_success,
        "release_start_system_s": release_start,
        "task_end_system_s": task_end,
        "activation_flag_column": activation_column,
        "vision_activation_csv_system_s": vision_activation_csv,
    }

    dt = raw["control_dt"].to_numpy(float)
    valid_dt = dt[np.isfinite(dt) & (dt >= 0)]
    timing = {
        "record_id": row["record_id"],
        "trial_key": row["trial_key"],
        "participant": row["participant"],
        "material": row["material"],
        "block": row["block"],
        "mode": mode,
        "mode_code": MODE_CODE[mode],
        "timestamp": row["timestamp"],
        "analysis_role": row["analysis_role"],
        "wall_start_unix_s": float(events.get("started_at_unix", float("nan"))),
        "timeline_clock": "time.perf_counter relative to ExperimentTimeline.start_perf",
        "wall_clock_role": "metadata only",
        "ros_timestamp_available": 0,
        "csv_first_system_s": float(t[0]),
        "csv_last_system_s": float(t[-1]),
        "csv_system_time_monotonic": time_monotonic,
        "task_start_system_s": task_start,
        "contact_onset_system_s": contact,
        "vision_lock_system_s": vision_lock,
        "vision_lock_csv_system_s": vision_activation_csv,
        "force_activation_system_s": force_activation,
        "force_activation_flag_column": activation_column,
        "vision_lock_minus_task_start_s": metric["vision_lock_minus_task_start_s"],
        "vision_lock_minus_contact_s": metric["vision_lock_minus_contact_s"],
        "force_activation_minus_task_start_s": metric["force_activation_minus_task_start_s"],
        "force_activation_minus_contact_s": metric["force_activation_minus_contact_s"],
        "force_activation_minus_baseline_ready_s": force_activation - baseline_ready if np.isfinite(force_activation) and np.isfinite(baseline_ready) else float("nan"),
        "raw_estimated_force_at_activation_N": force_at_activation,
        "trial_baseline_force_mean_N": baseline_mean,
        "contact_detection_threshold_N": threshold,
        "g_fixed_adaptation_deadband_N": 1.0 if mode == "force_only" else float("nan"),
        "vision_event_csv_difference_s": vision_activation_csv - vision_lock if np.isfinite(vision_activation_csv) and np.isfinite(vision_lock) else float("nan"),
        "control_dt_median_s": float(np.nanmedian(valid_dt)) if len(valid_dt) else float("nan"),
        "control_dt_p95_s": float(np.nanquantile(valid_dt, 0.95)) if len(valid_dt) else float("nan"),
        "control_dt_p99_s": float(np.nanquantile(valid_dt, 0.99)) if len(valid_dt) else float("nan"),
        "control_dt_max_s": float(np.nanmax(valid_dt)) if len(valid_dt) else float("nan"),
        "control_dt_gt20ms_fraction": float(np.mean(valid_dt > 0.02)) if len(valid_dt) else float("nan"),
        "control_dt_gt50ms_fraction": float(np.mean(valid_dt > 0.05)) if len(valid_dt) else float("nan"),
        "event_times_within_csv_range": int(
            all(t[0] - 0.01 <= v <= t[-1] + 0.01 for v in [task_start, contact, task_end] if np.isfinite(v))
        ),
    }

    unique_t, unique_idx = np.unique(rel, return_index=True)
    aligned = pd.DataFrame(
        {
            "record_id": row["record_id"],
            "trial_key": row["trial_key"],
            "participant": row["participant"],
            "material": row["material"],
            "block": row["block"],
            "mode": mode,
            "mode_code": MODE_CODE[mode],
            "t_rel_contact_s": GRID,
            "force_estimated_N": np.interp(GRID, unique_t, force[unique_idx], left=np.nan, right=np.nan),
            "excess_force_N": np.interp(GRID, unique_t, excess[unique_idx], left=np.nan, right=np.nan),
            "stiffness_trans_N_m": np.interp(GRID, unique_t, stiffness[unique_idx], left=np.nan, right=np.nan),
        }
    )
    return metric, aligned, timing


def participant_statistics(metrics: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    metric_cols = [
        "primary_excess_impulse_Ns_0p2_1p0",
        "initial_peak_force_N_0_0p2",
        "approach_time_s",
        "total_task_time_s",
        "success",
    ]
    participant = (
        metrics.groupby(["participant", "mode", "mode_code"], as_index=False)[metric_cols]
        .mean()
        .sort_values(["participant", "mode"])
    )
    comparisons = [
        ("E-A", "vision", "default"),
        ("G-A", "force_only", "default"),
        ("F-E", "vision_force", "vision"),
        ("F-G", "vision_force", "force_only"),
    ]
    infer_metrics = metric_cols[:-1]
    rows = []
    lopo_rows = []
    for metric_name in infer_metrics:
        wide = participant.pivot(index="participant", columns="mode", values=metric_name)
        for label, mode2, mode1 in comparisons:
            pair = wide[[mode1, mode2]].dropna()
            diff = (pair[mode2] - pair[mode1]).to_numpy(float)
            estimate, low, high = mean_ci_t(diff)
            t_result = stats.ttest_1samp(diff, 0.0)
            try:
                wilcoxon_p = float(stats.wilcoxon(diff, alternative="two-sided", method="exact").pvalue)
            except ValueError:
                wilcoxon_p = 1.0
            rows.append(
                {
                    "metric": metric_name,
                    "contrast": label,
                    "difference_definition": f"{MODE_CODE[mode2]} minus {MODE_CODE[mode1]}",
                    "n_participants": len(diff),
                    "raw_mean_difference": estimate,
                    "ci95_low": low,
                    "ci95_high": high,
                    "paired_t_statistic": float(t_result.statistic),
                    "paired_t_p": float(t_result.pvalue),
                    "exact_sign_flip_p": exact_sign_flip_p(diff),
                    "wilcoxon_p": wilcoxon_p,
                    "participant_differences": ";".join(f"{idx}:{value:.12g}" for idx, value in zip(pair.index, diff)),
                }
            )
            full_mean = estimate
            for left_out in pair.index:
                kept = pair.drop(index=left_out)
                kept_diff = (kept[mode2] - kept[mode1]).to_numpy(float)
                lopo_mean, lopo_low, lopo_high = mean_ci_t(kept_diff)
                lopo_rows.append(
                    {
                        "metric": metric_name,
                        "contrast": label,
                        "left_out_participant": left_out,
                        "n_remaining": len(kept_diff),
                        "full_sample_mean_difference": full_mean,
                        "lopo_mean_difference": lopo_mean,
                        "lopo_ci95_low": lopo_low,
                        "lopo_ci95_high": lopo_high,
                        "same_direction_as_full": int(np.sign(lopo_mean) == np.sign(full_mean)),
                    }
                )
    summary = pd.DataFrame(rows)
    for metric_name, idx in summary.groupby("metric").groups.items():
        summary.loc[idx, "paired_t_p_holm"] = holm(summary.loc[idx, "paired_t_p"])
        summary.loc[idx, "exact_sign_flip_p_holm"] = holm(summary.loc[idx, "exact_sign_flip_p"])
        summary.loc[idx, "wilcoxon_p_holm"] = holm(summary.loc[idx, "wilcoxon_p"])
    return participant, summary, pd.DataFrame(lopo_rows)


def aligned_summary(aligned: pd.DataFrame) -> pd.DataFrame:
    per_participant = (
        aligned.groupby(["participant", "mode", "mode_code", "t_rel_contact_s"], as_index=False)
        [["force_estimated_N", "excess_force_N", "stiffness_trans_N_m"]]
        .mean()
    )
    rows = []
    for keys, group in per_participant.groupby(["mode", "mode_code", "t_rel_contact_s"]):
        mode, code, time = keys
        row = {"mode": mode, "mode_code": code, "t_rel_contact_s": time, "n_participants": group["participant"].nunique()}
        for col in ["force_estimated_N", "excess_force_N", "stiffness_trans_N_m"]:
            mean, low, high = mean_ci_t(group[col].to_numpy(float))
            row[f"{col}_mean"] = mean
            row[f"{col}_ci95_low"] = low
            row[f"{col}_ci95_high"] = high
        rows.append(row)
    return pd.DataFrame(rows)


def mode_descriptives(metrics: pd.DataFrame, participant: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "primary_excess_impulse_Ns_0p2_1p0", "initial_peak_force_N_0_0p2",
        "approach_time_s", "total_task_time_s", "success",
    ]
    rows = []
    for mode in MODE_ORDER:
        trial_group = metrics[metrics["mode"].eq(mode)]
        part_group = participant[participant["mode"].eq(mode)]
        for col in cols:
            rows.append(
                {
                    "mode": mode,
                    "mode_code": MODE_CODE[mode],
                    "metric": col,
                    "n_trials": len(trial_group),
                    "trial_mean": trial_group[col].mean(),
                    "trial_sd": trial_group[col].std(ddof=1),
                    "n_participants": len(part_group),
                    "participant_mean": part_group[col].mean(),
                    "participant_sd": part_group[col].std(ddof=1),
                }
            )
    return pd.DataFrame(rows)


def code_and_timing_validation(timing: pd.DataFrame, metrics: pd.DataFrame) -> pd.DataFrame:
    code = subprocess.run(
        ["git", "-C", str(ROOT.parent), "show", f"{COLLECTION_COMMIT}:my_test/interactive_teleop.py"],
        check=True, capture_output=True, text=True, encoding="utf-8",
    ).stdout
    protocol = subprocess.run(
        ["git", "-C", str(ROOT.parent), "show", f"{COLLECTION_COMMIT}:my_test/experiment_protocol.py"],
        check=True, capture_output=True, text=True, encoding="utf-8",
    ).stdout
    checks = {
        "run_assigns_wall_now": "now = time.time()" in code,
        "f_passes_wall_now": "self._update_vision_force_fusion(now)" in code,
        "f_gate_calls_timeline_system_time": "self._timeline.system_time(now) - contact_t < FUSION_CONTACT_DELAY_S" in code,
        "timeline_start_uses_perf_counter": "self.start_perf = time.perf_counter()" in protocol,
        "timeline_system_time_subtracts_start_perf": "return (time.perf_counter() if now is None else now) - self.start_perf" in protocol,
        "g_uses_raw_force_norm": "f_mag = float(np.linalg.norm(self._F_ext_current[:3]))" in code,
        "g_uses_deadband_without_contact_gate": "effective_force = max(f_mag - self._force_adapt_deadband, 0.0)" in code,
    }
    if not all(checks.values()):
        raise RuntimeError(f"Collection-code signature check failed: {checks}")

    f = timing[timing["mode"].eq("vision_force")]
    g = timing[timing["mode"].eq("force_only")]
    f_delta = f["force_activation_minus_contact_s"].dropna()
    g_task = g["force_activation_minus_task_start_s"].dropna()
    g_contact = g["force_activation_minus_contact_s"].dropna()
    g_metrics = metrics[metrics["mode"].eq("force_only")]
    return pd.DataFrame(
        [
            {
                "mode": "F",
                "design_timing": "force fusion starts no earlier than contact_onset + 0.20 s",
                "code_actual_logic": "time.time() is passed into ExperimentTimeline.system_time(), which subtracts a time.perf_counter() origin; the mixed clock domains bypass the 0.20 s gate",
                "log_execution_summary": f"n={len(f)}; active={len(f_delta)}; median activation-contact={f_delta.median():.6f}s; min={f_delta.min():.6f}s; max={f_delta.max():.6f}s; before_0.20s={(f_delta < 0.2).sum()}",
                "design_code_logs_consistent": 0,
                "primary_cause": "mixed time.time/perf_counter clock domains",
            },
            {
                "mode": "G",
                "design_timing": "no contact gate in collection code; adaptation is driven directly by raw estimated force magnitude above 1 N",
                "code_actual_logic": "raw |F_ext| -> subtract 1 N deadband -> activate when ratio > 0; contact detector and baseline-corrected threshold are not consulted",
                "log_execution_summary": f"n={len(g)}; active={len(g_contact)}; before_task={(g_task < 0).sum()}; before_contact={(g_contact < 0).sum()}; at_or_after_contact={(g_contact >= 0).sum()}",
                "design_code_logs_consistent": 1,
                "primary_cause": f"raw-force baseline relative to fixed 1 N deadband; mean trial baseline={g_metrics['baseline_force_mean_N'].mean():.6f} N",
            },
        ]
    )


def g_activation_cause_summary(timing: pd.DataFrame) -> pd.DataFrame:
    g = timing[timing["mode"].eq("force_only")].copy()
    n = len(g)
    measures = [
        ("activated_before_task_start", int((g["force_activation_minus_task_start_s"] < 0).sum()), "cumulative timing count"),
        ("activated_before_contact", int((g["force_activation_minus_contact_s"] < 0).sum()), "cumulative timing count"),
        ("activated_at_or_after_contact", int((g["force_activation_minus_contact_s"] >= 0).sum()), "complement of before-contact count"),
        ("activated_before_force_baseline_ready", int((g["force_activation_minus_baseline_ready_s"] < 0).sum()), "shows G runs during PREP"),
        ("trial_baseline_mean_above_1N", int((g["trial_baseline_force_mean_N"] > 1.0).sum()), "raw baseline often exceeds fixed deadband"),
        ("raw_force_at_activation_above_1N", int((g["raw_estimated_force_at_activation_N"] > 1.0).sum()), "direct activation condition"),
        ("activation_force_below_contact_threshold", int((g["raw_estimated_force_at_activation_N"] < g["contact_detection_threshold_N"]).sum()), "proves G can activate without contact detector"),
    ]
    rows = [
        {"measure": name, "count": count, "denominator": n, "proportion": count / n, "interpretation": note}
        for name, count, note in measures
    ]
    rows.extend(
        [
            {"measure": "cause_raw_force_baseline", "count": np.nan, "denominator": np.nan, "proportion": np.nan, "interpretation": "Supported: G uses uncorrected raw |F_ext|; baseline mean is not subtracted"},
            {"measure": "cause_fixed_1N_deadband", "count": np.nan, "denominator": np.nan, "proportion": np.nan, "interpretation": "Supported: activation occurs whenever raw |F_ext| exceeds the fixed 1 N deadband"},
            {"measure": "cause_contact_detection", "count": np.nan, "denominator": np.nan, "proportion": np.nan, "interpretation": "Contact detection is not used by the G update law"},
            {"measure": "cause_initialization", "count": np.nan, "denominator": np.nan, "proportion": np.nan, "interpretation": "Contributes: last-update is initialized to 0 and the update executes during PREP"},
            {"measure": "cause_timestamp", "count": np.nan, "denominator": np.nan, "proportion": np.nan, "interpretation": "No evidence that a mixed-clock comparison triggers G; its update interval uses wall-clock values consistently"},
        ]
    )
    return pd.DataFrame(rows)


def old_new_comparisons(new_metrics: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    old = pd.read_csv(OLD_METRICS)
    cols = [
        "primary_excess_impulse_Ns_0p2_1p0", "initial_peak_force_N_0_0p2",
        "operation_time_s", "success", "task_start_system_s", "contact_onset_system_s",
    ]
    old_small = old[["trial_key", "timestamp", *cols]].copy()
    old_small = old_small.rename(columns={c: f"old_{c}" for c in ["timestamp", *cols]})
    new_small = new_metrics[["trial_key", "timestamp", *cols]].copy()
    new_small = new_small.rename(columns={c: f"clean_{c}" for c in ["timestamp", *cols]})
    joined = old_small.merge(new_small, on="trial_key", how="outer", validate="one_to_one")
    for col in cols:
        joined[f"delta_{col}"] = joined[f"clean_{col}"] - joined[f"old_{col}"]
    joined["record_changed"] = (joined["old_timestamp"] != joined["clean_timestamp"]).astype(int)

    old_for_stats = old.copy()
    old_for_stats["mode_code"] = old_for_stats["mode"].map(MODE_CODE)
    old_for_stats["approach_time_s"] = old_for_stats["contact_onset_system_s"] - old_for_stats["task_start_system_s"]
    old_for_stats["total_task_time_s"] = old_for_stats["operation_time_s"]
    old_participant, old_stats, _ = participant_statistics(old_for_stats)
    del old_participant
    return joined, old_stats


def make_figures(participant: pd.DataFrame, timing: pd.DataFrame, summary: pd.DataFrame) -> None:
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
    metric = "primary_excess_impulse_Ns_0p2_1p0"
    wide = participant.pivot(index="participant", columns="mode", values=metric)[MODE_ORDER]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    x = np.arange(len(MODE_ORDER))
    for participant_id, row in wide.iterrows():
        ax.plot(x, row.to_numpy(float), color="#A0A0A0", alpha=0.75, marker="o", linewidth=1, label=participant_id)
    ax.plot(x, wide.mean().to_numpy(float), color="#111111", marker="D", linewidth=2.5, label="participant mean")
    ax.set_xticks(x, [MODE_CODE[m] for m in MODE_ORDER])
    ax.set_ylabel("Excess-force impulse (N·s), 0.2–1.0 s")
    ax.set_title("Participant-level primary outcome (n=5)")
    ax.grid(axis="y", alpha=0.2)
    ax.legend(ncol=3, fontsize=7)
    fig.tight_layout()
    fig.savefig(FIG / "participant_level_primary_outcome.png", dpi=220)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(9.0, 4.0), sharey=True)
    for ax, col, title in [
        (axes[0], "force_activation_minus_task_start_s", "Activation relative to task start"),
        (axes[1], "force_activation_minus_contact_s", "Activation relative to contact"),
    ]:
        for i, mode in enumerate(["force_only", "vision_force"]):
            vals = timing.loc[timing["mode"].eq(mode), col].dropna().to_numpy(float)
            jitter = np.linspace(-0.08, 0.08, len(vals))
            ax.scatter(np.full(len(vals), i) + jitter, vals, s=18, alpha=0.65, color=MODE_COLORS[mode])
            ax.plot([i - 0.15, i + 0.15], [np.median(vals)] * 2, color="black", linewidth=2)
        ax.axhline(0, color="#444444", linestyle="--", linewidth=1)
        if col.endswith("contact_s"):
            ax.axhline(0.2, color="#B22222", linestyle=":", linewidth=1.5)
        ax.set_xticks([0, 1], ["G", "F"])
        ax.set_title(title)
        ax.grid(axis="y", alpha=0.2)
    axes[0].set_ylabel("Time difference (s)")
    fig.tight_layout()
    fig.savefig(FIG / "force_activation_timing_audit.png", dpi=220)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.0))
    for mode in MODE_ORDER:
        g = summary[summary["mode"].eq(mode)]
        axes[0].plot(g["t_rel_contact_s"], g["excess_force_N_mean"], color=MODE_COLORS[mode], label=MODE_CODE[mode])
        axes[1].plot(g["t_rel_contact_s"], g["stiffness_trans_N_m_mean"], color=MODE_COLORS[mode], label=MODE_CODE[mode])
    for ax in axes:
        ax.axvline(0, color="#444444", linestyle="--", linewidth=1)
        ax.grid(alpha=0.2)
        ax.set_xlabel("Time from contact (s)")
    axes[0].set_ylabel("Excess estimated force (N)")
    axes[1].set_ylabel("Translational stiffness (N/m)")
    axes[0].set_title("Contact-aligned excess force")
    axes[1].set_title("Contact-aligned stiffness")
    axes[1].legend(ncol=4)
    fig.tight_layout()
    fig.savefig(FIG / "contact_aligned_force_stiffness_clean.png", dpi=220)
    plt.close(fig)


def main() -> None:
    for path in [OUT, FIG, TAB]:
        path.mkdir(parents=True, exist_ok=True)

    master, lineage_audit = build_master_manifest()
    selected = master[master["included_main_clean"].eq(1)].copy()
    selected = selected.sort_values(["participant", "material", "block", "mode"])

    metric_rows = []
    timing_rows = []
    aligned_rows = []
    for _, row in selected.iterrows():
        metric, aligned, timing = load_one_trial(row)
        metric_rows.append(metric)
        timing_rows.append(timing)
        aligned_rows.append(aligned)
    metrics = pd.DataFrame(metric_rows)
    timing = pd.DataFrame(timing_rows)
    aligned = pd.concat(aligned_rows, ignore_index=True)
    if len(metrics) != 180 or metrics["trial_key"].nunique() != 180:
        raise RuntimeError("Metric output is not 180 unique trials")

    participant, statistics_summary, lopo = participant_statistics(metrics)
    aligned_agg = aligned_summary(aligned)
    descriptives = mode_descriptives(metrics, participant)
    validation = code_and_timing_validation(timing, metrics)
    g_cause = g_activation_cause_summary(timing)
    old_new_trial, old_statistics = old_new_comparisons(metrics)
    new_stats_merge = statistics_summary.merge(
        old_statistics,
        on=["metric", "contrast"],
        how="left",
        suffixes=("_clean", "_old"),
    )

    master.to_csv(OUT / "master_trial_manifest.csv", index=False, encoding="utf-8-sig")
    lineage_audit.to_csv(OUT / "data_lineage_audit.csv", index=False, encoding="utf-8-sig")
    metrics.to_csv(OUT / "trial_level_metrics.csv", index=False, encoding="utf-8-sig")
    timing.to_csv(OUT / "timing_audit.csv", index=False, encoding="utf-8-sig")
    participant.to_csv(OUT / "participant_level_metrics.csv", index=False, encoding="utf-8-sig")
    statistics_summary.to_csv(OUT / "statistics_summary.csv", index=False, encoding="utf-8-sig")
    lopo.to_csv(OUT / "leave_one_participant_out.csv", index=False, encoding="utf-8-sig")
    aligned.to_csv(OUT / "contact_aligned_trajectories.csv", index=False, encoding="utf-8-sig")
    aligned_agg.to_csv(OUT / "contact_aligned_summary.csv", index=False, encoding="utf-8-sig")
    old_new_trial.to_csv(OUT / "old_new_trial_metric_comparison.csv", index=False, encoding="utf-8-sig")
    new_stats_merge.to_csv(OUT / "old_new_statistics_comparison.csv", index=False, encoding="utf-8-sig")

    descriptives.to_csv(TAB / "mode_descriptive_statistics.csv", index=False, encoding="utf-8-sig")
    statistics_summary[statistics_summary["metric"].eq("primary_excess_impulse_Ns_0p2_1p0")].to_csv(
        TAB / "primary_participant_level_statistics.csv", index=False, encoding="utf-8-sig"
    )
    validation.to_csv(TAB / "f_g_timing_validation.csv", index=False, encoding="utf-8-sig")
    g_cause.to_csv(TAB / "g_activation_cause_summary.csv", index=False, encoding="utf-8-sig")
    master[master["duplicate_count"].eq(2)].to_csv(
        TAB / "six_error_replacement_mapping_12_records.csv", index=False, encoding="utf-8-sig"
    )

    make_figures(participant, timing, aligned_agg)

    metadata = {
        "analysis_generated_at": pd.Timestamp.now(tz="Asia/Shanghai").isoformat(),
        "collection_code_commit": COLLECTION_COMMIT,
        "source_manifest": str(SOURCE_MANIFEST),
        "raw_root": str(RAW_ROOT),
        "records_discovered": int(len(master)),
        "unique_trial_keys": int(master["trial_key"].nunique()),
        "main_clean_trials": int(len(metrics)),
        "excluded_known_errors": int(master["analysis_role"].eq("excluded_known_error").sum()),
        "valid_replacements": int(master["analysis_role"].eq("main_valid_replacement").sum()),
        "participants": int(metrics["participant"].nunique()),
        "raw_triplets_hash_verified": int(lineage_audit["all_triplet_files_verified"].sum()),
    }
    (OUT / "analysis_run_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
