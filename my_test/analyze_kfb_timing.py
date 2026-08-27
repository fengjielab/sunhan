#!/usr/bin/env python3
"""Blinded reconstruction and descriptive analysis for the K_fb timing pilot."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from kfb_timing_protocol import (
    CONDITIONS,
    DEFAULT_CONFIG,
    classify_delivery,
    config_hash,
    sha256_file,
)


def _float(value, default=math.nan) -> float:
    try:
        result = float(value)
        return result if math.isfinite(result) else default
    except (TypeError, ValueError):
        return default


def _int(value, default=0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _mean(values: Sequence[float]) -> float:
    clean = [value for value in values if math.isfinite(value)]
    return statistics.fmean(clean) if clean else math.nan


def _median(values: Sequence[float]) -> float:
    clean = [value for value in values if math.isfinite(value)]
    return statistics.median(clean) if clean else math.nan


def _percentile(values: Sequence[float], probability: float) -> float:
    clean = sorted(value for value in values if math.isfinite(value))
    if not clean:
        return math.nan
    index = (len(clean) - 1) * probability
    low = int(math.floor(index))
    high = int(math.ceil(index))
    if low == high:
        return clean[low]
    weight = index - low
    return clean[low] * (1.0 - weight) + clean[high] * weight


def _read_csv(path: Path) -> List[dict]:
    with Path(path).open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: List[dict], fieldnames: Optional[List[str]] = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0]) if rows else []
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _json_safe(value):
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _load_manifests(data_dir: Path) -> List[dict]:
    manifests = []
    for path in sorted(Path(data_dir).rglob("*_manifest.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["_manifest_path"] = str(path.resolve())
        files = payload.get("files", {})
        for role in ("csv", "events", "summary"):
            item = files.get(role, {})
            file_path = Path(item.get("path", ""))
            if not file_path.is_absolute():
                file_path = path.parent / file_path
            item["resolved_path"] = str(file_path.resolve())
            item["exists"] = file_path.is_file()
            item["hash_verified"] = bool(
                item["exists"] and item.get("sha256") == sha256_file(file_path)
            )
        manifests.append(payload)
    trial_ids = [str(item.get("trial_id", "")) for item in manifests]
    if len(trial_ids) != len(set(trial_ids)):
        raise RuntimeError("duplicate trial_id found in manifests")
    return manifests


def _time_s(row: dict) -> float:
    value = _float(row.get("t_mono_ns"))
    if math.isfinite(value):
        return value / 1_000_000_000.0
    return _float(row.get("system_time"))


def _first_contact_time(rows: Sequence[dict]) -> float:
    for row in rows:
        if _int(row.get("contact_confirmed")) == 1:
            return _time_s(row)
        if "contact_confirmed" in str(row.get("event", "")).split("|"):
            return _time_s(row)
    return math.nan


def _active(row: dict) -> bool:
    state = str(row.get("intervention_state", ""))
    if state == "intervention":
        return True
    return _float(row.get("K_fb_commanded", row.get("K_fb"))) >= (
        DEFAULT_CONFIG.K_fb_baseline + DEFAULT_CONFIG.K_fb_intervention
    ) / 2.0


def _transition_times(rows: Sequence[dict], contact_s: float) -> Tuple[float, float]:
    if not math.isfinite(contact_s):
        return math.nan, math.nan
    previous = False
    onset = math.nan
    offset = math.nan
    for row in rows:
        current = _active(row)
        relative = _time_s(row) - contact_s
        if current and not previous and not math.isfinite(onset):
            onset = relative
        elif previous and not current and math.isfinite(onset):
            offset = relative
            break
        previous = current
    return onset, offset


def _exposure(rows: Sequence[dict], contact_s: float) -> float:
    if not math.isfinite(contact_s) or len(rows) < 2:
        return math.nan
    start = contact_s + DEFAULT_CONFIG.outcome_window_start_s
    end = contact_s + DEFAULT_CONFIG.outcome_window_end_s
    covered = 0.0
    active_duration = 0.0
    for left, right in zip(rows, rows[1:]):
        t0 = _time_s(left)
        t1 = _time_s(right)
        lo = max(t0, start)
        hi = min(t1, end)
        if hi <= lo:
            continue
        covered += hi - lo
        if _active(left):
            active_duration += hi - lo
    window = end - start
    if covered < window - DEFAULT_CONFIG.max_metric_gap_s:
        return math.nan
    return active_duration / window


def reconstruct_trial(manifest: dict) -> dict:
    files = manifest.get("files", {})
    csv_info = files.get("csv", {})
    triplet_ok = all(files.get(role, {}).get("hash_verified", False) for role in ("csv", "events", "summary"))
    trial_id = str(manifest.get("trial_id", ""))
    base = {
        "trial_id": trial_id,
        "masked_condition": str(manifest.get("masked_condition", "")),
        "config_sha256": str(manifest.get("config_sha256", "")),
        "manifest_path": manifest.get("_manifest_path", ""),
        "triplet_hash_verified": int(triplet_ok),
        "source_csv_sha256": csv_info.get("sha256", ""),
    }
    if not csv_info.get("exists", False):
        return {**base, "evaluable": 0, "reason": "missing_csv", "inferred_condition": "NOT_EVALUABLE"}
    rows = _read_csv(Path(csv_info["resolved_path"]))
    if len(rows) < 2:
        return {**base, "evaluable": 0, "reason": "insufficient_rows", "inferred_condition": "NOT_EVALUABLE"}
    contact_s = _first_contact_time(rows)
    onset_s, offset_s = _transition_times(rows, contact_s)
    phi = _exposure(rows, contact_s)
    evaluable = bool(triplet_ok and all(math.isfinite(value) for value in (contact_s, onset_s, offset_s, phi)))
    inferred = classify_delivery(onset_s, offset_s, phi) if evaluable else "NOT_EVALUABLE"
    reason = "ok" if evaluable else "missing_or_unverified_timing_evidence"
    return {
        **base,
        "evaluable": int(evaluable),
        "reason": reason,
        "contact_confirmed_s": contact_s,
        "detected_onset_relative_s": onset_s,
        "detected_offset_relative_s": offset_s,
        "epsilon_hat_s": onset_s - 0.20 if math.isfinite(onset_s) else math.nan,
        "phi_hat": phi,
        "inferred_condition": inferred,
    }


def command_reconstruct(data_dir: Path, output: Path) -> None:
    rows = [reconstruct_trial(manifest) for manifest in _load_manifests(data_dir)]
    _write_csv(output, rows)
    freeze = {
        "analysis_stage": "outcome_blind_fidelity_reconstruction",
        "config_sha256_expected": config_hash(DEFAULT_CONFIG),
        "trial_count": len(rows),
        "evaluable_count": sum(_int(row.get("evaluable")) for row in rows),
        "output_sha256": sha256_file(output),
        "outcome_columns_read": [],
    }
    freeze_path = output.with_suffix(".freeze.json")
    freeze_path.write_text(json.dumps(freeze, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {output} and {freeze_path}")


def _load_oracle(path: Path) -> Dict[str, dict]:
    rows = _read_csv(path)
    result = {row["trial_id"]: row for row in rows}
    if len(result) != len(rows):
        raise RuntimeError("duplicate trial_id in oracle")
    return result


def command_unblind(fidelity: Path, oracle_path: Path, output: Path) -> None:
    reconstructed = _read_csv(fidelity)
    oracle = _load_oracle(oracle_path)
    rows = []
    for row in reconstructed:
        trial_id = row["trial_id"]
        expected = oracle.get(trial_id)
        if expected is None:
            rows.append({**row, "oracle_match": 0, "oracle_reason": "trial_missing_from_oracle"})
            continue
        onset_hat = _float(row.get("detected_onset_relative_s"))
        phi_hat = _float(row.get("phi_hat"))
        scheduled_onset = _float(expected["scheduled_onset_s"])
        expected_phi = _float(expected["expected_phi"])
        rows.append({
            **row,
            "oracle_match": 1,
            "participant_id": expected["participant_id"],
            "phase": expected["phase"],
            "analyzed": expected["analyzed"],
            "true_condition": expected["true_condition"],
            "scheduled_onset_s": scheduled_onset,
            "scheduled_offset_s": _float(expected["scheduled_offset_s"]),
            "expected_epsilon_s": _float(expected["expected_epsilon_s"]),
            "expected_phi": expected_phi,
            "onset_error_s": onset_hat - scheduled_onset,
            "phi_error": phi_hat - expected_phi,
            "classification_correct": int(row.get("inferred_condition") == expected["true_condition"]),
            "mask_match": int(row.get("masked_condition") == expected["masked_condition"]),
            "config_match": int(
                row.get("config_sha256") == expected["config_sha256"] == config_hash(DEFAULT_CONFIG)
            ),
        })
    _write_csv(output, rows)
    evaluable = [row for row in rows if _int(row.get("evaluable")) == 1 and _int(row.get("oracle_match")) == 1]
    onset_errors = [abs(_float(row.get("onset_error_s"))) for row in evaluable]
    phi_errors = [abs(_float(row.get("phi_error"))) for row in evaluable]
    report = {
        "fidelity_freeze_sha256": sha256_file(fidelity),
        "oracle_sha256": sha256_file(oracle_path),
        "trial_count": len(rows),
        "evaluable_count": len(evaluable),
        "timing_mae_s": _mean(onset_errors),
        "timing_p95_abs_error_s": _percentile(onset_errors, 0.95),
        "timing_max_abs_error_s": max(onset_errors, default=math.nan),
        "exposure_mae": _mean(phi_errors),
        "classification_accuracy": (
            _mean([_int(row.get("classification_correct")) for row in evaluable])
            if evaluable else math.nan
        ),
        "not_evaluable_rate": 1.0 - len(evaluable) / len(rows) if rows else math.nan,
    }
    output.with_suffix(".report.json").write_text(
        json.dumps(_json_safe(report), ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


def _window_rows(rows: Sequence[dict], contact_s: float, start_rel: float, end_rel: float) -> List[dict]:
    return [
        row for row in rows
        if contact_s + start_rel <= _time_s(row) <= contact_s + end_rel
    ]


def _integral_trapezoid(times: Sequence[float], values: Sequence[float], max_gap: float) -> float:
    total = 0.0
    used = 0
    for t0, t1, v0, v1 in zip(times, times[1:], values, values[1:]):
        dt = t1 - t0
        if 0 < dt <= max_gap and all(math.isfinite(value) for value in (v0, v1)):
            total += 0.5 * (v0 + v1) * dt
            used += 1
    return total if used else math.nan


def trial_metrics(manifest: dict, oracle: dict, fidelity_row: dict) -> dict:
    csv_path = Path(manifest["files"]["csv"]["resolved_path"])
    rows = _read_csv(csv_path)
    contact_s = _first_contact_time(rows)
    window = _window_rows(
        rows, contact_s,
        DEFAULT_CONFIG.outcome_window_start_s,
        DEFAULT_CONFIG.outcome_window_end_s,
    ) if math.isfinite(contact_s) else []
    initial = _window_rows(rows, contact_s, 0.0, 0.20) if math.isfinite(contact_s) else []
    axis = {"x": "omega_x", "y": "omega_y", "z": "omega_z"}[DEFAULT_CONFIG.contact_normal_axis]

    path_length = 0.0
    speeds = []
    signed_speeds = []
    valid_pairs = 0
    possible_pairs = max(0, len(window) - 1)
    first_motion_latency = math.nan
    sustained_start = None
    for left, right in zip(window, window[1:]):
        t0, t1 = _time_s(left), _time_s(right)
        dt = t1 - t0
        valid = (
            _int(left.get("omega_valid")) == 1
            and _int(right.get("omega_valid")) == 1
            and 0 < dt <= DEFAULT_CONFIG.max_metric_gap_s
        )
        coords0 = [_float(left.get(f"omega_{name}")) for name in "xyz"]
        coords1 = [_float(right.get(f"omega_{name}")) for name in "xyz"]
        if not valid or not all(math.isfinite(value) for value in coords0 + coords1):
            sustained_start = None
            continue
        distance = math.sqrt(sum((b - a) ** 2 for a, b in zip(coords0, coords1)))
        speed = distance / dt
        signed_speed = (_float(right.get(axis)) - _float(left.get(axis))) / dt
        path_length += distance
        speeds.append(speed)
        signed_speeds.append(signed_speed)
        valid_pairs += 1
        if speed >= DEFAULT_CONFIG.movement_speed_threshold_m_s:
            sustained_start = t0 if sustained_start is None else sustained_start
            if (
                not math.isfinite(first_motion_latency)
                and t1 - sustained_start >= DEFAULT_CONFIG.movement_sustain_s
            ):
                first_motion_latency = sustained_start - contact_s
        else:
            sustained_start = None

    reversal_count = 0
    previous_sign = 0
    for velocity in signed_speeds:
        sign = 1 if velocity >= DEFAULT_CONFIG.movement_speed_threshold_m_s else (
            -1 if velocity <= -DEFAULT_CONFIG.movement_speed_threshold_m_s else 0
        )
        if sign and previous_sign and sign != previous_sign:
            reversal_count += 1
        if sign:
            previous_sign = sign

    times = [_time_s(row) for row in window]
    threshold = _float(window[0].get("force_threshold_on_N", window[0].get("force_threshold"))) if window else math.nan
    excess = [max(_float(row.get("F_ext_mag")) - threshold, 0.0) for row in window]
    impulse = _integral_trapezoid(times, excess, DEFAULT_CONFIG.max_metric_gap_s)
    initial_peak = max((_float(row.get("F_ext_mag")) for row in initial), default=math.nan)
    omega_valid_rate = _mean([_int(row.get("omega_valid")) for row in window])
    control_dts = [_float(row.get("control_dt")) for row in window]
    haptic_norms = [_float(row.get("haptic_cmd_norm")) for row in rows]
    raw_force_values = [_float(row.get("F_ext_mag")) for row in rows]
    corrected_force_values = [_float(row.get("force_corrected_N")) for row in rows]
    coverage_complete = bool(
        window
        and _time_s(window[0]) <= contact_s + DEFAULT_CONFIG.outcome_window_start_s + DEFAULT_CONFIG.max_metric_gap_s
        and _time_s(window[-1]) >= contact_s + DEFAULT_CONFIG.outcome_window_end_s - DEFAULT_CONFIG.max_metric_gap_s
    )
    H_computable = bool(coverage_complete and valid_pairs > 0)
    return {
        "trial_id": oracle["trial_id"],
        "participant_id": oracle["participant_id"],
        "phase": oracle["phase"],
        "analyzed": oracle["analyzed"],
        "true_condition": oracle["true_condition"],
        "technical_valid": int(
            _int(fidelity_row.get("evaluable")) == 1
            and _int(fidelity_row.get("triplet_hash_verified")) == 1
            and _int(fidelity_row.get("oracle_match"), 1) == 1
            and _int(fidelity_row.get("mask_match"), 1) == 1
            and _int(fidelity_row.get("config_match"), 1) == 1
            and bool(manifest.get("completed", False))
            and not bool(manifest.get("incomplete", False))
            and not any(_int(row.get("safety_abort")) for row in rows)
        ),
        "H_computable": int(H_computable),
        "post_contact_master_path_length_m": path_length if H_computable else math.nan,
        "master_peak_speed_m_s": max(speeds, default=math.nan),
        "first_motion_latency_s": first_motion_latency,
        "normal_axis_reversal_count": reversal_count,
        "valid_motion_pair_rate": valid_pairs / possible_pairs if possible_pairs else math.nan,
        "omega_valid_rate": omega_valid_rate,
        "excess_force_impulse_Ns": impulse,
        "initial_peak_force_N": initial_peak,
        "control_dt_p99_s": _percentile(control_dts, 0.99),
        "control_dt_max_s": max((value for value in control_dts if math.isfinite(value)), default=math.nan),
        "panda_estimated_force_peak_N": max(
            (value for value in raw_force_values if math.isfinite(value)),
            default=math.nan,
        ),
        "force_corrected_peak_N": max(
            (value for value in corrected_force_values if math.isfinite(value)),
            default=math.nan,
        ),
        "haptic_command_peak_N": max((value for value in haptic_norms if math.isfinite(value)), default=math.nan),
        "haptic_clamped_any": int(any(_int(row.get("haptic_clamped")) for row in rows)),
        "haptic_send_failed_any": int(any(_int(row.get("haptic_send_ok"), 1) == 0 for row in rows)),
        "source_csv_sha256": manifest["files"]["csv"]["sha256"],
    }


def _summaries(metrics: List[dict]) -> Tuple[List[dict], List[dict]]:
    analyzed = [row for row in metrics if _int(row.get("analyzed")) == 1 and _int(row.get("technical_valid")) == 1]
    grouped: Dict[Tuple[str, str], List[dict]] = defaultdict(list)
    for row in analyzed:
        grouped[(row["participant_id"], row["true_condition"])].append(row)
    measure_names = [
        "post_contact_master_path_length_m",
        "master_peak_speed_m_s",
        "first_motion_latency_s",
        "normal_axis_reversal_count",
        "excess_force_impulse_Ns",
        "initial_peak_force_N",
    ]
    summaries = []
    for (participant, condition), group in sorted(grouped.items()):
        row = {"participant_id": participant, "true_condition": condition, "valid_trials": len(group)}
        for name in measure_names:
            values = [_float(item.get(name)) for item in group]
            row[f"{name}_mean"] = _mean(values)
            row[f"{name}_median"] = _median(values)
            clean = [value for value in values if math.isfinite(value)]
            row[f"{name}_min"] = min(clean, default=math.nan)
            row[f"{name}_max"] = max(clean, default=math.nan)
        summaries.append(row)

    by_participant = defaultdict(dict)
    for row in summaries:
        by_participant[row["participant_id"]][row["true_condition"]] = row
    contrasts = []
    for participant, condition_rows in sorted(by_participant.items()):
        for numerator, denominator in (("C1", "C0"), ("C2", "C0"), ("C3", "C0"), ("C4", "C0")):
            if numerator not in condition_rows or denominator not in condition_rows:
                continue
            row = {
                "participant_id": participant,
                "contrast": f"{numerator}_minus_{denominator}",
            }
            for name in measure_names:
                key = f"{name}_mean"
                row[f"{name}_difference"] = (
                    _float(condition_rows[numerator].get(key))
                    - _float(condition_rows[denominator].get(key))
                )
            contrasts.append(row)
    return summaries, contrasts


def _acceptance_report(metrics: List[dict], fidelity: List[dict], phase: str) -> dict:
    selected_metrics = [row for row in metrics if row.get("phase") == phase and (phase == "engineering" or _int(row.get("analyzed")) == 1)]
    selected_fidelity = [row for row in fidelity if row.get("phase") == phase and (phase == "engineering" or _int(row.get("analyzed")) == 1)]
    participant_ids = sorted({row["participant_id"] for row in selected_metrics})
    target = 25 if phase == "engineering" else 15 * len(participant_ids)
    valid_count = sum(_int(row.get("technical_valid")) for row in selected_metrics)
    evaluable = [row for row in selected_fidelity if _int(row.get("evaluable")) == 1]
    timing_errors = [abs(_float(row.get("onset_error_s"))) for row in evaluable]
    phi_errors = [abs(_float(row.get("phi_error"))) for row in evaluable]
    participant_valid = Counter(
        row["participant_id"] for row in selected_metrics if _int(row.get("technical_valid")) == 1
    )
    H_values = [
        _float(row.get("post_contact_master_path_length_m"))
        for row in selected_metrics if _int(row.get("H_computable")) == 1
    ]
    finite_H = [value for value in H_values if math.isfinite(value)]
    checks = {
        "expected_trial_count": len(selected_metrics) == target,
        "technical_valid_count": valid_count == 25 if phase == "engineering" else valid_count >= 57,
        "per_participant_valid": True if phase == "engineering" else all(
            participant_valid[participant_id] >= 14 for participant_id in participant_ids
        ),
        "classification_accuracy": _mean([_int(row.get("classification_correct")) for row in evaluable]) >= (1.0 if phase == "engineering" else 0.95),
        "timing_mae": _mean(timing_errors) <= 0.020,
        "timing_p95": _percentile(timing_errors, 0.95) <= 0.020,
        "timing_max": max(timing_errors, default=math.inf) <= 0.050,
        "exposure_mae": _mean(phi_errors) <= 0.020,
        "H_computable": (
            True if phase == "engineering" else
            _mean([_int(row.get("H_computable")) for row in selected_metrics]) >= 0.95
        ),
        "H_no_measurement_floor": (
            True if phase == "engineering" else bool(
                finite_H
                and _mean([int(value > 0.0001) for value in finite_H]) >= 0.80
                and max(finite_H) - min(finite_H) > 0.0001
            )
        ),
        "omega_valid": all(_float(row.get("omega_valid_rate"), 0.0) >= 0.99 for row in selected_metrics),
        "control_timing": all(
            _float(row.get("control_dt_p99_s"), math.inf) <= 0.020
            and _float(row.get("control_dt_max_s"), math.inf) <= 0.050
            for row in selected_metrics
        ),
        "force_limit": all(
            _float(row.get("panda_estimated_force_peak_N"), math.inf) <= 5.0
            for row in selected_metrics
        ),
        "haptic_limit": all(_float(row.get("haptic_command_peak_N"), math.inf) <= 2.0 for row in selected_metrics),
        "no_haptic_clamp_or_send_failure": all(
            _int(row.get("haptic_clamped_any")) == 0 and _int(row.get("haptic_send_failed_any")) == 0
            for row in selected_metrics
        ),
    }
    return {
        "phase": phase,
        "target_trial_count": target,
        "observed_trial_count": len(selected_metrics),
        "technical_valid_count": valid_count,
        "evaluable_fidelity_count": len(evaluable),
        "timing_mae_s": _mean(timing_errors),
        "exposure_mae": _mean(phi_errors),
        "classification_accuracy": _mean([_int(row.get("classification_correct")) for row in evaluable]),
        "checks": checks,
        "overall_pass": all(checks.values()),
        "interpretation": (
            "Engineering acceptance only; not human inference."
            if phase == "engineering"
            else "Feasibility only; no confirmatory p-values or external force endpoint."
        ),
    }


def command_analyze(data_dir: Path, fidelity_path: Path, oracle_path: Path, output_dir: Path) -> None:
    manifests = _load_manifests(data_dir)
    manifest_by_id = {item["trial_id"]: item for item in manifests}
    fidelity = _read_csv(fidelity_path)
    fidelity_by_id = {row["trial_id"]: row for row in fidelity}
    oracle = _load_oracle(oracle_path)
    common = sorted(set(manifest_by_id) & set(fidelity_by_id) & set(oracle))
    metrics = [
        trial_metrics(manifest_by_id[trial_id], oracle[trial_id], fidelity_by_id[trial_id])
        for trial_id in common
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "trial_metrics.csv", metrics)
    summaries, contrasts = _summaries(metrics)
    _write_csv(output_dir / "participant_condition_summary.csv", summaries)
    _write_csv(output_dir / "participant_contrasts.csv", contrasts)
    for phase in ("engineering", "measured"):
        if not any(row.get("phase") == phase for row in metrics):
            continue
        report = _acceptance_report(metrics, fidelity, phase)
        (output_dir / f"{phase}_acceptance.json").write_text(
            json.dumps(_json_safe(report), ensure_ascii=False, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
    provenance = {
        "data_dir": str(data_dir.resolve()),
        "unblinded_fidelity_sha256": sha256_file(fidelity_path),
        "oracle_sha256": sha256_file(oracle_path),
        "trial_metrics_sha256": sha256_file(output_dir / "trial_metrics.csv"),
        "p_values_computed": False,
        "force_source": "Franka estimated external wrench; not an independent physical force endpoint",
    }
    (output_dir / "analysis_provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(provenance, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    reconstruct = subparsers.add_parser("reconstruct", help="outcome-blind fidelity reconstruction")
    reconstruct.add_argument("--data-dir", type=Path, required=True)
    reconstruct.add_argument("--output", type=Path, required=True)

    unblind = subparsers.add_parser("unblind", help="compare frozen reconstruction with private oracle")
    unblind.add_argument("--fidelity", type=Path, required=True)
    unblind.add_argument("--oracle", type=Path, required=True)
    unblind.add_argument("--output", type=Path, required=True)

    analyze = subparsers.add_parser("analyze", help="compute descriptive human/system metrics")
    analyze.add_argument("--data-dir", type=Path, required=True)
    analyze.add_argument("--fidelity", type=Path, required=True)
    analyze.add_argument("--oracle", type=Path, required=True)
    analyze.add_argument("--output-dir", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "reconstruct":
        command_reconstruct(args.data_dir, args.output)
    elif args.command == "unblind":
        command_unblind(args.fidelity, args.oracle, args.output)
    else:
        command_analyze(args.data_dir, args.fidelity, args.oracle, args.output_dir)


if __name__ == "__main__":
    main()
