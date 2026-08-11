#!/usr/bin/env python3
"""Generate Figure 2: Case-study teleoperation system and acquisition lineage."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import struct
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import pandas as pd


MM_TO_INCH = 1.0 / 25.4
WIDTH_MM = 190.0
HEIGHT_MM = 118.0
DEFAULT_PNG_DPI = 600
STEM = "Fig02_system_and_lineage"

COLORS = {
    "neutral": "#F1F1F1",
    "blue": "#DCE8F2",
    "green": "#DDECE4",
    "orange": "#F2E1D5",
    "white": "#FFFFFF",
    "edge": "#555555",
    "line": "#4A4A4A",
    "guide": "#8A8A8A",
    "muted": "#555555",
    "trial": "#E5F0EA",
    "human": "#F4E4D8",
}

PANEL_LAYOUT = {
    "A": [0.025, 0.055, 0.535, 0.90],
    "B": [0.595, 0.055, 0.380, 0.90],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None, help="paper2_sci root or repository root")
    parser.add_argument("--dpi", type=int, default=DEFAULT_PNG_DPI, help="PNG resolution (minimum 600).")
    args = parser.parse_args()
    if args.dpi < 600:
        parser.error("--dpi must be at least 600 for publication PNG output")
    return args


def resolve_project_root(root: Path | None) -> Path:
    candidate = Path(__file__).resolve().parents[2] if root is None else root.resolve()
    if (candidate / "03_clean_analysis").is_dir():
        return candidate
    nested = candidate / "my_test" / "paper2_sci"
    if (nested / "03_clean_analysis").is_dir():
        return nested
    raise FileNotFoundError(f"Could not locate paper2_sci below --root={candidate}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def set_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
        }
    )


def read_clean_csv(clean_dir: Path, filename: str, required: list[str]) -> pd.DataFrame:
    path = clean_dir / filename
    frame = pd.read_csv(path)
    missing = [column for column in required if column not in frame.columns]
    print(f"SCHEMA {filename}: {frame.shape[0]} rows x {frame.shape[1]} columns")
    for column in required:
        print(f"  {column} -> {column if column in frame.columns else None}")
    if missing:
        raise KeyError(f"Missing columns in {filename}: {missing}; actual={list(frame.columns)}")
    return frame


def add_box(
    ax: plt.Axes,
    x: float,
    y: float,
    width: float,
    height: float,
    text: str,
    facecolor: str,
    fontsize: float = 6.8,
    bold_first_line: bool = False,
    linewidth: float = 0.75,
) -> FancyBboxPatch:
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.006,rounding_size=0.012",
        facecolor=facecolor,
        edgecolor=COLORS["edge"],
        linewidth=linewidth,
    )
    ax.add_patch(patch)
    lines = text.split("\n")
    if bold_first_line and len(lines) > 1:
        ax.text(x + width / 2, y + height * 0.68, lines[0], ha="center", va="center", fontsize=fontsize, fontweight="bold")
        ax.text(x + width / 2, y + height * 0.34, "\n".join(lines[1:]), ha="center", va="center", fontsize=fontsize - 0.25, linespacing=1.12)
    else:
        ax.text(x + width / 2, y + height / 2, text, ha="center", va="center", fontsize=fontsize, fontweight="bold" if bold_first_line else "normal", linespacing=1.12)
    return patch


def arrow(ax: plt.Axes, start: tuple[float, float], end: tuple[float, float], connectionstyle: str = "arc3") -> FancyArrowPatch:
    patch = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=8.5,
        linewidth=0.8,
        color=COLORS["line"],
        connectionstyle=connectionstyle,
        shrinkA=1.0,
        shrinkB=1.0,
    )
    ax.add_patch(patch)
    return patch


def panel_title(ax: plt.Axes, letter: str, title: str) -> None:
    ax.text(0.0, 1.01, f"({letter})", fontsize=9.5, fontweight="bold", va="bottom")
    ax.text(0.075, 1.01, title, fontsize=9.0, fontweight="bold", va="bottom")


def draw_panel_a(ax: plt.Axes) -> None:
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    panel_title(ax, "A", "Teleoperation system")

    main_x, main_w, box_h = 0.355, 0.285, 0.085
    main_nodes = [
        (0.855, "Human operator", COLORS["neutral"]),
        (0.690, "Force Dimension\nOmega.7", COLORS["blue"]),
        (0.505, "Supervisory controller", COLORS["blue"]),
        (0.320, "Franka Emika Panda\n+ Franka Hand", COLORS["green"]),
        (0.135, "Physical object / environment\ninteraction", COLORS["orange"]),
    ]
    for y, text, face in main_nodes:
        add_box(ax, main_x, y, main_w, box_h, text, face, fontsize=6.9, bold_first_line=False)

    centers = [y + box_h / 2 for y, _, _ in main_nodes]
    for index in range(len(main_nodes) - 1):
        upper_y = main_nodes[index][0]
        lower_top = main_nodes[index + 1][0] + box_h
        arrow(ax, (main_x + main_w / 2, upper_y - 0.006), (main_x + main_w / 2, lower_top + 0.006))
    ax.text(0.515, 0.642, "master translational\ncommand", fontsize=5.8, ha="left", va="center", color=COLORS["muted"])
    ax.text(0.515, 0.457, "commanded Cartesian impedance\n+ gripper command", fontsize=5.8, ha="left", va="center", color=COLORS["muted"])
    ax.text(0.515, 0.272, "physical interaction", fontsize=5.8, ha="left", va="center", color=COLORS["muted"])

    vision_x, vision_w, vision_h = 0.015, 0.245, 0.070
    vision_nodes = [
        (0.785, "Intel RealSense D435i"),
        (0.650, "Semantic detection"),
        (0.515, "Vision lock / profile"),
    ]
    for index, (y, text) in enumerate(vision_nodes):
        add_box(ax, vision_x, y, vision_w, vision_h, text, COLORS["blue"] if index < 2 else COLORS["green"], fontsize=6.1)
    for index in range(2):
        arrow(ax, (vision_x + vision_w / 2, vision_nodes[index][0] - 0.006), (vision_x + vision_w / 2, vision_nodes[index + 1][0] + vision_h + 0.006))
    arrow(ax, (vision_x + vision_w + 0.005, 0.550), (main_x - 0.005, 0.550))

    state_x, state_w, state_h = 0.700, 0.275, 0.073
    state_nodes = [
        (0.350, "Panda robot state", COLORS["neutral"]),
        (0.257, "$O\\_F\\_ext\\_hat\\_K$", COLORS["neutral"]),
        (0.164, "Internal estimated\nexternal wrench (filtered)", COLORS["green"]),
        (0.035, "Used for:\ncontact detection\nhaptic feedback\nlogged force signal", COLORS["neutral"]),
    ]
    for index, (y, text, face) in enumerate(state_nodes):
        add_box(ax, state_x, y, state_w, state_h if index < 3 else 0.095, text, face, fontsize=5.45, bold_first_line=(index == 2))
    arrow(ax, (main_x + main_w + 0.005, 0.362), (state_x - 0.005, 0.386))
    for index in range(3):
        current_y = state_nodes[index][0]
        next_top = state_nodes[index + 1][0] + (state_h if index + 1 < 3 else 0.095)
        arrow(ax, (state_x + state_w / 2, current_y - 0.004), (state_x + state_w / 2, next_top + 0.004))

    feedback_y = 0.732
    ax.plot([state_x + state_w, 0.992], [0.0825, 0.0825], color=COLORS["line"], linewidth=0.75)
    ax.plot([0.992, 0.992], [0.0825, feedback_y], color=COLORS["line"], linewidth=0.75)
    arrow(ax, (0.992, feedback_y), (main_x + main_w + 0.005, feedback_y))
    ax.text(0.825, feedback_y + 0.022, "haptic feedback", fontsize=5.8, ha="center", va="bottom", color=COLORS["muted"])


def draw_panel_b(ax: plt.Axes, counts: dict[str, int]) -> None:
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    panel_title(ax, "B", "Acquisition provenance")

    add_box(ax, 0.28, 0.895, 0.44, 0.066, "Experimental acquisition", COLORS["neutral"], fontsize=6.8, bold_first_line=True)
    source_y, source_h, source_w = 0.770, 0.082, 0.285
    source_x = [0.015, 0.3575, 0.700]
    source_text = ["Raw CSV\ntime series", "Event JSON", "Summary JSON"]
    for x, text in zip(source_x, source_text):
        add_box(ax, x, source_y, source_w, source_h, text, COLORS["blue"], fontsize=6.1)
        arrow(ax, (0.50, 0.895), (x + source_w / 2, source_y + source_h + 0.006))

    join_y = 0.708
    for x in source_x:
        ax.plot([x + source_w / 2, x + source_w / 2], [source_y, join_y], color=COLORS["guide"], linewidth=0.7)
    ax.plot([source_x[0] + source_w / 2, source_x[-1] + source_w / 2], [join_y, join_y], color=COLORS["guide"], linewidth=0.7)
    add_box(ax, 0.17, 0.615, 0.66, 0.078, "Exact logical key + timestamped acquisition ID", COLORS["green"], fontsize=5.9, bold_first_line=True)
    arrow(ax, (0.50, join_y), (0.50, 0.615 + 0.078 + 0.004))

    add_box(ax, 0.20, 0.505, 0.60, 0.074, "Master manifest\n+ SHA-256 verification", COLORS["neutral"], fontsize=6.3, bold_first_line=False)
    arrow(ax, (0.50, 0.615), (0.50, 0.505 + 0.074 + 0.004))

    add_box(ax, 0.14, 0.392, 0.72, 0.073, f"{counts['archived_acquisitions']} archived acquisitions\nsuperseded records preserved", COLORS["neutral"], fontsize=6.35, bold_first_line=True)
    arrow(ax, (0.50, 0.505), (0.50, 0.392 + 0.073 + 0.004))

    add_box(ax, 0.14, 0.280, 0.72, 0.075, f"{counts['selected_acquisitions']} selected clean acquisitions\n{counts['selected_source_files']} selected source files", COLORS["green"], fontsize=6.35, bold_first_line=True)
    arrow(ax, (0.50, 0.392), (0.50, 0.280 + 0.075 + 0.004))

    ax.text(0.06, 0.245, "TRIAL-LEVEL FIDELITY EVIDENCE", fontsize=5.8, fontweight="bold", color="#3B6A54", va="bottom")
    add_box(ax, 0.10, 0.155, 0.80, 0.075, f"Trial-level fidelity reconstruction\nn = {counts['selected_acquisitions']} trials (fidelity observations)", COLORS["trial"], fontsize=6.25, bold_first_line=True, linewidth=0.9)
    arrow(ax, (0.50, 0.280), (0.50, 0.150 + 0.080 + 0.004))

    ax.text(0.06, 0.118, "HUMAN OUTCOME INFERENCE", fontsize=5.8, fontweight="bold", color="#8A4C2E", va="bottom")
    add_box(ax, 0.08, 0.008, 0.84, 0.098, f"Participant-level outcome aggregation\nn = {counts['participants']} independent human participants\nhuman inference unit (not n = 180)", COLORS["human"], fontsize=6.1, bold_first_line=True, linewidth=1.0)
    arrow(ax, (0.50, 0.155), (0.50, 0.008 + 0.098 + 0.004))


def png_size_and_dpi(path: Path) -> tuple[int, int, float, float]:
    width = height = 0
    dpi_x = dpi_y = 0.0
    with path.open("rb") as handle:
        if handle.read(8) != b"\x89PNG\r\n\x1a\n":
            raise ValueError(f"Not a PNG: {path}")
        while True:
            raw_length = handle.read(4)
            if not raw_length:
                break
            length = struct.unpack(">I", raw_length)[0]
            chunk_type = handle.read(4)
            data = handle.read(length)
            handle.read(4)
            if chunk_type == b"IHDR":
                width, height = struct.unpack(">II", data[:8])
            elif chunk_type == b"pHYs":
                x_ppm, y_ppm, unit = struct.unpack(">IIB", data)
                if unit == 1:
                    dpi_x, dpi_y = x_ppm * 0.0254, y_ppm * 0.0254
            elif chunk_type == b"IEND":
                break
    return width, height, dpi_x, dpi_y


def write_qa(
    report_path: Path,
    counts: dict[str, int],
    input_paths: list[Path],
    outputs: list[Path],
    source_path: Path,
    png_dpi: int,
) -> dict[str, object]:
    checks: list[dict[str, object]] = []

    def check(name: str, actual: object, expected: object, passed: bool) -> None:
        checks.append({"check": name, "actual": actual, "expected": expected, "passed": bool(passed)})

    check("archived acquisitions", counts["archived_acquisitions"], 186, counts["archived_acquisitions"] == 186)
    check("selected clean acquisitions", counts["selected_acquisitions"], 180, counts["selected_acquisitions"] == 180)
    check("independent participants", counts["participants"], 5, counts["participants"] == 5)
    check("selected source files", counts["selected_source_files"], 540, counts["selected_source_files"] == 540)
    check("all requested outputs exist", [str(path) for path in outputs], "non-empty PDF/SVG/PNG", all(path.is_file() and path.stat().st_size > 1000 for path in outputs))
    svg = outputs[1].read_text(encoding="utf-8")
    check("SVG editable text", "<text" in svg, True, "<text" in svg)
    png_info = png_size_and_dpi(outputs[2])
    check("PNG resolution", png_info[2:4], f">= {png_dpi - 1} dpi", png_info[2] >= png_dpi - 1.0 and png_info[3] >= png_dpi - 1.0)
    check("PDF TrueType setting", matplotlib.rcParams["pdf.fonttype"], 42, matplotlib.rcParams["pdf.fonttype"] == 42)
    check("SVG live-text setting", matplotlib.rcParams["svg.fonttype"], "none", matplotlib.rcParams["svg.fonttype"] == "none")
    report = {
        "figure": STEM,
        "status": "PASS" if all(item["passed"] for item in checks) else "FAIL",
        "counts": counts,
        "input_files": [{"path": str(path), "sha256": sha256(path)} for path in input_paths],
        "source_data": {"path": str(source_path), "sha256": sha256(source_path)},
        "outputs": [str(path) for path in outputs],
        "python_version": platform.python_version(),
        "pandas_version": pd.__version__,
        "matplotlib_version": matplotlib.__version__,
        "generation_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    if report["status"] != "PASS":
        raise RuntimeError(f"Figure 2 QA failed: {[item for item in checks if not item['passed']]}")
    return report


def update_manifest(project_root: Path, input_paths: list[Path], source_path: Path, outputs: list[Path]) -> None:
    manifest_path = project_root / "19_publication_figures" / "figure_manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {"figures": []}

    def relative(path: Path) -> str:
        return str(path.resolve().relative_to(project_root.resolve())).replace("\\", "/")

    record = {
        "figure_name": STEM,
        "script_path": relative(Path(__file__)),
        "input_files": [{"path": relative(path), "sha256": sha256(path)} for path in input_paths],
        "figure_source_data": {"path": relative(source_path), "sha256": sha256(source_path)},
        "output_paths": [relative(path) for path in outputs],
        "python_version": platform.python_version(),
        "pandas_version": pd.__version__,
        "matplotlib_version": matplotlib.__version__,
        "generation_timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    payload["figures"] = [item for item in payload.get("figures", []) if item.get("figure_name") not in {STEM, "Fig02_system_data_lineage"}]
    payload["figures"].append(record)
    payload["figures"] = sorted(payload["figures"], key=lambda item: item["figure_name"])
    manifest_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    args = parse_args()
    project_root = resolve_project_root(args.root)
    clean_dir = project_root / "03_clean_analysis"
    publication_root = project_root / "19_publication_figures"
    figure_dir = publication_root / "figures"
    source_dir = publication_root / "figure_source_data"
    figure_dir.mkdir(parents=True, exist_ok=True)
    source_dir.mkdir(parents=True, exist_ok=True)

    lineage_path = clean_dir / "data_lineage_audit.csv"
    participant_path = clean_dir / "participant_level_metrics.csv"
    lineage = read_clean_csv(
        clean_dir,
        lineage_path.name,
        ["record_id", "included_main_clean", "csv_hash_verified", "events_hash_verified", "summary_hash_verified"],
    )
    participant = read_clean_csv(clean_dir, participant_path.name, ["participant", "mode_code"])
    selected = lineage[lineage["included_main_clean"].eq(1)].copy()
    counts = {
        "archived_acquisitions": int(lineage["record_id"].nunique()),
        "selected_acquisitions": int(selected["record_id"].nunique()),
        "participants": int(participant["participant"].nunique()),
        "selected_source_files": int(selected[["csv_hash_verified", "events_hash_verified", "summary_hash_verified"]].to_numpy(dtype=int).sum()),
    }
    source = pd.DataFrame(
        [
            {"quantity": "archived_acquisitions", "value": counts["archived_acquisitions"], "clean_source": lineage_path.name},
            {"quantity": "selected_clean_acquisitions", "value": counts["selected_acquisitions"], "clean_source": lineage_path.name},
            {"quantity": "independent_human_participants", "value": counts["participants"], "clean_source": participant_path.name},
            {"quantity": "selected_source_files_hash_verified", "value": counts["selected_source_files"], "clean_source": lineage_path.name},
        ]
    )
    source_path = source_dir / "figure02_source_data.csv"
    source.to_csv(source_path, index=False, lineterminator="\n")

    set_style()
    fig = plt.figure(figsize=(WIDTH_MM * MM_TO_INCH, HEIGHT_MM * MM_TO_INCH))
    ax_a = fig.add_axes(PANEL_LAYOUT["A"])
    ax_b = fig.add_axes(PANEL_LAYOUT["B"])
    draw_panel_a(ax_a)
    draw_panel_b(ax_b, counts)
    pdf_path = figure_dir / f"{STEM}.pdf"
    svg_path = figure_dir / f"{STEM}.svg"
    png_path = figure_dir / f"{STEM}.png"
    fig.savefig(pdf_path, bbox_inches="tight", pad_inches=0.02)
    fig.savefig(svg_path, bbox_inches="tight", pad_inches=0.02)
    fig.savefig(png_path, dpi=args.dpi, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)

    outputs = [pdf_path, svg_path, png_path]
    report = write_qa(publication_root / "figure02_qa_report.json", counts, [lineage_path, participant_path], outputs, source_path, args.dpi)
    update_manifest(project_root, [lineage_path, participant_path], source_path, outputs)
    print(f"Generated {STEM}")
    print(f"QA: {report['status']} ({len(report['checks'])}/{len(report['checks'])} checks)")


if __name__ == "__main__":
    main()
