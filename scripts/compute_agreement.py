"""Recompute the Development-50 inter-rater agreement artifacts.

The two JSON exports are treated as frozen inputs.  This script never writes to
either export; it writes only derived agreement tables and the disagreement
case index.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ANNOTATION_DIR = ROOT / "annotation" / "development_50"
ARTIFACTS_DIR = ROOT / "results" / "development_50"

FIELDS = (
    "original_validity",
    "target_state_t1",
    "lifecycle_label",
    "instructional_priority",
    "leakage_label",
)
LIFECYCLE_LABELS = ("KEEP", "RETIRE", "RETRACT", "UNSURE")


def load_export(path: Path, annotator_id: str) -> dict[str, dict[str, Any]]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or len(rows) != 50:
        raise ValueError(f"{path} must contain exactly 50 annotation records")

    by_item: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"{path} contains a non-object record")
        item_id = row.get("item_id")
        if not isinstance(item_id, str) or item_id in by_item:
            raise ValueError(f"{path} contains an invalid or duplicate item_id")
        if row.get("annotator_id") != annotator_id:
            raise ValueError(f"{path} has an unexpected annotator_id for {item_id}")
        by_item[item_id] = row

    expected_ids = {f"DEV_{index:03d}" for index in range(1, 51)}
    if set(by_item) != expected_ids:
        raise ValueError(f"{path} does not contain DEV_001 through DEV_050")
    return by_item


def kappa_and_agreement(
    pairs: list[tuple[str, str]],
) -> tuple[int, float]:
    n = len(pairs)
    raw = sum(left == right for left, right in pairs)
    categories = sorted({value for pair in pairs for value in pair})
    left_counts = Counter(left for left, _ in pairs)
    right_counts = Counter(right for _, right in pairs)
    observed = raw / n
    expected = sum(left_counts[label] * right_counts[label] for label in categories) / (n * n)
    kappa = 1.0 if expected == 1.0 else (observed - expected) / (1.0 - expected)
    return raw, kappa


def csv_value(value: Any) -> str:
    if isinstance(value, list):
        return "|".join(str(item) for item in value)
    return str(value)


def disagreement_rows(
    a01: dict[str, dict[str, Any]],
    a02: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    columns = [
        "item_id",
        "transition_id",
        "packet_id",
        "differing_label_fields",
        *[column for field in FIELDS for column in (f"A01_{field}", f"A02_{field}")],
        "A01_confidence",
        "A02_confidence",
        "A01_evidence_ids",
        "A02_evidence_ids",
        "A01_short_reason",
        "A02_short_reason",
    ]
    for item_id in sorted(a01):
        left = a01[item_id]
        right = a02[item_id]
        differing = [field for field in FIELDS if left[field] != right[field]]
        if not differing:
            continue
        row = {
            "item_id": item_id,
            "transition_id": str(left["transition_id"]),
            "packet_id": str(left["packet_id"]),
            "differing_label_fields": "; ".join(differing),
        }
        for field in FIELDS:
            row[f"A01_{field}"] = csv_value(left[field])
            row[f"A02_{field}"] = csv_value(right[field])
        row.update(
            {
                "A01_confidence": csv_value(left["confidence"]),
                "A02_confidence": csv_value(right["confidence"]),
                "A01_evidence_ids": csv_value(left["evidence_ids"]),
                "A02_evidence_ids": csv_value(right["evidence_ids"]),
                "A01_short_reason": csv_value(left["short_reason"]),
                "A02_short_reason": csv_value(right["short_reason"]),
            }
        )
        rows.append(row)
    return rows


def write_agreement_csv(a01: dict[str, dict[str, Any]], a02: dict[str, dict[str, Any]]) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for field in FIELDS:
        pairs = [(a01[item_id][field], a02[item_id][field]) for item_id in sorted(a01)]
        raw, kappa = kappa_and_agreement(pairs)
        rows.append({"field": field, "raw_agreement": f"{raw}/50", "kappa": f"{kappa:.4f}"})
    with (ARTIFACTS_DIR / "development_50_agreement.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["field", "raw_agreement", "kappa"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    matrix_path = ARTIFACTS_DIR / "lifecycle_confusion_matrix.csv"
    with matrix_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["A01\\A02", *LIFECYCLE_LABELS])
        for left_label in LIFECYCLE_LABELS:
            writer.writerow(
                [
                    left_label,
                    *[
                        sum(
                            a01[item_id]["lifecycle_label"] == left_label
                            and a02[item_id]["lifecycle_label"] == right_label
                            for item_id in a01
                        )
                        for right_label in LIFECYCLE_LABELS
                    ],
                ]
            )

    rows = disagreement_rows(a01, a02)
    disagreement_path = ANNOTATION_DIR / "disagreement_cases.csv"
    fieldnames = [
        "item_id",
        "transition_id",
        "packet_id",
        "differing_label_fields",
        *[column for field in FIELDS for column in (f"A01_{field}", f"A02_{field}")],
        "A01_confidence",
        "A02_confidence",
        "A01_evidence_ids",
        "A02_evidence_ids",
        "A01_short_reason",
        "A02_short_reason",
    ]
    with disagreement_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\r\n", quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {ARTIFACTS_DIR / 'development_50_agreement.csv'}")
    print(f"Wrote {matrix_path}")
    print(f"Wrote {disagreement_path} ({len(rows)} cases)")


def main() -> None:
    a01 = load_export(ANNOTATION_DIR / "feedback-lifecycle-audit_annotations_A01.json", "A01")
    a02 = load_export(ANNOTATION_DIR / "feedback-lifecycle-audit_annotations_A02.json", "A02")
    if set(a01) != set(a02):
        raise ValueError("A01 and A02 exports do not cover the same item IDs")
    write_agreement_csv(a01, a02)


if __name__ == "__main__":
    main()
