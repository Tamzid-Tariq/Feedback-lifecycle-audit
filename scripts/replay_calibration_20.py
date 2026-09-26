#!/usr/bin/env python3
"""Replay the usable Calibration-20 packets in the locked C runner.

The four Stage-A failures are intentionally absent from the annotation packet
and remain represented by the existing Stage-A error/eligibility artifacts.
This script reuses the same replay functions and runner settings as the
Development-50 workflow, but accepts CAL_### packet IDs.
"""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from replay_development_50 import canonical, image_id, replay_record
from utils.safe_execute_c import IMAGE, temporary_directory


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "annotation" / "calibration_20" / "calibration_20_evidence_frozen_v1.jsonl"
OUTPUT = ROOT / "results" / "calibration_20" / "runs" / "calibration_20_execution_results.jsonl"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=INPUT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--image", default=IMAGE)
    parser.add_argument("--state-workers", type=int, default=2)
    args = parser.parse_args()
    if args.state_workers < 1 or args.state_workers > 2:
        raise SystemExit("--state-workers must be between 1 and 2")
    records = read_jsonl(args.input)
    if len(records) != 16 or any(not str(record.get("item_id", "")).startswith("CAL_") for record in records):
        raise SystemExit("Expected the 16 usable CAL_### packets")
    if args.output.exists():
        raise SystemExit(f"Output already exists; refusing to overwrite: {args.output}")
    resolved_image_id = image_id(args.image)
    results: list[dict] = []
    with temporary_directory(prefix="revground_calibration_replay_") as directory:
        work_dir = Path(directory)

        def one(record: dict) -> dict:
            return replay_record(record, work_dir, args.image, resolved_image_id)

        with ThreadPoolExecutor(max_workers=args.state_workers) as executor:
            for index, result in enumerate(executor.map(one, records), start=1):
                print(f"[{index}/{len(records)}] {result['item_id']}", flush=True)
                results.append(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(canonical(result) + "\n" for result in results), encoding="utf-8", newline="\n")
    print(canonical({"status": "RUN_COMPLETE", "records": len(results), "output": str(args.output), "runner_image": args.image, "runner_image_id": resolved_image_id}))


if __name__ == "__main__":
    main()
