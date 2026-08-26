from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
BUNDLE = HERE.parents[1]
LOGIC = BUNDLE / "04_logic_and_qa" / "v5"
V4_VALIDATE = BUNDLE / "05_reproduction" / "v4" / "validate_v4.py"
V4_REPORT = BUNDLE / "04_logic_and_qa" / "v4" / "v4_validation_report.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    subprocess.run([sys.executable, str(V4_VALIDATE)], cwd=BUNDLE, check=True)
    frozen = json.loads(V4_REPORT.read_text(encoding="utf-8"))
    expected_hashes = json.loads((HERE / "baseline_hashes.json").read_text(encoding="utf-8"))
    baseline = []
    for relative, expected in expected_hashes.items():
        observed = sha256(BUNDLE / relative)
        baseline.append({"path": relative, "expected": expected, "observed": observed, "passed": int(observed == expected)})

    case = frozen["stage_a_stage_b_cases"]
    real = frozen["real_case"]
    checks = {
        "v4_validation_pass": frozen["status"] == "PASS",
        "controlled_cases_12_of_12": case["n_cases"] == 12 and case["exact_matches"] == 12,
        "provenance_180": real["provenance_valid_trials"] == 180,
        "mode_counts": real["mode_counts"] == {"A": 45, "E": 45, "F": 45, "G": 45},
        "g_replay_rows_12196": real["g_replay"]["n_replayed_update_rows"] == 12196,
        "e_exposure_39_2_4": real["exposure_counts"]["E"] == {"full": 39, "partial": 2, "zero": 4},
        "f_c_to_r_not_evaluable": real["configuration_states"]["F"]["c_to_r"] == "not_evaluable",
        "v4_baseline_unchanged": all(item["passed"] for item in baseline),
    }
    report = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "baseline": baseline,
        "source_validation": str(V4_REPORT.relative_to(BUNDLE)).replace("\\", "/"),
        "scientific_interface_change": "none",
    }
    LOGIC.mkdir(parents=True, exist_ok=True)
    (LOGIC / "v5_validation_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] != "PASS":
        raise SystemExit("v5 validation failed")


if __name__ == "__main__":
    main()
