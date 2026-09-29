#!/usr/bin/env python3
"""Record an already-sent primary call whose runner crashed before persistence.

This tool never calls a provider and only appends the one terminal attempt record
attested by the runner's terminal log. It prevents accidental reissue of that item.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "baselines" / "condition_B"))
import run_baseline as condition_b  # noqa: E402


def item_ids(path: Path) -> set[str]:
    return {row["item_id"] for row in condition_b.read_jsonl(path)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--item-id", required=True)
    parser.add_argument("--sequence", type=int, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--endpoint", default="https://openrouter.ai/api/v1/chat/completions")
    parser.add_argument("--max-tokens", type=int, default=16000)
    args = parser.parse_args()
    packet_path = ROOT / "results" / "heldout_test_197" / "evidence_frozen_v1.jsonl"
    packets = condition_b.read_jsonl(packet_path)
    if args.sequence < 1 or args.sequence > len(packets):
        raise SystemExit("sequence is outside the frozen packet range")
    packet = packets[args.sequence - 1]
    if packet.get("item_id") != args.item_id:
        raise SystemExit("item ID does not match the supplied frozen packet sequence")
    evidence, permitted_ids = condition_b.project_evidence(packet)
    prompt = condition_b.fixed_prompt()
    body = condition_b.request_body(args.model, prompt, evidence, args.max_tokens)
    request_sha = condition_b.sha256_text(condition_b.canonical(body))
    evidence_sha = condition_b.sha256_text(condition_b.canonical(evidence))
    paths = {
        "raw": args.run_dir / "raw_responses.jsonl",
        "errors": args.run_dir / "errors.jsonl",
        "metadata": args.run_dir / "request_metadata.jsonl",
    }
    if not all(path.is_file() for path in paths.values()):
        raise SystemExit("primary run artifacts are missing")
    existing = set().union(*(item_ids(path) for path in paths.values()))
    if args.item_id in existing:
        raise SystemExit("refusing to duplicate an already recorded item")
    now = condition_b.utc_now()
    error = {
        "item_id": args.item_id,
        "sequence": args.sequence,
        "request_sha256": request_sha,
        "error_type": "IncompleteRead",
        "error": "Primary request was sent, but the runner crashed on http.client.IncompleteRead before its normal error handler persisted a response.",
        "http_status": None,
        "raw_response_sha256": None,
        "provider_called": True,
        "attempt_class": "PRIMARY_FIRST_ATTEMPT",
        "record_origin": "terminal_log_reconstruction_no_provider_reissue",
        "occurred_at": now,
    }
    raw = {
        "item_id": args.item_id,
        "sequence": args.sequence,
        "request_sha256": request_sha,
        "http_status": None,
        "provider_response_id": None,
        "returned_model": None,
        "raw_response": "",
        "completion_content": None,
        "telemetry": condition_b.response_telemetry(""),
        "received_at": now,
        "provider_called": True,
        "attempt_class": "PRIMARY_FIRST_ATTEMPT",
        "record_origin": "terminal_log_reconstruction_no_provider_reissue",
    }
    metadata = {
        "item_id": args.item_id,
        "sequence": args.sequence,
        "model_requested": args.model,
        "max_tokens": args.max_tokens,
        "endpoint": args.endpoint,
        "prompt_sha256": condition_b.sha256_text(prompt),
        "request_sha256": request_sha,
        "evidence_sha256": evidence_sha,
        "evidence_top_level_keys": sorted(evidence),
        "available_evidence_ids": sorted(permitted_ids),
        "forbidden_reference_fields": sorted(condition_b.forbidden_reference_fields(evidence)),
        "started_at": None,
        "status": "error",
        "http_status": None,
        "provider_response_id": None,
        "model_returned": None,
        "response_sha256": None,
        "prompt_tokens": None,
        "completion_tokens": None,
        "reasoning_tokens": None,
        "total_tokens": None,
        "finish_reason": None,
        "usage_available": False,
        "latency_ms": None,
        "elapsed_ms": None,
        "finished_at": now,
        "provider_called": True,
        "attempt_class": "PRIMARY_FIRST_ATTEMPT",
        "record_origin": "terminal_log_reconstruction_no_provider_reissue",
    }
    for path, row in ((paths["errors"], error), (paths["raw"], raw), (paths["metadata"], metadata)):
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            condition_b.append_jsonl(handle, row)
    print(condition_b.canonical({
        "status": "RECORDED_UNLOGGED_PRIMARY_ATTEMPT_WITHOUT_REISSUE",
        "item_id": args.item_id,
        "sequence": args.sequence,
        "request_sha256": request_sha,
        "evidence_sha256": evidence_sha,
    }))


if __name__ == "__main__":
    main()
