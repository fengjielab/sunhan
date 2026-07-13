
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

MODE_C = "#6A3D9A"
MODE_C_LIGHT = "#D9C7F0"
BASE_BLUE = "#5B8DB8"
BASE_BLUE_LIGHT = "#DCEAF5"
DARK = "#333333"
MID_GREY = "#707070"
LIGHT_GREY = "#D0D0D0"

OP_ORDER = ["P01", "P02", "P03"]
OP_MARKERS = {"P01": "o", "P02": "^", "P03": "s"}
OP_OFFSETS = {"P01": -0.08, "P02": 0.00, "P03": 0.08}

OBJECT_MAP = {
    "瓶子 (bottle)": "Bottle",
    "香蕉 (banana)": "Banana",
    "苹果 (apple)": "Apple",
    "鼠标 (mouse)": "Mouse",
    "纸杯 (paper cup)": "Paper cup",
    "剪刀 (scissors)": "Scissors",
}

def resolve_trial_file(user_path: str | None = None) -> Path:
    candidates = []
    if user_path:
        candidates.append(Path(user_path))
    candidates.extend([
        Path("../data/all_trials_135.csv"),
        Path("data/all_trials_135.csv"),
        Path("all_trials_135.csv"),
        Path(__file__).resolve().parent / "data" / "all_trials_135.csv",
    ])
    for path in candidates:
        if path.exists():
            return path.resolve()
    raise FileNotFoundError(
        "Could not locate all_trials_135.csv. "
        "Pass it explicitly with --trial-file PATH."
    )

def load_paired_data(trial_file: Path) -> pd.DataFrame:
    df = pd.read_csv(trial_file)
    required = {
        "operator", "group_num", "specific_object", "mode", "duration_s"
    }
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    pivot = (
        df.pivot_table(
            index=["operator", "group_num", "specific_object"],
            columns="mode",
            values="duration_s",
            aggfunc="mean",
        )
        .reset_index()
    )

    for mode in ("C", "E"):
        if mode not in pivot.columns:
            raise ValueError(f"Mode {mode!r} is missing after pivoting.")

    if len(pivot) != 27:
        raise ValueError(f"Expected 27 matched task units, found {len(pivot)}.")

    operator_counts = pivot["operator"].value_counts().reindex(OP_ORDER)
    if operator_counts.isna().any() or not np.all(operator_counts.to_numpy() == 9):
        raise ValueError(
            "Expected exactly 9 matched task units for each of P01, P02, and P03; "
            f"found {operator_counts.to_dict()}."
        )

    if pivot[["C", "E"]].isna().any().any():
        raise ValueError("Missing paired C or E duration values.")

    pivot["improvement_s"] = pivot["E"] - pivot["C"]
    pivot["relative_reduction_pct"] = (
        pivot["improvement_s"] / pivot["E"] * 100.0
    )
    pivot["object_en"] = pivot["specific_object"].map(OBJECT_MAP)

    if pivot["object_en"].isna().any():
        unknown = sorted(pivot.loc[pivot["object_en"].isna(), "specific_object"].unique())
        raise ValueError(f"Unmapped object labels: {unknown}")

    return pivot

def style_axes(ax, grid_axis: str = "both") -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(0.8)
    ax.spines["bottom"].set_linewidth(0.8)
    ax.tick_params(axis="both", labelsize=8, width=0.8)
    if grid_axis:
        ax.grid(
            axis=grid_axis,
            linestyle="--",
            linewidth=0.5,
            alpha=0.25,
            zorder=0,
        )

def add_panel_tag(ax, tag: str) -> None:
    ax.text(
        0.015, 0.985, tag,
        transform=ax.transAxes,
        ha="left", va="top",
        fontsize=10.5, fontweight="bold",
    )

def operator_handles():
    return [
        Line2D(
            [0], [0],
            marker=OP_MARKERS[op],
            linestyle="none",
            markerfacecolor="white",
            markeredgecolor=DARK,
            markeredgewidth=0.8,
            markersize=5.2,
            label=op,
        )
        for op in OP_ORDER
    ]

def save_figure(fig, output_stem: Path) -> None:
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_stem.with_suffix(".png"), dpi=600, bbox_inches="tight")
    fig.savefig(output_stem.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(output_stem.with_suffix(".svg"), bbox_inches="tight")


def draw_panel_a(ax, pivot: pd.DataFrame, panel_tag: str = "(a)") -> None:
    # Same operator symbols are used throughout Fig. 6.
    for op in OP_ORDER:
        sub = pivot.loc[pivot["operator"] == op]
        ax.scatter(
            sub["E"], sub["C"],
            marker=OP_MARKERS[op],
            s=26,
            facecolors="white",
            edgecolors=BASE_BLUE,
            linewidths=0.9,
            alpha=0.90,
            zorder=3,
        )

    low = min(pivot["E"].min(), pivot["C"].min()) - 0.65
    high = max(pivot["E"].max(), pivot["C"].max()) + 0.65
    ax.plot(
        [low, high], [low, high],
        linestyle="--",
        linewidth=1.0,
        color=MID_GREY,
        zorder=1,
    )
    ax.set_xlim(low, high)
    ax.set_ylim(low, high)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel(r"Mode E duration, $T_E$ (s)", fontsize=9)
    ax.set_ylabel(r"Mode C duration, $T_C$ (s)", fontsize=9)
    ax.text(
        0.97, 0.05,
        "Below identity line:\nC faster",
        transform=ax.transAxes,
        ha="right", va="bottom",
        fontsize=7.5,
        color=DARK,
    )
    style_axes(ax, grid_axis="both")
    add_panel_tag(ax, panel_tag)


def draw_panel_b(ax, pivot: pd.DataFrame, panel_tag: str = "(b)") -> None:
    values = pivot["improvement_s"].to_numpy()
    rng = np.random.default_rng(42)

    parts = ax.violinplot(
        [values],
        positions=[1.0],
        widths=0.52,
        showmeans=False,
        showmedians=False,
        showextrema=False,
    )
    for body in parts["bodies"]:
        body.set_facecolor(MODE_C_LIGHT)
        body.set_edgecolor(MODE_C)
        body.set_linewidth(0.9)
        body.set_alpha(0.55)

    # Show the nesting explicitly using operator-specific markers and offsets.
    for op in OP_ORDER:
        sub = pivot.loc[pivot["operator"] == op, "improvement_s"].to_numpy()
        x = 1.0 + OP_OFFSETS[op] + rng.uniform(-0.012, 0.012, size=len(sub))
        ax.scatter(
            x, sub,
            marker=OP_MARKERS[op],
            s=22,
            facecolors="white",
            edgecolors=MODE_C,
            linewidths=0.8,
            alpha=0.90,
            zorder=3,
        )

    mean_value = float(values.mean())
    median_value = float(np.median(values))

    ax.axhline(0, color=MID_GREY, linestyle="--", linewidth=0.9, zorder=1)
    ax.hlines(
        median_value, 0.84, 1.16,
        color=DARK, linewidth=1.5, zorder=4,
    )
    ax.scatter(
        [1.29], [mean_value],
        marker="D",
        s=38,
        facecolors=MODE_C,
        edgecolors=MODE_C,
        linewidths=0.8,
        zorder=5,
    )
    ax.text(
        1.33, mean_value,
        f"Mean = {mean_value:.2f} s",
        ha="left", va="center",
        fontsize=7.5,
        color=DARK,
    )
    ax.text(
        0.98, 0.96,
        "Positive improvement: C faster",
        transform=ax.transAxes,
        ha="right", va="top",
        fontsize=7.5,
        color=DARK,
    )

    margin = 0.55
    ax.set_ylim(values.min() - margin, values.max() + margin)
    ax.set_xlim(0.66, 1.62)
    ax.set_xticks([1.0])
    ax.set_xticklabels(["27 matched task blocks\n(9 per operator)"])
    ax.set_ylabel(r"Paired improvement, $\Delta T=T_E-T_C$ (s)", fontsize=9)
    style_axes(ax, grid_axis="y")
    add_panel_tag(ax, panel_tag)



def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create the final two-panel Fig. 6 for the C–E core ablation."
    )
    parser.add_argument("--trial-file", default=None)
    parser.add_argument(
        "--output-stem",
        default="outputs/Fig6_AB_final",
        help="Output path without extension.",
    )
    args = parser.parse_args()

    trial_file = resolve_trial_file(args.trial_file)
    pivot = load_paired_data(trial_file)

    expected_mean = 1.794904
    if not np.isclose(pivot["improvement_s"].mean(), expected_mean, atol=5e-4):
        raise ValueError(
            f"Mean improvement mismatch: {pivot['improvement_s'].mean():.6f} vs {expected_mean:.6f}"
        )

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.45), constrained_layout=False)
    draw_panel_a(axes[0], pivot, "(a)")
    draw_panel_b(axes[1], pivot, "(b)")

    fig.legend(
        handles=operator_handles(),
        labels=OP_ORDER,
        loc="upper center",
        ncol=3,
        frameon=False,
        fontsize=8,
        bbox_to_anchor=(0.5, 0.995),
        handletextpad=0.45,
        columnspacing=1.25,
    )
    fig.subplots_adjust(
        left=0.095,
        right=0.985,
        bottom=0.16,
        top=0.86,
        wspace=0.30,
    )

    output_stem = Path(args.output_stem)
    save_figure(fig, output_stem)
    plt.close(fig)

    print(f"Input: {trial_file}")
    print(f"Matched task blocks: {len(pivot)}")
    print(f"Mean improvement (E-C): {pivot['improvement_s'].mean():.4f} s")
    print(f"Saved: {output_stem}.png/.pdf/.svg")


if __name__ == "__main__":
    main()
