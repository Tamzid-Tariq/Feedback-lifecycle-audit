#!/usr/bin/env python3
"""Write a deterministic SHA-256 inventory for TEST-197 preparation artifacts."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.repo
    roots = [root / "data/manifests/heldout_test_197_final_cohort_manifest.csv", root / "data/manifests/heldout_test_197_final_cohort_manifest.json", root / "data/manifests/heldout_test_197_final_cohort_manifest.SHA256SUMS", root / "data/manifests/archive/heldout_natural50_manifest_batch1.json"]
    files = [path for path in roots if path.is_file()]
    files += sorted(path for base in (root / "results/heldout_test_197", root / "annotation/heldout_test_197") for path in base.rglob("*") if path.is_file() and path.name != "SHA256SUMS.txt")
    seen: set[Path] = set()
    lines: list[str] = []
    for path in sorted(files):
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        lines.append(f"{digest(path)}  {path.relative_to(root).as_posix()}")
    out = root / "results/heldout_test_197/SHA256SUMS.txt"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(lines)} files hashed; {out}")


if __name__ == "__main__":
    main()
