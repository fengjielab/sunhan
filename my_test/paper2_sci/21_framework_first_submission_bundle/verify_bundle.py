#!/usr/bin/env python3
"""Write or verify the consolidated bundle SHA-256 manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "bundle_manifest_sha256.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def included_files() -> list[Path]:
    return sorted(
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and path != MANIFEST
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
    )


def snapshot() -> dict[str, object]:
    files = included_files()
    records = {
        path.relative_to(ROOT).as_posix(): {
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in files
    }
    return {
        "algorithm": "SHA-256",
        "file_count": len(records),
        "total_bytes": sum(record["bytes"] for record in records.values()),
        "files": records,
    }


def write_manifest() -> None:
    payload = snapshot()
    MANIFEST.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"status": "WRITTEN", "file_count": payload["file_count"], "total_bytes": payload["total_bytes"]}, indent=2))


def verify_manifest() -> None:
    if not MANIFEST.is_file():
        raise SystemExit("Manifest is missing; run: python verify_bundle.py write")
    expected = json.loads(MANIFEST.read_text(encoding="utf-8"))
    actual = snapshot()
    expected_files = expected["files"]
    actual_files = actual["files"]
    missing = sorted(set(expected_files) - set(actual_files))
    unexpected = sorted(set(actual_files) - set(expected_files))
    changed = sorted(
        name for name in set(expected_files) & set(actual_files)
        if expected_files[name] != actual_files[name]
    )
    status = "PASS" if not missing and not unexpected and not changed else "FAIL"
    report = {
        "status": status,
        "file_count": actual["file_count"],
        "missing": missing,
        "unexpected": unexpected,
        "changed": changed,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if status != "PASS":
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("write", "verify"))
    args = parser.parse_args()
    if args.action == "write":
        write_manifest()
    else:
        verify_manifest()


if __name__ == "__main__":
    main()
