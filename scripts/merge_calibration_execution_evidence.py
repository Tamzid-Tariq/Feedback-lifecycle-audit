#!/usr/bin/env python3
"""Merge locked-runner execution evidence into the blinded Calibration-20 packets."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PACKETS = ROOT / "annotation" / "calibration_20" / "calibration_20_evidence_frozen_v1.jsonl"
RUN = ROOT / "results" / "calibration_20" / "runs" / "calibration_20_execution_results.jsonl"


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def packet_test_from_output(existing: dict[str, Any], output: dict[str, Any]) -> dict[str, Any]:
    allowed = ("evidence_id", "status", "exit_code", "timed_out", "runtime_error", "stdout", "stderr")
    merged = {key: output[key] for key in allowed}
    # The packet's evidence ID is authoritative and must stay stable.
    if merged["evidence_id"] != existing["evidence_id"]:
        raise ValueError(f"Evidence ID mismatch: {existing['evidence_id']} != {merged['evidence_id']}")
    return merged


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packets", type=Path, default=PACKETS)
    parser.add_argument("--run", type=Path, default=RUN)
    args = parser.parse_args()
    packets = read_jsonl(args.packets)
    runs = {row["item_id"]: row for row in read_jsonl(args.run)}
    if len(packets) != 16 or set(runs) != {packet["item_id"] for packet in packets}:
        raise SystemExit("Packet and execution result sets do not match exactly")

    backup = ROOT / "results" / "calibration_20" / "runs" / "calibration_20_evidence_pre_replay_v1.jsonl"
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(args.packets, backup)

    for packet in packets:
        run = runs[packet["item_id"]]
        for state_key, packet_state in (("st", "earlier"), ("st1", "later")):
            compiler = run[state_key]["compiler_result"]
            packet["compiler"][packet_state] = {
                "compiler": compiler["compiler"],
                "evidence_id": packet["compiler"][packet_state]["evidence_id"],
                "status": compiler["status"],
                "exit_code": compiler["exit_code"],
                "timed_out": compiler["timed_out"],
                "stdout": compiler["stdout"],
                "stderr": compiler["stderr"],
            }
            outputs = run[state_key]["actual_outputs"]
            by_test = {row["test_case_id"]: row for row in outputs} if outputs is not None else {}
            for test in packet["tests"]:
                test_id = test["test_case_id"]
                if outputs is None:
                    replacement = dict(test[packet_state])
                    replacement.update({
                        "status": "INFRA_TIMEOUT",
                        "exit_code": None,
                        "timed_out": True,
                        "runtime_error": "host timeout while waiting for locked-down container",
                        "stdout": "",
                        "stderr": "",
                    })
                else:
                    replacement = packet_test_from_output(test[packet_state], by_test[test_id])
                test[packet_state] = replacement
        content = dict(packet)
        content.pop("packet_sha256", None)
        packet["packet_sha256"] = digest(canonical(content))

    args.packets.write_text("".join(canonical(packet) + "\n" for packet in packets), encoding="utf-8", newline="\n")
    status_path = ROOT / "results" / "calibration_20" / "calibration_20_packet_status.json"
    status_path.write_text(json.dumps({
        "selected_cases": 20,
        "stage_a_usable_cases": 16,
        "stage_a_failures_preserved": 4,
        "focal_claims_frozen": 16,
        "frozen_packet_rows": 16,
        "annotation_eligible_cases": 16,
        "execution_replay": "COMPLETE_LOCKED_RUNNER",
        "execution_results": str(args.run.relative_to(ROOT)),
        "pre_replay_packet_backup": str(backup.relative_to(ROOT)),
        "runner_image": runs[next(iter(runs))]["runner_image"],
        "runner_image_id": runs[next(iter(runs))]["runner_image_id"],
        "method_predictions_included": False,
    }, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "MERGED", "packet_rows": len(packets), "backup": str(backup), "execution_replay": "COMPLETE_LOCKED_RUNNER"}))


if __name__ == "__main__":
    main()
