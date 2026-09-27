#!/usr/bin/env python3
"""Integrity checks for the frozen TEST-197 label-independent preparation."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.repo
    manifest = csv_rows(root / "data/manifests/heldout_test_197_final_cohort_manifest.csv")
    ledger = csv_rows(root / "results/heldout_test_197/screening_ledger.csv")
    if len(manifest) != 197 or len({row["generation_case_id"] for row in manifest}) != 197:
        raise SystemExit("manifest uniqueness/count check failed")
    if len(ledger) != 197 or {row["generation_case_id"] for row in ledger} != {row["generation_case_id"] for row in manifest}:
        raise SystemExit("screening ledger does not cover exactly the frozen manifest")
    if any(row["partition"] != "test" for row in manifest):
        raise SystemExit("non-test row in final cohort manifest")
    counts = {
        "test_partition_cases": 197,
        "historical_batch1_cases": sum(row["batch"].startswith("Batch1") for row in manifest),
        "remaining_batch2_cases": sum(row["batch"].startswith("Batch2") for row in manifest),
        "confirmed_c": sum(row["qc_status"] == "CONFIRMED_C" for row in manifest),
        "objective_language_exclusions": sum(row["qc_status"] != "CONFIRMED_C" for row in manifest),
        "stage_a_failures": sum(row["packet_status"] == "STAGE_A_FAILURE" for row in ledger),
        "successful_c_claim_bearing": sum(row["packet_status"] == "SUCCESSFUL_C_CLAIM_BEARING" for row in ledger),
        "replacements": sum(row["replacement_used"] == "true" for row in ledger),
    }
    expected = {"test_partition_cases": 197, "historical_batch1_cases": 50, "remaining_batch2_cases": 147, "confirmed_c": 188, "objective_language_exclusions": 9, "stage_a_failures": 20, "successful_c_claim_bearing": 168, "replacements": 0}
    if counts != expected:
        raise SystemExit(f"cohort counts failed: {counts}")

    batch2_meta = json.loads((root / "results/heldout_test_197/stage_a_batch2_stealth_space_bunny_alpha/run_metadata.json").read_text(encoding="utf-8"))
    batch1_meta = json.loads((root / "results/heldout_test_197/stage_a_batch1_historical/run_metadata.json").read_text(encoding="utf-8"))
    if (batch2_meta["provider_calls"], batch2_meta["successes"], batch2_meta["errors"], batch2_meta["automatic_retry"], batch2_meta["fallback_disabled"]) != (140, 126, 14, False, True):
        raise SystemExit("Batch2 Stage-A metadata mismatch")
    if (batch1_meta["provider_calls"], batch1_meta["successes"], batch1_meta["errors"]) != (50, 44, 6):
        raise SystemExit("historical Batch1 Stage-A metadata mismatch")
    batch2_requests = jsonl(root / "results/heldout_test_197/stage_a_batch2_stealth_space_bunny_alpha/request_metadata.jsonl")
    batch2_errors = jsonl(root / "results/heldout_test_197/stage_a_batch2_stealth_space_bunny_alpha/errors.jsonl")
    if len(batch2_requests) != 140 or len({row["generation_case_id"] for row in batch2_requests}) != 140 or len(batch2_errors) != 14:
        raise SystemExit("Stage-A request/error cardinality mismatch")

    packets = jsonl(root / "results/heldout_test_197/evidence_frozen_v1.jsonl")
    claims = jsonl(root / "results/heldout_test_197/focal_claims_frozen_v1.jsonl")
    execution = jsonl(root / "results/heldout_test_197/execution_batch2_results.jsonl")
    if len(packets) != 168 or len({row["item_id"] for row in packets}) != 168:
        raise SystemExit("final packet uniqueness/count check failed")
    if len(claims) != 170 or len(execution) != 126 or len({row["item_id"] for row in execution}) != 126:
        raise SystemExit("claim/execution count check failed")
    for packet in packets:
        if any(packet["compiler"][state]["status"] == "NOT_REPLAYED" for state in ("earlier", "later")):
            raise SystemExit(f"unreplayed compiler evidence: {packet['item_id']}")
        if any(test[state]["status"] == "NOT_REPLAYED" for test in packet["tests"] for state in ("earlier", "later")):
            raise SystemExit(f"unreplayed test evidence: {packet['item_id']}")
        if "lifecycle_label" in packet or "human_labels" in packet or "prediction" in packet:
            raise SystemExit(f"reference/model field in packet: {packet['item_id']}")
    package_files = {}
    for annotator in ("A01", "A02"):
        package = root / "annotation/heldout_test_197" / annotator
        names = sorted(path.name for path in package.iterdir() if path.is_file())
        if names != ["LIFECYCLE_RUBRIC_v2.md", f"RevGround_Annotator_{annotator}.html", "heldout_test197_evidence_frozen_v1.jsonl"]:
            raise SystemExit(f"isolated package file set mismatch: {annotator}: {names}")
        if sha256_file(package / "heldout_test197_evidence_frozen_v1.jsonl") != sha256_file(root / "results/heldout_test_197/evidence_frozen_v1.jsonl"):
            raise SystemExit(f"package packet mismatch: {annotator}")
        package_files[annotator] = names
    result = {
        "status": "PASS",
        "checks": {
            "manifest_197_unique_test_ids": True,
            "source_language_qc_counts": counts,
            "batch1_stage_a_calls_preserved": 50,
            "batch2_stage_a_calls": 140,
            "batch2_stage_a_failures_preserved": 14,
            "final_packet_rows": len(packets),
            "locked_docker_state_replays_batch2": len(execution) * 2,
            "all_final_packets_replayed": True,
            "A01_A02_identical_packet_bytes": True,
            "isolated_packages_contain_no_predictions_or_labels": True,
        },
        "hashes": {
            "final_cohort_manifest_sha256": sha256_file(root / "data/manifests/heldout_test_197_final_cohort_manifest.csv"),
            "final_packet_sha256": sha256_file(root / "results/heldout_test_197/evidence_frozen_v1.jsonl"),
            "claims_sha256": sha256_file(root / "results/heldout_test_197/focal_claims_frozen_v1.jsonl"),
            "batch2_execution_sha256": sha256_file(root / "results/heldout_test_197/execution_batch2_results.jsonl"),
        },
        "package_files": package_files,
    }
    out = root / "results/heldout_test_197/integrity_summary.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
