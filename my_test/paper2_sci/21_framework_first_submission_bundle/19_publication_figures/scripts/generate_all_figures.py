#!/usr/bin/env python3
"""Run the complete publication-figure suite in numerical order."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


SCRIPTS = [
    "fig01_framework.py",
    "fig02_system_lineage.py",
    "fig03_fidelity_results.py",
    "fig04_participant_outcomes.py",
    "fig05_contact_trajectories.py",
    "fig06_participant_lopo.py",
    "fig07_lineage_examples.py",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--dpi", type=int, default=600)
    args = parser.parse_args()
    script_dir = Path(__file__).resolve().parent
    for name in SCRIPTS:
        command = [sys.executable, str(script_dir / name), "--dpi", str(args.dpi)]
        if args.root is not None:
            command.extend(["--root", str(args.root.resolve())])
        print(f"RUNNING: {' '.join(command)}", flush=True)
        subprocess.run(command, check=True)
    print("All publication figures generated successfully.")


if __name__ == "__main__":
    main()
