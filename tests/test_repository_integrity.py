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
            "README.md", "STATUS.md", "requirements.txt", ".gitignore",
            "docs/study_design.md", "docs/data_and_sampling.md", "data/README.md",
            "annotation/README.md", "annotation/annotation_schema.json",
            "annotation/tools/RevGround_Annotator_A01.html",
            "annotation/tools/RevGround_Annotator_A02.html",
            "scripts/profile_and_split.py", "scripts/rebuild_development_records.py",
            "scripts/generate_hints_openrouter.py", "scripts/replay_development_50.py",
            "scripts/evaluate_claims.py", "artifacts/current_status.json",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_manifest_counts_match_frozen_status(self) -> None:
        manifest_dir = ROOT / "data" / "manifests"
        expected = {
            "rubric_development_50_manifest.csv": 50,
            "fresh_calibration_25_manifest.csv": 25,
            "main_validation_191_manifest.csv": 191,
            "final_test_197_manifest.csv": 197,
        }
        for name, count in expected.items():
            with (manifest_dir / name).open(encoding="utf-8-sig", newline="") as handle:
                self.assertEqual(len(list(csv.DictReader(handle))), count, name)
        with (manifest_dir / "split_summary.csv").open(encoding="utf-8-sig", newline="") as handle:
            counts = {row["split"]: int(row["transitions"]) for row in csv.DictReader(handle)}
        self.assertEqual(counts, {"development": 590, "validation": 191, "test": 197})

    def test_annotation_packets_are_fixed_complete_and_blinded(self) -> None:
        packets = jsonl(ROOT / "annotation" / "development_50_evidence_frozen_v1.jsonl")
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

    def test_annotator_pages_embed_the_same_packets_but_use_separate_storage(self) -> None:
        pages = []
        for annotator in ("A01", "A02"):
            text = (ROOT / "annotation" / "tools" / f"RevGround_Annotator_{annotator}.html").read_text(encoding="utf-8")
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
        packet = jsonl(ROOT / "annotation" / "development_50_evidence_frozen_v1.jsonl")[0]
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

    def test_machine_status_does_not_claim_results(self) -> None:
        status = json.loads((ROOT / "artifacts" / "current_status.json").read_text(encoding="utf-8"))
        self.assertEqual(status["human_gold_claims"], 0)
        self.assertEqual(status["method_predictions"], 0)
        self.assertEqual(status["research_results"], 0)


if __name__ == "__main__":
    unittest.main()
