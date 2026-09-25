#!/usr/bin/env python3
"""Run the evidence-matched, fixed-prompt Condition B baseline.

The runner projects only the fields admitted by Condition B from a frozen
evidence packet. It never reads human annotations, adjudications, expected
lifecycle labels, or any RevGround decision procedure.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import secrets
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
DEFAULT_RUN_ROOT = BASELINE_DIR / "outputs" / "runs"
DEFAULT_ENDPOINT = "https://api.z.ai/api/coding/paas/v4/chat/completions"
DEFAULT_MODEL = "glm-5.3"
DEFAULT_API_KEY_ENV = "GLM_API_KEY"
DEFAULT_SMOKE_LIMIT = 5
DEFAULT_MAX_TOKENS = 5000

# These are reference-answer or method-output fields. They are intentionally
# rejected at the projection boundary even if a future packet accidentally
# contains one of them.
FORBIDDEN_REFERENCE_FIELDS = {
    "a01_label",
    "a02_label",
    "adjudicated_gold",
    "adjudicated_answer",
    "expected_answer",
    "expected_lifecycle",
    "predicted_label",
    "system_prediction",
    "annotator_1",
    "annotator_2",
}

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


def forbidden_reference_fields(value: Any) -> set[str]:
    """Return reference-answer keys found anywhere in a projected payload."""
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).strip().lower()
            if normalized in FORBIDDEN_REFERENCE_FIELDS or normalized.startswith(("a01", "a02")):
                found.add(str(key))
            found.update(forbidden_reference_fields(child))
    elif isinstance(value, list):
        for child in value:
            found.update(forbidden_reference_fields(child))
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
    forbidden = forbidden_reference_fields(evidence)
    if forbidden:
        raise ValueError(
            f"{item_id}: projected evidence contains forbidden reference field(s): "
            + ", ".join(sorted(forbidden))
        )
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


def request_body(
    model: str, prompt: str, evidence: dict[str, Any], max_tokens: int = DEFAULT_MAX_TOKENS
) -> dict[str, Any]:
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
        "max_tokens": max_tokens,
        "stream": False,
    }


class ProviderResponseError(RuntimeError):
    """Provider or response-shape failure retaining redacted raw response data."""

    def __init__(self, message: str, *, status: int | None = None, raw_response: str = "") -> None:
        super().__init__(message)
        self.status = status
        self.raw_response = raw_response


def call_provider(
    endpoint: str, api_key: str, body: dict[str, Any], timeout: float
) -> tuple[str, str, int | None, str | None, str | None]:
    """Call an OpenAI-compatible GLM endpoint.

    Returns completion text, raw provider response, HTTP status, provider
    response ID, and returned model. The API key is never returned or logged.
    """
    request = urllib.request.Request(
        endpoint,
        data=canonical(body).encode("utf-8"),
        method="POST",
        headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", None)
            raw_response = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        raise ProviderResponseError(
            f"LLM request failed with HTTP {exc.code}: {body_text[:500]}",
            status=exc.code,
            raw_response=body_text,
        ) from exc
    except urllib.error.URLError as exc:
        raise ProviderResponseError(f"LLM request could not be completed: {exc.reason}") from exc
    try:
        response_json = json.loads(raw_response)
        choices = response_json["choices"]
        content = choices[0]["message"]["content"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise ProviderResponseError(
            "LLM response did not contain choices[0].message.content",
            status=status,
            raw_response=raw_response,
        ) from exc
    if not isinstance(content, str):
        raise ProviderResponseError(
            "LLM response content was not a string",
            status=status,
            raw_response=raw_response,
        )
    response_id = response_json.get("id") if isinstance(response_json.get("id"), str) else None
    if response_id is None and isinstance(response_json.get("request_id"), str):
        response_id = response_json["request_id"]
    returned_model = response_json.get("model") if isinstance(response_json.get("model"), str) else None
    return content, raw_response, status, response_id, returned_model


def response_telemetry(raw_response: str) -> dict[str, Any]:
    """Extract provider usage and finish metadata without estimating tokens."""
    telemetry: dict[str, Any] = {
        "prompt_tokens": None,
        "completion_tokens": None,
        "reasoning_tokens": None,
        "total_tokens": None,
        "finish_reason": None,
    }
    if not raw_response:
        return telemetry
    try:
        response_json = json.loads(raw_response)
    except json.JSONDecodeError:
        return telemetry
    usage = response_json.get("usage")
    if isinstance(usage, dict):
        for field in ("prompt_tokens", "completion_tokens", "total_tokens"):
            value = usage.get(field)
            if isinstance(value, int) and value >= 0:
                telemetry[field] = value
        completion_details = usage.get("completion_tokens_details")
        if isinstance(completion_details, dict):
            value = completion_details.get("reasoning_tokens")
            if isinstance(value, int) and value >= 0:
                telemetry["reasoning_tokens"] = value
        if telemetry["reasoning_tokens"] is None:
            value = usage.get("reasoning_tokens")
            if isinstance(value, int) and value >= 0:
                telemetry["reasoning_tokens"] = value
    choices = response_json.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        finish_reason = choices[0].get("finish_reason")
        if isinstance(finish_reason, str):
            telemetry["finish_reason"] = finish_reason
    return telemetry


def call_openrouter(endpoint: str, api_key: str, body: dict[str, Any], timeout: float) -> str:
    """Backward-compatible completion-only wrapper for local callers."""
    return call_provider(endpoint, api_key, body, timeout)[0]


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


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(canonical(value) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def append_jsonl(handle: Any, value: dict[str, Any]) -> None:
    handle.write(canonical(value) + "\n")
    handle.flush()
    os.fsync(handle.fileno())


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def new_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + secrets.token_hex(4)


def select_packets(
    packets: list[dict[str, Any]], *, item_ids_arg: str | None, limit: int | None
) -> list[dict[str, Any]]:
    """Select an explicit subset while preserving requested item order."""
    by_id = {required_string(packet, "item_id", "<packet>"): packet for packet in packets}
    if item_ids_arg:
        requested = [item.strip() for item in item_ids_arg.split(",") if item.strip()]
        if not requested or len(requested) != len(set(requested)):
            raise ValueError("--item-ids must contain one or more unique comma-separated IDs")
        missing = [item_id for item_id in requested if item_id not in by_id]
        if missing:
            raise ValueError("Requested item ID(s) not found: " + ", ".join(missing))
        return [by_id[item_id] for item_id in requested]
    effective_limit = DEFAULT_SMOKE_LIMIT if limit is None else limit
    return packets[:effective_limit]


def artifact_paths(args: argparse.Namespace) -> dict[str, Path]:
    """Resolve a fresh default run directory, or an explicit output location."""
    if args.run_dir is not None:
        root = args.run_dir
    elif args.output is not None:
        root = args.output.parent
    else:
        root = DEFAULT_RUN_ROOT / (args.run_id or new_run_id())
    return {
        "predictions": args.output or root / "predictions.jsonl",
        "raw_responses": args.raw_output or root / "raw_responses.jsonl",
        "errors": args.errors_output or root / "errors.jsonl",
        "request_metadata": args.request_metadata_output or root / "request_metadata.jsonl",
        "run_metadata": args.run_metadata_output or root / "run_metadata.json",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_jsonl", nargs="?", type=Path, default=DEFAULT_INPUT, help="Frozen evidence packet JSONL.")
    parser.add_argument("--output", type=Path, default=None, help="Prediction JSONL path; default is a fresh run directory.")
    parser.add_argument("--model", default=os.getenv("CONDITION_B_MODEL", DEFAULT_MODEL), help="GLM model ID.")
    parser.add_argument("--endpoint", default=os.getenv("GLM_API_ENDPOINT", DEFAULT_ENDPOINT), help="OpenAI-compatible GLM endpoint.")
    parser.add_argument("--api-key-env", default=DEFAULT_API_KEY_ENV, help="Environment variable holding the API key.")
    parser.add_argument("--timeout", type=float, default=120.0, help="Per-request timeout in seconds.")
    parser.add_argument("--sleep", type=float, default=0.0, help="Seconds between requests.")
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS, help="Maximum completion tokens; GLM-5.3 needs room for reasoning plus JSON.")
    parser.add_argument("--limit", type=int, default=DEFAULT_SMOKE_LIMIT, help="Number of packets from the start; default is the five-case smoke test.")
    parser.add_argument("--item-ids", default=None, help="Optional comma-separated item IDs, in request order.")
    parser.add_argument("--run-id", default=None, help="Run ID used when creating the default fresh run directory.")
    parser.add_argument("--run-dir", type=Path, default=None, help="Explicit artifact directory.")
    parser.add_argument("--raw-output", type=Path, default=None, help="Raw provider response JSONL path.")
    parser.add_argument("--errors-output", type=Path, default=None, help="Per-item error JSONL path.")
    parser.add_argument("--request-metadata-output", type=Path, default=None, help="Per-request metadata JSONL path.")
    parser.add_argument("--run-metadata-output", type=Path, default=None, help="Run summary JSON path.")
    parser.add_argument("--overwrite", action="store_true", help="Replace explicit artifact files if they already exist.")
    parser.add_argument("--dry-run", action="store_true", help="Validate packets and print prompt hashes without calling an LLM.")
    args = parser.parse_args()
    if args.timeout <= 0 or args.sleep < 0 or args.max_tokens <= 0 or (args.limit is not None and args.limit <= 0):
        raise SystemExit("--timeout and --max-tokens must be positive; --sleep must be non-negative; --limit must be positive")

    try:
        packets = read_jsonl(args.input_jsonl)
        packets = select_packets(packets, item_ids_arg=args.item_ids, limit=args.limit)
        if not packets:
            raise ValueError("Selection produced no packets")
        item_ids = [required_string(packet, "item_id", "<packet>") for packet in packets]
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("Input contains duplicate item_id values")
        prompt = fixed_prompt()
        projected = [(project_evidence(packet), item_id) for packet, item_id in zip(packets, item_ids)]
    except ValueError as exc:
        raise SystemExit(f"Input validation failed: {exc}") from exc

    paths = artifact_paths(args)
    if args.dry_run:
        preview = {
            "status": "DRY_RUN_OK",
            "packets": len(projected),
            "item_ids": item_ids,
            "model": args.model,
            "endpoint": args.endpoint,
            "prompt_sha256": sha256_text(prompt),
            "evidence_top_level_keys": sorted(projected[0][0][0]),
            "evidence_ids_by_item": {item_id: sorted(permitted_ids) for (evidence, permitted_ids), item_id in projected},
            "forbidden_reference_fields_by_item": {
                item_id: sorted(forbidden_reference_fields(evidence))
                for (evidence, _), item_id in projected
            },
            "provider_calls": 0,
        }
        print(canonical(preview))
        return

    api_key = os.getenv(args.api_key_env)
    if not api_key:
        raise SystemExit(f"{args.api_key_env} is not set")

    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and not args.overwrite:
            raise SystemExit(f"Artifact already exists: {path}. Use a fresh run or --overwrite.")

    started_at = utc_now()
    predictions: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    total = len(projected)
    usage_totals = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "reasoning_tokens": 0,
        "total_tokens": 0,
    }
    requests_with_usage = 0
    request_latencies_ms: list[int] = []
    with (
        paths["predictions"].open("w", encoding="utf-8", newline="\n") as predictions_handle,
        paths["raw_responses"].open("w", encoding="utf-8", newline="\n") as raw_handle,
        paths["errors"].open("w", encoding="utf-8", newline="\n") as errors_handle,
        paths["request_metadata"].open("w", encoding="utf-8", newline="\n") as request_metadata_handle,
    ):
        for index, ((evidence, permitted_ids), item_id) in enumerate(projected, start=1):
            print(f"[{index}/{total}] {item_id}", flush=True)
            request_started = time.perf_counter()
            request_started_at = utc_now()
            body = request_body(args.model, prompt, evidence, args.max_tokens)
            request_hash = sha256_text(canonical(body))
            evidence_hash = sha256_text(canonical(evidence))
            metadata: dict[str, Any] = {
                "item_id": item_id,
                "sequence": index,
                "model_requested": args.model,
                "max_tokens": args.max_tokens,
                "endpoint": args.endpoint,
                "prompt_sha256": sha256_text(prompt),
                "request_sha256": request_hash,
                "evidence_sha256": evidence_hash,
                "evidence_top_level_keys": sorted(evidence),
                "available_evidence_ids": sorted(permitted_ids),
                "forbidden_reference_fields": sorted(forbidden_reference_fields(evidence)),
                "started_at": request_started_at,
            }
            raw_response = ""
            response_text = ""
            status: int | None = None
            response_id: str | None = None
            returned_model: str | None = None
            try:
                response_text, raw_response, status, response_id, returned_model = call_provider(
                    args.endpoint, api_key, body, args.timeout
                )
                prediction = parse_prediction(response_text, item_id, permitted_ids)
                predictions.append(prediction)
                append_jsonl(predictions_handle, prediction)
                outcome = "accepted"
                print(f"  accepted ({round((time.perf_counter() - request_started) * 1000)} ms)", flush=True)
            except (ProviderResponseError, ValueError) as exc:
                if isinstance(exc, ProviderResponseError):
                    raw_response = exc.raw_response
                    status = exc.status
                error_record = {
                    "item_id": item_id,
                    "sequence": index,
                    "request_sha256": request_hash,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "http_status": getattr(exc, "status", status),
                    "raw_response_sha256": sha256_text(raw_response) if raw_response else None,
                    "occurred_at": utc_now(),
                }
                errors.append(error_record)
                append_jsonl(errors_handle, error_record)
                outcome = "error"
                print(f"  error: {exc}", flush=True)
            raw_record = {
                "item_id": item_id,
                "sequence": index,
                "request_sha256": request_hash,
                "http_status": status,
                "provider_response_id": response_id,
                "returned_model": returned_model,
                "raw_response": raw_response,
                "completion_content": response_text or None,
                "telemetry": response_telemetry(raw_response),
                "received_at": utc_now(),
            }
            append_jsonl(raw_handle, raw_record)
            telemetry = response_telemetry(raw_response)
            latency_ms = round((time.perf_counter() - request_started) * 1000)
            request_latencies_ms.append(latency_ms)
            has_complete_usage = all(
                isinstance(telemetry[field], int)
                for field in ("prompt_tokens", "completion_tokens", "reasoning_tokens", "total_tokens")
            )
            if has_complete_usage:
                requests_with_usage += 1
                for field in usage_totals:
                    usage_totals[field] += telemetry[field]
            metadata.update(
                {
                    "status": outcome,
                    "http_status": status,
                    "provider_response_id": response_id,
                    "model_returned": returned_model,
                    "response_sha256": sha256_text(raw_response) if raw_response else None,
                    "prompt_tokens": telemetry["prompt_tokens"],
                    "completion_tokens": telemetry["completion_tokens"],
                    "reasoning_tokens": telemetry["reasoning_tokens"],
                    "total_tokens": telemetry["total_tokens"],
                    "finish_reason": telemetry["finish_reason"],
                    "usage_available": has_complete_usage,
                    "latency_ms": latency_ms,
                    "elapsed_ms": latency_ms,
                    "finished_at": utc_now(),
                }
            )
            append_jsonl(request_metadata_handle, metadata)
            if index < total and args.sleep:
                time.sleep(args.sleep)

    finished_at = utc_now()
    total_latency_ms = sum(request_latencies_ms)
    run_metadata = {
        "format_version": "revground-condition-b-glm-smoke-v1.1.0",
        "status": "RUN_COMPLETE" if not errors else "RUN_WITH_ERRORS",
        "started_at": started_at,
        "finished_at": finished_at,
        "model_requested": args.model,
        "endpoint": args.endpoint,
        "api_key_env": args.api_key_env,
        "input_jsonl": str(args.input_jsonl),
        "prompt_sha256": sha256_text(prompt),
        "selected_item_ids": item_ids,
        "requested_items": total,
        "accepted_predictions": len(predictions),
        "errors": len(errors),
        "one_prediction_per_item": len(predictions) == total,
        "token_usage": {
            **usage_totals,
            "requests_with_usage": requests_with_usage,
            "requests_without_usage": total - requests_with_usage,
        },
        "latency_summary": {
            "request_count": len(request_latencies_ms),
            "total_latency_ms": total_latency_ms,
            "mean_latency_ms": round(total_latency_ms / len(request_latencies_ms))
            if request_latencies_ms
            else None,
            "min_latency_ms": min(request_latencies_ms) if request_latencies_ms else None,
            "max_latency_ms": max(request_latencies_ms) if request_latencies_ms else None,
        },
        "forbidden_reference_fields_seen": sorted(
            set().union(*(forbidden_reference_fields(evidence) for evidence, _ in projected))
        ),
        "artifacts": {name: str(path) for name, path in paths.items()},
    }
    write_json(paths["run_metadata"], run_metadata)
    print(canonical(run_metadata))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
