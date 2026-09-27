from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import evaluate_claims  # noqa: E402
import generate_hints_openrouter  # noqa: E402
import replay_development_50  # noqa: E402


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def recursive_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | set().union(*(recursive_keys(child) for child in value.values()))
    if isinstance(value, list):
        return set().union(*(recursive_keys(child) for child in value), set())
    return set()


class RepositoryIntegrityTests(unittest.TestCase):
    def test_public_structure_and_links_exist(self) -> None:
        for relative in (
            "README.md", "requirements.txt", ".gitignore",
            "docs/study_design.md", "docs/data_and_sampling.md", "data/README.md",
            "annotation/common/annotation_schema.json", "annotation/common/annotation_schema_v1.json",
            "annotation/common/LIFECYCLE_RUBRIC_v2.md", "annotation/common/ANNOTATOR_TRAINING_AND_BLINDING.md",
            "annotation/development_50/revground_annotations_A01.json", "annotation/development_50/revground_annotations_A02.json",
            "annotation/development_50/disagreement_cases.csv", "annotation/development_50/adjudication_cases.json",
            "annotation/development_50/pre_adjudication_summary.md",
            "annotation/development_50/RevGround_Adjudicator.html",
            "annotation/development_50/tools/RevGround_Annotator_A01.html",
            "annotation/development_50/tools/RevGround_Annotator_A02.html",
            "annotation/calibration_20/calibration_20_evidence_frozen_v1.jsonl",
            "annotation/calibration_20/LIFECYCLE_RUBRIC_v2.md",
            "annotation/calibration_20/tools/RevGround_Annotator_A01.html",
            "annotation/calibration_20/tools/RevGround_Annotator_A02.html",
            "annotation/stress_20/README.md", "annotation/heldout_test_50/README.md",
            "results/README.md", "results/development_50/README.md", "results/calibration_20/README.md",
            "results/stress_20/README.md", "results/stress_20/stress_20_results_summary.md", "results/RESULTS_HIGHLIGHTS.md", "results/heldout_test_50/README.md",
            "annotation/stress_20/synthetic_stress_20_human_review.csv", "annotation/stress_20/synthetic_stress_20_human_review.SHA256SUMS",
            "docs/COMPLETED_VS_PLANNED.md", "docs/readiness_gates.csv", "docs/SUPERVISOR_REQUIREMENTS_TRACEABILITY.csv",
            "docs/generation_policy.json", "docs/model_card.json", "data/sampling_plan.json",
            "artifacts/screening_counts.csv", "artifacts/evidence_inventory.csv",
            "results/development_50/development_50_agreement.csv", "results/development_50/lifecycle_confusion_matrix.csv",
            "data/development_50_manifest.csv", "data/manifests/calibration_20_manifest.csv",
            "data/manifests/calibration_20_manifest.json", "data/manifests/calibration_20_manifest.SHA256SUMS",
            "data/manifests/archive/fresh_calibration_25_manifest.csv", "data/manifests/archive/fresh_calibration_25_manifest.SUPERSEDED.md",
            "docs/SUPERVISOR_PROGRESS.md", "docs/MODEL_ACCESS.md",
            "scripts/profile_and_split.py", "scripts/rebuild_development_records.py",
            "scripts/generate_hints_openrouter.py", "scripts/replay_development_50.py",
            "scripts/evaluate_claims.py", "scripts/compute_agreement.py", "artifacts/current_status.json",
            "scripts/language_qc.py", "scripts/compute_language_qc_impact.py", "scripts/replay_calibration_20.py", "scripts/merge_calibration_execution_evidence.py", "scripts/verify_calibration_package.py",
            "data/qc/language_qc_all_strict_c.csv", "data/qc/language_qc_summary.json",
            "data/qc/language_qc_exclusions.csv", "data/qc/language_qc_experiment_impact.json", "data/qc/SHA256SUMS.txt",
            "results/calibration_20/calibration_20_packet_status.json", "results/calibration_20/calibration_20_build_manifest.json",
            "results/calibration_20/runs/calibration_20_execution_results.jsonl", "results/calibration_20/runs/calibration_20_evidence_pre_replay_v1.jsonl",
            "baselines/condition_B/.env.example", "baselines/condition_B/outputs/.gitkeep",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_pre_adjudication_artifacts_match_the_frozen_exports(self) -> None:
        with (ROOT / "results" / "development_50" / "development_50_agreement.csv").open(encoding="utf-8", newline="") as handle:
            agreement = list(csv.DictReader(handle))
        self.assertEqual(
            [(row["field"], row["raw_agreement"], row["kappa"]) for row in agreement],
            [
                ("original_validity", "48/50", "0.3243"),
                ("target_state_t1", "48/50", "0.9228"),
                ("lifecycle_label", "48/50", "0.9228"),
                ("instructional_priority", "44/50", "0.7608"),
                ("leakage_label", "45/50", "0.0000"),
            ],
        )
        with (ROOT / "annotation" / "development_50" / "disagreement_cases.csv").open(encoding="utf-8-sig", newline="") as handle:
            disagreements = list(csv.DictReader(handle))
        self.assertEqual(len(disagreements), 10)
        self.assertEqual(
            [row["item_id"] for row in disagreements if "lifecycle_label" in row["differing_label_fields"]],
            ["DEV_010", "DEV_012"],
        )

    def test_manifest_counts_match_frozen_status(self) -> None:
        manifest_dir = ROOT / "data" / "manifests"
        expected = {
            "rubric_development_50_manifest.csv": 50,
            "calibration_20_manifest.csv": 20,
            "main_validation_191_manifest.csv": 191,
            "final_test_197_manifest.csv": 197,
        }
        for name, count in expected.items():
            with (manifest_dir / name).open(encoding="utf-8-sig", newline="") as handle:
                self.assertEqual(len(list(csv.DictReader(handle))), count, name)
        with (manifest_dir / "archive" / "fresh_calibration_25_manifest.csv").open(encoding="utf-8-sig", newline="") as handle:
            self.assertEqual(len(list(csv.DictReader(handle))), 25)
        with (manifest_dir / "split_summary.csv").open(encoding="utf-8-sig", newline="") as handle:
            counts = {row["split"]: int(row["transitions"]) for row in csv.DictReader(handle)}
        self.assertEqual(counts, {"development": 590, "validation": 191, "test": 197})

    def test_annotation_packets_are_fixed_complete_and_blinded(self) -> None:
        packets = jsonl(ROOT / "annotation" / "development_50" / "development_50_evidence_frozen_v1.jsonl")
        self.assertEqual(len(packets), 50)
        self.assertEqual([row["item_id"] for row in packets], [f"DEV_{index:03d}" for index in range(1, 51)])
        forbidden = {"model", "model_requested", "model_returned", "provider", "provider_raw_response", "predicted_label", "system_prediction", "annotator_1", "annotator_2"}
        self.assertFalse(set().union(*(recursive_keys(row) for row in packets)) & forbidden)
        for packet in packets:
            content = {key: value for key, value in packet.items() if key != "packet_sha256"}
            digest = hashlib.sha256(json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            self.assertEqual(packet["packet_sha256"], digest)
            self.assertEqual(packet["claim_span"]["start"], 0)
            self.assertEqual(packet["claim_span"]["end"], len(packet["claim_span"]["text"]))
            for state in ("earlier", "later"):
                self.assertIn(packet["compiler"][state]["status"], {"compile_success", "compile_error", "infra_timeout"})
            for test in packet["tests"]:
                for state in ("earlier", "later"):
                    self.assertIn(test[state]["status"], {"PASS", "FAIL", "PROGRAM_TIMEOUT", "RUNTIME_ERROR", "INFRA_TIMEOUT", "NOT_RUN_COMPILE_ERROR"})

    def test_development_exports_are_byte_preserved_after_reorganization(self) -> None:
        self.assertEqual(
            hashlib.sha256((ROOT / "annotation" / "development_50" / "revground_annotations_A01.json").read_bytes()).hexdigest(),
            "76bb53c99bca14615550f12a1b670b4b05810364c8d7c54c882e477ac3ff7e6a",
        )
        self.assertEqual(
            hashlib.sha256((ROOT / "annotation" / "development_50" / "revground_annotations_A02.json").read_bytes()).hexdigest(),
            "f888018f61ee4a97f08c12795e0ac7bae6edd98ca0c3ebb0f5802faa39ad9822",
        )

    def test_calibration_manifest_and_packet_are_blinded(self) -> None:
        manifest_path = ROOT / "data" / "manifests" / "calibration_20_manifest.csv"
        with manifest_path.open(encoding="utf-8-sig", newline="") as handle:
            manifest = list(csv.DictReader(handle))
        self.assertEqual(len(manifest), 20)
        self.assertEqual({row["partition"] for row in manifest}, {"validation"})
        self.assertEqual([row["item_id"] for row in manifest], [f"CAL_{index:03d}" for index in range(1, 21)])
        manifest_json = json.loads((ROOT / "data" / "manifests" / "calibration_20_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest_json["n"], 20)
        self.assertTrue(manifest_json["created_before_labels"])
        self.assertEqual(manifest_json["source_partition"], "validation")
        packets = jsonl(ROOT / "annotation" / "calibration_20" / "calibration_20_evidence_frozen_v1.jsonl")
        self.assertEqual(len(packets), 16)
        forbidden = {"model", "model_requested", "model_returned", "provider", "provider_raw_response", "predicted_label", "system_prediction", "annotator_1", "annotator_2", "lifecycle_label", "original_validity", "target_state_t1"}
        self.assertFalse(set().union(*(recursive_keys(row) for row in packets)) & forbidden)
        for packet in packets:
            content = {key: value for key, value in packet.items() if key != "packet_sha256"}
            self.assertEqual(packet["packet_sha256"], hashlib.sha256(json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest())
            self.assertTrue(packet["item_id"].startswith("CAL_"))
            self.assertEqual(packet["claim_span"]["text"], packet["original_hint"][packet["claim_span"]["start"]:packet["claim_span"]["end"]])
            for state in ("earlier", "later"):
                self.assertIn(packet["compiler"][state]["status"], {"compile_success", "compile_error", "infra_timeout"})

        for annotator in ("A01", "A02"):
            page = ROOT / "annotation" / "calibration_20" / "tools" / f"RevGround_Annotator_{annotator}.html"
            text = page.read_text(encoding="utf-8")
            self.assertIn("const cases = [", text)
            self.assertNotRegex(text, r"model_requested|model_returned|provider_raw_response|predicted_label|system_prediction")
        self.assertEqual({path.name for path in (ROOT / "annotation" / "calibration_20").iterdir()}, {"LIFECYCLE_RUBRIC_v2.md", "calibration_20_evidence_frozen_v1.jsonl", "tools"})
        build = json.loads((ROOT / "results" / "calibration_20" / "calibration_20_build_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(build["status"], "COMPLETE_BLINDED_CALIBRATION_PACKAGE")
        self.assertEqual(build["stage_a"]["usable_hints"], 16)
        self.assertEqual(build["stage_a"]["failures_preserved"], 4)
        self.assertEqual(build["evidence_packets"]["rows"], 16)
        self.assertTrue(build["evidence_packets"]["same_top_level_schema_as_development"])
        self.assertEqual(build["execution_replay"]["runner_image"], "revground-c-runner:2.0")

    def test_stress_human_review_is_preserved_and_not_mislabeled_as_consensus(self) -> None:
        review = ROOT / "annotation" / "stress_20" / "synthetic_stress_20_human_review.csv"
        self.assertEqual(hashlib.sha256(review.read_bytes()).hexdigest(), "172d4160511183d4fa4c39f01b851c0dc1a8c023460f335a9f415b6bda61a224")
        with review.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 20)
        self.assertEqual({row["annotator_id"] for row in rows}, {"A_02"})
        self.assertEqual({label: sum(row["lifecycle_label"] == label for row in rows) for label in ("RETRACT", "UNSURE")}, {"RETRACT": 10, "UNSURE": 10})
        status = json.loads((ROOT / "artifacts" / "current_status.json").read_text(encoding="utf-8"))
        self.assertEqual(status["stress_20"]["qwen_b_c"], "complete_verified")
        self.assertTrue(status["stress_20"]["reported_separately_from_natural_prevalence"])

    def test_annotator_pages_embed_the_same_packets_but_use_separate_storage(self) -> None:
        pages = []
        for annotator in ("A01", "A02"):
            text = (ROOT / "annotation" / "development_50" / "tools" / f"RevGround_Annotator_{annotator}.html").read_text(encoding="utf-8")
            self.assertIn(f'const annotatorId = "{annotator}"', text)
            self.assertIn("revground_annotation_v2_${annotatorId}_", text)
            self.assertNotRegex(text, r"model_requested|model_returned|provider_raw_response|predicted_label|system_prediction")
            pages.append(re.sub(r"A0[12]", "ANN", text))
        self.assertEqual(pages[0], pages[1])

    def test_hint_prompt_uses_no_future_state(self) -> None:
        record = {
            "item_id": "DEV_001", "generation_case_id": "case",
            "problem_statement": "Add two integers.", "st_source": "int main(void){return 0;}",
            "st1_source": "FUTURE_SOURCE_MUST_NOT_APPEAR",
            "stored_judge_evidence": {"st": {"final_verdict": "Wrong Answer"}, "st1": {"final_verdict": "Accepted"}},
        }
        prompt, digest = generate_hints_openrouter.prompt_for(record)
        self.assertIn(record["st_source"], prompt)
        self.assertNotIn(record["st1_source"], prompt)
        self.assertNotIn("Accepted", prompt)
        self.assertEqual(digest, generate_hints_openrouter.sha256_text(prompt))

    def test_replay_adapter_reads_the_frozen_packet(self) -> None:
        packet = jsonl(ROOT / "annotation" / "development_50" / "development_50_evidence_frozen_v1.jsonl")[0]
        tests = replay_development_50.official_tests(packet)
        self.assertEqual(len(tests), len(packet["tests"]))
        self.assertEqual(tests[0]["test_id"], packet["tests"][0]["test_case_id"])

    def test_evaluation_keeps_false_keep_and_coverage_separate(self) -> None:
        def row(claim: str, method: str, gold: str, prediction: str, abstain: bool = False) -> dict:
            return {"claim_id": claim, "trajectory_id": "t" + claim, "participant_id_hash": "u", "problem_id": "p", "problem_family_id": "f", "method": method, "gold_label": gold, "predicted_label": prediction, "abstain": abstain, "confidence": 0.8, "latency_ms": 1.0, "estimated_cost_usd": 0.0, "status": "success"}
        rows = []
        for method in ("B", "C"):
            rows.extend([row("1", method, "KEEP", "KEEP"), row("2", method, "RETIRE", "KEEP" if method == "B" else "RETIRE")])
        result = evaluate_claims.evaluate(rows)
        self.assertEqual(result["methods"]["B"]["overall"]["false_keep"]["numerator"], 1)
        self.assertEqual(result["methods"]["C"]["overall"]["false_keep"]["numerator"], 0)

    def test_machine_status_preserves_diagnostic_and_gold_boundaries(self) -> None:
        status = json.loads((ROOT / "artifacts" / "current_status.json").read_text(encoding="utf-8"))
        self.assertEqual(status["human_gold_claims"], 50)
        self.assertEqual(status["development"]["adjudication"], "complete_final_reference")
        self.assertEqual(status["method_predictions"]["tracked_raw_predictions"], 0)
        self.assertTrue(status["research_results"].startswith("diagnostic_only"))
        self.assertEqual(status["stress_20"]["qwen_b_c"], "complete_verified")
        self.assertEqual(status["calibration_20"]["qwen_b_c"], "not_run")
        self.assertEqual(status["heldout_test_50"]["qwen_b_c"], "not_run")

    def test_source_language_qc_is_complete_and_preserves_objective_exclusions(self) -> None:
        with (ROOT / "data" / "qc" / "language_qc_all_strict_c.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 978)
        self.assertEqual(
            {status: sum(row["qc_status"] == status for row in rows) for status in ("CONFIRMED_C", "NON_C_CPP", "NON_C_JAVA", "AMBIGUOUS")},
            {"CONFIRMED_C": 954, "NON_C_CPP": 13, "NON_C_JAVA": 9, "AMBIGUOUS": 2},
        )
        self.assertEqual(len({row["transition_id"] for row in rows}), 978)
        by_item = {row["development_item_id"] or row["test_id"]: row for row in rows if row["development_item_id"] or row["test_id"]}
        self.assertEqual(by_item["DEV_010"]["qc_status"], "NON_C_JAVA")
        self.assertEqual(by_item["DEV_012"]["qc_status"], "NON_C_CPP")
        self.assertEqual(by_item["726478f13ad8e011c4a0cfa2"]["qc_status"], "NON_C_JAVA")
        self.assertEqual(by_item["bda05da230eecfb67fa3a104"]["qc_status"], "NON_C_CPP")
        with (ROOT / "data" / "qc" / "language_qc_exclusions.csv").open(encoding="utf-8", newline="") as handle:
            exclusions = list(csv.DictReader(handle))
        self.assertEqual(len(exclusions), 24)
        summary = json.loads((ROOT / "data" / "qc" / "language_qc_summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["heldout_test_50"]["eligible_confirmed_c_n"], 48)
        self.assertTrue(summary["calibration"]["all_20_confirmed_c"])


if __name__ == "__main__":
    unittest.main()
