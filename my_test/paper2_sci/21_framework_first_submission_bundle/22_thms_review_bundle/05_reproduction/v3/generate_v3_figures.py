from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.text import Text


SCRIPT_DIR = Path(__file__).resolve().parent
BUNDLE = SCRIPT_DIR.parents[1]
FIGURE_SCRIPT_DIR = BUNDLE / "05_reproduction" / "figure_scripts"
if str(FIGURE_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(FIGURE_SCRIPT_DIR))

import fig01_framework as fig01  # noqa: E402
import fig04_participant_outcomes as fig04  # noqa: E402
from figure_style import save_publication_figure  # noqa: E402


OUTPUT_DIR = BUNDLE / "02_main_figures" / "v3"
SOURCE_DIR = SCRIPT_DIR / "figure_source_data"
QA_DIR = BUNDLE / "04_logic_and_qa" / "v3"
DPI = 600


def replace_text(fig: plt.Figure, mapping: dict[str, str]) -> None:
    for item in fig.findobj(match=lambda obj: isinstance(obj, Text)):
        current = item.get_text()
        if current in mapping:
            item.set_text(mapping[current])


def generate_fig01() -> tuple[list[Path], Path]:
    fig = fig01.create_figure()
    replace_text(
        fig,
        {
            "From nominal specification to an evidence-admissible claim":
                "From nominal specification to a fidelity-constrained claim",
            "Evidence-admissible\nclaim": "Fidelity-constrained\nclaim",
            "N ≠ C": "N absent / N ≠ C",
            "guard / clock": "spec / guard / clock",
            "R ≠ W": "R ≠ window",
        },
    )
    axes = fig.axes[0]
    axes.text(
        0.975,
        0.505,
        "Identity retained ≠ causal identification",
        fontsize=5.5,
        ha="right",
        va="bottom",
        color=fig01.COLORS["muted"],
        fontstyle="italic",
    )
    stem = "Fig01_fidelity_constrained_framework_v3"
    outputs = save_publication_figure(fig, OUTPUT_DIR, stem, DPI)
    plt.close(fig)

    source = pd.DataFrame(
        [
            {
                "element_type": "evidence_state",
                "field": "nominal_spec",
                "allowed_values": "available; unavailable",
                "decision_role": "separates missing N from N-to-C mismatch",
            },
            {
                "element_type": "evidence_state",
                "field": "n_to_c",
                "allowed_values": "pass; fail; not_evaluable",
                "decision_role": "specification-to-implementation status",
            },
            {
                "element_type": "evidence_state",
                "field": "c_to_r",
                "allowed_values": "pass; fail; not_evaluable",
                "decision_role": "implementation-to-realization status",
            },
            {
                "element_type": "evidence_state",
                "field": "exposure",
                "allowed_values": "full; partial; zero; unavailable; not_applicable",
                "decision_role": "outcome-window exposure status",
            },
            {
                "element_type": "evidence_state",
                "field": "provenance",
                "allowed_values": "valid; invalid",
                "decision_role": "orthogonal intervention-outcome linkage prerequisite",
            },
        ]
    )
    source_path = SOURCE_DIR / "figure01_v3_source_data.csv"
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    source.to_csv(source_path, index=False, encoding="utf-8-sig")
    return [Path(item) for item in outputs], source_path


def generate_fig04() -> tuple[list[Path], Path]:
    source_path_v2 = BUNDLE / "05_reproduction" / "figure_source_data" / "figure04_source_data.csv"
    source = pd.read_csv(source_path_v2)
    mapping = {
        "G-A": {
            "nominal_framing": "Label-implied post-contact adaptation",
            "fidelity_evidence": "G specification unavailable; 43/45 pre-contact",
            "admissible_comparison": "Realized raw-force-rule G versus fixed A",
        },
        "E-A": {
            "nominal_framing": "Vision-isolated assistance",
            "fidelity_evidence": "Bundled parameters; visual exposure 39/2/4",
            "admissible_comparison": "E bundle/exposure distribution versus fixed A",
        },
        "F-E": {
            "nominal_framing": "+0.20-s force refinement",
            "fidelity_evidence": "Only 3/45 met timing; mixed clocks",
            "admissible_comparison": "Early/heterogeneous F versus E",
        },
        "F-G": {
            "nominal_framing": "Vision × force interaction",
            "fidelity_evidence": "Different bundles, rules, and timing",
            "admissible_comparison": "Observed F bundle versus G bundle",
        },
    }
    for contrast, values in mapping.items():
        selected = source["row_type"].eq("interpretation_map") & source["contrast"].eq(contrast)
        for column, value in values.items():
            source.loc[selected, column] = value

    fig = fig04.create_figure(source)
    replace_text(
        fig,
        {
            "Evidence-admissible comparison": "Fidelity-constrained comparison",
            "Admissible = narrowest comparison supported by implementation, delivery, exposure, and analysis unit.":
                "Constrained = narrowest comparison supported by specification, delivery, exposure, provenance, and analysis unit.",
            "Primary participant-level outcome": "Primary operational force outcome",
            "E − A difference in excess-force impulse (N·s)":
                "E − A difference in operational excess-force impulse (N·s)",
        },
    )
    stem = "Fig04_fidelity_constrained_outcomes_v3"
    outputs = save_publication_figure(fig, OUTPUT_DIR, stem, DPI)
    plt.close(fig)

    v3_source = source.rename(columns={"admissible_comparison": "fidelity_constrained_comparison"})
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    source_path = SOURCE_DIR / "figure04_v3_source_data.csv"
    v3_source.to_csv(source_path, index=False, encoding="utf-8-sig")
    return [Path(item) for item in outputs], source_path


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    QA_DIR.mkdir(parents=True, exist_ok=True)
    fig01_outputs, fig01_source = generate_fig01()
    fig04_outputs, fig04_source = generate_fig04()
    outputs = fig01_outputs + fig04_outputs

    checks = []
    for path in outputs:
        checks.append({
            "check": f"nonempty_{path.name}",
            "passed": int(path.is_file() and path.stat().st_size > 1000),
            "observed_bytes": path.stat().st_size if path.is_file() else 0,
            "expected": ">1000",
        })
    for path in [item for item in outputs if item.suffix.lower() == ".svg"]:
        text = path.read_text(encoding="utf-8")
        checks.append({
            "check": f"no_admissible_wording_{path.name}",
            "passed": int("admissible" not in text.lower()),
            "observed_bytes": 0,
            "expected": "no 'admissible' text",
        })
    if not all(item["passed"] for item in checks):
        raise RuntimeError(f"v3 figure QA failed: {checks}")

    report = {
        "status": "PASS",
        "dpi": DPI,
        "checks": checks,
        "outputs": [str(path.relative_to(BUNDLE)) for path in outputs],
        "source_data": [
            str(fig01_source.relative_to(BUNDLE)),
            str(fig04_source.relative_to(BUNDLE)),
        ],
        "version_boundary": "No v1/v2 figure path is written by this script.",
    }
    (QA_DIR / "v3_figure_qa.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
