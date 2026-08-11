#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reproducible audit for the timing/operator-effects paper direction.

The script reads the preserved 180-trial first-attempt data and writes only
derived tables/figures.  The four mouse trials are a falsification pilot and
are never pooled with the human experiment.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats


HERE = Path(__file__).resolve().parent
PAPER = HERE.parent
RAW = PAPER / "01_primary_first_attempt_data"
TRIAL_METRICS = PAPER / "03_processed_data" / "trial_metrics_main_180.csv"
FIGURES = PAPER / "05_figures"
PILOT_ROOTS = [
    Path(r"F:\sun\sunhan\data\第二次"),
    Path(r"F:\sun\sunhan\data\trust_correction"),
]

MODE_ORDER = ["default", "force_only", "vision", "vision_force"]
MODE_CODE = {"default": "A", "force_only": "G", "vision": "E", "vision_force": "F"}
MODE_LABEL = {
    "default": "A Fixed",
    "force_only": "G Reactive force",
    "vision": "E Visual prior",
    "vision_force": "F Visual + force",
}
COLORS = {
    "default": "#6B7280",
    "force_only": "#7C3AED",
    "vision": "#2563EB",
    "vision_force": "#059669",
}


def read_csv(path: Path) -> list[dict]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"empty output is not allowed: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def finite(value: object) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return math.nan
    return result if math.isfinite(result) else math.nan


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_safe(value: object) -> object:
    """Replace non-finite floats so the audit JSON is standards compliant."""
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, (float, np.floating)) and not math.isfinite(float(value)):
        return None
    return value


def mean_sd(values: list[float]) -> tuple[float, float]:
    clean = np.asarray([v for v in values if math.isfinite(v)], dtype=float)
    if clean.size == 0:
        return math.nan, math.nan
    return float(clean.mean()), float(clean.std(ddof=1)) if clean.size > 1 else 0.0


def vector_speed(rows: list[dict], prefix: str, contact_s: float,
                 start_s: float, end_s: float) -> float:
    selected = [
        row for row in rows
        if start_s <= finite(row.get("system_time")) - contact_s <= end_s
    ]
    if len(selected) < 3:
        return math.nan
    t = np.asarray([finite(row["system_time"]) for row in selected])
    xyz = np.asarray([
        [finite(row[f"{prefix}_{axis}"]) for axis in "xyz"] for row in selected
    ])
    dt = np.diff(t)
    dx = np.diff(xyz, axis=0)
    valid = (np.isfinite(dt) & (dt > 0) & (dt < 0.10)
             & np.all(np.isfinite(dx), axis=1))
    if not np.any(valid):
        return math.nan
    return float(np.mean(np.linalg.norm(dx[valid], axis=1) / dt[valid]))


def tracking_error(rows: list[dict], contact_s: float,
                   start_s: float, end_s: float) -> float:
    values = []
    for row in rows:
        relative = finite(row.get("system_time")) - contact_s
        if not start_s <= relative <= end_s:
            continue
        target = np.asarray([finite(row[f"target_{axis}"]) for axis in "xyz"])
        robot = np.asarray([finite(row[f"robot_{axis}"]) for axis in "xyz"])
        if np.all(np.isfinite(target)) and np.all(np.isfinite(robot)):
            values.append(float(np.linalg.norm(target - robot)))
    return float(np.mean(values)) if values else math.nan


def load_human_trials() -> list[dict]:
    base = read_csv(TRIAL_METRICS)
    index = {
        (r["material"], r["participant"], r["block"], r["mode"]): r
        for r in base
    }
    output = []
    for path in sorted(RAW.rglob("*.csv")):
        material, participant, block = path.relative_to(RAW).parts[:3]
        mode = path.stem.rsplit("_", 2)[0]
        metric = index.get((material, participant, block, mode))
        if metric is None:
            raise KeyError(f"unmatched trial: {path}")
        rows = read_csv(path)
        contact = finite(metric["contact_onset_system_s"])
        output.append({
            "trial_key": metric["trial_key"],
            "participant": participant,
            "material": material,
            "block": block,
            "block_id": metric["block_id"],
            "mode": mode,
            "mode_code": MODE_CODE[mode],
            "visual": metric["visual"],
            "force_adaptive": metric["force_adaptive"],
            "success": metric["success"],
            "primary_excess_impulse_Ns_0p2_1p0": finite(metric["primary_excess_impulse_Ns_0p2_1p0"]),
            "initial_peak_force_N_0_0p2": finite(metric["initial_peak_force_N_0_0p2"]),
            "stiffness_mean_N_m_0p2_1p0": finite(metric["stiffness_mean_N_m_0p2_1p0"]),
            "omega_speed_precontact_m_s": vector_speed(rows, "omega", contact, -0.30, 0.0),
            "omega_speed_initial_contact_m_s": vector_speed(rows, "omega", contact, 0.0, 0.20),
            "target_speed_precontact_m_s": vector_speed(rows, "target", contact, -0.30, 0.0),
            "target_speed_initial_contact_m_s": vector_speed(rows, "target", contact, 0.0, 0.20),
            "robot_speed_precontact_m_s": vector_speed(rows, "robot", contact, -0.30, 0.0),
            "robot_speed_initial_contact_m_s": vector_speed(rows, "robot", contact, 0.0, 0.20),
            "tracking_error_precontact_m": tracking_error(rows, contact, -0.30, 0.0),
            "tracking_error_initial_contact_m": tracking_error(rows, contact, 0.0, 0.20),
            "source_csv": str(path),
        })
    if len(output) != 180:
        raise ValueError(f"expected 180 human trials, found {len(output)}")
    return output


def holm_adjust(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    adjusted = [math.nan] * len(values)
    running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, min(1.0, (len(values) - rank) * values[idx]))
        adjusted[idx] = running
    return adjusted


def paired_contrasts(rows: list[dict]) -> list[dict]:
    metrics = [
        "primary_excess_impulse_Ns_0p2_1p0",
        "initial_peak_force_N_0_0p2",
        "stiffness_mean_N_m_0p2_1p0",
        "omega_speed_precontact_m_s",
        "target_speed_precontact_m_s",
        "robot_speed_precontact_m_s",
        "tracking_error_initial_contact_m",
    ]
    comparisons = [
        ("vision", "default", "E-A: visual prior vs fixed"),
        ("force_only", "default", "G-A: reactive force vs fixed"),
        ("vision", "force_only", "E-G: anticipation vs reaction"),
        ("vision_force", "vision", "F-E: force added to vision"),
        ("vision_force", "force_only", "F-G: visual prior added to force"),
    ]
    lookup = {(r["block_id"], r["mode"]): r for r in rows}
    blocks = sorted({r["block_id"] for r in rows})
    output = []
    for metric in metrics:
        group = []
        for mode_a, mode_b, label in comparisons:
            diffs = np.asarray([
                finite(lookup[(block, mode_a)][metric])
                - finite(lookup[(block, mode_b)][metric]) for block in blocks
            ])
            diffs = diffs[np.isfinite(diffs)]
            n = len(diffs)
            mean = float(diffs.mean())
            sd = float(diffs.std(ddof=1))
            sem = sd / math.sqrt(n)
            critical = float(stats.t.ppf(0.975, n - 1))
            group.append({
                "metric": metric,
                "contrast": label,
                "mode_a": mode_a,
                "mode_b": mode_b,
                "n_pairs": n,
                "mean_paired_difference": mean,
                "sd_paired_difference": sd,
                "ci95_low": mean - critical * sem,
                "ci95_high": mean + critical * sem,
                "paired_effect_dz": mean / sd if sd > 0 else math.nan,
                "p_value": float(stats.ttest_1samp(diffs, 0.0).pvalue),
            })
        for row, corrected in zip(group, holm_adjust([r["p_value"] for r in group])):
            row["p_holm_within_metric"] = corrected
            output.append(row)
    return output


def mode_descriptives(rows: list[dict]) -> list[dict]:
    metrics = [
        "primary_excess_impulse_Ns_0p2_1p0", "initial_peak_force_N_0_0p2",
        "stiffness_mean_N_m_0p2_1p0", "omega_speed_precontact_m_s",
        "target_speed_precontact_m_s", "robot_speed_precontact_m_s",
        "tracking_error_initial_contact_m",
    ]
    output = []
    for mode in MODE_ORDER:
        selected = [r for r in rows if r["mode"] == mode]
        result = {"mode": mode, "mode_code": MODE_CODE[mode], "n_trials": len(selected)}
        for metric in metrics:
            mean, sd = mean_sd([finite(r[metric]) for r in selected])
            result[f"{metric}_mean"] = mean
            result[f"{metric}_sd"] = sd
        output.append(result)
    return output


def endogeneity_audit(rows: list[dict]) -> list[dict]:
    output = []
    for mode in MODE_ORDER:
        selected = [r for r in rows if r["mode"] == mode]
        stiffness = np.asarray([finite(r["stiffness_mean_N_m_0p2_1p0"]) for r in selected])
        impulse = np.asarray([finite(r["primary_excess_impulse_Ns_0p2_1p0"]) for r in selected])
        valid = np.isfinite(stiffness) & np.isfinite(impulse)
        if np.unique(stiffness[valid]).size < 2:
            rho, p = math.nan, math.nan
        else:
            rho, p = stats.spearmanr(stiffness[valid], impulse[valid])
        output.append({
            "mode": mode, "mode_code": MODE_CODE[mode], "n": int(valid.sum()),
            "spearman_rho_stiffness_vs_impulse": float(rho),
            "p_value_descriptive_only": float(p),
            "causal_warning": "force drives stiffness in adaptive modes; correlation is endogenous and not a treatment effect",
        })
    return output


def event_time(summary: dict, name: str) -> float:
    for item in summary.get("experiment", {}).get("events", []):
        if item.get("event") == name:
            return finite(item.get("system_time"))
    return math.nan


def pilot_directories() -> list[Path]:
    for root in PILOT_ROOTS:
        dirs = sorted(root.glob("MOUSE_DIAG,2,*")) if root.exists() else []
        dirs = [d for d in dirs if any(d.glob("*.csv"))]
        if len(dirs) == 4:
            return dirs
    return []


def mouse_pilot_audit() -> list[dict]:
    output = []
    for directory in pilot_directories():
        csv_path = next(directory.glob("*.csv"))
        summary_path = next(directory.glob("*summary.json"))
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        rows = read_csv(csv_path)
        condition = summary["mode"]["condition_code"]
        contact = event_time(summary, "contact_onset")
        threshold = finite(summary["experiment"]["force_threshold_N"])
        window = []
        for row in rows:
            relative = finite(row.get("system_time")) - contact
            if 0.2 <= relative <= 1.0:
                window.append((finite(row.get("system_time")), finite(row.get("F_ext_mag"))))
        impulse = 0.0
        for (t0, f0), (t1, f1) in zip(window[:-1], window[1:]):
            impulse += max(0.0, ((f0 + f1) / 2.0) - threshold) * max(0.0, t1 - t0)
        control_dt = np.asarray([finite(r.get("control_dt")) for r in rows])
        control_dt = control_dt[np.isfinite(control_dt) & (control_dt >= 0)] * 1000.0
        final = summary["final_params"]
        output.append({
            "condition": condition,
            "prior_condition": summary["mode"]["prior_condition"],
            "posterior_correction": int(bool(summary["mode"]["posterior_correction"])),
            "completed": int(bool(summary["experiment"]["completed"])),
            "force_threshold_N": threshold,
            "excess_impulse_Ns_0p2_1p0": impulse,
            "initial_K_N_m": summary["trust_correction_config"]["prior_K_N_per_m"],
            "window_end_K_N_m": final["K_trans"],
            "final_prior_trust": final["prior_trust_final"],
            "control_dt_median_ms": float(np.median(control_dt)),
            "control_dt_p99_ms": float(np.percentile(control_dt, 99)),
            "control_dt_over_20ms_pct": float(np.mean(control_dt > 20) * 100),
            "control_dt_over_50ms_pct": float(np.mean(control_dt > 50) * 100),
            "source_csv": str(csv_path),
            "source_sha256": sha256(csv_path),
            "inference_status": "falsification pilot only; n=1 per cell; excluded from human inference",
        })
    return sorted(output, key=lambda r: r["condition"])


def save_all_formats(fig: plt.Figure, stem: Path) -> None:
    for suffix, kwargs in [("png", {"dpi": 600}), ("pdf", {}), ("svg", {})]:
        fig.savefig(stem.with_suffix(f".{suffix}"), bbox_inches="tight", **kwargs)


def figure_evidence(rows: list[dict], contrasts: list[dict], endog: list[dict]) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.1))
    blocks = sorted({r["block_id"] for r in rows})
    lookup = {(r["block_id"], r["mode"]): r for r in rows}
    data = [[lookup[(b, m)]["primary_excess_impulse_Ns_0p2_1p0"] for b in blocks] for m in MODE_ORDER]
    vp = axes[0].violinplot(data, showmeans=False, showmedians=True, widths=0.78)
    for body, mode in zip(vp["bodies"], MODE_ORDER):
        body.set_facecolor(COLORS[mode]); body.set_edgecolor("none"); body.set_alpha(0.55)
    axes[0].scatter(np.repeat(np.arange(1, 5), 45), np.concatenate(data), s=7, color="#111827", alpha=0.20)
    axes[0].set_xticks(range(1, 5), [MODE_CODE[m] for m in MODE_ORDER])
    axes[0].set_ylabel("Excess-force impulse (N·s), 0.2–1.0 s")
    axes[0].set_title("a  Human trials (n=45 paired blocks)", loc="left", fontweight="bold")

    selected = [r for r in contrasts if r["metric"] == "primary_excess_impulse_Ns_0p2_1p0"]
    y = np.arange(len(selected))[::-1]
    means = np.asarray([r["mean_paired_difference"] for r in selected])
    lo = np.asarray([r["ci95_low"] for r in selected])
    hi = np.asarray([r["ci95_high"] for r in selected])
    axes[1].axvline(0, color="#111827", lw=1)
    axes[1].errorbar(means, y, xerr=[means - lo, hi - means], fmt="o", color="#2563EB", capsize=3)
    axes[1].set_yticks(y, [r["contrast"].split(":")[0] for r in selected])
    axes[1].set_xlabel("Paired difference (first mode − second mode), N·s")
    axes[1].set_title("b  Prespecified timing contrasts", loc="left", fontweight="bold")

    g = [r for r in rows if r["mode"] == "force_only"]
    x = np.asarray([r["stiffness_mean_N_m_0p2_1p0"] for r in g])
    z = np.asarray([r["primary_excess_impulse_Ns_0p2_1p0"] for r in g])
    axes[2].scatter(x, z, s=22, color=COLORS["force_only"], alpha=0.70)
    rho = next(r["spearman_rho_stiffness_vs_impulse"] for r in endog if r["mode"] == "force_only")
    axes[2].text(0.04, 0.95, f"Spearman ρ = {rho:.3f}\n(descriptive, endogenous)",
                 transform=axes[2].transAxes, va="top")
    axes[2].set_xlabel("Observed mean stiffness (N/m)")
    axes[2].set_ylabel("Excess-force impulse (N·s)")
    axes[2].set_title("c  Reverse-causal correlation in G", loc="left", fontweight="bold")
    fig.tight_layout()
    save_all_formats(fig, FIGURES / "fig7_timing_and_human_compensation_evidence")
    plt.close(fig)


def figure_replay_design() -> None:
    fig, ax = plt.subplots(figsize=(11.8, 4.6))
    ax.axis("off")
    boxes = [
        (0.03, 0.58, 0.20, 0.24, "Recorded human trial\ninput trajectory + events", "#DBEAFE"),
        (0.32, 0.58, 0.20, 0.24, "Matched robot replay\nsame target trajectory", "#DCFCE7"),
        (0.61, 0.72, 0.23, 0.18, "Policy 1\noriginal impedance", "#EDE9FE"),
        (0.61, 0.45, 0.23, 0.18, "Policy 2\ncounterfactual impedance", "#FEF3C7"),
        (0.86, 0.58, 0.12, 0.24, "Direct\nmechanical\neffect", "#FCE7F3"),
        (0.32, 0.12, 0.36, 0.18, "Human total effect − replay direct effect\n= operator-mediated component (estimand)", "#F3F4F6"),
    ]
    for x, y, w, h, label, color in boxes:
        rect = plt.Rectangle((x, y), w, h, transform=ax.transAxes, facecolor=color,
                             edgecolor="#374151", lw=1.3)
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", transform=ax.transAxes, fontsize=10)
    arrows = [((0.23, 0.70), (0.32, 0.70)), ((0.52, 0.70), (0.61, 0.81)),
              ((0.52, 0.70), (0.61, 0.54)), ((0.84, 0.81), (0.86, 0.73)),
              ((0.84, 0.54), (0.86, 0.66)), ((0.92, 0.58), (0.68, 0.27))]
    for start, end in arrows:
        ax.annotate("", xy=end, xytext=start, xycoords=ax.transAxes,
                    arrowprops=dict(arrowstyle="->", lw=1.5, color="#374151"))
    ax.text(0.03, 0.95, "Matched human–replay decomposition", transform=ax.transAxes,
            fontsize=15, fontweight="bold", va="top")
    ax.text(0.03, 0.38, "Kinematics are held fixed during replay; only the impedance policy changes.",
            transform=ax.transAxes, fontsize=10.5)
    ax.text(0.03, 0.04, "Required before claiming causal operator compensation; this is a protocol, not a result.",
            transform=ax.transAxes, fontsize=10, color="#B91C1C")
    save_all_formats(fig, FIGURES / "fig8_matched_human_replay_design")
    plt.close(fig)


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    trials = load_human_trials()
    contrasts = paired_contrasts(trials)
    descriptives = mode_descriptives(trials)
    endog = endogeneity_audit(trials)
    pilot = mouse_pilot_audit()
    write_csv(HERE / "human_motion_trial_metrics_180.csv", trials)
    write_csv(HERE / "paired_timing_contrasts.csv", contrasts)
    write_csv(HERE / "mode_descriptives_timing.csv", descriptives)
    write_csv(HERE / "adaptive_endogeneity_audit.csv", endog)
    if pilot:
        write_csv(HERE / "mouse_pilot_falsification.csv", pilot)
    primary = [r for r in contrasts if r["metric"] == "primary_excess_impulse_Ns_0p2_1p0"]
    summary = {
        "status": "timing/operator-effects direction; trust-correction main claim retired",
        "human_design": {"n_trials": len(trials), "n_participants": 5, "n_paired_blocks": 45,
                         "success_count": sum(int(r["success"]) for r in trials)},
        "primary_metric": "baseline-corrected excess-force impulse, 0.2–1.0 s after contact",
        "primary_contrasts": primary,
        "mode_descriptives": descriptives,
        "endogeneity_audit": endog,
        "mouse_pilot": pilot,
        "causal_boundary": "operator compensation is a hypothesis until matched robot replay is completed",
    }
    (HERE / "new_direction_summary.json").write_text(
        json.dumps(json_safe(summary), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8"
    )
    figure_evidence(trials, contrasts, endog)
    figure_replay_design()
    print(json.dumps({"human_trials": len(trials), "pilot_trials": len(pilot),
                      "outputs": str(HERE)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
