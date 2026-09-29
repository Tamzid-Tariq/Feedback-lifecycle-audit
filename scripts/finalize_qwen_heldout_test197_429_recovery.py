#!/usr/bin/env python3
"""Finalize and audit Qwen RECOVERY_429_V1 for held-out TEST-197."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EVALUATIONS = ROOT / "results" / "heldout_test_197" / "evaluations"
BASE = EVALUATIONS / "qwen_qwen3_8_27b"
PRIMARY = {condition: BASE / f"condition_{condition}" for condition in ("B", "C")}
RECOVERY = BASE / "RECOVERY_429_V1"
GLOBAL_FREEZE = EVALUATIONS / "primary_first_attempt_freeze_summary.json"
EXPECTED_PRIMARY_429 = {"B": 51, "C": 27}
SETTINGS = {
    "model": "qwen/qwen3.8-27b",
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
    if not path.is_file():
        raise SystemExit(f"Missing required artifact: {path}")
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def verify_global_freeze() -> dict[str, Any]:
    summary = json.loads(GLOBAL_FREEZE.read_text(encoding="utf-8"))
    if summary.get("status") != "COMPLETE_PRIMARY_FIRST_ATTEMPTS_FROZEN":
        raise SystemExit("Primary matrix is not marked complete")
    if summary.get("frozen_run_count") != 4 or summary.get("requested_primary_attempts") != 672:
        raise SystemExit("Primary matrix count mismatch")
    return {
        "path": relative(GLOBAL_FREEZE),
        "sha256": sha256(GLOBAL_FREEZE),
        "status": summary["status"],
        "frozen_run_count": summary["frozen_run_count"],
        "requested_primary_attempts": summary["requested_primary_attempts"],
    }


def verify_primary(condition: str) -> dict[str, Any]:
    directory = PRIMARY[condition]
    sums_path = directory / "PRIMARY_FIRST_ATTEMPT_SHA256SUMS.txt"
    base_resolved = BASE.resolve()
    observed: dict[str, str] = {}
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected_digest, name = line.split(maxsplit=1)
        target = (directory / name).resolve()
        if target != base_resolved and base_resolved not in target.parents:
            raise SystemExit(f"Primary {condition} checksum target escapes model directory: {name}")
        if not target.is_file():
            raise SystemExit(f"Primary {condition} checksum target is missing: {name}")
        actual_digest = sha256(target)
        if actual_digest != expected_digest:
            raise SystemExit(f"Primary {condition} artifact hash changed: {name}")
        observed[relative(target)] = actual_digest

    freeze_path = directory / "primary_first_attempt_freeze.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if freeze.get("status") != "FROZEN_PRIMARY_FIRST_ATTEMPT":
        raise SystemExit(f"Primary {condition} is not frozen")
    if freeze.get("requested_model") != SETTINGS["model"]:
        raise SystemExit(f"Primary {condition} requested model mismatch")

    ledger_path = directory / "primary_first_attempt_ledger.jsonl"
    ledger = jsonl(ledger_path)
    selected = [row for row in ledger if row.get("http_status") == 429]
    selected_ids = [row["item_id"] for row in selected]
    expected_count = EXPECTED_PRIMARY_429[condition]
    if len(selected_ids) != expected_count or len(set(selected_ids)) != expected_count:
        raise SystemExit(
            f"Primary {condition} canonical ledger must contain exactly "
            f"{expected_count} unique HTTP-429 IDs"
        )
    if any(row.get("attempt_class") != "PRIMARY_FIRST_ATTEMPT" for row in selected):
        raise SystemExit(f"Primary {condition} selected rows are not first attempts")

    return {
        "ids": selected_ids,
        "rows_by_id": {row["item_id"]: row for row in selected},
        "prompt_sha256": freeze["prompt_sha256"],
        "evidence_packet_sha256": freeze["evidence_packet_sha256"],
        "freeze_sha256": sha256(freeze_path),
        "checksums_sha256": sha256(sums_path),
        "verified_artifact_sha256": observed,
    }


def require_unique_exact(rows: list[dict[str, Any]], expected_ids: list[str], label: str) -> None:
    ids = [row.get("item_id") for row in rows]
    if len(ids) != len(set(ids)):
        raise SystemExit(f"{label} contains duplicate item IDs")
    if ids != expected_ids:
        raise SystemExit(f"{label} does not exactly preserve the frozen primary-429 order")


def load_condition(condition: str, primary: dict[str, Any]) -> dict[str, Any]:
    directory = RECOVERY / f"condition_{condition}"
    metadata = jsonl(directory / "request_metadata.jsonl")
    raws = jsonl(directory / "raw_responses.jsonl")
    predictions = jsonl(directory / "predictions.jsonl")
    errors = jsonl(directory / "errors.jsonl")
    run_metadata_path = directory / "run_metadata.json"
    run_metadata = json.loads(run_metadata_path.read_text(encoding="utf-8"))
    expected_ids: list[str] = primary["ids"]

    require_unique_exact(metadata, expected_ids, f"Recovery {condition} request metadata")
    require_unique_exact(raws, expected_ids, f"Recovery {condition} raw responses")

    prediction_ids = [row.get("item_id") for row in predictions]
    error_ids = [row.get("item_id") for row in errors]
    if len(prediction_ids) != len(set(prediction_ids)):
        raise SystemExit(f"Recovery {condition} predictions contain duplicate IDs")
    if len(error_ids) != len(set(error_ids)):
        raise SystemExit(f"Recovery {condition} errors contain duplicate IDs")
    if set(prediction_ids) & set(error_ids):
        raise SystemExit(f"Recovery {condition} accepted/error outcomes overlap")
    if set(prediction_ids) | set(error_ids) != set(expected_ids):
        raise SystemExit(f"Recovery {condition} outcomes do not partition selected IDs")

    expected_prompt = primary["prompt_sha256"]
    primary_rows = primary["rows_by_id"]
    for sequence, row in enumerate(metadata, start=1):
        item_id = row["item_id"]
        checks = {
            "sequence": row.get("sequence") == sequence,
            "model": row.get("model_requested") == SETTINGS["model"],
            "endpoint": row.get("endpoint") == SETTINGS["endpoint"],
            "max_tokens": row.get("max_tokens") == SETTINGS["max_tokens"],
            "prompt": row.get("prompt_sha256") == expected_prompt,
            "evidence": row.get("evidence_sha256")
            == primary_rows[item_id].get("evidence_sha256"),
        }
        failed = [name for name, passed in checks.items() if not passed]
        if failed:
            raise SystemExit(
                f"Recovery {condition} metadata mismatch for {item_id}: {', '.join(failed)}"
            )

    run_checks = {
        "model": run_metadata.get("model_requested") == SETTINGS["model"],
        "endpoint": run_metadata.get("endpoint") == SETTINGS["endpoint"],
        "requested_items": run_metadata.get("requested_items") == len(expected_ids),
        "selected_ids": run_metadata.get("selected_item_ids") == expected_ids,
        "prompt": run_metadata.get("prompt_sha256") == expected_prompt,
        "sleep": run_metadata.get("pacing_seconds_between_completed_requests")
        == SETTINGS["sleep_seconds_between_requests"],
        "post_429_sleep": run_metadata.get("pacing_seconds_after_http_429")
        == SETTINGS["post_429_sleep_seconds"],
    }
    failed_run_checks = [name for name, passed in run_checks.items() if not passed]
    if failed_run_checks:
        raise SystemExit(
            f"Recovery {condition} run settings mismatch: {', '.join(failed_run_checks)}"
        )

    error_by_id = {row["item_id"]: row for row in errors}
    raw_by_id = {row["item_id"]: row for row in raws}
    prediction_id_set = set(prediction_ids)
    ledger: list[dict[str, Any]] = []
    for row in metadata:
        item_id = row["item_id"]
        error = error_by_id.get(item_id, {})
        raw = raw_by_id[item_id]
        ledger.append(
            {
                "item_id": item_id,
                "sequence": row["sequence"],
                "attempt_class": "RECOVERY_429_V1",
                "attempt_number": 1,
                "selected_from_primary_http_status": 429,
                "outcome": "accepted" if item_id in prediction_id_set else "error",
                "http_status": row.get("http_status", error.get("http_status")),
                "error_type": error.get("error_type"),
                "requested_model": row.get("model_requested"),
                "returned_model": row.get("model_returned"),
                "prompt_sha256": row.get("prompt_sha256"),
                "request_sha256": row.get("request_sha256"),
                "evidence_sha256": row.get("evidence_sha256"),
                "raw_response_sha256": row.get("response_sha256")
                or error.get("raw_response_sha256")
                or raw.get("raw_response_sha256"),
            }
        )

    ledger_path = RECOVERY / f"{condition}_recovery_429_v1_ledger.jsonl"
    ledger_path.write_text(
        "".join(canonical(row) + "\n" for row in ledger),
        encoding="utf-8",
        newline="\n",
    )
    status_counts = Counter(str(row["http_status"]) for row in ledger)
    error_counts = Counter(row["error_type"] for row in ledger if row["error_type"])
    artifacts = {
        relative(path): sha256(path)
        for path in (
            directory / "predictions.jsonl",
            directory / "raw_responses.jsonl",
            directory / "errors.jsonl",
            directory / "request_metadata.jsonl",
            run_metadata_path,
            ledger_path,
        )
    }
    return {
        "primary_http_429_count": len(expected_ids),
        "recovery_attempt_count": len(ledger),
        "accepted_count": len(predictions),
        "error_count": len(errors),
        "http_statuses": dict(sorted(status_counts.items())),
        "error_types": dict(sorted(error_counts.items())),
        "exact_primary_429_coverage": True,
        "one_attempt_per_selected_id": True,
        "selected_only_from_primary_canonical_ledger": True,
        "selected_non_429_primary_count": 0,
        "prompt_sha256_matches_primary": True,
        "evidence_sha256_matches_primary_per_item": True,
        "ledger": relative(ledger_path),
        "ledger_sha256": sha256(ledger_path),
        "run_directory": relative(directory),
        "artifact_sha256": artifacts,
    }


def write_readme(conditions: dict[str, dict[str, Any]]) -> Path:
    b = conditions["B"]
    c = conditions["C"]
    text = f"""# Qwen RECOVERY_429_V1

This namespace contains exactly one recovery attempt for each primary HTTP-429 outcome in the frozen Qwen B/C runs. No HTTP 400, malformed JSON, schema rejection, input-size failure, or other primary failure was selected.

## Settings

- Model: `qwen/qwen3.8-27b`
- Maximum completion tokens: 16,000
- Temperature: 0
- Per-call timeout: 360 seconds
- Pacing: 20 seconds between calls; 90 seconds after a recovery HTTP 429
- Automatic retry: disabled
- Fallback: disabled
- Primary files: untouched and hash-verified after recovery

## Outcomes

- Condition B: {b['recovery_attempt_count']} attempts covering {b['primary_http_429_count']} primary 429s; {b['accepted_count']} accepted, {b['error_count']} recorded errors.
- Condition C: {c['recovery_attempt_count']} attempts covering {c['primary_http_429_count']} primary 429s; {c['accepted_count']} accepted, {c['error_count']} recorded errors.

Recovery failures were retained as final outcomes and were not retried or replaced. See `recovery_429_v1_summary.json` and the condition ledgers for the audited record.
"""
    path = RECOVERY / "README.md"
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def main() -> None:
    RECOVERY.mkdir(parents=True, exist_ok=True)
    global_freeze = verify_global_freeze()
    primary = {condition: verify_primary(condition) for condition in ("B", "C")}
    conditions = {
        condition: load_condition(condition, primary[condition])
        for condition in ("B", "C")
    }
    summary = {
        "status": "RECOVERY_429_V1_COMPLETE_WITH_RECORDED_ERRORS",
        "finalized_at": utc_now(),
        "dataset": "heldout_test_197_final_claim_bearing_cohort",
        "model": SETTINGS["model"],
        "recovery_namespace": relative(RECOVERY),
        "scope": (
            "exactly one recovery attempt for every primary HTTP-429 outcome; "
            "no recovery of non-429 primary failures; no retry of recovery failures"
        ),
        "settings": SETTINGS,
        "primary_matrix_freeze": global_freeze,
        "conditions": conditions,
        "primary_records_untouched": True,
        "primary_artifact_hashes_after_recovery": {
            condition: primary[condition]["verified_artifact_sha256"]
            for condition in ("B", "C")
        },
        "primary_freeze_sha256": {
            condition: primary[condition]["freeze_sha256"]
            for condition in ("B", "C")
        },
        "primary_checksum_manifest_sha256": {
            condition: primary[condition]["checksums_sha256"]
            for condition in ("B", "C")
        },
        "human_annotations": "results/heldout_test_197/annotations_frozen_v1",
    }
    summary_path = RECOVERY / "recovery_429_v1_summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    readme_path = write_readme(conditions)

    files_to_hash = [summary_path, readme_path]
    for condition in ("B", "C"):
        directory = RECOVERY / f"condition_{condition}"
        files_to_hash.extend(
            directory / name
            for name in (
                "predictions.jsonl",
                "raw_responses.jsonl",
                "errors.jsonl",
                "request_metadata.jsonl",
                "run_metadata.json",
            )
        )
        files_to_hash.append(RECOVERY / f"{condition}_recovery_429_v1_ledger.jsonl")
    sums_path = RECOVERY / "RECOVERY_429_V1_SHA256SUMS.txt"
    sums_path.write_text(
        "".join(f"{sha256(path)}  {path.relative_to(RECOVERY).as_posix()}\n" for path in files_to_hash),
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
