from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np
import pandas as pd


ROOT = Path(r"F:\sun\sunhan\my_test")
OUT = ROOT / "paper2_sci" / "03_clean_analysis"
RAW_ROOT = ROOT / "data" / "ral_date"
FIG = OUT / "figures"
TAB = OUT / "tables"

MASTER_PATH = OUT / "master_trial_manifest.csv"
LINEAGE_PATH = OUT / "data_lineage_audit.csv"
TRIAL_METRICS_PATH = OUT / "trial_level_metrics.csv"
TIMING_PATH = OUT / "timing_audit.csv"

MODE_ORDER = ["default", "force_only", "vision", "vision_force"]
MODE_CODE = {
    "default": "A",
    "force_only": "G",
    "vision": "E",
    "vision_force": "F",
}
MODE_COLORS = {"A": "#4D4D4D", "G": "#7A5195", "E": "#2F6BFF", "F": "#00A6A6"}

OUTCOME_LO = 0.20
OUTCOME_HI = 1.00
OUTCOME_DURATION = OUTCOME_HI - OUTCOME_LO
F_NOMINAL_DELAY = 0.20
CONTROL_PERIOD = 0.005

# Tolerances describe resolution-level equality of logged software commands.
# They are not physical impedance tolerances.
TOL = {
    "K_trans": 0.5,
    "K_rot": 0.05,
    "damping_ratio": 0.005,
    "K_fb": 0.005,
    "deadband": 0.005,
    "scale": 0.005,
    "gripper_speed": 0.0005,
    "gripper_force": 0.05,
}

VISION_PROFILES = {
    "soft": {
        "K_trans": 50.0,
        "K_rot": 5.0,
        "damping_ratio": 0.8,
        "K_fb": 0.2,
        "deadband": 0.3,
        "scale": 3.0,
        "gripper_speed": 0.05,
        "gripper_force": 8.0,
    },
    "medium": {
        "K_trans": 120.0,
        "K_rot": 8.0,
        "damping_ratio": 1.0,
        "K_fb": 0.5,
        "deadband": 0.4,
        "scale": 3.0,
        "gripper_speed": 0.05,
        "gripper_force": 15.0,
    },
    "hard": {
        "K_trans": 200.0,
        "K_rot": 13.0,
        "damping_ratio": 1.2,
        "K_fb": 0.7,
        "deadband": 0.5,
        "scale": 3.0,
        "gripper_speed": 0.05,
        "gripper_force": 20.0,
    },
}

FIXED_A = {
    "K_trans": 200.0,
    "K_rot": 13.0,
    "damping_ratio": 1.2,
    "K_fb": 0.5,
    "deadband": 0.3,
    "scale": 3.0,
    "gripper_speed": 0.05,
    "gripper_force": 20.0,
}

INITIAL_G = {
    "K_trans": 200.0,
    "K_rot": 13.0,
    "damping_ratio": 1.2,
    "K_fb": 0.5,
    "deadband": 0.3,
    "scale": 3.0,
    "gripper_speed": 0.05,
    "gripper_force": 20.0,
}

INITIAL_VISION = {
    "K_trans": 150.0,
    "K_rot": 10.0,
    "damping_ratio": 1.0,
    "K_fb": 0.5,
    "deadband": 0.3,
    "scale": 3.0,
    "gripper_speed": 0.05,
    "gripper_force": 20.0,
}

PARAM_COLS = list(FIXED_A)


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
    value = event_lookup(payload, name).get("system_time")
    return float(value) if value is not None else float("nan")


def finite(value: object) -> bool:
    try:
        return bool(np.isfinite(float(value)))
    except (TypeError, ValueError):
        return False


def exposure_fraction(duration: float) -> float:
    if not finite(duration):
        return float("nan")
    return float(np.clip(duration / OUTCOME_DURATION, 0.0, 1.0))


def first_active_time(raw: pd.DataFrame, column: str) -> float:
    values = pd.to_numeric(raw[column], errors="coerce").fillna(0).to_numpy(float)
    idx = np.flatnonzero(values > 0)
    return float(raw["system_time"].iloc[idx[0]]) if len(idx) else float("nan")


def value_at(raw: pd.DataFrame, column: str, when: float) -> float:
    t = raw["system_time"].to_numpy(float)
    y = pd.to_numeric(raw[column], errors="coerce").to_numpy(float)
    ok = np.isfinite(t) & np.isfinite(y)
    if ok.sum() == 0 or when < np.nanmin(t[ok]) or when > np.nanmax(t[ok]):
        return float("nan")
    tt, idx = np.unique(t[ok], return_index=True)
    yy = y[ok][idx]
    return float(np.interp(when, tt, yy))


def duration_true(raw: pd.DataFrame, state: np.ndarray, lo: float, hi: float) -> float:
    """Left-continuous exposure duration clipped to [lo, hi]."""
    t = raw["system_time"].to_numpy(float)
    state = np.asarray(state, dtype=bool)
    ok = np.isfinite(t)
    t, state = t[ok], state[ok]
    if len(t) < 2 or hi <= lo:
        return float("nan")
    order = np.argsort(t)
    t, state = t[order], state[order]
    starts = np.maximum(t[:-1], lo)
    ends = np.minimum(t[1:], hi)
    widths = np.maximum(ends - starts, 0.0)
    return float(np.sum(widths * state[:-1]))


def time_weighted_mean(raw: pd.DataFrame, column: str, lo: float, hi: float) -> float:
    t = raw["system_time"].to_numpy(float)
    y = pd.to_numeric(raw[column], errors="coerce").to_numpy(float)
    ok = np.isfinite(t) & np.isfinite(y)
    t, y = t[ok], y[ok]
    if len(t) < 2 or lo < t.min() or hi > t.max():
        return float("nan")
    keep = (t > lo) & (t < hi)
    tt = np.r_[lo, t[keep], hi]
    yy = np.interp(tt, t, y)
    return float(np.trapezoid(yy, tt) / (hi - lo))


def range_in_window(raw: pd.DataFrame, column: str, lo: float, hi: float) -> tuple[float, float]:
    t = raw["system_time"].to_numpy(float)
    y = pd.to_numeric(raw[column], errors="coerce").to_numpy(float)
    ok = np.isfinite(t) & np.isfinite(y)
    t, y = t[ok], y[ok]
    if len(t) < 2 or lo < t.min() or hi > t.max():
        return float("nan"), float("nan")
    keep = (t >= lo) & (t <= hi)
    vals = np.r_[np.interp(lo, t, y), y[keep], np.interp(hi, t, y)]
    return float(np.min(vals)), float(np.max(vals))


def first_logged_parameter_change(raw: pd.DataFrame, lock: float) -> tuple[float, str]:
    before = raw[raw["system_time"] < lock]
    after = raw[raw["system_time"] >= lock]
    if before.empty or after.empty:
        return float("nan"), "not_observable_no_bracketing_samples"
    ref = before.iloc[-1]
    for _, row in after.iterrows():
        changed = False
        for col in PARAM_COLS:
            if finite(ref[col]) and finite(row[col]) and abs(float(row[col]) - float(ref[col])) > TOL[col]:
                changed = True
                break
        if changed:
            return float(row["system_time"]), "first_logged_departure_from_last_prelock_command"
    return float("nan"), "no_logged_parameter_change_after_lock"


def target_reach_time(
    raw: pd.DataFrame,
    lock: float,
    target: dict[str, float],
    mode: str,
) -> tuple[float, str]:
    """Find logged completion; in F, fusion evidence provides an upper bound."""
    after = raw[raw["system_time"] >= lock]
    for _, row in after.iterrows():
        if all(
            finite(row[col]) and abs(float(row[col]) - target[col]) <= TOL[col]
            for col in ("K_trans", "K_rot", "damping_ratio")
        ):
            return float(row["system_time"]), "target_observed"
    if mode == "vision_force":
        evidence = after[
            (pd.to_numeric(after["fusion_active"], errors="coerce").fillna(0) > 0)
            | (pd.to_numeric(after["fusion_delta_K"], errors="coerce").fillna(0).abs() > TOL["K_trans"])
        ]
        if not evidence.empty:
            return float(evidence["system_time"].iloc[0]), "upper_bound_from_fusion_execution"
    return float("nan"), "not_observable"


def profile_from_trial(raw: pd.DataFrame, events: dict) -> str:
    label = str(event_lookup(events, "vision_lock").get("semantic_label", "")).strip().lower()
    if label not in VISION_PROFILES:
        locked = raw[pd.to_numeric(raw["vision_locked"], errors="coerce").fillna(0) > 0]
        if not locked.empty:
            label = str(locked["vision_label"].iloc[0]).strip().lower()
    return label if label in VISION_PROFILES else "medium"


def json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def build_specification() -> pd.DataFrame:
    rows = [
        {
            "framework_version": "1.0",
            "mode_code": "A",
            "mode": "default",
            "nominal_label": "fixed impedance baseline",
            "nominal_scientific_interpretation": "Fixed commanded impedance/reference configuration",
            "initial_parameters_json": json_text(FIXED_A),
            "event_guards_json": json_text(["force_baseline_ready", "controller_ready"]),
            "activation_conditions_json": json_text([]),
            "parameter_update_rules_json": json_text(["No dynamic impedance update after task_start"]),
            "nominal_expected_event_order_json": json_text(["force_baseline_ready<=task_start", "task_start<contact_onset"]),
            "executable_expected_event_order_json": json_text(["force_baseline_ready<=task_start", "task_start<contact_onset"]),
            "expected_activation_timing": "not_applicable",
            "outcome_relevant_exposure_window": "contact+0.20s to contact+1.00s",
            "mode_specific_exposure_definition": "All logged commanded parameters remain within resolution tolerances of fixed A values",
            "source_logic": "interactive_teleop.py PRESETS['experiment_fixed_a']; run() initial preset selection",
        },
        {
            "framework_version": "1.0",
            "mode_code": "G",
            "mode": "force_only",
            "nominal_label": "force-only online variable impedance",
            "nominal_scientific_interpretation": "A nominally post-contact force-refinement comparison when contrasted with A",
            "initial_parameters_json": json_text(INITIAL_G),
            "event_guards_json": json_text(["No baseline-ready guard", "No contact guard", "50-ms update interval"]),
            "activation_conditions_json": json_text(["raw F_ext_mag > 1.0 N"]),
            "parameter_update_rules_json": json_text(["ratio=clip((F-1)/(5-1),0,1)", "K_target=200*(1-0.5*ratio)", "K=K+0.3*(K_target-K)", "Krot=0.065*K target with same smoothing"]),
            "nominal_expected_event_order_json": json_text(["force_baseline_ready<=task_start", "task_start<contact_onset<=force_adaptation"]),
            "executable_expected_event_order_json": json_text(["raw_force_above_1N=>adaptation_allowed", "no required contact ordering"]),
            "expected_activation_timing": "No executable contact-relative target; contact-relative timing is descriptive, not a timing-error estimand",
            "outcome_relevant_exposure_window": "contact+0.20s to contact+1.00s",
            "mode_specific_exposure_definition": "Logged force_adapt_active=1",
            "source_logic": "interactive_teleop.py _update_force_only_adaptive_impedance",
        },
        {
            "framework_version": "1.0",
            "mode_code": "E",
            "mode": "vision",
            "nominal_label": "vision-enabled bundled configuration",
            "nominal_scientific_interpretation": "Vision selects a bundled parameter profile before/during approach",
            "initial_parameters_json": json_text(INITIAL_VISION),
            "event_guards_json": json_text(["vision profile available", "first valid detection locks profile"]),
            "activation_conditions_json": json_text(["vision_lock"]),
            "parameter_update_rules_json": json_text(["soft/medium/hard profile", "smoothstep Kt/Kr/damping transition", "immediate Kfb/deadband/scale/gripper update"]),
            "nominal_expected_event_order_json": json_text(["vision_start<vision_lock<=first_parameter_change", "vision_lock<transition_complete"]),
            "executable_expected_event_order_json": json_text(["vision profile valid", "start transition and immediate bundled commands", "mark vision_lock"]),
            "expected_activation_timing": "No fixed contact-relative target",
            "outcome_relevant_exposure_window": "contact+0.20s to contact+1.00s",
            "mode_specific_exposure_definition": "Vision profile has reached its logged transition-complete state",
            "source_logic": "interactive_teleop.py _profile_to_preset and run() vision auto-map block",
        },
        {
            "framework_version": "1.0",
            "mode_code": "F",
            "mode": "vision_force",
            "nominal_label": "vision-enabled configuration plus post-contact force refinement",
            "nominal_scientific_interpretation": "Vision profile followed by force refinement no earlier than contact+0.20s",
            "initial_parameters_json": json_text(INITIAL_VISION),
            "event_guards_json": json_text(["vision_locked", "vision transition inactive", "contact exists", "nominal contact delay 0.20 s", "50-ms update interval"]),
            "activation_conditions_json": json_text(["contact confirmed", "nominal delay elapsed", "force above class-specific deadband"]),
            "parameter_update_rules_json": json_text(["vision profile as K base", "class-specific bounded force ratio", "class-specific gain/smoothing"]),
            "nominal_expected_event_order_json": json_text(["vision_start<vision_lock", "vision_lock<transition_complete<=force_adaptation", "contact_onset<force_adaptation"]),
            "executable_expected_event_order_json": json_text(["vision_locked", "transition inactive", "contact exists", "mixed time.time/perf_counter delay comparison", "class force threshold"]),
            "expected_activation_timing": "t_contact+0.20 s",
            "outcome_relevant_exposure_window": "contact+0.20s to contact+1.00s",
            "mode_specific_exposure_definition": "Vision profile established AND logged fusion_active=1",
            "source_logic": "interactive_teleop.py _update_vision_force_fusion; FUSION_CONTACT_DELAY_S",
        },
    ]
    return pd.DataFrame(rows)


def load_raw(row: pd.Series) -> tuple[pd.DataFrame, dict, dict]:
    csv_path = RAW_ROOT / row["csv_source"]
    events_path = RAW_ROOT / row["events_source"]
    summary_path = RAW_ROOT / row["summary_source"]
    raw = pd.read_csv(csv_path)
    numeric = [
        "system_time", "F_ext_mag", "K_trans", "K_rot", "damping_ratio", "K_fb",
        "deadband", "scale", "gripper_speed", "gripper_force", "vision_locked",
        "fusion_active", "fusion_delta_K", "force_adapt_active", "force_adapt_ratio",
        "force_adapt_target_K", "force_adapt_delta_K", "control_dt",
    ]
    for col in numeric:
        if col not in raw:
            raw[col] = np.nan
        raw[col] = pd.to_numeric(raw[col], errors="coerce")
    raw = raw.dropna(subset=["system_time"]).sort_values("system_time").reset_index(drop=True)
    events = json.loads(events_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    return raw, events, summary


def analyze_trial(
    row: pd.Series,
    scalar: pd.Series,
    timing: pd.Series,
    lineage: pd.Series,
) -> tuple[dict, dict]:
    raw, events, summary = load_raw(row)
    mode = row["mode"]
    code = MODE_CODE[mode]
    task = event_time(events, "task_start")
    baseline = event_time(events, "force_baseline_ready")
    contact = event_time(events, "contact_onset")
    vision_start = event_time(events, "vision_start")
    vision_lock = event_time(events, "vision_lock")
    task_end = event_time(events, "task_end")

    adapt_col = "force_adapt_active" if mode == "force_only" else "fusion_active"
    activation = first_active_time(raw, adapt_col) if mode in ("force_only", "vision_force") else float("nan")
    profile = profile_from_trial(raw, events) if mode in ("vision", "vision_force") else "not_applicable"
    vision_target = VISION_PROFILES.get(profile)

    first_change, first_change_method = (float("nan"), "not_applicable")
    transition_complete, transition_method = (float("nan"), "not_applicable")
    if mode in ("vision", "vision_force") and finite(vision_lock):
        first_change, first_change_method = first_logged_parameter_change(raw, vision_lock)
        transition_complete, transition_method = target_reach_time(raw, vision_lock, vision_target, mode)

    # Nominal event-order compliance is deliberately distinct from executable-logic compliance.
    basic_order = finite(baseline) and finite(task) and finite(contact) and baseline <= task < contact
    if mode == "default":
        nominal_order = basic_order
        executable_order = basic_order
    elif mode == "force_only":
        nominal_order = basic_order and finite(activation) and contact <= activation
        idx = np.flatnonzero(pd.to_numeric(raw[adapt_col], errors="coerce").fillna(0).to_numpy(float) > 0)
        executable_order = bool(len(idx) and float(raw["F_ext_mag"].iloc[idx[0]]) > 1.0)
    elif mode == "vision":
        nominal_order = (
            basic_order and finite(vision_start) and finite(vision_lock) and finite(first_change)
            and finite(transition_complete) and vision_start < vision_lock <= first_change
            and vision_lock <= transition_complete
        )
        executable_order = nominal_order
    else:
        nominal_order = (
            basic_order and finite(vision_start) and finite(vision_lock)
            and finite(transition_complete) and finite(activation)
            and vision_start < vision_lock <= transition_complete <= activation
            and contact < activation
        )
        executable_order = (
            finite(vision_lock) and finite(transition_complete) and finite(activation)
            and vision_lock <= transition_complete <= activation and contact < activation
        )

    f_timing_error = activation - (contact + F_NOMINAL_DELAY) if mode == "vision_force" and finite(activation) else float("nan")
    nominal_timing_compliance = int(f_timing_error >= 0) if finite(f_timing_error) else float("nan")
    precontact = int(activation < contact) if mode in ("force_only", "vision_force") and finite(activation) else float("nan")
    contact_latency = activation - contact if mode in ("force_only", "vision_force") and finite(activation) else float("nan")

    w_lo = contact + OUTCOME_LO
    w_hi = contact + OUTCOME_HI
    window_available = int(raw["system_time"].min() <= w_lo and raw["system_time"].max() >= w_hi)

    adapt_state = pd.to_numeric(raw[adapt_col], errors="coerce").fillna(0).to_numpy(float) > 0
    adapt_exposure = duration_true(raw, adapt_state, w_lo, w_hi) if mode in ("force_only", "vision_force") else float("nan")

    vision_established_state = np.zeros(len(raw), dtype=bool)
    if mode in ("vision", "vision_force") and finite(transition_complete):
        vision_established_state = raw["system_time"].to_numpy(float) >= transition_complete
    vision_exposure = duration_true(raw, vision_established_state, w_lo, w_hi) if mode in ("vision", "vision_force") else float("nan")

    fixed_state = np.ones(len(raw), dtype=bool)
    for col, target in FIXED_A.items():
        fixed_state &= np.isfinite(raw[col].to_numpy(float)) & (np.abs(raw[col].to_numpy(float) - target) <= TOL[col])
    fixed_exposure = duration_true(raw, fixed_state, w_lo, w_hi) if mode == "default" else float("nan")

    if mode == "default":
        active_state = fixed_state
        exposure_definition = "fixed_A_command_vector_within_tolerance"
    elif mode == "force_only":
        active_state = adapt_state
        exposure_definition = "force_adapt_active"
    elif mode == "vision":
        active_state = vision_established_state
        exposure_definition = "vision_transition_complete"
    else:
        active_state = vision_established_state & adapt_state
        exposure_definition = "vision_transition_complete_AND_fusion_active"
    exposure = duration_true(raw, active_state, w_lo, w_hi)
    overlap = exposure_fraction(exposure)

    kt_min, kt_max = range_in_window(raw, "K_trans", w_lo, w_hi)
    kt_mean = time_weighted_mean(raw, "K_trans", w_lo, w_hi)

    master_timestamp_ok = all(str(row[src]).find(str(row["timestamp"])) >= 0 for src in ("csv_source", "events_source", "summary_source"))
    scalar_paths_ok = all(str(scalar[src]) == str(row[src]) for src in ("csv_source", "events_source", "summary_source"))
    recorded_hash_ok = all(int(lineage[col]) == 1 for col in ("csv_hash_verified", "events_hash_verified", "summary_hash_verified"))
    current_hash = {
        "csv": sha256(RAW_ROOT / row["csv_source"]),
        "events": sha256(RAW_ROOT / row["events_source"]),
        "summary": sha256(RAW_ROOT / row["summary_source"]),
    }
    current_hash_ok = {
        "csv": current_hash["csv"] == str(row["csv_sha256"]),
        "events": current_hash["events"] == str(row["events_sha256"]),
        "summary": current_hash["summary"] == str(row["summary_sha256"]),
    }
    summary_timestamp_ok = str(summary.get("timestamp", "")) == str(row["timestamp"])
    provenance_valid = int(
        master_timestamp_ok and scalar_paths_ok and recorded_hash_ok
        and all(current_hash_ok.values()) and summary_timestamp_ok
        and scalar["record_id"] == row["record_id"]
    )

    raw_time = raw["system_time"].to_numpy(float)
    analysis_clock_ok = int(np.all(np.diff(raw_time) >= 0) and int(timing["event_times_within_csv_range"]) == 1)
    gate_clock_ok = 0 if mode == "vision_force" else 1
    clock_integrity = int(analysis_clock_ok and gate_clock_ok)

    dt = pd.to_numeric(raw["control_dt"], errors="coerce").to_numpy(float)
    dt = dt[np.isfinite(dt) & (dt >= 0)]
    dt_median = float(np.median(dt)) if len(dt) else float("nan")
    dt_q1 = float(np.quantile(dt, 0.25)) if len(dt) else float("nan")
    dt_q3 = float(np.quantile(dt, 0.75)) if len(dt) else float("nan")
    within_2x = float(np.mean(dt <= 2 * CONTROL_PERIOD)) if len(dt) else float("nan")

    a_task_end = task_end if finite(task_end) else float(raw["system_time"].max())
    a_window = raw[(raw["system_time"] >= task) & (raw["system_time"] <= a_task_end)]
    a_fixed_max_dev = float(np.max(np.abs(a_window["K_trans"] - FIXED_A["K_trans"]))) if mode == "default" and not a_window.empty else float("nan")
    a_fixed_compliance = int(bool(np.all(fixed_state[(raw["system_time"] >= task) & (raw["system_time"] <= a_task_end)]))) if mode == "default" and not a_window.empty else float("nan")

    result = {
        "record_id": row["record_id"],
        "trial_id": row["trial_key"],
        "trial_key": row["trial_key"],
        "participant": row["participant"],
        "material": row["material"],
        "block": row["block"],
        "mode": mode,
        "mode_code": code,
        "timestamp": row["timestamp"],
        "profile_label": profile,
        "task_start_system_s": task,
        "force_baseline_ready_system_s": baseline,
        "vision_start_system_s": vision_start,
        "vision_lock_system_s": vision_lock,
        "contact_system_s": contact,
        "adaptation_activation_system_s": activation,
        "transition_complete_system_s": transition_complete,
        "transition_complete_observation": transition_method,
        "event_order_compliance": int(nominal_order),
        "executable_logic_compliance": int(executable_order),
        "activation_timing_error_s": f_timing_error,
        "nominal_activation_timing_compliance": nominal_timing_compliance,
        "pre_contact_activation": precontact,
        "contact_to_adaptation_latency_s": contact_latency,
        "vision_lock_to_first_parameter_change_latency_s": first_change - vision_lock if finite(first_change) and finite(vision_lock) else float("nan"),
        "vision_first_parameter_change_observation": first_change_method,
        "vision_lock_to_transition_complete_latency_s": transition_complete - vision_lock if finite(transition_complete) and finite(vision_lock) else float("nan"),
        "transition_complete_before_contact": int(transition_complete <= contact) if finite(transition_complete) else float("nan"),
        "transition_complete_by_outcome_window_start": int(transition_complete <= w_lo) if finite(transition_complete) else float("nan"),
        "adaptation_exposure_duration_s_0p2_1p0": adapt_exposure,
        "adaptation_outcome_window_overlap": exposure_fraction(adapt_exposure),
        "vision_configuration_exposure_duration_s_0p2_1p0": vision_exposure,
        "vision_configuration_outcome_window_overlap": exposure_fraction(vision_exposure),
        "mode_specific_intervention_exposure_duration_s_0p2_1p0": exposure,
        "outcome_window_overlap": overlap,
        "mode_specific_exposure_definition": exposure_definition,
        "active_intervention_during_window": int(exposure > 0) if finite(exposure) else float("nan"),
        "outcome_window_fully_observed": window_available,
        "Kt_mean_in_window_N_m": kt_mean,
        "Kt_min_in_window_N_m": kt_min,
        "Kt_max_in_window_N_m": kt_max,
        "Kt_range_in_window_N_m": kt_max - kt_min if finite(kt_min) and finite(kt_max) else float("nan"),
        "A_fixed_command_compliance_task_to_end": a_fixed_compliance,
        "A_Kt_max_abs_deviation_task_to_end_N_m": a_fixed_max_dev,
        "acquisition_lineage_consistency": provenance_valid,
        "raw_csv_hash_verified_current": int(current_hash_ok["csv"]),
        "event_log_hash_verified_current": int(current_hash_ok["events"]),
        "summary_hash_verified_current": int(current_hash_ok["summary"]),
        "summary_timestamp_matches_record": int(summary_timestamp_ok),
        "analysis_timeline_integrity": analysis_clock_ok,
        "intervention_gate_clock_domain_integrity": gate_clock_ok,
        "clock_domain_integrity": clock_integrity,
        "control_cycle_nominal_period_s": CONTROL_PERIOD,
        "control_cycle_median_s": dt_median,
        "control_cycle_q1_s": dt_q1,
        "control_cycle_q3_s": dt_q3,
        "control_cycle_median_period_ratio": dt_median / CONTROL_PERIOD if finite(dt_median) else float("nan"),
        "control_cycle_within_2x_nominal_fraction": within_2x,
        "control_cycle_adherence": within_2x,
        "primary_excess_impulse_Ns_0p2_1p0": float(scalar["primary_excess_impulse_Ns_0p2_1p0"]),
        "raw_csv_source": row["csv_source"],
        "event_log_source": row["events_source"],
        "summary_source": row["summary_source"],
        "scalar_outcome_record_id": scalar["record_id"],
    }

    for label, when in {
        "task_start": task,
        "contact": contact,
        "contact_plus_0p2": contact + 0.2,
        "contact_plus_1p0": contact + 1.0,
    }.items():
        for col in PARAM_COLS:
            result[f"{col}_at_{label}"] = value_at(raw, col, when)

    if vision_target:
        for col, value in vision_target.items():
            result[f"vision_target_{col}"] = value
        result["Kt_mean_abs_deviation_from_vision_base_in_window_N_m"] = time_weighted_mean_abs_deviation(raw, "K_trans", vision_target["K_trans"], w_lo, w_hi)
    else:
        result["Kt_mean_abs_deviation_from_vision_base_in_window_N_m"] = float("nan")

    exposure_row = {
        "trial_id": row["trial_key"],
        "record_id": row["record_id"],
        "mode": mode,
        "mode_code": code,
        "participant": row["participant"],
        "material": row["material"],
        "block": row["block"],
        "outcome": float(scalar["primary_excess_impulse_Ns_0p2_1p0"]),
        "outcome_name": "threshold-referenced excess-force impulse, contact+0.20 to +1.00 s",
        "active_intervention_definition": exposure_definition,
        "active_intervention_during_window": result["active_intervention_during_window"],
        "exposure_duration_s": exposure,
        "exposure_fraction": overlap,
        "vision_configuration_exposure_fraction": result["vision_configuration_outcome_window_overlap"],
        "force_adaptation_exposure_fraction": result["adaptation_outcome_window_overlap"],
        "transition_complete_by_window_start": result["transition_complete_by_outcome_window_start"],
        "Kt_mean_in_window": kt_mean,
        "Kt_range_in_window": result["Kt_range_in_window_N_m"],
        "provenance_valid": provenance_valid,
        "raw_csv_source": row["csv_source"],
        "scalar_outcome_record_id": scalar["record_id"],
    }
    return result, exposure_row


def time_weighted_mean_abs_deviation(raw: pd.DataFrame, column: str, target: float, lo: float, hi: float) -> float:
    temp = raw[["system_time", column]].copy()
    temp[column] = np.abs(pd.to_numeric(temp[column], errors="coerce") - target)
    return time_weighted_mean(temp, column, lo, hi)


def summarize(metrics: pd.DataFrame) -> pd.DataFrame:
    definitions = [
        ("event_order_compliance", "binary"),
        ("executable_logic_compliance", "binary"),
        ("nominal_activation_timing_compliance", "binary"),
        ("pre_contact_activation", "binary"),
        ("transition_complete_before_contact", "binary"),
        ("transition_complete_by_outcome_window_start", "binary"),
        ("active_intervention_during_window", "binary"),
        ("A_fixed_command_compliance_task_to_end", "binary"),
        ("acquisition_lineage_consistency", "binary"),
        ("analysis_timeline_integrity", "binary"),
        ("intervention_gate_clock_domain_integrity", "binary"),
        ("clock_domain_integrity", "binary"),
        ("activation_timing_error_s", "continuous"),
        ("contact_to_adaptation_latency_s", "continuous"),
        ("vision_lock_to_first_parameter_change_latency_s", "continuous"),
        ("vision_lock_to_transition_complete_latency_s", "continuous"),
        ("adaptation_exposure_duration_s_0p2_1p0", "continuous"),
        ("vision_configuration_exposure_duration_s_0p2_1p0", "continuous"),
        ("mode_specific_intervention_exposure_duration_s_0p2_1p0", "continuous"),
        ("outcome_window_overlap", "continuous"),
        ("Kt_mean_in_window_N_m", "continuous"),
        ("Kt_range_in_window_N_m", "continuous"),
        ("A_Kt_max_abs_deviation_task_to_end_N_m", "continuous"),
        ("control_cycle_median_s", "continuous"),
        ("control_cycle_median_period_ratio", "continuous"),
        ("control_cycle_within_2x_nominal_fraction", "continuous"),
        ("control_cycle_adherence", "continuous"),
    ]
    rows = []
    for mode in MODE_ORDER:
        sub = metrics[metrics["mode"] == mode]
        for metric, kind in definitions:
            x = pd.to_numeric(sub[metric], errors="coerce").dropna().to_numpy(float)
            row = {
                "mode": mode,
                "mode_code": MODE_CODE[mode],
                "metric": metric,
                "metric_type": kind,
                "n_total": len(sub),
                "n_applicable": len(x),
                "n_missing_or_not_applicable": len(sub) - len(x),
                "compliance_count": float("nan"),
                "compliance_rate": float("nan"),
                "median": float("nan"),
                "q1": float("nan"),
                "q3": float("nan"),
                "iqr": float("nan"),
                "minimum": float("nan"),
                "maximum": float("nan"),
            }
            if len(x):
                q1, med, q3 = np.quantile(x, [0.25, 0.5, 0.75])
                row.update({
                    "median": float(med), "q1": float(q1), "q3": float(q3),
                    "iqr": float(q3 - q1), "minimum": float(np.min(x)), "maximum": float(np.max(x)),
                })
                if kind == "binary":
                    row["compliance_count"] = int(np.sum(x == 1))
                    row["compliance_rate"] = float(np.mean(x == 1))
            rows.append(row)
    return pd.DataFrame(rows)


def count_text(metrics: pd.DataFrame, mode: str, column: str, condition) -> str:
    sub = metrics[metrics["mode_code"] == mode]
    n = int(np.sum(condition(pd.to_numeric(sub[column], errors="coerce"))))
    return f"{n}/{len(sub)}"


def build_interpretation_table(metrics: pd.DataFrame) -> pd.DataFrame:
    g_pre = count_text(metrics, "G", "pre_contact_activation", lambda x: x == 1)
    f_gate_fail = count_text(metrics, "F", "nominal_activation_timing_compliance", lambda x: x == 0)
    f_med = float(metrics.loc[metrics["mode_code"] == "F", "contact_to_adaptation_latency_s"].median())
    a_pass = count_text(metrics, "A", "A_fixed_command_compliance_task_to_end", lambda x: x == 1)
    e_full = count_text(metrics, "E", "transition_complete_by_outcome_window_start", lambda x: x == 1)
    f_full = count_text(metrics, "F", "transition_complete_by_outcome_window_start", lambda x: x == 1)
    rows = [
        ["A", "Fixed impedance baseline", "Preset A; no dynamic update", f"{a_pass} retained fixed commanded parameter vector", "None detected for logged commands", "Fixed logged commanded configuration", "Independently measured physical impedance"],
        ["G", "Post-contact force-only refinement", "Raw force >1 N; no baseline/contact gate", f"{g_pre} activated before contact", "Semantic mismatch between post-contact interpretation and executable/realized exposure", "Association with raw-force adaptive configuration, including pre-contact exposure", "Isolated post-contact force-refinement effect"],
        ["E", "Vision effect", "Vision selects bundled Kt/Kr/damping/Kfb/deadband/scale/gripper profile", f"Vision transition complete by outcome-window start in {e_full}", "Bundled intervention and exposure-timing heterogeneity", "Realized vision-enabled bundled-configuration association", "Isolated vision, stiffness, semantic, or gripper effect"],
        ["F", "Vision plus correctly gated force refinement", "Vision bundle plus nominal +0.20-s gate implemented with mixed clocks", f"Median activation contact+{f_med:.3f} s; {f_gate_fail} failed nominal timing", "Temporal runtime noncompliance; component exposure heterogeneity", "Association with the realized F command/exposure pattern", "Effect of a correctly executed +0.20-s refinement policy"],
        ["E-A", "Isolated vision-enabled impedance effect", "Different bundled command trajectories", "E bundle versus fixed A", "Multiple parameters and timing differ", "Association of realized E bundle relative to A", "Single-factor causal effect of vision or stiffness"],
        ["G-A", "Post-contact force-refinement effect", "G adapts from raw force before contact in most trials", "G exposure differs before and after contact", "Nominal contrast does not isolate post-contact adaptation", "Association of realized raw-force adaptive G relative to A", "Pure post-contact force-only effect"],
        ["F-E", "Incremental correctly gated force-refinement effect", "F nominal gate not reliably executed", "F differs through early realized adaptation/exposure", "The intended +0.20-s mechanism was not implemented", "Difference between realized F and realized E configurations", "Effect of the nominal +0.20-s policy"],
        ["F-G", "Incremental vision effect", "Different vision bundles, force laws, deadbands, and timing", "Multiple realized intervention dimensions differ", "Not a single-factor contrast", "Difference between realized F and G configurations", "Isolated vision main effect"],
        ["A/G/E/F overall", "Clean controller-mode or 2x2 comparison", "Four non-equivalent asynchronous pipelines", "Nominal labels do not form a clean realized factorial design", "Semantic, timing, exposure, provenance, and experimental-unit checks are required", "Descriptive/paired comparisons among realized logged configurations", "Independent vision and force main effects or interaction"],
    ]
    return pd.DataFrame(rows, columns=[
        "nominal_label", "nominal_scientific_interpretation", "executable_logic",
        "realized_intervention", "observed_fidelity_issue", "what_contrast_can_estimate",
        "what_contrast_cannot_estimate",
    ])


def save_figure(fig: plt.Figure, stem: Path) -> None:
    fig.savefig(stem.with_suffix(".png"), dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
    fig.savefig(stem.with_suffix(".svg"), bbox_inches="tight", facecolor="white")
    plt.close(fig)


def figure_framework(metrics: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(13.2, 7.4))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    titles = ["Nominal\nintervention", "Executable /\ncommanded logic", "Realized logged\nintervention", "Outcome\ninterpretation"]
    subtitles = [
        "Mode semantics, parameters,\nevent order and timing target",
        "Code guards, clocks, update laws\nand issued commands",
        "Event-aligned command trajectories,\nactivation states and provenance",
        "Exposure in the analysis window\nand admissible estimand",
    ]
    xs = [0.02, 0.265, 0.51, 0.755]
    colors = ["#E8EEF8", "#E9F4EE", "#FFF2D8", "#F2EAF7"]
    for i, (x, title, subtitle, color) in enumerate(zip(xs, titles, subtitles, colors)):
        box = FancyBboxPatch((x, 0.72), 0.225, 0.18, boxstyle="round,pad=0.012,rounding_size=0.015", fc=color, ec="#334155", lw=1.2)
        ax.add_patch(box)
        ax.text(x + 0.018, 0.845, str(i + 1), ha="left", va="center", fontsize=12, fontweight="bold", color="#172033")
        ax.text(x + 0.125, 0.845, title, ha="center", va="center", fontsize=10.3, fontweight="bold", color="#172033", linespacing=1.05)
        ax.text(x + 0.1125, 0.775, subtitle, ha="center", va="center", fontsize=9, color="#334155", linespacing=1.3)
        if i < 3:
            ax.add_patch(FancyArrowPatch((x + 0.226, 0.81), (xs[i + 1] - 0.006, 0.81), arrowstyle="-|>", mutation_scale=13, lw=1.2, color="#475569"))

    ax.text(0.5, 0.955, "Realized-Intervention Fidelity Framework", ha="center", va="center", fontsize=17, fontweight="bold", color="#111827")
    ax.text(0.5, 0.925, "Specification → executable logic → logged exposure → defensible outcome interpretation", ha="center", va="center", fontsize=10.5, color="#475569")

    f_med = metrics.loc[metrics.mode_code == "F", "contact_to_adaptation_latency_s"].median()
    examples = [
        ("A", "fixed", "fixed preset", "logged fixed", "interpretation retained", "#F3F4F6"),
        ("G", "force-only", "raw force; no contact gate", "43/45 pre-contact", "not isolated post-contact", "#F2EAF7"),
        ("E", "vision", "bundled profile transition", "window-specific exposure", "bundled association only", "#E8EEF8"),
        ("F", "+0.20-s gate", "mixed-clock comparison", f"median contact+{f_med:.3f} s", "not correctly gated effect", "#E4F4F3"),
    ]
    y0, row_h = 0.59, 0.115
    for r, (code, nominal, executable, realized, interpretation, fc) in enumerate(examples):
        y = y0 - r * row_h
        ax.text(0.04, y, code, fontsize=13, fontweight="bold", va="center", color=MODE_COLORS[code])
        vals = [nominal, executable, realized, interpretation]
        for j, (x, val) in enumerate(zip(xs, vals)):
            bx = FancyBboxPatch((x + 0.025, y - 0.035), 0.19, 0.07, boxstyle="round,pad=0.006", fc=fc, ec="#CBD5E1", lw=0.9)
            ax.add_patch(bx)
            ax.text(x + 0.12, y, val, ha="center", va="center", fontsize=8.4, color="#1F2937", wrap=True)
            if j < 3:
                ax.add_patch(FancyArrowPatch((x + 0.216, y), (xs[j + 1] + 0.018, y), arrowstyle="-|>", mutation_scale=10, lw=0.9, color="#94A3B8"))

    ax.text(0.5, 0.075, "Realized logged intervention = logged software command/event trace; physical impedance was not independently measured.", ha="center", va="center", fontsize=9, color="#475569")
    save_figure(fig, FIG / "realized_intervention_fidelity_framework")


def figure_raster(metrics: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 4, figsize=(15.5, 8.0), sharex=True, sharey=True)
    markers = {
        "task": ("|", "#111827", 55, "Task start"),
        "vision": ("o", "#2F6BFF", 18, "Vision lock"),
        "transition": ("s", "#00A6A6", 18, "Transition complete/upper bound"),
        "adapt": ("D", "#B42318", 18, "Adaptation activation"),
    }
    for ax, mode in zip(axes, MODE_ORDER):
        sub = metrics[metrics["mode"] == mode].copy()
        sort_col = {
            "default": "task_start_system_s",
            "force_only": "contact_to_adaptation_latency_s",
            "vision": "vision_lock_to_transition_complete_latency_s",
            "vision_force": "contact_to_adaptation_latency_s",
        }[mode]
        sub = sub.sort_values(sort_col, na_position="last").reset_index(drop=True)
        y = np.arange(1, len(sub) + 1)
        contact = sub["contact_system_s"].to_numpy(float)
        rels = {
            "task": sub["task_start_system_s"].to_numpy(float) - contact,
            "vision": sub["vision_lock_system_s"].to_numpy(float) - contact,
            "transition": sub["transition_complete_system_s"].to_numpy(float) - contact,
            "adapt": sub["adaptation_activation_system_s"].to_numpy(float) - contact,
        }
        for key, x in rels.items():
            marker, color, size, _ = markers[key]
            ok = np.isfinite(x)
            ax.scatter(x[ok], y[ok], marker=marker, c=color, s=size, linewidths=0.7, alpha=0.9, zorder=3)
        ax.axvspan(OUTCOME_LO, OUTCOME_HI, color="#FDE68A", alpha=0.22, zorder=0)
        ax.axvline(0, color="#111827", lw=1.2, zorder=1)
        if mode == "vision_force":
            ax.axvline(F_NOMINAL_DELAY, color="#B42318", lw=1.1, ls="--", zorder=1)
        ax.grid(axis="x", color="#E5E7EB", lw=0.7)
        ax.set_title(f"{MODE_CODE[mode]}  ({len(sub)} trials)", fontsize=12, fontweight="bold", color=MODE_COLORS[MODE_CODE[mode]])
        ax.set_xlabel("Time relative to contact (s)")
        ax.set_ylim(0, len(sub) + 1)
        ax.invert_yaxis()
    axes[0].set_ylabel("Trial (sorted within mode)")
    axes[0].set_xlim(-4.2, 3.0)
    legend = [Line2D([0], [0], marker=v[0], color="none", markerfacecolor=v[1], markeredgecolor=v[1], markersize=6, label=v[3]) for v in markers.values()]
    legend += [Line2D([0], [0], color="#111827", lw=1.2, label="Contact"), Line2D([0], [0], color="#B42318", lw=1.1, ls="--", label="F nominal +0.20 s")]
    fig.legend(handles=legend, loc="lower center", ncol=6, frameon=False, fontsize=9, bbox_to_anchor=(0.5, 0.01))
    fig.suptitle("Event-aligned realized intervention timing across all 180 trials", fontsize=15, fontweight="bold", y=0.985)
    fig.text(0.5, 0.948, "Yellow band: early force outcome window (contact +0.20 to +1.00 s)", ha="center", fontsize=9.5, color="#475569")
    fig.tight_layout(rect=[0.02, 0.07, 1, 0.94])
    save_figure(fig, FIG / "trial_level_intervention_timing_raster")


def write_report(metrics: pd.DataFrame, summary: pd.DataFrame) -> None:
    def binary(mode: str, metric: str) -> tuple[int, int]:
        x = pd.to_numeric(metrics.loc[metrics.mode_code == mode, metric], errors="coerce").dropna()
        return int((x == 1).sum()), len(x)

    a_pass = binary("A", "A_fixed_command_compliance_task_to_end")
    g_pre = binary("G", "pre_contact_activation")
    f_pre = binary("F", "pre_contact_activation")
    f_gate = binary("F", "nominal_activation_timing_compliance")
    e_start = binary("E", "transition_complete_by_outcome_window_start")
    f_start = binary("F", "transition_complete_by_outcome_window_start")
    def exposure_classes(code: str, column: str) -> tuple[int, int, int]:
        x = pd.to_numeric(metrics.loc[metrics.mode_code == code, column], errors="coerce").dropna()
        zero = int((x <= 1e-9).sum())
        full = int((x >= 1 - 1e-9).sum())
        partial = int(len(x) - zero - full)
        return zero, partial, full
    e_exp = exposure_classes("E", "vision_configuration_outcome_window_overlap")
    f_vis_exp = exposure_classes("F", "vision_configuration_outcome_window_overlap")
    f_adapt_exp = exposure_classes("F", "adaptation_outcome_window_overlap")
    provenance = binary("A", "acquisition_lineage_consistency")[0] + binary("G", "acquisition_lineage_consistency")[0] + binary("E", "acquisition_lineage_consistency")[0] + binary("F", "acquisition_lineage_consistency")[0]
    lines = [
        "# Realized-Intervention Fidelity Framework Results",
        "",
        "This report is generated from the existing clean 180-trial dataset. It does not rerun outcome significance tests and does not exclude noncompliant trials.",
        "",
        "## Stable metrics",
        "",
        "- Event times, contact-aligned activation latency, pre-contact activation, landmark commanded parameters, window-specific adaptation exposure, Kt exposure, provenance consistency, analysis timeline integrity, and control-cycle distributions are directly computable.",
        f"- A fixed-command negative control passed in {a_pass[0]}/{a_pass[1]} trials.",
        f"- G pre-contact activation occurred in {g_pre[0]}/{g_pre[1]} trials; this is descriptive timing relative to contact, not a G timing-error score.",
        f"- F pre-contact activation occurred in {f_pre[0]}/{f_pre[1]} trials; {f_gate[0]}/{f_gate[1]} met the nominal +0.20-s activation target.",
        "",
        "## Partially observable metrics",
        "",
        "- Vision-lock-to-first-parameter-change is a CSV-resolution command latency, not end-to-end perception-to-physical-impedance latency.",
        "- Transition completion is exact when the target command vector is logged. When F immediately departs from its vision base under fusion, the first fusion execution supplies only an upper bound; the observation type is retained per trial.",
        "- Logged commanded stiffness is not an independent physical impedance measurement.",
        "",
        "## Mode interpretation",
        "",
        "- A is a usable pass/negative control for fixed logged commands.",
        "- G is primarily a semantic/estimand mismatch: executable logic intentionally has no baseline-ready or contact gate. The logged behavior is generally code-consistent, even though it cannot support an isolated post-contact interpretation.",
        "- F is a temporal runtime-fidelity failure relative to the nominal +0.20-s gate, caused by a mixed-clock comparison. Its logged analysis timeline remains reconstructable.",
        f"- The vision-selected transition was complete by the outcome-window start in E {e_start[0]}/{e_start[1]} and F {f_start[0]}/{f_start[1]} trials.",
        f"- E vision-configuration exposure in the outcome window was zero/partial/full in {e_exp[0]}/{e_exp[1]}/{e_exp[2]} trials. F vision exposure was {f_vis_exp[0]}/{f_vis_exp[1]}/{f_vis_exp[2]}, while F force-adaptation exposure was {f_adapt_exp[0]}/{f_adapt_exp[1]}/{f_adapt_exp[2]}. This is direct outcome-window exposure heterogeneity, not a subgroup efficacy analysis.",
        f"- Provenance is valid for {provenance}/180 clean trials. The repair changes which records may be used and therefore restores admissible record-level linkage; it did not by itself reverse the principal E-A numerical pattern.",
        "",
        "## Framework conclusion",
        "",
        "The data support the bounded proposition: realized-intervention reconstruction can change the admissible interpretation of nominal controller comparisons. The strongest support is a change in estimand/mechanistic interpretation, not a universal claim that numerical rankings must reverse.",
    ]
    (OUT / "REALIZED_INTERVENTION_FIDELITY_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    FIG.mkdir(exist_ok=True)
    TAB.mkdir(exist_ok=True)
    master = pd.read_csv(MASTER_PATH)
    master = master[master["included_main_clean"].eq(1)].copy()
    lineage = pd.read_csv(LINEAGE_PATH).set_index("record_id", drop=False)
    scalar = pd.read_csv(TRIAL_METRICS_PATH).set_index("record_id", drop=False)
    timing = pd.read_csv(TIMING_PATH).set_index("record_id", drop=False)
    if len(master) != 180 or master["trial_key"].nunique() != 180:
        raise RuntimeError("Expected exactly 180 selected clean trial keys")
    if set(master["record_id"]) != set(scalar.index) or set(master["record_id"]) != set(timing.index):
        raise RuntimeError("Master, scalar, and timing record IDs do not match")

    specs = build_specification()
    trial_rows, exposure_rows = [], []
    for _, row in master.sort_values(["mode", "participant", "material", "block"]).iterrows():
        rid = row["record_id"]
        trial, exposure = analyze_trial(row, scalar.loc[rid], timing.loc[rid], lineage.loc[rid])
        trial_rows.append(trial)
        exposure_rows.append(exposure)
    metrics = pd.DataFrame(trial_rows).sort_values(["mode_code", "participant", "material", "block"])
    exposure = pd.DataFrame(exposure_rows).sort_values(["mode_code", "participant", "material", "block"])
    config_summary = summarize(metrics)
    interpretation = build_interpretation_table(metrics)

    specs.to_csv(OUT / "intervention_specification.csv", index=False, encoding="utf-8-sig")
    metrics.to_csv(OUT / "trial_level_fidelity_metrics.csv", index=False, encoding="utf-8-sig")
    config_summary.to_csv(OUT / "configuration_fidelity_summary.csv", index=False, encoding="utf-8-sig")
    exposure.to_csv(OUT / "outcome_window_exposure.csv", index=False, encoding="utf-8-sig")
    interpretation.to_csv(TAB / "nominal_vs_realized_interpretation.csv", index=False, encoding="utf-8-sig")

    figure_framework(metrics)
    figure_raster(metrics)
    write_report(metrics, config_summary)

    print("Generated fidelity framework outputs for", len(metrics), "trials")


if __name__ == "__main__":
    main()
