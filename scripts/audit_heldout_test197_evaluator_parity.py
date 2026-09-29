#!/usr/bin/env python3
"""Construct the no-call parity audit for the final TEST-197 packet cohort."""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "results" / "heldout_test_197" / "evidence_frozen_v1.jsonl"
OUT = ROOT / "results" / "heldout_test_197"
sys.path.insert(0, str(ROOT / "baselines" / "condition_B"))
import run_baseline as condition_b  # noqa: E402


MODELS = {
    "qwen": "qwen/qwen3.8-27b",
    "deepseek": "deepseek/deepseek-v4.1-flash",
}
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


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    packets = condition_b.read_jsonl(PACKET)
    if len(packets) != 168:
        raise SystemExit(f"Expected 168 final claim-bearing packets, found {len(packets)}")
    rows: list[dict[str, Any]] = []
    evidence_by_condition: dict[str, dict[str, str]] = {"B": {}, "C": {}}
    request_hashes: dict[str, set[str]] = {"B": set(), "C": set()}
    prompts = {
        "B": condition_b.fixed_prompt(),
        "C": (ROOT / "baselines" / "condition_C" / "prompt.txt").read_text(encoding="utf-8").strip(),
    }
    packet_sha = file_sha256(PACKET)
    for packet in packets:
        item_id = condition_b.required_string(packet, "item_id", "<packet>")
        evidence, _ = condition_b.project_evidence(packet)
        for condition, prompt in prompts.items():
            body = condition_b.request_body("qwen/qwen3.8-27b", prompt, evidence, SETTINGS["max_tokens"])
            evidence_sha = condition_b.sha256_text(condition_b.canonical(evidence))
            request_sha = condition_b.sha256_text(condition_b.canonical(body))
            evidence_by_condition[condition][item_id] = evidence_sha
            request_hashes[condition].add(request_sha)
            rows.append({
                "item_id": item_id,
                "condition": condition,
                "model_independent_evidence_sha256": evidence_sha,
                "request_sha256_qwen": request_sha,
                "prompt_sha256": condition_b.sha256_text(prompt),
                "packet_file_sha256": packet_sha,
                **SETTINGS,
            })
    if evidence_by_condition["B"] != evidence_by_condition["C"]:
        raise SystemExit("B/C evidence parity failed")
    if len(request_hashes["B"]) != 168 or len(request_hashes["C"]) != 168:
        raise SystemExit("Unexpected request-hash cardinality; item evidence/order may not be unique")
    model_rows = []
    for model_name, model in MODELS.items():
        for condition in ("B", "C"):
            model_rows.append({
                "model": model,
                "condition": condition,
                "packet_count": len(packets),
                "evidence_parity_with_other_condition": True,
                "evidence_parity_with_frozen_packet_projection": True,
                "prompt_sha256": condition_b.sha256_text(prompts[condition]),
                **SETTINGS,
            })
    OUT.mkdir(parents=True, exist_ok=True)
    csv_path = OUT / "evaluator_parity.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "status": "PASS_NO_PROVIDER_CALLS",
        "dataset": "heldout_test_197_final_claim_bearing_cohort",
        "packet_count": len(packets),
        "packet_file": str(PACKET),
        "packet_file_sha256": packet_sha,
        "models": MODELS,
        "conditions": ["B", "C"],
        "development_exclusions_and_stage_a_failures_not_called": True,
        "evidence_parity": "168/168",
        "evidence_sha256_B_equals_C": True,
        "request_construction_provider_calls": 0,
        "prompts": {key: condition_b.sha256_text(value) for key, value in prompts.items()},
        "settings": SETTINGS,
        "model_condition_matrix": model_rows,
        "artifacts": {"per_item_csv": str(csv_path)},
    }
    write_json(OUT / "evaluator_parity_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
