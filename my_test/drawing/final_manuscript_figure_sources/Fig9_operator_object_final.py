
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

MODE_C = "#6A3D9A"
MODE_E = "#4F86A6"
DARK = "#333333"
MID_GREY = "#707070"

OP_ORDER = ["P01", "P02", "P03"]
OBJECT_DISPLAY = ["Scissors", "Paper cup", "Mouse", "Apple", "Banana", "Bottle"]

OBJECT_MAP = {
    "瓶子 (bottle)": "Bottle",
    "香蕉 (banana)": "Banana",
    "苹果 (apple)": "Apple",
    "鼠标 (mouse)": "Mouse",
    "纸杯 (paper cup)": "Paper cup",
    "剪刀 (scissors)": "Scissors",
}

def resolve_trial_file(user_path: str | None = None) -> Path:
    drawing_root = Path(__file__).resolve().parent.parent
    candidates = []
    if user_path:
        candidates.append(Path(user_path))
    candidates.extend([
        drawing_root / "Fig5_final_source_and_outputs" / "mnt" / "data" / "Fig5_final_package" / "all_trials_135.csv",
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
    required = {"operator", "group_num", "specific_object", "mode", "duration_s"}
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
            "Expected exactly 9 matched task units for each operator; "
            f"found {operator_counts.to_dict()}."
        )

    pivot["improvement_s"] = pivot["E"] - pivot["C"]  # positive = C faster
    pivot["object_en"] = pivot["specific_object"].map(OBJECT_MAP)
    if pivot["object_en"].isna().any():
        unknown = sorted(pivot.loc[pivot["object_en"].isna(), "specific_object"].unique())
        raise ValueError(f"Unmapped object labels: {unknown}")

    return pivot

def style_axes(ax, grid_axis: str = "x") -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(0.8)
    ax.spines["bottom"].set_linewidth(0.8)
    ax.tick_params(axis="both", labelsize=8, width=0.8)
    if grid_axis:
        ax.grid(axis=grid_axis, linestyle="--", linewidth=0.5, alpha=0.25, zorder=0)

def add_panel_tag(ax, tag: str) -> None:
    ax.text(
        0.015, 0.985, tag,
        transform=ax.transAxes,
        ha="left", va="top",
        fontsize=10.5, fontweight="bold",
    )

def save_figure(fig, output_stem: Path) -> None:
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_stem.with_suffix(".png"), dpi=600, bbox_inches="tight")
    fig.savefig(output_stem.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(output_stem.with_suffix(".svg"), bbox_inches="tight")

def summarize_groups(pivot: pd.DataFrame, group_column: str, order: list[str]) -> pd.DataFrame:
    rows = []
    for group in order:
        subset = pivot.loc[pivot[group_column] == group]
        c_values = subset["C"].to_numpy(float)
        e_values = subset["E"].to_numpy(float)
        improvement = e_values - c_values
        rows.append(
            {
                "group": group,
                "mean_c": float(c_values.mean()),
                "sd_c": float(c_values.std(ddof=1)),
                "mean_e": float(e_values.mean()),
                "sd_e": float(e_values.std(ddof=1)),
                "improvement": float(improvement.mean()),
                "n_pos": int((improvement > 0).sum()),
                "n_total": int(improvement.size),
            }
        )
    return pd.DataFrame(rows)


def draw_dumbbell_panel(
    ax,
    stats: pd.DataFrame,
    panel_tag: str,
    title: str,
    x_limits: tuple[float, float],
    sort_by_improvement: bool,
) -> None:
    ordered = (
        stats.sort_values("improvement", ascending=False).reset_index(drop=True)
        if sort_by_improvement
        else stats.reset_index(drop=True)
    )
    y_positions = np.arange(len(ordered))[::-1]
    label_x = x_limits[1] - 0.10

    for y, row in zip(y_positions, ordered.itertuples(index=False)):
        ax.plot([row.mean_c, row.mean_e], [y, y], color=MID_GREY, linewidth=1.15, alpha=0.80, zorder=1)
        ax.errorbar(
            row.mean_c, y + 0.11, xerr=row.sd_c, fmt="o", markersize=6.3,
            markerfacecolor=MODE_C, markeredgecolor="white", markeredgewidth=0.75,
            color=MODE_C, ecolor=MODE_C, elinewidth=1.25, capsize=2.6, capthick=1.25, zorder=3,
        )
        ax.errorbar(
            row.mean_e, y - 0.11, xerr=row.sd_e, fmt="o", markersize=6.3,
            markerfacecolor=MODE_E, markeredgecolor="white", markeredgewidth=0.75,
            color=MODE_E, ecolor=MODE_E, elinewidth=1.25, capsize=2.6, capthick=1.25, zorder=3,
        )
        ax.text(
            label_x,
            y,
            f"+{row.improvement:.2f} s | {row.n_pos}/{row.n_total}",
            ha="right",
            va="center",
            fontsize=7.3,
            color=DARK,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.88, "pad": 0.25},
            zorder=4,
        )

    ax.set_xlim(*x_limits)
    ax.set_ylim(-0.65, len(ordered) - 0.28)
    ax.set_yticks(y_positions)
    ax.set_yticklabels(ordered["group"])
    ax.set_xlabel("Mean task duration (s)", fontsize=8.5)
    ax.set_title(f"{panel_tag} {title}", loc="left", fontsize=9.5, fontweight="bold", pad=6)
    ax.text(label_x, len(ordered) - 0.14, r"$\Delta T$ | C faster", ha="right", va="bottom", fontsize=7.2, color=DARK)
    style_axes(ax, grid_axis="x")

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create the final two-panel Fig. 7 for operator- and object-stratified consistency."
    )
    parser.add_argument("--trial-file", default=None)
    parser.add_argument(
        "--output-stem",
        default=Path(__file__).resolve().parent.parent / "outputs" / "final_manuscript_figures" / "Fig9_operator_object_final",
        help="Output path without extension.",
    )
    args = parser.parse_args()

    trial_file = resolve_trial_file(args.trial_file)
    pivot = load_paired_data(trial_file)

    # Audit expected values against manuscript text.
    operator_means = pivot.groupby("operator")["improvement_s"].mean().reindex(OP_ORDER)
    expected_operator = np.array([1.662678, 2.564933, 1.157100])
    if not np.allclose(operator_means.to_numpy(), expected_operator, atol=5e-4):
        raise ValueError(
            "Operator means do not match audited values: "
            f"{operator_means.to_dict()}"
        )

    object_means = (
        pivot.groupby("object_en")["improvement_s"].mean()
        .reindex(OBJECT_DISPLAY)
    )
    expected_object = {
        "Scissors": 2.854775,
        "Paper cup": 2.481540,
        "Mouse": 1.890340,
        "Apple": 1.695775,
        "Banana": 1.144760,
        "Bottle": 0.669250,
    }
    for key, val in expected_object.items():
        if not np.isclose(object_means.loc[key], val, atol=5e-4):
            raise ValueError(f"Object mean mismatch for {key}: {object_means.loc[key]:.6f} vs {val:.6f}")

    operator_stats = summarize_groups(pivot, "operator", OP_ORDER)
    object_stats = summarize_groups(pivot, "object_en", OBJECT_DISPLAY)
    lower = min(
        (operator_stats["mean_c"] - operator_stats["sd_c"]).min(),
        (operator_stats["mean_e"] - operator_stats["sd_e"]).min(),
        (object_stats["mean_c"] - object_stats["sd_c"]).min(),
        (object_stats["mean_e"] - object_stats["sd_e"]).min(),
    ) - 0.55
    upper = max(
        (operator_stats["mean_c"] + operator_stats["sd_c"]).max(),
        (operator_stats["mean_e"] + operator_stats["sd_e"]).max(),
        (object_stats["mean_c"] + object_stats["sd_c"]).max(),
        (object_stats["mean_e"] + object_stats["sd_e"]).max(),
    ) + 2.15
    x_limits = (float(lower), float(upper))

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.45), constrained_layout=False)
    draw_dumbbell_panel(axes[0], operator_stats, "(a)", "Operator", x_limits, sort_by_improvement=False)
    draw_dumbbell_panel(axes[1], object_stats, "(b)", "Object", x_limits, sort_by_improvement=True)
    fig.legend(
        handles=[
            Line2D([0], [0], marker="o", color=MODE_C, markerfacecolor=MODE_C, markeredgecolor="white", markersize=6, linewidth=1.25, label=r"Mode C: mean $\pm$ SD"),
            Line2D([0], [0], marker="o", color=MODE_E, markerfacecolor=MODE_E, markeredgecolor="white", markersize=6, linewidth=1.25, label=r"Mode E: mean $\pm$ SD"),
        ],
        loc="upper center",
        bbox_to_anchor=(0.5, 1.01),
        ncol=2,
        frameon=False,
        fontsize=8.0,
    )

    fig.subplots_adjust(
        left=0.075,
        right=0.985,
        bottom=0.19,
        top=0.84,
        wspace=0.28,
    )

    output_stem = Path(args.output_stem)
    save_figure(fig, output_stem)
    plt.close(fig)

    print(f"Input: {trial_file}")
    print("Operator means:", operator_means.round(4).to_dict())
    print("Object means:", object_means.round(4).to_dict())
    print(f"Saved: {output_stem}.png/.pdf/.svg")


if __name__ == "__main__":
    main()
