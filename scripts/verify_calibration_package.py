#!/usr/bin/env python3
"""Verify and record the blinded Calibration-20 package build."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    manifest_path = ROOT / "data" / "manifests" / "calibration_20_manifest.csv"
    qc_path = ROOT / "data" / "qc" / "language_qc_summary.json"
    stage_dir = ROOT / "results" / "calibration_20" / "stage_a_stealth_space_bunny_alpha"
    claims_path = ROOT / "results" / "calibration_20" / "frozen_focal_claims.jsonl"
    packets_path = ROOT / "annotation" / "calibration_20" / "calibration_20_evidence_frozen_v1.jsonl"
    execution_path = ROOT / "results" / "calibration_20" / "runs" / "calibration_20_execution_results.jsonl"
    manifest = list(csv.DictReader(manifest_path.open(encoding="utf-8-sig", newline="")))
    qc = json.loads(qc_path.read_text(encoding="utf-8"))
    hints = read_jsonl(stage_dir / "raw_hints.jsonl")
    errors = read_jsonl(stage_dir / "errors.jsonl")
    claims = read_jsonl(claims_path)
    packets = read_jsonl(packets_path)
    execution = read_jsonl(execution_path)
    if len(manifest) != 20 or {row["partition"] for row in manifest} != {"validation"}:
        raise SystemExit("Calibration manifest is not the frozen validation-20 manifest")
    if not qc["calibration"]["all_20_confirmed_c"]:
        raise SystemExit("Calibration language QC is not 20/20 CONFIRMED_C")
    if len(packets) != len(claims) or len(packets) != len(execution):
        raise SystemExit("Claims, packets, and execution rows do not align")
    packet_by_id = {row["item_id"]: row for row in packets}
    execution_by_id = {row["item_id"]: row for row in execution}
    if set(packet_by_id) != set(execution_by_id):
        raise SystemExit("Packet/execution item IDs differ")
    dev_first = read_jsonl(ROOT / "annotation" / "development_50" / "development_50_evidence_frozen_v1.jsonl")[0]
    packet_keys_match = set(packets[0]) == set(dev_first)
    compiler_counts = Counter(packet["compiler"][state]["status"] for packet in packets for state in ("earlier", "later"))
    test_counts = Counter(test[state]["status"] for packet in packets for test in packet["tests"] for state in ("earlier", "later"))
    forbidden = {"model", "model_requested", "model_returned", "provider", "provider_raw_response", "predicted_label", "system_prediction", "lifecycle_label", "original_validity", "target_state_t1"}
    packet_text = packets_path.read_text(encoding="utf-8")
    package_entries = sorted(path.name for path in (ROOT / "annotation" / "calibration_20").iterdir())
    if set(package_entries) != {"LIFECYCLE_RUBRIC_v2.md", "calibration_20_evidence_frozen_v1.jsonl", "tools"}:
        raise SystemExit(f"Unexpected calibration package entries: {package_entries}")
    if forbidden & set().union(*(set(row) for row in packets)) or any(value in packet_text for value in ("provider_raw_response", "predicted_label", "system_prediction")):
        raise SystemExit("Model/prediction fields found in blinded packet")
    if any(status == "NOT_REPLAYED" for status in compiler_counts) or any(status == "NOT_REPLAYED" for status in test_counts):
        raise SystemExit("Execution replay remains incomplete")
    build = {
        "status": "COMPLETE_BLINDED_CALIBRATION_PACKAGE",
        "language_qc": {"summary": "data/qc/language_qc_summary.json", "calibration_confirmed_c": 20},
        "manifest": {"path": str(manifest_path.relative_to(ROOT)), "n": len(manifest), "partition": "validation", "seed": 20260926, "sha256": sha256_file(manifest_path)},
        "stage_a": {"requested": 20, "usable_hints": sum(row.get("status") == "success" for row in hints), "failures_preserved": len(errors), "raw_hint_records": len(hints), "raw_hints_sha256": sha256_file(stage_dir / "raw_hints.jsonl"), "errors_sha256": sha256_file(stage_dir / "errors.jsonl")},
        "focal_claims": {"frozen": len(claims), "path": str(claims_path.relative_to(ROOT)), "sha256": sha256_file(claims_path)},
        "evidence_packets": {"rows": len(packets), "path": str(packets_path.relative_to(ROOT)), "sha256": sha256_file(packets_path), "same_top_level_schema_as_development": packet_keys_match, "compiler_status_counts": dict(compiler_counts), "test_status_counts": dict(test_counts)},
        "execution_replay": {"rows": len(execution), "path": str(execution_path.relative_to(ROOT)), "sha256": sha256_file(execution_path), "runner_image": execution[0]["runner_image"], "runner_image_id": execution[0]["runner_image_id"]},
        "annotation_package": {"path": "annotation/calibration_20", "entries": package_entries, "a01_a02_isolated": True, "model_predictions_included": False},
        "stage_a_failures_remain_outside_annotation_packet": True,
        "qwen_b_c_run": "not_run",
    }
    output = ROOT / "results" / "calibration_20" / "calibration_20_build_manifest.json"
    output.write_text(json.dumps(build, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(build, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
