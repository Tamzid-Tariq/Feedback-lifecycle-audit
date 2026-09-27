#!/usr/bin/env python3
"""Write the final TEST-197 cohort profile after packet replay."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.repo
    manifest = rows(root / "data/manifests/heldout_test_197_final_cohort_manifest.csv")
    ledger = rows(root / "results/heldout_test_197/screening_ledger.csv")
    by_id = {row["generation_case_id"]: row for row in manifest}
    def profile(selected: list[dict[str, str]]) -> dict[str, int]:
        return {
            "cases": len(selected),
            "problems": len({by_id[row["generation_case_id"]]["problem_id"] for row in selected}),
            "trajectories": len({by_id[row["generation_case_id"]]["trajectory_id"] for row in selected}),
            "participants": len({by_id[row["generation_case_id"]]["participant_id_hash"] for row in selected}),
        }
    eligible = [row for row in manifest if row["qc_status"] == "CONFIRMED_C"]
    claim_bearing = [row for row in ledger if row["packet_status"] == "SUCCESSFUL_C_CLAIM_BEARING"]
    final = {
        "status": "FROZEN_FINAL_NATURAL_TEST_COHORT_PROFILE",
        "protocol_amendment": "test197_full_eligible_cohort_v1",
        "source_partition": "test",
        "counts": {
            "all_test_partition": profile(manifest),
            "eligible_confirmed_c_after_objective_qc": profile(eligible),
            "successful_c_claim_bearing_after_stage_a": profile(claim_bearing),
        },
        "screening": {
            "original_test_cases": len(manifest),
            "historical_batch1_cases": sum(row["batch"].startswith("Batch1") for row in manifest),
            "remaining_batch2_cases": sum(row["batch"].startswith("Batch2") for row in manifest),
            "objective_language_exclusions": sum(row["qc_status"] != "CONFIRMED_C" for row in manifest),
            "stage_a_failures": sum(row["packet_status"] == "STAGE_A_FAILURE" for row in ledger),
            "successful_claim_bearing_cases": len(claim_bearing),
            "replacements": 0,
        },
        "stage_a_policy": {
            "model": "stealth/space-bunny-alpha",
            "prompt_sha256": "3916584eb94f1ffa7749bbc94a2b51e1584a9d2eca97d1f197780ee8d956eaee",
            "max_tokens": 512,
            "timeout_seconds": 90,
            "fallback_disabled": True,
            "automatic_retry": False,
            "acceptance": "20-60 word accepted hint; accepted claim-bearing output required for packet construction",
        },
        "claim_extraction_rule": "first_explicit_diagnostic_assertion_v1",
        "evidence_replay": {
            "runner_image": "revground-c-runner:2.0",
            "new_batch2_cases": 126,
            "new_batch2_state_replays": 252,
            "all_final_packet_rows_replayed": True,
        },
        "model_evaluator_calls": {"qwen_b": 0, "qwen_c": 0, "authorized_next_step": "not yet authorized by this preparation run"},
        "method_predictions_included": False,
    }
    out = root / "results/heldout_test_197/final_cohort_profile.json"
    out.write_text(json.dumps(final, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(final, indent=2))


if __name__ == "__main__":
    main()
