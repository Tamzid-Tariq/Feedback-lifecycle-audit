#!/usr/bin/env python3
"""Freeze exact focal claims from successful Stage-A hint records.

This script is future-blind: it reads only raw Stage-A hint records and never
reads S_t+1, execution evidence, labels, predictions, or adjudication files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


EXTRACTOR = "first_explicit_diagnostic_assertion_v1"
COMPOSITE = re.compile(r"(?:\balso\b|;|\bwhile\b|\band no\b|\band each\b|\bfirst\b.*\bthen\b)", re.I)
IMPERATIVE = re.compile(
    r"^(compile|check|focus|review|reassess|inspect|ensure|verify|replace|move|remove|confirm|address)\b",
    re.I,
)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def spans(text: str) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    start = 0
    for match in re.finditer(r"[.!?](?=\s|$)", text):
        result.append((start, match.end()))
        start = match.end()
        while start < len(text) and text[start].isspace():
            start += 1
    if start < len(text):
        result.append((start, len(text)))
    return result


def trim(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def choose_claim(text: str) -> tuple[int, int, str]:
    candidates = spans(text)
    if not candidates:
        return 0, 0, "none"
    start, end = trim(text, *candidates[0])
    first = text[start:end]
    if len(candidates) > 1 and IMPERATIVE.match(first) and ":" not in first:
        start, end = trim(text, *candidates[1])
    if start >= end:
        return 0, 0, "none"
    text_span = text[start:end]
    return start, end, "composite" if COMPOSITE.search(text_span) else "diagnostic"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hints", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.hints.read_text(encoding="utf-8").splitlines() if line.strip()]
    usable = [row for row in rows if row.get("status") == "success" and isinstance(row.get("raw_hint_text"), str)]
    claims = []
    manifest_rows = []
    for row in usable:
        hint = row["raw_hint_text"]
        start, end, claim_type = choose_claim(hint)
        claim_text = hint[start:end] if claim_type != "none" else None
        status = "success" if claim_type == "diagnostic" else "composite_requires_review" if claim_type == "composite" else "no_focal_diagnostic_claim"
        claim_id = "CLM-" + row["generation_case_id"]
        claims.append({
            "claim_id": claim_id,
            "hint_id": row["hint_id"],
            "generation_case_id": row["generation_case_id"],
            "claim_span_start": start if claim_text is not None else None,
            "claim_span_end": end if claim_text is not None else None,
            "claim_text": claim_text,
            "claim_type": claim_type,
            "claimed_problem": None,
            "claimed_code_location": None,
            "claimed_causal_explanation": None,
            "recommended_direction": None,
            "claimed_evidence": None,
            "extraction_status": status,
            "extractor": EXTRACTOR,
            "human_checked": False,
        })
        manifest_rows.append({
            "claim_id": claim_id,
            "generation_case_id": row["generation_case_id"],
            "hint_id": row["hint_id"],
            "hint_sha256": sha256_text(hint),
            "claim_text_sha256": sha256_text(claim_text) if claim_text is not None else None,
            "extraction_status": status,
            "claim_type": claim_type,
            "human_checked": False,
        })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in claims), encoding="utf-8")
    summary = {
        "status": "CLAIMS_FROZEN_AUTOMATICALLY",
        "extractor": EXTRACTOR,
        "input_hints": str(args.hints),
        "output_claims": str(args.output),
        "attempted_generation_count": len(rows),
        "usable_hint_count": len(usable),
        "claim_count": len(claims),
        "human_checked_count": 0,
        "future_fields_read": False,
        "records": manifest_rows,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": summary["status"], "attempted": len(rows), "usable": len(usable), "claims": len(claims), "extractor": EXTRACTOR}))


if __name__ == "__main__":
    main()
