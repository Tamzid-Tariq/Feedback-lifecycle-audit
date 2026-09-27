#!/usr/bin/env python3
"""Freeze the full TEST-197 cohort using source-only QC and Batch-1 provenance."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


FIELDS = [
    "generation_case_id", "transition_id", "trajectory_id", "participant_id_hash",
    "problem_id", "problem_family_id", "submission_id_t", "attempt_t", "partition",
    "selection_order", "batch", "historical_batch1", "qc_status",
    "detected_source_language", "qc_reason", "eligible_final_c_cohort", "stage_a_required",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--historical-batch1", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    historical = json.loads(args.historical_batch1.resolve().read_text(encoding="utf-8"))
    batch1_ids = list(historical["selected_item_ids"])
    if historical.get("source_partition") != "test" or historical.get("n") != 50:
        raise SystemExit("Historical Batch 1 manifest is not the frozen TEST-50 manifest")
    if len(batch1_ids) != 50 or len(set(batch1_ids)) != 50:
        raise SystemExit("Historical Batch 1 IDs are not unique 50-case selection")

    source_path = repo / "data" / "manifests" / "final_test_197_manifest.csv"
    qc_path = repo / "data" / "qc" / "language_qc_all_strict_c.csv"
    source_rows = read_csv(source_path)
    qc_rows = {row["transition_id"]: row for row in read_csv(qc_path) if row.get("partition") == "test"}
    if len(source_rows) != 197 or len({row["generation_case_id"] for row in source_rows}) != 197:
        raise SystemExit("Final TEST manifest must contain 197 unique cases")
    if set(batch1_ids) - {row["generation_case_id"] for row in source_rows}:
        raise SystemExit("Historical Batch 1 contains an ID absent from TEST-197")
    if len(qc_rows) != 197:
        raise SystemExit(f"Expected source-only QC for 197 TEST rows, found {len(qc_rows)}")

    rows: list[dict[str, Any]] = []
    for source in source_rows:
        item_id = source["generation_case_id"]
        qc = qc_rows.get(source["transition_id"])
        if qc is None:
            raise SystemExit(f"Missing QC row for {item_id}")
        batch1 = item_id in batch1_ids
        eligible = qc["qc_status"] == "CONFIRMED_C"
        rows.append({
            "generation_case_id": item_id,
            "transition_id": source["transition_id"],
            "trajectory_id": source["trajectory_id"],
            "participant_id_hash": source["participant_id_hash"],
            "problem_id": source["problem_id"],
            "problem_family_id": source["problem_family_id"],
            "submission_id_t": source["submission_id_t"],
            "attempt_t": source["attempt_t"],
            "partition": source["partition"],
            "selection_order": source["selection_order"],
            "batch": "Batch1_historical_TEST50" if batch1 else "Batch2_remaining_TEST197",
            "historical_batch1": "true" if batch1 else "false",
            "qc_status": qc["qc_status"],
            "detected_source_language": qc["detected_source_language"],
            "qc_reason": qc["reason"],
            "eligible_final_c_cohort": "true" if eligible else "false",
            "stage_a_required": "true" if eligible and not batch1 else "false",
        })

    rows.sort(key=lambda row: int(row["selection_order"]))
    counts = {
        "test_partition_cases": len(rows),
        "historical_batch1_cases": sum(row["historical_batch1"] == "true" for row in rows),
        "remaining_batch2_cases": sum(row["historical_batch1"] == "false" for row in rows),
        "confirmed_c": sum(row["qc_status"] == "CONFIRMED_C" for row in rows),
        "objective_exclusions": sum(row["qc_status"] != "CONFIRMED_C" for row in rows),
        "batch1_confirmed_c": sum(row["historical_batch1"] == "true" and row["eligible_final_c_cohort"] == "true" for row in rows),
        "batch1_objective_exclusions": sum(row["historical_batch1"] == "true" and row["eligible_final_c_cohort"] == "false" for row in rows),
        "remaining_eligible_stage_a_cases": sum(row["stage_a_required"] == "true" for row in rows),
    }
    expected = {"test_partition_cases": 197, "historical_batch1_cases": 50, "remaining_batch2_cases": 147, "confirmed_c": 188, "objective_exclusions": 9, "batch1_confirmed_c": 48, "batch1_objective_exclusions": 2, "remaining_eligible_stage_a_cases": 140}
    if counts != expected:
        raise SystemExit(f"Unexpected TEST-197 counts: {counts}")

    out_dir = repo / "data" / "manifests"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "heldout_test_197_final_cohort_manifest.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "protocol_amendment_id": "test197_full_eligible_cohort_v1",
        "status": "FROZEN_BEFORE_ADDITIONAL_HELDOUT_LABELS_OR_MODEL_RESULTS",
        "source_partition": "test",
        "source_manifest": "data/manifests/final_test_197_manifest.csv",
        "source_manifest_sha256": sha256_file(source_path),
        "historical_batch1_manifest": "data/manifests/archive/heldout_natural50_manifest_batch1.json",
        "historical_batch1_manifest_sha256": sha256_file(args.historical_batch1.resolve()),
        "final_manifest": "data/manifests/heldout_test_197_final_cohort_manifest.csv",
        "selection_rule": "census of the existing 197-case TEST partition; no sampling, deletion, replacement, or label-based filtering",
        "created_before_labels": True,
        "labels_read_during_selection": False,
        "counts": counts,
        "qc": {"rule": "source syntax only from code_t and code_t1", "qc_artifact": "data/qc/language_qc_all_strict_c.csv", "qc_sha256": sha256_file(qc_path)},
        "stage_a_policy": {"model": "stealth/space-bunny-alpha", "max_tokens": 512, "timeout_seconds": 90, "fallback": False, "automatic_retry": False, "prompt_sha256": "3916584eb94f1ffa7749bbc94a2b51e1584a9d2eca97d1f197780ee8d956eaee", "remaining_calls_required": 140},
        "claim_extraction_rule": "first_explicit_diagnostic_assertion_v1",
        "replacement_policy": "No replacement; all objective exclusions and Stage-A failures remain in the final ledger.",
        "model_evaluator_calls_authorized": False,
    }
    summary_path = out_dir / "heldout_test_197_final_cohort_manifest.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    checksum_path = out_dir / "heldout_test_197_final_cohort_manifest.SHA256SUMS"
    checksum_path.write_text(f"{sha256_file(manifest_path)}  {manifest_path.name}\n{sha256_file(summary_path)}  {summary_path.name}\n", encoding="utf-8")
    print(json.dumps({"status": summary["status"], "counts": counts, "manifest_sha256": sha256_file(manifest_path), "summary_sha256": sha256_file(summary_path)}, indent=2))


if __name__ == "__main__":
    main()
