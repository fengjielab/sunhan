#!/usr/bin/env python3
"""Independent formal analysis for the 20-participant K_fb criterion study.

This module intentionally does not import the online controller or
``kfb_timing_protocol``.  The frozen protocol JSON and private oracle are the
only sources of condition truth.  Raw acquisition files are read-only.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Sequence


PRIMARY_LIMITS = {
    "classification_accuracy_min": 0.95,
    "timing_mae_s_max": 0.020,
    "timing_p95_s_max": 0.020,
    "timing_max_s_max": 0.050,
    "exposure_mae_max": 0.020,
}
CONTRASTS = (("C1", "C0"), ("C2", "C0"), ("C3", "C0"), ("C4", "C0"))
HUMAN_METRICS = ("excess_force_impulse_Ns", "initial_peak_force_N")


def finite_float(value, default=math.nan) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def int_value(value, default=0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def mean(values: Iterable[float]) -> float:
    clean = [value for value in values if math.isfinite(value)]
    return statistics.fmean(clean) if clean else math.nan


def percentile(values: Iterable[float], probability: float) -> float:
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


def t_critical_975(df: int) -> float:
    table = {
        1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
        6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
        11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131,
        16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
        21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060,
        26: 2.056, 27: 2.052, 28: 2.048, 29: 2.045, 30: 2.042,
    }
    return table.get(df, 1.960 if df >= 120 else 2.000)


def mean_ci(values: Iterable[float]) -> tuple[float, float, float, int]:
    clean = [value for value in values if math.isfinite(value)]
    center = mean(clean)
    if len(clean) < 2:
        return center, math.nan, math.nan, len(clean)
    half = t_critical_975(len(clean) - 1) * statistics.stdev(clean) / math.sqrt(len(clean))
    return center, center - half, center + half, len(clean)


def sha256_bytes(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_text_bytes(path: Path) -> bytes:
    text = path.read_text(encoding="utf-8-sig")
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def sha256_text(path: Path) -> str:
    return hashlib.sha256(canonical_text_bytes(path)).hexdigest()


def json_safe(value):
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(json_safe(payload), ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], fieldnames: Sequence[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: "" if isinstance(value, float) and not math.isfinite(value) else value for key, value in row.items()})


def parse_participants(spec: str) -> list[str]:
    participants: list[str] = []
    for token in (item.strip() for item in spec.split(",")):
        if not token:
            continue
        if "-" in token:
            left, right = token.split("-", 1)
            if not (left.startswith("F") and right.startswith("F")):
                raise ValueError(f"invalid participant range: {token}")
            start, end = int(left[1:]), int(right[1:])
            if start > end:
                raise ValueError(f"descending participant range: {token}")
            participants.extend(f"F{index:02d}" for index in range(start, end + 1))
        else:
            if len(token) != 3 or not token.startswith("F") or not token[1:].isdigit():
                raise ValueError(f"invalid participant id: {token}")
            participants.append(token)
    if not participants or len(participants) != len(set(participants)):
        raise ValueError("participants must be a non-empty unique list")
    return participants


def expected_trial_ids(participants: Sequence[str]) -> list[str]:
    return [
        f"{participant}_M{block:02d}_{trial:02d}"
        for participant in participants
        for block in range(1, 4)
        for trial in range(1, 6)
    ]


def load_protocol(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    canonical = {"config": payload["config"], "conditions": payload["conditions"]}
    computed = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if computed != payload.get("config_sha256"):
        raise RuntimeError("protocol config hash does not match its canonical payload")
    if sorted(payload["conditions"]) != ["C0", "C1", "C2", "C3", "C4"]:
        raise RuntimeError("formal protocol must define exactly C0-C4")
    return payload


def load_oracle(path: Path, participants: Sequence[str], config_hash: str) -> dict[str, dict]:
    all_rows = read_csv(path)
    selected = [row for row in all_rows if row.get("participant_id") in participants]
    result = {row["trial_id"]: row for row in selected}
    expected = set(expected_trial_ids(participants))
    if len(result) != len(selected):
        raise RuntimeError("duplicate selected trial_id in oracle")
    if set(result) != expected:
        missing = sorted(expected - set(result))
        extra = sorted(set(result) - expected)
        raise RuntimeError(f"oracle cohort mismatch; missing={missing[:5]} extra={extra[:5]}")
    for trial_id, row in result.items():
        if row.get("config_sha256") != config_hash:
            raise RuntimeError(f"oracle config mismatch for {trial_id}")
    counts = Counter((row["participant_id"], row["true_condition"]) for row in selected)
    if any(counts[(participant, condition)] != 3 for participant in participants for condition in ("C0", "C1", "C2", "C3", "C4")):
        raise RuntimeError("oracle is not balanced at three trials per participant-condition")
    return result


def verify_source_file(path: Path, expected_hash: str, role: str) -> dict:
    if not path.is_file():
        raise RuntimeError(f"missing {role} file: {path}")
    raw_hash = sha256_bytes(path)
    normalized_hash = sha256_text(path) if role in {"events", "summary"} else raw_hash
    raw_match = raw_hash == expected_hash
    normalized_match = normalized_hash == expected_hash
    if role == "csv" and not raw_match:
        raise RuntimeError(f"CSV byte hash mismatch: {path}")
    if role in {"events", "summary"} and not (raw_match or normalized_match):
        raise RuntimeError(f"JSON content hash mismatch: {path}")
    return {
        "expected_sha256": expected_hash,
        "raw_sha256": raw_hash,
        "normalized_text_sha256": normalized_hash,
        "raw_match": int(raw_match),
        "normalized_text_match": int(normalized_match),
        "verification": "byte_exact" if raw_match else "canonical_text_exact",
    }


def build_cohort(data_dir: Path, participants: Sequence[str], oracle: dict[str, dict], config_hash: str) -> tuple[list[dict], dict[str, dict]]:
    actual_dirs = sorted(path.name for path in data_dir.iterdir() if path.is_dir())
    if actual_dirs != sorted(participants):
        raise RuntimeError(f"participant directory mismatch; expected={sorted(participants)} actual={actual_dirs}")
    queue: list[dict] = []
    manifests: dict[str, dict] = {}
    for trial_id in expected_trial_ids(participants):
        participant = trial_id[:3]
        block = int(trial_id[5:7])
        trial_dir = data_dir / participant / f"block_{block:02d}"
        manifest_path = trial_dir / f"{trial_id}_manifest.json"
        if not manifest_path.is_file():
            raise RuntimeError(f"missing manifest: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        if manifest.get("trial_id") != trial_id or manifest.get("participant_id") != participant:
            raise RuntimeError(f"manifest identity mismatch: {manifest_path}")
        expected = oracle[trial_id]
        if manifest.get("masked_condition") != expected.get("masked_condition"):
            raise RuntimeError(f"masked condition mismatch: {trial_id}")
        if manifest.get("config_sha256") != config_hash:
            raise RuntimeError(f"manifest config mismatch: {trial_id}")
        file_results: dict[str, dict] = {}
        resolved: dict[str, Path] = {}
        for role in ("csv", "events", "summary"):
            info = manifest.get("files", {}).get(role, {})
            expected_name = f"{trial_id}.csv" if role == "csv" else f"{trial_id}_{role}.json"
            if info.get("path") != expected_name:
                raise RuntimeError(f"unexpected {role} filename in {trial_id}")
            path = trial_dir / expected_name
            file_results[role] = verify_source_file(path, info.get("sha256", ""), role)
            resolved[role] = path
        summary = json.loads(resolved["summary"].read_text(encoding="utf-8-sig"))
        experiment = summary.get("experiment", {})
        if experiment.get("trial_id") != trial_id or experiment.get("subject_id") != participant:
            raise RuntimeError(f"summary identity mismatch: {trial_id}")
        if bool(manifest.get("completed")) != bool(experiment.get("completed")):
            raise RuntimeError(f"completion mismatch between manifest and summary: {trial_id}")
        manifest["_paths"] = {key: value for key, value in resolved.items()}
        manifests[trial_id] = manifest
        relative_manifest = manifest_path.relative_to(data_dir).as_posix()
        row = {
            "trial_id": trial_id,
            "participant_id": participant,
            "block": block,
            "true_condition": expected["true_condition"],
            "masked_condition": expected["masked_condition"],
            "completed": int(bool(manifest.get("completed"))),
            "incomplete": int(bool(manifest.get("incomplete"))),
            "manifest_relative_path": relative_manifest,
            "manifest_raw_sha256": sha256_bytes(manifest_path),
        }
        for role in ("csv", "events", "summary"):
            result = file_results[role]
            row[f"{role}_relative_path"] = resolved[role].relative_to(data_dir).as_posix()
            row[f"{role}_expected_sha256"] = result["expected_sha256"]
            row[f"{role}_raw_sha256"] = result["raw_sha256"]
            row[f"{role}_normalized_text_sha256"] = result["normalized_text_sha256"]
            row[f"{role}_verification"] = result["verification"]
        queue.append(row)
    discovered = sorted(path.stem.removesuffix("_manifest") for path in data_dir.rglob("*_manifest.json"))
    if discovered != expected_trial_ids(participants):
        raise RuntimeError("manifest discovery contains missing, extra, or misplaced trial IDs")
    return queue, manifests


def row_time(row: dict) -> float:
    mono = finite_float(row.get("t_mono_ns"))
    return mono / 1_000_000_000.0 if math.isfinite(mono) else finite_float(row.get("system_time"))


def first_contact(rows: Sequence[dict]) -> float:
    for row in rows:
        if int_value(row.get("contact_confirmed")) == 1 or "contact_confirmed" in str(row.get("event", "")).split("|"):
            return row_time(row)
    return math.nan


def active(row: dict, baseline: float, intervention: float) -> bool:
    if row.get("intervention_state") == "intervention":
        return True
    return finite_float(row.get("K_fb_commanded", row.get("K_fb"))) >= (baseline + intervention) / 2.0


def transition_times(rows: Sequence[dict], contact_s: float, baseline: float, intervention: float) -> tuple[float, float]:
    previous = False
    onset = math.nan
    offset = math.nan
    for row in rows:
        current = active(row, baseline, intervention)
        relative = row_time(row) - contact_s
        if current and not previous and not math.isfinite(onset):
            onset = relative
        elif previous and not current and math.isfinite(onset):
            offset = relative
            break
        previous = current
    return onset, offset


def exposure(rows: Sequence[dict], contact_s: float, start_rel: float, end_rel: float, max_gap: float, baseline: float, intervention: float) -> float:
    covered = 0.0
    active_duration = 0.0
    start, end = contact_s + start_rel, contact_s + end_rel
    for left, right in zip(rows, rows[1:]):
        lo, hi = max(row_time(left), start), min(row_time(right), end)
        if hi <= lo:
            continue
        covered += hi - lo
        if active(left, baseline, intervention):
            active_duration += hi - lo
    window = end - start
    return active_duration / window if covered >= window - max_gap else math.nan


def classify(onset: float, offset: float, phi: float, conditions: dict) -> str:
    if not all(math.isfinite(value) for value in (onset, offset, phi)):
        return "NOT_EVALUABLE"
    return min(
        conditions,
        key=lambda code: (
            abs(onset - finite_float(conditions[code]["onset_s"])) / 0.05
            + abs(offset - finite_float(conditions[code]["offset_s"])) / 0.05
            + abs(phi - finite_float(conditions[code]["expected_phi"])) / 0.05,
            code,
        ),
    )


def window_rows(rows: Sequence[dict], contact_s: float, start_rel: float, end_rel: float) -> list[dict]:
    return [row for row in rows if contact_s + start_rel <= row_time(row) <= contact_s + end_rel]


def trapezoid(times: Sequence[float], values: Sequence[float], max_gap: float) -> float:
    total = 0.0
    used = 0
    for t0, t1, v0, v1 in zip(times, times[1:], values, values[1:]):
        dt = t1 - t0
        if 0 < dt <= max_gap and all(math.isfinite(value) for value in (v0, v1)):
            total += 0.5 * (v0 + v1) * dt
            used += 1
    return total if used else math.nan


def analyze_trial(manifest: dict, oracle: dict, protocol: dict) -> dict:
    config = protocol["config"]
    conditions = protocol["conditions"]
    rows = read_csv(manifest["_paths"]["csv"])
    contact_s = first_contact(rows)
    onset, offset = transition_times(rows, contact_s, config["K_fb_baseline"], config["K_fb_intervention"])
    phi = exposure(
        rows, contact_s, config["outcome_window_start_s"], config["outcome_window_end_s"],
        config["max_metric_gap_s"], config["K_fb_baseline"], config["K_fb_intervention"],
    ) if math.isfinite(contact_s) else math.nan
    completed = bool(manifest.get("completed")) and not bool(manifest.get("incomplete"))
    safety_abort = any(int_value(row.get("safety_abort")) == 1 for row in rows)
    evaluable = completed and not safety_abort and all(math.isfinite(value) for value in (contact_s, onset, offset, phi))
    inferred = classify(onset, offset, phi, conditions) if evaluable else "NOT_EVALUABLE"
    scheduled_onset = finite_float(oracle["scheduled_onset_s"])
    expected_phi = finite_float(oracle["expected_phi"])
    outcome = window_rows(rows, contact_s, config["outcome_window_start_s"], config["outcome_window_end_s"]) if math.isfinite(contact_s) else []
    initial = window_rows(rows, contact_s, 0.0, 0.20) if math.isfinite(contact_s) else []
    threshold = finite_float(outcome[0].get("force_threshold_on_N", outcome[0].get("force_threshold"))) if outcome else math.nan
    times = [row_time(row) for row in outcome]
    excess = [max(finite_float(row.get("F_ext_mag")) - threshold, 0.0) for row in outcome]
    impulse = trapezoid(times, excess, config["max_metric_gap_s"]) if evaluable else math.nan
    control_dts = [finite_float(row.get("control_dt")) for row in outcome]
    omega_valid = [int_value(row.get("omega_valid")) for row in outcome]
    haptic_window = [int_value(row.get("haptic_clamped")) for row in outcome]
    haptic_all = [int_value(row.get("haptic_clamped")) for row in rows]
    send_all = [int_value(row.get("haptic_send_ok"), 1) for row in rows]
    forces = [finite_float(row.get("F_ext_mag")) for row in rows]
    return {
        "trial_id": oracle["trial_id"],
        "participant_id": oracle["participant_id"],
        "true_condition": oracle["true_condition"],
        "completed": int(completed),
        "safety_abort": int(safety_abort),
        "fidelity_evaluable": int(evaluable),
        "contact_confirmed_s": contact_s,
        "scheduled_onset_s": scheduled_onset,
        "detected_onset_relative_s": onset,
        "scheduled_offset_s": finite_float(oracle["scheduled_offset_s"]),
        "detected_offset_relative_s": offset,
        "expected_epsilon_s": finite_float(oracle["expected_epsilon_s"]),
        "epsilon_hat_s": onset - finite_float(config["outcome_window_start_s"]) if math.isfinite(onset) else math.nan,
        "onset_error_s": onset - scheduled_onset if evaluable else math.nan,
        "expected_phi": expected_phi,
        "phi_hat": phi,
        "phi_error": phi - expected_phi if evaluable else math.nan,
        "inferred_condition": inferred,
        "classification_correct": int(evaluable and inferred == oracle["true_condition"]),
        "excess_force_impulse_Ns": impulse,
        "initial_peak_force_N": max((finite_float(row.get("F_ext_mag")) for row in initial), default=math.nan) if evaluable else math.nan,
        "omega_valid_rate": mean(omega_valid),
        "control_dt_p99_s": percentile(control_dts, 0.99),
        "control_dt_max_s": max((value for value in control_dts if math.isfinite(value)), default=math.nan),
        "panda_estimated_force_peak_N": max((value for value in forces if math.isfinite(value)), default=math.nan),
        "haptic_clamped_any": int(any(haptic_all)),
        "haptic_clamped_window_rate": mean(haptic_window),
        "haptic_send_failed_any": int(any(value == 0 for value in send_all)),
    }


def participant_group_values(rows: list[dict], value_key: str, condition: str | None = None) -> dict[str, float]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        if int_value(row.get("fidelity_evaluable")) != 1:
            continue
        if condition is not None and row["true_condition"] != condition:
            continue
        value = finite_float(row.get(value_key))
        if math.isfinite(value):
            grouped[row["participant_id"]].append(value)
    return {participant: mean(values) for participant, values in grouped.items()}


def fidelity_summary(metrics: list[dict], participants: Sequence[str]) -> list[dict]:
    output: list[dict] = []
    for condition in ["C0", "C1", "C2", "C3", "C4", "OVERALL"]:
        selected = [row for row in metrics if condition == "OVERALL" or row["true_condition"] == condition]
        evaluable = [row for row in selected if int_value(row["fidelity_evaluable"]) == 1]
        timing_abs = [abs(finite_float(row["onset_error_s"])) for row in evaluable]
        phi_abs = [abs(finite_float(row["phi_error"])) for row in evaluable]
        condition_arg = None if condition == "OVERALL" else condition
        onset_by_p = participant_group_values(evaluable, "detected_onset_relative_s", condition_arg)
        phi_by_p = participant_group_values(evaluable, "phi_hat", condition_arg)
        timing_by_p = participant_group_values(
            [{**row, "timing_abs": abs(finite_float(row["onset_error_s"]))} for row in evaluable],
            "timing_abs", condition_arg,
        )
        phi_error_by_p = participant_group_values(
            [{**row, "phi_abs": abs(finite_float(row["phi_error"]))} for row in evaluable],
            "phi_abs", condition_arg,
        )
        onset_center, onset_low, onset_high, onset_n = mean_ci(onset_by_p.values())
        phi_center, phi_low, phi_high, phi_n = mean_ci(phi_by_p.values())
        timing_center, timing_low, timing_high, _ = mean_ci(timing_by_p.values())
        phi_error_center, phi_error_low, phi_error_high, _ = mean_ci(phi_error_by_p.values())
        expected_onset = mean([finite_float(row["scheduled_onset_s"]) for row in selected])
        expected_phi = mean([finite_float(row["expected_phi"]) for row in selected])
        output.append({
            "condition": condition,
            "participant_count": min(onset_n, phi_n),
            "planned_trials": len(selected),
            "evaluable_trials": len(evaluable),
            "classification_correct": sum(int_value(row["classification_correct"]) for row in evaluable),
            "classification_accuracy": mean([int_value(row["classification_correct"]) for row in evaluable]),
            "expected_onset_s": expected_onset,
            "onset_hat_participant_mean_s": onset_center,
            "onset_hat_ci_low_s": onset_low,
            "onset_hat_ci_high_s": onset_high,
            "timing_mae_s": mean(timing_abs),
            "timing_mae_participant_mean_s": timing_center,
            "timing_mae_ci_low_s": timing_low,
            "timing_mae_ci_high_s": timing_high,
            "timing_p95_abs_error_s": percentile(timing_abs, 0.95),
            "timing_max_abs_error_s": max(timing_abs, default=math.nan),
            "expected_phi": expected_phi,
            "phi_hat_participant_mean": phi_center,
            "phi_hat_ci_low": phi_low,
            "phi_hat_ci_high": phi_high,
            "exposure_mae": mean(phi_abs),
            "exposure_mae_participant_mean": phi_error_center,
            "exposure_mae_ci_low": phi_error_low,
            "exposure_mae_ci_high": phi_error_high,
            "exposure_p95_abs_error": percentile(phi_abs, 0.95),
            "exposure_max_abs_error": max(phi_abs, default=math.nan),
        })
    return output


def quality_summary(metrics: list[dict]) -> list[dict]:
    output = []
    for condition in ["C0", "C1", "C2", "C3", "C4", "OVERALL"]:
        selected = [row for row in metrics if condition == "OVERALL" or row["true_condition"] == condition]
        complete = [row for row in selected if int_value(row["completed"]) == 1 and int_value(row["safety_abort"]) == 0]
        output.append({
            "condition": condition,
            "planned_trials": len(selected),
            "completed_trials": len(complete),
            "safety_abort_trials": sum(int_value(row["safety_abort"]) for row in selected),
            "fidelity_evaluable_trials": sum(int_value(row["fidelity_evaluable"]) for row in selected),
            "haptic_clamped_all_trials": sum(int_value(row["haptic_clamped_any"]) for row in selected),
            "haptic_clamped_completed_trials": sum(int_value(row["haptic_clamped_any"]) for row in complete),
            "haptic_send_failure_trials": sum(int_value(row["haptic_send_failed_any"]) for row in selected),
            "omega_valid_below_99pct_trials": sum(finite_float(row["omega_valid_rate"], 0.0) < 0.99 for row in complete),
            "control_p99_above_20ms_trials": sum(finite_float(row["control_dt_p99_s"], math.inf) > 0.020 for row in complete),
            "control_max_above_50ms_trials": sum(finite_float(row["control_dt_max_s"], math.inf) > 0.050 for row in complete),
            "force_peak_above_5N_trials": sum(finite_float(row["panda_estimated_force_peak_N"], 0.0) > 5.0 for row in selected),
        })
    return output


def participant_summaries(metrics: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    condition_rows: list[dict] = []
    participant_contrasts: list[dict] = []
    contrast_summary: list[dict] = []
    for analysis_set, predicate in (
        ("all_complete", lambda row: int_value(row["fidelity_evaluable"]) == 1),
        ("unclamped_complete", lambda row: int_value(row["fidelity_evaluable"]) == 1 and int_value(row["haptic_clamped_any"]) == 0),
    ):
        selected = [row for row in metrics if predicate(row)]
        grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for row in selected:
            grouped[(row["participant_id"], row["true_condition"])].append(row)
        lookup: dict[tuple[str, str], dict] = {}
        for (participant, condition), group in sorted(grouped.items()):
            row = {
                "analysis_set": analysis_set,
                "participant_id": participant,
                "true_condition": condition,
                "valid_trials": len(group),
            }
            for metric in HUMAN_METRICS:
                row[f"{metric}_mean"] = mean(finite_float(item[metric]) for item in group)
            condition_rows.append(row)
            lookup[(participant, condition)] = row
        for numerator, denominator in CONTRASTS:
            for participant in sorted({key[0] for key in lookup}):
                left = lookup.get((participant, numerator))
                right = lookup.get((participant, denominator))
                if left is None or right is None:
                    continue
                for metric in HUMAN_METRICS:
                    difference = finite_float(left[f"{metric}_mean"]) - finite_float(right[f"{metric}_mean"])
                    participant_contrasts.append({
                        "analysis_set": analysis_set,
                        "participant_id": participant,
                        "contrast": f"{numerator}_minus_{denominator}",
                        "metric": metric,
                        "difference": difference,
                    })
    groups: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for row in participant_contrasts:
        groups[(row["analysis_set"], row["contrast"], row["metric"])].append(finite_float(row["difference"]))
    for (analysis_set, contrast, metric), values in sorted(groups.items()):
        center, low, high, n = mean_ci(values)
        contrast_summary.append({
            "analysis_set": analysis_set,
            "contrast": contrast,
            "metric": metric,
            "participant_count": n,
            "mean_difference": center,
            "ci_low": low,
            "ci_high": high,
            "negative_participants": sum(value < 0 for value in values),
            "positive_participants": sum(value > 0 for value in values),
            "zero_participants": sum(value == 0 for value in values),
            "interpretation": "exploratory; no confirmatory p-value",
        })
    return condition_rows, participant_contrasts, contrast_summary


def acceptance_report(fidelity_rows: list[dict], quality_rows: list[dict]) -> dict:
    overall = next(row for row in fidelity_rows if row["condition"] == "OVERALL")
    quality = next(row for row in quality_rows if row["condition"] == "OVERALL")
    checks = {
        "classification_accuracy": finite_float(overall["classification_accuracy"]) >= PRIMARY_LIMITS["classification_accuracy_min"],
        "timing_mae": finite_float(overall["timing_mae_s"]) <= PRIMARY_LIMITS["timing_mae_s_max"],
        "timing_p95": finite_float(overall["timing_p95_abs_error_s"]) <= PRIMARY_LIMITS["timing_p95_s_max"],
        "timing_max": finite_float(overall["timing_max_abs_error_s"]) <= PRIMARY_LIMITS["timing_max_s_max"],
        "exposure_mae": finite_float(overall["exposure_mae"]) <= PRIMARY_LIMITS["exposure_mae_max"],
    }
    return {
        "cohort": "F01-F20",
        "independent_participants": 20,
        "planned_trials": int_value(quality["planned_trials"]),
        "completed_trials": int_value(quality["completed_trials"]),
        "fidelity_evaluable_trials": int_value(quality["fidelity_evaluable_trials"]),
        "safety_abort_trials": int_value(quality["safety_abort_trials"]),
        "haptic_clamped_completed_trials": int_value(quality["haptic_clamped_completed_trials"]),
        "limits": PRIMARY_LIMITS,
        "primary_checks": checks,
        "overall_primary_pass": all(checks.values()),
        "interpretation": "Prospective within-system criterion validation of epsilon and Phi recovery; not external validation or confirmatory human-effect evidence.",
        "quality_constraint": "Haptic clamping and safety aborts are reported separately and constrain interpretation of delivered physical dose and exploratory human outcomes.",
    }


def create_figures(output_dir: Path, protocol: dict, metrics: list[dict], fidelity_rows: list[dict], quality_rows: list[dict]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    matplotlib.rcParams["svg.hashsalt"] = "kfb-timing-formal-v2"

    figures = output_dir / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    conditions = ["C0", "C1", "C2", "C3", "C4"]
    specs = protocol["conditions"]

    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    window_start = protocol["config"]["outcome_window_start_s"]
    window_end = protocol["config"]["outcome_window_end_s"]
    ax.axvspan(window_start, window_end, color="#d9e8f5", alpha=0.8)
    for y, code in enumerate(reversed(conditions)):
        spec = specs[code]
        ax.barh(y, spec["offset_s"] - spec["onset_s"], left=spec["onset_s"], height=0.48, color="#2878B5")
        ax.text(1.36, y, f"epsilon={spec['expected_epsilon_s']:.3f}, Phi={spec['expected_phi']:.3f}", va="center", fontsize=8)
    ax.set_yticks(range(5), list(reversed(conditions)))
    ax.set_xlim(0, 1.72)
    ax.set_xlabel("Time from confirmed contact (s)")
    ax.set_title("Known timing and exposure targets")
    fig.tight_layout()
    fig.savefig(figures / "fig4_protocol_design.png", dpi=300)
    fig.savefig(figures / "fig4_protocol_design.svg", metadata={"Date": None})
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.4))
    for x, code in enumerate(conditions):
        values = [finite_float(row["detected_onset_relative_s"]) for row in metrics if row["true_condition"] == code and int_value(row["fidelity_evaluable"]) == 1]
        axes[0].scatter([x] * len(values), values, s=8, alpha=0.25, color="#2878B5")
        axes[0].plot(x, mean(values), "o", color="#C82423", markersize=5)
        axes[0].plot([x - 0.22, x + 0.22], [specs[code]["onset_s"]] * 2, color="black", linewidth=1.5)
        phi_values = [finite_float(row["phi_hat"]) for row in metrics if row["true_condition"] == code and int_value(row["fidelity_evaluable"]) == 1]
        axes[1].scatter([x] * len(phi_values), phi_values, s=8, alpha=0.25, color="#2878B5")
        axes[1].plot(x, mean(phi_values), "o", color="#C82423", markersize=5)
        axes[1].plot([x - 0.22, x + 0.22], [specs[code]["expected_phi"]] * 2, color="black", linewidth=1.5)
    for ax in axes:
        ax.set_xticks(range(5), conditions)
        ax.grid(axis="y", alpha=0.2)
    axes[0].set_ylabel("Recovered onset from contact (s)")
    axes[0].set_title("Timing recovery")
    axes[1].set_ylabel("Recovered outcome-window exposure")
    axes[1].set_title("Exposure recovery")
    fig.tight_layout(w_pad=2.6)
    fig.savefig(figures / "fig5_fidelity_recovery.png", dpi=300)
    fig.savefig(figures / "fig5_fidelity_recovery.svg", metadata={"Date": None})
    plt.close(fig)

    planned = [next(row for row in quality_rows if row["condition"] == code)["planned_trials"] for code in conditions]
    completed = [next(row for row in quality_rows if row["condition"] == code)["completed_trials"] for code in conditions]
    aborted = [next(row for row in quality_rows if row["condition"] == code)["safety_abort_trials"] for code in conditions]
    clamped = [next(row for row in quality_rows if row["condition"] == code)["haptic_clamped_completed_trials"] for code in conditions]
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.4))
    x = list(range(5))
    axes[0].bar(x, completed, color="#2878B5", label="Completed")
    axes[0].bar(x, aborted, bottom=completed, color="#C82423", label="Safety abort")
    axes[0].plot(x, planned, "k_", markersize=16, label="Planned")
    axes[0].set_xticks(x, conditions)
    axes[0].set_ylabel("Trials")
    axes[0].set_title("Trial disposition")
    axes[0].legend(frameon=False, fontsize=8)
    axes[1].bar(x, clamped, color="#F39C12")
    axes[1].set_xticks(x, conditions)
    axes[1].set_ylabel("Completed trials with clamp")
    axes[1].set_title("Haptic command saturation")
    fig.tight_layout(w_pad=2.6)
    fig.savefig(figures / "fig6_flow_and_quality.png", dpi=300)
    fig.savefig(figures / "fig6_flow_and_quality.svg", metadata={"Date": None})
    plt.close(fig)


def write_results_summary(path: Path, acceptance: dict, fidelity_rows: list[dict], quality_rows: list[dict], contrast_rows: list[dict]) -> None:
    overall = next(row for row in fidelity_rows if row["condition"] == "OVERALL")
    quality = next(row for row in quality_rows if row["condition"] == "OVERALL")
    impulse = [row for row in contrast_rows if row["analysis_set"] == "all_complete" and row["metric"] == "excess_force_impulse_Ns"]
    lines = [
        "# Formal 20-participant criterion-validation results",
        "",
        "## Primary result",
        "",
        f"The fixed cohort contains 20 independent participants and 300 planned trials. {quality['completed_trials']} trials completed and {quality['safety_abort_trials']} ended by the prespecified 5 N safety abort. Primary fidelity reconstruction therefore used {overall['evaluable_trials']}/{overall['planned_trials']} trials.",
        "",
        f"Condition classification was correct in {overall['classification_correct']}/{overall['evaluable_trials']} evaluable trials ({100 * finite_float(overall['classification_accuracy']):.1f}%). Absolute onset error had MAE {1000 * finite_float(overall['timing_mae_s']):.3f} ms, P95 {1000 * finite_float(overall['timing_p95_abs_error_s']):.3f} ms, and maximum {1000 * finite_float(overall['timing_max_abs_error_s']):.3f} ms. Exposure error had MAE {finite_float(overall['exposure_mae']):.6f}, P95 {finite_float(overall['exposure_p95_abs_error']):.6f}, and maximum {finite_float(overall['exposure_max_abs_error']):.6f}.",
        "",
        f"All prespecified criterion-recovery checks passed: {str(acceptance['overall_primary_pass']).lower()}.",
        "",
        "## Quality constraints",
        "",
        f"Haptic command clamping occurred in {quality['haptic_clamped_completed_trials']}/{quality['completed_trials']} completed trials. This does not alter reconstruction of scheduled onset or outcome-window exposure, but it limits interpretation of delivered physical dose and exploratory human outcomes. Force was the Franka-estimated external wrench, not an independent force/torque sensor endpoint.",
        "",
        "## Exploratory participant-level excess-force contrasts",
        "",
        "These estimates are descriptive and carry no confirmatory p-values.",
        "",
        "| Contrast | n | Mean difference (N·s) | 95% CI | Negative/positive |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in impulse:
        lines.append(f"| {row['contrast']} | {row['participant_count']} | {finite_float(row['mean_difference']):.4f} | [{finite_float(row['ci_low']):.4f}, {finite_float(row['ci_high']):.4f}] | {row['negative_participants']}/{row['positive_participants']} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def run_analysis(data_dir: Path, protocol_path: Path, oracle_path: Path, participants: Sequence[str], output_dir: Path) -> dict:
    protocol = load_protocol(protocol_path)
    config_hash = protocol["config_sha256"]
    oracle = load_oracle(oracle_path, participants, config_hash)
    queue, manifests = build_cohort(data_dir, participants, oracle, config_hash)
    metrics = [analyze_trial(manifests[trial_id], oracle[trial_id], protocol) for trial_id in expected_trial_ids(participants)]
    fidelity_rows = fidelity_summary(metrics, participants)
    quality_rows = quality_summary(metrics)
    condition_rows, participant_contrasts, contrast_rows = participant_summaries(metrics)
    acceptance = acceptance_report(fidelity_rows, quality_rows)

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "analysis_cohort_manifest.csv", queue)
    write_csv(output_dir / "trial_metrics.csv", metrics)
    write_csv(output_dir / "condition_fidelity_summary.csv", fidelity_rows)
    write_csv(output_dir / "quality_and_safety_summary.csv", quality_rows)
    write_csv(output_dir / "participant_condition_summary.csv", condition_rows)
    write_csv(output_dir / "participant_contrasts.csv", participant_contrasts)
    write_csv(output_dir / "exploratory_contrast_summary.csv", contrast_rows)
    write_json(output_dir / "validation_acceptance.json", acceptance)
    create_figures(output_dir, protocol, metrics, fidelity_rows, quality_rows)
    write_results_summary(output_dir / "results_summary.md", acceptance, fidelity_rows, quality_rows, contrast_rows)

    output_files = sorted(
        path for path in output_dir.rglob("*")
        if path.is_file() and path.name != "analysis_provenance.json"
    )
    provenance = {
        "analysis_name": "kfb_timing_formal_20_v2",
        "analysis_script_sha256": sha256_bytes(Path(__file__).resolve()),
        "data_root_name": data_dir.name,
        "protocol_config_sha256": sha256_bytes(protocol_path),
        "protocol_canonical_config_sha256": config_hash,
        "oracle_sha256": sha256_bytes(oracle_path),
        "participants": list(participants),
        "expected_trial_count": len(expected_trial_ids(participants)),
        "historical_first_five_scanned": False,
        "raw_files_modified": False,
        "outcome_role": "exploratory only",
        "force_source": "Franka estimated external wrench; no independent force/torque sensor",
        "output_sha256": {path.relative_to(output_dir).as_posix(): sha256_bytes(path) for path in output_files},
    }
    write_json(output_dir / "analysis_provenance.json", provenance)
    return acceptance


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--protocol-config", type=Path, required=True)
    parser.add_argument("--oracle", type=Path, required=True)
    parser.add_argument("--participants", default="F01-F20")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    participants = parse_participants(args.participants)
    if participants != [f"F{index:02d}" for index in range(1, 21)]:
        raise SystemExit("formal v2 analysis is locked to F01-F20")
    acceptance = run_analysis(
        args.data_dir.resolve(), args.protocol_config.resolve(), args.oracle.resolve(),
        participants, args.output_dir.resolve(),
    )
    print(json.dumps(acceptance, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
