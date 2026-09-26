#!/usr/bin/env python3
"""Replay the frozen development manifest in the locked-down C runner.

This script never sends source code to a model and never executes it on the
host.  It compiles each S_t/S_t+1 source and then passes the same official
tests for both states to ``safe_execute_c``.  The resulting JSONL is an
immutable merge input for the canonical development records.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from utils.safe_execute_c import IMAGE, run_state, temporary_directory


REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT = REPO_ROOT / "annotation" / "development_50" / "development_50_evidence_frozen_v1.jsonl"
OUTPUT = REPO_ROOT / "results" / "development_50" / "runs" / "development_50_execution_results.jsonl"
FORMAT_VERSION = "revground-development-execution-v1.1.0"


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def image_id(image: str) -> str:
    completed = subprocess.run(
        ["docker", "image", "inspect", image, "--format", "{{.Id}}"],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        raise RuntimeError("Isolated runner image is unavailable: " + completed.stderr.strip())
    return completed.stdout.strip()


def official_tests(record: dict[str, Any]) -> list[dict[str, str]]:
    tests = record["tests"]
    return [
        {
            "test_id": str(test["test_case_id"]),
            "input": str(test["input"]),
            "expected_output": str(test["expected_output"]),
        }
        for test in tests
    ]


def normalized_test_status(row: dict[str, Any]) -> str:
    """Accept legacy evidence on read; emit only the explicit v1.1 categories."""
    status = str(row["status"])
    if status in {"PASS", "FAIL", "PROGRAM_TIMEOUT", "RUNTIME_ERROR", "INFRA_TIMEOUT", "NOT_RUN_COMPILE_ERROR"}:
        return status
    if status == "host_timeout":
        return "INFRA_TIMEOUT"
    if status in {"completed", "compile_or_runtime_failure"}:
        exit_code = row.get("returncode", row.get("exit_code"))
        if exit_code == 0:
            return "PASS" if bool(row["normalized_match"]) else "FAIL"
        return "PROGRAM_TIMEOUT" if exit_code == 124 else "RUNTIME_ERROR"
    raise ValueError(f"Unknown test status: {status}")


def test_output(row: dict[str, Any], item_id: str, state: str) -> dict[str, Any]:
    status = normalized_test_status(row)
    exit_code = row["returncode"]
    timed_out = status in {"PROGRAM_TIMEOUT", "INFRA_TIMEOUT"}
    if status == "INFRA_TIMEOUT":
        runtime_error: str | None = "host timeout while waiting for locked-down container"
    elif status == "PROGRAM_TIMEOUT":
        runtime_error = "student program exceeded the in-container execution limit"
    elif status == "RUNTIME_ERROR":
        runtime_error = row["stderr"].strip() or f"non-zero process exit code: {exit_code}"
    elif status == "NOT_RUN_COMPILE_ERROR":
        runtime_error = "not run because compilation failed"
    else:
        runtime_error = None
    return {
        "test_case_id": row["test_id"],
        "status": status,
        "stdout": row["stdout"],
        "stderr": row["stderr"],
        "exit_code": exit_code,
        "timed_out": timed_out,
        "runtime_error": runtime_error,
        "runtime_ms": row["latency_ms"],
        "exact_match": row["exact_match"],
        "normalized_match": row["normalized_match"],
        "evidence_id": f"execution:{item_id}:{state}:{row['test_id']}",
    }


def termination_summary(outputs: list[dict[str, Any]]) -> dict[str, Any]:
    exit_codes = {output["exit_code"] for output in outputs}
    failed = [output for output in outputs if output["runtime_error"]]
    return {
        "exit_code": next(iter(exit_codes)) if len(exit_codes) == 1 else None,
        "timed_out": any(output["timed_out"] for output in outputs),
        "runtime_error": (
            None
            if not failed
            else "Per-test runtime/compile details are recorded in actual_outputs."
        ),
        "runtime_ms": round(sum(float(output["runtime_ms"]) for output in outputs), 2),
    }


def replay_state(
    record: dict[str, Any], state: str, source: str, source_sha256: str,
    work_dir: Path, runner_image: str,
) -> dict[str, Any]:
    item_id = record["item_id"]
    source_path = work_dir / f"{item_id}_{state}.c"
    source_path.write_text(source, encoding="utf-8", newline="\n")
    state_replay = run_state(source_path, official_tests(record), image=runner_image)
    compile_result = state_replay["compiler_result"]
    compile_evidence_id = f"execution:{item_id}:{state}:compile"
    raw_outputs = state_replay["tests"]
    if raw_outputs is None:
        return {
            "status": "completed",
            "compiler_result": compile_result,
            "actual_outputs": None,
            "termination": None,
            "evidence_ids": [compile_evidence_id],
            "source_sha256": source_sha256,
        }
    outputs = [test_output(row, item_id, state) for row in raw_outputs]
    return {
        "status": "completed",
        "compiler_result": compile_result,
        "actual_outputs": outputs,
        "termination": termination_summary(outputs),
        "evidence_ids": [compile_evidence_id, *(output["evidence_id"] for output in outputs)],
        "source_sha256": source_sha256,
    }


def replay_record(record: dict[str, Any], work_dir: Path, runner_image: str, runner_image_id: str) -> dict[str, Any]:
    st = replay_state(record, "st", record["earlier"]["source"], record["earlier"]["source_sha256"], work_dir, runner_image)
    st1 = replay_state(record, "st1", record["later"]["source"], record["later"]["source_sha256"], work_dir, runner_image)
    return {
        "result_format_version": FORMAT_VERSION,
        "item_id": record["item_id"],
        "packet_id": record["packet_id"],
        "transition_id": record["transition_id"],
        "st_source_sha256": record["earlier"]["source_sha256"],
        "st1_source_sha256": record["later"]["source_sha256"],
        "runner_image": runner_image,
        "runner_image_id": runner_image_id,
        "st": st,
        "st1": st1,
        "claim_relevant_trace": None,
        "evidence_ids": [*st["evidence_ids"], *st1["evidence_ids"]],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=INPUT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--image", default=IMAGE)
    parser.add_argument("--mode", choices=("verify", "run"), default="verify")
    parser.add_argument("--state-workers", type=int, default=1)
    parser.add_argument(
        "--item-ids",
        default=None,
        help="Comma-separated DEV IDs for an audited replacement-only replay; the input still must contain all 50 records.",
    )
    args = parser.parse_args()
    records = read_jsonl(args.input)
    if args.state_workers < 1 or args.state_workers > 8:
        raise SystemExit("--state-workers must be between 1 and 8")
    if len(records) != 50 or [record["item_id"] for record in records] != [f"DEV_{index:03d}" for index in range(1, 51)]:
        raise SystemExit("Expected frozen DEV_001..DEV_050 development manifest")
    for record in records:
        official_tests(record)
    if args.item_ids is None:
        selected_records = records
    else:
        requested_ids = [item_id.strip() for item_id in args.item_ids.split(",") if item_id.strip()]
        if not requested_ids or len(set(requested_ids)) != len(requested_ids):
            raise SystemExit("--item-ids must contain distinct non-empty DEV IDs")
        by_id = {record["item_id"]: record for record in records}
        if any(item_id not in by_id for item_id in requested_ids):
            raise SystemExit("--item-ids contains an ID outside DEV_001..DEV_050")
        selected_records = [by_id[item_id] for item_id in requested_ids]
    if args.mode == "verify":
        print(canonical({"status": "PASS", "records": len(selected_records), "state_replays": len(selected_records) * 2, "official_test_entries": sum(len(official_tests(record)) for record in selected_records) * 2, "provider_calls": 0}))
        return
    if args.output.exists():
        raise SystemExit(f"Output already exists; do not overwrite execution evidence: {args.output}")
    resolved_image_id = image_id(args.image)
    results: list[dict[str, Any]] = []
    with temporary_directory(prefix="revground_development_replay_") as directory:
        work_dir = Path(directory)
        def one(record: dict[str, Any]) -> dict[str, Any]:
            return replay_record(record, work_dir, args.image, resolved_image_id)
        with ThreadPoolExecutor(max_workers=args.state_workers) as executor:
            for index, result in enumerate(executor.map(one, selected_records), start=1):
                print(f"[{index}/{len(selected_records)}] {result['item_id']}", flush=True)
                results.append(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary_output.write_text("".join(canonical(result) + "\n" for result in results), encoding="utf-8", newline="\n")
    temporary_output.replace(args.output)
    print(canonical({"status": "RUN_COMPLETE", "records": len(results), "output": str(args.output), "results_sha256": sha256_text(args.output.read_text(encoding="utf-8"))}))


if __name__ == "__main__":
    main()
