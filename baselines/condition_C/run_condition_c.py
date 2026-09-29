#!/usr/bin/env python3
"""Run Condition C: the Condition B evidence packet with Feedback-lifecycle-audit auditing."""
from __future__ import annotations

import argparse
from pathlib import Path
import json
import os
import sys
import time
from typing import Any


BASELINE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASELINE_DIR.parents[1]
CONDITION_B_DIR = BASELINE_DIR.parent / "condition_B"
if str(CONDITION_B_DIR) not in sys.path:
    sys.path.insert(0, str(CONDITION_B_DIR))
import run_baseline as condition_b  # noqa: E402


PROMPT_PATH = BASELINE_DIR / "prompt.txt"
DEFAULT_INPUT = REPO_ROOT / "annotation" / "development_50" / "development_50_evidence_frozen_v1.jsonl"
DEFAULT_RUN_ROOT = BASELINE_DIR / "outputs" / "runs"
DEFAULT_ENDPOINT = condition_b.DEFAULT_ENDPOINT
DEFAULT_MODEL = condition_b.DEFAULT_MODEL
DEFAULT_API_KEY_ENV = condition_b.DEFAULT_API_KEY_ENV
DEFAULT_SMOKE_LIMIT = condition_b.DEFAULT_SMOKE_LIMIT
# The explicit audit procedure is longer than Condition B's baseline prompt,
# and B's known long-response retries used a 12,000-token budget.
DEFAULT_MAX_TOKENS = 12000

C_MODEL_KEYS = condition_b.OUTPUT_KEYS | {"abstain", "abstention_reason"}
TERMINAL_TEST_STATUSES = {
    "pending",
    "running",
    "queued",
    "in_progress",
    "unknown",
    "not_started",
}


def fixed_prompt() -> str:
    if not PROMPT_PATH.is_file():
        raise ValueError(f"Fixed prompt file does not exist: {PROMPT_PATH}")
    prompt = PROMPT_PATH.read_text(encoding="utf-8").strip()
    if not prompt:
        raise ValueError("Fixed Condition C prompt is empty")
    return prompt


def strip_json_fence(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 2 and lines[-1].strip() == "```":
            cleaned = "\n".join(lines[1:-1]).strip()
    return cleaned


def parse_audit(text: str, item_id: str, permitted_ids: set[str]) -> dict[str, Any]:
    try:
        result = json.loads(strip_json_fence(text))
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM response was not valid JSON: {exc.msg}") from exc
    if not isinstance(result, dict) or set(result) != C_MODEL_KEYS:
        raise ValueError("LLM response keys do not match the fixed Condition C output schema")
    base = {key: result[key] for key in condition_b.OUTPUT_KEYS}
    parsed_base = condition_b.parse_prediction(
        condition_b.canonical(base), item_id, permitted_ids
    )
    if not isinstance(result["abstain"], bool):
        raise ValueError("LLM response abstain must be a boolean")
    abstention_reason = result["abstention_reason"]
    if not isinstance(abstention_reason, str) or len(abstention_reason) > 2000:
        raise ValueError("LLM response abstention_reason must be a string up to 2,000 characters")
    if result["abstain"] and not abstention_reason.strip():
        raise ValueError("LLM response abstention_reason is required when abstain is true")
    parsed_base.update(
        {
            "abstain": result["abstain"],
            "abstention_reason": abstention_reason,
        }
    )
    return parsed_base


def _status_is_incomplete(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return True
    return value.strip().lower() in TERMINAL_TEST_STATUSES


def _evidence_id(value: Any) -> str | None:
    if isinstance(value, dict):
        for key in ("evidence_id", "official_evidence_id"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate:
                return candidate
    return None


def _check_evidence_id(issues: list[str], evidence_id: str | None, allowed: set[str], label: str) -> None:
    if evidence_id is None:
        issues.append(f"{label} is missing an evidence ID")
    elif evidence_id not in allowed:
        issues.append(f"{label} references an evidence ID not supplied in the packet: {evidence_id}")


def validate_packet(
    packet: dict[str, Any], evidence: dict[str, Any], permitted_ids: set[str]
) -> list[str]:
    """Validate usability without adding any validation result to the GLM input."""
    item_id = str(packet.get("item_id", "<unknown>"))
    issues: list[str] = []
    required_values = {
        "problem statement": evidence.get("problem_statement"),
        "focal claim": evidence.get("fixed_focal_claim"),
        "S_t code": (evidence.get("S_t") or {}).get("code") if isinstance(evidence.get("S_t"), dict) else None,
        "S_t+1 code": (evidence.get("S_t_plus_1") or {}).get("code") if isinstance(evidence.get("S_t_plus_1"), dict) else None,
        "diff": (evidence.get("diff") or {}).get("text") if isinstance(evidence.get("diff"), dict) else None,
    }
    for label, value in required_values.items():
        if not isinstance(value, str) or not value.strip():
            issues.append(f"{label} is missing")

    forbidden = condition_b.forbidden_reference_fields(packet)
    if forbidden:
        issues.append("packet contains forbidden gold/human/reference fields: " + ", ".join(sorted(forbidden)))
    if packet.get("packet_prepared_without_method_predictions") is not True:
        issues.append("packet is not explicitly marked packet_prepared_without_method_predictions=true")

    listed_ids = packet.get("all_evidence_ids")
    if not isinstance(listed_ids, list) or not all(isinstance(value, str) and value for value in listed_ids):
        issues.append("all_evidence_ids is missing or malformed")
        listed_id_set: set[str] = set()
    else:
        listed_id_set = set(listed_ids)
        if not permitted_ids <= listed_id_set:
            issues.append("projected evidence IDs are absent from all_evidence_ids")
        if set(evidence.get("available_evidence_ids", [])) != permitted_ids:
            issues.append("available_evidence_ids does not match the projected evidence IDs")

    compiler = evidence.get("compiler_evidence")
    if not isinstance(compiler, dict):
        issues.append("compiler evidence is missing or not an object")
    else:
        for state in ("earlier", "later"):
            entry = compiler.get(state)
            if not isinstance(entry, dict):
                issues.append(f"compiler evidence {state} entry is missing")
                continue
            _check_evidence_id(issues, _evidence_id(entry), permitted_ids, f"compiler evidence {state}")
            if _status_is_incomplete(entry.get("status")):
                issues.append(f"compiler evidence {state} has no completed status")
            # A timeout remains a compiler-run outcome, but is never reclassified
            # as a compiler error or silently treated as an execution failure.

    tests = evidence.get("official_tests_and_results")
    if not isinstance(tests, list) or not tests:
        issues.append("official tests are missing or empty")
    else:
        for index, test in enumerate(tests):
            if not isinstance(test, dict):
                issues.append(f"test {index} is not an object")
                continue
            official_id = _evidence_id(test)
            _check_evidence_id(issues, official_id, permitted_ids, f"test {index}")
            for state in ("earlier", "later"):
                result = test.get(state)
                label = f"test {index} {state} result"
                if not isinstance(result, dict):
                    issues.append(f"{label} is missing")
                    continue
                if _status_is_incomplete(result.get("status")):
                    issues.append(f"{label} has no completed status")
                execution_id = _evidence_id(result)
                _check_evidence_id(issues, execution_id, permitted_ids, label)
                if execution_id and ":compile" in execution_id:
                    issues.append(f"{label} is indistinguishable from compiler evidence")

    traces = evidence.get("trace_evidence")
    if not isinstance(traces, dict):
        issues.append("trace evidence is missing or not an object")
    else:
        stored = traces.get("stored_judge_traces")
        if not isinstance(stored, dict):
            issues.append("stored judge traces are missing or not an object")
        else:
            for state in ("earlier", "later"):
                trace = stored.get(state)
                _check_evidence_id(issues, _evidence_id(trace), permitted_ids, f"stored trace {state}")
                if not isinstance(trace, dict):
                    issues.append(f"stored trace {state} is missing")
        trace_ids = condition_b.collect_evidence_ids(traces)
        missing_trace_ids = trace_ids - permitted_ids
        if missing_trace_ids:
            issues.append("trace evidence references unsupplied IDs: " + ", ".join(sorted(missing_trace_ids)))

    if listed_id_set and not listed_id_set.issuperset(permitted_ids):
        issues.append(f"{item_id}: not all projected IDs are listed")
    return list(dict.fromkeys(issues))


def expected_lifecycle(original: str, target: str) -> str:
    if original == "REFUTED":
        return "RETRACT"
    if original == "SUPPORTED" and target == "PRESENT":
        return "KEEP"
    if original == "SUPPORTED" and target == "RESOLVED":
        return "RETIRE"
    return "UNSURE"


def validate_decision(prediction: dict[str, Any]) -> dict[str, Any]:
    """Apply the lifecycle table after parsing; model JSON is not trusted by itself."""
    original = prediction["original_validity"]
    target = prediction["target_state_t1"]
    model_lifecycle = prediction["lifecycle_label"]
    expected = expected_lifecycle(original, target)
    violations: list[str] = []
    if original == "REFUTED" and target != "NOT_APPLICABLE":
        violations.append("REFUTED original claim requires target_state_t1=NOT_APPLICABLE")
    if original == "SUPPORTED" and target == "NOT_APPLICABLE":
        violations.append("SUPPORTED original claim cannot use target_state_t1=NOT_APPLICABLE")
    if original == "INDETERMINATE" and target != "INDETERMINATE":
        violations.append("INDETERMINATE original claim requires target_state_t1=INDETERMINATE")
    if prediction["abstain"] and model_lifecycle != "UNSURE":
        violations.append("abstain=true requires lifecycle_label=UNSURE")
    if not prediction["abstain"] and model_lifecycle != expected:
        violations.append(
            f"Lifecycle output inconsistent with decision table; expected {expected}, got {model_lifecycle}"
        )

    final = dict(prediction)
    final["model_lifecycle_label"] = model_lifecycle
    final["rule_expected_lifecycle"] = expected
    final["decision_rule_violation"] = bool(violations)
    if violations:
        final["lifecycle_label"] = "UNSURE"
        final["abstain"] = True
        final["abstention_reason"] = "; ".join(violations)
        final["decision_validation"] = "RULE_VIOLATION_ABSTAINED"
    elif prediction["abstain"]:
        final["lifecycle_label"] = "UNSURE"
        final["decision_validation"] = "ABSTAINED"
    else:
        final["decision_validation"] = "PASS"
    return final


def deterministic_abstention(
    item_id: str, permitted_ids: set[str], issues: list[str]
) -> dict[str, Any]:
    return {
        "item_id": item_id,
        "original_validity": "INDETERMINATE",
        "target_state_t1": "INDETERMINATE",
        "lifecycle_label": "UNSURE",
        "instructional_priority": "UNKNOWN",
        "leakage_label": "NOT_EVALUATED",
        "evidence_ids": sorted(permitted_ids),
        "short_reason": "Deterministic evidence validation failed; no GLM decision was requested.",
        "abstain": True,
        "abstention_reason": "; ".join(issues),
        "model_lifecycle_label": None,
        "rule_expected_lifecycle": "UNSURE",
        "decision_rule_violation": False,
        "decision_validation": "DETERMINISTIC_PACKET_ABSTENTION",
        "packet_validation_issues": issues,
    }


def artifact_paths(args: argparse.Namespace) -> dict[str, Path]:
    if args.run_dir is not None:
        root = args.run_dir
    elif args.output is not None:
        root = args.output.parent
    else:
        root = DEFAULT_RUN_ROOT / (args.run_id or condition_b.new_run_id())
    return {
        "predictions": args.output or root / "predictions.jsonl",
        "raw_responses": args.raw_output or root / "raw_responses.jsonl",
        "errors": args.errors_output or root / "errors.jsonl",
        "request_metadata": args.request_metadata_output or root / "request_metadata.jsonl",
        "run_metadata": args.run_metadata_output or root / "run_metadata.json",
    }


def _write_json(path: Path, value: dict[str, Any]) -> None:
    condition_b.write_json(path, value)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_jsonl", nargs="?", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--model", default=os.getenv("CONDITION_C_MODEL", DEFAULT_MODEL))
    parser.add_argument("--endpoint", default=os.getenv("GLM_API_ENDPOINT", DEFAULT_ENDPOINT))
    parser.add_argument("--api-key-env", default=DEFAULT_API_KEY_ENV)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--sleep", type=float, default=0.0)
    parser.add_argument("--post-429-sleep", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--limit", type=int, default=DEFAULT_SMOKE_LIMIT)
    parser.add_argument("--item-ids", default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--run-dir", type=Path, default=None)
    parser.add_argument("--raw-output", type=Path, default=None)
    parser.add_argument("--errors-output", type=Path, default=None)
    parser.add_argument("--request-metadata-output", type=Path, default=None)
    parser.add_argument("--run-metadata-output", type=Path, default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.timeout <= 0 or args.sleep < 0 or args.post_429_sleep < 0 or args.max_tokens <= 0 or (args.limit is not None and args.limit <= 0):
        raise SystemExit("--timeout and --max-tokens must be positive; pacing values must be non-negative; --limit must be positive")

    try:
        packets = condition_b.read_jsonl(args.input_jsonl)
        packets = condition_b.select_packets(packets, item_ids_arg=args.item_ids, limit=args.limit)
        if not packets:
            raise ValueError("Selection produced no packets")
        item_ids = [condition_b.required_string(packet, "item_id", "<packet>") for packet in packets]
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("Input contains duplicate item_id values")
        prompt = fixed_prompt()
        projected: list[tuple[dict[str, Any], set[str], dict[str, Any], list[str]]] = []
        for packet, item_id in zip(packets, item_ids):
            evidence, permitted_ids = condition_b.project_evidence(packet)
            issues = validate_packet(packet, evidence, permitted_ids)
            projected.append((evidence, permitted_ids, packet, issues))
    except ValueError as exc:
        raise SystemExit(f"Input validation failed: {exc}") from exc

    paths = artifact_paths(args)
    validation_counts: dict[str, int] = {}
    for evidence, _permitted_ids, _packet, issues in projected:
        for issue in issues:
            validation_counts[issue] = validation_counts.get(issue, 0) + 1
    if args.dry_run:
        preview = {
            "status": "DRY_RUN_OK",
            "condition": "C",
            "packets": len(projected),
            "item_ids": item_ids,
            "model": args.model,
            "endpoint": args.endpoint,
            "prompt_sha256": condition_b.sha256_text(prompt),
            "evidence_top_level_keys": sorted(projected[0][0]),
            "evidence_ids_by_item": {item_id: sorted(ids) for (_evidence, ids, _packet, _issues), item_id in zip(projected, item_ids)},
            "forbidden_reference_fields_by_item": {
                item_id: sorted(condition_b.forbidden_reference_fields(evidence))
                for (evidence, _ids, _packet, _issues), item_id in zip(projected, item_ids)
            },
            "packet_validation_issue_counts": validation_counts,
            "packet_validation_passes": sum(not issues for _evidence, _ids, _packet, issues in projected),
            "packet_validation_abstentions": sum(bool(issues) for _evidence, _ids, _packet, issues in projected),
            "provider_calls": 0,
            "same_condition_b_projection": True,
        }
        print(condition_b.canonical(preview))
        return

    api_key = os.getenv(args.api_key_env)
    if not api_key:
        raise SystemExit(f"{args.api_key_env} is not set")
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and not args.overwrite:
            raise SystemExit(f"Artifact already exists: {path}. Use a fresh run or --overwrite.")

    started_at = condition_b.utc_now()
    predictions: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    request_latencies_ms: list[int] = []
    usage_totals = {"prompt_tokens": 0, "completion_tokens": 0, "reasoning_tokens": 0, "total_tokens": 0}
    requests_with_usage = 0
    provider_calls = 0
    decision_rule_violations = 0
    packet_abstentions = 0
    with (
        paths["predictions"].open("w", encoding="utf-8", newline="\n") as predictions_handle,
        paths["raw_responses"].open("w", encoding="utf-8", newline="\n") as raw_handle,
        paths["errors"].open("w", encoding="utf-8", newline="\n") as errors_handle,
        paths["request_metadata"].open("w", encoding="utf-8", newline="\n") as metadata_handle,
    ):
        for index, (evidence, permitted_ids, packet, packet_issues) in enumerate(projected, start=1):
            item_id = item_ids[index - 1]
            print(f"[{index}/{len(projected)}] {item_id}", flush=True)
            request_started = time.perf_counter()
            request_started_at = condition_b.utc_now()
            body = condition_b.request_body(args.model, prompt, evidence, args.max_tokens)
            request_hash = condition_b.sha256_text(condition_b.canonical(body))
            evidence_hash = condition_b.sha256_text(condition_b.canonical(evidence))
            metadata: dict[str, Any] = {
                "condition": "C",
                "item_id": item_id,
                "sequence": index,
                "model_requested": args.model,
                "max_tokens": args.max_tokens,
                "endpoint": args.endpoint,
                "prompt_sha256": condition_b.sha256_text(prompt),
                "request_sha256": request_hash,
                "evidence_sha256": evidence_hash,
                "evidence_top_level_keys": sorted(evidence),
                "available_evidence_ids": sorted(permitted_ids),
                "packet_validation_issues": packet_issues,
                "forbidden_reference_fields": sorted(condition_b.forbidden_reference_fields(evidence)),
                "started_at": request_started_at,
            }
            raw_response = ""
            response_text = ""
            status: int | None = None
            response_id: str | None = None
            returned_model: str | None = None
            outcome = "error"
            if packet_issues:
                prediction = deterministic_abstention(item_id, permitted_ids, packet_issues)
                predictions.append(prediction)
                condition_b.append_jsonl(predictions_handle, prediction)
                error_record = {
                    "condition": "C",
                    "item_id": item_id,
                    "sequence": index,
                    "error_type": "PacketValidationError",
                    "error": "; ".join(packet_issues),
                    "provider_called": False,
                    "occurred_at": condition_b.utc_now(),
                }
                errors.append(error_record)
                condition_b.append_jsonl(errors_handle, error_record)
                packet_abstentions += 1
                outcome = "deterministic_abstention"
            else:
                provider_calls += 1
                try:
                    response_text, raw_response, status, response_id, returned_model = condition_b.call_provider(
                        args.endpoint, api_key, body, args.timeout
                    )
                    parsed = parse_audit(response_text, item_id, permitted_ids)
                    prediction = validate_decision(parsed)
                    predictions.append(prediction)
                    condition_b.append_jsonl(predictions_handle, prediction)
                    if prediction["decision_rule_violation"]:
                        decision_rule_violations += 1
                    outcome = "accepted"
                except (condition_b.ProviderResponseError, ValueError) as exc:
                    if isinstance(exc, condition_b.ProviderResponseError):
                        raw_response = exc.raw_response
                        status = exc.status
                    error_record = {
                        "condition": "C",
                        "item_id": item_id,
                        "sequence": index,
                        "request_sha256": request_hash,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                        "http_status": getattr(exc, "status", status),
                        "provider_called": True,
                        "raw_response_sha256": condition_b.sha256_text(raw_response) if raw_response else None,
                        "occurred_at": condition_b.utc_now(),
                    }
                    errors.append(error_record)
                    condition_b.append_jsonl(errors_handle, error_record)
            telemetry = condition_b.response_telemetry(raw_response)
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
            raw_record = {
                "condition": "C",
                "item_id": item_id,
                "sequence": index,
                "request_sha256": request_hash,
                "provider_called": bool(not packet_issues),
                "http_status": status,
                "provider_response_id": response_id,
                "returned_model": returned_model,
                "raw_response": raw_response,
                "completion_content": response_text or None,
                "telemetry": telemetry,
                "received_at": condition_b.utc_now(),
            }
            condition_b.append_jsonl(raw_handle, raw_record)
            metadata.update(
                {
                    "status": outcome,
                    "provider_called": bool(not packet_issues),
                    "http_status": status,
                    "provider_response_id": response_id,
                    "model_returned": returned_model,
                    "response_sha256": condition_b.sha256_text(raw_response) if raw_response else None,
                    "prompt_tokens": telemetry["prompt_tokens"],
                    "completion_tokens": telemetry["completion_tokens"],
                    "reasoning_tokens": telemetry["reasoning_tokens"],
                    "total_tokens": telemetry["total_tokens"],
                    "finish_reason": telemetry["finish_reason"],
                    "usage_available": has_complete_usage,
                    "latency_ms": latency_ms if not packet_issues else 0,
                    "elapsed_ms": latency_ms,
                    "finished_at": condition_b.utc_now(),
                }
            )
            condition_b.append_jsonl(metadata_handle, metadata)
            print(f"  {outcome} ({latency_ms} ms)", flush=True)
            if index < len(projected):
                delay = args.sleep
                if status == 429:
                    delay = max(delay, args.post_429_sleep)
                if delay:
                    time.sleep(delay)

    finished_at = condition_b.utc_now()
    total_latency_ms = sum(request_latencies_ms)
    run_metadata = {
        "format_version": "revground-condition-c-glm-audit-v1.0.0",
        "condition": "C",
        "status": "RUN_COMPLETE" if not errors else "RUN_WITH_ERRORS",
        "started_at": started_at,
        "finished_at": finished_at,
        "model_requested": args.model,
        "endpoint": args.endpoint,
        "pacing_seconds_between_completed_requests": args.sleep,
        "pacing_seconds_after_http_429": args.post_429_sleep,
        "api_key_env": args.api_key_env,
        "input_jsonl": str(args.input_jsonl),
        "prompt_sha256": condition_b.sha256_text(prompt),
        "selected_item_ids": item_ids,
        "requested_items": len(projected),
        "accepted_predictions": len(predictions),
        "errors": len(errors),
        "provider_calls": provider_calls,
        "packet_validation_abstentions": packet_abstentions,
        "decision_rule_violations": decision_rule_violations,
        "one_prediction_per_item": len(predictions) == len(projected),
        "same_condition_b_projection": True,
        "token_usage": {
            **usage_totals,
            "requests_with_usage": requests_with_usage,
            "requests_without_usage": provider_calls - requests_with_usage,
        },
        "latency_summary": {
            "request_count": provider_calls,
            "total_latency_ms": total_latency_ms,
            "mean_latency_ms": round(total_latency_ms / provider_calls) if provider_calls else None,
            "min_latency_ms": min(request_latencies_ms) if request_latencies_ms else None,
            "max_latency_ms": max(request_latencies_ms) if request_latencies_ms else None,
        },
        "packet_validation_issue_counts": validation_counts,
        "forbidden_reference_fields_seen": sorted(
            set().union(*(condition_b.forbidden_reference_fields(evidence) for evidence, _ids, _packet, _issues in projected))
        ),
        "artifacts": {name: str(path) for name, path in paths.items()},
    }
    _write_json(paths["run_metadata"], run_metadata)
    print(condition_b.canonical(run_metadata))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
