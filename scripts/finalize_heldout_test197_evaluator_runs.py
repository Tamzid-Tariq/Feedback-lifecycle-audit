#!/usr/bin/env python3
"""Add provider/model/settings telemetry and integrity summaries to evaluator runs."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "results" / "heldout_test_197" / "evaluations"
EXPECTED = 168
SETTINGS = {
    "max_tokens": 16000,
    "temperature": 0,
    "top_p": None,
    "timeout_seconds": 360,
    "automatic_retry": False,
    "fallback_disabled": True,
    "retry_policy": "none; failures recorded, no retry calls",
    "endpoint": "https://openrouter.ai/api/v1/chat/completions",
}


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    summaries: dict[str, Any] = {}
    for directory in sorted(BASE.glob("*/condition_*")):
        required = {name: directory / name for name in (
            "predictions.jsonl", "raw_responses.jsonl", "errors.jsonl",
            "request_metadata.jsonl", "run_metadata.json",
        )}
        if not all(path.is_file() for path in required.values()):
            continue
        run = json.loads(required["run_metadata.json"].read_text(encoding="utf-8"))
        metadata = jsonl(required["request_metadata.jsonl"])
        raws = jsonl(required["raw_responses.jsonl"])
        predictions = jsonl(required["predictions.jsonl"])
        errors = jsonl(required["errors.jsonl"])
        if len(metadata) != EXPECTED or len(raws) != EXPECTED:
            raise SystemExit(f"{directory}: expected {EXPECTED} request/raw rows")
        raw_by_id = {row["item_id"]: row for row in raws}
        providers: Counter[str] = Counter()
        returned_models: Counter[str] = Counter()
        provider_by_item: dict[str, str | None] = {}
        returned_by_item: dict[str, str | None] = {}
        mismatches: list[dict[str, Any]] = []
        missing: list[str] = []
        for row in metadata:
            item_id = row["item_id"]
            raw_record = raw_by_id[item_id]
            try:
                raw_json = json.loads(raw_record.get("raw_response") or "{}")
            except json.JSONDecodeError:
                raw_json = {}
            provider = raw_json.get("provider") if isinstance(raw_json.get("provider"), str) else None
            returned = row.get("model_returned") or raw_record.get("returned_model")
            if not returned and isinstance(raw_json.get("model"), str):
                returned = raw_json["model"]
            provider_by_item[item_id] = provider
            returned_by_item[item_id] = returned
            if provider:
                providers[provider] += 1
            if returned:
                returned_models[returned] += 1
            else:
                missing.append(item_id)
            match = returned == row.get("model_requested") if returned else None
            row.update({
                "provider_returned": provider,
                "returned_model": returned,
                "returned_model_matches_requested": match,
                **SETTINGS,
            })
            raw_record.update({
                "provider_returned": provider,
                "returned_model": returned,
                "returned_model_matches_requested": match,
            })
            if returned and returned != row.get("model_requested"):
                mismatches.append({"item_id": item_id, "requested_model": row.get("model_requested"), "returned_model": returned})
        required["request_metadata.jsonl"].write_text("".join(canonical(row) + "\n" for row in metadata), encoding="utf-8", newline="\n")
        required["raw_responses.jsonl"].write_text("".join(canonical(row) + "\n" for row in raws), encoding="utf-8", newline="\n")
        request_count = len(metadata)
        accepted_count = len(predictions)
        failed_count = len(errors)
        latencies = [row["latency_ms"] for row in metadata if isinstance(row.get("latency_ms"), int)]
        usage = {key: sum(row.get(key, 0) for row in metadata if isinstance(row.get(key), int)) for key in (
            "prompt_tokens", "completion_tokens", "reasoning_tokens", "total_tokens")}
        run.update({
            "dataset": "heldout_test_197",
            "condition": directory.name,
            "requested_model": run.get("model_requested"),
            "returned_models": dict(returned_models),
            "requested_model_equals_returned_model_for_accepted_responses": all(
                row.get("returned_model") == row.get("model_requested") for row in metadata if row.get("status") == "accepted"
            ),
            "requested_model_equals_returned_model_for_all_returned_responses": not mismatches,
            "model_mismatches": mismatches,
            "missing_returned_model_item_ids": missing,
            "provider": dict(providers),
            "provider_by_item": provider_by_item,
            "evidence_sha256_by_item": {row["item_id"]: row.get("evidence_sha256") for row in metadata},
            **SETTINGS,
            "requested_count": request_count,
            "accepted_count": accepted_count,
            "failed_count": failed_count,
            "input_tokens": usage["prompt_tokens"],
            "output_tokens": usage["completion_tokens"],
            "reasoning_tokens": usage["reasoning_tokens"],
            "total_tokens": usage["total_tokens"],
            "requests_with_usage": sum(1 for row in metadata if row.get("usage_available")),
            "mean_latency_ms_from_requests": round(sum(latencies) / len(latencies)) if latencies else None,
            "median_latency_ms_from_requests": sorted(latencies)[len(latencies) // 2] if latencies else None,
            "min_latency_ms_from_requests": min(latencies) if latencies else None,
            "max_latency_ms_from_requests": max(latencies) if latencies else None,
            "raw_responses_sha256": sha256(required["raw_responses.jsonl"]),
            "request_metadata_sha256": sha256(required["request_metadata.jsonl"]),
            "predictions_sha256": sha256(required["predictions.jsonl"]),
            "errors_sha256": sha256(required["errors.jsonl"]),
            "reference_labels_changed": False,
            "automatic_fallback_model": None,
            "finalized_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        })
        (required["run_metadata.json"]).write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        summaries[str(directory.relative_to(BASE))] = {
            "requested": request_count,
            "accepted": accepted_count,
            "failed": failed_count,
            "provider_counts": dict(providers),
            "returned_models": dict(returned_models),
            "model_parity_pass": not mismatches and not missing,
            "errors": [{"item_id": row.get("item_id"), "error_type": row.get("error_type"), "http_status": row.get("http_status")} for row in errors],
            "tokens": usage,
            "mean_latency_ms": run["mean_latency_ms_from_requests"],
            "median_latency_ms": run["median_latency_ms_from_requests"],
        }
    if not summaries:
        raise SystemExit(f"No completed evaluator runs found below {BASE}")
    summary = {
        "status": "FINALIZED_WITH_PRIMARY_OUTCOMES",
        "dataset": "heldout_test_197_final_claim_bearing_cohort",
        "requested_model_condition_runs": 4,
        "requested_provider_calls": 4 * EXPECTED,
        "settings": SETTINGS,
        "runs": summaries,
    }
    (BASE / "run_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
