#!/usr/bin/env python3
"""Rebuild the unannotated 50-case development records from local raw data.

Raw CodeStream CSVs are intentionally not tracked. Place them under
``data/raw`` as documented in ``data/README.md``. This script joins the frozen
development manifest to each selected S_t submission and its authentic next
attempt, while keeping generated hints and claims null.
"""
from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
HASH_SALT = "revground-codestream-stage45-v1"
FORMAT_VERSION = "revground-development-record-v1.0.0"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def participant_hash(user_id: str) -> str:
    return sha256_text(f"{HASH_SALT}|{user_id}")[:16]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_json_list(value: str, label: str) -> list[Any]:
    parsed = json.loads(value)
    if not isinstance(parsed, list):
        raise ValueError(f"{label} must be a JSON list")
    return parsed


def code_diff(item_id: str, earlier: str, later: str) -> str:
    before = [line + "\n" for line in earlier.splitlines()]
    after = [line + "\n" for line in later.splitlines()]
    return "".join(difflib.unified_diff(before, after, fromfile=f"{item_id}:S_t", tofile=f"{item_id}:S_t+1", lineterm="\n"))


def official_tests(problem_id: str, raw_value: str) -> list[dict[str, str]]:
    tests = parse_json_list(raw_value, f"{problem_id} evaluation_test_cases")
    result: list[dict[str, str]] = []
    for test in tests:
        if not isinstance(test, dict) or set(test) != {"test_case_no", "input", "output"}:
            raise ValueError(f"Unexpected test structure for {problem_id}")
        test_id = f"{problem_id}_T{int(test['test_case_no'])}"
        result.append({
            "evidence_id": f"official_test:{test_id}",
            "test_case_id": test_id,
            "input": str(test["input"]),
            "expected_output": str(test["output"]),
        })
    return sorted(result, key=lambda row: int(row["test_case_id"].rsplit("T", 1)[1]))


def require_columns(rows: list[dict[str, str]], columns: set[str], label: str) -> None:
    if not rows:
        raise ValueError(f"{label} is empty")
    missing = columns - set(rows[0])
    if missing:
        raise ValueError(f"{label} is missing columns: {sorted(missing)}")


def build_records(submissions_path: Path, problems_path: Path, manifest_path: Path) -> list[dict[str, Any]]:
    submissions = read_csv(submissions_path)
    problems = read_csv(problems_path)
    manifest = read_csv(manifest_path)
    require_columns(submissions, {"submission_id", "user_id", "problem_id", "attempt_number", "programming_language", "source_code", "final_verdict", "verdict_sequence_trace"}, "submissions")
    require_columns(problems, {"problem_id", "problem_description", "evaluation_test_cases"}, "problems")
    require_columns(manifest, {"generation_case_id", "transition_id", "trajectory_id", "participant_id_hash", "problem_id", "submission_id_t", "attempt_t", "selection_order"}, "manifest")

    by_id = {row["submission_id"]: row for row in submissions}
    if len(by_id) != len(submissions):
        raise ValueError("Duplicate submission_id values")
    by_attempt: dict[tuple[str, str, int], dict[str, str]] = {}
    for row in submissions:
        key = (row["user_id"], row["problem_id"], int(row["attempt_number"]))
        if key in by_attempt:
            raise ValueError(f"Duplicate participant/problem/attempt key: {key}")
        by_attempt[key] = row
    problem_by_id = {row["problem_id"]: row for row in problems}

    records: list[dict[str, Any]] = []
    ordered_manifest = sorted(manifest, key=lambda row: int(row["selection_order"]))
    for position, selected in enumerate(ordered_manifest, start=1):
        item_id = f"DEV_{position:03d}"
        earlier = by_id.get(selected["submission_id_t"])
        if earlier is None:
            raise ValueError(f"Missing selected submission for {item_id}")
        attempt = int(selected["attempt_t"])
        if int(earlier["attempt_number"]) != attempt or earlier["problem_id"] != selected["problem_id"]:
            raise ValueError(f"Manifest/source mismatch for {item_id}")
        if participant_hash(earlier["user_id"]) != selected["participant_id_hash"]:
            raise ValueError(f"Participant hash mismatch for {item_id}")
        later = by_attempt.get((earlier["user_id"], earlier["problem_id"], attempt + 1))
        if later is None:
            raise ValueError(f"No consecutive S_t+1 submission for {item_id}")
        if earlier["programming_language"].strip().lower() != "c" or later["programming_language"].strip().lower() != "c":
            raise ValueError(f"Non-C transition selected for {item_id}")
        problem = problem_by_id.get(earlier["problem_id"])
        if problem is None:
            raise ValueError(f"Missing problem row for {item_id}")
        tests = official_tests(earlier["problem_id"], problem["evaluation_test_cases"])
        earlier_source = earlier["source_code"]
        later_source = later["source_code"]
        trace_t = parse_json_list(earlier["verdict_sequence_trace"], f"{item_id} S_t trace")
        trace_t1 = parse_json_list(later["verdict_sequence_trace"], f"{item_id} S_t+1 trace")
        records.append({
            "record_format_version": FORMAT_VERSION,
            "item_id": item_id,
            "generation_case_id": selected["generation_case_id"],
            "transition_id": selected["transition_id"],
            "trajectory_id": selected["trajectory_id"],
            "participant_id": selected["participant_id_hash"],
            "problem_id": earlier["problem_id"],
            "language": "C",
            "st_submission_id": earlier["submission_id"],
            "st_attempt_number": attempt,
            "st_source": earlier_source,
            "st_source_sha256": sha256_text(earlier_source),
            "st1_submission_id": later["submission_id"],
            "st1_attempt_number": attempt + 1,
            "st1_source": later_source,
            "st1_source_sha256": sha256_text(later_source),
            "problem_statement": problem["problem_description"],
            "test_case_ids": [test["test_case_id"] for test in tests],
            "stored_judge_evidence": {
                "st": {"final_verdict": earlier["final_verdict"], "verdict_sequence_trace": trace_t},
                "st1": {"final_verdict": later["final_verdict"], "verdict_sequence_trace": trace_t1},
            },
            "hint": None,
            "diagnostic_claim": None,
            "execution_evidence": {
                "official_tests": tests,
                "st": {"status": "not_run", "compiler_result": None, "actual_outputs": None, "termination": None, "evidence_ids": []},
                "st1": {"status": "not_run", "compiler_result": None, "actual_outputs": None, "termination": None, "evidence_ids": []},
                "code_diff": code_diff(item_id, earlier_source, later_source),
                "claim_relevant_trace": None,
                "evidence_ids": [f"source:{item_id}:S_t", f"source:{item_id}:S_t+1", *(test["evidence_id"] for test in tests)],
            },
            "annotation_split": "development",
        })
    return records


def encoded_jsonl(records: list[dict[str, Any]]) -> bytes:
    return "".join(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for record in records).encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--submissions", type=Path, default=REPO_ROOT / "data" / "raw" / "Submission Data.csv")
    parser.add_argument("--problems", type=Path, default=REPO_ROOT / "data" / "raw" / "Problem Data.csv")
    parser.add_argument("--manifest", type=Path, default=REPO_ROOT / "data" / "manifests" / "rubric_development_50_manifest.csv")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "data" / "derived" / "development_50_records_unannotated.jsonl")
    parser.add_argument("--mode", choices=("write", "check"), default="write")
    args = parser.parse_args()
    records = build_records(args.submissions, args.problems, args.manifest)
    if len(records) != 50:
        raise SystemExit(f"Expected 50 records, found {len(records)}")
    content = encoded_jsonl(records)
    if args.mode == "check":
        if not args.output.exists() or args.output.read_bytes() != content:
            raise SystemExit("REBUILD_CHECK_FAILED")
        print(json.dumps({"status": "PASS", "records": 50}, separators=(",", ":")))
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(content)
    print(json.dumps({"status": "WRITTEN", "records": 50, "output": str(args.output)}, separators=(",", ":")))


if __name__ == "__main__":
    main()
