#!/usr/bin/env python3
"""Merge locked-runner evidence into new TEST-197 packets without model calls."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packets", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    packets = read_jsonl(args.packets)
    runs = {row["item_id"]: row for row in read_jsonl(args.run)}
    if len(packets) != 126 or set(runs) != {packet["item_id"] for packet in packets}:
        raise SystemExit("packet and execution result sets do not match exactly")
    for packet in packets:
        run = runs[packet["item_id"]]
        for state_key, packet_state in (("st", "earlier"), ("st1", "later")):
            compiler = run[state_key]["compiler_result"]
            packet["compiler"][packet_state] = {
                "compiler": compiler["compiler"],
                "evidence_id": packet["compiler"][packet_state]["evidence_id"],
                "status": compiler["status"], "exit_code": compiler["exit_code"],
                "timed_out": compiler["timed_out"], "stdout": compiler["stdout"], "stderr": compiler["stderr"],
            }
            outputs = run[state_key]["actual_outputs"]
            by_test = {row["test_case_id"]: row for row in outputs} if outputs is not None else {}
            for test in packet["tests"]:
                test_id = test["test_case_id"]
                if outputs is None:
                    test[packet_state].update({
                        "status": "INFRA_TIMEOUT", "exit_code": None, "timed_out": True,
                        "runtime_error": "host timeout while waiting for locked-down container", "stdout": "", "stderr": "",
                    })
                else:
                    output = by_test[test_id]
                    if output["evidence_id"] != test[packet_state]["evidence_id"]:
                        raise SystemExit(f"evidence ID mismatch: {packet['item_id']} {test_id}")
                    for key in ("status", "exit_code", "timed_out", "runtime_error", "stdout", "stderr"):
                        test[packet_state][key] = output[key]
        content = dict(packet)
        content.pop("packet_sha256", None)
        packet["packet_sha256"] = sha256_text(canonical(content))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(canonical(packet) + "\n" for packet in packets), encoding="utf-8", newline="\n")
    print(json.dumps({"status": "MERGED", "packet_rows": len(packets), "output": str(args.output), "sha256": sha256_text(args.output.read_text(encoding="utf-8"))}))


if __name__ == "__main__":
    main()
