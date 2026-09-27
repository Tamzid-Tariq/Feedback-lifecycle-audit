#!/usr/bin/env python3
"""Build the post-amendment Stage-A input without inspecting future fields."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cohort-manifest", type=Path, required=True)
    parser.add_argument("--source-input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    with args.cohort_manifest.open(encoding="utf-8", newline="") as handle:
        cohort_rows = list(csv.DictReader(handle))
    target_ids = {
        row["generation_case_id"]
        for row in cohort_rows
        if row["batch"] == "Batch2_remaining_TEST197"
        and row["eligible_final_c_cohort"].lower() == "true"
    }
    if len(target_ids) != 140:
        raise SystemExit(f"expected 140 remaining eligible IDs, found {len(target_ids)}")

    source_rows: dict[str, dict[str, Any]] = {}
    with args.source_input.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                case_id = row["generation_case_id"]
                if case_id in source_rows:
                    raise SystemExit(f"duplicate source case: {case_id}")
                source_rows[case_id] = row

    missing = target_ids - source_rows.keys()
    if missing:
        raise SystemExit(f"missing source rows: {sorted(missing)[:5]}")
    selected = [source_rows[item_id] for item_id in sorted(target_ids)]
    if any(row.get("partition") != "test" for row in selected):
        raise SystemExit("non-test row in Stage-A input")
    if any(row.get("language") != "C" for row in selected):
        raise SystemExit("non-C declared row in eligible Stage-A input")
    if any("lifecycle_label" in row or "human_labels" in row for row in selected):
        raise SystemExit("reference field present in Stage-A input")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(canonical(row) + "\n" for row in selected)
    args.output.write_text(payload, encoding="utf-8", newline="\n")
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    print(canonical({
        "status": "READY",
        "records": len(selected),
        "output": str(args.output),
        "sha256": digest,
        "source_rows_available": len(source_rows),
    }))


if __name__ == "__main__":
    main()
