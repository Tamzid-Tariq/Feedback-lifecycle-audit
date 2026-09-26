#!/usr/bin/env python3
"""Build the blinded, validation-based calibration evidence packet.

Only successful Stage-A hints with a frozen focal claim are eligible for the
annotator packet. All 20 selected cases remain represented in the Stage-A
results and eligibility manifest; failures are never silently replaced.
"""
from __future__ import annotations

import csv
import difflib
import hashlib
import json
import re
from pathlib import Path
from typing import Any


COMPILER = "gcc -std=c11 -O0 -Wall -Wextra -Werror=return-type"
PACKET_VERSION = "revground-annotation-evidence-v1.1.0"


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(canonical(row) + "\n" for row in rows), encoding="utf-8")


def diff(item_id: str, before: str, after: str) -> str:
    return "".join(difflib.unified_diff(
        [line + "\n" for line in before.splitlines()],
        [line + "\n" for line in after.splitlines()],
        fromfile=f"{item_id}:S_t", tofile=f"{item_id}:S_t+1", lineterm="\n",
    ))


def tests(problem: dict[str, str]) -> list[dict[str, Any]]:
    raw = json.loads(problem["evaluation_test_cases"])
    result = []
    for case in sorted(raw, key=lambda x: int(x["test_case_no"])):
        test_id = f"{problem['problem_id']}_T{case['test_case_no']}"
        result.append({
            "test_case_id": test_id,
            "official_evidence_id": f"official_test:{test_id}",
            "input": case["input"],
            "expected_output": case["output"],
            "earlier": {
                "evidence_id": f"execution:{{item}}:st:{test_id}",
                "status": "NOT_REPLAYED",
                "exit_code": None,
                "timed_out": False,
                "runtime_error": "Validation source state was not replayed in the locked-down execution runner at packet-freeze time.",
                "stdout": "",
                "stderr": "",
            },
            "later": {
                "evidence_id": f"execution:{{item}}:st1:{test_id}",
                "status": "NOT_REPLAYED",
                "exit_code": None,
                "timed_out": False,
                "runtime_error": "Validation revised state was not replayed in the locked-down execution runner at packet-freeze time.",
                "stdout": "",
                "stderr": "",
            },
        })
    return result


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    package = root.parent / "RevGround_Supervisor_Aligned_Package_v2"
    manifest = read_csv(root / "data" / "manifests" / "calibration_20_manifest.csv")
    transitions = {row["transition_id"]: row for row in read_csv(package / "stage5_partitions" / "validation_transition_index.csv")}
    submissions = {row["submission_id"]: row for row in read_csv(root.parent / "Dataset" / "Submission Data.csv")}
    problems = {row["problem_id"]: row for row in read_csv(root.parent / "Dataset" / "Problem Data.csv")}
    stage_rows = {row["generation_case_id"]: row for row in read_jsonl(root / "results" / "calibration_20" / "stage_a_input.jsonl")}
    hints = {row["generation_case_id"]: row for row in read_jsonl(root / "results" / "calibration_20" / "stage_a_stealth_space_bunny_alpha" / "raw_hints.jsonl")}
    claims = {row["generation_case_id"]: row for row in read_jsonl(root / "results" / "calibration_20" / "frozen_focal_claims.jsonl")}

    packets = []
    eligibility = []
    for selected in manifest:
        case_id = selected["generation_case_id"]
        hint = hints[case_id]
        claim = claims.get(case_id)
        eligible = hint.get("status") == "success" and isinstance(claim, dict) and claim.get("claim_text")
        eligibility.append({
            "item_id": selected["item_id"],
            "generation_case_id": case_id,
            "stage_a_status": hint.get("status"),
            "claim_status": claim.get("extraction_status") if claim else None,
            "annotation_eligible": bool(eligible),
        })
        if not eligible:
            continue
        transition = transitions[selected["transition_id"]]
        st = submissions[transition["submission_id_t"]]
        st1 = submissions[transition["submission_id_t1"]]
        problem = problems[transition["problem_id"]]
        item_id = selected["item_id"]
        if stage_rows[case_id]["code_t"] != st["source_code"]:
            raise ValueError(f"{item_id}: Stage-A/source mismatch")
        hint_text = hint["raw_hint_text"]
        claim_text = claim["claim_text"]
        start, end = int(claim["claim_span_start"]), int(claim["claim_span_end"])
        if hint_text[start:end] != claim_text:
            raise ValueError(f"{item_id}: claim span is not exact")
        packet_tests = tests(problem)
        for test in packet_tests:
            test["earlier"]["evidence_id"] = test["earlier"]["evidence_id"].format(item=item_id)
            test["later"]["evidence_id"] = test["later"]["evidence_id"].format(item=item_id)
        evidence_ids = [
            f"source:{item_id}:S_t", f"source:{item_id}:S_t+1", f"diff:{item_id}",
            f"stored_trace:{item_id}:S_t", f"stored_trace:{item_id}:S_t+1",
            f"execution:{item_id}:st:compile", f"execution:{item_id}:st1:compile",
        ]
        evidence_ids.extend(test["official_evidence_id"] for test in packet_tests)
        evidence_ids.extend(test[state]["evidence_id"] for test in packet_tests for state in ("earlier", "later"))
        packet = {
            "packet_format_version": PACKET_VERSION,
            "packet_id": f"packet:{item_id}:{transition['transition_id']}",
            "item_id": item_id,
            "transition_id": transition["transition_id"],
            "problem_id": transition["problem_id"],
            "language": "C",
            "problem_statement": problem["problem_description"],
            "earlier": {"attempt_number": int(st["attempt_number"]), "source": st["source_code"], "source_sha256": sha256_text(st["source_code"])},
            "later": {"attempt_number": int(st1["attempt_number"]), "source": st1["source_code"], "source_sha256": sha256_text(st1["source_code"])},
            "original_hint": hint_text,
            "claim_span": {"text": claim_text, "start": start, "end": end, "source_field": "stage_a_hint_exact_span"},
            "code_diff": diff(item_id, st["source_code"], st1["source_code"]),
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
        packets.append(packet)

    results = root / "results" / "calibration_20"
    results.joinpath("annotation_eligibility_manifest.json").write_text(json.dumps({"selected_count": len(manifest), "annotation_eligible_count": len(packets), "records": eligibility}, indent=2) + "\n", encoding="utf-8")
    annotation = root / "annotation" / "calibration_20"
    annotation.joinpath("calibration_20_evidence_frozen_v1.jsonl").write_text("".join(canonical(row) + "\n" for row in packets), encoding="utf-8")
    annotation.joinpath("calibration_20_packet_status.json").write_text(json.dumps({"selected_cases": len(manifest), "frozen_packet_rows": len(packets), "annotation_eligible_cases": len(packets), "execution_replay": "NOT_REPLAYED", "stage_a_failures_preserved_in": "results/calibration_20"}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"selected": len(manifest), "packets": len(packets), "eligible": len(packets), "failures": len(manifest) - len(packets)}))


if __name__ == "__main__":
    main()
