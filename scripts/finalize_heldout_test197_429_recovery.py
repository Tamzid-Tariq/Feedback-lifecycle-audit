#!/usr/bin/env python3
"""Finalize and audit the one-attempt held-out TEST-197 HTTP-429 recovery."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "results" / "heldout_test_197" / "evaluations" / "deepseek_v4_1_flash"
PRIMARY = {
    "B": BASE / "condition_B",
    "C": BASE / "condition_C",
}
RECOVERY = BASE / "RECOVERY_429_V1"
SETTINGS = {
    "model": "deepseek/deepseek-v4.1-flash",
    "endpoint": "https://openrouter.ai/api/v1/chat/completions",
    "max_tokens": 16000,
    "temperature": 0,
    "timeout_seconds": 360,
    "sleep_seconds_between_requests": 20,
    "post_429_sleep_seconds": 90,
    "automatic_retry": False,
    "fallback_disabled": True,
}


def jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def primary_429_ids(condition: str) -> set[str]:
    rows = jsonl(PRIMARY[condition] / "errors.jsonl")
    return {row["item_id"] for row in rows if row.get("http_status") == 429}


def check_primary_unchanged(condition: str) -> dict[str, str]:
    directory = PRIMARY[condition]
    sums = directory / "PRIMARY_FIRST_ATTEMPT_SHA256SUMS.txt"
    expected: dict[str, str] = {}
    for line in sums.read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, name = line.split(maxsplit=1)
            expected[name] = digest
    observed = {name: sha256(directory / name) for name in (
        "predictions.jsonl", "raw_responses.jsonl", "errors.jsonl",
        "request_metadata.jsonl", "run_metadata.json",
    )}
    if any(observed[name] != expected.get(name) for name in observed):
        raise SystemExit(f"Primary {condition} artifact hash changed")
    return observed


def load_condition(condition: str) -> dict[str, Any]:
    expected = primary_429_ids(condition)
    if condition == "B":
        directories = [RECOVERY / "condition_B", RECOVERY / "condition_B_remaining_after_auth_v1"]
    else:
        directories = [RECOVERY / "condition_C"]

    metadata: list[dict[str, Any]] = []
    raws: list[dict[str, Any]] = []
    predictions: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for directory in directories:
        metadata.extend(jsonl(directory / "request_metadata.jsonl"))
        raws.extend(jsonl(directory / "raw_responses.jsonl"))
        prediction_path = directory / "predictions.jsonl"
        error_path = directory / "errors.jsonl"
        if prediction_path.is_file():
            predictions.extend(jsonl(prediction_path))
        if error_path.is_file():
            errors.extend(jsonl(error_path))

    metadata_ids = [row["item_id"] for row in metadata]
    raw_ids = [row["item_id"] for row in raws]
    prediction_ids = [row["item_id"] for row in predictions]
    error_ids = [row["item_id"] for row in errors]
    if len(metadata_ids) != len(set(metadata_ids)):
        raise SystemExit(f"Recovery {condition} metadata contains duplicate IDs")
    if set(metadata_ids) != expected:
        raise SystemExit(f"Recovery {condition} IDs do not exactly cover primary HTTP-429 IDs")
    if len(raw_ids) != len(set(raw_ids)) or set(raw_ids) != expected:
        raise SystemExit(f"Recovery {condition} raw responses do not exactly cover selected IDs")
    if set(prediction_ids) & set(error_ids) or set(prediction_ids) | set(error_ids) != expected:
        raise SystemExit(f"Recovery {condition} predictions/errors do not partition selected IDs")
    for row in metadata:
        if row.get("max_tokens") != SETTINGS["max_tokens"] or row.get("endpoint") != SETTINGS["endpoint"]:
            raise SystemExit(f"Recovery {condition} settings mismatch for {row['item_id']}")

    error_by_id = {row["item_id"]: row for row in errors}
    raw_by_id = {row["item_id"]: row for row in raws}
    ledger: list[dict[str, Any]] = []
    for row in metadata:
        item_id = row["item_id"]
        error = error_by_id.get(item_id, {})
        raw = raw_by_id[item_id]
        ledger.append({
            "item_id": item_id,
            "sequence": row.get("sequence"),
            "attempt_class": "RECOVERY_429_V1",
            "attempt_number": 1,
            "outcome": "accepted" if item_id in set(prediction_ids) else "error",
            "http_status": row.get("http_status") if row.get("http_status") is not None else error.get("http_status"),
            "error_type": error.get("error_type"),
            "request_sha256": row.get("request_sha256"),
            "evidence_sha256": row.get("evidence_sha256"),
            "raw_response_sha256": row.get("response_sha256") or raw.get("raw_response_sha256"),
        })
    ledger.sort(key=lambda row: row["item_id"])
    ledger_path = RECOVERY / f"{condition}_recovery_429_v1_ledger.jsonl"
    ledger_path.write_text("".join(canonical(row) + "\n" for row in ledger), encoding="utf-8", newline="\n")
    outcome_counts = Counter(row["outcome"] for row in ledger)
    status_counts = Counter(str(row["http_status"]) for row in ledger if row["http_status"] is not None)
    error_counts = Counter(row["error_type"] for row in ledger if row["error_type"])
    return {
        "primary_http_429_count": len(expected),
        "recovery_attempt_count": len(ledger),
        "accepted_count": outcome_counts["accepted"],
        "error_count": outcome_counts["error"],
        "http_statuses": dict(status_counts),
        "error_types": dict(error_counts),
        "exact_primary_429_coverage": True,
        "one_attempt_per_selected_id": all(row["attempt_number"] == 1 for row in ledger),
        "ledger": str(ledger_path.relative_to(ROOT)),
        "ledger_sha256": sha256(ledger_path),
        "source_directories": [str(directory.relative_to(ROOT)) for directory in directories],
    }


def main() -> None:
    primary_hashes = {condition: check_primary_unchanged(condition) for condition in ("B", "C")}
    conditions = {condition: load_condition(condition) for condition in ("B", "C")}
    summary = {
        "status": "RECOVERY_429_V1_COMPLETE_WITH_RECORDED_ERRORS",
        "finalized_at": utc_now(),
        "dataset": "heldout_test_197_final_claim_bearing_cohort",
        "model": SETTINGS["model"],
        "recovery_namespace": str(RECOVERY.relative_to(ROOT)),
        "scope": "exactly one recovery attempt for every primary HTTP-429 outcome; no retry for recovery errors",
        "settings": SETTINGS,
        "conditions": conditions,
        "primary_records_untouched": True,
        "primary_artifact_hashes_after_recovery": primary_hashes,
        "human_annotations": "results/heldout_test_197/annotations_frozen_v1",
    }
    out = RECOVERY / "recovery_429_v1_summary.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
