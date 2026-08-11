#!/usr/bin/env python3
"""Generate Figure 4: exploratory participant-level E-A force and timing outcomes."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from figure_common import (
    parse_root_args,
    prepare_run,
    read_clean_csv,
    record_manifest,
    write_source_csv,
)
from figure_style import (
    figure_size,
    panel_label,
    save_publication_figure,
    set_publication_style,
)


STEM = "Fig04_participant_EA_outcomes"
FIGURE_WIDTH_MM = 178.0
FIGURE_HEIGHT_MM = 88.0
LAYOUT = {
    "left": 0.075,
    "right": 0.985,
    "bottom": 0.245,
    "top": 0.825,
    "wspace": 0.34,
}

METRICS = [
    {
        "panel": "A",
        "source_column": "primary_excess_impulse_Ns_0p2_1p0",
        "title": "Excess-force impulse",
        "axis_label": "Threshold-referenced excess-force\nimpulse, 0.20–1.00 s after contact (N·s)",
        "unit": "N·s",
        "effect_decimals": 4,
        "expected_effect": -0.3489,
        "expected_low": -0.6080,
        "expected_high": -0.0898,
        "direction": "negative",
    },
    {
        "panel": "B",
        "source_column": "approach_time_s",
        "title": "Task-start-to-contact time",
        "axis_label": "Task-start-to-contact time (s)",
        "unit": "s",
        "effect_decimals": 4,
        "expected_effect": 1.7805,
        "expected_low": 1.5084,
        "expected_high": 2.0527,
        "direction": "positive",
    },
    {
        "panel": "C",
        "source_column": "total_task_time_s",
        "title": "Total task time",
        "axis_label": "Total task time (s)",
        "unit": "s",
        "effect_decimals": 4,
        "expected_effect": 1.2128,
        "expected_low": 0.5741,
        "expected_high": 1.8514,
        "direction": "positive",
    },
]

PARTICIPANT_COLUMNS = [
    "participant",
    "mode_code",
    *[metric["source_column"] for metric in METRICS],
]
STATISTICS_COLUMNS = [
    "metric",
    "contrast",
    "difference_definition",
    "n_participants",
    "raw_mean_difference",
    "ci95_low",
    "ci95_high",
]
TRIAL_COLUMNS = ["record_id", "participant", "mode_code"]


def prune_legacy_manifest_alias(manifest_path: Path) -> None:
    """Remove the superseded pre-redesign Figure 4 manifest entry."""
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["figures"] = [
        record
        for record in payload.get("figures", [])
        if record.get("figure_name") != "Fig04_participant_outcomes"
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


def build_source_data(
    participant: pd.DataFrame,
    statistics: pd.DataFrame,
    trial_counts: pd.Series,
) -> pd.DataFrame:
    selected = participant.loc[participant["mode_code"].isin(["A", "E"])].copy()
    long = selected.melt(
        id_vars=["participant", "mode_code"],
        value_vars=[metric["source_column"] for metric in METRICS],
        var_name="metric",
        value_name="participant_mean",
    )
    long.insert(0, "row_type", "participant_mean")
    long["panel"] = long["metric"].map(
        {metric["source_column"]: metric["panel"] for metric in METRICS}
    )
    long["metric_axis_label"] = long["metric"].map(
        {metric["source_column"]: metric["axis_label"].replace("\n", " ") for metric in METRICS}
    )
    long["unit"] = long["metric"].map(
        {metric["source_column"]: metric["unit"] for metric in METRICS}
    )
    long["n_selected_trials"] = [
        int(trial_counts.loc[(participant_id, mode_code)])
        for participant_id, mode_code in zip(long["participant"], long["mode_code"])
    ]

    wide_differences = (
        long.pivot(index=["participant", "metric"], columns="mode_code", values="participant_mean")
        .assign(participant_difference_E_minus_A=lambda frame: frame["E"] - frame["A"])
        ["participant_difference_E_minus_A"]
    )
    difference_lookup = wide_differences.to_dict()
    long["participant_difference_E_minus_A"] = [
        difference_lookup[(participant_id, metric)]
        for participant_id, metric in zip(long["participant"], long["metric"])
    ]

    requested_metrics = [metric["source_column"] for metric in METRICS]
    summary = statistics.loc[
        statistics["contrast"].eq("E-A") & statistics["metric"].isin(requested_metrics),
        STATISTICS_COLUMNS,
    ].copy()
    summary.insert(0, "row_type", "contrast_summary")
    summary["panel"] = summary["metric"].map(
        {metric["source_column"]: metric["panel"] for metric in METRICS}
    )
    summary["metric_axis_label"] = summary["metric"].map(
        {metric["source_column"]: metric["axis_label"].replace("\n", " ") for metric in METRICS}
    )
    summary["unit"] = summary["metric"].map(
        {metric["source_column"]: metric["unit"] for metric in METRICS}
    )
    summary = summary.rename(columns={"raw_mean_difference": "effect_estimate_E_minus_A"})

    direction_rows: list[dict[str, object]] = []
    for metric in METRICS:
        values = wide_differences.xs(metric["source_column"], level="metric")
        count = int((values < 0).sum()) if metric["direction"] == "negative" else int((values > 0).sum())
        direction_rows.append(
            {
                "metric": metric["source_column"],
                "direction_count": count,
                "direction": metric["direction"],
            }
        )
    directions = pd.DataFrame(direction_rows)
    summary = summary.merge(directions, on="metric", how="left", validate="one_to_one")

    source = pd.concat([long, summary], ignore_index=True, sort=False)
    ordered_columns = [
        "row_type",
        "panel",
        "participant",
        "mode_code",
        "metric",
        "metric_axis_label",
        "unit",
        "n_selected_trials",
        "participant_mean",
        "participant_difference_E_minus_A",
        "contrast",
        "difference_definition",
        "n_participants",
        "effect_estimate_E_minus_A",
        "ci95_low",
        "ci95_high",
        "direction_count",
        "direction",
    ]
    return source.reindex(columns=ordered_columns).sort_values(
        ["panel", "row_type", "participant", "mode_code"],
        kind="stable",
        na_position="last",
    )


def run_figure_qa(
    participant: pd.DataFrame,
    statistics: pd.DataFrame,
    trials: pd.DataFrame,
    source: pd.DataFrame,
) -> list[dict[str, object]]:
    checks: list[dict[str, object]] = []
    participants = sorted(participant["participant"].unique())
    _add_check(checks, "independent human participants", len(participants), 5, len(participants) == 5)
    _add_check(
        checks,
        "participant identities",
        participants,
        ["P01", "P02", "P03", "P04", "P05"],
        participants == ["P01", "P02", "P03", "P04", "P05"],
    )
    participant_keys = participant[["participant", "mode_code"]]
    _add_check(
        checks,
        "unique participant/configuration aggregates",
        int(participant_keys.drop_duplicates().shape[0]),
        20,
        participant_keys.drop_duplicates().shape[0] == len(participant) == 20,
    )
    ae = participant.loc[participant["mode_code"].isin(["A", "E"])]
    ae_counts = ae.groupby("mode_code")["participant"].nunique().to_dict()
    _add_check(checks, "A/E participant coverage", ae_counts, {"A": 5, "E": 5}, ae_counts == {"A": 5, "E": 5})

    trial_counts = trials.groupby(["participant", "mode_code"]).size()
    trial_count_values = sorted(set(int(value) for value in trial_counts.to_numpy()))
    _add_check(
        checks,
        "selected trials per participant/configuration",
        trial_count_values,
        [9],
        len(trial_counts) == 20 and trial_count_values == [9],
    )
    _add_check(
        checks,
        "selected trial total",
        int(len(trials)),
        180,
        len(trials) == 180 and trials["record_id"].nunique() == 180,
    )

    participant_rows = source.loc[source["row_type"].eq("participant_mean")]
    summary_rows = source.loc[source["row_type"].eq("contrast_summary")]
    _add_check(
        checks,
        "figure participant source rows",
        len(participant_rows),
        30,
        len(participant_rows) == 30,
    )
    _add_check(
        checks,
        "figure contrast summary rows",
        len(summary_rows),
        3,
        len(summary_rows) == 3,
    )

    for metric in METRICS:
        metric_name = metric["source_column"]
        summary_match = summary_rows.loc[summary_rows["metric"].eq(metric_name)]
        one_summary = len(summary_match) == 1
        _add_check(
            checks,
            f"{metric['panel']} exactly one frozen E-A summary",
            len(summary_match),
            1,
            one_summary,
        )
        if not one_summary:
            continue
        row = summary_match.iloc[0]
        n_participants = int(row["n_participants"])
        _add_check(
            checks,
            f"{metric['panel']} frozen n_participants",
            n_participants,
            5,
            n_participants == 5,
        )
        decimals = int(metric["effect_decimals"])
        observed = (
            round(float(row["effect_estimate_E_minus_A"]), decimals),
            round(float(row["ci95_low"]), decimals),
            round(float(row["ci95_high"]), decimals),
        )
        expected = (
            metric["expected_effect"],
            metric["expected_low"],
            metric["expected_high"],
        )
        _add_check(
            checks,
            f"{metric['panel']} frozen effect and 95% CI",
            observed,
            expected,
            observed == expected,
        )

        metric_participants = participant_rows.loc[
            participant_rows["metric"].eq(metric_name)
        ]
        differences = (
            metric_participants.drop_duplicates(["participant", "metric"])
            ["participant_difference_E_minus_A"]
            .to_numpy(dtype=float)
        )
        direction_count = int((differences < 0).sum()) if metric["direction"] == "negative" else int((differences > 0).sum())
        _add_check(
            checks,
            f"{metric['panel']} participant differences {metric['direction']}",
            direction_count,
            5,
            direction_count == 5,
        )
        computed_mean = float(np.mean(differences))
        frozen_mean = float(row["effect_estimate_E_minus_A"])
        _add_check(
            checks,
            f"{metric['panel']} participant mean difference matches frozen summary",
            computed_mean,
            frozen_mean,
            np.isclose(computed_mean, frozen_mean, rtol=0.0, atol=1e-12),
        )
    return checks


def write_qa_report(
    path: Path,
    checks: list[dict[str, object]],
    trial_counts: pd.Series,
    input_paths: list[Path],
) -> bool:
    passed = all(bool(item["passed"]) for item in checks)
    lines = [
        "Figure 4 QA — Participant-level exploratory E-A outcomes",
        f"STATUS: {'PASS' if passed else 'FAIL'}",
        "",
        "Semantic column mapping:",
        "- Task-start-to-contact time (s) -> participant_level_metrics.csv: approach_time_s",
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
            "Selected trials before participant aggregation:",
            trial_counts.rename("n_selected_trials").to_string(),
            "",
            "No trial-level inferential test is run by this figure script.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return passed


def _signed(value: float) -> str:
    return f"{value:+.4f}".replace("-", "−")


def plot_metric_panel(
    ax: plt.Axes,
    participant_rows: pd.DataFrame,
    summary_row: pd.Series,
    metric: dict[str, object],
) -> None:
    metric_rows = participant_rows.loc[
        participant_rows["metric"].eq(metric["source_column"])
    ]
    wide = (
        metric_rows.pivot(index="participant", columns="mode_code", values="participant_mean")
        .loc[:, ["A", "E"]]
        .sort_index()
    )
    differences = wide["E"] - wide["A"]
    participants = differences.index.tolist()
    y = np.arange(len(participants), dtype=float)
    mean_y = len(participants) + 0.65

    ax.axvline(0.0, color="#666666", linewidth=0.75, linestyle=(0, (3, 2)), zorder=1)
    ax.scatter(
        differences.to_numpy(dtype=float),
        y,
        s=31,
        marker="o",
        facecolor="white",
        edgecolor="#009E73",
        linewidth=1.0,
        zorder=3,
    )

    effect = float(summary_row["effect_estimate_E_minus_A"])
    low = float(summary_row["ci95_low"])
    high = float(summary_row["ci95_high"])
    ax.hlines(mean_y, low, high, color="#303030", linewidth=1.15, zorder=3)
    ax.plot([low, low], [mean_y - 0.12, mean_y + 0.12], color="#303030", linewidth=0.85)
    ax.plot([high, high], [mean_y - 0.12, mean_y + 0.12], color="#303030", linewidth=0.85)
    ax.scatter([effect], [mean_y], s=37, marker="D", facecolor="#009E73", edgecolor="white", linewidth=0.45, zorder=4)

    x_values = np.concatenate([differences.to_numpy(dtype=float), np.array([low, high, 0.0])])
    data_min, data_max = float(x_values.min()), float(x_values.max())
    span = max(data_max - data_min, 0.25)
    ax.set_xlim(data_min - 0.10 * span, data_max + 0.10 * span)
    ax.set_ylim(-1.35, mean_y + 0.7)
    ax.invert_yaxis()
    ax.set_yticks([*y, mean_y])
    if metric["panel"] == "A":
        ax.set_yticklabels([*participants, "Mean (95% CI)"])
    else:
        ax.set_yticklabels([])
        ax.tick_params(axis="y", length=0)
    ax.set_xlabel(f"E − A difference ({metric['unit']})")
    ax.set_title(str(metric["title"]), loc="left", pad=7)
    ax.grid(axis="x", color="#D9D9D9", linewidth=0.5, alpha=0.55)
    ax.set_axisbelow(True)
    panel_label(ax, str(metric["panel"]), x=-0.20, y=1.10)

    annotation = (
        f"Δ(E−A) = {_signed(effect)} {metric['unit']}\n"
        f"95% CI [{_signed(low)}, {_signed(high)}]"
    )
    ax.text(
        0.98,
        0.985,
        annotation,
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=6.2,
        linespacing=1.18,
        zorder=5,
    )


def create_figure(source: pd.DataFrame) -> plt.Figure:
    set_publication_style()
    fig, axes = plt.subplots(
        1,
        3,
        figsize=figure_size(FIGURE_WIDTH_MM, FIGURE_HEIGHT_MM),
    )
    fig.subplots_adjust(**LAYOUT)
    participant_rows = source.loc[source["row_type"].eq("participant_mean")]
    summary_rows = source.loc[source["row_type"].eq("contrast_summary")]
    for ax, metric in zip(axes, METRICS):
        summary = summary_rows.loc[
            summary_rows["metric"].eq(metric["source_column"])
        ].iloc[0]
        plot_metric_panel(ax, participant_rows, summary, metric)

    fig.text(
        0.5,
        0.045,
        "Exploratory paired differences; n=5 independent participants (9 selected trials per participant/configuration).\n"
        "E is a bundled assignment with heterogeneous realized visual exposure. Task start denotes system readiness, not first human movement.",
        ha="center",
        va="bottom",
        fontsize=6.6,
        fontstyle="italic",
        color="#303030",
    )
    return fig


def main() -> None:
    args = parse_root_args(__doc__ or "")
    project_root, clean_dir, figures_dir, source_dir = prepare_run(args, __file__)
    publication_root = project_root / "19_publication_figures"
    participant_path = clean_dir / "participant_level_metrics.csv"
    statistics_path = clean_dir / "statistics_summary.csv"
    trials_path = clean_dir / "trial_level_fidelity_metrics.csv"

    participant = read_clean_csv(clean_dir, participant_path.name, PARTICIPANT_COLUMNS)
    statistics = read_clean_csv(clean_dir, statistics_path.name, STATISTICS_COLUMNS)
    trials = read_clean_csv(clean_dir, trials_path.name, TRIAL_COLUMNS)
    print("SEMANTIC COLUMN MAPPING")
    print("  Task-start-to-contact time (s) -> participant_level_metrics.csv: approach_time_s")

    trial_counts = trials.groupby(["participant", "mode_code"]).size()
    source = build_source_data(participant, statistics, trial_counts)
    checks = run_figure_qa(participant, statistics, trials, source)
    qa_path = publication_root / "figure04_qa.txt"
    qa_passed = write_qa_report(
        qa_path,
        checks,
        trial_counts,
        [participant_path, statistics_path, trials_path],
    )
    if not qa_passed:
        print("FIGURE 4 QA FAILED — STOPPING BEFORE SOURCE-DATA OR FIGURE GENERATION", file=sys.stderr)
        for item in checks:
            if not item["passed"]:
                print(
                    f"  {item['name']}: actual={item['actual']!r}; expected={item['expected']!r}",
                    file=sys.stderr,
                )
        raise SystemExit(1)
    print(f"FIGURE 4 QA: PASS ({len(checks)}/{len(checks)} checks)")
    print("Selected trials per participant/configuration before aggregation:")
    print(trial_counts.rename("n_selected_trials").to_string())

    source_path = write_source_csv(source, source_dir / "figure04_source_data.csv")
    fig = create_figure(source)
    outputs = save_publication_figure(fig, figures_dir, STEM, args.dpi)
    manifest_path = record_manifest(
        publication_root,
        project_root,
        STEM,
        Path(__file__),
        [participant_path, statistics_path, trials_path],
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
