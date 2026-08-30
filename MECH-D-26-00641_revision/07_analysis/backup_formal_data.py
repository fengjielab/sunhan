"""Create a verified, non-overwriting snapshot of formal raw data."""

from __future__ import annotations

import argparse
import hashlib
import shutil
from datetime import datetime
from pathlib import Path


def digest(path: Path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination_root", type=Path)
    args = parser.parse_args()
    source = args.source.resolve()
    destination_root = args.destination_root.resolve()
    if source == destination_root or source in destination_root.parents:
        raise SystemExit("Destination must not be inside the formal-data directory")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination = destination_root / f"MECH-D-26-00641_formal_{stamp}"
    if destination.exists():
        raise SystemExit(f"Refusing to overwrite {destination}")
    shutil.copytree(source, destination)
    rows = []
    for path in sorted(destination.rglob("*")):
        if path.is_file():
            rows.append(f"{digest(path)}  {path.relative_to(destination).as_posix()}")
    (destination / "SHA256SUMS.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"Backed up and hashed {len(rows)} files to {destination}")


if __name__ == "__main__":
    main()
