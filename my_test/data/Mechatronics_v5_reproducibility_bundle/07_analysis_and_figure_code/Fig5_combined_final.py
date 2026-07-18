from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Iterable

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

# -----------------------------
# Global configuration
# -----------------------------
MODE_ORDER = ["A", "B", "C", "D", "E"]
OPERATORS = ["P01", "P02", "P03"]
OPERATOR_MARKERS: Dict[str, str] = {"P01": "o", "P02": "^", "P03": "s"}
OPERATOR_OFFSETS: Dict[str, float] = {"P01": -0.11, "P02": 0.00, "P03": 0.11}

BASE_EDGE = "#5B8DB8"
BASE_FILL = "#DCEAF5"
METHOD_EDGE = "#6A3D9A"
METHOD_FILL = "#D9C7F0"
MEDIAN_COLOR = "#333333"
WHISKER_COLOR = "#5A5A5A"
GRID_COLOR = "#B7B7B7"

SUCCESS_COUNTS = {"A": 22, "B": 21, "C": 26, "D": 24, "E": 24}
N_ATTEMPTS_PER_MODE = 27

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "axes.unicode_minus": False,
    }
)


def parse_args() -> argparse.Namespace:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Generate the final four-panel Fig. 5 for the Mechatronics manuscript."
    )
    parser.add_argument(
        "--trial-file",
        type=Path,
        default=here / "all_trials_135.csv",
        help="CSV containing task-level data (default: all_trials_135.csv beside this script).",
    )
    parser.add_argument(
        "--nasa-file",
        type=Path,
        default=here / "nasa.md",
        help="CSV-formatted NASA-TLX file (default: nasa.md beside this script).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=here / "outputs",
        help="Directory for PNG/PDF/SVG outputs.",
    )
    parser.add_argument(
        "--dpi", type=int, default=600, help="PNG resolution (default: 600 dpi)."
    )
    return parser.parse_args()


def validate_trial_data(df: pd.DataFrame) -> None:
    required = {"operator", "mode", "duration_s", "traj_length_m"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Trial file is missing required columns: {sorted(missing)}")

    mode_counts = df["mode"].value_counts().reindex(MODE_ORDER, fill_value=0)
    if not (mode_counts == N_ATTEMPTS_PER_MODE).all():
        raise ValueError(
            "Expected 27 task observations per mode; found "
            + ", ".join(f"{m}={int(mode_counts[m])}" for m in MODE_ORDER)
        )

    unknown_ops = sorted(set(df["operator"].dropna()) - set(OPERATORS))
    if unknown_ops:
        raise ValueError(f"Unexpected operator labels: {unknown_ops}")


def load_nasa_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {
        "operator",
        "mode",
        "mental_demand",
        "physical_demand",
        "temporal_demand",
        "performance",
        "effort",
        "frustration",
    }
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"NASA-TLX file is missing required columns: {sorted(missing)}")

    op_map = {1: "P01", 2: "P02", 3: "P03", "1": "P01", "2": "P02", "3": "P03"}
    df = df.copy()
    df["operator_id"] = df["operator"].map(op_map)
    if df["operator_id"].isna().any():
        bad = sorted(df.loc[df["operator_id"].isna(), "operator"].astype(str).unique())
        raise ValueError(f"Unexpected NASA-TLX operator values: {bad}")

    dimensions = [
        "mental_demand",
        "physical_demand",
        "temporal_demand",
        "performance",
        "effort",
        "frustration",
    ]
    df["Raw_NASA_TLX"] = df[dimensions].mean(axis=1)

    mode_counts = df["mode"].value_counts().reindex(MODE_ORDER, fill_value=0)
    if not (mode_counts == 9).all():
        raise ValueError(
            "Expected 9 questionnaire units per mode; found "
            + ", ".join(f"{m}={int(mode_counts[m])}" for m in MODE_ORDER)
        )
    return df


def mode_edge(mode: str) -> str:
    return METHOD_EDGE if mode == "C" else BASE_EDGE


def mode_fill(mode: str) -> str:
    return METHOD_FILL if mode == "C" else BASE_FILL


def format_axes(ax: plt.Axes) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(0.8)
    ax.spines["bottom"].set_linewidth(0.8)
    ax.tick_params(axis="both", labelsize=8, width=0.8, length=3.0)
    ax.grid(axis="y", linestyle="--", linewidth=0.5, color=GRID_COLOR, alpha=0.35)
    ax.set_axisbelow(True)


def add_panel_tag(ax: plt.Axes, tag: str) -> None:
    ax.text(
        0.015,
        0.985,
        tag,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=10.5,
        fontweight="bold",
    )


def draw_box_scatter(
    ax: plt.Axes,
    data: pd.DataFrame,
    column: str,
    ylabel: str,
    panel_tag: str,
    ylim: tuple[float, float],
    yticks: Iterable[float],
    seed: int,
) -> None:
    values = [data.loc[data["mode"] == m, column].dropna().to_numpy() for m in MODE_ORDER]
    bp = ax.boxplot(
        values,
        positions=np.arange(1, 6),
        widths=0.46,
        patch_artist=True,
        showfliers=False,
        medianprops={"color": MEDIAN_COLOR, "linewidth": 1.35},
        whiskerprops={"color": WHISKER_COLOR, "linewidth": 0.8},
        capprops={"color": WHISKER_COLOR, "linewidth": 0.8},
        boxprops={"linewidth": 0.9},
    )

    for mode, patch in zip(MODE_ORDER, bp["boxes"]):
        patch.set_facecolor(mode_fill(mode))
        patch.set_edgecolor(mode_edge(mode))
        patch.set_alpha(0.16)

    rng = np.random.default_rng(seed)
    for mode_x, mode in enumerate(MODE_ORDER, start=1):
        subset = data.loc[data["mode"] == mode].dropna(subset=[column])
        for operator in OPERATORS:
            y = subset.loc[subset["operator"] == operator, column].to_numpy()
            if y.size == 0:
                continue
            x = mode_x + OPERATOR_OFFSETS[operator] + rng.uniform(-0.012, 0.012, size=y.size)
            ax.scatter(
                x,
                y,
                marker=OPERATOR_MARKERS[operator],
                s=13,
                facecolors="white",
                edgecolors=mode_edge(mode),
                linewidths=0.65,
                alpha=0.68,
                zorder=3,
                clip_on=True,
            )

    ax.set_xlim(0.55, 5.45)
    ax.set_xticks(np.arange(1, 6))
    ax.set_xticklabels(MODE_ORDER)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.set_ylim(*ylim)
    ax.set_yticks(list(yticks))
    format_axes(ax)
    add_panel_tag(ax, panel_tag)


def add_completion_time_significance(ax: plt.Axes) -> None:
    """Show the four prespecified Holm-adjusted comparisons with mode C."""
    comparisons = [
        (1, 3, 25.95),  # A vs C
        (2, 3, 26.25),  # B vs C
        (3, 4, 26.55),  # C vs D
        (3, 5, 26.85),  # C vs E
    ]
    for x1, x2, y in comparisons:
        h = 0.10
        ax.plot([x1, x1, x2, x2], [y, y + h, y + h, y], color="#4A4A4A", linewidth=0.75, clip_on=False)
        ax.text(
            (x1 + x2) / 2,
            y + h + 0.025,
            "**",
            ha="center",
            va="bottom",
            fontsize=6.0,
            color="#333333",
        )


def draw_nasa_panel(ax: plt.Axes, nasa: pd.DataFrame) -> None:
    op_means = (
        nasa.groupby(["operator_id", "mode"], as_index=False)["Raw_NASA_TLX"].mean()
    )

    # Operator-level lines: the x-position includes the same fixed operator offset used in panels (a) and (b).
    for operator in OPERATORS:
        rows = (
            op_means.loc[op_means["operator_id"] == operator]
            .set_index("mode")
            .reindex(MODE_ORDER)
        )
        xs = np.arange(1, 6, dtype=float) + OPERATOR_OFFSETS[operator]
        ax.plot(
            xs,
            rows["Raw_NASA_TLX"].to_numpy(),
            color="#A8A8A8",
            linewidth=0.75,
            alpha=0.60,
            zorder=1,
        )

    # Strategy-level units: three small observations for each operator and mode.
    strategy_offsets = np.array([-0.024, 0.0, 0.024])
    for mode_x, mode in enumerate(MODE_ORDER, start=1):
        subset = nasa.loc[nasa["mode"] == mode]
        for operator in OPERATORS:
            y = subset.loc[subset["operator_id"] == operator, "Raw_NASA_TLX"].to_numpy()
            if y.size == 0:
                continue
            offsets = strategy_offsets[: y.size]
            x = mode_x + OPERATOR_OFFSETS[operator] + offsets
            ax.scatter(
                x,
                y,
                marker=OPERATOR_MARKERS[operator],
                s=10,
                facecolors=mode_fill(mode),
                edgecolors=mode_edge(mode),
                linewidths=0.40,
                alpha=0.38,
                zorder=2,
            )

    # Operator-level means: larger open markers.
    for mode_x, mode in enumerate(MODE_ORDER, start=1):
        for operator in OPERATORS:
            row = op_means.loc[
                (op_means["operator_id"] == operator) & (op_means["mode"] == mode),
                "Raw_NASA_TLX",
            ]
            if row.empty:
                continue
            ax.scatter(
                mode_x + OPERATOR_OFFSETS[operator],
                float(row.iloc[0]),
                marker=OPERATOR_MARKERS[operator],
                s=30,
                facecolors="white",
                edgecolors=mode_edge(mode),
                linewidths=0.95,
                zorder=4,
            )

    ax.set_xlim(0.55, 5.45)
    ax.set_xticks(np.arange(1, 6))
    ax.set_xticklabels(MODE_ORDER)
    ax.set_ylabel("Raw NASA-TLX score", fontsize=9)
    ax.set_ylim(35, 80)
    ax.set_yticks(np.arange(35, 81, 5))
    format_axes(ax)
    add_panel_tag(ax, "(c)")


def draw_success_panel(ax: plt.Axes) -> None:
    xs = np.arange(1, 6)
    rates = np.array([SUCCESS_COUNTS[m] / N_ATTEMPTS_PER_MODE * 100 for m in MODE_ORDER])

    for x, mode, rate in zip(xs, MODE_ORDER, rates):
        edge = mode_edge(mode)
        face = METHOD_FILL if mode == "C" else "white"
        ax.vlines(x, 0, rate, color=edge, linewidth=1.65, zorder=1)
        ax.scatter(
            x,
            rate,
            s=100,
            facecolors=face,
            edgecolors=edge,
            linewidths=1.05,
            zorder=3,
        )
        ax.text(
            x,
            rate + 2.5,
            f"{SUCCESS_COUNTS[mode]}/{N_ATTEMPTS_PER_MODE}\n({rate:.1f}%)",
            ha="center",
            va="bottom",
            fontsize=7.4,
            linespacing=0.95,
        )

    ax.set_xlim(0.55, 5.45)
    ax.set_xticks(xs)
    ax.set_xticklabels(MODE_ORDER)
    ax.set_ylabel("Task success rate (%)", fontsize=9)
    ax.set_ylim(0, 112)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    format_axes(ax)
    add_panel_tag(ax, "(d)")


def operator_legend_handles() -> list[Line2D]:
    return [
        Line2D(
            [0],
            [0],
            marker=OPERATOR_MARKERS[op],
            linestyle="none",
            markerfacecolor="white",
            markeredgecolor="#6B6B6B",
            markeredgewidth=0.8,
            markersize=5.2,
            label=op,
        )
        for op in OPERATORS
    ]


def save_figure(fig: plt.Figure, output_dir: Path, stem: str, dpi: int) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_dir / f"{stem}.png", dpi=dpi, bbox_inches="tight", facecolor="white")
    fig.savefig(output_dir / f"{stem}.pdf", bbox_inches="tight", facecolor="white")
    fig.savefig(output_dir / f"{stem}.svg", bbox_inches="tight", facecolor="white")


def main() -> None:
    args = parse_args()
    trial = pd.read_csv(args.trial_file)
    validate_trial_data(trial)
    nasa = load_nasa_data(args.nasa_file)

    fig, axes = plt.subplots(2, 2, figsize=(7.2, 6.0))
    ax_a, ax_b, ax_c, ax_d = axes.flat

    draw_box_scatter(
        ax_a,
        trial,
        column="duration_s",
        ylabel="Task execution duration (s)",
        panel_tag="(a)",
        ylim=(15, 27.25),
        yticks=[16, 18, 20, 22, 24, 26],
        seed=7,
    )
    add_completion_time_significance(ax_a)
    draw_box_scatter(
        ax_b,
        trial,
        column="traj_length_m",
        ylabel="Master-side trajectory length (m)",
        panel_tag="(b)",
        ylim=(0.5, 1.1),
        yticks=[0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1],
        seed=11,
    )
    draw_nasa_panel(ax_c, nasa)
    draw_success_panel(ax_d)

    fig.legend(
        handles=operator_legend_handles(),
        loc="upper center",
        ncol=3,
        frameon=False,
        fontsize=8,
        handletextpad=0.45,
        columnspacing=1.6,
        bbox_to_anchor=(0.5, 0.995),
    )
    fig.subplots_adjust(
        left=0.105,
        right=0.985,
        bottom=0.085,
        top=0.925,
        wspace=0.31,
        hspace=0.34,
    )

    save_figure(fig, args.output_dir, "Fig5_combined_final", args.dpi)
    plt.close(fig)
    print(f"Saved final Fig. 5 to: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
