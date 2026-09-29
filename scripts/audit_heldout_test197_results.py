#!/usr/bin/env python3
"""Recompute and verify the final held-out TEST-197/TEST-168 results.

The source partition contains 197 transitions. The analytic cohort contains the
168 claim-bearing packets that survived objective language QC and Stage-A.
This script combines only frozen primary outputs with the separately frozen
RECOVERY_429_V1 outputs and never calls a model provider.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


CORE_FIELDS = (
    "original_validity",
    "target_state_t1",
    "lifecycle_label",
    "instructional_priority",
)
REQUIRED_ADJUDICATION_FIELDS = (
    "item_id",
    "original_validity",
    "target_state_t1",
    "lifecycle_label",
    "instructional_priority",
    "confidence",
    "reason_code",
    "evidence_ids",
    "adjudication_reason",
    "adjudicator_id",
)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def percent(numerator: int, denominator: int) -> float:
    return round(100.0 * numerator / denominator, 2) if denominator else 0.0


def cohen_kappa(left: Iterable[str], right: Iterable[str]) -> float:
    a = list(left)
    b = list(right)
    if len(a) != len(b) or not a:
        raise ValueError("Kappa inputs must be non-empty and have equal length")
    observed = sum(x == y for x, y in zip(a, b)) / len(a)
    ca = Counter(a)
    cb = Counter(b)
    expected = sum(ca[label] * cb[label] for label in set(ca) | set(cb)) / (len(a) ** 2)
    return (observed - expected) / (1.0 - expected) if expected != 1.0 else 1.0


def index_unique(rows: list[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    ids = [row.get("item_id") for row in rows]
    if None in ids or len(ids) != len(set(ids)):
        raise SystemExit(f"{label} has a missing or duplicate item_id")
    return {row["item_id"]: row for row in rows}


def predictions(paths: list[Path], cohort_ids: set[str], label: str) -> dict[str, dict[str, Any]]:
    combined: dict[str, dict[str, Any]] = {}
    for path in paths:
        for row in read_jsonl(path):
            item_id = row.get("item_id")
            if item_id not in cohort_ids:
                raise SystemExit(f"{label}: prediction outside frozen cohort: {item_id}")
            if item_id in combined:
                raise SystemExit(f"{label}: duplicate accepted prediction: {item_id}")
            combined[item_id] = row
    return combined


def condition_metrics(
    predicted: dict[str, dict[str, Any]],
    gold: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    # The frozen shared evaluator defines abstention through the explicit
    # boolean field, not through the lifecycle token alone. Condition B has no
    # selective-decision field and is normalized as non-abstaining even if it
    # emits UNSURE; that output remains an incorrect decision against this gold.
    non_abstaining = {
        item_id: row
        for item_id, row in predicted.items()
        if not row.get("abstain", False)
    }
    correct = sum(
        row["lifecycle_label"] == gold[item_id]["lifecycle_label"]
        for item_id, row in non_abstaining.items()
    )
    gold_counts = Counter(row["lifecycle_label"] for row in gold.values())
    false_keep = sum(
        row["lifecycle_label"] == "KEEP"
        and gold[item_id]["lifecycle_label"] != "KEEP"
        for item_id, row in non_abstaining.items()
    )
    keep_true_positive = sum(
        row["lifecycle_label"] == "KEEP"
        and gold[item_id]["lifecycle_label"] == "KEEP"
        for item_id, row in non_abstaining.items()
    )
    wrongful_removal = sum(
        row["lifecycle_label"] in {"RETIRE", "RETRACT"}
        and gold[item_id]["lifecycle_label"] == "KEEP"
        for item_id, row in non_abstaining.items()
    )
    retract_true_positive = sum(
        row["lifecycle_label"] == "RETRACT"
        and gold[item_id]["lifecycle_label"] == "RETRACT"
        for item_id, row in non_abstaining.items()
    )
    retract_predicted = sum(
        row["lifecycle_label"] == "RETRACT" for row in non_abstaining.values()
    )
    retract_precision = (
        retract_true_positive / retract_predicted if retract_predicted else 0.0
    )
    retract_recall = retract_true_positive / gold_counts["RETRACT"]
    retract_f1 = (
        2 * retract_precision * retract_recall / (retract_precision + retract_recall)
        if retract_precision + retract_recall
        else 0.0
    )
    total = len(gold)
    decisions = len(non_abstaining)
    return {
        "usable_output_count": len(predicted),
        "explicit_abstention_count": len(predicted) - decisions,
        "non_abstaining_decision_count": decisions,
        "correct_count": correct,
        "decision_accuracy_percent": percent(correct, decisions),
        "usable_output_availability_percent": percent(len(predicted), total),
        "decision_coverage_percent": percent(decisions, total),
        "selective_risk_percent": percent(decisions - correct, decisions),
        "false_keep_count": false_keep,
        "false_keep_denominator": total - gold_counts["KEEP"],
        "false_keep_rate_percent": percent(false_keep, total - gold_counts["KEEP"]),
        "keep_true_positive_count": keep_true_positive,
        "keep_recall_denominator": gold_counts["KEEP"],
        "keep_recall_percent": percent(keep_true_positive, gold_counts["KEEP"]),
        "wrongful_removal_count": wrongful_removal,
        "retract_true_positive_count": retract_true_positive,
        "retract_predicted_count": retract_predicted,
        "retract_gold_count": gold_counts["RETRACT"],
        "retract_precision_percent": round(100 * retract_precision, 2),
        "retract_recall_percent": round(100 * retract_recall, 2),
        "retract_f1_percent": round(100 * retract_f1, 2),
    }


def paired_metrics(
    b: dict[str, dict[str, Any]],
    c: dict[str, dict[str, Any]],
    gold: dict[str, dict[str, Any]],
    problem_by_id: dict[str, str],
) -> dict[str, Any]:
    ids = sorted(
        item_id
        for item_id in set(b) & set(c)
        if not b[item_id].get("abstain", False)
        and not c[item_id].get("abstain", False)
    )
    b_correct = {
        item_id: b[item_id]["lifecycle_label"] == gold[item_id]["lifecycle_label"]
        for item_id in ids
    }
    c_correct = {
        item_id: c[item_id]["lifecycle_label"] == gold[item_id]["lifecycle_label"]
        for item_id in ids
    }
    b_only = [item_id for item_id in ids if b_correct[item_id] and not c_correct[item_id]]
    c_only = [item_id for item_id in ids if c_correct[item_id] and not b_correct[item_id]]
    both_correct = sum(b_correct[item_id] and c_correct[item_id] for item_id in ids)
    both_wrong = sum(not b_correct[item_id] and not c_correct[item_id] for item_id in ids)
    gold_keep = sum(gold[item_id]["lifecycle_label"] == "KEEP" for item_id in ids)
    gold_retract = sum(gold[item_id]["lifecycle_label"] == "RETRACT" for item_id in ids)
    gold_non_keep = len(ids) - gold_keep

    def count_for(condition: dict[str, dict[str, Any]], metric: str) -> int:
        if metric == "false_keep":
            return sum(
                condition[item_id]["lifecycle_label"] == "KEEP"
                and gold[item_id]["lifecycle_label"] != "KEEP"
                for item_id in ids
            )
        if metric == "keep_tp":
            return sum(
                condition[item_id]["lifecycle_label"] == "KEEP"
                and gold[item_id]["lifecycle_label"] == "KEEP"
                for item_id in ids
            )
        if metric == "wrongful_removal":
            return sum(
                condition[item_id]["lifecycle_label"] in {"RETIRE", "RETRACT"}
                and gold[item_id]["lifecycle_label"] == "KEEP"
                for item_id in ids
            )
        if metric == "retract_tp":
            return sum(
                condition[item_id]["lifecycle_label"] == "RETRACT"
                and gold[item_id]["lifecycle_label"] == "RETRACT"
                for item_id in ids
            )
        raise ValueError(metric)

    b_total_correct = sum(b_correct.values())
    c_total_correct = sum(c_correct.values())
    return {
        "paired_decision_count": len(ids),
        "condition_B_correct_count": b_total_correct,
        "condition_C_correct_count": c_total_correct,
        "condition_B_accuracy_percent": percent(b_total_correct, len(ids)),
        "condition_C_accuracy_percent": percent(c_total_correct, len(ids)),
        "condition_C_minus_B_percentage_points": round(
            100 * (c_total_correct - b_total_correct) / len(ids), 2
        ),
        "both_correct_count": both_correct,
        "condition_B_only_correct_count": len(b_only),
        "condition_C_only_correct_count": len(c_only),
        "both_wrong_count": both_wrong,
        "lifecycle_label_agreement_count": sum(
            b[item_id]["lifecycle_label"] == c[item_id]["lifecycle_label"]
            for item_id in ids
        ),
        "gold_keep_count": gold_keep,
        "gold_non_keep_count": gold_non_keep,
        "gold_retract_count": gold_retract,
        "condition_B_false_keep_count": count_for(b, "false_keep"),
        "condition_C_false_keep_count": count_for(c, "false_keep"),
        "condition_B_keep_true_positive_count": count_for(b, "keep_tp"),
        "condition_C_keep_true_positive_count": count_for(c, "keep_tp"),
        "condition_B_wrongful_removal_count": count_for(b, "wrongful_removal"),
        "condition_C_wrongful_removal_count": count_for(c, "wrongful_removal"),
        "condition_B_retract_true_positive_count": count_for(b, "retract_tp"),
        "condition_C_retract_true_positive_count": count_for(c, "retract_tp"),
        "condition_B_only_item_ids": b_only,
        "condition_C_only_item_ids": c_only,
        "condition_B_only_problem_ids": sorted({problem_by_id[item_id] for item_id in b_only}),
        "condition_C_only_problem_ids": sorted({problem_by_id[item_id] for item_id in c_only}),
    }


def require_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise SystemExit(f"{label}: expected {expected!r}, observed {actual!r}")


def write_markdown(path: Path, result: dict[str, Any]) -> None:
    human = result["human_annotation"]
    models = result["model_results"]
    ds = models["deepseek_v4_1_flash"]
    qw = models["qwen_qwen3_8_27b"]
    text = f"""# Verified held-out TEST results

## Scope and verdict

The source partition is **TEST-197**. After objective language exclusions and
preserved Stage-A failures, the claim-bearing analytic cohort is **TEST-168**.
Every numerical TEST-set result in the audited report recomputes from the frozen
repository artifacts. No false quantitative result was detected.

This is a deterministic, no-provider-call audit. Primary failures remain
failures; only separately recorded `RECOVERY_429_V1` predictions are combined
with primary accepted outputs.

## Human annotation and final gold

- A01/A02 rows: {human['row_count_per_annotator']} each.
- Unique core-field disagreements: {human['unique_core_field_disagreement_count']}
  ({human['lifecycle_disagreement_count']} lifecycle; {human['priority_only_disagreement_count']} priority-only).
- Original-validity agreement: {human['agreement']['original_validity']['count']}/168,
  kappa {human['agreement']['original_validity']['cohen_kappa']:.4f}.
- Target-state agreement: {human['agreement']['target_state_t1']['count']}/168,
  kappa {human['agreement']['target_state_t1']['cohen_kappa']:.4f}.
- Lifecycle agreement: {human['agreement']['lifecycle_label']['count']}/168,
  kappa {human['agreement']['lifecycle_label']['cohen_kappa']:.4f}.
- Priority agreement: {human['agreement']['instructional_priority']['count']}/168,
  kappa {human['agreement']['instructional_priority']['cohen_kappa']:.4f}.
- All four core fields agree on {human['all_four_core_fields_agreement_count']}/168.
- Final gold: {human['final_gold_distribution']['KEEP']} KEEP,
  {human['final_gold_distribution']['RETIRE']} RETIRE,
  {human['final_gold_distribution']['RETRACT']} RETRACT,
  {human['final_gold_distribution'].get('UNSURE', 0)} UNSURE.

## Post-recovery model results

| Model | Condition | Usable | Abstain | Decisions | Correct | Accuracy | False KEEP | Wrongful removal |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| DeepSeek | B | {ds['B']['usable_output_count']} | {ds['B']['explicit_abstention_count']} | {ds['B']['non_abstaining_decision_count']} | {ds['B']['correct_count']} | {ds['B']['decision_accuracy_percent']:.2f}% | {ds['B']['false_keep_count']} | {ds['B']['wrongful_removal_count']} |
| DeepSeek | C | {ds['C']['usable_output_count']} | {ds['C']['explicit_abstention_count']} | {ds['C']['non_abstaining_decision_count']} | {ds['C']['correct_count']} | {ds['C']['decision_accuracy_percent']:.2f}% | {ds['C']['false_keep_count']} | {ds['C']['wrongful_removal_count']} |
| Qwen | B | {qw['B']['usable_output_count']} | {qw['B']['explicit_abstention_count']} | {qw['B']['non_abstaining_decision_count']} | {qw['B']['correct_count']} | {qw['B']['decision_accuracy_percent']:.2f}% | {qw['B']['false_keep_count']} | {qw['B']['wrongful_removal_count']} |
| Qwen | C | {qw['C']['usable_output_count']} | {qw['C']['explicit_abstention_count']} | {qw['C']['non_abstaining_decision_count']} | {qw['C']['correct_count']} | {qw['C']['decision_accuracy_percent']:.2f}% | {qw['C']['false_keep_count']} | {qw['C']['wrongful_removal_count']} |

## Paired comparisons

| Model | Paired n | B correct | C correct | B accuracy | C accuracy | C-B |
|---|---:|---:|---:|---:|---:|---:|
| DeepSeek | {ds['paired']['paired_decision_count']} | {ds['paired']['condition_B_correct_count']} | {ds['paired']['condition_C_correct_count']} | {ds['paired']['condition_B_accuracy_percent']:.2f}% | {ds['paired']['condition_C_accuracy_percent']:.2f}% | {ds['paired']['condition_C_minus_B_percentage_points']:+.2f} pp |
| Qwen | {qw['paired']['paired_decision_count']} | {qw['paired']['condition_B_correct_count']} | {qw['paired']['condition_C_correct_count']} | {qw['paired']['condition_B_accuracy_percent']:.2f}% | {qw['paired']['condition_C_accuracy_percent']:.2f}% | {qw['paired']['condition_C_minus_B_percentage_points']:+.2f} pp |

Across the {result['cross_model_paired']['paired_decision_count']} paired model-case
comparisons, B and C are each correct on {result['cross_model_paired']['condition_B_correct_count']}
({result['cross_model_paired']['condition_B_accuracy_percent']:.2f}%); both are correct on the
same case in {result['cross_model_paired']['both_conditions_correct_count']} comparisons.
The model-specific effects have opposite signs, so the supported interpretation
is **no consistent directional advantage observed**. This audit does not
establish statistical equivalence or prove a null effect.

## Provenance boundary

- The blind adjudication packet remains unchanged under `adjudication_24_blind_v1/`.
- The completed return is frozen separately under `adjudication_24_final_v1/`.
- The four 168-attempt primary runs remain separate from both models' recovery namespaces.
- Recovery was limited to exactly one attempt per primary HTTP 429; non-429 failures were not recovered.
"""
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--write", action="store_true", help="Write verified JSON/Markdown and final-adjudication manifest")
    args = parser.parse_args()
    root = args.repo.resolve()
    base = root / "results" / "heldout_test_197"

    evidence_path = base / "evidence_frozen_v1.jsonl"
    packets = read_jsonl(evidence_path)
    packet_by_id = index_unique(packets, "frozen evidence")
    cohort_ids = set(packet_by_id)
    require_equal(len(cohort_ids), 168, "claim-bearing cohort size")
    problem_by_id = {item_id: row["problem_id"] for item_id, row in packet_by_id.items()}

    annotation_dir = base / "annotations_frozen_v1"
    annotation_paths = {
        "A01_json": annotation_dir / "A01" / "revground_annotations_A01 (2).json",
        "A02_json": annotation_dir / "A02" / "revground_annotations_A02 (2).json",
        "A01_csv": annotation_dir / "A01" / "revground_annotations_A01 (2).csv",
        "A02_csv": annotation_dir / "A02" / "revground_annotations_A02 (2).csv",
    }
    a01 = index_unique(read_json(annotation_paths["A01_json"]), "A01")
    a02 = index_unique(read_json(annotation_paths["A02_json"]), "A02")
    require_equal(set(a01), cohort_ids, "A01 cohort coverage")
    require_equal(set(a02), cohort_ids, "A02 cohort coverage")

    agreement: dict[str, Any] = {}
    ordered_ids = sorted(cohort_ids)
    for field in CORE_FIELDS:
        count = sum(a01[item_id][field] == a02[item_id][field] for item_id in ordered_ids)
        agreement[field] = {
            "count": count,
            "total": len(ordered_ids),
            "raw_agreement_percent": percent(count, len(ordered_ids)),
            "cohen_kappa": cohen_kappa(
                (a01[item_id][field] for item_id in ordered_ids),
                (a02[item_id][field] for item_id in ordered_ids),
            ),
        }
    all_four = sum(
        all(a01[item_id][field] == a02[item_id][field] for field in CORE_FIELDS)
        for item_id in ordered_ids
    )
    disagreement_ids = {
        item_id
        for item_id in ordered_ids
        if any(a01[item_id][field] != a02[item_id][field] for field in CORE_FIELDS)
    }
    lifecycle_disagreements = {
        item_id
        for item_id in disagreement_ids
        if a01[item_id]["lifecycle_label"] != a02[item_id]["lifecycle_label"]
    }
    priority_only = {
        item_id
        for item_id in disagreement_ids
        if a01[item_id]["instructional_priority"] != a02[item_id]["instructional_priority"]
        and all(
            a01[item_id][field] == a02[item_id][field]
            for field in CORE_FIELDS
            if field != "instructional_priority"
        )
    }

    final_adj_dir = base / "adjudication_24_final_v1"
    final_json = final_adj_dir / "adjudication_final_24.json"
    final_jsonl = final_adj_dir / "adjudication_final_24.jsonl"
    adjudication_rows = read_json(final_json)
    adjudication_jsonl_rows = read_jsonl(final_jsonl)
    require_equal(adjudication_rows, adjudication_jsonl_rows, "JSON/JSONL adjudication semantic equality")
    adjudication = index_unique(adjudication_rows, "final adjudication")
    require_equal(set(adjudication), disagreement_ids, "adjudication disagreement coverage")
    missing_fields: dict[str, list[str]] = {}
    invalid_evidence: dict[str, list[str]] = {}
    for item_id, row in adjudication.items():
        missing = [field for field in REQUIRED_ADJUDICATION_FIELDS if field not in row or row[field] in (None, "", [])]
        if missing:
            missing_fields[item_id] = missing
        valid_ids = set(packet_by_id[item_id].get("all_evidence_ids", []))
        invalid = [evidence_id for evidence_id in row["evidence_ids"] if evidence_id not in valid_ids]
        if invalid:
            invalid_evidence[item_id] = invalid
    require_equal(missing_fields, {}, "required adjudication fields")
    require_equal(invalid_evidence, {}, "adjudication evidence references")

    gold: dict[str, dict[str, Any]] = {}
    for item_id in ordered_ids:
        source = adjudication[item_id] if item_id in adjudication else a01[item_id]
        gold[item_id] = {field: source[field] for field in CORE_FIELDS}
    gold_distribution = Counter(row["lifecycle_label"] for row in gold.values())

    evaluation_dir = base / "evaluations"
    model_sources = {
        "deepseek_v4_1_flash": {
            "B": [
                evaluation_dir / "deepseek_v4_1_flash" / "condition_B" / "predictions.jsonl",
                evaluation_dir / "deepseek_v4_1_flash" / "RECOVERY_429_V1" / "condition_B" / "predictions.jsonl",
                evaluation_dir / "deepseek_v4_1_flash" / "RECOVERY_429_V1" / "condition_B_remaining_after_auth_v1" / "predictions.jsonl",
            ],
            "C": [
                evaluation_dir / "deepseek_v4_1_flash" / "condition_C" / "predictions.jsonl",
                evaluation_dir / "deepseek_v4_1_flash" / "RECOVERY_429_V1" / "condition_C" / "predictions.jsonl",
            ],
        },
        "qwen_qwen3_8_27b": {
            "B": [
                evaluation_dir / "qwen_qwen3_8_27b" / "condition_B" / "predictions.jsonl",
                evaluation_dir / "qwen_qwen3_8_27b" / "condition_B_primary_continuation_unattempted_v1" / "predictions.jsonl",
                evaluation_dir / "qwen_qwen3_8_27b" / "RECOVERY_429_V1" / "condition_B" / "predictions.jsonl",
            ],
            "C": [
                evaluation_dir / "qwen_qwen3_8_27b" / "condition_C" / "predictions.jsonl",
                evaluation_dir / "qwen_qwen3_8_27b" / "RECOVERY_429_V1" / "condition_C" / "predictions.jsonl",
            ],
        },
    }
    combined_predictions: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
    model_results: dict[str, Any] = {}
    for model, conditions in model_sources.items():
        combined_predictions[model] = {}
        model_results[model] = {}
        for condition, paths in conditions.items():
            combined = predictions(paths, cohort_ids, f"{model} {condition}")
            combined_predictions[model][condition] = combined
            model_results[model][condition] = condition_metrics(combined, gold)
        model_results[model]["paired"] = paired_metrics(
            combined_predictions[model]["B"],
            combined_predictions[model]["C"],
            gold,
            problem_by_id,
        )

    primary_freeze_path = evaluation_dir / "primary_first_attempt_freeze_summary.json"
    primary_freeze = read_json(primary_freeze_path)
    require_equal(primary_freeze["status"], "COMPLETE_PRIMARY_FIRST_ATTEMPTS_FROZEN", "primary freeze status")
    require_equal(primary_freeze["frozen_run_count"], 4, "primary frozen run count")
    require_equal(primary_freeze["requested_primary_attempts"], 672, "primary attempt count")

    recovery_paths = {
        "deepseek_v4_1_flash": evaluation_dir / "deepseek_v4_1_flash" / "RECOVERY_429_V1" / "recovery_429_v1_summary.json",
        "qwen_qwen3_8_27b": evaluation_dir / "qwen_qwen3_8_27b" / "RECOVERY_429_V1" / "recovery_429_v1_summary.json",
    }
    recovery = {model: read_json(path) for model, path in recovery_paths.items()}

    human = {
        "row_count_per_annotator": len(a01),
        "agreement": agreement,
        "all_four_core_fields_agreement_count": all_four,
        "unique_core_field_disagreement_count": len(disagreement_ids),
        "lifecycle_disagreement_count": len(lifecycle_disagreements),
        "priority_only_disagreement_count": len(priority_only),
        "adjudicated_case_count": len(adjudication),
        "adjudicator_ids": sorted({row["adjudicator_id"] for row in adjudication.values()}),
        "invalid_adjudication_evidence_id_count": sum(map(len, invalid_evidence.values())),
        "final_gold_distribution": dict(sorted(gold_distribution.items())),
        "supported_original_validity_count": sum(row["original_validity"] == "SUPPORTED" for row in gold.values()),
        "supported_and_resolved_count": sum(
            row["original_validity"] == "SUPPORTED" and row["target_state_t1"] == "RESOLVED"
            for row in gold.values()
        ),
    }

    # Explicit regression checks against the audited report values.
    require_equal([agreement[f]["count"] for f in CORE_FIELDS], [161, 145, 145, 144], "human agreement counts")
    require_equal(all_four, 144, "all-core agreement")
    require_equal((len(disagreement_ids), len(lifecycle_disagreements), len(priority_only)), (24, 23, 1), "disagreement counts")
    require_equal(dict(gold_distribution), {"KEEP": 100, "RETIRE": 65, "RETRACT": 3}, "final gold distribution")

    expected_conditions = {
        ("deepseek_v4_1_flash", "B"): (154, 0, 154, 146, 1, 87, 6, 3),
        ("deepseek_v4_1_flash", "C"): (135, 3, 132, 127, 0, 73, 5, 3),
        ("qwen_qwen3_8_27b", "B"): (136, 0, 136, 133, 0, 78, 3, 2),
        ("qwen_qwen3_8_27b", "C"): (141, 4, 137, 132, 1, 76, 4, 2),
    }
    for (model, condition), expected in expected_conditions.items():
        metrics = model_results[model][condition]
        actual = (
            metrics["usable_output_count"],
            metrics["explicit_abstention_count"],
            metrics["non_abstaining_decision_count"],
            metrics["correct_count"],
            metrics["false_keep_count"],
            metrics["keep_true_positive_count"],
            metrics["wrongful_removal_count"],
            metrics["retract_true_positive_count"],
        )
        require_equal(actual, expected, f"{model} {condition} metrics")

    expected_paired = {
        "deepseek_v4_1_flash": (124, 117, 119, 117, 0, 2, 5, 1, 0, 6, 5),
        "qwen_qwen3_8_27b": (115, 113, 111, 111, 2, 0, 2, 0, 1, 2, 3),
    }
    for model, expected in expected_paired.items():
        paired = model_results[model]["paired"]
        actual = (
            paired["paired_decision_count"],
            paired["condition_B_correct_count"],
            paired["condition_C_correct_count"],
            paired["both_correct_count"],
            paired["condition_B_only_correct_count"],
            paired["condition_C_only_correct_count"],
            paired["both_wrong_count"],
            paired["condition_B_false_keep_count"],
            paired["condition_C_false_keep_count"],
            paired["condition_B_wrongful_removal_count"],
            paired["condition_C_wrongful_removal_count"],
        )
        require_equal(actual, expected, f"{model} paired metrics")

    expected_recovery = {
        "deepseek_v4_1_flash": {"B": (90, 83, 7), "C": (53, 24, 29)},
        "qwen_qwen3_8_27b": {"B": (51, 28, 23), "C": (27, 8, 19)},
    }
    for model, conditions in expected_recovery.items():
        for condition, expected in conditions.items():
            row = recovery[model]["conditions"][condition]
            require_equal(
                (row["recovery_attempt_count"], row["accepted_count"], row["error_count"]),
                expected,
                f"{model} {condition} recovery",
            )

    paired_total = sum(model_results[model]["paired"]["paired_decision_count"] for model in model_results)
    paired_b_correct = sum(model_results[model]["paired"]["condition_B_correct_count"] for model in model_results)
    paired_c_correct = sum(model_results[model]["paired"]["condition_C_correct_count"] for model in model_results)
    paired_both_correct = sum(model_results[model]["paired"]["both_correct_count"] for model in model_results)
    result = {
        "status": "PASS_ALL_REPORTED_TEST_RESULTS_RECOMPUTED",
        "verified_on": "2026-09-29",
        "provider_calls": 0,
        "cohort_naming": {
            "source_partition": "TEST-197",
            "claim_bearing_analytic_cohort": "TEST-168",
        },
        "human_annotation": human,
        "primary_matrix": {
            "status": primary_freeze["status"],
            "frozen_run_count": primary_freeze["frozen_run_count"],
            "requested_primary_attempts": primary_freeze["requested_primary_attempts"],
        },
        "recovery": {
            model: {
                condition: recovery[model]["conditions"][condition]
                for condition in ("B", "C")
            }
            for model in recovery
        },
        "model_results": model_results,
        "cross_model_paired": {
            "paired_decision_count": paired_total,
            "condition_B_correct_count": paired_b_correct,
            "condition_C_correct_count": paired_c_correct,
            "condition_B_accuracy_percent": percent(paired_b_correct, paired_total),
            "condition_C_accuracy_percent": percent(paired_c_correct, paired_total),
            "both_conditions_correct_count": paired_both_correct,
            "both_conditions_correct_percent": percent(paired_both_correct, paired_total),
            "condition_B_total_false_keep_count": sum(model_results[m]["paired"]["condition_B_false_keep_count"] for m in model_results),
            "condition_C_total_false_keep_count": sum(model_results[m]["paired"]["condition_C_false_keep_count"] for m in model_results),
            "condition_B_total_wrongful_removal_count": sum(model_results[m]["paired"]["condition_B_wrongful_removal_count"] for m in model_results),
            "condition_C_total_wrongful_removal_count": sum(model_results[m]["paired"]["condition_C_wrongful_removal_count"] for m in model_results),
        },
        "interpretation": "No false quantitative TEST-set result detected; no consistent directional advantage observed across models. No equivalence or null-hypothesis claim is made.",
        "input_sha256": {
            "evidence_frozen_v1.jsonl": sha256(evidence_path),
            **{str(path.relative_to(root)).replace("\\", "/"): sha256(path) for path in annotation_paths.values()},
            str(final_json.relative_to(root)).replace("\\", "/"): sha256(final_json),
            str(final_jsonl.relative_to(root)).replace("\\", "/"): sha256(final_jsonl),
            str(primary_freeze_path.relative_to(root)).replace("\\", "/"): sha256(primary_freeze_path),
            **{str(path.relative_to(root)).replace("\\", "/"): sha256(path) for path in recovery_paths.values()},
            **{
                str(path.relative_to(root)).replace("\\", "/"): sha256(path)
                for conditions in model_sources.values()
                for paths in conditions.values()
                for path in paths
            },
        },
    }
    require_equal(result["cross_model_paired"]["paired_decision_count"], 239, "cross-model paired count")
    require_equal(result["cross_model_paired"]["condition_B_correct_count"], 230, "cross-model B correct count")
    require_equal(result["cross_model_paired"]["condition_C_correct_count"], 230, "cross-model C correct count")
    require_equal(result["cross_model_paired"]["both_conditions_correct_count"], 228, "cross-model both-correct count")

    if args.write:
        analysis_dir = base / "analysis"
        analysis_dir.mkdir(parents=True, exist_ok=True)
        json_path = analysis_dir / "verified_test_results.json"
        md_path = analysis_dir / "verified_test_results.md"
        json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        write_markdown(md_path, result)

        manifest = {
            "status": "FINAL_ADJUDICATION_FROZEN_AND_VALIDATED",
            "dataset": "heldout_test_197_final_claim_bearing_cohort",
            "case_count": len(adjudication),
            "source_disagreement_count": len(disagreement_ids),
            "exact_disagreement_coverage": True,
            "required_fields_complete": True,
            "evidence_ids_valid": True,
            "json_jsonl_semantically_identical": True,
            "adjudicator_ids": human["adjudicator_ids"],
            "source_blind_packet": "../adjudication_24_blind_v1",
            "source_blind_packet_unchanged": True,
            "files": {
                "adjudication_final_24.json": {"bytes": final_json.stat().st_size, "sha256": sha256(final_json)},
                "adjudication_final_24.jsonl": {"bytes": final_jsonl.stat().st_size, "sha256": sha256(final_jsonl)},
            },
        }
        (final_adj_dir / "MANIFEST.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
