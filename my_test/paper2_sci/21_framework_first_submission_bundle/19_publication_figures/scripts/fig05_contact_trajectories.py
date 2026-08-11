#!/usr/bin/env python3
"""Generate Figure 5: contact-aligned force and commanded-stiffness trajectories."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd
from scipy.stats import t as student_t

from figure_common import (
    parse_root_args,
    prepare_run,
    read_clean_csv,
    record_manifest,
    write_source_csv,
)
from figure_style import (
    MODE_COLORS,
    MODE_LINESTYLES,
    MODE_ORDER,
    figure_size,
    light_horizontal_grid,
    panel_label,
    save_publication_figure,
    set_publication_style,
)


STEM = "Fig05_contact_aligned_trajectories"
FIGURE_WIDTH_MM = 193.7
FIGURE_HEIGHT_MM = 88.0
LAYOUT = {
    "left": 0.085,
    "right": 0.985,
    "bottom": 0.245,
    "top": 0.820,
    "wspace": 0.27,
}
TIME_GRID = np.round(np.arange(-0.50, 1.5001, 0.01), 2)
OUTCOME_WINDOW = (0.20, 1.00)
CURVE_WIDTH = 1.2
CI_ALPHA = 0.09

SUMMARY_COLUMNS = [
    "mode_code",
    "t_rel_contact_s",
    "n_participants",
    "excess_force_N_mean",
    "excess_force_N_ci95_low",
    "excess_force_N_ci95_high",
    "stiffness_trans_N_m_mean",
    "stiffness_trans_N_m_ci95_low",
    "stiffness_trans_N_m_ci95_high",
]
TRAJECTORY_COLUMNS = [
    "record_id",
    "participant",
    "mode_code",
    "t_rel_contact_s",
    "excess_force_N",
    "stiffness_trans_N_m",
]
TRIAL_COLUMNS = [
    "record_id",
    "mode_code",
    "K_trans_at_contact",
    "K_trans_at_contact_plus_0p2",
]


def prune_legacy_manifest_alias(manifest_path: Path) -> None:
    """Remove the superseded pre-redesign Figure 5 manifest entry."""
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["figures"] = [
        record
        for record in payload.get("figures", [])
        if record.get("figure_name") != "Fig05_contact_trajectories"
    ]
    manifest_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _add_check(
    checks: list[dict[str, object]],
    name: str,
    actual: object,
    expected: object,
    passed: bool,
) -> None:
    checks.append(
        {
            "name": name,
            "actual": actual,
            "expected": expected,
            "passed": bool(passed),
        }
    )


def _format_value(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.12g}"
    return str(value)


def reconstruct_hierarchical_summary(trajectories: pd.DataFrame) -> pd.DataFrame:
    """Reconstruct the frozen hierarchy for QA only; the plotted data remain the clean summary."""
    participant_curves = (
        trajectories.groupby(
            ["participant", "mode_code", "t_rel_contact_s"],
            as_index=False,
            sort=False,
        )[["excess_force_N", "stiffness_trans_N_m"]]
        .mean()
    )
    grouped = participant_curves.groupby(
        ["mode_code", "t_rel_contact_s"],
        sort=False,
    )
    means = grouped[["excess_force_N", "stiffness_trans_N_m"]].mean()
    sems = grouped[["excess_force_N", "stiffness_trans_N_m"]].sem()
    counts = grouped["participant"].nunique().rename("n_participants_reconstructed")
    critical = float(student_t.ppf(0.975, 4))
    result = means.join(sems, lsuffix="_mean", rsuffix="_sem").join(counts).reset_index()
    result["excess_force_N_ci95_low"] = (
        result["excess_force_N_mean"] - critical * result["excess_force_N_sem"]
    )
    result["excess_force_N_ci95_high"] = (
        result["excess_force_N_mean"] + critical * result["excess_force_N_sem"]
    )
    result["stiffness_trans_N_m_ci95_low"] = (
        result["stiffness_trans_N_m_mean"] - critical * result["stiffness_trans_N_m_sem"]
    )
    result["stiffness_trans_N_m_ci95_high"] = (
        result["stiffness_trans_N_m_mean"] + critical * result["stiffness_trans_N_m_sem"]
    )
    return result


def contact_stiffness_summary(trials: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for mode in MODE_ORDER:
        values = trials.loc[trials["mode_code"].eq(mode), "K_trans_at_contact"].astype(float)
        rows.append(
            {
                "mode_code": mode,
                "timepoint": "contact",
                "median_N_m": float(values.median()),
                "min_N_m": float(values.min()),
                "max_N_m": float(values.max()),
            }
        )
    f_values = trials.loc[
        trials["mode_code"].eq("F"),
        "K_trans_at_contact_plus_0p2",
    ].astype(float)
    rows.append(
        {
            "mode_code": "F",
            "timepoint": "contact +0.20 s",
            "median_N_m": float(f_values.median()),
            "min_N_m": float(f_values.min()),
            "max_N_m": float(f_values.max()),
        }
    )
    return pd.DataFrame(rows)


def run_figure_qa(
    summary: pd.DataFrame,
    trajectories: pd.DataFrame,
    trials: pd.DataFrame,
) -> tuple[list[dict[str, object]], pd.DataFrame, dict[str, float]]:
    checks: list[dict[str, object]] = []
    expected_mode_rows = {mode: 201 for mode in MODE_ORDER}
    summary_mode_rows = summary.groupby("mode_code").size().to_dict()
    _add_check(
        checks,
        "clean summary rows by configuration",
        summary_mode_rows,
        expected_mode_rows,
        summary_mode_rows == expected_mode_rows and len(summary) == 804,
    )
    for mode in MODE_ORDER:
        grid = np.sort(
            summary.loc[summary["mode_code"].eq(mode), "t_rel_contact_s"].to_numpy(dtype=float)
        )
        _add_check(
            checks,
            f"{mode} clean time grid -0.50 to +1.50 s at 0.01 s",
            (len(grid), float(grid[0]), float(grid[-1])),
            (201, -0.5, 1.5),
            len(grid) == 201 and np.allclose(grid, TIME_GRID, rtol=0.0, atol=1e-12),
        )
    n_participants_values = sorted(
        set(int(value) for value in summary["n_participants"].to_numpy())
    )
    _add_check(
        checks,
        "summary participant count at every time point",
        n_participants_values,
        [5],
        n_participants_values == [5],
    )
    missing_summary = int(summary[SUMMARY_COLUMNS].isna().sum().sum())
    _add_check(
        checks,
        "missing plotted summary values",
        missing_summary,
        0,
        missing_summary == 0,
    )

    _add_check(
        checks,
        "frozen aligned trajectory rows",
        len(trajectories),
        36180,
        len(trajectories) == 36180,
    )
    _add_check(
        checks,
        "aligned trajectory trial identities",
        trajectories["record_id"].nunique(),
        180,
        trajectories["record_id"].nunique() == 180,
    )
    _add_check(
        checks,
        "aligned trajectory participants",
        trajectories["participant"].nunique(),
        5,
        trajectories["participant"].nunique() == 5,
    )
    points_per_trial = trajectories.groupby("record_id").size()
    point_count_values = sorted(set(int(value) for value in points_per_trial.to_numpy()))
    _add_check(
        checks,
        "aligned points per trial",
        point_count_values,
        [201],
        point_count_values == [201],
    )
    trial_cells = (
        trajectories[["record_id", "participant", "mode_code"]]
        .drop_duplicates()
        .groupby(["participant", "mode_code"])
        .size()
    )
    trials_per_cell = sorted(set(int(value) for value in trial_cells.to_numpy()))
    _add_check(
        checks,
        "trials averaged within each participant/configuration",
        trials_per_cell,
        [9],
        len(trial_cells) == 20 and trials_per_cell == [9],
    )

    reconstructed = reconstruct_hierarchical_summary(trajectories)
    comparison = reconstructed.merge(
        summary,
        on=["mode_code", "t_rel_contact_s"],
        how="inner",
        validate="one_to_one",
        suffixes=("_reconstructed", "_clean"),
    )
    comparison_columns = [
        "excess_force_N_mean",
        "excess_force_N_ci95_low",
        "excess_force_N_ci95_high",
        "stiffness_trans_N_m_mean",
        "stiffness_trans_N_m_ci95_low",
        "stiffness_trans_N_m_ci95_high",
    ]
    max_differences: dict[str, float] = {}
    for column in comparison_columns:
        reconstructed_column = (
            column
            if column.endswith("ci95_low") or column.endswith("ci95_high")
            else f"{column}_reconstructed"
        )
        clean_column = (
            f"{column}_clean"
            if column.endswith("_mean")
            else column
        )
        if column.endswith("ci95_low") or column.endswith("ci95_high"):
            reconstructed_column = f"{column}_reconstructed"
            clean_column = f"{column}_clean"
        max_difference = float(
            np.max(
                np.abs(
                    comparison[reconstructed_column].to_numpy(dtype=float)
                    - comparison[clean_column].to_numpy(dtype=float)
                )
            )
        )
        max_differences[column] = max_difference
        _add_check(
            checks,
            f"hierarchical reconstruction matches {column}",
            max_difference,
            "<= 1e-10",
            max_difference <= 1e-10,
        )
    reconstructed_n = sorted(
        set(int(value) for value in reconstructed["n_participants_reconstructed"].to_numpy())
    )
    _add_check(
        checks,
        "hierarchical CI uses five participant curves",
        reconstructed_n,
        [5],
        reconstructed_n == [5],
    )

    contact_summary = contact_stiffness_summary(trials)
    expected_contact = {
        ("A", "contact"): (200.0, 200.0, 200.0),
        ("G", "contact"): (198.3, 178.9, 200.0),
        ("E", "contact"): (120.0, 50.0, 200.0),
        ("F", "contact"): (120.0, 50.0, 200.0),
        ("F", "contact +0.20 s"): (116.1, 41.1, 189.2),
    }
    for row in contact_summary.itertuples(index=False):
        actual = (
            round(float(row.median_N_m), 1),
            round(float(row.min_N_m), 1),
            round(float(row.max_N_m), 1),
        )
        expected = expected_contact[(row.mode_code, row.timepoint)]
        _add_check(
            checks,
            f"{row.mode_code} commanded K_t at {row.timepoint}: median/min/max (N/m)",
            actual,
            expected,
            actual == expected,
        )
    return checks, contact_summary, max_differences


def write_qa_report(
    path: Path,
    checks: list[dict[str, object]],
    contact_summary: pd.DataFrame,
    max_differences: dict[str, float],
    input_paths: list[Path],
) -> bool:
    passed = all(bool(item["passed"]) for item in checks)
    lines = [
        "Figure 5 QA — Contact-aligned force and commanded-stiffness trajectories",
        f"STATUS: {'PASS' if passed else 'FAIL'}",
        "",
        "Inputs:",
        *(f"- {input_path}" for input_path in input_paths),
        "",
        "Checks:",
    ]
    for item in checks:
        status = "PASS" if item["passed"] else "FAIL"
        lines.append(
            f"[{status}] {item['name']} | actual={_format_value(item['actual'])} "
            f"| expected={_format_value(item['expected'])}"
        )
    lines.extend(
        [
            "",
            "Underlying trial-level commanded K_t summaries (QA only; not plotted as inference):",
            contact_summary.to_string(index=False),
            "",
            "Maximum absolute differences between reconstructed hierarchical summaries and clean summary:",
            *(f"- {column}: {difference:.12g}" for column, difference in max_differences.items()),
            "",
            "No pointwise significance testing is run by this figure script.",
            "No smoothing or interpolation is applied by this figure script; it reads the frozen aligned outputs.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return passed


def plot_panel(
    ax: plt.Axes,
    source: pd.DataFrame,
    prefix: str,
    ylabel: str,
    title: str,
    letter: str,
    panel_x: float,
    window_label_y: float,
) -> None:
    ax.axvspan(
        OUTCOME_WINDOW[0],
        OUTCOME_WINDOW[1],
        facecolor="#E6E6E6",
        alpha=0.55,
        edgecolor="none",
        zorder=0,
    )
    for mode in MODE_ORDER:
        frame = source.loc[source["mode_code"].eq(mode)].sort_values(
            "t_rel_contact_s",
            kind="stable",
        )
        x = frame["t_rel_contact_s"].to_numpy(dtype=float)
        mean = frame[f"{prefix}_mean"].to_numpy(dtype=float)
        low = frame[f"{prefix}_ci95_low"].to_numpy(dtype=float)
        high = frame[f"{prefix}_ci95_high"].to_numpy(dtype=float)
        ax.fill_between(
            x,
            low,
            high,
            color=MODE_COLORS[mode],
            alpha=CI_ALPHA,
            linewidth=0,
            zorder=1,
        )
        ax.plot(
            x,
            mean,
            color=MODE_COLORS[mode],
            linestyle=MODE_LINESTYLES[mode],
            linewidth=CURVE_WIDTH,
            solid_capstyle="round",
            label=mode,
            zorder=3,
        )
    ax.axvline(0.0, color="#3F3F3F", linewidth=0.8, linestyle="-", zorder=4)
    ax.text(
        0.60,
        window_label_y,
        "Outcome window",
        transform=ax.get_xaxis_transform(),
        ha="center",
        va="top",
        fontsize=7.0,
        color="#555555",
    )
    ax.set_xlim(-0.50, 1.50)
    ax.set_xlabel("Time relative to contact (s)")
    ax.set_ylabel(ylabel)
    ax.set_title(title, loc="left", pad=7)
    light_horizontal_grid(ax)
    panel_label(ax, letter, x=panel_x, y=1.09)


def create_figure(source: pd.DataFrame) -> plt.Figure:
    set_publication_style()
    fig, axes = plt.subplots(
        1,
        2,
        figsize=figure_size(FIGURE_WIDTH_MM, FIGURE_HEIGHT_MM),
    )
    fig.subplots_adjust(**LAYOUT)
    plot_panel(
        axes[0],
        source,
        "excess_force_N",
        "Threshold-referenced excess force (N)",
        "Threshold-referenced excess force",
        "A",
        -0.13,
        0.97,
    )
    plot_panel(
        axes[1],
        source,
        "stiffness_trans_N_m",
        r"Commanded translational stiffness, $K_t$ (N/m)",
        "Commanded translational stiffness",
        "B",
        -0.30,
        0.88,
    )

    legend_handles = [
        Line2D(
            [],
            [],
            color=MODE_COLORS[mode],
            linestyle=MODE_LINESTYLES[mode],
            linewidth=CURVE_WIDTH,
            label=mode,
        )
        for mode in MODE_ORDER
    ]
    fig.legend(
        handles=legend_handles,
        loc="upper center",
        bbox_to_anchor=(0.53, 0.985),
        ncol=4,
        handlelength=3.0,
        columnspacing=1.8,
        handletextpad=0.55,
        borderaxespad=0.0,
    )
    fig.text(
        0.5,
        0.075,
        "Participant-level means and pointwise t-based 95% CIs (n=5); no pointwise tests. "
        "Descriptive context only—not causal mechanism evidence.",
        ha="center",
        va="bottom",
        fontsize=7.1,
        fontstyle="italic",
        color="#303030",
    )
    fig.text(
        0.5,
        0.030,
        "Logged stiffness is a commanded software parameter and was not independently validated as physical closed-loop impedance.",
        ha="center",
        va="bottom",
        fontsize=7.1,
        fontstyle="italic",
        color="#303030",
    )
    return fig


def main() -> None:
    args = parse_root_args(__doc__ or "")
    project_root, clean_dir, figures_dir, source_dir = prepare_run(args, __file__)
    publication_root = project_root / "19_publication_figures"
    summary_path = clean_dir / "contact_aligned_summary.csv"
    trajectories_path = clean_dir / "contact_aligned_trajectories.csv"
    trials_path = clean_dir / "trial_level_fidelity_metrics.csv"

    summary = read_clean_csv(clean_dir, summary_path.name, SUMMARY_COLUMNS)
    trajectories = read_clean_csv(clean_dir, trajectories_path.name, TRAJECTORY_COLUMNS)
    trials = read_clean_csv(clean_dir, trials_path.name, TRIAL_COLUMNS)
    checks, contact_summary, max_differences = run_figure_qa(
        summary,
        trajectories,
        trials,
    )
    qa_path = publication_root / "figure05_qa.txt"
    qa_passed = write_qa_report(
        qa_path,
        checks,
        contact_summary,
        max_differences,
        [summary_path, trajectories_path, trials_path],
    )
    print("Underlying trial-level commanded K_t summaries (QA only):")
    print(contact_summary.to_string(index=False))
    if not qa_passed:
        print("FIGURE 5 QA FAILED — STOPPING BEFORE SOURCE-DATA OR FIGURE GENERATION", file=sys.stderr)
        for item in checks:
            if not item["passed"]:
                print(
                    f"  {item['name']}: actual={item['actual']!r}; expected={item['expected']!r}",
                    file=sys.stderr,
                )
        raise SystemExit(1)
    print(f"FIGURE 5 QA: PASS ({len(checks)}/{len(checks)} checks)")

    source_path = write_source_csv(summary[SUMMARY_COLUMNS], source_dir / "figure05_source_data.csv")
    fig = create_figure(summary)
    outputs = save_publication_figure(fig, figures_dir, STEM, args.dpi)
    manifest_path = record_manifest(
        publication_root,
        project_root,
        STEM,
        Path(__file__),
        [summary_path, trajectories_path, trials_path],
        source_path,
        [*outputs, qa_path],
    )
    prune_legacy_manifest_alias(manifest_path)
    print(f"Generated {STEM}")
    for output in outputs:
        print(f"  {output}")
    print(f"  {source_path}")
    print(f"  {qa_path}")


if __name__ == "__main__":
    main()
