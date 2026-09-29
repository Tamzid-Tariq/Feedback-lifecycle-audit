#!/usr/bin/env python3
"""Freeze completed TEST-197 evaluator runs without rewriting primary records."""
from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "results" / "heldout_test_197" / "evidence_frozen_v1.jsonl"
BASE = ROOT / "results" / "heldout_test_197" / "evaluations"
EXPECTED = 168
SETTINGS = {
    "max_tokens": 16000,
    "temperature": 0,
    "top_p": None,
    "timeout_seconds": 360,
    "fallback_disabled": True,
    "automatic_retry": False,
    "retry_policy": "none; failures recorded, no retry calls",
    "endpoint": "https://openrouter.ai/api/v1/chat/completions",
}
PRIMARY_RECORD_NAMES = (
    "predictions.jsonl",
    "raw_responses.jsonl",
    "errors.jsonl",
    "request_metadata.jsonl",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(canonical(row) + "\n" for row in rows), encoding="utf-8", newline="\n")


def verify_existing_freeze(directory: Path) -> dict[str, Any] | None:
    ledger_path = directory / "primary_first_attempt_ledger.jsonl"
    freeze_path = directory / "primary_first_attempt_freeze.json"
    sums_path = directory / "PRIMARY_FIRST_ATTEMPT_SHA256SUMS.txt"
    if not all(path.is_file() for path in (ledger_path, freeze_path, sums_path)):
        return None
    model_root = directory.parent.resolve()
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            digest, relative = line.split("  ", 1)
        except ValueError as exc:
            raise SystemExit(f"Malformed checksum line in {sums_path}: {line!r}") from exc
        target = (directory / relative).resolve()
        try:
            target.relative_to(model_root)
        except ValueError as exc:
            raise SystemExit(f"Checksum target escapes model directory: {relative}") from exc
        if not target.is_file() or sha256(target) != digest:
            raise SystemExit(f"Frozen artifact changed or is missing: {target}")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    ledger = jsonl(ledger_path)
    if freeze.get("status") != "FROZEN_PRIMARY_FIRST_ATTEMPT" or len(ledger) != EXPECTED:
        raise SystemExit(f"Existing freeze is malformed: {directory}")
    return freeze


def build_freeze(directory: Path, sources: list[Path], packet_ids: list[str]) -> dict[str, Any]:
    expected_ids = set(packet_ids)
    metadata_by_id: dict[str, dict[str, Any]] = {}
    raw_by_id: dict[str, dict[str, Any]] = {}
    prediction_ids: set[str] = set()
    error_by_id: dict[str, dict[str, Any]] = {}
    source_by_id: dict[str, Path] = {}
    source_artifacts: list[Path] = []

    for source in sources:
        files = {name: source / name for name in PRIMARY_RECORD_NAMES}
        if not all(path.is_file() for path in files.values()):
            raise SystemExit(f"Incomplete primary source directory: {source}")
        metadata = jsonl(files["request_metadata.jsonl"])
        raws = jsonl(files["raw_responses.jsonl"])
        predictions = jsonl(files["predictions.jsonl"])
        errors = jsonl(files["errors.jsonl"])
        source_artifacts.extend(files.values())
        run_metadata_path = source / "run_metadata.json"
        if run_metadata_path.is_file():
            source_artifacts.append(run_metadata_path)
        item_ids = [row["item_id"] for row in metadata]
        if len(item_ids) != len(set(item_ids)) or len(raws) != len(item_ids):
            raise SystemExit(f"Request/raw count or uniqueness failed: {source}")
        source_prediction_ids = {row["item_id"] for row in predictions}
        source_error_ids = {row["item_id"] for row in errors}
        if source_prediction_ids & source_error_ids or source_prediction_ids | source_error_ids != set(item_ids):
            raise SystemExit(f"Predictions/errors do not partition source attempts: {source}")
        if set(item_ids) & set(metadata_by_id):
            raise SystemExit(f"Duplicate first-attempt item across source directories: {source}")
        source_raw_by_id = {row["item_id"]: row for row in raws}
        if len(source_raw_by_id) != len(item_ids) or set(source_raw_by_id) != set(item_ids):
            raise SystemExit(f"Raw response IDs do not match request IDs: {source}")
        source_error_by_id = {row["item_id"]: row for row in errors}
        for row in metadata:
            item_id = row["item_id"]
            metadata_by_id[item_id] = row
            raw_by_id[item_id] = source_raw_by_id[item_id]
            source_by_id[item_id] = source
        prediction_ids.update(source_prediction_ids)
        error_by_id.update(source_error_by_id)

    if set(metadata_by_id) != expected_ids or len(metadata_by_id) != EXPECTED:
        raise SystemExit(f"{directory}: combined request IDs are not exactly the frozen 168-case cohort")
    if prediction_ids & set(error_by_id) or prediction_ids | set(error_by_id) != expected_ids:
        raise SystemExit(f"{directory}: combined predictions/errors do not partition all first attempts")
    requested_models = {row.get("model_requested") for row in metadata_by_id.values()}
    prompt_hashes = {row.get("prompt_sha256") for row in metadata_by_id.values()}
    endpoints = {row.get("endpoint") for row in metadata_by_id.values()}
    max_tokens = {row.get("max_tokens") for row in metadata_by_id.values()}
    if len(requested_models) != 1 or None in requested_models:
        raise SystemExit(f"{directory}: requested model is inconsistent")
    if len(prompt_hashes) != 1 or None in prompt_hashes:
        raise SystemExit(f"{directory}: prompt hash is inconsistent")
    if endpoints != {SETTINGS["endpoint"]} or max_tokens != {SETTINGS["max_tokens"]}:
        raise SystemExit(f"{directory}: endpoint or max_tokens differs from the fixed policy")

    providers: Counter[str] = Counter()
    returned_models: Counter[str] = Counter()
    ledger: list[dict[str, Any]] = []
    for sequence, item_id in enumerate(packet_ids, start=1):
        row = metadata_by_id[item_id]
        raw_record = raw_by_id[item_id]
        try:
            raw_json = json.loads(raw_record.get("raw_response") or "{}")
        except json.JSONDecodeError:
            raw_json = {}
        provider = raw_json.get("provider") if isinstance(raw_json.get("provider"), str) else None
        returned_model = row.get("model_returned") or raw_record.get("returned_model")
        if not returned_model and isinstance(raw_json.get("model"), str):
            returned_model = raw_json["model"]
        if provider:
            providers[provider] += 1
        if returned_model:
            returned_models[returned_model] += 1
        error = error_by_id.get(item_id)
        ledger.append({
            "item_id": item_id,
            "sequence": sequence,
            "source_directory": str(source_by_id[item_id].relative_to(BASE)),
            "source_sequence": row.get("sequence"),
            "attempt_class": "PRIMARY_FIRST_ATTEMPT",
            "attempt_number": 1,
            "outcome": "accepted" if item_id in prediction_ids else "error",
            "http_status": row.get("http_status") if row.get("http_status") is not None else (error or {}).get("http_status"),
            "error_type": (error or {}).get("error_type"),
            "provider_returned": provider,
            "requested_model": row.get("model_requested"),
            "returned_model": returned_model,
            "returned_model_matches_requested": returned_model == row.get("model_requested") if returned_model else None,
            "evidence_sha256": row.get("evidence_sha256"),
            "request_sha256": row.get("request_sha256"),
            "raw_response_sha256": row.get("response_sha256") or raw_record.get("raw_response_sha256"),
        })

    ledger_path = directory / "primary_first_attempt_ledger.jsonl"
    freeze_path = directory / "primary_first_attempt_freeze.json"
    sums_path = directory / "PRIMARY_FIRST_ATTEMPT_SHA256SUMS.txt"
    write_jsonl(ledger_path, ledger)
    status_counts = Counter(row["outcome"] for row in ledger)
    error_types = Counter(row["error_type"] for row in ledger if row["error_type"])
    http_statuses = Counter(str(row["http_status"]) for row in ledger if row["http_status"] is not None)
    source_hashes = {str(path.relative_to(BASE)): sha256(path) for path in source_artifacts}
    freeze = {
        "status": "FROZEN_PRIMARY_FIRST_ATTEMPT",
        "attempt_class": "PRIMARY_FIRST_ATTEMPT",
        "frozen_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "dataset": "heldout_test_197_final_claim_bearing_cohort",
        "condition": directory.name,
        "requested_model": next(iter(requested_models)),
        "requested_count": EXPECTED,
        "accepted_count": len(prediction_ids),
        "failed_count": len(error_by_id),
        "status_counts": dict(status_counts),
        "error_types": dict(error_types),
        "http_statuses": dict(http_statuses),
        "provider_counts": dict(providers),
        "returned_models": dict(returned_models),
        "model_mismatch_count": sum(1 for row in ledger if row["returned_model"] and not row["returned_model_matches_requested"]),
        "missing_returned_model_count": sum(1 for row in ledger if not row["returned_model"]),
        "evidence_packet_sha256": sha256(PACKET),
        "prompt_sha256": next(iter(prompt_hashes)),
        "settings": SETTINGS,
        "source_directories": [str(source.relative_to(BASE)) for source in sources],
        "source_artifact_sha256": source_hashes,
        "canonical_ledger_sha256": sha256(ledger_path),
        "primary_records_are_not_overwritten_by_recovery": True,
        "sha256sums_file": str(sums_path),
    }
    freeze_path.write_text(json.dumps(freeze, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    sums_entries = source_artifacts + [ledger_path, freeze_path]
    sums_path.write_text(
        "".join(
            f"{sha256(path)}  {Path(os.path.relpath(path, directory)).as_posix()}\n"
            for path in sums_entries
        ),
        encoding="utf-8", newline="\n",
    )
    return freeze


def summary_entry(directory: Path, freeze: dict[str, Any]) -> dict[str, Any]:
    ledger = jsonl(directory / "primary_first_attempt_ledger.jsonl")
    error_types = Counter(row["error_type"] for row in ledger if row.get("error_type"))
    return {
        "requested": EXPECTED,
        "accepted": sum(1 for row in ledger if row["outcome"] == "accepted"),
        "failed": sum(1 for row in ledger if row["outcome"] == "error"),
        "http_429": sum(1 for row in ledger if row.get("http_status") == 429),
        "http_400": sum(1 for row in ledger if row.get("http_status") == 400),
        "error_types": dict(error_types),
        "freeze_sha256": sha256(directory / "primary_first_attempt_freeze.json"),
        "sums_sha256": sha256(directory / "PRIMARY_FIRST_ATTEMPT_SHA256SUMS.txt"),
    }


def main() -> None:
    packet_ids = [json.loads(line)["item_id"] for line in PACKET.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(packet_ids) != EXPECTED or len(set(packet_ids)) != EXPECTED:
        raise SystemExit("Frozen evidence packet is not the expected unique 168-case cohort")
    frozen_runs: dict[str, Any] = {}
    for model_directory in sorted(path for path in BASE.iterdir() if path.is_dir()):
        for condition in ("condition_B", "condition_C"):
            directory = model_directory / condition
            if not directory.is_dir():
                continue
            sources = [directory]
            if model_directory.name == "qwen_qwen3_8_27b" and condition == "condition_B":
                continuation = model_directory / "condition_B_primary_continuation_unattempted_v1"
                if continuation.is_dir():
                    sources.append(continuation)
            freeze = verify_existing_freeze(directory)
            if freeze is None:
                if not all(all((source / name).is_file() for name in PRIMARY_RECORD_NAMES) for source in sources):
                    continue
                freeze = build_freeze(directory, sources, packet_ids)
            frozen_runs[str(directory.relative_to(BASE))] = summary_entry(directory, freeze)
    if not frozen_runs:
        raise SystemExit("No completed 168-case primary runs found")
    summary = {
        "status": "COMPLETE_PRIMARY_FIRST_ATTEMPTS_FROZEN" if len(frozen_runs) == 4 else "PARTIAL_PRIMARY_FIRST_ATTEMPTS_FROZEN",
        "dataset": "heldout_test_197_final_claim_bearing_cohort",
        "expected_run_count": 4,
        "frozen_run_count": len(frozen_runs),
        "requested_primary_attempts": len(frozen_runs) * EXPECTED,
        "runs": frozen_runs,
        "recovery_policy": "one separately named RECOVERY_429_V1 attempt only for HTTP 429 after all primary runs; no 400/schema/other retry",
    }
    (BASE / "primary_first_attempt_freeze_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
