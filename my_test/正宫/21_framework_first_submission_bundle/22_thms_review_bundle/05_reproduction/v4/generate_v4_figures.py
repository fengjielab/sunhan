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
OUTPUT = BUNDLE / "02_main_figures" / "v4"
SOURCE_OUT = HERE / "figure_source_data"
LOGIC_OUT = BUNDLE / "04_logic_and_qa" / "v4"
FIG04_SCRIPT = BUNDLE / "05_reproduction" / "figure_scripts" / "fig04_participant_outcomes.py"
V3_FIG04_SOURCE = BUNDLE / "05_reproduction" / "v3" / "figure_source_data" / "figure04_v3_source_data.csv"
DPI = 600


def save(fig: plt.Figure, stem: str) -> list[Path]:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    paths = [OUTPUT / f"{stem}.{suffix}" for suffix in ("pdf", "svg", "png")]
    fig.savefig(paths[0], bbox_inches="tight")
    fig.savefig(paths[1], bbox_inches="tight")
    fig.savefig(paths[2], dpi=DPI, bbox_inches="tight")
    return paths


def box(ax, x, y, w, h, title, body, color, edge="#334155", title_size=12, body_size=9.5):
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.012,rounding_size=0.015",
        linewidth=1.3, edgecolor=edge, facecolor=color,
    )
    ax.add_patch(patch)
    ax.text(x + 0.018, y + h - 0.035, title, ha="left", va="top", fontsize=title_size, fontweight="bold", color="#0f172a")
    ax.text(x + 0.018, y + h - 0.075, body, ha="left", va="top", fontsize=body_size, linespacing=1.28, color="#334155")


def arrow(ax, x0, y0, x1, y1, color="#475569", lw=1.7):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=14, linewidth=lw, color=color))


def generate_fig01() -> tuple[list[Path], Path]:
    fig, ax = plt.subplots(figsize=(16, 8.7))
    fig.patch.set_facecolor("white")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.02, 0.965, "(A)", fontsize=17, fontweight="bold", va="top")
    ax.text(0.075, 0.965, "Two-stage artifact-to-inference pipeline", fontsize=17, fontweight="bold", va="top")

    ax.text(0.14, 0.895, "STAGE A — Evidence reconstruction", fontsize=11.5, fontweight="bold", color="#0369a1")
    box(ax, 0.14, 0.64, 0.17, 0.22, "Raw artifacts", "specification / protocol\nsource snapshot\nevents and state logs\nrecord IDs and hashes", "#e0f2fe", body_size=8.8)
    box(ax, 0.37, 0.64, 0.20, 0.22, "Auditable extraction", "automatic computation\nstructured author audit\nrule + tolerance\nmissingness + rationale", "#e0f2fe", body_size=8.8)
    box(ax, 0.63, 0.64, 0.20, 0.22, "EvidenceState  S", "nominal_spec\nn_to_c   |   c_to_r\nexposure   |   provenance", "#dbeafe", body_size=9)
    arrow(ax, 0.31, 0.78, 0.37, 0.78)
    arrow(ax, 0.57, 0.78, 0.63, 0.78)
    ax.text(0.225, 0.612, "Label ≠ specification", ha="center", fontsize=9.2, color="#9a3412", fontweight="bold")
    ax.text(0.47, 0.612, "No outcome, direction, or p value", ha="center", fontsize=9.2, color="#9a3412", fontweight="bold")

    ax.text(0.14, 0.575, "STAGE B — Inference constraint", fontsize=11.5, fontweight="bold", color="#047857")
    box(ax, 0.14, 0.35, 0.17, 0.18, "Diagnostics", "cumulative break codes\nmissing ≠ mismatch\nmultiple breaks retained", "#dcfce7", body_size=8.8)
    box(ax, 0.37, 0.35, 0.20, 0.18, "Comparison identity", "retained / qualified\nunsupported / indeterminate\nnot evaluable", "#dcfce7", body_size=8.8)
    box(ax, 0.63, 0.35, 0.20, 0.18, "Scientific wording", "narrowest supported level\nallowed description\nprohibited claim", "#d1fae5", body_size=8.8)
    arrow(ax, 0.31, 0.455, 0.37, 0.455)
    arrow(ax, 0.57, 0.455, 0.63, 0.455)
    arrow(ax, 0.73, 0.69, 0.73, 0.54, color="#047857")
    ax.text(0.86, 0.31, "Identity retained ≠ causal identification", ha="center", va="center", fontsize=9.2, fontstyle="italic", color="#475569")

    ax.plot([0.02, 0.98], [0.28, 0.28], color="#cbd5e1", lw=1.2)
    ax.text(0.02, 0.255, "(B)", fontsize=17, fontweight="bold", va="top")
    ax.text(0.075, 0.255, "Closed-loop timing changes the human–machine outcome path", fontsize=15, fontweight="bold", va="top")
    box(ax, 0.13, 0.065, 0.16, 0.12, "Realized intervention", "$R_i(t)$\nvisual / haptic / machine state", "#fef3c7", title_size=10.5, body_size=8.2)
    box(ax, 0.41, 0.065, 0.16, 0.12, "Later human input", "$H_i(t+\\delta)$\napproach / correction", "#ffedd5", title_size=10.5, body_size=8.2)
    box(ax, 0.69, 0.065, 0.16, 0.12, "Later realization/outcome", "$R_i(t+\\delta) \\rightarrow Y_i$", "#fee2e2", title_size=10.5, body_size=8.2)
    arrow(ax, 0.29, 0.132, 0.41, 0.132)
    arrow(ax, 0.57, 0.132, 0.69, 0.132)
    ax.text(0.50, 0.018, "Acquisition provenance is an orthogonal prerequisite for linking realized intervention to outcome.", ha="center", fontsize=9.5, color="#475569", fontstyle="italic")

    paths = save(fig, "Fig01_artifact_to_inference_pipeline_v4")
    plt.close(fig)
    source = pd.DataFrame([
        {"stage": "A", "input": "raw artifacts", "operation": "automatic computation or structured author audit", "output": "EvidenceState"},
        {"stage": "B", "input": "EvidenceState", "operation": "deterministic inference constraint", "output": "diagnosis; identity; comparison; wording"},
        {"stage": "closed_loop", "input": "realized intervention", "operation": "changes later human input", "output": "later realization and outcome"},
    ])
    SOURCE_OUT.mkdir(parents=True, exist_ok=True)
    source_path = SOURCE_OUT / "figure01_v4_source_data.csv"
    source.to_csv(source_path, index=False, encoding="utf-8-sig")
    return paths, source_path


def load_module(path: Path):
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("fig04_v4_base", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def replace_text(fig: plt.Figure, mapping: dict[str, str]) -> None:
    for item in fig.findobj(match=lambda obj: isinstance(obj, Text)):
        if item.get_text() in mapping:
            item.set_text(mapping[item.get_text()])


def generate_fig04() -> tuple[list[Path], Path]:
    module = load_module(FIG04_SCRIPT)
    source = pd.read_csv(V3_FIG04_SOURCE)
    if "fidelity_constrained_comparison" in source.columns:
        source["admissible_comparison"] = source["fidelity_constrained_comparison"]
    source.loc[source["contrast"].eq("F-E"), "fidelity_evidence"] = "Only 3/45 met timing; C-to-R replay incomplete"
    source.loc[source["contrast"].eq("F-E"), "admissible_comparison"] = "Recorded early/heterogeneous F versus E"
    source.loc[source["contrast"].eq("F-G"), "fidelity_evidence"] = "Different bundles/timing; F replay incomplete"
    fig = module.create_figure(source)
    replace_text(fig, {
        "Evidence-admissible comparison": "Artifact- and fidelity-constrained comparison",
        "Fidelity-constrained comparison": "Artifact- and fidelity-constrained comparison",
        "Admissible = narrowest comparison supported by implementation, delivery, exposure, and analysis unit.": "Constrained = narrowest comparison supported by artifacts, delivery, exposure, provenance, and analysis unit.",
        "Constrained = narrowest comparison supported by specification, delivery, exposure, provenance, and analysis unit.": "Constrained = narrowest comparison supported by artifacts, delivery, exposure, provenance, and analysis unit.",
        "Primary participant-level outcome": "Primary operational force outcome",
    })
    paths = save(fig, "Fig04_fidelity_constrained_outcomes_v4")
    plt.close(fig)
    SOURCE_OUT.mkdir(parents=True, exist_ok=True)
    source_path = SOURCE_OUT / "figure04_v4_source_data.csv"
    source.to_csv(source_path, index=False, encoding="utf-8-sig")
    return paths, source_path


def main() -> None:
    p1, s1 = generate_fig01()
    p4, s4 = generate_fig04()
    checks = []
    for path in p1 + p4:
        checks.append({"check": f"exists_nonempty_{path.name}", "passed": int(path.exists() and path.stat().st_size > 1000), "observed_bytes": path.stat().st_size})
    for path in [item for item in p1 + p4 if item.suffix == ".svg"]:
        content = path.read_text(encoding="utf-8").lower()
        checks.append({"check": f"safe_wording_{path.name}", "passed": int("admissible" not in content and "validated framework" not in content), "observed_bytes": path.stat().st_size})
    if not all(item["passed"] for item in checks):
        raise RuntimeError(checks)
    report = {"status": "PASS", "checks": checks, "source_data": [str(s1.relative_to(BUNDLE)), str(s4.relative_to(BUNDLE))], "version_boundary": "Only 02_main_figures/v4 and 05_reproduction/v4/figure_source_data are written."}
    LOGIC_OUT.mkdir(parents=True, exist_ok=True)
    (LOGIC_OUT / "v4_figure_qa.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
