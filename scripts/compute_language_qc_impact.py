"""Compute documented downstream sensitivity counts after source-language QC.

The classifier itself is implemented in language_qc.py and is source-only.
This companion script uses the already-published Development annotations and
Stage-A run metadata only to quantify the requested sensitivity/eligibility
impact; it never feeds those fields back into QC classification.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


FIELDS = (
    "original_validity",
    "target_state_t1",
    "lifecycle_label",
    "instructional_priority",
    "leakage_label",
)


def kappa(pairs: list[tuple[Any, Any]]) -> tuple[int, float]:
    n = len(pairs)
    raw = sum(left == right for left, right in pairs)
    left = Counter(left for left, _ in pairs)
    right = Counter(right for _, right in pairs)
    categories = set(left) | set(right)
    observed = raw / n if n else 0.0
    expected = sum(left[value] * right[value] for value in categories) / (n * n) if n else 0.0
    score = 1.0 if expected == 1.0 else ((observed - expected) / (1.0 - expected) if n else 0.0)
    return raw, score


def load_jsonl_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    ids: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            ids.add(json.loads(line)["generation_case_id"])
    return ids


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--stage-a-errors", type=Path, default=None)
    args = parser.parse_args()
    repo = args.repo.resolve()
    qc = json.loads((repo / "data" / "qc" / "language_qc_summary.json").read_text(encoding="utf-8"))
    qc_rows = []
    with (repo / "data" / "qc" / "language_qc_all_strict_c.csv").open(encoding="utf-8", newline="") as handle:
        import csv
        qc_rows = list(csv.DictReader(handle))

    development_exclusions = sorted(
        row["development_item_id"]
        for row in qc_rows
        if row["development_item_id"] and row["qc_status"] != "CONFIRMED_C"
    )
    test_exclusions = sorted(
        row["test_id"]
        for row in qc_rows
        if row["test_id"] and row["qc_status"] != "CONFIRMED_C"
    )

    annotation_dir = repo / "annotation" / "development_50"
    a01 = {row["item_id"]: row for row in json.loads((annotation_dir / "revground_annotations_A01.json").read_text(encoding="utf-8"))}
    a02 = {row["item_id"]: row for row in json.loads((annotation_dir / "revground_annotations_A02.json").read_text(encoding="utf-8"))}
    eligible_dev = sorted(set(a01) - set(development_exclusions))
    sensitivity: dict[str, Any] = {"n": len(eligible_dev), "excluded_item_ids": development_exclusions}
    for field in FIELDS:
        raw, score = kappa([(a01[item][field], a02[item][field]) for item in eligible_dev])
        sensitivity[field] = {"raw_agreement": f"{raw}/{len(eligible_dev)}", "kappa": round(score, 4)}
    sensitivity["joint_five_field_agreement"] = {
        "raw_agreement": f"{sum(all(a01[item][field] == a02[item][field] for field in FIELDS) for item in eligible_dev)}/{len(eligible_dev)}"
    }

    stage_a_errors_path = args.stage_a_errors
    if stage_a_errors_path is None:
        stage_a_errors_path = repo.parent / "RevGround_Supervisor_Aligned_Package_v2" / "evaluation" / "stage_a_stealth_space_bunny_alpha" / "test_natural50_max512" / "errors.jsonl"
    stage_a_failures = sorted(load_jsonl_ids(stage_a_errors_path))
    stage_a_failures_eligible = sorted(set(stage_a_failures) - set(test_exclusions))
    eligible_test_n = 50 - len(test_exclusions)
    impact = {
        "protocol": "language_qc_experiment_impact_v1",
        "development": {
            "historical_primary_lifecycle_agreement": "48/50 (96%)",
            "historical_primary_lifecycle_kappa": 0.9228,
            "sensitivity_excluding_objective_language_exclusions": sensitivity,
        },
        "heldout_test_50": {
            "frozen_sample_n": 50,
            "objective_language_exclusions_n": len(test_exclusions),
            "objective_language_exclusion_ids": test_exclusions,
            "eligible_confirmed_c_n": eligible_test_n,
            "stage_a_run": "stealth/space-bunny-alpha; 50 provider calls; 44 usable hints; 6 failures; automatic retry disabled",
            "stage_a_failure_ids": stage_a_failures,
            "stage_a_failures_among_eligible": stage_a_failures_eligible,
            "stage_a_failures_among_eligible_n": len(stage_a_failures_eligible),
            "final_analyzable_n": eligible_test_n - len(stage_a_failures_eligible),
            "stage_a_errors_source": str(stage_a_errors_path),
        },
        "calibration_20": {
            "selected_n": 20,
            "confirmed_c_n": qc["calibration"]["mapped_calibration_20_n"],
            "objective_language_exclusions_n": len(qc["calibration"]["objective_exclusions_in_calibration_20"]),
            "annotation_status": "not_started",
        },
    }
    out = repo / "data" / "qc" / "language_qc_experiment_impact.json"
    out.write_text(json.dumps(impact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(impact, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
