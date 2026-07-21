
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

OP_ORDER = ["P01", "P02", "P03"]
OP_MARKERS = {"P01": "o", "P02": "^", "P03": "s"}
OBJECT_MARKERS = {
    "Scissors": "o",
    "Paper cup": "s",
    "Mouse": "^",
    "Apple": "D",
    "Banana": "v",
    "Bottle": "P",
}
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

def draw_panel_a(ax, pivot: pd.DataFrame, panel_tag: str = "(a)") -> None:
    rng = np.random.default_rng(42)
    y_positions = np.arange(len(OP_ORDER))[::-1]  # P01 top

    stats = []
    for op, y in zip(OP_ORDER, y_positions):
        vals = pivot.loc[pivot["operator"] == op, "improvement_s"].to_numpy()
        stats.append((op, y, vals.mean(), vals.std(ddof=1), int((vals > 0).sum()), len(vals)))

        y_jitter = y + rng.uniform(-0.10, 0.10, size=len(vals))
        ax.scatter(
            vals, y_jitter,
            marker=OP_MARKERS[op],
            s=18,
            facecolors="white",
            edgecolors=BASE_BLUE,
            linewidths=0.8,
            alpha=0.70,
            zorder=2,
        )
        mean_val = vals.mean()
        sd_val = vals.std(ddof=1)
        ax.hlines(y, mean_val - sd_val, mean_val + sd_val, color=MID_GREY, linewidth=1.2, zorder=3)
        ax.scatter(
            [mean_val], [y],
            marker="D",
            s=42,
            facecolors=MODE_C,
            edgecolors=MODE_C,
            linewidths=0.8,
            zorder=4,
        )

    ax.axvline(0, linestyle="--", linewidth=1.0, color=MID_GREY, zorder=1)
    ax.set_yticks(y_positions)
    ax.set_yticklabels(OP_ORDER)
    ax.set_ylabel("Operator", fontsize=9)
    ax.set_xlabel(r"Paired improvement, $\Delta T=T_E-T_C$ (s)", fontsize=9)

    xmin = min(0, pivot["improvement_s"].min()) - 0.45
    xmax = max(pivot["improvement_s"].max(), 3.0) + 2.05
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(-0.65, len(OP_ORDER) - 0.35)

    label_x = max(3.25, pivot["improvement_s"].max() + 0.32)
    header_y = y_positions.max() + 0.42
    ax.text(label_x, header_y, "Mean", fontsize=7.7, color=DARK, ha="left")
    ax.text(label_x + 1.25, header_y, "C faster", fontsize=7.7, color=DARK, ha="left")

    for op, y, mean_val, sd_val, n_pos, n_total in stats:
        ax.text(label_x, y, f"{mean_val:.2f} s", va="center", fontsize=7.7, color=DARK)
        ax.text(label_x + 1.25, y, f"{n_pos}/{n_total}", va="center", fontsize=7.7, color=DARK, ha="left")

    style_axes(ax, grid_axis="x")
    add_panel_tag(ax, panel_tag)


def draw_panel_b(ax, pivot: pd.DataFrame, panel_tag: str = "(b)") -> None:
    rng = np.random.default_rng(123)
    rows = []
    for obj in OBJECT_DISPLAY:
        vals = pivot.loc[pivot["object_en"] == obj, "improvement_s"].to_numpy()
        rows.append(
            {
                "object": obj,
                "mean": vals.mean(),
                "sd": vals.std(ddof=1) if len(vals) > 1 else 0.0,
                "n_pos": int((vals > 0).sum()),
                "n_total": len(vals),
                "vals": vals,
            }
        )
    stats = pd.DataFrame(rows).sort_values("mean", ascending=False).reset_index(drop=True)
    y_positions = np.arange(len(stats))[::-1]

    for y, row in zip(y_positions, stats.itertuples(index=False)):
        y_jitter = y + rng.uniform(-0.10, 0.10, size=len(row.vals))
        ax.scatter(
            row.vals, y_jitter,
            marker=OBJECT_MARKERS[row.object],
            s=18,
            facecolors="white",
            edgecolors=BASE_BLUE,
            linewidths=0.8,
            alpha=0.70,
            zorder=2,
        )
        ax.hlines(y, row.mean - row.sd, row.mean + row.sd, color=MID_GREY, linewidth=1.2, zorder=3)
        ax.scatter(
            [row.mean], [y],
            marker="D",
            s=42,
            facecolors=MODE_C,
            edgecolors=MODE_C,
            linewidths=0.8,
            zorder=4,
        )

    ax.axvline(0, linestyle="--", linewidth=1.0, color=MID_GREY, zorder=1)
    ax.set_yticks(y_positions)
    ax.set_yticklabels(stats["object"])
    ax.set_ylabel("Object", fontsize=9)
    ax.set_xlabel(r"Paired improvement, $\Delta T=T_E-T_C$ (s)", fontsize=9)

    xmin = min(0, pivot["improvement_s"].min()) - 0.55
    xmax = max(3.0, pivot["improvement_s"].max()) + 2.15
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(-0.55, len(stats) - 0.35)

    label_x = max(3.25, pivot["improvement_s"].max() + 0.32)
    header_y = y_positions.max() + 0.58
    ax.text(label_x, header_y, "Mean", fontsize=7.7, color=DARK, ha="left")
    ax.text(label_x + 1.25, header_y, "C faster", fontsize=7.7, color=DARK, ha="left")

    for y, row in zip(y_positions, stats.itertuples(index=False)):
        ax.text(label_x, y + 0.11, f"{row.mean:.2f} s", va="center", fontsize=7.6, color=DARK)
        ax.text(label_x + 1.25, y - 0.12, f"{row.n_pos}/{row.n_total}", va="center", fontsize=7.6, color=DARK, ha="left")

    style_axes(ax, grid_axis="x")
    add_panel_tag(ax, panel_tag)

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create the final two-panel Fig. 7 for operator- and object-stratified consistency."
    )
    parser.add_argument("--trial-file", default=None)
    parser.add_argument(
        "--output-stem",
        default="outputs/Fig7_combined_final",
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

    fig, axes = plt.subplots(
        2, 1,
        figsize=(7.2, 6.6),
        constrained_layout=False,
    )

    draw_panel_a(axes[0], pivot, "(a)")
    draw_panel_b(axes[1], pivot, "(b)")

    fig.subplots_adjust(
        left=0.11,
        right=0.985,
        bottom=0.08,
        top=0.985,
        hspace=0.28,
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
