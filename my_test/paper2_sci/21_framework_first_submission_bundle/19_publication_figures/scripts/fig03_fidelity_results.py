#!/usr/bin/env python3
"""Generate Figure 3: trial-level realized-intervention fidelity."""

from __future__ import annotations

from pathlib import Path
import sys

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import PercentFormatter
import numpy as np
import pandas as pd

from figure_common import (
    classify_exposure,
    parse_root_args,
    prepare_run,
    read_clean_csv,
    record_manifest,
    write_source_csv,
)
from figure_style import (
    MODE_COLORS,
    figure_size,
    panel_label,
    save_publication_figure,
    set_publication_style,
)


STEM = "Fig03_realized_intervention_fidelity"
FIGURE_WIDTH_MM = 190.0
FIGURE_HEIGHT_MM = 140.0
LAYOUT = {
    "left": 0.185,
    "right": 0.985,
    "bottom": 0.105,
    "top": 0.855,
    "wspace": 0.27,
    "hspace": 0.42,
    "height_ratios": (1.62, 0.78),
}
EXPOSURE_LEVELS = ("Full", "Partial", "Zero")
EXPOSURE_STYLE = {
    "Full": {"color": "#5F8F78", "hatch": ""},
    "Partial": {"color": "#D9B45B", "hatch": "///"},
    "Zero": {"color": "#F2F2F2", "hatch": "xx"},
}
CONTACT_COLOR = "#3F3F3F"
SECONDARY_COLOR = "#6A6A6A"


FIDELITY_COLUMNS = [
    "record_id",
    "trial_id",
    "participant",
    "material",
    "block",
    "mode_code",
    "task_start_system_s",
    "force_baseline_ready_system_s",
    "contact_system_s",
    "adaptation_activation_system_s",
    "executable_logic_compliance",
    "pre_contact_activation",
    "nominal_activation_timing_compliance",
    "contact_to_adaptation_latency_s",
    "activation_timing_error_s",
]
EXPOSURE_COLUMNS = [
    "record_id",
    "trial_id",
    "participant",
    "material",
    "block",
    "mode_code",
    "exposure_fraction",
    "vision_configuration_exposure_fraction",
    "force_adaptation_exposure_fraction",
    "provenance_valid",
]
KEY_COLUMNS = ["record_id", "trial_id", "participant", "material", "block", "mode_code"]


def _format_value(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.10g}"
    return str(value)


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


def _exposure_counts(frame: pd.DataFrame, class_column: str) -> dict[str, int]:
    return {level: int(frame[class_column].eq(level).sum()) for level in EXPOSURE_LEVELS}


def build_figure_source(fidelity: pd.DataFrame, exposure: pd.DataFrame) -> pd.DataFrame:
    """Create one auditable, trial-identity-preserving source table for all panels."""
    source = fidelity[FIDELITY_COLUMNS].merge(
        exposure[EXPOSURE_COLUMNS],
        on=KEY_COLUMNS,
        how="inner",
        validate="one_to_one",
    )
    source["task_start_relative_contact_s"] = (
        source["task_start_system_s"] - source["contact_system_s"]
    )
    source["baseline_ready_relative_contact_s"] = (
        source["force_baseline_ready_system_s"] - source["contact_system_s"]
    )
    source["activation_relative_contact_s"] = (
        source["adaptation_activation_system_s"] - source["contact_system_s"]
    )

    source["G_trial_rank"] = pd.Series(pd.NA, index=source.index, dtype="Int64")
    source["F_trial_rank"] = pd.Series(pd.NA, index=source.index, dtype="Int64")
    for mode in ("G", "F"):
        ordered_index = (
            source.loc[source["mode_code"].eq(mode)]
            .sort_values(
                ["contact_to_adaptation_latency_s", "record_id"],
                kind="stable",
            )
            .index
        )
        source.loc[ordered_index, f"{mode}_trial_rank"] = np.arange(1, len(ordered_index) + 1)

    for column in (
        "E_vision_exposure_class",
        "F_vision_exposure_class",
        "F_adaptation_exposure_class",
        "F_joint_exposure_class",
    ):
        source[column] = pd.Series(pd.NA, index=source.index, dtype="object")

    e_mask = source["mode_code"].eq("E")
    f_mask = source["mode_code"].eq("F")
    source.loc[e_mask, "E_vision_exposure_class"] = classify_exposure(
        source.loc[e_mask, "vision_configuration_exposure_fraction"]
    )
    source.loc[f_mask, "F_vision_exposure_class"] = classify_exposure(
        source.loc[f_mask, "vision_configuration_exposure_fraction"]
    )
    source.loc[f_mask, "F_adaptation_exposure_class"] = classify_exposure(
        source.loc[f_mask, "force_adaptation_exposure_fraction"]
    )
    source.loc[f_mask, "F_joint_exposure_class"] = classify_exposure(
        source.loc[f_mask, "exposure_fraction"]
    )

    ordered_columns = [
        *KEY_COLUMNS,
        "G_trial_rank",
        "F_trial_rank",
        "task_start_system_s",
        "force_baseline_ready_system_s",
        "contact_system_s",
        "adaptation_activation_system_s",
        "task_start_relative_contact_s",
        "baseline_ready_relative_contact_s",
        "activation_relative_contact_s",
        "contact_to_adaptation_latency_s",
        "activation_timing_error_s",
        "executable_logic_compliance",
        "pre_contact_activation",
        "nominal_activation_timing_compliance",
        "exposure_fraction",
        "vision_configuration_exposure_fraction",
        "force_adaptation_exposure_fraction",
        "E_vision_exposure_class",
        "F_vision_exposure_class",
        "F_adaptation_exposure_class",
        "F_joint_exposure_class",
        "provenance_valid",
    ]
    return source[ordered_columns].sort_values(
        ["mode_code", "participant", "material", "block", "record_id"],
        kind="stable",
    )


def figure_specific_qa(
    fidelity: pd.DataFrame,
    exposure: pd.DataFrame,
    source: pd.DataFrame,
) -> tuple[list[dict[str, object]], dict[str, pd.DataFrame]]:
    checks: list[dict[str, object]] = []
    expected_modes = {"A": 45, "G": 45, "E": 45, "F": 45}
    fidelity_modes = fidelity.groupby("mode_code", sort=False).size().to_dict()
    exposure_modes = exposure.groupby("mode_code", sort=False).size().to_dict()
    _add_check(checks, "trial-level fidelity rows", len(fidelity), 180, len(fidelity) == 180)
    _add_check(checks, "outcome-window exposure rows", len(exposure), 180, len(exposure) == 180)
    _add_check(
        checks,
        "A/G/E/F counts in fidelity input",
        fidelity_modes,
        expected_modes,
        fidelity_modes == expected_modes,
    )
    _add_check(
        checks,
        "A/G/E/F counts in exposure input",
        exposure_modes,
        expected_modes,
        exposure_modes == expected_modes,
    )
    _add_check(
        checks,
        "unique record_id in both inputs",
        (fidelity["record_id"].nunique(), exposure["record_id"].nunique()),
        (180, 180),
        fidelity["record_id"].nunique() == exposure["record_id"].nunique() == 180,
    )
    same_record_ids = set(fidelity["record_id"]) == set(exposure["record_id"])
    _add_check(checks, "exact record_id linkage across inputs", same_record_ids, True, same_record_ids)
    _add_check(
        checks,
        "independent human participants",
        source["participant"].nunique(),
        5,
        source["participant"].nunique() == 5,
    )
    _add_check(
        checks,
        "exposure provenance valid",
        int(exposure["provenance_valid"].sum()),
        180,
        int(exposure["provenance_valid"].sum()) == 180,
    )

    g = source.loc[source["mode_code"].eq("G")].copy()
    f = source.loc[source["mode_code"].eq("F")].copy()
    _add_check(
        checks,
        "G executable raw-force rule compliant",
        int(g["executable_logic_compliance"].sum()),
        45,
        int(g["executable_logic_compliance"].sum()) == 45,
    )
    _add_check(
        checks,
        "G pre-contact activation",
        int(g["pre_contact_activation"].sum()),
        43,
        int(g["pre_contact_activation"].sum()) == 43,
    )
    g_median = float(g["contact_to_adaptation_latency_s"].median())
    _add_check(
        checks,
        "G median contact-to-activation (s)",
        g_median,
        -1.214,
        round(g_median, 3) == -1.214,
    )
    _add_check(
        checks,
        "F nominal +0.20-s satisfied",
        int(f["nominal_activation_timing_compliance"].sum()),
        3,
        int(f["nominal_activation_timing_compliance"].sum()) == 3,
    )
    f_median = float(f["contact_to_adaptation_latency_s"].median())
    f_error = float(f["activation_timing_error_s"].median())
    _add_check(
        checks,
        "F median activation (s)",
        f_median,
        0.0533,
        round(f_median, 4) == 0.0533,
    )
    _add_check(
        checks,
        "F median timing error (s)",
        f_error,
        -0.1467,
        round(f_error, 4) == -0.1467,
    )

    timestamp_match = np.allclose(
        source.loc[source["mode_code"].isin(["G", "F"]), "activation_relative_contact_s"],
        source.loc[source["mode_code"].isin(["G", "F"]), "contact_to_adaptation_latency_s"],
        rtol=0.0,
        atol=1e-10,
    )
    _add_check(
        checks,
        "timestamp-derived activation latency matches clean metric",
        timestamp_match,
        True,
        timestamp_match,
    )
    required_timing = [
        "contact_system_s",
        "adaptation_activation_system_s",
        "contact_to_adaptation_latency_s",
    ]
    g_required = [*required_timing, "task_start_system_s", "force_baseline_ready_system_s"]
    g_missing = int(g[g_required].isna().sum().sum())
    f_missing = int(f[required_timing].isna().sum().sum())
    _add_check(checks, "G required timing values missing", g_missing, 0, g_missing == 0)
    _add_check(checks, "F required timing values missing", f_missing, 0, f_missing == 0)
    _add_check(
        checks,
        "G deterministic ranks 1-45",
        sorted(g["G_trial_rank"].dropna().astype(int).tolist()),
        list(range(1, 46)),
        sorted(g["G_trial_rank"].dropna().astype(int).tolist()) == list(range(1, 46)),
    )
    _add_check(
        checks,
        "F deterministic ranks 1-45",
        sorted(f["F_trial_rank"].dropna().astype(int).tolist()),
        list(range(1, 46)),
        sorted(f["F_trial_rank"].dropna().astype(int).tolist()) == list(range(1, 46)),
    )

    exposure_specs = [
        ("E vision exposure", "E", "E_vision_exposure_class", {"Full": 39, "Partial": 2, "Zero": 4}),
        ("F vision exposure", "F", "F_vision_exposure_class", {"Full": 42, "Partial": 0, "Zero": 3}),
        ("F adaptation exposure", "F", "F_adaptation_exposure_class", {"Full": 35, "Partial": 7, "Zero": 3}),
        ("F joint exposure", "F", "F_joint_exposure_class", {"Full": 35, "Partial": 7, "Zero": 3}),
    ]
    for name, mode, column, expected in exposure_specs:
        actual = _exposure_counts(source.loc[source["mode_code"].eq(mode)], column)
        _add_check(checks, name, actual, expected, actual == expected)

    exceptions = {
        "G post-contact exceptions": g.loc[
            g["pre_contact_activation"].eq(0),
            ["record_id", "trial_id", "contact_to_adaptation_latency_s"],
        ].sort_values("record_id", kind="stable"),
        "F +0.20-s compliant cases": f.loc[
            f["nominal_activation_timing_compliance"].eq(1),
            ["record_id", "trial_id", "contact_to_adaptation_latency_s", "activation_timing_error_s"],
        ].sort_values("record_id", kind="stable"),
        "E vision zero-exposure cases": source.loc[
            source["E_vision_exposure_class"].eq("Zero"),
            ["record_id", "trial_id", "vision_configuration_exposure_fraction"],
        ].sort_values("record_id", kind="stable"),
        "F vision zero-exposure cases": source.loc[
            source["F_vision_exposure_class"].eq("Zero"),
            ["record_id", "trial_id", "vision_configuration_exposure_fraction"],
        ].sort_values("record_id", kind="stable"),
        "F adaptation zero-exposure cases": source.loc[
            source["F_adaptation_exposure_class"].eq("Zero"),
            ["record_id", "trial_id", "force_adaptation_exposure_fraction"],
        ].sort_values("record_id", kind="stable"),
        "F joint zero-exposure cases": source.loc[
            source["F_joint_exposure_class"].eq("Zero"),
            ["record_id", "trial_id", "exposure_fraction"],
        ].sort_values("record_id", kind="stable"),
    }
    return checks, exceptions


def write_qa_report(
    path: Path,
    checks: list[dict[str, object]],
    exceptions: dict[str, pd.DataFrame],
    inputs: list[Path],
) -> bool:
    passed = all(bool(item["passed"]) for item in checks)
    lines = [
        "Figure 3 QA — Trial-level realized-intervention fidelity",
        f"STATUS: {'PASS' if passed else 'FAIL'}",
        "",
        "Inputs:",
        *(f"- {input_path}" for input_path in inputs),
        "",
        "Frozen and structural checks:",
    ]
    for item in checks:
        status = "PASS" if item["passed"] else "FAIL"
        lines.append(
            f"[{status}] {item['name']} | actual={_format_value(item['actual'])} "
            f"| expected={_format_value(item['expected'])}"
        )
    lines.extend(["", "Exact reproducibility case lists:"])
    for heading, frame in exceptions.items():
        lines.extend(["", heading, "-" * len(heading)])
        lines.append(frame.to_string(index=False) if len(frame) else "(none)")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return passed


def print_exception_trials(exceptions: dict[str, pd.DataFrame]) -> None:
    print("\nEXACT TRIAL LISTS FOR REPRODUCIBILITY")
    for heading, frame in exceptions.items():
        print(f"\n{heading} (n={len(frame)})")
        print(frame.to_string(index=False) if len(frame) else "(none)")


def style_timing_axis(ax: plt.Axes) -> None:
    ax.set_ylim(45.8, 0.2)
    ax.set_yticks([1, 5, 10, 15, 20, 25, 30, 35, 40, 45])
    ax.set_ylabel("Trial rank")
    ax.set_xlabel("Time relative to contact (s)")
    ax.axvline(0.0, color=CONTACT_COLOR, linewidth=0.85, linestyle="-", zorder=1)
    ax.tick_params(direction="out")


def plot_g_panel(ax: plt.Axes, source: pd.DataFrame) -> None:
    g = source.loc[source["mode_code"].eq("G")].sort_values("G_trial_rank", kind="stable")
    rank = g["G_trial_rank"].astype(int).to_numpy()
    style_timing_axis(ax)
    ax.plot(
        g["task_start_relative_contact_s"],
        rank,
        linestyle="none",
        marker="|",
        markersize=5.3,
        markeredgewidth=0.85,
        color=SECONDARY_COLOR,
        zorder=2,
    )
    ax.plot(
        g["baseline_ready_relative_contact_s"],
        rank,
        linestyle="none",
        marker="^",
        markersize=3.6,
        markerfacecolor="white",
        markeredgecolor=SECONDARY_COLOR,
        markeredgewidth=0.7,
        zorder=3,
    )
    ax.scatter(
        g["activation_relative_contact_s"],
        rank,
        s=18,
        marker="o",
        facecolor=MODE_COLORS["G"],
        edgecolor="white",
        linewidth=0.35,
        zorder=4,
    )
    values = g[
        [
            "task_start_relative_contact_s",
            "baseline_ready_relative_contact_s",
            "activation_relative_contact_s",
        ]
    ].to_numpy(dtype=float)
    lower = np.floor(np.nanmin(values) * 2.0) / 2.0 - 0.10
    ax.set_xlim(lower, 3.08)
    ax.set_title("G: raw-force-rule activation", loc="left", pad=7)
    panel_label(ax, "A", x=-0.13, y=1.08)
    annotation = (
        "Executable raw-force\n"
        "rule compliant: 45/45\n"
        "Pre-contact activation: 43/45\n"
        "Median contact-to-\n"
        "activation: −1.214 s\n"
        "Coded rule executed;\n"
        "intervention was not\n"
        "purely post-contact."
    )
    ax.text(
        0.18,
        1.0,
        annotation,
        ha="left",
        va="top",
        fontsize=7.0,
        linespacing=1.25,
        bbox={"boxstyle": "round,pad=0.28", "facecolor": "#F4F8FA", "edgecolor": "#C8D7DF", "linewidth": 0.55},
        zorder=6,
    )


def plot_f_panel(ax: plt.Axes, source: pd.DataFrame) -> None:
    f = source.loc[source["mode_code"].eq("F")].sort_values("F_trial_rank", kind="stable")
    rank = f["F_trial_rank"].astype(int).to_numpy()
    style_timing_axis(ax)
    ax.axvline(
        0.20,
        color=MODE_COLORS["F"],
        linewidth=0.95,
        linestyle=(0, (4.0, 2.0)),
        zorder=1,
    )
    ax.scatter(
        f["activation_relative_contact_s"],
        rank,
        s=20,
        marker="D",
        facecolor=MODE_COLORS["F"],
        edgecolor="white",
        linewidth=0.35,
        zorder=4,
    )
    upper = np.ceil(float(f["activation_relative_contact_s"].max()) * 2.0) / 2.0 + 0.08
    ax.set_xlim(-0.08, upper)
    ax.set_title("F: nominally gated activation", loc="left", pad=7)
    panel_label(ax, "B", x=-0.13, y=1.08)
    annotation = (
        "Nominal +0.20-s satisfied: 3/45\n"
        "Median activation: +0.0533 s\n"
        "Median timing error: −0.1467 s"
    )
    ax.text(
        0.98,
        0.98,
        annotation,
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=7.0,
        linespacing=1.25,
        bbox={"boxstyle": "round,pad=0.28", "facecolor": "#FCF7F2", "edgecolor": "#E1CDBF", "linewidth": 0.55},
        zorder=6,
    )


def plot_exposure_panel(ax: plt.Axes, source: pd.DataFrame) -> None:
    specs = [
        ("E vision", "E", "E_vision_exposure_class"),
        ("F vision", "F", "F_vision_exposure_class"),
        ("F adaptation", "F", "F_adaptation_exposure_class"),
        ("F joint vision + adaptation", "F", "F_joint_exposure_class"),
    ]
    counts_by_row = [
        _exposure_counts(source.loc[source["mode_code"].eq(mode)], class_column)
        for _, mode, class_column in specs
    ]
    y = np.arange(len(specs), dtype=float)
    left = np.zeros(len(specs), dtype=float)
    for level in EXPOSURE_LEVELS:
        counts = np.array([row[level] for row in counts_by_row], dtype=float)
        widths = counts / 45.0
        style = EXPOSURE_STYLE[level]
        bars = ax.barh(
            y,
            widths,
            left=left,
            height=0.58,
            color=style["color"],
            edgecolor="#4D4D4D",
            linewidth=0.55,
            hatch=style["hatch"],
            label=f"{level} exposure",
            zorder=2,
        )
        for bar, count in zip(bars, counts.astype(int)):
            if count == 0:
                continue
            text_color = "white" if level == "Full" else "#242424"
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                bar.get_y() + bar.get_height() / 2.0,
                str(count),
                ha="center",
                va="center",
                fontsize=7.2,
                fontweight="bold",
                color=text_color,
                zorder=4,
            )
        left += widths

    for index, counts in enumerate(counts_by_row):
        ax.text(
            1.025,
            index,
            f"{counts['Full']} / {counts['Partial']} / {counts['Zero']}",
            ha="left",
            va="center",
            fontsize=7.2,
            color="#303030",
        )
    ax.text(
        1.025,
        -0.72,
        "n: Full / Partial / Zero",
        ha="left",
        va="bottom",
        fontsize=7.0,
        fontweight="bold",
        color="#303030",
    )
    ax.set_yticks(y, [label for label, _, _ in specs])
    ax.set_ylim(3.55, -1.15)
    ax.set_xlim(0.0, 1.18)
    ax.set_xticks([0.0, 0.25, 0.50, 0.75, 1.0])
    ax.xaxis.set_major_formatter(PercentFormatter(xmax=1.0, decimals=0))
    ax.set_xlabel("Outcome-window exposure (% of 45 trials)")
    ax.set_title("Outcome-window exposure: contact +0.20 to +1.00 s", loc="left", pad=8)
    ax.legend(
        loc="center",
        bbox_to_anchor=(0.64, -0.77),
        bbox_transform=ax.transData,
        ncol=3,
        handlelength=2.4,
        handleheight=1.0,
        columnspacing=1.3,
    )
    panel_label(ax, "C", x=-0.065, y=1.16)


def create_figure(source: pd.DataFrame) -> plt.Figure:
    set_publication_style()
    fig = plt.figure(figsize=figure_size(FIGURE_WIDTH_MM, FIGURE_HEIGHT_MM))
    grid = fig.add_gridspec(
        2,
        2,
        left=LAYOUT["left"],
        right=LAYOUT["right"],
        bottom=LAYOUT["bottom"],
        top=LAYOUT["top"],
        wspace=LAYOUT["wspace"],
        hspace=LAYOUT["hspace"],
        height_ratios=LAYOUT["height_ratios"],
    )
    ax_g = fig.add_subplot(grid[0, 0])
    ax_f = fig.add_subplot(grid[0, 1])
    ax_exposure = fig.add_subplot(grid[1, :])
    plot_g_panel(ax_g, source)
    plot_f_panel(ax_f, source)
    plot_exposure_panel(ax_exposure, source)

    timing_handles = [
        Line2D([], [], linestyle="none", marker="o", markersize=4.5, markerfacecolor=MODE_COLORS["G"], markeredgecolor="white", label="G first activation"),
        Line2D([], [], linestyle="none", marker="D", markersize=4.2, markerfacecolor=MODE_COLORS["F"], markeredgecolor="white", label="F first activation"),
        Line2D([], [], linestyle="none", marker="|", markersize=6.0, markeredgewidth=0.9, color=SECONDARY_COLOR, label="task_start"),
        Line2D([], [], linestyle="none", marker="^", markersize=4.2, markerfacecolor="white", markeredgecolor=SECONDARY_COLOR, label="baseline_ready"),
        Line2D([], [], color=CONTACT_COLOR, linewidth=0.85, linestyle="-", label="contact = 0 s"),
        Line2D([], [], color=MODE_COLORS["F"], linewidth=0.95, linestyle=(0, (4.0, 2.0)), label="nominal F gate = +0.20 s"),
    ]
    fig.legend(
        handles=timing_handles,
        loc="upper center",
        bbox_to_anchor=(0.52, 0.972),
        ncol=6,
        handlelength=2.1,
        columnspacing=1.2,
        handletextpad=0.45,
        borderaxespad=0.0,
    )
    fig.text(
        0.5,
        0.025,
        "Trial-level displays characterize intervention fidelity; human outcome inference uses participant n=5.",
        ha="center",
        va="bottom",
        fontsize=7.4,
        fontstyle="italic",
        color="#303030",
    )
    return fig


def main() -> None:
    args = parse_root_args(__doc__ or "")
    project_root, clean_dir, figures_dir, source_dir = prepare_run(args, __file__)
    publication_root = project_root / "19_publication_figures"
    fidelity_path = clean_dir / "trial_level_fidelity_metrics.csv"
    exposure_path = clean_dir / "outcome_window_exposure.csv"

    fidelity = read_clean_csv(clean_dir, fidelity_path.name, FIDELITY_COLUMNS)
    exposure = read_clean_csv(clean_dir, exposure_path.name, EXPOSURE_COLUMNS)
    source = build_figure_source(fidelity, exposure)
    checks, exceptions = figure_specific_qa(fidelity, exposure, source)
    qa_path = publication_root / "figure03_qa.txt"
    qa_passed = write_qa_report(
        qa_path,
        checks,
        exceptions,
        [fidelity_path, exposure_path],
    )
    print_exception_trials(exceptions)
    if not qa_passed:
        print("\nFIGURE 3 QA FAILED — STOPPING BEFORE SOURCE-DATA OR FIGURE GENERATION", file=sys.stderr)
        for item in checks:
            if not item["passed"]:
                print(
                    f"  {item['name']}: actual={item['actual']!r}; expected={item['expected']!r}",
                    file=sys.stderr,
                )
        raise SystemExit(1)
    print(f"\nFIGURE 3 QA: PASS ({len(checks)}/{len(checks)} checks)")

    source_path = write_source_csv(source, source_dir / "figure03_source_data.csv")
    fig = create_figure(source)
    outputs = save_publication_figure(fig, figures_dir, STEM, args.dpi)
    record_manifest(
        publication_root,
        project_root,
        STEM,
        Path(__file__),
        [fidelity_path, exposure_path],
        source_path,
        [*outputs, qa_path],
    )
    print(f"Generated {STEM}")
    for output in outputs:
        print(f"  {output}")
    print(f"  {source_path}")
    print(f"  {qa_path}")


if __name__ == "__main__":
    main()
