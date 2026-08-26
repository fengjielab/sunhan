from __future__ import annotations

import csv
import hashlib
import json
import math
import textwrap
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np
import pandas as pd
from scipy import linalg, optimize, stats


ROOT = Path(r"F:\sun\sunhan\my_test")
SOURCE = ROOT / "data" / "ral_date"
OUT = ROOT / "正宫"

DIRS = {
    "audit": OUT / "02_audit",
    "processed": OUT / "03_processed_data",
    "stats": OUT / "04_statistics",
    "figures": OUT / "05_figures",
    "manuscript": OUT / "06_manuscript",
}

MATERIAL_MAP = {
    "soft_date": "soft",
    "medium_date": "medium",
    "hard_date": "hard",
}
MATERIAL_ZH = {"soft": "软质", "medium": "中等", "hard": "硬质"}
MATERIAL_ORDER = ["soft", "medium", "hard"]
MODE_ORDER = ["default", "force_only", "vision", "vision_force"]
MODE_SHORT = {
    "default": "A 固定参数",
    "force_only": "G 纯力自适应",
    "vision": "E 视觉先验",
    "vision_force": "F 视觉-力融合",
}
MODE_COLORS = {
    "default": "#7F8C8D",
    "force_only": "#D97706",
    "vision": "#2563EB",
    "vision_force": "#059669",
}
PARTICIPANT_MAP = {
    "第一实验员": "P01",
    "第二实验员": "P02",
    "第三实验员": "P03",
    "第四实验员": "P04",
    "第五实验员": "P05",
}
ALIGN_GRID = np.round(np.arange(-0.5, 1.5001, 0.01), 2)
VISION_TRANSITION_S = 0.30
RNG = np.random.default_rng(20260804)


@dataclass
class Trial:
    summary_path: Path
    csv_path: Path
    events_path: Path
    material: str
    operator_raw: str
    participant: str
    block: str
    mode: str
    timestamp: str
    key: str
    payload: dict
    selected_latest: bool = False
    selected_earliest: bool = False
    duplicate_rank: int = 1
    duplicate_count: int = 1


def ensure_dirs() -> None:
    for path in DIRS.values():
        path.mkdir(parents=True, exist_ok=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def discover_trials() -> list[Trial]:
    trials: list[Trial] = []
    for summary_path in sorted(SOURCE.rglob("*_summary.json")):
        rel = summary_path.relative_to(SOURCE)
        if len(rel.parts) < 4:
            continue
        material_raw, operator_raw, block = rel.parts[:3]
        material = MATERIAL_MAP.get(material_raw)
        if material is None:
            continue
        payload = read_json(summary_path)
        mode_obj = payload.get("mode", {})
        mode = mode_obj.get("mode") if isinstance(mode_obj, dict) else str(mode_obj)
        if mode not in MODE_ORDER:
            continue
        participant = PARTICIPANT_MAP.get(operator_raw, operator_raw)
        timestamp = str(payload.get("timestamp") or summary_path.stem.split("_")[-2])
        stem = summary_path.name[: -len("_summary.json")]
        csv_path = summary_path.with_name(stem + ".csv")
        events_path = summary_path.with_name(stem + "_events.json")
        if not csv_path.exists() or not events_path.exists():
            raise FileNotFoundError(f"Missing companion file for {summary_path}")
        key = "|".join([material, participant, block, mode])
        trials.append(
            Trial(
                summary_path=summary_path,
                csv_path=csv_path,
                events_path=events_path,
                material=material,
                operator_raw=operator_raw,
                participant=participant,
                block=block,
                mode=mode,
                timestamp=timestamp,
                key=key,
                payload=payload,
            )
        )
    groups: dict[str, list[Trial]] = {}
    for t in trials:
        groups.setdefault(t.key, []).append(t)
    for group in groups.values():
        group.sort(key=lambda t: t.timestamp)
        for idx, t in enumerate(group, 1):
            t.duplicate_rank = idx
            t.duplicate_count = len(group)
            t.selected_earliest = idx == 1
            t.selected_latest = idx == len(group)
    return trials


def write_manifest(trials: list[Trial]) -> pd.DataFrame:
    rows = []
    selected = [t for t in trials if t.selected_earliest]
    if len(selected) != 180 or len(trials) not in {180, 186}:
        raise RuntimeError(f"Unexpected trial counts: all={len(trials)}, selected={len(selected)}")
    for t in trials:
        files = [t.csv_path, t.events_path, t.summary_path]
        rel_files = [str(p.relative_to(SOURCE)) for p in files]
        hashes = [sha256(p) for p in files]
        rows.append(
            {
                "trial_key": t.key,
                "material": t.material,
                "participant": t.participant,
                "operator_original": t.operator_raw,
                "block": t.block,
                "mode": t.mode,
                "timestamp": t.timestamp,
                "duplicate_count": t.duplicate_count,
                "duplicate_rank": t.duplicate_rank,
                "included_main_first_attempt": int(t.selected_earliest),
                "included_sensitivity_latest": int(t.selected_latest),
                "record_role": (
                    "first_attempt_selected"
                    if t.duplicate_count > 1 and t.selected_earliest
                    else "retest_sensitivity_only"
                    if t.duplicate_count > 1
                    else "unique_first_attempt"
                ),
                "csv_source": rel_files[0],
                "events_source": rel_files[1],
                "summary_source": rel_files[2],
                "csv_sha256": hashes[0],
                "events_sha256": hashes[1],
                "summary_sha256": hashes[2],
            }
        )
    manifest = pd.DataFrame(rows).sort_values(
        ["participant", "material", "block", "mode", "timestamp"]
    )
    manifest.to_csv(DIRS["audit"] / f"trial_manifest_{len(trials)}.csv", index=False, encoding="utf-8-sig")
    duplicate_audit = manifest[manifest["duplicate_count"] > 1]
    if not duplicate_audit.empty:
        duplicate_audit.to_csv(
            DIRS["audit"] / "duplicate_retest_audit_12_records.csv",
            index=False,
            encoding="utf-8-sig",
        )
    duplicate_note = (
        "- 重复单元格：6 个，每个含一条原记录和一条后续补测。\n"
        "- 主规则：同一单元格保留时间戳较早的首测，识别错误不因补测被替换。\n"
        "- 敏感性规则 1：改用时间戳较晚的补测。\n"
        "- 敏感性规则 2：全部 186 条记录在单元格内先求平均，再进行匹配比较。"
        if len(trials) == 186
        else "- 当前源目录已经由用户清理为严格平衡的 180 个唯一试次，不再存在重复补测记录。"
    )
    readme = f"""# 数据审计说明

- 原始目录：`{SOURCE}`（保持不变）
- 发现试次：{len(trials)}
- 主分析试次：{len(selected)}
- 设计：5 位操作者 × 3 类材料 × 3 个匹配组 × 4 种模式 = 180
{duplicate_note}
- 每个源文件均记录 SHA-256，用于验证复制完整性。
"""
    (DIRS["audit"] / "README.md").write_text(readme, encoding="utf-8")
    return manifest


def event_map(payload: dict) -> dict[str, float]:
    exp = payload.get("experiment", {})
    result: dict[str, float] = {}
    for item in exp.get("events", []):
        name = item.get("event")
        value = item.get("system_time")
        if name and value is not None and name not in result:
            result[name] = float(value)
    return result


def event_record(payload: dict, event_name: str) -> dict:
    """Return the first full event record, preserving success/metadata fields."""
    exp = payload.get("experiment", {})
    for item in exp.get("events", []):
        if item.get("event") == event_name:
            return dict(item)
    return {}


def integrate_window(t: np.ndarray, y: np.ndarray, lo: float, hi: float) -> float:
    mask = np.isfinite(t) & np.isfinite(y) & (t >= lo) & (t <= hi)
    if mask.sum() < 2:
        return float("nan")
    return float(np.trapezoid(y[mask], t[mask]))


def duration_above(t: np.ndarray, y: np.ndarray, lo: float, hi: float) -> float:
    mask = np.isfinite(t) & np.isfinite(y) & (t >= lo) & (t <= hi)
    if mask.sum() < 2:
        return float("nan")
    tm = t[mask]
    flag = (y[mask] > 0).astype(float)
    return float(np.trapezoid(flag, tm))


def convergence_time(t: np.ndarray, k: np.ndarray) -> float:
    mask = np.isfinite(t) & np.isfinite(k) & (t >= 0.2) & (t <= 1.5)
    if mask.sum() < 10:
        return float("nan")
    tm, km = t[mask], k[mask]
    start = float(np.nanmedian(km[: max(3, len(km) // 10)]))
    final = float(np.nanmedian(km[-max(3, len(km) // 5) :]))
    excursion = abs(final - start)
    if excursion < 1.0:
        return 0.0
    tol = max(1.0, 0.05 * excursion)
    hold = 0.2
    for i in range(len(tm)):
        j = np.searchsorted(tm, tm[i] + hold, side="left")
        if j >= len(tm):
            break
        if np.all(np.abs(km[i : j + 1] - final) <= tol):
            return float(tm[i] - 0.2)
    return float("nan")


def load_trial_metric(t: Trial, keep_series: bool = False) -> tuple[dict, pd.DataFrame | None]:
    events = event_map(t.payload)
    contact = events.get("contact_onset")
    if contact is None:
        raise ValueError(f"No contact event: {t.summary_path}")
    usecols = [
        "system_time",
        "F_ext_mag",
        "K_trans",
        "fusion_delta_K",
        "fusion_active",
        "force_adapt_delta_K",
        "force_adapt_ratio",
        "force_adapt_active",
        "vision_locked",
        "control_dt",
    ]
    df = pd.read_csv(t.csv_path, usecols=lambda c: c in usecols)
    for col in usecols:
        if col not in df:
            df[col] = 0.0 if "delta" in col else np.nan
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["system_time", "F_ext_mag", "K_trans"]).sort_values("system_time")
    rel_t = df["system_time"].to_numpy(float) - contact
    fmag = df["F_ext_mag"].to_numpy(float)
    ktrans = df["K_trans"].to_numpy(float)
    exp = t.payload.get("experiment", {})
    threshold = float(exp.get("force_threshold_N") or np.nan)
    if not np.isfinite(threshold):
        pre = fmag[(rel_t >= -0.5) & (rel_t < 0)]
        threshold = float(np.nanmean(pre) + 3 * np.nanstd(pre))
    excess = np.maximum(fmag - threshold, 0.0)
    init_mask = (rel_t >= 0) & (rel_t <= 0.2)
    adapt_mask = (rel_t >= 0.2) & (rel_t <= 1.0)
    pre_mask = (rel_t >= -0.5) & (rel_t < 0)
    delta_col = "fusion_delta_K" if t.mode == "vision_force" else "force_adapt_delta_K"
    delta = df[delta_col].to_numpy(float)
    grasp_start = events.get("grasp_start", np.nan)
    grasp_success = events.get("grasp_success", np.nan)
    release_start = events.get("release_start", np.nan)
    task_end = events.get("task_end", np.nan)
    task_start = events.get("task_start", np.nan)
    vision_lock = events.get("vision_lock", np.nan)
    vision_lead = float(contact - vision_lock) if np.isfinite(vision_lock) else np.nan
    vision_before_contact = int(np.isfinite(vision_lead) and vision_lead > 0.0)
    vision_transition_complete = int(
        np.isfinite(vision_lead) and vision_lead >= VISION_TRANSITION_S
    )
    grasp_event = event_record(t.payload, "grasp_success")
    task_end_event = event_record(t.payload, "task_end")
    completed = bool(exp.get("completed", False))
    grasp_success_flag = bool(grasp_event.get("grasp_success", completed))
    task_success_flag = bool(task_end_event.get("success", completed))
    strict_success = int(completed and grasp_success_flag and task_success_flag)

    system_time = df["system_time"].to_numpy(float)
    control_dt = df["control_dt"].to_numpy(float)
    valid_dt = control_dt[np.isfinite(control_dt) & (control_dt >= 0.001) & (control_dt <= 0.02)]
    loop_hz = float(1.0 / np.nanmedian(valid_dt)) if len(valid_dt) else np.nan
    k_change = np.r_[False, np.abs(np.diff(ktrans)) > 1e-6]
    if t.mode == "vision_force":
        online_window = (rel_t >= 0.2) & (
            system_time <= task_end if np.isfinite(task_end) else np.ones(len(df), dtype=bool)
        )
    elif t.mode == "force_only":
        online_window = (
            (system_time >= task_start if np.isfinite(task_start) else np.ones(len(df), dtype=bool))
            & (system_time <= task_end if np.isfinite(task_end) else np.ones(len(df), dtype=bool))
        )
    else:
        online_window = np.zeros(len(df), dtype=bool)
    online_change_times = system_time[k_change & online_window]
    online_update_interval = (
        float(np.nanmedian(np.diff(online_change_times))) if len(online_change_times) >= 3 else np.nan
    )
    online_change_count = int(np.sum(k_change & online_window))
    precontact_k_range = (
        float(np.nanmax(ktrans[pre_mask]) - np.nanmin(ktrans[pre_mask])) if pre_mask.any() else np.nan
    )
    adaptive_k_range = (
        float(np.nanmax(ktrans[adapt_mask]) - np.nanmin(ktrans[adapt_mask])) if adapt_mask.any() else np.nan
    )
    force_k_rho = np.nan
    if adapt_mask.sum() >= 10 and np.nanstd(fmag[adapt_mask]) > 0 and np.nanstd(ktrans[adapt_mask]) > 0:
        force_k_rho = float(stats.spearmanr(fmag[adapt_mask], ktrans[adapt_mask], nan_policy="omit").statistic)
    runtime = t.payload.get("runtime", {})
    ext = t.payload.get("external_force", {})
    metric = {
        "trial_key": t.key,
        "participant": t.participant,
        "material": t.material,
        "block": t.block,
        "block_id": "|".join([t.participant, t.material, t.block]),
        "mode": t.mode,
        "visual": int(t.mode in {"vision", "vision_force"}),
        "force_adaptive": int(t.mode in {"force_only", "vision_force"}),
        "timestamp": t.timestamp,
        "duplicate_count": t.duplicate_count,
        "duplicate_rank": t.duplicate_rank,
        "completed": int(completed),
        "grasp_success_flag": int(grasp_success_flag),
        "task_end_success_flag": int(task_success_flag),
        "success": strict_success,
        "task_start_system_s": task_start,
        "contact_onset_system_s": contact,
        "vision_lock_system_s": vision_lock,
        "vision_lead_to_contact_s": vision_lead,
        "vision_locked_before_contact": vision_before_contact if t.mode in {"vision", "vision_force"} else np.nan,
        "vision_transition_complete_before_contact": vision_transition_complete if t.mode in {"vision", "vision_force"} else np.nan,
        "contact_signal_source": "Franka estimated external wrench O_F_ext_hat_K",
        "force_threshold_N": threshold,
        "baseline_force_mean_N": float(np.nanmean(fmag[pre_mask])) if pre_mask.any() else np.nan,
        "primary_excess_impulse_Ns_0p2_1p0": integrate_window(rel_t, excess, 0.2, 1.0),
        "initial_peak_force_N_0_0p2": float(np.nanmax(fmag[init_mask])) if init_mask.any() else np.nan,
        "initial_excess_impulse_Ns_0_0p2": integrate_window(rel_t, excess, 0.0, 0.2),
        "adapt_peak_force_N_0p2_1p0": float(np.nanmax(fmag[adapt_mask])) if adapt_mask.any() else np.nan,
        "excess_duration_s_0p2_1p0": duration_above(rel_t, excess, 0.2, 1.0),
        "contact_to_grasp_start_s": float(grasp_start - contact),
        "contact_to_grasp_success_s": float(grasp_success - contact),
        "grasp_to_release_s": float(release_start - grasp_success),
        "release_duration_s": float(task_end - release_start),
        "operation_time_s": float(exp.get("operation_time_s") or np.nan),
        "trajectory_length_m": float(runtime.get("traj_length_m") or np.nan),
        "speed_std_m_s": float(runtime.get("speed_std_ms") or np.nan),
        "whole_peak_force_N": float(ext.get("F_ext_peak_N") or np.nan),
        "whole_mean_force_N": float(ext.get("F_ext_mean_N") or np.nan),
        "recognition_time_s": float(exp.get("recognition_time_s") or np.nan),
        "stiffness_min_N_m_0p2_1p0": float(np.nanmin(ktrans[adapt_mask])) if adapt_mask.any() else np.nan,
        "stiffness_mean_N_m_0p2_1p0": float(np.nanmean(ktrans[adapt_mask])) if adapt_mask.any() else np.nan,
        "stiffness_delta_min_N_m": float(np.nanmin(delta[adapt_mask])) if adapt_mask.any() else 0.0,
        "stiffness_delta_end_N_m": float(np.nanmedian(delta[adapt_mask][-max(1, adapt_mask.sum() // 10) :])) if adapt_mask.any() else 0.0,
        "stiffness_convergence_s": convergence_time(rel_t, ktrans),
        "observed_control_loop_hz": loop_hz,
        "online_stiffness_change_count": online_change_count,
        "online_update_interval_median_s": online_update_interval,
        "online_update_observed": int(online_change_count >= 3) if t.mode in {"force_only", "vision_force"} else 0,
        "precontact_stiffness_range_N_m": precontact_k_range,
        "adaptive_window_stiffness_range_N_m": adaptive_k_range,
        "force_stiffness_spearman_0p2_1p0": force_k_rho,
    }
    aligned = None
    if keep_series:
        unique_t, idx = np.unique(rel_t, return_index=True)
        if len(unique_t) >= 2:
            aligned = pd.DataFrame(
                {
                    "t_rel_s": ALIGN_GRID,
                    "F_ext_N": np.interp(ALIGN_GRID, unique_t, fmag[idx], left=np.nan, right=np.nan),
                    "F_excess_N": np.interp(ALIGN_GRID, unique_t, excess[idx], left=np.nan, right=np.nan),
                    "K_trans_N_m": np.interp(ALIGN_GRID, unique_t, ktrans[idx], left=np.nan, right=np.nan),
                }
            )
            for k, v in {
                "participant": t.participant,
                "material": t.material,
                "block": t.block,
                "mode": t.mode,
                "trial_key": t.key,
            }.items():
                aligned[k] = v
    return metric, aligned


def metrics_for_trials(trials: Iterable[Trial], keep_series: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict] = []
    series: list[pd.DataFrame] = []
    for i, t in enumerate(trials, 1):
        metric, aligned = load_trial_metric(t, keep_series=keep_series)
        rows.append(metric)
        if aligned is not None:
            series.append(aligned)
        if i % 30 == 0:
            print(f"processed {i} trials")
    return pd.DataFrame(rows), pd.concat(series, ignore_index=True) if series else pd.DataFrame()


def aggregate_aligned(aligned: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for keys, g in aligned.groupby(["material", "mode", "t_rel_s"], observed=True):
        material, mode, tm = keys
        row = {"material": material, "mode": mode, "t_rel_s": tm, "n": g["trial_key"].nunique()}
        for col in ["F_ext_N", "F_excess_N", "K_trans_N_m"]:
            vals = g[col].dropna().to_numpy(float)
            mean = float(np.mean(vals)) if len(vals) else np.nan
            se = float(np.std(vals, ddof=1) / math.sqrt(len(vals))) if len(vals) > 1 else np.nan
            row[f"{col}_mean"] = mean
            row[f"{col}_ci_low"] = mean - 1.96 * se if np.isfinite(se) else np.nan
            row[f"{col}_ci_high"] = mean + 1.96 * se if np.isfinite(se) else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def paired_diff(metric_df: pd.DataFrame, metric: str) -> pd.DataFrame:
    cell = (
        metric_df.groupby(["block_id", "participant", "material", "mode"], as_index=False)[metric]
        .mean()
    )
    wide = cell.pivot(index=["block_id", "participant", "material"], columns="mode", values=metric).reset_index()
    wide["contrast_F_minus_E"] = wide["vision_force"] - wide["vision"]
    wide["contrast_F_minus_G"] = wide["vision_force"] - wide["force_only"]
    wide["interaction"] = wide["vision_force"] - wide["vision"] - wide["force_only"] + wide["default"]
    return wide


def complete_visual_timing_blocks(metrics: pd.DataFrame, flag_col: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Keep full 2x2 blocks only when both visual modes satisfy the timing rule."""
    visual = metrics[metrics["mode"].isin(["vision", "vision_force"])].copy()
    block_audit = (
        visual.groupby(["block_id", "participant", "material", "block"], as_index=False)
        .agg(visual_trials=("mode", "nunique"), eligible_visual_trials=(flag_col, "sum"))
    )
    block_audit["complete_block_eligible"] = (
        (block_audit["visual_trials"] == 2) & (block_audit["eligible_visual_trials"] == 2)
    ).astype(int)
    eligible_ids = set(block_audit.loc[block_audit["complete_block_eligible"].eq(1), "block_id"])
    return metrics[metrics["block_id"].isin(eligible_ids)].copy(), block_audit


def build_sensitivity_analyses(metrics: pd.DataFrame, metric: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    analyses: list[pd.DataFrame] = []
    timing_audits: list[pd.DataFrame] = []

    main, _ = contrast_table(metrics, metric, "main_all_180")
    main["n_trials_analyzed"] = len(metrics)
    analyses.append(main)

    rules = [
        ("vision_locked_before_contact", "sensitivity_visual_lock_before_contact_complete_blocks"),
        (
            "vision_transition_complete_before_contact",
            "sensitivity_visual_transition_0p3s_complete_blocks",
        ),
    ]
    for flag_col, analysis_name in rules:
        subset, audit = complete_visual_timing_blocks(metrics, flag_col)
        audit["criterion"] = flag_col
        timing_audits.append(audit)
        table, _ = contrast_table(subset, metric, analysis_name)
        table["n_trials_analyzed"] = len(subset)
        analyses.append(table)

    soft_medium = metrics[metrics["material"].isin(["soft", "medium"])].copy()
    material_table, _ = contrast_table(
        soft_medium, metric, "sensitivity_soft_medium_only_hard_policy_excluded"
    )
    material_table["n_trials_analyzed"] = len(soft_medium)
    analyses.append(material_table)

    return pd.concat(analyses, ignore_index=True), pd.concat(timing_audits, ignore_index=True)


def bootstrap_ci(values: np.ndarray, n_boot: int = 10000) -> tuple[float, float]:
    values = values[np.isfinite(values)]
    if len(values) < 2:
        return np.nan, np.nan
    local_rng = np.random.default_rng(20260804)
    draws = local_rng.choice(values, size=(n_boot, len(values)), replace=True).mean(axis=1)
    return tuple(np.quantile(draws, [0.025, 0.975]).tolist())


def permutation_p(values: np.ndarray, n_perm: int = 50000) -> float:
    values = values[np.isfinite(values)]
    if len(values) == 0:
        return np.nan
    observed = abs(float(np.mean(values)))
    local_rng = np.random.default_rng(20260805)
    count = 0
    batch = 5000
    done = 0
    while done < n_perm:
        n = min(batch, n_perm - done)
        signs = local_rng.choice([-1.0, 1.0], size=(n, len(values)))
        perm = np.abs((signs * values).mean(axis=1))
        count += int(np.sum(perm >= observed - 1e-15))
        done += n
    return (count + 1) / (n_perm + 1)


def holm_adjust(pvals: list[float]) -> list[float]:
    p = np.asarray(pvals, float)
    order = np.argsort(p)
    out = np.empty_like(p)
    running = 0.0
    m = len(p)
    for rank, idx in enumerate(order):
        value = min(1.0, (m - rank) * p[idx])
        running = max(running, value)
        out[idx] = running
    return out.tolist()


def contrast_table(metric_df: pd.DataFrame, metric: str, analysis_name: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    wide = paired_diff(metric_df, metric)
    rows = []
    mapping = {
        "F - E（融合相对视觉先验）": "contrast_F_minus_E",
        "F - G（融合相对纯力自适应）": "contrast_F_minus_G",
        "2×2 交互 (F-E-G+A)": "interaction",
    }
    raw_p = []
    for label, col in mapping.items():
        vals = wide[col].to_numpy(float)
        vals = vals[np.isfinite(vals)]
        mean = float(np.mean(vals))
        sd = float(np.std(vals, ddof=1))
        low, high = bootstrap_ci(vals)
        p = permutation_p(vals)
        raw_p.append(p)
        rows.append(
            {
                "analysis": analysis_name,
                "metric": metric,
                "contrast": label,
                "n_blocks": len(vals),
                "mean_difference": mean,
                "sd_difference": sd,
                "dz": mean / sd if sd > 0 else np.nan,
                "ci95_low": low,
                "ci95_high": high,
                "p_permutation": p,
            }
        )
    adjusted = holm_adjust(raw_p)
    for row, p_adj in zip(rows, adjusted):
        row["p_holm"] = p_adj
    return pd.DataFrame(rows), wide


def build_fixed_matrix(df: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    v = df["visual"].to_numpy(float)
    f = df["force_adaptive"].to_numpy(float)
    med = (df["material"] == "medium").to_numpy(float)
    hard = (df["material"] == "hard").to_numpy(float)
    columns = [
        np.ones(len(df)), v, f, med, hard, v * f,
        v * med, v * hard, f * med, f * hard,
        v * f * med, v * f * hard,
    ]
    names = [
        "Intercept (soft, no vision, no force)",
        "Vision",
        "Force adaptation",
        "Material: medium",
        "Material: hard",
        "Vision × Force",
        "Vision × Medium",
        "Vision × Hard",
        "Force × Medium",
        "Force × Hard",
        "Vision × Force × Medium",
        "Vision × Force × Hard",
    ]
    return np.column_stack(columns), names


def fit_reml_random_intercepts(df: pd.DataFrame, response: str) -> tuple[pd.DataFrame, dict]:
    work = df.dropna(subset=[response]).copy().reset_index(drop=True)
    y = work[response].to_numpy(float)
    X, names = build_fixed_matrix(work)
    n, p = X.shape
    op_codes = pd.Categorical(work["participant"]).codes
    block_codes = pd.Categorical(work["block_id"]).codes
    Zop = np.equal.outer(op_codes, op_codes).astype(float)
    Zblock = np.equal.outer(block_codes, block_codes).astype(float)
    eye = np.eye(n)

    def evaluate(theta: np.ndarray, need_beta: bool = False):
        ve, vo, vb = np.exp(theta)
        V = ve * eye + vo * Zop + vb * Zblock
        try:
            c, lower = linalg.cho_factor(V, lower=True, check_finite=False)
            ViX = linalg.cho_solve((c, lower), X, check_finite=False)
            Viy = linalg.cho_solve((c, lower), y, check_finite=False)
            XtViX = X.T @ ViX
            cx, lx = linalg.cho_factor(XtViX, lower=True, check_finite=False)
            beta = linalg.cho_solve((cx, lx), X.T @ Viy, check_finite=False)
            resid = y - X @ beta
            Vir = linalg.cho_solve((c, lower), resid, check_finite=False)
            logdet_v = 2 * np.log(np.diag(c)).sum()
            logdet_x = 2 * np.log(np.diag(cx)).sum()
            nll = 0.5 * (logdet_v + logdet_x + resid @ Vir + (n - p) * np.log(2 * np.pi))
            if need_beta:
                cov_beta = linalg.cho_solve((cx, lx), np.eye(p), check_finite=False)
                return nll, beta, cov_beta, (ve, vo, vb)
            return nll
        except (linalg.LinAlgError, ValueError, FloatingPointError):
            return 1e100

    var_y = max(float(np.var(y, ddof=1)), 1e-8)
    start = np.log([0.5 * var_y, 0.15 * var_y, 0.35 * var_y])
    fit = optimize.minimize(evaluate, start, method="L-BFGS-B", bounds=[(-20, 20)] * 3)
    nll, beta, cov_beta, variances = evaluate(fit.x, need_beta=True)
    se = np.sqrt(np.clip(np.diag(cov_beta), 0, np.inf))
    dof = max(n - p, 1)
    tvals = beta / se
    pvals = 2 * stats.t.sf(np.abs(tvals), dof)
    crit = stats.t.ppf(0.975, dof)
    rows = []
    for name, b, s, tv, pv in zip(names, beta, se, tvals, pvals):
        rows.append(
            {
                "term": name,
                "estimate": b,
                "std_error": s,
                "t_value": tv,
                "df_approx": dof,
                "p_value": pv,
                "ci95_low": b - crit * s,
                "ci95_high": b + crit * s,
            }
        )
    info = {
        "converged": bool(fit.success),
        "optimizer_message": str(fit.message),
        "reml_neg_loglik": float(nll),
        "variance_residual": variances[0],
        "variance_operator": variances[1],
        "variance_block": variances[2],
        "n": n,
        "p": p,
    }
    return pd.DataFrame(rows), info


def descriptive_table(metrics: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "primary_excess_impulse_Ns_0p2_1p0",
        "initial_peak_force_N_0_0p2",
        "excess_duration_s_0p2_1p0",
        "contact_to_grasp_success_s",
        "operation_time_s",
        "trajectory_length_m",
        "whole_peak_force_N",
        "whole_mean_force_N",
    ]
    rows = []
    for (material, mode), g in metrics.groupby(["material", "mode"], observed=True):
        row = {"material": material, "mode": mode, "n": len(g), "success_rate": g["success"].mean()}
        for col in cols:
            row[f"{col}_mean"] = g[col].mean()
            row[f"{col}_sd"] = g[col].std(ddof=1)
        rows.append(row)
    return pd.DataFrame(rows)


def online_mechanism_summary(metrics: pd.DataFrame) -> pd.DataFrame:
    rows = []
    adaptive = metrics[metrics["mode"].isin(["force_only", "vision_force"])]
    for (material, mode), g in adaptive.groupby(["material", "mode"], observed=True):
        rows.append(
            {
                "material": material,
                "mode": mode,
                "n_trials": len(g),
                "online_update_observed_rate": g["online_update_observed"].mean(),
                "control_loop_hz_median": g["observed_control_loop_hz"].median(),
                "online_update_interval_median_s": g["online_update_interval_median_s"].median(),
                "stiffness_change_count_median": g["online_stiffness_change_count"].median(),
                "precontact_stiffness_range_median_N_m": g["precontact_stiffness_range_N_m"].median(),
                "adaptive_stiffness_range_median_N_m": g["adaptive_window_stiffness_range_N_m"].median(),
                "force_stiffness_spearman_median": g["force_stiffness_spearman_0p2_1p0"].median(),
            }
        )
    return pd.DataFrame(rows)


def fusion_policy_audit_table() -> pd.DataFrame:
    rows = [
        ["soft", 50.0, -0.25, 30.0, 90.0, 37.5, 50.0, 37.5, 50.0, 1, "全力域连续调制"],
        ["medium", 120.0, -0.35, 85.0, 130.0, 78.0, 120.0, 85.0, 120.0, 1, "高力端受下界截断"],
        ["hard", 200.0, -0.15, 140.0, 170.0, 170.0, 200.0, 170.0, 170.0, 0, "目标恒为170 N/m，属于事件触发固定柔化"],
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "material",
            "K_base_N_m",
            "gain",
            "K_min_N_m",
            "K_max_N_m",
            "raw_target_min_N_m",
            "raw_target_max_N_m",
            "clipped_target_min_N_m",
            "clipped_target_max_N_m",
            "force_amplitude_dependent",
            "interpretation",
        ],
    )


def save_all_formats(fig: plt.Figure, stem: str) -> None:
    for ext in ["png", "pdf", "svg"]:
        kwargs = {"dpi": 600} if ext == "png" else {}
        fig.savefig(DIRS["figures"] / f"{stem}.{ext}", bbox_inches="tight", **kwargs)
    plt.close(fig)


def setup_plotting() -> None:
    plt.rcParams.update(
        {
            "font.sans-serif": ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"],
            "axes.unicode_minus": False,
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "legend.fontsize": 8,
            "figure.dpi": 120,
        }
    )


def box(ax, xy, wh, text, fc="#F8FAFC", ec="#334155", fontsize=9):
    x, y = xy
    w, h = wh
    patch = FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.02",
        facecolor=fc, edgecolor=ec, linewidth=1.2, transform=ax.transAxes,
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize, transform=ax.transAxes)
    return patch


def arrow(ax, start, end, color="#475569", text=None, rad=0.0):
    patch = FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=12, linewidth=1.2,
                            color=color, connectionstyle=f"arc3,rad={rad}", transform=ax.transAxes)
    ax.add_patch(patch)
    if text:
        ax.text((start[0] + end[0]) / 2, (start[1] + end[1]) / 2 + 0.025, text,
                ha="center", va="bottom", color=color, fontsize=8, transform=ax.transAxes)


def fig1_system() -> None:
    fig, ax = plt.subplots(figsize=(11, 5.2))
    ax.axis("off")
    box(ax, (0.03, 0.38), (0.16, 0.22), "操作者\nOmega.7 主端", "#E0F2FE", "#0369A1", 10)
    box(ax, (0.27, 0.38), (0.17, 0.22), "200 Hz 监督控制\n位置映射 / 事件状态机", "#F1F5F9", "#475569", 9)
    box(ax, (0.55, 0.38), (0.17, 0.22), "Franka Panda\n笛卡尔阻抗控制", "#DCFCE7", "#15803D", 10)
    box(ax, (0.80, 0.38), (0.16, 0.22), "异质物体\n软 / 中 / 硬", "#FEF3C7", "#B45309", 10)
    box(ax, (0.30, 0.76), (0.16, 0.15), "RealSense D435i\nRGB 15 fps", "#EDE9FE", "#6D28D9", 9)
    box(ax, (0.54, 0.76), (0.18, 0.15), "YOLO 语义识别\n类别 → 材料先验", "#EDE9FE", "#6D28D9", 9)
    box(ax, (0.55, 0.07), (0.17, 0.15), "Panda 外力估计\n|Fext| / 接触事件", "#FEE2E2", "#B91C1C", 9)
    arrow(ax, (0.19, 0.49), (0.27, 0.49), "#0369A1", "位移命令")
    arrow(ax, (0.44, 0.49), (0.55, 0.49), "#475569", "期望位姿与阻抗")
    arrow(ax, (0.72, 0.49), (0.80, 0.49), "#15803D", "交互")
    arrow(ax, (0.80, 0.42), (0.72, 0.42), "#B91C1C", "接触反力")
    arrow(ax, (0.46, 0.835), (0.54, 0.835), "#6D28D9", "图像")
    arrow(ax, (0.63, 0.76), (0.39, 0.60), "#6D28D9", "接触前先验")
    arrow(ax, (0.635, 0.38), (0.635, 0.22), "#B91C1C", "外力状态")
    arrow(ax, (0.55, 0.145), (0.41, 0.38), "#B91C1C", "接触后修正")
    arrow(ax, (0.55, 0.12), (0.19, 0.38), "#B91C1C", "主端力反馈", rad=-0.15)
    ax.text(0.5, 0.98, "图 1  人机在环视觉-力融合遥操作平台与数据流", ha="center", va="top",
            fontsize=13, fontweight="bold", transform=ax.transAxes)
    ax.text(0.5, 0.01, "注：视觉通道提供接触前材料先验；外力估计用于接触检测、在线刚度修正与主端触觉反馈。",
            ha="center", va="bottom", fontsize=8, color="#475569", transform=ax.transAxes)
    save_all_formats(fig, "fig1_system_and_dataflow")


def fig2_control() -> None:
    fig, ax = plt.subplots(figsize=(11, 6.2))
    ax.axis("off")
    box(ax, (0.04, 0.68), (0.18, 0.16), "RGB 图像\n目标类别 c", "#EDE9FE", "#6D28D9")
    box(ax, (0.31, 0.68), (0.22, 0.16), "语义先验映射\nKbase(c), [Kmin,Kmax]", "#E0F2FE", "#0369A1")
    box(ax, (0.04, 0.24), (0.18, 0.16), "外力估计 |Fext|\ncontact_onset", "#FEE2E2", "#B91C1C")
    box(ax, (0.31, 0.24), (0.22, 0.16), "材料相关接触后修正\ns(F;c), gain(c)", "#FEF3C7", "#B45309")
    box(ax, (0.62, 0.46), (0.20, 0.18), "有界平滑更新\nK(t+1)=(1-β)K(t)+βK*", "#DCFCE7", "#15803D")
    box(ax, (0.87, 0.46), (0.10, 0.18), "机器人\n阻抗", "#F1F5F9", "#334155")
    arrow(ax, (0.22, 0.76), (0.31, 0.76), "#6D28D9")
    arrow(ax, (0.53, 0.76), (0.69, 0.64), "#0369A1", "接触前")
    arrow(ax, (0.22, 0.32), (0.31, 0.32), "#B91C1C")
    arrow(ax, (0.53, 0.32), (0.69, 0.46), "#B45309", "接触后 0.2 s 起")
    arrow(ax, (0.82, 0.55), (0.87, 0.55), "#15803D")
    modes = [
        ("A", "固定参数", "无", "无", "#7F8C8D"),
        ("G", "纯力自适应", "无", "有", "#D97706"),
        ("E", "视觉先验", "有", "无", "#2563EB"),
        ("F", "视觉-力融合", "有", "有", "#059669"),
    ]
    x0 = 0.10
    for i, (code, name, vis, force, color) in enumerate(modes):
        x = x0 + i * 0.22
        box(ax, (x, 0.02), (0.18, 0.12), f"{code} {name}\n视觉={vis}，力自适应={force}", "#FFFFFF", color, 8)
    ax.text(0.5, 0.96, "图 2  接触前视觉先验与接触后力反馈修正及四模式消融",
            ha="center", va="top", fontsize=13, fontweight="bold", transform=ax.transAxes)
    save_all_formats(fig, "fig2_control_and_ablation")


def fig3_update_law() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), gridspec_kw={"width_ratios": [1.1, 1]})
    ax = axes[0]
    force = np.linspace(0, 10, 300)
    policies = {
        "soft": (60, -0.25, 0.3, 2.5, 30, 90),
        "medium": (110, -0.35, 0.8, 6.0, 85, 130),
        "hard": (200, -0.15, 1.2, 8.0, 140, 170),
    }
    colors = {"soft": "#60A5FA", "medium": "#F59E0B", "hard": "#16A34A"}
    for material, (base, gain, dead, sat, kmin, kmax) in policies.items():
        ratio = np.clip((force - dead) / (sat - dead), 0, 1)
        target = np.clip(base * (1 + gain * ratio), kmin, kmax)
        ax.plot(force, target, lw=2.2, color=colors[material], label=MATERIAL_ZH[material])
        ax.fill_between(force, kmin, kmax, color=colors[material], alpha=0.05)
    ax.set_xlabel("末端外力 |Fext| (N)")
    ax.set_ylabel("目标平动刚度 K* (N/m)")
    ax.set_title("(a) 材料相关的有界目标刚度")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False)
    ax = axes[1]
    ax.set_xlim(-0.6, 2.3)
    ax.set_ylim(0, 1)
    ax.axvspan(-0.5, 0, color="#CBD5E1", alpha=0.35)
    ax.axvspan(0, 0.2, color="#93C5FD", alpha=0.35)
    ax.axvspan(0.2, 1.0, color="#86EFAC", alpha=0.35)
    ax.axvspan(1.0, 2.2, color="#FDE68A", alpha=0.35)
    for x, name in [(0, "接触"), (0.2, "反馈启用"), (1.0, "后续抓取")]:
        ax.axvline(x, color="#334155", ls="--", lw=1)
        ax.text(x, 0.88, name, rotation=90, va="top", ha="right", fontsize=8)
    ax.text(-0.25, 0.45, "基线\n0.5 s", ha="center", va="center")
    ax.text(0.10, 0.45, "初始接触\n视觉先验主导", ha="center", va="center")
    ax.text(0.60, 0.45, "自适应阶段\n在线力反馈修正", ha="center", va="center")
    ax.text(1.60, 0.45, "抓取 / 搬运\n分阶段指标", ha="center", va="center")
    ax.set_xlabel("相对接触时间 (s)")
    ax.set_yticks([])
    ax.set_title("(b) 事件对齐分析窗口")
    fig.suptitle("图 3  离散刚度更新律、材料边界与事件时间线", fontsize=13, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    save_all_formats(fig, "fig3_update_law_and_timeline")


def fig4_aligned(aligned_summary: pd.DataFrame) -> None:
    fig, axes = plt.subplots(3, 2, figsize=(11, 9), sharex=True)
    for r, material in enumerate(MATERIAL_ORDER):
        for mode in MODE_ORDER:
            g = aligned_summary[(aligned_summary["material"] == material) & (aligned_summary["mode"] == mode)].sort_values("t_rel_s")
            if g.empty:
                continue
            tm = g["t_rel_s"].to_numpy(float)
            for c, (metric, ylabel) in enumerate([("F_excess_N", "基线校正超阈值力 (N)"), ("K_trans_N_m", "平动刚度 (N/m)")]):
                ax = axes[r, c]
                mean = g[f"{metric}_mean"].to_numpy(float)
                low = g[f"{metric}_ci_low"].to_numpy(float)
                high = g[f"{metric}_ci_high"].to_numpy(float)
                ax.plot(tm, mean, color=MODE_COLORS[mode], lw=1.5, label=MODE_SHORT[mode])
                ax.fill_between(tm, low, high, color=MODE_COLORS[mode], alpha=0.08)
                ax.set_ylabel(ylabel)
                ax.grid(alpha=0.2)
                ax.axvline(0, color="#334155", ls="--", lw=0.8)
                ax.axvline(0.2, color="#B91C1C", ls=":", lw=1.1)
        axes[r, 0].text(0.02, 0.92, MATERIAL_ZH[material], transform=axes[r, 0].transAxes,
                        fontweight="bold", bbox=dict(fc="white", ec="#CBD5E1", pad=3))
    for ax in axes[-1, :]:
        ax.set_xlabel("相对接触时间 (s)")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 0.965))
    fig.suptitle("图 4  不同材料与模式的接触对齐外力和刚度响应（均值与 95% CI）",
                 fontsize=13, fontweight="bold", y=0.995)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    save_all_formats(fig, "fig4_contact_aligned_force_stiffness")


def fig5_primary(metrics: pd.DataFrame, contrast: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), gridspec_kw={"width_ratios": [1.25, 1]})
    ax = axes[0]
    data = [metrics.loc[metrics["mode"] == mode, "primary_excess_impulse_Ns_0p2_1p0"].to_numpy(float) for mode in MODE_ORDER]
    bp = ax.boxplot(data, positions=np.arange(4), widths=0.55, patch_artist=True, showfliers=False,
                    medianprops=dict(color="#111827", lw=1.4))
    for patch, mode in zip(bp["boxes"], MODE_ORDER):
        patch.set_facecolor(MODE_COLORS[mode])
        patch.set_alpha(0.30)
        patch.set_edgecolor(MODE_COLORS[mode])
    for i, (vals, mode) in enumerate(zip(data, MODE_ORDER)):
        jitter = RNG.normal(0, 0.055, len(vals))
        ax.scatter(np.full(len(vals), i) + jitter, vals, s=12, alpha=0.55, color=MODE_COLORS[mode], edgecolor="none")
    ax.set_xticks(range(4), ["A", "G", "E", "F"])
    ax.set_ylabel("0.2–1.0 s 超阈值力冲量 (N·s)")
    ax.set_title("(a) 四模式原始分布")
    ax.grid(axis="y", alpha=0.22)
    ax = axes[1]
    c = contrast.copy()
    labels = ["F − E", "F − G", "交互项"]
    y = np.arange(len(c))[::-1]
    means = c["mean_difference"].to_numpy(float)
    low = c["ci95_low"].to_numpy(float)
    high = c["ci95_high"].to_numpy(float)
    ax.errorbar(means, y, xerr=[means - low, high - means], fmt="o", color="#0F766E", capsize=4, lw=1.6)
    ax.axvline(0, color="#334155", lw=1, ls="--")
    for yi, p in zip(y, c["p_holm"]):
        ax.text(ax.get_xlim()[1] if ax.get_xlim()[1] else max(high), yi, f"  pHolm={p:.3f}", va="center", fontsize=8)
    ax.set_yticks(y, labels)
    ax.set_xlabel("配对均值差 (N·s)，负值表示 F 更低")
    ax.set_title("(b) 预定义对比及 95% 自助置信区间")
    ax.grid(axis="x", alpha=0.22)
    fig.suptitle("图 5  主指标的原始分布与预定义配对效应", fontsize=13, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    save_all_formats(fig, "fig5_primary_metric_effects")


def fig6_interactions(metrics: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.4))
    ax = axes[0]
    for mode in MODE_ORDER:
        means = []
        ses = []
        for material in MATERIAL_ORDER:
            vals = metrics[(metrics["mode"] == mode) & (metrics["material"] == material)]["primary_excess_impulse_Ns_0p2_1p0"].dropna()
            means.append(vals.mean())
            ses.append(vals.std(ddof=1) / math.sqrt(len(vals)))
        ax.errorbar(range(3), means, yerr=np.array(ses) * 1.96, marker="o", lw=1.5, capsize=3,
                    color=MODE_COLORS[mode], label=MODE_SHORT[mode])
    ax.set_xticks(range(3), [MATERIAL_ZH[m] for m in MATERIAL_ORDER])
    ax.set_ylabel("超阈值力冲量 (N·s)")
    ax.set_title("(a) 模式 × 材料")
    ax.grid(alpha=0.2)
    ax.legend(frameon=False, fontsize=7)
    ax = axes[1]
    adaptive = metrics[metrics["mode"].isin(["force_only", "vision_force"])].copy()
    positions = []
    values = []
    colors = []
    labels = []
    pos = 0
    for material in MATERIAL_ORDER:
        for mode in ["force_only", "vision_force"]:
            vals = -adaptive[(adaptive["material"] == material) & (adaptive["mode"] == mode)]["stiffness_delta_min_N_m"].dropna().to_numpy(float)
            positions.append(pos)
            values.append(vals)
            colors.append(MODE_COLORS[mode])
            labels.append(f"{MATERIAL_ZH[material]}\n{'G' if mode == 'force_only' else 'F'}")
            pos += 1
        pos += 0.4
    bp = ax.boxplot(values, positions=positions, widths=0.55, patch_artist=True, showfliers=False)
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.35)
        patch.set_edgecolor(color)
    ax.set_xticks(positions, labels)
    ax.set_ylabel("最大刚度降低幅值 (N/m)")
    ax.set_title("(b) 接触后在线刚度修正幅度")
    ax.grid(axis="y", alpha=0.2)
    ax = axes[2]
    phase_cols = ["contact_to_grasp_success_s", "grasp_to_release_s", "release_duration_s"]
    phase_names = ["接触→抓取成功", "抓取→释放", "释放阶段"]
    bottom = np.zeros(4)
    phase_colors = ["#93C5FD", "#FBBF24", "#A7F3D0"]
    for col, name, color in zip(phase_cols, phase_names, phase_colors):
        vals = [metrics[metrics["mode"] == mode][col].mean() for mode in MODE_ORDER]
        ax.bar(range(4), vals, bottom=bottom, label=name, color=color, width=0.65)
        bottom += np.array(vals)
    ax.set_xticks(range(4), ["A", "G", "E", "F"])
    ax.set_ylabel("平均阶段时间 (s)")
    ax.set_title("(c) 分阶段耗时")
    ax.legend(frameon=False, fontsize=7)
    ax.grid(axis="y", alpha=0.2)
    fig.suptitle("图 6  材料交互、刚度修正与分阶段效率", fontsize=13, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    save_all_formats(fig, "fig6_interaction_convergence_phases")


def write_tables(descriptive: pd.DataFrame, contrast: pd.DataFrame, sensitivity: pd.DataFrame) -> None:
    lit = pd.DataFrame(
        [
            ["Huang et al.", 2021, "物体属性视觉识别", "材料/脆弱性", "否", "接触前离散设定", "概念验证", "未报告", "https://doi.org/10.1109/ICAR53236.2021.9659427"],
            ["Yang et al.", 2022, "示教轨迹", "无", "是", "学习变阻抗技能", "自主接触任务", "未作为主要贡献", "https://doi.org/10.1109/LRA.2022.3187276"],
            ["Michel et al.", 2023, "状态/动力系统", "无", "是", "能量罐变刚度", "物理交互", "钝性与渐近稳定", "https://arxiv.org/abs/2307.09571"],
            ["Siegemund et al.", 2024, "RGB-D 视觉", "材料+几何+环境关系", "否", "对象感知刚度估计", "遥操作", "未作为主要贡献", "https://doi.org/10.1109/Humanoids58906.2024.10769858"],
            ["OmniVIC", 2025, "VLM+语言", "任务语义", "是", "语义生成+实时力约束", "自主接触任务", "安全约束/实验验证", "https://arxiv.org/abs/2510.17150"],
            ["本文", 2026, "对象类别", "软/中/硬材料先验", "是", "接触事件分段的材料限定在线变阻抗", "人机在环遥操作，2×2 配对消融", "区间不变性与更新收敛", "本研究"],
        ],
        columns=["研究", "年份", "视觉/先验", "材料语义", "接触力在线反馈", "阻抗策略", "验证场景", "数学性质", "来源"],
    )
    lit.to_csv(DIRS["stats"] / "table1_related_work.csv", index=False, encoding="utf-8-sig")
    mode = pd.DataFrame(
        [
            ["A", "default", 0, 0, "固定参数基线"],
            ["G", "force_only", 0, 1, "无接触门控的全程纯外力在线自适应"],
            ["E", "vision", 1, 0, "视觉材料先验，接触后不修正"],
            ["F", "vision_force", 1, 1, "视觉先验+接触事件门控的材料限定在线修正"],
        ],
        columns=["代码", "日志模式", "视觉因子", "力自适应因子", "控制含义"],
    )
    mode.to_csv(DIRS["stats"] / "table2_modes.csv", index=False, encoding="utf-8-sig")
    design = pd.DataFrame(
        [
            ["接触前基线", "contact_onset 前 0.5 s", "基线力均值、个体阈值", "校正传感器/估计偏置"],
            ["初始接触", "接触后 0–0.2 s", "峰值力、超阈值力冲量", "视觉先验的前接触作用"],
            ["自适应阶段", "接触后 0.2–1.0 s", "超阈值力冲量（主指标）、持续时间、刚度收敛", "在线力反馈修正"],
            ["抓取阶段", "1.0 s 至 grasp_success", "接触至抓取成功时间", "操作者与控制协同"],
            ["搬运释放", "grasp_success 至 task_end", "搬运及释放时间", "任务效率"],
        ],
        columns=["阶段", "时间定义", "指标", "解释"],
    )
    design.to_csv(DIRS["stats"] / "table3_design_metrics.csv", index=False, encoding="utf-8-sig")
    table4 = sensitivity.copy()
    table4["primary_analysis"] = table4["analysis"].eq("main_all_180").astype(int)
    table4.to_csv(DIRS["stats"] / "table4_main_statistics.csv", index=False, encoding="utf-8-sig")


def fmt_num(x: float, digits: int = 3) -> str:
    return "NA" if not np.isfinite(x) else f"{x:.{digits}f}"


def write_literature_review() -> None:
    content = """# 第二篇论文创新性文献核验

## 核验结论

“视觉识别物体后自动设置阻抗”以及“视觉与力反馈融合调节阻抗”均已有直接或相邻先例，不能作为宽泛首创。本文可辩护的增量在于：针对人机在环抓取，把视觉材料先验明确限定为接触前基线与安全区间，把接触力限定为事件触发后的在线修正，并用完整配对的 2×2 因子实验和事件对齐指标验证两条信息通道在不同时间阶段的作用。

## 关键近邻工作

1. Huang, Abbink 与 Peternel（ICAR 2021）使用视觉识别材料/脆弱性并在接触前选择阻抗，已覆盖“物体属性到阻抗”的核心概念。https://doi.org/10.1109/ICAR53236.2021.9659427
2. Siegemund 等（Humanoids 2024）将材料、几何及物体与环境关系用于半自主遥阻抗，覆盖对象感知的刚度估计。https://doi.org/10.1109/Humanoids58906.2024.10769858
3. OmniVIC（2025）利用 VLM/RAG 生成情境相关阻抗，并用实时力/力矩信息约束安全交互，说明“高层语义+低层力反馈”也不是空白。https://arxiv.org/abs/2510.17150
4. Duan 等（Robotics and Autonomous Systems, 2018）针对未知环境的动态接触力跟踪提出自适应变阻抗并给出稳定性与收敛分析。https://doi.org/10.1016/j.robot.2018.01.009
5. Michel、Saveriano 与 Lee（2023）采用能量罐保证变刚度交互的钝性，表明二区控制论文通常需要正面处理时变阻抗的稳定性问题。https://arxiv.org/abs/2307.09571
6. Yang 等（RA-L 2022）把变阻抗作为接触丰富操作的学习动作空间，说明在线或任务相关阻抗调节本身已是成熟研究方向。https://doi.org/10.1109/LRA.2022.3187276

## 本文可采用的创新表述

- 不是“首次将视觉用于遥操作阻抗”，而是“提出接触事件分段的语义先验约束—在线力反馈调节结构”。
- 不是“首次融合视觉和力”，而是“材料语义同时限定死区、饱和区、修正增益与刚度边界，使接触后调节具有对象相关的可解释性”。
- 不是只展示单条过程曲线，而是“以 45 个匹配任务块完成四模式 2×2 消融，并按接触事件重建控制作用阶段”。
- 数学部分只证明离散平滑更新的区间不变性和常值目标下的指数收敛，不宣称完整遥操作闭环钝性。

## 审稿风险

若融合模式相对视觉模式不能降低 0.2–1.0 s 的超阈值力冲量，或相对纯力模式不能显示材料先验价值，则“协同增益”不成立。此时应将论文改写为视觉先验与力自适应的阶段性边界研究，并补充更高接触冲击、错误先验或未见对象条件，而不能仅依靠更换统计图维持正面结论。
"""
    (DIRS["manuscript"] / "literature_innovation_review_zh.md").write_text(content, encoding="utf-8")


def write_manuscript(metrics: pd.DataFrame, contrasts: pd.DataFrame, lmm: pd.DataFrame, lmm_info: dict, sensitivity: pd.DataFrame, source_trial_count: int) -> None:
    metric = "primary_excess_impulse_Ns_0p2_1p0"
    mode_stats = metrics.groupby("mode")[metric].agg(["mean", "std", "count"])
    op_stats = metrics.groupby("mode")["operation_time_s"].agg(["mean", "std"])
    peak_stats = metrics.groupby("mode")["initial_peak_force_N_0_0p2"].agg(["mean", "std"])
    adaptive_trials = metrics[metrics["mode"].isin(["force_only", "vision_force"])]
    convergence_missing = int(adaptive_trials["stiffness_convergence_s"].isna().sum())
    convergence_total = int(len(adaptive_trials))
    e_trials = metrics[metrics["mode"].eq("vision")]
    f_trials = metrics[metrics["mode"].eq("vision_force")]
    g_trials = metrics[metrics["mode"].eq("force_only")]
    e_lock_before = int(e_trials["vision_locked_before_contact"].sum())
    f_lock_before = int(f_trials["vision_locked_before_contact"].sum())
    e_transition_before = int(e_trials["vision_transition_complete_before_contact"].sum())
    f_transition_before = int(f_trials["vision_transition_complete_before_contact"].sum())
    f_online_rate = float(f_trials["online_update_observed"].mean())
    g_online_rate = float(g_trials["online_update_observed"].mean())
    f_update_interval = float(f_trials["online_update_interval_median_s"].median())
    g_update_interval = float(g_trials["online_update_interval_median_s"].median())
    observed_loop_hz = float(metrics["observed_control_loop_hz"].median())
    c_map = {r["contrast"]: r for _, r in contrasts.iterrows()}
    c_fe = c_map["F - E（融合相对视觉先验）"]
    c_fg = c_map["F - G（融合相对纯力自适应）"]
    c_int = c_map["2×2 交互 (F-E-G+A)"]
    synergy_supported = bool(c_fe["ci95_high"] < 0 and c_fg["ci95_high"] < 0)
    verdict = (
        "结果同时支持融合模式相对视觉先验和纯力自适应的增量优势，因此可谨慎表述前馈—反馈协同。"
        if synergy_supported
        else "结果未同时满足融合模式相对视觉先验与纯力自适应均改善的门槛，因此本文将结论限定为两类信息的阶段性作用与边界，不宣称普遍协同增益。"
    )
    sensitivity_lines = []
    for analysis, g in sensitivity.groupby("analysis"):
        row = g[g["contrast"] == "F - E（融合相对视觉先验）"].iloc[0]
        sensitivity_lines.append(
            f"- {analysis}（{int(row.n_blocks)} 个完整配对块，{int(row.n_trials_analyzed)} 次试验）："
            f"F−E = {row.mean_difference:.3f} N·s，95% CI [{row.ci95_low:.3f}, {row.ci95_high:.3f}]，Holm p={row.p_holm:.3f}。"
        )
    mode_sentence = "；".join(
        f"{MODE_SHORT[m]} {mode_stats.loc[m, 'mean']:.3f}±{mode_stats.loc[m, 'std']:.3f} N·s"
        for m in MODE_ORDER
    )
    duplicate_methods = (
        "源目录共含186条记录，其中6个条件单元各有一次后续补测。"
        "为保留端到端识别错误，主分析预先固定为每个单元时间戳最早的首测180条；"
        "后补记录仅用于改用补测和186条单元均值两套敏感性分析。"
        if source_trial_count == 186
        else "当前数据目录包含180个唯一且平衡的首测试次。"
    )
    sensitivity_text = (
        "主分析及三套预设敏感性分析的 F−E 结果如下：\n\n"
        + chr(10).join(sensitivity_lines)
        + "\n\n两项视觉时序敏感性分析均以完整匹配块为单位排除，避免逐条删除造成2×2配对破坏；"
        "软/中材料分析用于检验结论是否受硬材料固定柔化分支影响。"
    )
    manuscript = rf"""# 视觉语义先验约束的接触感知在线变阻抗遥操作：异质物体抓取中的阶段性作用与边界

## 摘要

异质物体遥操作抓取同时面临接触前物体属性未知与接触后交互状态变化两类问题。视觉语义能够在接触前提供材料属性先验，但离散参数预设不能反映接触位置、抓取姿态及局部形变造成的实际差异；纯力反馈自适应能够响应真实交互，却只能在接触发生后调节。针对这一时序互补关系，本文构建了一种接触事件分段、材料语义限定的在线变阻抗方法。目标类别首先映射为软质、中等和硬质三类交互先验，确定平动刚度基线及允许区间；检测到接触并经过 0.2 s 延迟后，系统以20 Hz根据材料相关死区、饱和力和修正增益对阻抗实施有界平滑更新。基于 Omega.7–Franka Panda–RealSense 平台，5 位操作者在三类物体条件下完成固定参数、纯力自适应、视觉先验和视觉–力融合四种模式，共形成 45 个完整匹配块和 180 个主分析试次。以接触后 0.2–1.0 s 基线校正超阈值力冲量为主要指标，融合模式相对视觉先验模式的配对差为 {c_fe.mean_difference:.3f} N·s（95% CI [{c_fe.ci95_low:.3f}, {c_fe.ci95_high:.3f}]，Holm 校正 p={c_fe.p_holm:.3f}），相对纯力自适应模式的差为 {c_fg.mean_difference:.3f} N·s（95% CI [{c_fg.ci95_low:.3f}, {c_fg.ci95_high:.3f}]，p={c_fg.p_holm:.3f}）。{verdict}本文的贡献在于用事件对齐与因子消融分离视觉先验和力反馈在不同接触阶段的作用，并给出离散刚度更新的区间不变性与收敛性质。该结果适用于当前平台、对象集合和参数范围，不构成完整闭环钝性保证。

**关键词：** 遥操作；变阻抗控制；视觉语义；接触力反馈；人机在环；异质物体

## 1 引言

遥操作将人的认知决策与机器人的远程执行能力结合，适用于危险环境、远程维护和非结构化操作。对于抓取和搬运任务，操作者不仅需要控制末端运动，还需要在接触瞬间与持续抓取阶段维持适当的柔顺性。统一固定参数难以覆盖具有不同变形敏感性、摩擦条件和位姿保持需求的物体：过高刚度可能增加接触冲击，过低刚度又会削弱轨迹保持和抓取稳定性。

已有遥阻抗研究允许操作者或自主模块调节从端阻抗。Huang 等利用视觉识别材料与脆弱性，在接触前为遥操作机器人选择阻抗；Siegemund 等进一步将材料、几何以及物体与环境关系纳入刚度估计。上述工作证明了视觉对象属性对于接触前设置的价值，但其主要作用仍是生成离散或准静态阻抗。另一方面，自适应变阻抗与力跟踪研究根据实际交互状态在线调节阻抗，并常通过 Lyapunov、钝性或能量罐方法处理稳定性。OmniVIC 则把视觉语言模型生成的高层控制先验与实时力/力矩约束结合，说明视觉语义与力反馈的融合本身已不是研究空白。

因此，本文不把“视觉选择阻抗”或“视觉–力融合”作为宽泛首创，而关注一个更具体的问题：在人机在环抓取中，接触前语义先验和接触后外力反馈分别在何时起作用，材料语义是否能够为在线刚度修正提供比统一力反馈更有解释力的约束？为回答该问题，本文将试验组织为视觉先验×力自适应的 2×2 配对设计，并依据自动事件日志将一次操作划分为基线、初始接触、自适应、抓取及搬运释放阶段。

本文贡献如下：

1. 提出一种接触事件分段的语义先验约束在线变阻抗结构，视觉通道给出材料相关基线与可行域，F模式在接触事件后连续修正阻抗。
2. 设计材料相关的力死区、饱和力、修正增益与刚度边界，使接触后在线调节保持有界并具有明确物理解释。
3. 建立 5 位操作者、三类材料、四模式、45 个匹配块的 2×2 消融试验，采用事件对齐的接触过程指标而非仅比较全程均值。
4. 给出离散平滑更新的区间不变性和常值目标下的指数收敛结论，同时明确其不等价于完整遥操作闭环的钝性证明。

## 2 系统与控制方法

### 2.1 实验平台与主从映射

系统由 Omega.7 力反馈主端、七自由度 Franka Panda 从端、Franka Hand 夹爪、RealSense D435i RGB 相机和控制计算机构成（图 1）。操作者的主端平移增量经比例系数与坐标变换后更新从端期望位置，末端期望姿态在单次试验内保持固定。监督循环以名义 200 Hz 运行，完成主端采样、末端期望更新、力反馈、夹爪状态机、事件检测与数据记录。视觉采集以 15 fps 运行，目标检测进程与监督循环异步解耦。

设主端位置为 $p_m(k)$，从端期望位置为 $p_d(k)$，则

$$
\Delta p_m(k)=p_m(k)-p_m(k-1),\qquad
p_d(k)=p_d(k-1)+SC\Delta p_m(k),
$$

其中 $S=3.0$ 为位置比例，$C=\mathrm{{diag}}(-1,-1,1)$ 为坐标方向映射。

### 2.2 从端笛卡尔阻抗

从端笛卡尔阻抗作用写为

$$
w_c=K(t)e+D(t)\dot e,
$$

其中 $e$ 和 $\dot e$ 为位姿误差与误差变化率。平动刚度 $K_t$、旋转刚度 $K_r$ 及阻尼比例共同构成控制接口所需的对角阻抗参数。本文在线调节 $K_t$，并保持 $K_r/K_t$ 的类别相关比例，使旋转刚度随平动刚度同步变化。

### 2.3 接触前视觉语义先验

视觉识别的物体类别 $c$ 首先映射为材料语义 $m\in\{{soft,medium,hard\}}$，再得到类别相关基线 $K_{{base}}(m)$、允许区间 $[K_{{min}}(m),K_{{max}}(m)]$ 以及力反馈调节参数。视觉结果在单次试验首次达到置信阈值后锁定，以避免识别波动导致反复切换。

该先验并不估计连续的真实材料模量，而是面向当前平台和任务定义的操作属性标签。其功能是使机器人在首次接触前进入与变形敏感性和位姿保持需求相匹配的参数区域。

### 2.4 接触检测与在线刚度修正

接触事件由末端外力模长超过个体试次的基线阈值触发。视觉–力融合模式在接触后等待 0.2 s，再以 0.05 s 周期更新阻抗。对材料 $m$，定义归一化接触强度

$$
s(F;m)=\mathrm{{clip}}\left(\frac{{|F|-F_{{db}}(m)}}{{F_{{sat}}(m)-F_{{db}}(m)}},0,1\right).
$$

目标刚度为

$$
K^*(F,m)=\mathrm{{clip}}\left[K_{{base}}(m)(1+g(m)s(F;m)),K_{{min}}(m),K_{{max}}(m)\right],
$$

其中 $g(m)<0$。软质和中等材料中，外力增大时目标刚度在预定范围内降低；硬材料由于原始目标区间 $[170,200]$ N/m 被 $K_{{max}}=170$ N/m 截断，裁剪后的目标恒为170 N/m，因此该分支属于接触事件触发的固定柔化，而非力幅值连续调制。实际命令采用一阶平滑：

$$
K_{{n+1}}=(1-\beta_m)K_n+\beta_mK^*_n,\qquad 0<\beta_m\le 1.
$$

软质、中等和硬质类别分别采用不同的死区、饱和力、增益、平滑系数和刚度边界。纯力自适应模式使用统一基线与统一外力调节律，不使用视觉标签，也不采用接触事件门控；视觉先验模式仅设置类别基线而不执行接触后修正；固定模式始终保持默认参数（图 2）。

## 3 数学性质

### 3.1 刚度区间不变性

若初始刚度 $K_0\in[K_{{min}},K_{{max}}]$，且裁剪后的目标 $K^*_n$ 始终位于同一区间，则 $K_{{n+1}}$ 是 $K_n$ 与 $K^*_n$ 的凸组合。因此对任意 $n$ 均有

$$
K_n\in[K_{{min}},K_{{max}}].
$$

该性质保证在线修正不会产生超出控制器预定范围的刚度命令。

### 3.2 常值目标下的收敛

当外力在局部时间段内保持不变，使 $K^*_n=K^*$ 时，定义误差 $\tilde K_n=K_n-K^*$，可得

$$
\tilde K_{{n+1}}=(1-\beta_m)\tilde K_n,
$$

从而

$$
|\tilde K_n|=(1-\beta_m)^n|\tilde K_0|.
$$

因此 $0<\beta_m\le1$ 时，刚度以指数形式收敛至局部目标。该结论只描述阻抗参数更新器本身的有界性与收敛性，不能替代包含操作者、主端、从端、时延和环境动力学的完整闭环钝性分析。

## 4 实验设计与统计方法

### 4.1 试验设计

5 位操作者分别在软质、中等和硬质对象条件下完成 3 个重复匹配组。每个匹配组包含 A 固定参数、G 纯力自适应、E 视觉先验和 F 视觉–力融合四种模式，共 45 个匹配组和 180 个主分析试次。{duplicate_methods} 当前日志能够确认材料条件、操作者、组别和模式，但实际物体编号仍需根据实验记录补录；在补录完成前，“配对”严格指实验条件块配对，而不是已验证的同一实体物体配对。

所有 180 个主分析试次均同时满足完成、抓取成功和任务结束成功标记，描述性成功率为100%，因此成功率不能区分模式。由于本数据集尚不包含与当前四模式试验严格对应的 NASA-TLX，当前稿不报告或混入旧试验的主观量表结果；后续回顾性填写将明确标注回忆偏倚。

### 4.2 事件与指标

日志包含 `vision_lock`、`contact_onset`、`grasp_start`、`grasp_success`、`release_start` 和 `task_end` 等事件。接触事件依据Franka内部模型外力估计 `O_F_ext_hat_K` 超过试次基线阈值并持续50 ms判定，不等价于独立力传感器真值。以 `contact_onset` 为零点，将接触前 0.5 s 用作基线；0–0.2 s 定义为初始接触阶段；0.2–1.0 s 定义为自适应阶段。

主要指标为自适应阶段的基线校正超阈值力冲量：

$$
J_F=\int_{{0.2}}^{{1.0}}\max(|F(t)|-F_{{th}},0)\,dt.
$$

次要指标包括初始接触峰值力、超阈值持续时间、接触至抓取成功时间、刚度修正幅值、刚度收敛时间、全程完成时间、轨迹长度与速度波动。

### 4.3 统计分析

主要指标采用含操作者与匹配组随机截距的限制最大似然混合模型，固定效应包括视觉、力自适应、材料及其交互。预定义三个配对对比：F−E、F−G 和 2×2 交互项 F−E−G+A。配对均值差的 95% 置信区间由 10,000 次自助抽样获得，p 值由 50,000 次配对符号置换估计，并采用 Holm 方法校正。所有统计均为双侧，重点依据效应量和置信区间解释。

## 5 结果

### 5.1 数据完整性与描述性结果

四模式主指标均值为：{mode_sentence}。初始接触峰值分别为 A {peak_stats.loc['default','mean']:.3f}±{peak_stats.loc['default','std']:.3f} N、G {peak_stats.loc['force_only','mean']:.3f}±{peak_stats.loc['force_only','std']:.3f} N、E {peak_stats.loc['vision','mean']:.3f}±{peak_stats.loc['vision','std']:.3f} N 和 F {peak_stats.loc['vision_force','mean']:.3f}±{peak_stats.loc['vision_force','std']:.3f} N。全任务时间分别为 A {op_stats.loc['default','mean']:.2f}±{op_stats.loc['default','std']:.2f} s、G {op_stats.loc['force_only','mean']:.2f}±{op_stats.loc['force_only','std']:.2f} s、E {op_stats.loc['vision','mean']:.2f}±{op_stats.loc['vision','std']:.2f} s 和 F {op_stats.loc['vision_force','mean']:.2f}±{op_stats.loc['vision_force','std']:.2f} s。全程时间不作为证明接触安全性的主要证据。事件审计显示，E模式有 {e_lock_before}/45 次、F模式有 {f_lock_before}/45 次在接触事件前完成视觉锁定；按锁定后至少0.3 s完成参数过渡的严格标准，分别为 {e_transition_before}/45 和 {f_transition_before}/45 次。

### 5.2 主要指标与预定义对比

F−E 的超阈值力冲量配对差为 {c_fe.mean_difference:.3f} N·s，95% CI [{c_fe.ci95_low:.3f}, {c_fe.ci95_high:.3f}]，标准化配对效应 $d_z={c_fe.dz:.3f}$，Holm 校正 p={c_fe.p_holm:.3f}。F−G 的差为 {c_fg.mean_difference:.3f} N·s，95% CI [{c_fg.ci95_low:.3f}, {c_fg.ci95_high:.3f}]，$d_z={c_fg.dz:.3f}$，p={c_fg.p_holm:.3f}。2×2 交互项为 {c_int.mean_difference:.3f} N·s，95% CI [{c_int.ci95_low:.3f}, {c_int.ci95_high:.3f}]，p={c_int.p_holm:.3f}。

{verdict}因此，本文对“协同”的使用严格服从预设门槛，并将不满足门槛的结果解释为信息通道作用边界，而非统计失败。

### 5.3 接触过程与刚度响应

图 4 以接触事件对齐展示三类材料下外力和刚度的时间演化。0–0.2 s 内 F 与 E 共享视觉基线，理论上主要检验前接触参数预设；0.2 s 后 F 模式启动材料相关在线修正，而 E 保持视觉基线。G 模式的统一外力调节可用于判断材料先验是否带来超出一般柔顺化的增量价值。

刚度日志表明，F和G模式观测到在线刚度更新的试次比例分别为 {f_online_rate:.1%} 和 {g_online_rate:.1%}；监督循环实测中位频率为 {observed_loop_hz:.1f} Hz，F和G的刚度变化时间间隔中位数分别为 {f_update_interval:.3f} s和 {g_update_interval:.3f} s，与20 Hz上层更新设置一致。底层Cartesian impedance controller根据刚度及阻尼比计算控制增益并在机器人力矩环执行，因此本文将实现称为在线变阻抗，而不是离线参数选择。F模式的在线命令保持在各材料预设边界内。按“进入终值5%容差并持续0.2 s”的探索性判据，{convergence_missing}/{convergence_total} 个自适应试次在1.5 s观察窗内未达到收敛，属于右删失；因此不将收敛时间用于模式优劣推断。参数更新有界且平滑只能确认实现层面的参数安全边界，不能推出任意环境下的闭环稳定性。

### 5.4 敏感性分析

{sensitivity_text}

## 6 讨论

### 6.1 与相关工作的区别

Huang 等和 Siegemund 等已经证明视觉对象属性可用于接触前阻抗选择，本文不重复声称该映射为首创。本文的增量是将视觉输出限定为在线调节的材料条件，并利用接触事件将“首次接触前的准备”与“接触后的真实状态修正”明确分开。与 OmniVIC 的通用 VLM 推理不同，本文采用小规模、可解释、确定性的材料策略，优势是控制逻辑透明、计算负担低，代价是泛化能力有限。

与一般纯力自适应相比，材料相关策略不是把外力直接映射到统一刚度，而是同时改变死区、饱和区、增益和允许边界。F−G 对比因此是检验视觉先验增量价值的关键，F−E 则检验接触后反馈的增量价值。只有二者均获得支持，才可以讨论前馈与反馈的协同。

### 6.2 结果解释

{verdict} 该结论比“融合模式总体最好”的表述更严格，因为它要求改善发生在算法实际生效的 0.2–1.0 s 窗口，并要求相对两个单模块条件均有证据。全程完成时间受操作者策略、抓取路径和释放动作影响，不能替代接触过程指标。

### 6.3 局限与补实验建议

本研究仅包含5位操作者和每类三组重复，操作者层面的随机效应估计仍不稳定；三种材料标签是操作属性类别而非连续材料力学参数；实际物体编号尚待补录，当前匹配首先是条件块匹配；末端外力来自Panda内部估计，不是独立校准的接触传感器；8个视觉试次按日志判定为接触早于视觉锁定，可能来自真实提前接触、识别延迟或接触检测假阳性；G模式没有接触门控并在部分试次中出现接触前刚度变化；硬材料F分支裁剪后目标恒为170 N/m，不能作为力幅值连续自适应证据；所有试次均成功，使成功率无法区分模式；当前对象与任务不足以证明对未见对象、错误视觉先验或高冲击接触的鲁棒性。

若主要交互效应不能成立，最小补实验应增加三类条件：一是提高接触速度或设置受控扰动，扩大接触瞬态差异；二是加入视觉标签错误或 unknown 条件，验证安全回退；三是每类加入未参与参数设定的新对象，检验材料策略的类内泛化。若目标期刊强调控制理论，还需要在新实现中加入能量罐或明确的刚度变化率约束，并重新采集验证数据。

## 7 结论

本文围绕人机在环异质物体抓取，研究了视觉材料先验和接触力反馈在变阻抗遥操作中的阶段性作用。系统在接触前根据物体语义确定阻抗基线和材料相关边界，在接触后根据真实外力进行有界平滑修正，并通过四模式 2×2 配对消融和接触事件对齐进行验证。主要指标结果显示，F−E 为 {c_fe.mean_difference:.3f} N·s，F−G 为 {c_fg.mean_difference:.3f} N·s，交互项为 {c_int.mean_difference:.3f} N·s。{verdict}研究同时证明了参数更新器的区间不变性和常值目标下的收敛性，但不宣称完整遥操作闭环的钝性或对未见环境的普适安全性。

## 参考文献（第一版）

1. Ajoudani A, Tsagarakis N G, Bicchi A. Tele-impedance: Teleoperation with impedance regulation using a body-machine interface. *International Journal of Robotics Research*, 2012.
2. Huang Y C, Abbink D A, Peternel L. A Semi-Autonomous Tele-Impedance Method based on Vision and Voice Interfaces. *ICAR*, 2021. https://doi.org/10.1109/ICAR53236.2021.9659427
3. Siegemund G, Díaz Rosales A, Glodde A, et al. Semi-autonomous Teleimpedance Based on Visual Detection of Object Geometry and Material and its Relation to Environment. *Humanoids*, 2024. https://doi.org/10.1109/Humanoids58906.2024.10769858
4. Zhang H, Huang W H, Solak G, Ajoudani A. OmniVIC: A Self-Improving Variable Impedance Controller with Vision-Language In-Context Learning for Safe Robotic Manipulation. 2025. https://arxiv.org/abs/2510.17150
5. Duan J, Gan Y, Chen M, Dai X. Adaptive variable impedance control for dynamic contact force tracking in uncertain environment. *Robotics and Autonomous Systems*, 2018. https://doi.org/10.1016/j.robot.2018.01.009
6. Michel Y, Saveriano M, Lee D. A Passivity-based Approach for Variable Stiffness Control with Dynamical Systems. 2023. https://arxiv.org/abs/2307.09571
7. Yang Q, Dürr A, Topp E A, et al. Variable impedance skill learning for contact-rich manipulation. *IEEE Robotics and Automation Letters*, 2022. https://doi.org/10.1109/LRA.2022.3187276
8. Zeng C, Li S, Jiang Y, et al. Learning compliant grasping and manipulation by teleoperation with adaptive force control. 2021. https://arxiv.org/abs/2107.08996

---

**统计实现说明：** 双随机截距模型由 SciPy 实现限制最大似然估计。优化状态：{lmm_info['converged']}；样本量 n={lmm_info['n']}；操作者方差={lmm_info['variance_operator']:.6f}；匹配组方差={lmm_info['variance_block']:.6f}；残差方差={lmm_info['variance_residual']:.6f}。
"""
    (DIRS["manuscript"] / "paper2_chinese_manuscript_v1.md").write_text(manuscript, encoding="utf-8")


def write_figure_captions() -> None:
    captions = """# 正文图表清单与图注

## 图

1. **图 1 人机在环视觉-力融合遥操作平台与数据流。** 视觉通道异步提供接触前材料先验，Panda 外力估计用于接触事件检测、接触后在线刚度修正及主端触觉反馈。
2. **图 2 接触前视觉先验与接触后力反馈修正及四模式消融。** A、G、E、F 分别对应视觉与力自适应两个因子的四种组合。
3. **图 3 离散刚度更新律、材料边界与事件时间线。** 左侧为材料相关目标刚度示意，右侧给出预定义分析窗口。
4. **图 4 不同材料与模式的接触对齐外力和刚度响应。** 曲线为试次均值，阴影为正态近似 95% 置信区间；0.2 s 虚线表示融合模式在线修正开始时间。
5. **图 5 主指标的原始分布与预定义配对效应。** 负的 F−E 或 F−G 表示融合模式的超阈值力冲量较低。
6. **图 6 材料交互、刚度修正与分阶段效率。** 展示主指标的模式×材料关系、两种自适应模式的最大刚度降低幅值和操作阶段耗时。

## 表

1. 表 1：相关研究的视觉/材料/力反馈/阻抗/验证/数学性质对比。
2. 表 2：四模式的 2×2 因子定义。
3. 表 3：事件分析窗口及评价指标。
4. 表 4：主要配对对比、效应量、置信区间及敏感性结果。
"""
    (DIRS["manuscript"] / "figure_table_captions_zh.md").write_text(captions, encoding="utf-8")


def write_data_entry_templates(metrics: pd.DataFrame) -> None:
    background_header = (
        "participant_id,age,sex,dominant_hand,robotics_experience_years,"
        "teleoperation_experience_level,vision_status,prior_training_minutes,"
        "consent_confirmed,notes"
    )
    background_rows = [f"P{i:02d},,,,,,,,," for i in range(1, 6)]
    (DIRS["manuscript"] / "participant_background_template.md").write_text(
        background_header + "\n" + "\n".join(background_rows) + "\n", encoding="utf-8"
    )

    tlx_header = (
        "operator,object_class,mode,mental_demand,physical_demand,temporal_demand,"
        "performance,effort,frustration,notes"
    )
    tlx_rows = []
    for participant in [f"P{i:02d}" for i in range(1, 6)]:
        for material in MATERIAL_ORDER:
            for mode in MODE_ORDER:
                tlx_rows.append(f"{participant},{material},{mode},,,,,,,")
    (DIRS["manuscript"] / "nasa_tlx_template.md").write_text(
        tlx_header + "\n" + "\n".join(tlx_rows) + "\n", encoding="utf-8"
    )

    failure_header = (
        "attempt_id,operator,object_class,actual_object_id,mode,block,attempt_time,"
        "completed,grasp_success,drop_occurred,collision_occurred,emergency_stop,"
        "failure_stage,failure_reason,recovery_action,include_in_success_rate,notes"
    )
    (DIRS["manuscript"] / "failure_log_template.md").write_text(
        failure_header + "\n", encoding="utf-8"
    )

    object_header = (
        "trial_key,operator,object_class,block,mode,timestamp,actual_object_id,"
        "actual_object_name,material_verified,same_object_within_block,notes"
    )
    object_rows = []
    ordered = metrics.sort_values(["participant", "material", "block", "mode"])
    for _, row in ordered.iterrows():
        object_rows.append(
            f"{row.trial_key},{row.participant},{row.material},{row.block},{row['mode']},"
            f"{row.timestamp},,,,,"
        )
    (DIRS["manuscript"] / "actual_object_labels_template.md").write_text(
        object_header + "\n" + "\n".join(object_rows) + "\n", encoding="utf-8"
    )

    instructions = """# 补充数据填写说明

- 四个模板均采用逗号分隔文本，填写时不要修改首行字段名。
- 本稿不使用回顾性 NASA-TLX；现有量表模板仅保留归档，不进入第二篇论文统计。
- `failure_log_template.md` 仅记录真实发生的额外尝试或失败，不得根据当前成功试次反推或虚构失败。主分析180份首测日志均为任务完成记录；视觉误识别仍保留在端到端识别分析中。
- `actual_object_labels_template.md` 用于补充每次实验实际使用的物体。`same_object_within_block` 只有在同一操作者、材料和组别的四模式确实使用同一物体时填写1，否则填写0。
- 背景信息和知情同意字段以伦理审批及原始记录为准；未知字段留空，不作推测。
"""
    (DIRS["manuscript"] / "data_entry_template_README.md").write_text(instructions, encoding="utf-8")


def write_delivery_readme(source_trial_count: int) -> None:
    content = f"""# 正宫 交付说明

本目录由 `paper2_pipeline.py` 从只读源目录 `{SOURCE}` 生成。

## 目录

- 原始 CSV、events 和 summary 只从 `{SOURCE}` 读取，不在本目录生成副本。
- `02_audit`：全部 {source_trial_count} 条记录的审计清单和 SHA-256。
- `03_processed_data`：主分析、敏感性分析和接触对齐后的派生数据。
- `04_statistics`：描述统计、配对对比、混合模型、视觉时序/在线机制/策略数学审计、敏感性分析和四张正文表。
- `05_figures`：6 幅正文图，每幅含 SVG、PDF 和 600 dpi PNG。
- `06_manuscript`：文献创新性审查、中文版论文第一稿、图表说明及记录模板。
- `07_supplement_experiment`：先验可信度闭环的8次预试、80次正式顺序及失败/背景记录表。

## 复现

在 `F:\\sun\\sunhan` 下执行：

```powershell
python .\\my_test\\paper2_pipeline.py
```

再次执行不会修改原始数据；已复制且大小一致的文件会跳过。

## 重要解释边界

- 当前源目录含 {source_trial_count} 条记录；主分析固定使用每个条件单元的最早首测180条，后补记录仅作敏感性分析。
- 全部成功，因此成功率仅描述，不做模式优劣推断。
- E/F视觉时序敏感性按完整2×2匹配块排除，不逐条删除试次。
- F/G均有在线阻抗更新证据；硬材料F分支为接触触发固定柔化，不表述为力幅值连续调制。
- 实际物体编号尚待人工补录；完成前只称条件块配对，不称同一实体物体严格配对。
- 数学证明仅覆盖刚度更新器的有界性与局部收敛，不是完整闭环钝性证明。
- 论文是否可表述“协同增益”由 F−E 与 F−G 两个预定义对比的置信区间共同决定。
"""
    (OUT / "README.md").write_text(content, encoding="utf-8")


def main() -> None:
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    ensure_dirs()
    setup_plotting()
    trials = discover_trials()
    manifest = write_manifest(trials)
    earliest = [t for t in trials if t.selected_earliest]
    latest = [t for t in trials if t.selected_latest]

    metrics_main, aligned = metrics_for_trials(earliest, keep_series=True)
    metrics_main.to_csv(DIRS["processed"] / "trial_metrics_main_180.csv", index=False, encoding="utf-8-sig")
    if len(trials) == 186:
        metrics_retest, _ = metrics_for_trials(latest, keep_series=False)
        metrics_all, _ = metrics_for_trials(trials, keep_series=False)
        metrics_retest.to_csv(DIRS["processed"] / "trial_metrics_latest_retest_180.csv", index=False, encoding="utf-8-sig")
        metrics_all.to_csv(DIRS["processed"] / "trial_metrics_all_186.csv", index=False, encoding="utf-8-sig")
    aligned_summary = aggregate_aligned(aligned)
    aligned_summary.to_csv(DIRS["processed"] / "aligned_timeseries_summary.csv", index=False, encoding="utf-8-sig")

    primary = "primary_excess_impulse_Ns_0p2_1p0"
    c_main, wide_main = contrast_table(metrics_main, primary, "main_all_180")
    c_main["n_trials_analyzed"] = len(metrics_main)
    sensitivity, timing_block_audit = build_sensitivity_analyses(metrics_main, primary)
    if len(trials) == 186:
        c_retest, _ = contrast_table(metrics_retest, primary, "sensitivity_latest_retest_180")
        c_all, _ = contrast_table(metrics_all, primary, "sensitivity_all_186_cell_mean")
        c_retest["n_trials_analyzed"] = len(metrics_retest)
        c_all["n_trials_analyzed"] = len(metrics_all)
        sensitivity = pd.concat([sensitivity, c_retest, c_all], ignore_index=True)
    wide_main.to_csv(DIRS["processed"] / "paired_block_primary_data.csv", index=False, encoding="utf-8-sig")
    sensitivity.to_csv(DIRS["stats"] / "sensitivity_results.csv", index=False, encoding="utf-8-sig")
    timing_block_audit.to_csv(
        DIRS["stats"] / "vision_prior_timing_block_audit.csv", index=False, encoding="utf-8-sig"
    )

    all_contrasts = []
    for metric in [
        primary,
        "initial_peak_force_N_0_0p2",
        "excess_duration_s_0p2_1p0",
        "contact_to_grasp_success_s",
        "operation_time_s",
        "trajectory_length_m",
        "whole_peak_force_N",
    ]:
        table, _ = contrast_table(metrics_main, metric, "main_all_180")
        table["n_trials_analyzed"] = len(metrics_main)
        all_contrasts.append(table)
    model_results = pd.concat(all_contrasts, ignore_index=True)
    model_results.to_csv(DIRS["stats"] / "predefined_contrasts_all_metrics.csv", index=False, encoding="utf-8-sig")

    lmm, lmm_info = fit_reml_random_intercepts(metrics_main, primary)
    lmm.to_csv(DIRS["stats"] / "mixed_effects_primary.csv", index=False, encoding="utf-8-sig")
    (DIRS["stats"] / "mixed_effects_primary_info.json").write_text(
        json.dumps(lmm_info, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    descriptive = descriptive_table(metrics_main)
    descriptive.to_csv(DIRS["stats"] / "descriptive_by_material_mode.csv", index=False, encoding="utf-8-sig")
    online_summary = online_mechanism_summary(metrics_main)
    online_summary.to_csv(DIRS["stats"] / "online_mechanism_audit.csv", index=False, encoding="utf-8-sig")
    fusion_policy = fusion_policy_audit_table()
    fusion_policy.to_csv(DIRS["stats"] / "fusion_policy_mathematical_audit.csv", index=False, encoding="utf-8-sig")

    figure_data = metrics_main[[
        "participant", "material", "block", "block_id", "mode", "visual", "force_adaptive",
        primary, "initial_peak_force_N_0_0p2", "excess_duration_s_0p2_1p0",
        "contact_to_grasp_success_s", "grasp_to_release_s", "release_duration_s",
        "operation_time_s", "stiffness_convergence_s", "stiffness_delta_min_N_m",
        "vision_lead_to_contact_s", "vision_locked_before_contact",
        "vision_transition_complete_before_contact", "online_update_observed",
        "online_update_interval_median_s", "online_stiffness_change_count",
        "precontact_stiffness_range_N_m", "adaptive_window_stiffness_range_N_m",
        "force_stiffness_spearman_0p2_1p0",
    ]].copy()
    figure_data.to_csv(DIRS["stats"] / "figure_data_trial_level.csv", index=False, encoding="utf-8-sig")
    aligned_summary.to_csv(DIRS["stats"] / "figure_data_aligned_curves.csv", index=False, encoding="utf-8-sig")

    write_tables(descriptive, c_main, sensitivity)
    fig1_system()
    fig2_control()
    fig3_update_law()
    fig4_aligned(aligned_summary)
    fig5_primary(metrics_main, c_main)
    fig6_interactions(metrics_main)
    write_literature_review()
    write_manuscript(metrics_main, c_main, lmm, lmm_info, sensitivity, len(trials))
    write_figure_captions()
    write_data_entry_templates(metrics_main)
    write_delivery_readme(len(trials))

    summary = {
        "all_trials": len(trials),
        "main_trials": len(metrics_main),
        "main_blocks": int(metrics_main["block_id"].nunique()),
        "all_success": bool(metrics_main["success"].eq(1).all()),
        "vision_timing": {
            "E_lock_before_contact": int(metrics_main.loc[metrics_main["mode"].eq("vision"), "vision_locked_before_contact"].sum()),
            "F_lock_before_contact": int(metrics_main.loc[metrics_main["mode"].eq("vision_force"), "vision_locked_before_contact"].sum()),
            "E_transition_complete_before_contact": int(metrics_main.loc[metrics_main["mode"].eq("vision"), "vision_transition_complete_before_contact"].sum()),
            "F_transition_complete_before_contact": int(metrics_main.loc[metrics_main["mode"].eq("vision_force"), "vision_transition_complete_before_contact"].sum()),
        },
        "online_update_observed": metrics_main.groupby("mode")["online_update_observed"].mean().to_dict(),
        "main_contrasts": c_main.to_dict(orient="records"),
        "sensitivity_contrasts": sensitivity.to_dict(orient="records"),
        "mixed_model": lmm_info,
        "outputs": {k: str(v) for k, v in DIRS.items()},
    }
    (OUT / "analysis_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
