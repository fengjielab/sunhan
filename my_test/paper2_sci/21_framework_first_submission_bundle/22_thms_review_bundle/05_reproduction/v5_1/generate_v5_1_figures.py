from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from matplotlib.text import Text
import pandas as pd


HERE = Path(__file__).resolve().parent
BUNDLE = HERE.parents[1]
OUTPUT = BUNDLE / "02_main_figures" / "v5_1"
LOGIC_OUT = BUNDLE / "04_logic_and_qa" / "v5_1"
ASSET = BUNDLE / "05_reproduction" / "assets" / "experimental_setup.jpg"
FIG03_SCRIPT = BUNDLE / "05_reproduction" / "figure_scripts" / "fig03_fidelity_results.py"
FIG03_SOURCE = BUNDLE / "05_reproduction" / "figure_source_data" / "figure03_source_data.csv"
FIG04_SOURCE = BUNDLE / "05_reproduction" / "v3" / "figure_source_data" / "figure04_v3_source_data.csv"
ROBUSTNESS_SOURCE = BUNDLE / "03_supplement" / "v4_data" / "record_selection_summary.csv"
DPI = 600


COLORS = {
    "ink": "#172033",
    "line": "#475569",
    "blue": "#0b78b5",
    "blue_fill": "#dbeafe",
    "green": "#079b74",
    "green_fill": "#dff3ea",
    "orange": "#d55e00",
    "orange_fill": "#f8e8dc",
    "gray_fill": "#f2f2f2",
    "yellow_fill": "#fff2c7",
}


def save(fig: plt.Figure, stem: str) -> list[Path]:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    paths = [OUTPUT / f"{stem}.{suffix}" for suffix in ("pdf", "svg", "png")]
    fig.savefig(paths[0], bbox_inches="tight")
    fig.savefig(paths[1], bbox_inches="tight")
    fig.savefig(paths[2], dpi=DPI, bbox_inches="tight")
    return paths


def box(ax, xy, width, height, title, body="", face="#f2f2f2", edge="#475569", title_size=11, body_size=9):
    x, y = xy
    patch = FancyBboxPatch(
        (x, y), width, height,
        boxstyle="round,pad=0.012,rounding_size=0.018",
        facecolor=face, edgecolor=edge, linewidth=1.4,
    )
    ax.add_patch(patch)
    ax.text(x + width / 2, y + height * 0.64, title, ha="center", va="center", fontsize=title_size, fontweight="bold", color=COLORS["ink"])
    if body:
        ax.text(x + width / 2, y + height * 0.29, body, ha="center", va="center", fontsize=body_size, color=COLORS["line"], linespacing=1.15)
    return patch


def arrow(ax, start, end, color=None, style="-|>", connectionstyle="arc3", lw=1.8):
    ax.add_patch(FancyArrowPatch(
        start, end, arrowstyle=style, mutation_scale=14, linewidth=lw,
        color=color or COLORS["line"], connectionstyle=connectionstyle,
    ))


def generate_fig01() -> list[Path]:
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 9), gridspec_kw={"height_ratios": [1.15, 0.85]})
    fig.patch.set_facecolor("white")
    for ax in (ax1, ax2):
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")

    ax1.text(0.01, 0.96, "(A)", fontsize=18, fontweight="bold", va="top")
    ax1.text(0.07, 0.96, "Asynchronous human–machine loop determines intervention delivery and exposure", fontsize=17, fontweight="bold", va="top")

    box(ax1, (0.04, 0.38), 0.15, 0.28, "Human operator", "$H_i(t)$\napproach · contact · correction", COLORS["orange_fill"])
    box(ax1, (0.25, 0.38), 0.14, 0.28, "Omega.7", "master motion\nhaptic feedback", COLORS["blue_fill"])
    box(ax1, (0.47, 0.38), 0.17, 0.28, "Supervisory controller", "guards · clocks\nimpedance · force rule", COLORS["blue_fill"])
    box(ax1, (0.72, 0.38), 0.15, 0.28, "Panda + task", "robot state\ncontact interaction", COLORS["green_fill"])
    box(ax1, (0.47, 0.73), 0.17, 0.15, "RGB vision process", "asynchronous lock", COLORS["green_fill"], title_size=10.5, body_size=8.5)

    arrow(ax1, (0.19, 0.56), (0.25, 0.56), COLORS["blue"])
    arrow(ax1, (0.39, 0.56), (0.47, 0.56), COLORS["blue"])
    arrow(ax1, (0.64, 0.56), (0.72, 0.56), COLORS["blue"])
    ax1.text(0.43, 0.60, "human command", ha="center", fontsize=9, color=COLORS["blue"])
    ax1.text(0.68, 0.60, "robot / gripper command", ha="center", fontsize=9, color=COLORS["blue"])

    arrow(ax1, (0.555, 0.73), (0.555, 0.67), COLORS["green"])
    ax1.text(0.575, 0.70, "vision lock", fontsize=9, color=COLORS["green"], va="center")
    arrow(ax1, (0.79, 0.38), (0.33, 0.32), COLORS["orange"], connectionstyle="arc3,rad=-0.12")
    arrow(ax1, (0.72, 0.45), (0.19, 0.43), COLORS["orange"], connectionstyle="arc3,rad=0.10")
    ax1.text(0.55, 0.20, "estimated wrench → contact state · logged force · haptic response", ha="center", fontsize=9.5, color=COLORS["orange"])
    ax1.text(0.92, 0.53, "$R_i(t)$", fontsize=15, fontweight="bold", color=COLORS["green"])
    ax1.text(0.90, 0.42, "visual / haptic /\nmachine state", fontsize=9.5, color=COLORS["line"], ha="center")
    ax1.text(0.50, 0.07, r"$R_i(t)\;\rightarrow\;H_i(t+\delta)\;\rightarrow\;R_i(t+\delta)\;\rightarrow\;Y_i$", ha="center", fontsize=16, color=COLORS["ink"])

    ax2.text(0.01, 0.96, "(B)", fontsize=18, fontweight="bold", va="top")
    ax2.text(0.07, 0.96, "Evidence reconstruction constrains comparison identity before outcome interpretation", fontsize=16, fontweight="bold", va="top")
    labels = [
        (0.04, "Nominal intervention", "$N_m$", COLORS["gray_fill"]),
        (0.23, "Executable implementation", "$C_m$", COLORS["blue_fill"]),
        (0.42, "Realized intervention", "$R_i$", COLORS["green_fill"]),
        (0.61, "Windowed outcome", "$Y_i$", COLORS["orange_fill"]),
    ]
    for x, title, body, face in labels:
        box(ax2, (x, 0.46), 0.15, 0.25, title, body, face, title_size=10.5, body_size=13)
    for x0, x1 in ((0.19, 0.23), (0.38, 0.42), (0.57, 0.61)):
        arrow(ax2, (x0, 0.585), (x1, 0.585))
    ax2.text(0.21, 0.75, "specification / guard / clock", ha="center", fontsize=8.5, color=COLORS["line"])
    ax2.text(0.405, 0.75, "delivery", ha="center", fontsize=8.5, color=COLORS["line"])
    ax2.text(0.595, 0.75, "window exposure", ha="center", fontsize=8.5, color=COLORS["line"])

    box(ax2, (0.79, 0.58), 0.17, 0.20, "EvidenceState", "$s_N, s_{NC}, s_{CR}, s_\\Phi, s_\\mathcal{P}$", COLORS["yellow_fill"], title_size=11, body_size=10)
    box(ax2, (0.79, 0.22), 0.17, 0.22, "Inference constraint", "diagnosis · identity\ncomparison · wording", COLORS["green_fill"], title_size=11, body_size=9)
    arrow(ax2, (0.495, 0.71), (0.79, 0.68), COLORS["line"], connectionstyle="arc3,rad=-0.24")
    ax2.text(0.70, 0.84, "evidence reconstruction\n(outcome values excluded)", ha="center", fontsize=8.5, color=COLORS["line"])
    arrow(ax2, (0.875, 0.58), (0.875, 0.44), COLORS["green"])
    ax2.text(0.36, 0.20, "Raw artifacts: specification · source · events · state logs · record identity / hashes", ha="center", fontsize=10, color=COLORS["line"])
    ax2.text(0.50, 0.08, "Acquisition provenance is an orthogonal prerequisite; identity retained ≠ causal identification.", ha="center", fontsize=10, fontstyle="italic", color=COLORS["line"])

    fig.tight_layout(h_pad=0.6)
    paths = save(fig, "Fig01_human_machine_fidelity_framework_v5_1")
    plt.close(fig)
    return paths


def generate_fig02() -> list[Path]:
    fig = plt.figure(figsize=(16, 8.8))
    fig.patch.set_facecolor("white")
    gs = fig.add_gridspec(2, 2, width_ratios=[1.18, 0.82], height_ratios=[1, 1], wspace=0.08, hspace=0.20)
    ax_photo = fig.add_subplot(gs[:, 0])
    ax_loop = fig.add_subplot(gs[0, 1])
    ax_design = fig.add_subplot(gs[1, 1])

    image = plt.imread(ASSET)
    ax_photo.imshow(image)
    ax_photo.axis("off")
    ax_photo.set_title("(A)  Archived teleoperation setup and task workspace", loc="left", fontsize=16, fontweight="bold", pad=12)
    ax_photo.text(0.01, -0.045, "Real archived photograph; supplied annotations retained without generative editing.", transform=ax_photo.transAxes, fontsize=9.5, fontstyle="italic", color=COLORS["line"])

    for ax in (ax_loop, ax_design):
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")

    ax_loop.text(0.00, 0.98, "(B)  Closed-loop signals and asynchronous event channels", fontsize=15, fontweight="bold", va="top")
    box(ax_loop, (0.02, 0.43), 0.18, 0.25, "Operator", "human input", COLORS["orange_fill"], title_size=10.5)
    box(ax_loop, (0.28, 0.43), 0.18, 0.25, "Omega.7", "motion / haptics", COLORS["blue_fill"], title_size=10.5)
    box(ax_loop, (0.55, 0.43), 0.19, 0.25, "Controller", "vision · guards\nimpedance / force", COLORS["blue_fill"], title_size=10.5, body_size=8.5)
    box(ax_loop, (0.82, 0.43), 0.15, 0.25, "Panda", "task contact", COLORS["green_fill"], title_size=10.5)
    arrow(ax_loop, (0.20, 0.56), (0.28, 0.56), COLORS["blue"])
    arrow(ax_loop, (0.46, 0.56), (0.55, 0.56), COLORS["blue"])
    arrow(ax_loop, (0.74, 0.56), (0.82, 0.56), COLORS["blue"])
    arrow(ax_loop, (0.88, 0.42), (0.38, 0.30), COLORS["orange"], connectionstyle="arc3,rad=-0.10")
    ax_loop.text(0.63, 0.21, "contact estimate · logged force · haptic feedback", ha="center", fontsize=8.5, color=COLORS["orange"])
    box(ax_loop, (0.55, 0.76), 0.19, 0.13, "RGB vision", "asynchronous lock", COLORS["green_fill"], title_size=9.5, body_size=7.8)
    arrow(ax_loop, (0.645, 0.76), (0.645, 0.69), COLORS["green"])
    ax_loop.text(0.50, 0.07, "Separate clocks and update loops are evaluated before outcome interpretation.", ha="center", fontsize=9, fontstyle="italic", color=COLORS["line"])

    ax_design.text(0.00, 0.98, "(C)  Archived experiment and analysis window", fontsize=15, fontweight="bold", va="top")
    box(ax_design, (0.04, 0.61), 0.18, 0.18, "5 participants", "human unit n=5", COLORS["orange_fill"], title_size=10.5, body_size=8.5)
    box(ax_design, (0.29, 0.61), 0.18, 0.18, "3 materials", "× 3 repeat blocks", COLORS["gray_fill"], title_size=10.5, body_size=8.5)
    box(ax_design, (0.54, 0.61), 0.18, 0.18, "4 conditions", "A · G · E · F", COLORS["blue_fill"], title_size=10.5, body_size=9)
    box(ax_design, (0.79, 0.61), 0.17, 0.18, "180 trials", "45 per condition", COLORS["green_fill"], title_size=10.5, body_size=8.5)
    for x0, x1 in ((0.22, 0.29), (0.47, 0.54), (0.72, 0.79)):
        arrow(ax_design, (x0, 0.70), (x1, 0.70))

    ax_design.plot([0.08, 0.94], [0.34, 0.34], color=COLORS["line"], lw=1.6)
    ax_design.axvline(0.35, ymin=0.24, ymax=0.43, color=COLORS["ink"], lw=2)
    ax_design.text(0.35, 0.43, "recorded contact = 0 s", ha="center", fontsize=9.5, fontweight="bold")
    ax_design.add_patch(plt.Rectangle((0.50, 0.27), 0.31, 0.14, facecolor="#e5e7eb", edgecolor="#6b7280", lw=1.2))
    ax_design.text(0.655, 0.34, "outcome window\n+0.20 to +1.00 s", ha="center", va="center", fontsize=9.5)
    ax_design.text(0.50, 0.10, "Trial-level fidelity: 180 observations", ha="center", fontsize=10, color=COLORS["green"])
    ax_design.text(0.50, 0.02, "Human outcome inference: 5 independent participants", ha="center", fontsize=10, color=COLORS["orange"], fontweight="bold")

    paths = save(fig, "Fig02_system_experiment_v5_1")
    plt.close(fig)
    return paths


def load_module(path: Path, name: str):
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def generate_fig03() -> list[Path]:
    module = load_module(FIG03_SCRIPT, "fig03_v5_base")
    source = pd.read_csv(FIG03_SOURCE)
    fig = module.create_figure(source)
    for item in fig.findobj(match=lambda obj: isinstance(obj, Text)):
        if "Nominal delay implemented with mixed clocks" in item.get_text():
            item.set_text(item.get_text().replace(
                "Nominal delay implemented with mixed clocks",
                "Mixed clocks; full replay unavailable",
            ))
            item.set_fontsize(9.6)
    paths = save(fig, "Fig03_realized_intervention_fidelity_v5_1")
    plt.close(fig)
    return paths


def generate_fig04() -> list[Path]:
    source = pd.read_csv(FIG04_SOURCE)
    summary = source[source["row_type"].eq("contrast_summary")].iloc[0]
    participants = (
        source[source["row_type"].eq("participant_mean")][["participant", "participant_difference_E_minus_A"]]
        .dropna().drop_duplicates("participant").sort_values("participant")
    )
    robustness = pd.read_csv(ROBUSTNESS_SOURCE)
    ea = robustness[robustness["contrast"].eq("EA")].iloc[0]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15.5, 6.6), gridspec_kw={"width_ratios": [1.7, 0.85]})
    fig.patch.set_facecolor("white")

    y = list(range(len(participants)))
    diffs = participants["participant_difference_E_minus_A"].to_numpy()
    ax1.axvline(0, color=COLORS["line"], lw=1.6, ls="--")
    for yi, value in zip(y, diffs):
        ax1.plot([value, 0], [yi, yi], color="#8bb9aa", lw=2)
        ax1.scatter([value], [yi], s=125, facecolor="white", edgecolor=COLORS["green"], linewidth=2.4, zorder=3)
    mean = float(summary["effect_estimate_E_minus_A"])
    lo = float(summary["ci95_low"])
    hi = float(summary["ci95_high"])
    mean_y = len(y) + 0.75
    ax1.errorbar(mean, mean_y, xerr=[[mean - lo], [hi - mean]], fmt="D", markersize=10, color=COLORS["ink"], markerfacecolor=COLORS["green"], markeredgecolor="white", capsize=5, lw=2.2)
    ax1.set_yticks(y + [mean_y], list(participants["participant"]) + ["Mean (95% CI)"])
    ax1.invert_yaxis()
    ax1.set_xlim(-0.66, 0.04)
    ax1.set_xlabel("E − A difference in excess-force impulse (N·s)", fontsize=12)
    ax1.set_title("(A)  Participant-level retained E–A comparison", loc="left", fontsize=16, fontweight="bold")
    ax1.grid(axis="x", alpha=0.25)
    ax1.spines[["top", "right"]].set_visible(False)
    ax1.text(-0.65, mean_y + 0.55, "← lower operational impulse under the E bundle", fontsize=9.5, color=COLORS["green"])

    minimum = float(ea["minimum_mean_difference_Ns"])
    maximum = float(ea["maximum_mean_difference_Ns"])
    ax2.plot([minimum, maximum], [0.55, 0.55], color=COLORS["green"], lw=8, solid_capstyle="round")
    ax2.scatter([mean], [0.55], marker="D", s=130, color=COLORS["ink"], edgecolor="white", linewidth=1.5, zorder=3)
    ax2.scatter([minimum, maximum], [0.55, 0.55], s=80, color=COLORS["green"], zorder=3)
    ax2.set_xlim(-0.36, -0.33)
    ax2.set_ylim(0, 1)
    ax2.set_yticks([])
    ax2.set_xlabel("Mean E − A difference (N·s)", fontsize=12)
    ax2.set_title("(B)  Record-selection robustness", loc="left", fontsize=16, fontweight="bold")
    ax2.grid(axis="x", alpha=0.25)
    ax2.spines[["top", "right", "left"]].set_visible(False)
    ax2.text(0.50, 0.88, "All 64 combinations remained negative", transform=ax2.transAxes, ha="center", fontsize=11, fontweight="bold", color=COLORS["green"])
    ax2.text(0.50, 0.77, "range −0.353791 to −0.336697 N·s", transform=ax2.transAxes, ha="center", fontsize=10)
    ax2.text(0.98, 0.66, "zero lies to the right →", transform=ax2.transAxes, ha="right", fontsize=9, color=COLORS["line"])
    ax2.text(0.50, 0.17, "5/5 participants negative\nin every combination", transform=ax2.transAxes, ha="center", fontsize=10, color=COLORS["line"])
    ax2.text(0.50, 0.05, "Selection sensitivity does not legalize\nsuperseded records or increase n.", transform=ax2.transAxes, ha="center", fontsize=9, fontstyle="italic", color=COLORS["line"])

    fig.text(0.50, 0.01, "Exploratory bundled-configuration comparison; not a vision-, stiffness-, or force-isolated causal effect.", ha="center", fontsize=10, fontstyle="italic", color="#8a3d1d")
    fig.tight_layout(rect=[0, 0.05, 1, 1], w_pad=3.0)
    paths = save(fig, "Fig04_EA_outcome_robustness_v5_1")
    plt.close(fig)
    return paths


def main() -> None:
    generated = generate_fig01() + generate_fig02() + generate_fig03() + generate_fig04()
    checks = []
    for path in generated:
        checks.append({
            "check": f"exists_nonempty_{path.name}",
            "passed": int(path.exists() and path.stat().st_size > 1000),
            "bytes": path.stat().st_size,
        })
    if not all(item["passed"] for item in checks):
        raise RuntimeError(checks)
    report = {
        "status": "PASS",
        "checks": checks,
        "frozen_analysis_sources": [
            str(FIG03_SOURCE.relative_to(BUNDLE)).replace("\\", "/"),
            str(FIG04_SOURCE.relative_to(BUNDLE)).replace("\\", "/"),
            str(ROBUSTNESS_SOURCE.relative_to(BUNDLE)).replace("\\", "/"),
        ],
        "version_boundary": "Only 02_main_figures/v5_1 and 04_logic_and_qa/v5_1 are written.",
    }
    LOGIC_OUT.mkdir(parents=True, exist_ok=True)
    (LOGIC_OUT / "v5_1_figure_qa.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "n_checks": len(checks)}, ensure_ascii=False))


if __name__ == "__main__":
    main()


