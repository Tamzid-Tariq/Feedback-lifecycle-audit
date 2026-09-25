#!/usr/bin/env python3
"""Normalize Condition B/C outputs and verify matched evidence packets."""
from __future__ import annotations

import argparse
from pathlib import Path
import json
import sys
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
WORK_ROOT = SCRIPT_DIR.parents[1]
CONDITION_B_DIR = SCRIPT_DIR.parent / "baselines" / "condition_B"
if str(CONDITION_B_DIR) not in sys.path:
    sys.path.insert(0, str(CONDITION_B_DIR))
import run_baseline as condition_b  # noqa: E402


LIFECYCLE_LABELS = {"KEEP", "RETIRE", "RETRACT", "UNSURE"}
VALIDITY_LABELS = {"SUPPORTED", "REFUTED", "INDETERMINATE"}
TARGET_LABELS = {"PRESENT", "RESOLVED", "INDETERMINATE", "NOT_APPLICABLE"}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ValueError(f"JSONL file does not exist: {path}")
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
                raise ValueError(f"{path}:{line_number}: expected a JSON object")
            rows.append(row)
    return rows


def unique_by_item(rows: list[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        item_id = row.get("item_id")
        if not isinstance(item_id, str) or not item_id:
            raise ValueError(f"{label}: every record needs a non-empty item_id")
        if item_id in indexed:
            raise ValueError(f"{label}: duplicate item_id {item_id}")
        indexed[item_id] = row
    return indexed


def normalize_prediction(row: dict[str, Any], condition: str) -> dict[str, Any]:
    item_id = row.get("item_id")
    if not isinstance(item_id, str) or not item_id:
        raise ValueError(f"{condition}: prediction is missing item_id")
    original = row.get("original_validity")
    target = row.get("target_state_t1")
    lifecycle = row.get("lifecycle_label")
    if original not in VALIDITY_LABELS:
        raise ValueError(f"{condition}/{item_id}: invalid original_validity {original!r}")
    if target not in TARGET_LABELS:
        raise ValueError(f"{condition}/{item_id}: invalid target_state_t1 {target!r}")
    if lifecycle not in LIFECYCLE_LABELS:
        raise ValueError(f"{condition}/{item_id}: invalid lifecycle_label {lifecycle!r}")

    # B has no selective-decision fields. Its normalized representation is
    # explicitly non-abstaining without rerunning or rewriting the B records.
    abstain = row.get("abstain", False)
    if not isinstance(abstain, bool):
        raise ValueError(f"{condition}/{item_id}: abstain must be boolean")
    abstention_reason = row.get("abstention_reason", "")
    if not isinstance(abstention_reason, str):
        raise ValueError(f"{condition}/{item_id}: abstention_reason must be a string")

    model_lifecycle = row.get("model_lifecycle_label")
    if model_lifecycle is None:
        predicted_lifecycle = lifecycle
    else:
        if model_lifecycle not in LIFECYCLE_LABELS:
            raise ValueError(f"{condition}/{item_id}: invalid model_lifecycle_label {model_lifecycle!r}")
        predicted_lifecycle = model_lifecycle
    final_action = "UNSURE" if abstain else lifecycle
    evidence_ids = row.get("evidence_ids")
    if (
        not isinstance(evidence_ids, list)
        or not evidence_ids
        or not all(isinstance(value, str) and value for value in evidence_ids)
    ):
        raise ValueError(f"{condition}/{item_id}: evidence_ids must be a non-empty string list")
    short_reason = row.get("short_reason")
    if not isinstance(short_reason, str) or not short_reason.strip():
        raise ValueError(f"{condition}/{item_id}: short_reason must be non-empty")

    return {
        "condition": condition,
        "item_id": item_id,
        "original_validity": original,
        "target_state_t1": target,
        "predicted_lifecycle": predicted_lifecycle,
        "abstain": abstain,
        "final_action": final_action,
        "evidence_ids": evidence_ids,
        "short_reason": short_reason,
        "abstention_reason": abstention_reason,
    }


def load_hashes(path: Path, label: str) -> dict[str, str | None]:
    rows = read_jsonl(path)
    indexed: dict[str, str | None] = {}
    for row in rows:
        item_id = row.get("item_id")
        if not isinstance(item_id, str) or not item_id:
            raise ValueError(f"{label}: request metadata has a missing item_id")
        if item_id in indexed:
            raise ValueError(f"{label}: duplicate request metadata item_id {item_id}")
        value = row.get("evidence_sha256")
        indexed[item_id] = value if isinstance(value, str) and value else None
    return indexed


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(condition_b.canonical(row) + "\n")
        handle.flush()
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--b-predictions", type=Path, required=True)
    parser.add_argument("--c-predictions", type=Path, required=True)
    parser.add_argument("--b-request-metadata", type=Path, required=True)
    parser.add_argument("--c-request-metadata", type=Path, required=True)
    parser.add_argument("--evaluation-output", type=Path, required=True)
    parser.add_argument("--matched-evidence-output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    parser.add_argument("--item-ids", default=None, help="Optional comma-separated comparison item IDs.")
    args = parser.parse_args()

    b_predictions = unique_by_item(
        [normalize_prediction(row, "B") for row in read_jsonl(args.b_predictions)], "B predictions"
    )
    c_predictions = unique_by_item(
        [normalize_prediction(row, "C") for row in read_jsonl(args.c_predictions)], "C predictions"
    )
    b_hashes = load_hashes(args.b_request_metadata, "B request metadata")
    c_hashes = load_hashes(args.c_request_metadata, "C request metadata")

    if args.item_ids:
        item_ids = [item.strip() for item in args.item_ids.split(",") if item.strip()]
        if not item_ids or len(item_ids) != len(set(item_ids)):
            raise ValueError("--item-ids must contain unique comma-separated IDs")
    else:
        # Scope the comparison to the C run. This makes smoke/stress artifacts
        # report 5/5 and 3/3 rather than counting unrelated B-only items.
        item_ids = sorted(set(c_hashes) | set(c_predictions))
    if not item_ids:
        raise ValueError("No comparison items were selected")

    evaluation_rows: list[dict[str, Any]] = []
    for item_id in item_ids:
        if item_id not in b_predictions:
            raise ValueError(f"B prediction missing for {item_id}")
        if item_id not in c_predictions:
            raise ValueError(f"C prediction missing for {item_id}")
        evaluation_rows.extend([b_predictions[item_id], c_predictions[item_id]])

    matched_rows: list[dict[str, Any]] = []
    for item_id in item_ids:
        b_hash = b_hashes.get(item_id)
        c_hash = c_hashes.get(item_id)
        matched_rows.append(
            {
                "item_id": item_id,
                "B_evidence_sha256": b_hash,
                "C_evidence_sha256": c_hash,
                "matched": bool(b_hash and c_hash and b_hash == c_hash),
            }
        )
    matched_count = sum(row["matched"] for row in matched_rows)
    summary = {
        "status": "MATCHED" if matched_count == len(matched_rows) else "MISMATCH",
        "comparison_items": len(item_ids),
        "matched_items": matched_count,
        "unmatched_items": len(matched_rows) - matched_count,
        "match_rate": matched_count / len(matched_rows) if matched_rows else None,
        "b_predictions": str(args.b_predictions),
        "c_predictions": str(args.c_predictions),
        "b_request_metadata": str(args.b_request_metadata),
        "c_request_metadata": str(args.c_request_metadata),
        "evaluation_output": str(args.evaluation_output),
        "matched_evidence_output": str(args.matched_evidence_output),
    }
    write_jsonl(args.evaluation_output, evaluation_rows)
    write_jsonl(args.matched_evidence_output, matched_rows)
    condition_b.write_json(args.summary_output, summary)
    print(condition_b.canonical(summary))
    if summary["status"] != "MATCHED":
        raise SystemExit(1)


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        raise SystemExit(f"Evaluation failed: {exc}") from exc
