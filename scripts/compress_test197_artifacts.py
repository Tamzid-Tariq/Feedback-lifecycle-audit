#!/usr/bin/env python3
"""Create lossless compressed mirrors of the largest TEST-197 artifacts."""
from __future__ import annotations

import argparse
import gzip
import shutil
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.repo
    names = [
        "results/heldout_test_197/evidence_frozen_v1.jsonl",
        "results/heldout_test_197/execution_batch2_results.jsonl",
    ]
    outputs = []
    for relative in names:
        source = root / relative
        target = source.with_suffix(source.suffix + ".gz")
        with source.open("rb") as src, gzip.open(target, "wb", compresslevel=6) as dst:
            shutil.copyfileobj(src, dst, length=1024 * 1024)
        outputs.append({"source": relative, "compressed": str(target.relative_to(root)), "bytes": target.stat().st_size})
    print(outputs)


if __name__ == "__main__":
    main()
