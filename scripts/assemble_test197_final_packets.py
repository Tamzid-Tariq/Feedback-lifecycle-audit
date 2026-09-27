#!/usr/bin/env python3
"""Assemble historical Batch 1 and new Batch 2 packets after replay."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def packet_hash(packet: dict[str, Any]) -> str:
    content = dict(packet)
    content.pop("packet_sha256", None)
    return sha256_text(canonical(content))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch1-packets", type=Path, required=True)
    parser.add_argument("--batch2-packets", type=Path, required=True)
    parser.add_argument("--batch1-claims", type=Path, required=True)
    parser.add_argument("--batch2-claims", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    batch1 = read_jsonl(args.batch1_packets)
    batch2 = read_jsonl(args.batch2_packets)
    if len(batch1) != 42 or len(batch2) != 126:
        raise SystemExit(f"expected 42 Batch1 and 126 Batch2 packets, found {len(batch1)} and {len(batch2)}")
    packets = sorted(batch1 + batch2, key=lambda row: row["item_id"])
    if len({row["item_id"] for row in packets}) != 168:
        raise SystemExit("duplicate packet item ID")
    for packet in packets:
        if packet.get("packet_sha256") != packet_hash(packet):
            raise SystemExit(f"packet hash mismatch: {packet['item_id']}")
        for state in ("earlier", "later"):
            if packet["compiler"][state]["status"] == "NOT_REPLAYED":
                raise SystemExit(f"compiler replay missing: {packet['item_id']} {state}")
            for test in packet["tests"]:
                if test[state]["status"] == "NOT_REPLAYED":
                    raise SystemExit(f"test replay missing: {packet['item_id']} {state} {test['test_case_id']}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    packet_path = args.output_dir / "evidence_frozen_v1.jsonl"
    packet_path.write_text("".join(canonical(packet) + "\n" for packet in packets), encoding="utf-8", newline="\n")

    claims = sorted(read_jsonl(args.batch1_claims) + read_jsonl(args.batch2_claims), key=lambda row: row["generation_case_id"])
    if len(claims) != 170 or len({row["generation_case_id"] for row in claims}) != 170:
        raise SystemExit(f"expected 170 frozen claim records, found {len(claims)}")
    claims_path = args.output_dir / "focal_claims_frozen_v1.jsonl"
    claims_path.write_text("".join(canonical(row) + "\n" for row in claims), encoding="utf-8", newline="\n")

    manifest = {
        "status": "FROZEN_FINAL_TEST197_CLAIM_BEARING_COHORT",
        "protocol_amendment": "test197_full_eligible_cohort_v1",
        "historical_batch1_packet_rows": len(batch1),
        "new_batch2_packet_rows": len(batch2),
        "final_packet_rows": len(packets),
        "claim_records_carried_or_frozen": len(claims),
        "stage_a_failures_preserved": 20,
        "objective_language_exclusions_preserved": 9,
        "replacement_used": False,
        "claim_extraction_rule": "first_explicit_diagnostic_assertion_v1",
        "batch1_claims_carried_without_regeneration": True,
        "method_predictions_included": False,
        "packet_path": str(packet_path),
        "packet_sha256": sha256_text(packet_path.read_text(encoding="utf-8")),
        "claims_path": str(claims_path),
        "claims_sha256": sha256_text(claims_path.read_text(encoding="utf-8")),
        "item_ids": [packet["item_id"] for packet in packets],
    }
    (args.output_dir / "final_packet_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "packet_rows": len(packets), "claim_rows": len(claims), "packet_sha256": manifest["packet_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
