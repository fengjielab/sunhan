#!/usr/bin/env python3
"""Run the verified, manuscript-aligned core reproduction checks.

This entry point deliberately excludes legacy exploratory scripts.  It checks
the frozen archive and reproduces the primary C--E bootstrap summaries used in
the current manuscript.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable


def run(relative: str) -> None:
    print(f"\n>>> {relative}")
    subprocess.run([PYTHON, str(ROOT / relative)], check=True, cwd=ROOT)


def main() -> None:
    run("verify_bundle.py")
    run("07_analysis_and_figure_code/bootstrap_ci_ce.py")
    print("\nPASS: core manuscript-aligned checks completed.")


if __name__ == "__main__":
    main()
