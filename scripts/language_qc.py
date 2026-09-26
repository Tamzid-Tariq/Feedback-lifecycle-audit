"""Source-language quality control for the strict-C transition pool.

This module deliberately does not load lifecycle labels, annotator exports, or
model results.  It classifies source text using only syntax found in code_t and
code_t1 plus the declared-language/split metadata needed to identify the pool.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


STATUS_ORDER = ["CONFIRMED_C", "NON_C_JAVA", "NON_C_CPP", "AMBIGUOUS"]
OUTPUT_FIELDS = [
    "transition_id",
    "declared_language",
    "detected_source_language",
    "qc_status",
    "reason",
    "partition",
    "development_item_id",
    "calibration_id",
    "test_id",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def compact(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def syntax_view(text: str) -> str:
    """Remove comments and string/char bodies while preserving token shape.

    Include directives are deliberately preserved because they are strong
    source-language signatures.  Raw text is also retained by the caller for
    signatures whose spelling itself matters.
    """

    text = re.sub(r"\"(?:\\.|[^\"\\])*\"", '""', text)
    text = re.sub(r"'(?:\\.|[^'\\])*'", "''", text)
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"//[^\n]*", " ", text)
    return text


JAVA_SIGNATURES: list[tuple[str, re.Pattern[str]]] = [
    ("package declaration", re.compile(r"\bpackage\s+[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*\s*;")),
    ("Java import", re.compile(r"\bimport\s+(?:java|javax|android|org)\s*\.\s*[\w$\.]+\s*;")),
    ("Java class declaration", re.compile(r"\b(?:public\s+|private\s+|protected\s+)?(?:final\s+|abstract\s+)?class\s+[A-Za-z_$][\w$]*\s*(?:extends\b|implements\b|\{|\n)")),
    ("Java main signature", re.compile(r"\bpublic\s+static\s+void\s+main\s*\(\s*String(?:\[\]|\s+\[\])")),
    ("System output/input", re.compile(r"\bSystem\s*\.\s*(?:out|in|err)\s*\.")),
    ("Java Scanner", re.compile(r"\bnew\s+Scanner\s*\(")),
    ("Java String type", re.compile(r"\bString\s+[A-Za-z_$][\w$]*\s*(?:=|;|\))")),
    ("Java Character API", re.compile(r"\bCharacter\s*\.\s*(?:isDigit|isLetter|toLowerCase|toUpperCase)\s*\(")),
]

CPP_SIGNATURES: list[tuple[str, re.Pattern[str]]] = [
    ("C++ standard header", re.compile(r"#\s*include\s*[<\"]\s*(?:iostream|vector|string|map|set|queue|stack|algorithm|bits\s*/\s*stdc\+\+\.h|sstream|fstream|iomanip|utility|unordered_map|unordered_set|deque|list|array|cmath|cstdint|cstring|limits|numeric|tuple|type_traits)\s*[>\"]")),
    ("std namespace qualifier", re.compile(r"\bstd\s*::")),
    ("C++ namespace directive", re.compile(r"\busing\s+namespace\s+std\s*;")),
    ("C++ stream operator", re.compile(r"\b(?:cout|cin|cerr|clog)\s*(?:<<|>>)|(?:<<|>>)\s*\b(?:cout|cin|cerr|clog)\b")),
    ("C++ template", re.compile(r"\btemplate\s*<")),
    ("C++ STL type", re.compile(r"\b(?:vector|string|map|set|queue|stack|unordered_map|unordered_set|deque|list|array)\s*<\s*[A-Za-z_]")),
    ("C++ nullptr type", re.compile(r"\bnullptr\b")),
]

C_SIGNATURES: list[tuple[str, re.Pattern[str]]] = [
    ("C standard header", re.compile(r"#\s*include\s*[<\"]\s*(?:stdio|stdlib|string|math|ctype|time|assert|limits|stdint|stdbool|stddef|errno|float|inttypes|locale|signal|setjmp|stdarg|wchar|wctype)\.h\s*[>\"]")),
    ("C stdio function", re.compile(r"\b(?:printf|fprintf|sprintf|snprintf|scanf|fscanf|sscanf|puts|getchar|putchar)\s*\(")),
    ("C allocation function", re.compile(r"\b(?:malloc|calloc|realloc|free)\s*\(")),
    ("C typedef/struct syntax", re.compile(r"\b(?:typedef\s+(?:struct|enum)|struct\s+[A-Za-z_]\w*\s*\{|enum\s+[A-Za-z_]\w*\s*\{)")),
    ("C sizeof operator", re.compile(r"\bsizeof\s*(?:\(|[A-Za-z_(])")),
]


def matched_signatures(text: str, signatures: list[tuple[str, re.Pattern[str]]]) -> list[str]:
    view = syntax_view(text)
    return [name for name, pattern in signatures if pattern.search(view)]


def classify_source(code_t: str, code_t1: str) -> tuple[str, str, str]:
    raw = f"{code_t}\n{code_t1}"
    java = matched_signatures(raw, JAVA_SIGNATURES)
    cpp = matched_signatures(raw, CPP_SIGNATURES)
    c = matched_signatures(raw, C_SIGNATURES)

    if java and cpp:
        status = "AMBIGUOUS"
        detected = "AMBIGUOUS"
        reason = "conflicting Java and C++ source signatures: " + "; ".join((java + cpp)[:4])
    elif java:
        status = "NON_C_JAVA"
        detected = "Java"
        reason = "Java-only source signatures: " + "; ".join(java[:4])
    elif cpp:
        status = "NON_C_CPP"
        detected = "C++"
        reason = "C++-only source signatures: " + "; ".join(cpp[:4])
    elif c:
        status = "CONFIRMED_C"
        detected = "C"
        reason = "C source signatures and no Java/C++-specific signature: " + "; ".join(c[:4])
    else:
        status = "AMBIGUOUS"
        detected = "AMBIGUOUS"
        reason = "no decisive source-language signature found in either state"
    return detected, status, reason


def load_item_maps(repo: Path) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    development: dict[str, str] = {}
    for row in read_csv(repo / "data" / "development_50_manifest.csv"):
        development[row["transition_id"]] = row.get("development_item_id") or row.get("item_id") or row.get("case_id") or row.get("generation_case_id") or ""

    calibration: dict[str, str] = {}
    for row in read_csv(repo / "data" / "manifests" / "calibration_20_manifest.csv"):
        calibration[row["transition_id"]] = row.get("calibration_id") or row.get("item_id") or row.get("case_id") or row.get("generation_case_id") or ""

    heldout_path = repo.parent / "RevGround_Supervisor_Aligned_Package_v2" / "evaluation" / "heldout_natural50_manifest.json"
    final_test_path = repo / "data" / "manifests" / "final_test_197_manifest.csv"
    test: dict[str, str] = {}
    if heldout_path.exists() and final_test_path.exists():
        heldout = json.loads(heldout_path.read_text(encoding="utf-8"))
        selected = set(heldout["selected_item_ids"])
        # The frozen TEST manifest calls the generation-case identifier the
        # item ID and separately stores the source transition_id.  QC rows are
        # keyed by the source transition_id, so join on that explicit mapping.
        for row in read_csv(final_test_path):
            generation_case_id = row.get("generation_case_id", "")
            if generation_case_id in selected:
                test[row["transition_id"]] = generation_case_id
    return development, calibration, test


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    repo = args.repo.resolve()
    source = (args.source or (repo.parent / "CodeStream_Stage4_5_Research_Bundle" / "data" / "primary_language_transitions_all_splits.csv")).resolve()
    output = (args.output or (repo / "data" / "qc")).resolve()
    output.mkdir(parents=True, exist_ok=True)

    rows = read_csv(source)
    strict_rows = [
        row for row in rows
        if row.get("split_primary") in {"development", "validation", "test"}
        and row.get("language_t") == "C"
        and row.get("language_t1") == "C"
        and row.get("evidence_ready", "").lower() == "true"
        and row.get("cross_split_code_duplicate", "").lower() == "false"
    ]
    dev_map, calibration_map, test_map = load_item_maps(repo)
    all_records: list[dict[str, str]] = []
    for row in strict_rows:
        detected, status, reason = classify_source(row.get("code_t", ""), row.get("code_t1", ""))
        transition_id = row["transition_id"]
        all_records.append({
            "transition_id": transition_id,
            "declared_language": row.get("language_t", ""),
            "detected_source_language": detected,
            "qc_status": status,
            "reason": reason,
            "partition": row["split_primary"],
            "development_item_id": dev_map.get(transition_id, ""),
            "calibration_id": calibration_map.get(transition_id, ""),
            "test_id": test_map.get(transition_id, ""),
        })

    all_records.sort(key=lambda record: record["transition_id"])
    exclusions = [record for record in all_records if record["qc_status"] != "CONFIRMED_C"]
    write_csv(output / "language_qc_all_strict_c.csv", all_records, OUTPUT_FIELDS)
    write_csv(output / "language_qc_exclusions.csv", exclusions, OUTPUT_FIELDS)

    by_partition: dict[str, Counter[str]] = defaultdict(Counter)
    for record in all_records:
        by_partition[record["partition"]][record["qc_status"]] += 1
    item_records = {record["development_item_id"]: record for record in all_records if record["development_item_id"]}
    calibration_records = {record["calibration_id"]: record for record in all_records if record["calibration_id"]}
    test_records = {record["test_id"]: record for record in all_records if record["test_id"]}
    known = {
        "DEV_010": item_records.get("DEV_010"),
        "DEV_012": item_records.get("DEV_012"),
        "726478f13ad8e011c4a0cfa2": test_records.get("726478f13ad8e011c4a0cfa2"),
        "bda05da230eecfb67fa3a104": test_records.get("bda05da230eecfb67fa3a104"),
    }
    summary = {
        "protocol": "source_language_qc_v1",
        "source_file": str(source),
        "source_sha256": sha256_file(source),
        "classification_rule": "source syntax only from code_t and code_t1; no lifecycle labels, annotator fields, model predictions, or model performance",
        "strict_pool_definition": {
            "split_primary": ["development", "validation", "test"],
            "language_t": "C",
            "language_t1": "C",
            "evidence_ready": True,
            "cross_split_code_duplicate": False,
        },
        "strict_c_pool_n": len(all_records),
        "status_counts": dict(Counter(record["qc_status"] for record in all_records)),
        "partition_status_counts": {partition: dict(counts) for partition, counts in sorted(by_partition.items())},
        "objective_exclusions_n": len(exclusions),
        "known_cases": known,
        "development": {
            "strict_rows": sum(1 for record in all_records if record["partition"] == "development"),
            "mapped_development_50_n": len(item_records),
            "objective_exclusions_in_development_50": [record for record in item_records.values() if record["qc_status"] != "CONFIRMED_C"],
        },
        "calibration": {
            "strict_rows": sum(1 for record in all_records if record["partition"] == "validation"),
            "mapped_calibration_20_n": len(calibration_records),
            "objective_exclusions_in_calibration_20": [record for record in calibration_records.values() if record["qc_status"] != "CONFIRMED_C"],
            "all_20_confirmed_c": len(calibration_records) == 20 and all(record["qc_status"] == "CONFIRMED_C" for record in calibration_records.values()),
        },
        "heldout_test_50": {
            "frozen_sample_n": len(test_map),
            "mapped_test_n": len(test_records),
            "objective_exclusions_in_frozen_test_50": [record for record in test_records.values() if record["qc_status"] != "CONFIRMED_C"],
            "eligible_confirmed_c_n": sum(1 for record in test_records.values() if record["qc_status"] == "CONFIRMED_C"),
        },
    }
    (output / "language_qc_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    hash_paths = [output / name for name in ("language_qc_all_strict_c.csv", "language_qc_summary.json", "language_qc_exclusions.csv")]
    impact_path = output / "language_qc_experiment_impact.json"
    if impact_path.exists():
        hash_paths.append(impact_path)
    with (output / "SHA256SUMS.txt").open("w", encoding="utf-8", newline="") as handle:
        for path in hash_paths:
            handle.write(f"{sha256_file(path)}  {path.name}\n")

    print(json.dumps({
        "strict_c_pool_n": len(all_records),
        "status_counts": dict(Counter(record["qc_status"] for record in all_records)),
        "exclusions_n": len(exclusions),
        "known_cases": known,
        "calibration_20": summary["calibration"],
        "heldout_test_50": summary["heldout_test_50"],
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
