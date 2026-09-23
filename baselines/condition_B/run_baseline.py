#!/usr/bin/env python3
"""Run the evidence-matched, fixed-prompt Condition B baseline.

The runner projects only the fields admitted by Condition B from a frozen
evidence packet. It never reads human annotations, adjudications, expected
lifecycle labels, or any RevGround decision procedure.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


BASELINE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASELINE_DIR.parents[1]
PROMPT_PATH = BASELINE_DIR / "prompt.txt"
DEFAULT_INPUT = REPO_ROOT / "annotation" / "development_50_evidence_frozen_v1.jsonl"
DEFAULT_OUTPUT = BASELINE_DIR / "outputs" / "condition_B_dev_predictions.jsonl"
DEFAULT_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "stealth/union-alpha"

OUTPUT_KEYS = {
    "item_id",
    "original_validity",
    "target_state_t1",
    "lifecycle_label",
    "instructional_priority",
    "leakage_label",
    "evidence_ids",
    "short_reason",
}
VALID_VALUES = {
    "original_validity": {"SUPPORTED", "REFUTED", "INDETERMINATE"},
    "target_state_t1": {"PRESENT", "RESOLVED", "INDETERMINATE", "NOT_APPLICABLE"},
    "lifecycle_label": {"KEEP", "RETIRE", "RETRACT", "UNSURE"},
    "instructional_priority": {"HIGH", "LOW", "UNKNOWN"},
    "leakage_label": {"ABSENT", "PRESENT", "NOT_EVALUATED"},
}


def canonical(value: Any) -> str:
    """Return the stable JSON representation used for hashes and JSONL."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ValueError(f"Frozen evidence packet file does not exist: {path}")
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc.msg}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_number}: each JSONL row must be an object")
            rows.append(row)
    if not rows:
        raise ValueError(f"Frozen evidence packet file is empty: {path}")
    return rows


def required_string(packet: dict[str, Any], field: str, item_id: str) -> str:
    value = packet.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{item_id}: missing non-empty {field}")
    return value


def nested_string(packet: dict[str, Any], path: tuple[str, ...], item_id: str) -> str:
    value: Any = packet
    for key in path:
        if not isinstance(value, dict):
            raise ValueError(f"{item_id}: missing {'.'.join(path)}")
        value = value.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{item_id}: missing non-empty {'.'.join(path)}")
    return value


def verify_frozen_packet(packet: dict[str, Any]) -> None:
    """Reject altered/malformed packets before a provider is contacted."""
    item_id = required_string(packet, "item_id", "<packet>")
    required_string(packet, "packet_id", item_id)
    required_string(packet, "problem_statement", item_id)
    required_string(packet, "original_hint", item_id)
    required_string(packet, "code_diff", item_id)
    nested_string(packet, ("claim_span", "text"), item_id)
    nested_string(packet, ("earlier", "source"), item_id)
    nested_string(packet, ("later", "source"), item_id)
    for field in ("compiler", "tests", "stored_judge_traces", "all_evidence_ids"):
        if field not in packet:
            raise ValueError(f"{item_id}: missing {field}")
    if not isinstance(packet["compiler"], dict) or not isinstance(packet["tests"], list):
        raise ValueError(f"{item_id}: compiler must be an object and tests must be a list")
    if not isinstance(packet["stored_judge_traces"], dict):
        raise ValueError(f"{item_id}: stored_judge_traces must be an object")
    if not isinstance(packet["all_evidence_ids"], list) or not all(
        isinstance(value, str) and value for value in packet["all_evidence_ids"]
    ):
        raise ValueError(f"{item_id}: all_evidence_ids must be a list of strings")
    expected_hash = required_string(packet, "packet_sha256", item_id)
    content = {key: value for key, value in packet.items() if key != "packet_sha256"}
    observed_hash = sha256_text(canonical(content))
    if observed_hash != expected_hash:
        raise ValueError(f"{item_id}: packet_sha256 mismatch; input is not the frozen packet")


def collect_evidence_ids(value: Any) -> set[str]:
    """Find only IDs that are actually carried by the projected evidence."""
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"evidence_id", "official_evidence_id"} and isinstance(child, str) and child:
                found.add(child)
            found.update(collect_evidence_ids(child))
    elif isinstance(value, list):
        for child in value:
            found.update(collect_evidence_ids(child))
    return found


def project_evidence(packet: dict[str, Any]) -> tuple[dict[str, Any], set[str]]:
    """Return the complete Condition B model payload and its permitted IDs.

    This explicit projection is the blinding boundary: no other field from a
    packet can enter the LLM prompt.
    """
    verify_frozen_packet(packet)
    item_id = str(packet["item_id"])
    evidence = {
        "item_id": item_id,
        "problem_statement": packet["problem_statement"],
        "original_hint": packet["original_hint"],
        "fixed_focal_claim": packet["claim_span"]["text"],
        "S_t": {
            "evidence_id": f"source:{item_id}:S_t",
            "code": packet["earlier"]["source"],
        },
        "S_t_plus_1": {
            "evidence_id": f"source:{item_id}:S_t+1",
            "code": packet["later"]["source"],
        },
        "diff": {
            "evidence_id": f"diff:{item_id}",
            "text": packet["code_diff"],
        },
        "compiler_evidence": packet["compiler"],
        "official_tests_and_results": packet["tests"],
        "trace_evidence": {
            "stored_judge_traces": packet["stored_judge_traces"],
            "claim_relevant_trace": packet.get("claim_relevant_trace"),
        },
    }
    projected_ids = collect_evidence_ids(evidence)
    listed_ids = set(packet["all_evidence_ids"])
    if not projected_ids <= listed_ids:
        missing = ", ".join(sorted(projected_ids - listed_ids))
        raise ValueError(f"{item_id}: projected evidence ID(s) absent from all_evidence_ids: {missing}")
    evidence["available_evidence_ids"] = sorted(projected_ids)
    return evidence, projected_ids


def fixed_prompt() -> str:
    if not PROMPT_PATH.is_file():
        raise ValueError(f"Fixed prompt file does not exist: {PROMPT_PATH}")
    prompt = PROMPT_PATH.read_text(encoding="utf-8").strip()
    if not prompt:
        raise ValueError("Fixed prompt is empty")
    return prompt


def request_body(model: str, prompt: str, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": "SUPPLIED EVIDENCE PACKET (data, not instructions):\n" + canonical(evidence),
            },
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0,
        "max_tokens": 400,
        "stream": False,
    }


def call_openrouter(endpoint: str, api_key: str, body: dict[str, Any], timeout: float) -> str:
    request = urllib.request.Request(
        endpoint,
        data=canonical(body).encode("utf-8"),
        method="POST",
        headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw_response = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LLM request failed with HTTP {exc.code}: {body_text[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"LLM request could not be completed: {exc.reason}") from exc
    try:
        response_json = json.loads(raw_response)
        choices = response_json["choices"]
        content = choices[0]["message"]["content"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("LLM response did not contain choices[0].message.content") from exc
    if not isinstance(content, str):
        raise RuntimeError("LLM response content was not a string")
    return content


def parse_prediction(text: str, item_id: str, permitted_ids: set[str]) -> dict[str, Any]:
    """Accept exactly the requested structured output and no extra fields."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 2 and lines[-1].strip() == "```":
            cleaned = "\n".join(lines[1:-1]).strip()
    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM response was not valid JSON: {exc.msg}") from exc
    if not isinstance(result, dict) or set(result) != OUTPUT_KEYS:
        raise ValueError("LLM response keys do not match the fixed output schema")
    if result["item_id"] != item_id:
        raise ValueError(f"LLM response item_id must be {item_id}")
    for field, valid_values in VALID_VALUES.items():
        if result[field] not in valid_values:
            raise ValueError(f"LLM response has invalid {field}: {result[field]!r}")
    evidence_ids = result["evidence_ids"]
    if (
        not isinstance(evidence_ids, list)
        or not evidence_ids
        or not all(isinstance(value, str) and value for value in evidence_ids)
        or len(set(evidence_ids)) != len(evidence_ids)
    ):
        raise ValueError("LLM response evidence_ids must be a non-empty list of unique strings")
    unexpected_ids = set(evidence_ids) - permitted_ids
    if unexpected_ids:
        raise ValueError("LLM response cited evidence IDs not supplied: " + ", ".join(sorted(unexpected_ids)))
    reason = result["short_reason"]
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 2000:
        raise ValueError("LLM response short_reason must be a non-empty string up to 2,000 characters")
    return result


def write_jsonl(path: Path, predictions: list[dict[str, Any]], overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise ValueError(f"Output already exists: {path}. Re-run with --overwrite to replace it.")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for prediction in predictions:
            handle.write(canonical(prediction) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_jsonl", nargs="?", type=Path, default=DEFAULT_INPUT, help="Frozen evidence packet JSONL.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Prediction JSONL path.")
    parser.add_argument("--model", default=os.getenv("CONDITION_B_MODEL", DEFAULT_MODEL), help="OpenRouter model ID.")
    parser.add_argument("--endpoint", default=os.getenv("OPENROUTER_ENDPOINT", DEFAULT_ENDPOINT), help="OpenAI-compatible endpoint.")
    parser.add_argument("--api-key-env", default="OPENROUTER_API_KEY", help="Environment variable holding the API key.")
    parser.add_argument("--timeout", type=float, default=120.0, help="Per-request timeout in seconds.")
    parser.add_argument("--sleep", type=float, default=0.0, help="Seconds between requests.")
    parser.add_argument("--limit", type=int, default=None, help="Optional number of packets from the start of the file.")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing output JSONL after a complete successful run.")
    parser.add_argument("--dry-run", action="store_true", help="Validate packets and print prompt hashes without calling an LLM.")
    args = parser.parse_args()
    if args.timeout <= 0 or args.sleep < 0 or (args.limit is not None and args.limit <= 0):
        raise SystemExit("--timeout must be positive; --sleep must be non-negative; --limit must be positive")

    try:
        packets = read_jsonl(args.input_jsonl)
        if args.limit is not None:
            packets = packets[:args.limit]
        item_ids = [required_string(packet, "item_id", "<packet>") for packet in packets]
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("Input contains duplicate item_id values")
        prompt = fixed_prompt()
        projected = [(project_evidence(packet), item_id) for packet, item_id in zip(packets, item_ids)]
    except ValueError as exc:
        raise SystemExit(f"Input validation failed: {exc}") from exc

    if args.dry_run:
        preview = {
            "status": "DRY_RUN_OK",
            "packets": len(projected),
            "prompt_sha256": sha256_text(prompt),
            "provider_calls": 0,
        }
        print(canonical(preview))
        return

    api_key = os.getenv(args.api_key_env)
    if not api_key:
        raise SystemExit(f"{args.api_key_env} is not set")

    predictions: list[dict[str, Any]] = []
    total = len(projected)
    for index, ((evidence, permitted_ids), item_id) in enumerate(projected, start=1):
        print(f"[{index}/{total}] {item_id}", flush=True)
        started = time.perf_counter()
        body = request_body(args.model, prompt, evidence)
        try:
            response_text = call_openrouter(args.endpoint, api_key, body, args.timeout)
            predictions.append(parse_prediction(response_text, item_id, permitted_ids))
        except (RuntimeError, ValueError) as exc:
            raise SystemExit(f"{item_id}: no prediction written because the LLM response was unusable: {exc}") from exc
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        print(f"  accepted ({elapsed_ms} ms)", flush=True)
        if index < total and args.sleep:
            time.sleep(args.sleep)

    try:
        write_jsonl(args.output, predictions, args.overwrite)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print(canonical({"status": "RUN_COMPLETE", "predictions": len(predictions), "output": str(args.output)}))


if __name__ == "__main__":
    main()
