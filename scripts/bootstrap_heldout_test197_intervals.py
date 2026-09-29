#!/usr/bin/env python3
"""Cluster-bootstrap 95% intervals for the held-out TEST-168 estimates.

Reports percentile intervals for (1) the share of generation-time SUPPORTED
claims whose final label is RETIRE and (2) each model's paired C-B accuracy
difference on common non-abstaining decisions. Resampling units are
trajectories (primary) and participants (sensitivity). Uses only frozen
annotations, adjudications, primary outputs, and RECOVERY_429_V1 outputs;
never calls a model provider.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

REPO = Path(__file__).resolve().parents[1]
TEST = REPO / "results" / "heldout_test_197"
EVAL = TEST / "evaluations"
MANIFEST = REPO / "data" / "manifests" / "final_test_197_manifest.csv"
OUTPUT = TEST / "analysis" / "bootstrap_intervals.json"
RESAMPLES = 10_000
SEED = 20260929
RUNS = {
    ("deepseek_v4_1_flash", "B"): ["condition_B", "RECOVERY_429_V1/condition_B",
                                    "RECOVERY_429_V1/condition_B_remaining_after_auth_v1"],
    ("deepseek_v4_1_flash", "C"): ["condition_C", "RECOVERY_429_V1/condition_C"],
    ("qwen_qwen3_8_27b", "B"): ["condition_B", "condition_B_primary_continuation_unattempted_v1",
                                 "RECOVERY_429_V1/condition_B"],
    ("qwen_qwen3_8_27b", "C"): ["condition_C", "RECOVERY_429_V1/condition_C"],
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def annotator_rows(annotator: str) -> list[dict[str, Any]]:
    [path] = sorted((TEST / "annotations_frozen_v1" / annotator).glob("*.json"))
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, list) else next(v for v in data.values() if isinstance(v, list))


def final_gold() -> dict[str, dict[str, Any]]:
    gold = {row["item_id"]: row for row in annotator_rows("A01")}
    for row in read_jsonl(TEST / "adjudication_24_final_v1" / "adjudication_final_24.jsonl"):
        gold[row["item_id"]] = row
    return gold


def decisions(model: str, condition: str) -> dict[str, str]:
    merged: dict[str, dict[str, Any]] = {}
    for sub in RUNS[(model, condition)]:
        for row in read_jsonl(EVAL / model / sub / "predictions.jsonl"):
            merged[row["item_id"]] = row
    return {item: row["lifecycle_label"] for item, row in merged.items() if not row.get("abstain")}


def percentile(sorted_values: list[float], q: float) -> float:
    position = (len(sorted_values) - 1) * q
    low = int(position)
    high = min(low + 1, len(sorted_values) - 1)
    return sorted_values[low] + (sorted_values[high] - sorted_values[low]) * (position - low)


def cluster_interval(items: list[str], cluster_of: dict[str, str],
                     statistic: Callable[[list[str]], float], seed: int) -> list[float]:
    groups: dict[str, list[str]] = defaultdict(list)
    for item in items:
        groups[cluster_of[item]].append(item)
    keys = sorted(groups)
    rng = random.Random(seed)
    values = sorted(
        statistic([item for key in rng.choices(keys, k=len(keys)) for item in groups[key]])
        for _ in range(RESAMPLES)
    )
    return [round(percentile(values, 0.025), 2), round(percentile(values, 0.975), 2)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help=f"write {OUTPUT.relative_to(REPO)}")
    args = parser.parse_args()

    gold = final_gold()
    manifest = {row["generation_case_id"]: row for row in csv.DictReader(MANIFEST.open(encoding="utf-8"))}
    clusters = {
        "trajectory": {item: manifest[item]["trajectory_id"] for item in gold},
        "participant": {item: manifest[item]["participant_id_hash"] for item in gold},
    }

    supported = sorted(item for item, row in gold.items() if row["original_validity"] == "SUPPORTED")

    def resolved_percent(sample: list[str]) -> float:
        return 100 * sum(gold[item]["lifecycle_label"] == "RETIRE" for item in sample) / len(sample)

    result: dict[str, Any] = {
        "method": "percentile cluster bootstrap",
        "resamples": RESAMPLES,
        "seed": SEED,
        "provider_calls": 0,
        "resolution_among_supported": {
            "resolved": sum(gold[item]["lifecycle_label"] == "RETIRE" for item in supported),
            "supported": len(supported),
            "percent": round(resolved_percent(supported), 2),
            "ci95_trajectory": cluster_interval(supported, clusters["trajectory"], resolved_percent, SEED),
            "ci95_participant": cluster_interval(supported, clusters["participant"], resolved_percent, SEED),
        },
        "paired_c_minus_b": {},
    }

    for model in ("deepseek_v4_1_flash", "qwen_qwen3_8_27b"):
        b, c = decisions(model, "B"), decisions(model, "C")
        common = sorted(set(b) & set(c))

        def difference(sample: list[str], b=b, c=c) -> float:
            correct_c = sum(c[item] == gold[item]["lifecycle_label"] for item in sample)
            correct_b = sum(b[item] == gold[item]["lifecycle_label"] for item in sample)
            return 100 * (correct_c - correct_b) / len(sample)

        result["paired_c_minus_b"][model] = {
            "paired_n": len(common),
            "b_correct": sum(b[item] == gold[item]["lifecycle_label"] for item in common),
            "c_correct": sum(c[item] == gold[item]["lifecycle_label"] for item in common),
            "c_minus_b_pp": round(difference(common), 2),
            "ci95_trajectory": cluster_interval(common, clusters["trajectory"], difference, SEED),
            "ci95_participant": cluster_interval(common, clusters["participant"], difference, SEED),
        }

    text = json.dumps(result, indent=2)
    print(text)
    if args.write:
        OUTPUT.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
