#!/usr/bin/env python3
"""Generate manuscript Figure 1: Realized-Intervention Fidelity Framework."""

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


MM_TO_INCH = 1.0 / 25.4
FULL_WIDTH_MM = 190.0
FULL_HEIGHT_MM = 105.0
REDUCED_WIDTH_MM = 90.0
DEFAULT_PNG_DPI = 600
STEM = "Fig01_realized_intervention_framework"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="paper2_sci project root, or repository root containing my_test/paper2_sci",
    )
    parser.add_argument("--dpi", type=int, default=DEFAULT_PNG_DPI, help="PNG resolution (minimum 600).")
    args = parser.parse_args()
    if args.dpi < 600:
        parser.error("--dpi must be at least 600 for publication PNG output")
    return args


def resolve_project_root(root: Path | None) -> Path:
    candidate = Path(__file__).resolve().parents[2] if root is None else root.resolve()
    if (candidate / "19_publication_figures").is_dir() and (candidate / "03_clean_analysis").is_dir():
        return candidate
    nested = candidate / "my_test" / "paper2_sci"
    if (nested / "19_publication_figures").is_dir() and (nested / "03_clean_analysis").is_dir():
        return nested
    raise FileNotFoundError(f"Could not resolve paper2_sci below --root={candidate}")


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


def add_box(
    ax: plt.Axes,
    xy: tuple[float, float],
    size: tuple[float, float],
    facecolor: str,
    edgecolor: str,
    scale: float,
    title: str | list[str],
    symbol: str | None,
    lines: list[str],
    title_size: float = 8.1,
    text_size: float = 7.0,
    linewidth: float = 0.8,
) -> FancyBboxPatch:
    x, y = xy
    width, height = size
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.006,rounding_size=0.010",
        linewidth=linewidth * scale,
        edgecolor=edgecolor,
        facecolor=facecolor,
    )
    ax.add_patch(patch)
    title_lines = title if isinstance(title, list) else [title]
    title_y = y + height - 0.025
    ax.text(x + 0.014, title_y, "\n".join(title_lines), fontsize=title_size * scale, fontweight="bold", va="top", linespacing=1.02)
    title_block = 0.034 * len(title_lines)
    text_y = title_y - title_block - 0.022
    if symbol:
        symbol_y = title_y - title_block - 0.004
        ax.text(x + 0.014, symbol_y, symbol, fontsize=(title_size + 0.4) * scale, va="top")
        text_y = symbol_y - 0.052
    ax.text(x + 0.014, text_y, "\n".join(lines), fontsize=text_size * scale, va="top", linespacing=1.18)
    return patch


def add_right_arrow(ax: plt.Axes, x0: float, x1: float, y: float, scale: float) -> FancyArrowPatch:
    arrow = FancyArrowPatch(
        (x0, y),
        (x1, y),
        arrowstyle="-|>",
        mutation_scale=8.5 * scale,
        linewidth=0.85 * scale,
        color="#4A4A4A",
        shrinkA=1.0,
        shrinkB=1.0,
    )
    ax.add_patch(arrow)
    return arrow


def normalized_layout(definition: dict[str, object]) -> dict[str, object]:
    layout = definition["layout"]
    margin = float(layout["margin_x"])
    layer_width = float(layout["layer_width"])
    final_width = float(layout["final_width"])
    gap = (1.0 - 2.0 * margin - 4.0 * layer_width - final_width) / 4.0
    layer_x = [margin + index * (layer_width + gap) for index in range(4)]
    final_x = layer_x[-1] + layer_width + gap
    return {
        "margin": margin,
        "layer_y": float(layout["layer_y"]),
        "layer_height": float(layout["layer_height"]),
        "layer_width": layer_width,
        "gap": gap,
        "layer_x": layer_x,
        "final_x": final_x,
        "final_width": final_width,
        "interface_title_y": float(layout["interface_title_y"]),
        "interface_failure_y": float(layout["interface_failure_y"]),
        "provenance_y": float(layout["provenance_y"]),
        "provenance_height": float(layout["provenance_height"]),
    }


def build_figure(definition: dict[str, object], width_mm: float) -> tuple[plt.Figure, list[tuple[float, float]]]:
    scale = width_mm / FULL_WIDTH_MM
    height_mm = FULL_HEIGHT_MM * scale
    fig, ax = plt.subplots(figsize=(width_mm * MM_TO_INCH, height_mm * MM_TO_INCH))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    layout = normalized_layout(definition)
    colors = definition["colors"]
    layers = definition["layers"]
    arrows: list[tuple[float, float]] = []

    for index, layer in enumerate(layers):
        add_box(
            ax,
            (layout["layer_x"][index], layout["layer_y"]),
            (layout["layer_width"], layout["layer_height"]),
            colors[layer["color_key"]],
            colors["edge"],
            scale,
            layer["display_title"],
            layer["symbol"],
            layer.get("display_subtext", layer["subtext"]),
        )

    main_y = layout["layer_y"] + layout["layer_height"] / 2.0
    for index, interface in enumerate(definition["interfaces"]):
        x0 = layout["layer_x"][index] + layout["layer_width"] + 0.004
        x1 = layout["layer_x"][index + 1] - 0.004
        add_right_arrow(ax, x0, x1, main_y, scale)
        arrows.append((x0, x1))
        center = (x0 + x1) / 2.0
        ax.text(center, layout["interface_title_y"], "\n".join(interface["display_label"]), fontsize=6.6 * scale, fontweight="bold", ha="center", va="center", linespacing=1.03)
        ax.text(center, layout["interface_failure_y"], "\n".join(interface["failure"]), fontsize=6.25 * scale, ha="center", va="top", color=colors["muted_text"], linespacing=1.10)

    final = definition["final_interpretation"]
    add_box(
        ax,
        (layout["final_x"], layout["layer_y"]),
        (layout["final_width"], layout["layer_height"]),
        colors["final"],
        colors["final_edge"],
        scale,
        final["title"],
        None,
        final["subtext"],
        title_size=8.1,
        text_size=5.9,
        linewidth=1.0,
    )
    final_x0 = layout["layer_x"][-1] + layout["layer_width"] + 0.004
    final_x1 = layout["final_x"] - 0.004
    add_right_arrow(ax, final_x0, final_x1, main_y, scale)
    arrows.append((final_x0, final_x1))
    ax.text((final_x0 + final_x1) / 2.0, layout["interface_title_y"], "\n".join(final["display_arrow_label"]), fontsize=6.4 * scale, fontweight="bold", ha="center", va="center", linespacing=1.03)

    provenance = definition["provenance"]
    source_x, identity_x, linkage_x = 0.340, 0.525, 0.760
    source_w, identity_w, linkage_w = 0.145, 0.195, 0.215
    py = layout["provenance_y"]
    ph = layout["provenance_height"]
    ax.text(0.355, py + ph + 0.045, provenance["path_label"], fontsize=7.1 * scale, fontweight="bold", va="bottom")
    add_box(ax, (source_x, py), (source_w, ph), colors["provenance_source"], colors["edge"], scale, provenance["sources_title"], None, provenance["sources"], title_size=6.5, text_size=5.55)
    add_box(ax, (identity_x, py), (identity_w, ph), colors["provenance_identity"], colors["edge"], scale, provenance["identity_title"], None, provenance["identity_subtext"], title_size=6.5, text_size=5.7)
    add_box(ax, (linkage_x, py), (linkage_w, ph), colors["provenance_linkage"], colors["edge"], scale, provenance["linkage_title"], None, provenance["linkage_subtext"], title_size=6.5, text_size=5.7)
    provenance_arrow_y = py + ph / 2.0
    p1 = (source_x + source_w + 0.004, identity_x - 0.004)
    p2 = (identity_x + identity_w + 0.004, linkage_x - 0.004)
    add_right_arrow(ax, p1[0], p1[1], provenance_arrow_y, scale)
    add_right_arrow(ax, p2[0], p2[1], provenance_arrow_y, scale)
    arrows.extend([p1, p2])
    ax.text((p1[0] + p1[1]) / 2.0, py - 0.025, provenance["failure"], fontsize=6.2 * scale, ha="center", va="top", color=colors["failure"])

    r_center = layout["layer_x"][2] + layout["layer_width"] / 2.0
    y_center = layout["layer_x"][3] + layout["layer_width"] / 2.0
    guide_y = py + ph + 0.022
    ax.plot([r_center, r_center], [layout["layer_y"], guide_y], color=colors["guide"], linewidth=0.65 * scale)
    ax.plot([y_center, y_center], [layout["layer_y"], guide_y], color=colors["guide"], linewidth=0.65 * scale)
    ax.plot([r_center, y_center], [guide_y, guide_y], color=colors["guide"], linewidth=0.65 * scale)

    ax.text(0.5, 0.018, definition["footnote"], fontsize=6.4 * scale, ha="center", va="bottom", color=colors["muted_text"])
    fig.subplots_adjust(left=0.008, right=0.992, top=0.985, bottom=0.015)
    return fig, arrows


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


def run_qa(
    definition: dict[str, object],
    definition_path: Path,
    outputs: list[Path],
    reduced_png: Path,
    arrow_pairs: list[tuple[float, float]],
    report_path: Path,
    png_dpi: int,
) -> dict[str, object]:
    checks: list[dict[str, object]] = []

    def check(name: str, actual: object, expected: object, passed: bool) -> None:
        checks.append({"check": name, "actual": actual, "expected": expected, "passed": bool(passed)})

    layer_titles = [layer["title"] for layer in definition["layers"]]
    check("generic four-layer structure", layer_titles, ["Nominal intervention", "Executable controller logic", "Realized logged intervention", "Outcome"], layer_titles == ["Nominal intervention", "Executable controller logic", "Realized logged intervention", "Outcome"])
    interface_labels = [item["label"] for item in definition["interfaces"]]
    check("three required interface labels", interface_labels, ["Semantic fidelity", "Runtime fidelity", "Outcome-window exposure"], interface_labels == ["Semantic fidelity", "Runtime fidelity", "Outcome-window exposure"])
    check("all arrows left-to-right", arrow_pairs, "x_end > x_start for every arrow", all(end > start for start, end in arrow_pairs))
    layout = normalized_layout(definition)
    boxes = [(x, x + layout["layer_width"]) for x in layout["layer_x"]] + [(layout["final_x"], layout["final_x"] + layout["final_width"])]
    check("main boxes within normalized canvas", boxes, "0 <= left < right <= 1", all(0 <= left < right <= 1 for left, right in boxes))
    check("main boxes do not overlap", boxes, "strictly separated", all(boxes[index][1] < boxes[index + 1][0] for index in range(len(boxes) - 1)))
    check("double-column width", FULL_WIDTH_MM, 190.0, FULL_WIDTH_MM == 190.0)
    check("reduced preview width", REDUCED_WIDTH_MM, 90.0, REDUCED_WIDTH_MM == 90.0)
    check("PDF/SVG/PNG outputs exist", [str(path) for path in outputs], "all files non-empty", all(path.is_file() and path.stat().st_size > 1000 for path in outputs))
    svg_text = outputs[1].read_text(encoding="utf-8")
    check("SVG retains editable text", "<text" in svg_text, True, "<text" in svg_text)
    full_png = png_size_and_dpi(outputs[2])
    reduced_info = png_size_and_dpi(reduced_png)
    check("full PNG resolution", full_png, f">= {png_dpi - 1} dpi", full_png[2] >= png_dpi - 1.0 and full_png[3] >= png_dpi - 1.0)
    expected_reduced_width_px = round(REDUCED_WIDTH_MM / 25.4 * png_dpi)
    relative_width_error = abs(reduced_info[0] - expected_reduced_width_px) / expected_reduced_width_px
    check("90-mm tight-crop equivalent width", reduced_info[0], f"{expected_reduced_width_px} px within 1%", relative_width_error <= 0.01)
    check("90-mm PNG resolution", reduced_info[2:4], f">= {png_dpi - 1} dpi", reduced_info[2] >= png_dpi - 1.0 and reduced_info[3] >= png_dpi - 1.0)
    smallest_source_font_pt = 5.55
    effective_reduced_font_px = smallest_source_font_pt * (REDUCED_WIDTH_MM / FULL_WIDTH_MM) * png_dpi / 72.0
    check("90-mm text raster readability", round(effective_reduced_font_px, 1), ">= 18 px minimum predicted glyph height", effective_reduced_font_px >= 18.0)
    check("PDF TrueType setting", matplotlib.rcParams["pdf.fonttype"], 42, matplotlib.rcParams["pdf.fonttype"] == 42)
    check("SVG live-text setting", matplotlib.rcParams["svg.fonttype"], "none", matplotlib.rcParams["svg.fonttype"] == "none")
    check("required impedance footnote", definition["footnote"], "mentions logged commands and independently measured physical impedance", "not equivalent to independently measured physical impedance" in definition["footnote"])

    report = {
        "figure": STEM,
        "status": "PASS" if all(item["passed"] for item in checks) else "FAIL",
        "definition_path": str(definition_path),
        "definition_sha256": sha256(definition_path),
        "full_width_mm": FULL_WIDTH_MM,
        "reduced_width_mm": REDUCED_WIDTH_MM,
        "generation_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "matplotlib_version": matplotlib.__version__,
        "checks": checks,
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    if report["status"] != "PASS":
        failed = [item for item in checks if not item["passed"]]
        raise RuntimeError(f"Figure 1 QA failed: {failed}")
    return report


def update_manifest(project_root: Path, definition_path: Path, outputs: list[Path]) -> None:
    publication_root = project_root / "19_publication_figures"
    manifest_path = publication_root / "figure_manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {"figures": []}

    def relative(path: Path) -> str:
        return str(path.resolve().relative_to(project_root.resolve())).replace("\\", "/")

    record = {
        "figure_name": STEM,
        "script_path": relative(Path(__file__)),
        "input_files": [{"path": relative(definition_path), "sha256": sha256(definition_path)}],
        "figure_source_data": {"path": relative(definition_path), "sha256": sha256(definition_path)},
        "output_paths": [relative(path) for path in outputs],
        "python_version": platform.python_version(),
        "matplotlib_version": matplotlib.__version__,
        "generation_timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    payload["figures"] = [item for item in payload.get("figures", []) if item.get("figure_name") != STEM]
    payload["figures"].append(record)
    payload["figures"] = sorted(payload["figures"], key=lambda item: item["figure_name"])
    manifest_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    args = parse_args()
    project_root = resolve_project_root(args.root)
    publication_root = project_root / "19_publication_figures"
    figure_dir = publication_root / "figures"
    source_dir = publication_root / "figure_source_data"
    definition_path = source_dir / "figure01_source_definition.json"
    report_path = publication_root / "figure01_qa_report.json"
    definition = json.loads(definition_path.read_text(encoding="utf-8"))
    figure_dir.mkdir(parents=True, exist_ok=True)
    set_style()

    full_figure, arrow_pairs = build_figure(definition, FULL_WIDTH_MM)
    pdf_path = figure_dir / f"{STEM}.pdf"
    svg_path = figure_dir / f"{STEM}.svg"
    png_path = figure_dir / f"{STEM}.png"
    full_figure.savefig(pdf_path, bbox_inches="tight", pad_inches=0.02)
    full_figure.savefig(svg_path, bbox_inches="tight", pad_inches=0.02)
    full_figure.savefig(png_path, dpi=args.dpi, bbox_inches="tight", pad_inches=0.02)
    plt.close(full_figure)

    reduced_figure, reduced_arrows = build_figure(definition, REDUCED_WIDTH_MM)
    reduced_png = figure_dir / f"{STEM}_90mm.png"
    reduced_figure.savefig(reduced_png, dpi=args.dpi, bbox_inches="tight", pad_inches=0.02)
    plt.close(reduced_figure)

    outputs = [pdf_path, svg_path, png_path, reduced_png]
    report = run_qa(definition, definition_path, outputs[:3], reduced_png, arrow_pairs + reduced_arrows, report_path, args.dpi)
    update_manifest(project_root, definition_path, outputs)
    print(f"Generated {STEM} at 190 mm and 90 mm-equivalent widths")
    print(f"QA: {report['status']} ({len(report['checks'])}/{len(report['checks'])} checks)")


if __name__ == "__main__":
    main()
