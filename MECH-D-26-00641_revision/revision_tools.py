"""Small deterministic utilities for the MECH-D-26-00641 revision workspace."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
from pathlib import Path


def copy_unique(pattern: str, destination: str) -> None:
    matches = sorted(Path.cwd().glob(pattern))
    if len(matches) != 1:
        raise SystemExit(f"Expected one match for {pattern!r}, found {len(matches)}")
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(matches[0], target)
    print(f"Copied {matches[0]} -> {target}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(root: str, output: str) -> None:
    base = Path(root).resolve()
    target = Path(output).resolve()
    rows = []
    for path in sorted(base.rglob("*")):
        if path.is_file() and path.resolve() != target:
            rows.append(f"{sha256(path)}  {path.relative_to(base).as_posix()}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} hashes to {target}")


def verify_manifest(root: str, manifest: str) -> None:
    base = Path(root).resolve()
    manifest_path = Path(manifest).resolve()
    checked = 0
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        path = base / Path(relative)
        if not path.is_file():
            raise SystemExit(f"Missing manifest file: {relative}")
        actual = sha256(path)
        if actual != expected:
            raise SystemExit(f"Hash mismatch: {relative}")
        checked += 1
    print(f"Verified {checked} files against {manifest_path}")


def show_slice(path: str, start: int, end: int) -> None:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    for number in range(max(1, start), min(end, len(lines)) + 1):
        print(f"{number:04d}: {lines[number - 1]}")


def make_read_only(root: str) -> None:
    base = Path(root)
    count = 0
    for path in base.rglob("*"):
        if path.is_file():
            os.chmod(path, 0o444)
            count += 1
    print(f"Marked {count} files read-only under {base}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    copy_parser = subparsers.add_parser("copy-unique")
    copy_parser.add_argument("pattern")
    copy_parser.add_argument("destination")

    manifest_parser = subparsers.add_parser("manifest")
    manifest_parser.add_argument("root")
    manifest_parser.add_argument("output")

    verify_parser = subparsers.add_parser("verify-manifest")
    verify_parser.add_argument("root")
    verify_parser.add_argument("manifest")

    slice_parser = subparsers.add_parser("slice")
    slice_parser.add_argument("path")
    slice_parser.add_argument("start", type=int)
    slice_parser.add_argument("end", type=int)

    readonly_parser = subparsers.add_parser("read-only")
    readonly_parser.add_argument("root")

    args = parser.parse_args()
    if args.command == "copy-unique":
        copy_unique(args.pattern, args.destination)
    elif args.command == "manifest":
        write_manifest(args.root, args.output)
    elif args.command == "slice":
        show_slice(args.path, args.start, args.end)
    elif args.command == "verify-manifest":
        verify_manifest(args.root, args.manifest)
    elif args.command == "read-only":
        make_read_only(args.root)


if __name__ == "__main__":
    main()
