from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "baselines" / "condition_B"))

import run_baseline  # noqa: E402


def recursive_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | set().union(*(recursive_keys(child) for child in value.values()))
    if isinstance(value, list):
        return set().union(*(recursive_keys(child) for child in value), set())
    return set()


class ConditionBBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        source = ROOT / "annotation" / "development_50_evidence_frozen_v1.jsonl"
        cls.packet = json.loads(source.read_text(encoding="utf-8").splitlines()[0])

    def test_projection_uses_only_condition_b_evidence(self) -> None:
        evidence, evidence_ids = run_baseline.project_evidence(self.packet)

        self.assertEqual(evidence["item_id"], "DEV_001")
        self.assertEqual(evidence["fixed_focal_claim"], self.packet["claim_span"]["text"])
        self.assertEqual(evidence["S_t"]["code"], self.packet["earlier"]["source"])
        self.assertEqual(evidence["S_t_plus_1"]["code"], self.packet["later"]["source"])
        self.assertIn("official_tests_and_results", evidence)
        self.assertIn("trace_evidence", evidence)
        self.assertEqual(evidence_ids, set(evidence["available_evidence_ids"]))
        self.assertFalse(
            recursive_keys(evidence)
            & {"annotator_1", "annotator_2", "predicted_label", "expected_lifecycle", "adjudicated_answer"}
        )

    def test_prediction_parser_requires_the_fixed_contract(self) -> None:
        _, evidence_ids = run_baseline.project_evidence(self.packet)
        response = json.dumps({
            "item_id": "DEV_001",
            "original_validity": "SUPPORTED",
            "target_state_t1": "PRESENT",
            "lifecycle_label": "KEEP",
            "instructional_priority": "LOW",
            "leakage_label": "ABSENT",
            "evidence_ids": ["source:DEV_001:S_t", "diff:DEV_001"],
            "short_reason": "The cited source and diff support this classification.",
        })
        parsed = run_baseline.parse_prediction(response, "DEV_001", evidence_ids)
        self.assertEqual(parsed["lifecycle_label"], "KEEP")

        bad_response = response.replace('"KEEP"', '"INVALID"')
        with self.assertRaises(ValueError):
            run_baseline.parse_prediction(bad_response, "DEV_001", evidence_ids)


if __name__ == "__main__":
    unittest.main()
