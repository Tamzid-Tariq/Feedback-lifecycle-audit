#!/usr/bin/env python3
"""Build the complete label-independent TEST-197 screening and packet cohort."""
from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import json
from pathlib import Path
from typing import Any


PACKET_VERSION = "revground-annotation-evidence-v1.1.0"
COMPILER = "gcc -std=c11 -O0 -Wall -Wextra -Werror=return-type"


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(canonical(row) + "\n" for row in rows), encoding="utf-8", newline="\n")


def unified_diff(item_id: str, before: str, after: str) -> str:
    return "".join(difflib.unified_diff(
        [line + "\n" for line in before.splitlines()],
        [line + "\n" for line in after.splitlines()],
        fromfile=f"{item_id}:S_t", tofile=f"{item_id}:S_t+1", lineterm="\n",
    ))


def official_tests(problem: dict[str, str], item_id: str) -> list[dict[str, Any]]:
    raw = json.loads(problem["evaluation_test_cases"])
    tests: list[dict[str, Any]] = []
    for case in sorted(raw, key=lambda row: int(row["test_case_no"])):
        test_id = f"{problem['problem_id']}_T{case['test_case_no']}"
        tests.append({
            "test_case_id": test_id,
            "official_evidence_id": f"official_test:{test_id}",
            "input": case["input"],
            "expected_output": case["output"],
            "earlier": {
                "evidence_id": f"execution:{item_id}:st:{test_id}", "status": "NOT_REPLAYED",
                "exit_code": None, "timed_out": False, "runtime_error": "TEST packet state was not replayed at packet-freeze time.",
                "stdout": "", "stderr": "",
            },
            "later": {
                "evidence_id": f"execution:{item_id}:st1:{test_id}", "status": "NOT_REPLAYED",
                "exit_code": None, "timed_out": False, "runtime_error": "TEST packet state was not replayed at packet-freeze time.",
                "stdout": "", "stderr": "",
            },
        })
    return tests


def load_stage(stage_dir: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    hints = {row["generation_case_id"]: row for row in read_jsonl(stage_dir / "raw_hints.jsonl")}
    errors = {row["generation_case_id"]: row for row in read_jsonl(stage_dir / "errors.jsonl")}
    claims = {row["generation_case_id"]: row for row in read_jsonl(stage_dir / "frozen_focal_claims.jsonl")}
    return hints, errors, claims


def make_packet(item_id: str, selected: dict[str, str], transition: dict[str, str], stage: dict[str, Any],
                hint: dict[str, Any], claim: dict[str, Any], st: dict[str, str], st1: dict[str, str],
                problem: dict[str, str], claim_source: str) -> dict[str, Any]:
    claim_text = claim["claim_text"]
    start, end = int(claim["claim_span_start"]), int(claim["claim_span_end"])
    if hint["raw_hint_text"][start:end] != claim_text:
        raise SystemExit(f"frozen claim span mismatch: {item_id}")
    packet_tests = official_tests(problem, item_id)
    evidence_ids = [
        f"source:{item_id}:S_t", f"source:{item_id}:S_t+1", f"diff:{item_id}",
        f"stored_trace:{item_id}:S_t", f"stored_trace:{item_id}:S_t+1",
        f"execution:{item_id}:st:compile", f"execution:{item_id}:st1:compile",
    ]
    evidence_ids += [test["official_evidence_id"] for test in packet_tests]
    evidence_ids += [test[state]["evidence_id"] for test in packet_tests for state in ("earlier", "later")]
    packet: dict[str, Any] = {
        "packet_format_version": PACKET_VERSION,
        "packet_id": f"packet:{item_id}:{transition['transition_id']}",
        "item_id": item_id,
        "transition_id": transition["transition_id"],
        "problem_id": transition["problem_id"],
        "language": "C",
        "problem_statement": problem["problem_description"],
        "earlier": {"attempt_number": int(st["attempt_number"]), "source": st["source_code"], "source_sha256": sha256_text(st["source_code"])},
        "later": {"attempt_number": int(st1["attempt_number"]), "source": st1["source_code"], "source_sha256": sha256_text(st1["source_code"])},
        "original_hint": hint["raw_hint_text"],
        "claim_span": {"text": claim_text, "start": start, "end": end, "source_field": claim_source},
        "code_diff": unified_diff(item_id, st["source_code"], st1["source_code"]),
        "compiler": {
            "earlier": {"compiler": COMPILER, "evidence_id": f"execution:{item_id}:st:compile", "status": "NOT_REPLAYED", "exit_code": None, "timed_out": False, "stdout": "", "stderr": ""},
            "later": {"compiler": COMPILER, "evidence_id": f"execution:{item_id}:st1:compile", "status": "NOT_REPLAYED", "exit_code": None, "timed_out": False, "stdout": "", "stderr": ""},
        },
        "tests": packet_tests,
        "stored_judge_traces": {
            "earlier": {"evidence_id": f"stored_trace:{item_id}:S_t", "final_verdict": st["final_verdict"], "verdict_sequence_trace": json.loads(st["verdict_sequence_trace"])},
            "later": {"evidence_id": f"stored_trace:{item_id}:S_t+1", "final_verdict": st1["final_verdict"], "verdict_sequence_trace": json.loads(st1["verdict_sequence_trace"])},
        },
        "claim_relevant_trace": None,
        "all_evidence_ids": evidence_ids,
        "packet_prepared_without_method_predictions": True,
    }
    packet["packet_sha256"] = sha256_text(canonical(packet))
    return packet


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cohort-manifest", type=Path, required=True)
    parser.add_argument("--source-input", type=Path, required=True)
    parser.add_argument("--transition-index", type=Path, required=True)
    parser.add_argument("--submissions", type=Path, required=True)
    parser.add_argument("--problems", type=Path, required=True)
    parser.add_argument("--batch1-stage-dir", type=Path, required=True)
    parser.add_argument("--batch2-stage-dir", type=Path, required=True)
    parser.add_argument("--batch1-packets", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    cohort = read_csv(args.cohort_manifest)
    by_id = {row["generation_case_id"]: row for row in cohort}
    if len(cohort) != 197 or len(by_id) != 197:
        raise SystemExit("cohort manifest must contain 197 unique rows")
    source = {row["generation_case_id"]: row for row in read_jsonl(args.source_input)}
    transitions = {row["transition_id"]: row for row in read_csv(args.transition_index)}
    submissions = {row["submission_id"]: row for row in read_csv(args.submissions)}
    problems = {row["problem_id"]: row for row in read_csv(args.problems)}
    if len(source) != 197 or len(transitions) != 197:
        raise SystemExit("source or transition index is not TEST-197")
    stage_sets = [load_stage(args.batch1_stage_dir), load_stage(args.batch2_stage_dir)]
    batch1_hint, batch1_error, batch1_claim = stage_sets[0]
    batch2_hint, batch2_error, batch2_claim = stage_sets[1]

    ledger: list[dict[str, str]] = []
    batch2_packets: list[dict[str, Any]] = []
    for item_id in sorted(by_id):
        row = by_id[item_id]
        is_batch1 = row["batch"] == "Batch1_historical_TEST50"
        hint_map, error_map, claim_map = stage_sets[0] if is_batch1 else stage_sets[1]
        qc_confirmed = row["qc_status"] == "CONFIRMED_C"
        hint = hint_map.get(item_id, {})
        error = error_map.get(item_id, {})
        claim = claim_map.get(item_id, {})
        stage_accepted = hint.get("status") == "success" and not error
        if stage_accepted and not claim:
            raise SystemExit(f"accepted hint missing frozen claim: {item_id}")
        if stage_accepted and claim.get("claim_text") is None:
            packet_status = "NO_FOCAL_CLAIM"
            reason = "accepted hint did not yield a focal claim under the frozen extraction rule"
        elif not qc_confirmed:
            packet_status = "EXCLUDED_LANGUAGE"
            reason = "objective source-language exclusion"
        elif not stage_accepted:
            packet_status = "STAGE_A_FAILURE"
            reason = "preserved Stage-A generation/output failure"
        else:
            packet_status = "SUCCESSFUL_C_CLAIM_BEARING"
            reason = "accepted Stage-A hint with frozen focal claim"
        ledger.append({
            "generation_case_id": item_id, "test_id": item_id, "transition_id": row["transition_id"],
            "partition": row["partition"], "batch": row["batch"], "declared_language": "C",
            "detected_source_language": row["detected_source_language"], "qc_status": row["qc_status"],
            "qc_reason": row["qc_reason"], "stage_a_status": "accepted" if stage_accepted else ("not_run_objective_exclusion" if not qc_confirmed and not hint else "failure"),
            "stage_a_error_status": error.get("status", ""), "stage_a_error": error.get("error", ""),
            "claim_status": claim.get("extraction_status", ""), "claim_id": claim.get("claim_id", ""),
            "packet_status": packet_status, "eligibility_reason": reason, "replacement_used": "false",
            "reference_or_model_fields_read": "false",
        })
        if packet_status != "SUCCESSFUL_C_CLAIM_BEARING" or is_batch1:
            continue
        transition = transitions[row["transition_id"]]
        st = submissions[transition["submission_id_t"]]
        st1 = submissions[transition["submission_id_t1"]]
        problem = problems[transition["problem_id"]]
        if source[item_id]["code_t"] != st["source_code"]:
            raise SystemExit(f"S_t source mismatch: {item_id}")
        batch2_packets.append(make_packet(item_id, row, transition, source[item_id], hint, claim, st, st1, problem, "frozen_focal_claims_batch2.jsonl"))

    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    ledger_path = out / "screening_ledger.csv"
    with ledger_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(ledger[0]))
        writer.writeheader()
        writer.writerows(ledger)
    batch2_packet_path = out / "evidence_batch2_pre_replay_v1.jsonl"
    write_jsonl(batch2_packet_path, batch2_packets)

    counts = {
        "test_partition_cases": len(ledger),
        "historical_batch1_cases": sum(row["batch"] == "Batch1_historical_TEST50" for row in ledger),
        "remaining_batch2_cases": sum(row["batch"] == "Batch2_remaining_TEST197" for row in ledger),
        "confirmed_c": sum(row["qc_status"] == "CONFIRMED_C" for row in ledger),
        "objective_language_exclusions": sum(row["packet_status"] == "EXCLUDED_LANGUAGE" for row in ledger),
        "stage_a_accepted": sum(row["stage_a_status"] == "accepted" for row in ledger),
        "stage_a_failures": sum(row["packet_status"] == "STAGE_A_FAILURE" for row in ledger),
        "no_focal_claim": sum(row["packet_status"] == "NO_FOCAL_CLAIM" for row in ledger),
        "successful_c_claim_bearing": sum(row["packet_status"] == "SUCCESSFUL_C_CLAIM_BEARING" for row in ledger),
        "batch2_packets_pre_replay": len(batch2_packets),
        "replacements": sum(row["replacement_used"] == "true" for row in ledger),
    }
    expected = {"test_partition_cases": 197, "historical_batch1_cases": 50, "remaining_batch2_cases": 147, "confirmed_c": 188, "objective_language_exclusions": 9, "replacements": 0}
    for key, value in expected.items():
        if counts[key] != value:
            raise SystemExit(f"unexpected {key}: {counts[key]} != {value}")
    profile_rows = [row for row in ledger if row["packet_status"] == "SUCCESSFUL_C_CLAIM_BEARING"]
    profile = {
        "status": "FROZEN_SUCCESSFUL_C_CLAIM_BEARING_COHORT",
        "protocol_amendment": "test197_full_eligible_cohort_v1",
        "source_partition": "test",
        "profile_basis": "successful C claim-bearing transitions after objective QC and Stage-A acceptance; exclusions and failures remain in screening_ledger.csv",
        "counts": counts,
        "successful_claim_bearing": {
            "cases": len(profile_rows),
            "problems": len({by_id[row["generation_case_id"]]["problem_id"] for row in profile_rows}),
            "trajectories": len({by_id[row["generation_case_id"]]["trajectory_id"] for row in profile_rows}),
            "participants": len({by_id[row["generation_case_id"]]["participant_id_hash"] for row in profile_rows}),
        },
        "all_eligible_confirmed_c": {
            "cases": counts["confirmed_c"],
            "problems": len({by_id[row["generation_case_id"]]["problem_id"] for row in ledger if row["qc_status"] == "CONFIRMED_C"}),
            "trajectories": len({by_id[row["generation_case_id"]]["trajectory_id"] for row in ledger if row["qc_status"] == "CONFIRMED_C"}),
            "participants": len({by_id[row["generation_case_id"]]["participant_id_hash"] for row in ledger if row["qc_status"] == "CONFIRMED_C"}),
        },
        "stage_a_policy": {"model": "stealth/space-bunny-alpha", "max_tokens": 512, "timeout_seconds": 90, "fallback_disabled": True, "automatic_retry": False, "replacement": False},
        "claim_extraction_rule": "first_explicit_diagnostic_assertion_v1",
        "method_predictions_included": False,
        "screening_ledger_sha256": sha256_file(ledger_path),
        "batch2_packet_sha256": sha256_file(batch2_packet_path),
    }
    (out / "screening_summary.json").write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "BUILT", "counts": counts, "profile": profile["successful_claim_bearing"], "batch2_packet_sha256": profile["batch2_packet_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
