"""Shared schema, frozen-QA, path, source-data, and manifest utilities."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import matplotlib
import numpy as np
import pandas as pd


MODE_ORDER = ["A", "G", "E", "F"]
WINDOW_DURATION_S = 0.8


class FrozenQAError(RuntimeError):
    """Raised when a frozen result no longer matches the clean outputs."""


def parse_root_args(description: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="正宫 project root, or a repository root containing my_test/正宫",
    )
    parser.add_argument("--dpi", type=int, default=600, help="PNG resolution (minimum 600).")
    args = parser.parse_args()
    if args.dpi < 600:
        parser.error("--dpi must be at least 600 for publication PNG output")
    return args


def resolve_project_root(root: Path | None, script_file: str) -> Path:
    if root is None:
        candidate = Path(script_file).resolve().parents[2]
    else:
        candidate = root.resolve()
    if (candidate / "03_clean_analysis").is_dir():
        return candidate
    nested = candidate / "my_test" / "正宫"
    if (nested / "03_clean_analysis").is_dir():
        return nested
    raise FileNotFoundError(
        f"Could not locate 03_clean_analysis below --root={candidate}. "
        "Pass the 正宫 directory or the repository root."
    )


def output_paths(project_root: Path) -> tuple[Path, Path, Path]:
    publication_root = project_root / "19_publication_figures"
    return publication_root, publication_root / "figures", publication_root / "figure_source_data"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_clean_csv(clean_dir: Path, filename: str, required_columns: Iterable[str]) -> pd.DataFrame:
    path = clean_dir / filename
    if not path.is_file():
        raise FileNotFoundError(f"Required frozen clean output is missing: {path}")
    frame = pd.read_csv(path)
    missing = [column for column in required_columns if column not in frame.columns]
    print(f"SCHEMA {filename}: {frame.shape[0]} rows x {frame.shape[1]} columns")
    mapping = {column: column if column in frame.columns else None for column in required_columns}
    for canonical, actual in mapping.items():
        print(f"  {canonical} -> {actual}")
    if missing:
        raise KeyError(
            f"Schema mismatch in {filename}; required columns absent: {missing}. "
            f"Actual columns: {list(frame.columns)}"
        )
    return frame


def classify_exposure(values: pd.Series) -> pd.Series:
    array = values.to_numpy(dtype=float)
    labels = np.full(len(array), "Partial", dtype=object)
    labels[np.isclose(array, 0.0, atol=1e-12)] = "Zero"
    labels[np.isclose(array, 1.0, atol=1e-12)] = "Full"
    return pd.Series(labels, index=values.index, dtype="object")


def _check(report: list[dict[str, object]], name: str, actual: object, expected: object, passed: bool) -> None:
    report.append({"check": name, "actual": actual, "expected": expected, "passed": bool(passed)})


def run_frozen_qa(clean_dir: Path, report_path: Path | None = None) -> dict[str, object]:
    """Validate every user-specified frozen figure gate before plotting."""
    manifest = read_clean_csv(clean_dir, "master_trial_manifest.csv", ["included_main_clean"])
    fidelity = read_clean_csv(
        clean_dir,
        "trial_level_fidelity_metrics.csv",
        [
            "record_id",
            "mode_code",
            "pre_contact_activation",
            "executable_logic_compliance",
            "nominal_activation_timing_compliance",
            "contact_to_adaptation_latency_s",
            "activation_timing_error_s",
            "vision_configuration_outcome_window_overlap",
            "adaptation_outcome_window_overlap",
            "outcome_window_overlap",
        ],
    )
    checks: list[dict[str, object]] = []
    selected = int(manifest["included_main_clean"].sum())
    _check(checks, "total selected trials", selected, 180, selected == 180)
    counts = fidelity.groupby("mode_code", sort=False).size().to_dict()
    expected_counts = {"A": 45, "G": 45, "E": 45, "F": 45}
    _check(checks, "A/G/E/F counts", counts, expected_counts, counts == expected_counts)

    g = fidelity[fidelity["mode_code"].eq("G")]
    g_pre = int(g["pre_contact_activation"].sum())
    g_exec = int(g["executable_logic_compliance"].sum())
    _check(checks, "G pre-contact activation", g_pre, 43, g_pre == 43)
    _check(checks, "G executable compliance", g_exec, 45, g_exec == 45)

    f = fidelity[fidelity["mode_code"].eq("F")]
    f_compliant = int(f["nominal_activation_timing_compliance"].sum())
    f_latency = float(f["contact_to_adaptation_latency_s"].median())
    f_error = float(f["activation_timing_error_s"].median())
    _check(checks, "F nominal +0.20-s compliant", f_compliant, 3, f_compliant == 3)
    _check(checks, "F median contact-to-activation", f_latency, 0.0533, round(f_latency, 4) == 0.0533)
    _check(checks, "F median timing error", f_error, -0.1467, round(f_error, 4) == -0.1467)

    exposure_specs = [
        ("E vision exposure", "E", "vision_configuration_outcome_window_overlap", {"Full": 39, "Partial": 2, "Zero": 4}),
        ("F vision exposure", "F", "vision_configuration_outcome_window_overlap", {"Full": 42, "Partial": 0, "Zero": 3}),
        ("F adaptation exposure", "F", "adaptation_outcome_window_overlap", {"Full": 35, "Partial": 7, "Zero": 3}),
        ("F joint exposure", "F", "outcome_window_overlap", {"Full": 35, "Partial": 7, "Zero": 3}),
    ]
    for name, mode, column, expected in exposure_specs:
        labels = classify_exposure(fidelity.loc[fidelity["mode_code"].eq(mode), column])
        actual = {level: int((labels == level).sum()) for level in ["Full", "Partial", "Zero"]}
        _check(checks, name, actual, expected, actual == expected)

    passed = all(bool(item["passed"]) for item in checks)
    report = {
        "status": "PASS" if passed else "FAIL",
        "clean_directory": str(clean_dir),
        "checks": checks,
    }
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    if not passed:
        print("FROZEN FIGURE QA FAILED — STOPPING BEFORE FIGURE GENERATION", file=sys.stderr)
        for item in checks:
            if not item["passed"]:
                print(
                    f"  {item['check']}: actual={item['actual']!r}; expected={item['expected']!r}",
                    file=sys.stderr,
                )
        raise FrozenQAError("Frozen clean outputs do not match the manuscript values")
    print("FROZEN FIGURE QA: PASS")
    return report


def write_source_csv(frame: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, lineterminator="\n")
    return path


def write_schema_mapping(publication_root: Path, mappings: dict[str, list[str]]) -> Path:
    payload = {
        filename: {canonical: canonical for canonical in columns}
        for filename, columns in sorted(mappings.items())
    }
    path = publication_root / "schema_mapping.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def record_manifest(
    publication_root: Path,
    project_root: Path,
    figure_name: str,
    script_path: Path,
    input_paths: Iterable[Path],
    source_data_path: Path,
    output_paths_list: Iterable[Path],
) -> Path:
    manifest_path = publication_root / "figure_manifest.json"
    if manifest_path.exists():
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        payload = {"figures": []}

    def relative(path: Path) -> str:
        try:
            return str(path.resolve().relative_to(project_root.resolve())).replace("\\", "/")
        except ValueError:
            return str(path.resolve())

    record = {
        "figure_name": figure_name,
        "script_path": relative(script_path),
        "input_files": [
            {"path": relative(path), "sha256": sha256(path)} for path in sorted(set(input_paths), key=lambda p: str(p))
        ],
        "figure_source_data": {"path": relative(source_data_path), "sha256": sha256(source_data_path)},
        "output_paths": [relative(path) for path in output_paths_list],
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
        "matplotlib_version": matplotlib.__version__,
        "generation_timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    payload["figures"] = [item for item in payload.get("figures", []) if item.get("figure_name") != figure_name]
    payload["figures"].append(record)
    payload["figures"] = sorted(payload["figures"], key=lambda item: item["figure_name"])
    manifest_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest_path


def prepare_run(args: argparse.Namespace, script_file: str) -> tuple[Path, Path, Path, Path]:
    project_root = resolve_project_root(args.root, script_file)
    publication_root, figures_dir, source_dir = output_paths(project_root)
    publication_root.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    source_dir.mkdir(parents=True, exist_ok=True)
    clean_dir = project_root / "03_clean_analysis"
    run_frozen_qa(clean_dir, publication_root / "figure_qa_report.json")
    return project_root, clean_dir, figures_dir, source_dir
