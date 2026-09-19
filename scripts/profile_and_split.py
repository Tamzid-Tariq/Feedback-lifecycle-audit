#!/usr/bin/env python3
"""Reproducible Stage 4-5 profiling and leakage-safe trajectory splitting.

This script never edits the raw CodeStream CSV files. It writes derived,
pseudonymized research artifacts into an output directory.
"""

from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROFILE_VERSION = "1.0.0"
HASH_SALT = "revground-codestream-stage45-v1"
SPLIT_SEED = "revground-problem-split-v1"
REQUIRED_SUBMISSION_COLUMNS = [
    "submission_id",
    "user_id",
    "problem_id",
    "attempt_number",
    "programming_language",
    "source_code",
    "final_verdict",
    "verdict_sequence_trace",
]
REQUIRED_PROBLEM_COLUMNS = [
    "problem_id",
    "problem_description",
    "evaluation_test_cases",
]


def sha256_text(value: Any) -> str:
    return hashlib.sha256(str(value).encode("utf-8", errors="replace")).hexdigest()


def pseudonymize_user(user_id: Any) -> str:
    return sha256_text(f"{HASH_SALT}|{user_id}")[:16]


def normalize_language(value: Any) -> str:
    text = str(value).strip().lower()
    aliases = {
        "c++": "C++",
        "cpp": "C++",
        "gnu c++": "C++",
        "c": "C",
        "java": "Java",
    }
    return aliases.get(text, str(value).strip())


def parse_json_list(value: Any) -> tuple[list[Any] | None, str | None]:
    if pd.isna(value):
        return None, "missing"
    try:
        parsed = json.loads(str(value))
    except Exception as exc:  # noqa: BLE001 - error is logged as a data-quality flag
        return None, f"malformed: {type(exc).__name__}"
    if not isinstance(parsed, list):
        return None, f"expected list, found {type(parsed).__name__}"
    return parsed, None


def normalize_code(code: Any) -> str:
    return re.sub(r"\s+", "", str(code))


def normalize_problem_text(text: Any) -> str:
    tokens = re.findall(r"[a-z0-9]+", str(text).lower())
    return " ".join(tokens)


def token_jaccard(a: str, b: str) -> float:
    sa, sb = set(a.split()), set(b.split())
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def line_diff_counts(old: str, new: str) -> tuple[int, int, int]:
    matcher = difflib.SequenceMatcher(a=old.splitlines(), b=new.splitlines(), autojunk=False)
    added = deleted = replaced = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "insert":
            added += j2 - j1
        elif tag == "delete":
            deleted += i2 - i1
        elif tag == "replace":
            deleted += i2 - i1
            added += j2 - j1
            replaced += max(i2 - i1, j2 - j1)
    return added, deleted, replaced


def stable_split(items: list[str], dev=0.60, val=0.20, test=0.20) -> dict[str, str]:
    assert math.isclose(dev + val + test, 1.0)
    ranked = sorted(items, key=lambda x: sha256_text(f"{SPLIT_SEED}|{x}"))
    n = len(ranked)
    if n == 0:
        return {}
    n_test = max(1, round(n * test)) if n >= 3 else 0
    n_val = max(1, round(n * val)) if n >= 3 else 0
    if n_test + n_val >= n:
        n_test = 1 if n >= 2 else 0
        n_val = 1 if n >= 3 else 0
    mapping: dict[str, str] = {}
    for i, item in enumerate(ranked):
        if i < n_test:
            mapping[item] = "test"
        elif i < n_test + n_val:
            mapping[item] = "validation"
        else:
            mapping[item] = "development"
    return mapping


def stable_weighted_split(weights: dict[str, int], dev=0.60, val=0.20, test=0.20) -> dict[str, str]:
    """Assign atomic groups while approximately balancing transition counts."""
    ratios = {"development": dev, "validation": val, "test": test}
    total = sum(weights.values())
    targets = {name: total * ratio for name, ratio in ratios.items()}
    assigned = {name: 0 for name in ratios}
    mapping: dict[str, str] = {}
    ordered = sorted(weights, key=lambda x: (-weights[x], sha256_text(f"{SPLIT_SEED}|{x}")))
    split_order = ["development", "validation", "test"]
    for group_id in ordered:
        chosen = min(
            split_order,
            key=lambda name: (
                assigned[name] / targets[name] if targets[name] else float("inf"),
                split_order.index(name),
            ),
        )
        mapping[group_id] = chosen
        assigned[chosen] += weights[group_id]
    return mapping


def build_leakage_groups(problem_ids: list[str], near_pairs: list[dict[str, Any]]) -> tuple[dict[str, str], dict[str, int]]:
    """Join exact/high-similarity problem descriptions into atomic split groups."""
    parent = {p: p for p in problem_ids}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    for pair in near_pairs:
        a, b = str(pair["problem_id_a"]), str(pair["problem_id_b"])
        if a in parent and b in parent:
            union(a, b)

    components: dict[str, list[str]] = {}
    for problem_id in problem_ids:
        components.setdefault(find(problem_id), []).append(problem_id)
    mapping: dict[str, str] = {}
    sizes: dict[str, int] = {}
    for members in components.values():
        group_id = "lg_" + sha256_text("|".join(sorted(members)))[:12]
        sizes[group_id] = len(members)
        for problem_id in members:
            mapping[problem_id] = group_id
    return mapping, sizes


def write_csv(path: Path, rows: list[dict[str, Any]] | pd.DataFrame, columns=None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
    if columns is not None:
        frame = frame.reindex(columns=columns)
    frame.to_csv(path, index=False, quoting=csv.QUOTE_MINIMAL)


def ensure_columns(frame: pd.DataFrame, required: list[str], label: str) -> None:
    missing = [c for c in required if c not in frame.columns]
    if missing:
        raise ValueError(f"{label} is missing required columns: {missing}")


def make_flow_diagram(summary: dict[str, Any], path: Path) -> None:
    stages = [
        ("All submissions", summary["submissions_rows"]),
        ("Valid ordered trajectories", summary["valid_trajectories"]),
        ("Consecutive transitions", summary["consecutive_transitions_all"]),
        (f"Evidence-ready {summary['primary_language']} edits", summary["primary_eligible_transitions"]),
        ("Pilot sampling pool", summary["primary_eligible_transitions"]),
        ("Annotated benchmark", "Future stage"),
    ]
    fig, ax = plt.subplots(figsize=(13, 3.6))
    ax.axis("off")
    xs = np.linspace(0.08, 0.92, len(stages))
    for i, ((label, count), x) in enumerate(zip(stages, xs)):
        color = "#123B5D" if i < 4 else "#2E74B5" if i == 4 else "#7A8793"
        text = f"{label}\n{count:,}" if isinstance(count, int) else f"{label}\n{count}"
        ax.text(
            x,
            0.5,
            text,
            ha="center",
            va="center",
            fontsize=10.5,
            color="white",
            bbox=dict(boxstyle="round,pad=0.55", facecolor=color, edgecolor=color),
        )
        if i < len(stages) - 1:
            ax.annotate(
                "",
                xy=(xs[i + 1] - 0.075, 0.5),
                xytext=(x + 0.075, 0.5),
                arrowprops=dict(arrowstyle="->", color="#5A6872", lw=1.8),
            )
    fig.suptitle("CodeStream Stage 4-5 Data Flow", fontsize=15, fontweight="bold", color="#123B5D")
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def make_attempt_distribution(trajectory_index: pd.DataFrame, path: Path) -> None:
    counts = trajectory_index["submission_count"].value_counts().sort_index()
    capped = Counter()
    for attempts, trajectories in counts.items():
        label = str(int(attempts)) if attempts <= 10 else "11+"
        capped[label] += int(trajectories)
    labels = [str(i) for i in range(1, 11)] + ["11+"]
    values = [capped.get(label, 0) for label in labels]
    fig, ax = plt.subplots(figsize=(10, 5.2))
    bars = ax.bar(labels, values, color="#2E74B5", edgecolor="#123B5D", linewidth=0.6)
    ax.set_title("Student-Problem Trajectories by Number of Attempts", fontsize=14, fontweight="bold", color="#123B5D")
    ax.set_xlabel("Submissions in trajectory")
    ax.set_ylabel("Number of trajectories")
    ax.grid(axis="y", color="#D8E0E8", linewidth=0.7)
    ax.set_axisbelow(True)
    for bar, value in zip(bars, values):
        if value:
            ax.text(bar.get_x() + bar.get_width() / 2, value, f"{value:,}", ha="center", va="bottom", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def make_language_chart(language_profile: pd.DataFrame, path: Path) -> None:
    frame = language_profile.sort_values("evidence_ready_edited_transitions", ascending=True)
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    bars = ax.barh(frame["language"], frame["evidence_ready_edited_transitions"], color="#2E74B5")
    ax.set_title("Evidence-Ready Edited Transitions by Language", fontsize=14, fontweight="bold", color="#123B5D")
    ax.set_xlabel("Consecutive transitions")
    ax.grid(axis="x", color="#D8E0E8", linewidth=0.7)
    ax.set_axisbelow(True)
    for bar, value in zip(bars, frame["evidence_ready_edited_transitions"]):
        ax.text(value, bar.get_y() + bar.get_height() / 2, f" {int(value):,}", va="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--submissions", required=True, type=Path)
    parser.add_argument("--problems", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    out = args.output
    for folder in ["analysis", "tables", "data", "figures", "checksums"]:
        (out / folder).mkdir(parents=True, exist_ok=True)

    submissions = pd.read_csv(args.submissions, dtype={"submission_id": "string", "user_id": "string", "problem_id": "string"})
    problems = pd.read_csv(args.problems, dtype={"problem_id": "string"})
    ensure_columns(submissions, REQUIRED_SUBMISSION_COLUMNS, "Submission Data")
    ensure_columns(problems, REQUIRED_PROBLEM_COLUMNS, "Problem Data")

    submissions["_raw_row_number"] = np.arange(2, len(submissions) + 2)
    submissions["attempt_number_numeric"] = pd.to_numeric(submissions["attempt_number"], errors="coerce")
    submissions["language_normalized"] = submissions["programming_language"].map(normalize_language)
    submissions["participant_id_hash"] = submissions["user_id"].map(pseudonymize_user)
    submissions["trajectory_id"] = [
        sha256_text(f"{u}|{p}")[:20] for u, p in zip(submissions["participant_id_hash"], submissions["problem_id"])
    ]

    problem_ids = set(problems["problem_id"].dropna().astype(str))
    required_missing = submissions[REQUIRED_SUBMISSION_COLUMNS].isna().any(axis=1)
    invalid_attempt = (
        submissions["attempt_number_numeric"].isna()
        | (submissions["attempt_number_numeric"] <= 0)
        | (submissions["attempt_number_numeric"] % 1 != 0)
    )
    submissions["attempt_valid"] = ~invalid_attempt
    submissions["problem_linked"] = submissions["problem_id"].astype(str).isin(problem_ids)
    submissions["duplicate_submission_id"] = submissions.duplicated("submission_id", keep=False)
    submissions["duplicate_attempt_key"] = submissions.duplicated(["user_id", "problem_id", "attempt_number"], keep=False)
    submissions["exact_duplicate_row"] = submissions[REQUIRED_SUBMISSION_COLUMNS].duplicated(keep=False)

    trace_parsed, trace_errors = [], []
    for value in submissions["verdict_sequence_trace"]:
        parsed, err = parse_json_list(value)
        trace_parsed.append(parsed)
        trace_errors.append(err)
    submissions["trace_parsed"] = trace_parsed
    submissions["trace_parse_error"] = trace_errors
    submissions["trace_valid"] = submissions["trace_parse_error"].isna()
    submissions["trace_length"] = submissions["trace_parsed"].map(lambda x: len(x) if isinstance(x, list) else np.nan)
    submissions["trace_last_verdict"] = submissions["trace_parsed"].map(lambda x: x[-1] if isinstance(x, list) and x else None)
    submissions["trace_last_matches_final"] = submissions["trace_last_verdict"] == submissions["final_verdict"]
    submissions["code_sha256"] = submissions["source_code"].map(sha256_text)
    submissions["code_whitespace_normalized_sha256"] = submissions["source_code"].map(lambda x: sha256_text(normalize_code(x)))

    problem_test_parsed, problem_test_errors = [], []
    for value in problems["evaluation_test_cases"]:
        parsed, err = parse_json_list(value)
        problem_test_parsed.append(parsed)
        problem_test_errors.append(err)
    problems["test_cases_parsed"] = problem_test_parsed
    problems["test_case_parse_error"] = problem_test_errors
    problems["test_case_items_valid"] = problems["test_cases_parsed"].map(
        lambda cases: bool(
            isinstance(cases, list)
            and all(isinstance(item, dict) and {"test_case_no", "input", "output"}.issubset(item) for item in cases)
        )
    )
    problems["test_cases_valid"] = problems["test_case_parse_error"].isna() & problems["test_case_items_valid"]
    problems["test_case_count"] = problems["test_cases_parsed"].map(lambda x: len(x) if isinstance(x, list) else np.nan)
    problems["test_case_key_pattern"] = problems["test_cases_parsed"].map(
        lambda cases: ";".join(sorted({"|".join(sorted(item.keys())) for item in cases if isinstance(item, dict)}))
        if isinstance(cases, list)
        else ""
    )
    problems["has_reference_solution_field"] = False
    problems["normalized_description"] = problems["problem_description"].map(normalize_problem_text)
    problems["description_sha256"] = problems["normalized_description"].map(sha256_text)

    near_problem_pairs = []
    problem_records = problems[["problem_id", "normalized_description", "description_sha256"]].to_dict("records")
    for i, a in enumerate(problem_records):
        for b in problem_records[i + 1 :]:
            exact = a["description_sha256"] == b["description_sha256"]
            jaccard = token_jaccard(a["normalized_description"], b["normalized_description"])
            if exact or jaccard >= 0.90:
                near_problem_pairs.append(
                    {
                        "problem_id_a": a["problem_id"],
                        "problem_id_b": b["problem_id"],
                        "exact_normalized_description": exact,
                        "token_jaccard": round(jaccard, 4),
                        "review_required": True,
                    }
                )
    leakage_group_map, leakage_group_sizes = build_leakage_groups(
        sorted(problems["problem_id"].astype(str).tolist()), near_problem_pairs
    )
    problems["leakage_group_id"] = problems["problem_id"].map(leakage_group_map)
    problems["leakage_group_size"] = problems["leakage_group_id"].map(leakage_group_sizes)

    test_count_map = problems.set_index("problem_id")["test_case_count"].to_dict()
    test_valid_map = problems.set_index("problem_id")["test_cases_valid"].to_dict()
    submissions["problem_test_case_count"] = submissions["problem_id"].map(test_count_map)
    submissions["problem_tests_valid"] = submissions["problem_id"].map(test_valid_map).fillna(False)
    submissions["trace_length_matches_test_count"] = submissions["trace_length"] == submissions["problem_test_case_count"]
    submissions["row_valid_for_ordering"] = (
        ~required_missing
        & submissions["attempt_valid"]
        & submissions["problem_linked"]
        & ~submissions["duplicate_submission_id"]
        & ~submissions["duplicate_attempt_key"]
    )

    ordered = submissions[submissions["row_valid_for_ordering"]].copy()
    ordered["attempt_number_numeric"] = ordered["attempt_number_numeric"].astype(int)
    ordered = ordered.sort_values(["user_id", "problem_id", "attempt_number_numeric", "submission_id"], kind="stable")

    trajectory_rows: list[dict[str, Any]] = []
    transition_rows: list[dict[str, Any]] = []
    for (user_id, problem_id), group in ordered.groupby(["user_id", "problem_id"], sort=False):
        group = group.sort_values("attempt_number_numeric", kind="stable")
        attempts = group["attempt_number_numeric"].astype(int).tolist()
        languages = group["language_normalized"].astype(str).tolist()
        unique_languages = sorted(set(languages))
        expected = list(range(min(attempts), max(attempts) + 1)) if attempts else []
        gaps = sorted(set(expected) - set(attempts))
        trajectory_id = str(group.iloc[0]["trajectory_id"])
        trajectory_rows.append(
            {
                "trajectory_id": trajectory_id,
                "participant_id_hash": pseudonymize_user(user_id),
                "problem_id": problem_id,
                "submission_count": len(group),
                "min_attempt": min(attempts) if attempts else None,
                "max_attempt": max(attempts) if attempts else None,
                "starts_at_one": bool(attempts and min(attempts) == 1),
                "attempt_numbers_contiguous": not gaps,
                "missing_attempt_numbers": ";".join(map(str, gaps)),
                "language_count": len(unique_languages),
                "languages": ";".join(unique_languages),
                "mixed_language": len(unique_languages) > 1,
                "accepted_ever": bool((group["final_verdict"] == "Accepted").any()),
                "final_attempt_verdict": group.iloc[-1]["final_verdict"],
            }
        )
        records = list(group.to_dict("records"))
        for old, new in zip(records, records[1:]):
            attempt_t = int(old["attempt_number_numeric"])
            attempt_t1 = int(new["attempt_number_numeric"])
            consecutive = attempt_t1 == attempt_t + 1
            same_language = old["language_normalized"] == new["language_normalized"]
            old_code, new_code = str(old["source_code"]), str(new["source_code"])
            code_exact_same = old_code == new_code
            code_ws_same = normalize_code(old_code) == normalize_code(new_code)
            added, deleted, replaced = line_diff_counts(old_code, new_code)
            evidence_ready = bool(
                consecutive
                and old["trace_valid"]
                and new["trace_valid"]
                and old["problem_tests_valid"]
                and new["problem_tests_valid"]
            )
            raw_id = f"{trajectory_id}|{old['submission_id']}|{new['submission_id']}"
            transition_rows.append(
                {
                    "transition_id": sha256_text(raw_id)[:24],
                    "trajectory_id": trajectory_id,
                    "participant_id_hash": pseudonymize_user(user_id),
                    "problem_id": problem_id,
                    "submission_id_t": old["submission_id"],
                    "submission_id_t1": new["submission_id"],
                    "raw_row_t": int(old["_raw_row_number"]),
                    "raw_row_t1": int(new["_raw_row_number"]),
                    "attempt_t": attempt_t,
                    "attempt_t1": attempt_t1,
                    "is_consecutive": consecutive,
                    "language_t": old["language_normalized"],
                    "language_t1": new["language_normalized"],
                    "same_language": same_language,
                    "code_t": old_code,
                    "code_t1": new_code,
                    "code_t_sha256": old["code_sha256"],
                    "code_t1_sha256": new["code_sha256"],
                    "code_t_whitespace_sha256": old["code_whitespace_normalized_sha256"],
                    "code_t1_whitespace_sha256": new["code_whitespace_normalized_sha256"],
                    "code_exact_same": code_exact_same,
                    "code_whitespace_normalized_same": code_ws_same,
                    "lines_added": added,
                    "lines_deleted": deleted,
                    "lines_replaced": replaced,
                    "verdict_t": old["final_verdict"],
                    "verdict_t1": new["final_verdict"],
                    "verdict_changed": old["final_verdict"] != new["final_verdict"],
                    "trace_t": old["verdict_sequence_trace"],
                    "trace_t1": new["verdict_sequence_trace"],
                    "trace_length_t": old["trace_length"],
                    "trace_length_t1": new["trace_length"],
                    "problem_test_case_count": old["problem_test_case_count"],
                    "trace_t_matches_test_count": old["trace_length_matches_test_count"],
                    "trace_t1_matches_test_count": new["trace_length_matches_test_count"],
                    "evidence_ready": evidence_ready,
                    "pair_sha256": sha256_text(raw_id + "|" + old["code_sha256"] + "|" + new["code_sha256"]),
                    "ast_diff_status": "not_computed_language_parser_not_bundled",
                }
            )

    trajectory_index = pd.DataFrame(trajectory_rows)
    transitions = pd.DataFrame(transition_rows)
    consecutive = transitions[transitions["is_consecutive"]].copy()

    language_rows: list[dict[str, Any]] = []
    all_languages = sorted(set(submissions["language_normalized"].dropna().astype(str)))
    for language in all_languages:
        sub_l = submissions[submissions["language_normalized"] == language]
        trans_l = consecutive[(consecutive["language_t"] == language) & (consecutive["language_t1"] == language)]
        eligible_l = trans_l[trans_l["evidence_ready"] & ~trans_l["code_exact_same"]]
        language_rows.append(
            {
                "language": language,
                "submissions": len(sub_l),
                "participants": sub_l["participant_id_hash"].nunique(),
                "problems": sub_l["problem_id"].nunique(),
                "same_language_consecutive_transitions": len(trans_l),
                "evidence_ready_transitions": int(trans_l["evidence_ready"].sum()),
                "evidence_ready_edited_transitions": len(eligible_l),
                "eligible_trajectories": eligible_l["trajectory_id"].nunique(),
                "eligible_problems": eligible_l["problem_id"].nunique(),
                "eligible_participants": eligible_l["participant_id_hash"].nunique(),
            }
        )
    language_profile = pd.DataFrame(language_rows)
    language_profile["selection_score"] = (
        language_profile["evidence_ready_edited_transitions"]
        * np.sqrt(language_profile["eligible_problems"] * language_profile["eligible_participants"])
    )
    language_profile = language_profile.sort_values(
        ["selection_score", "eligible_problems", "eligible_participants"], ascending=False
    )
    if language_profile.empty:
        raise RuntimeError("No languages found in Submission Data")
    primary_language = str(language_profile.iloc[0]["language"])

    primary = consecutive[
        (consecutive["language_t"] == primary_language)
        & (consecutive["language_t1"] == primary_language)
        & consecutive["evidence_ready"]
        & ~consecutive["code_exact_same"]
    ].copy()

    primary_problem_ids = sorted(primary["problem_id"].unique().tolist())
    primary["leakage_group_id"] = primary["problem_id"].map(leakage_group_map)
    primary_group_weights = primary.groupby("leakage_group_id").size().astype(int).to_dict()
    leakage_group_split = stable_weighted_split(primary_group_weights)
    problem_split = {p: leakage_group_split[leakage_group_map[p]] for p in primary_problem_ids}
    primary["split_primary"] = primary["problem_id"].map(problem_split)
    participant_split = stable_split(sorted(primary["participant_id_hash"].unique().tolist()))
    primary["split_participant_secondary"] = primary["participant_id_hash"].map(participant_split)

    cross_split_code_audit_rows: list[dict[str, Any]] = []
    duplicate_hashes: set[str] = set()
    for match_type, hash_columns in [
        ("exact", ["code_t_sha256", "code_t1_sha256"]),
        ("whitespace_normalized", ["code_t_whitespace_sha256", "code_t1_whitespace_sha256"]),
    ]:
        exploded_parts = []
        for column in hash_columns:
            part = primary[["transition_id", "problem_id", "split_primary", column]].rename(columns={column: "code_hash"})
            exploded_parts.append(part)
        exploded = pd.concat(exploded_parts, ignore_index=True).drop_duplicates()
        for code_hash, group in exploded.groupby("code_hash"):
            splits = sorted(group["split_primary"].unique().tolist())
            if len(splits) > 1:
                duplicate_hashes.add(str(code_hash))
                cross_split_code_audit_rows.append(
                    {
                        "match_type": match_type,
                        "code_hash": code_hash,
                        "splits": ";".join(splits),
                        "split_count": len(splits),
                        "problem_count": group["problem_id"].nunique(),
                        "transition_count": group["transition_id"].nunique(),
                        "action": "Exclude touched transitions from strict evaluation partitions",
                    }
                )
    primary["cross_split_code_duplicate"] = primary[
        ["code_t_sha256", "code_t1_sha256", "code_t_whitespace_sha256", "code_t1_whitespace_sha256"]
    ].isin(duplicate_hashes).any(axis=1)
    strict_primary = primary[~primary["cross_split_code_duplicate"]].copy()

    all_problem_split_rows = []
    primary_counts = primary.groupby("problem_id").size().to_dict()
    for problem_id in sorted(problems["problem_id"].astype(str)):
        all_problem_split_rows.append(
            {
                "problem_id": problem_id,
                "primary_language": primary_language,
                "eligible_transition_count": int(primary_counts.get(problem_id, 0)),
                "split_primary": problem_split.get(problem_id, "ineligible"),
                "leakage_group_id": leakage_group_map[problem_id],
                "leakage_group_size": leakage_group_sizes[leakage_group_map[problem_id]],
                "manual_similarity_review_required": leakage_group_sizes[leakage_group_map[problem_id]] > 1,
                "split_method": "deterministic weighted assignment by near-duplicate-aware problem group",
                "split_seed_id": SPLIT_SEED,
            }
        )
    problem_split_assignments = pd.DataFrame(all_problem_split_rows)

    near_pair_split_violations = 0
    for pair in near_problem_pairs:
        a, b = str(pair["problem_id_a"]), str(pair["problem_id_b"])
        if a in problem_split and b in problem_split and problem_split[a] != problem_split[b]:
            near_pair_split_violations += 1

    strict_hash_overlap_count = 0
    for hash_columns in [
        ["code_t_sha256", "code_t1_sha256"],
        ["code_t_whitespace_sha256", "code_t1_whitespace_sha256"],
    ]:
        exploded = pd.concat(
            [strict_primary[["split_primary", column]].rename(columns={column: "code_hash"}) for column in hash_columns],
            ignore_index=True,
        ).drop_duplicates()
        strict_hash_overlap_count += int((exploded.groupby("code_hash")["split_primary"].nunique() > 1).sum())

    validation_checks = {
        "all_required_submission_columns_present": all(c in submissions.columns for c in REQUIRED_SUBMISSION_COLUMNS),
        "all_required_problem_columns_present": all(c in problems.columns for c in REQUIRED_PROBLEM_COLUMNS),
        "problem_ids_unique_in_problem_data": bool(problems["problem_id"].is_unique),
        "submission_ids_unique": bool(submissions["submission_id"].is_unique),
        "all_primary_pairs_are_consecutive": bool(strict_primary["is_consecutive"].all()),
        "all_primary_pairs_are_same_language": bool(strict_primary["same_language"].all()),
        "all_primary_pairs_have_evidence": bool(strict_primary["evidence_ready"].all()),
        "one_primary_split_per_problem": bool(strict_primary.groupby("problem_id")["split_primary"].nunique().max() == 1),
        "one_primary_split_per_trajectory": bool(strict_primary.groupby("trajectory_id")["split_primary"].nunique().max() == 1),
        "one_secondary_split_per_participant": bool(primary.groupby("participant_id_hash")["split_participant_secondary"].nunique().max() == 1),
        "no_near_duplicate_problem_pair_crosses_primary_splits": near_pair_split_violations == 0,
        "no_exact_or_whitespace_code_hash_crosses_strict_splits": strict_hash_overlap_count == 0,
        "all_three_primary_splits_nonempty": set(strict_primary["split_primary"].unique()) == {"development", "validation", "test"},
    }

    trajectory_length_distribution = (
        trajectory_index["submission_count"]
        .value_counts()
        .sort_index()
        .rename_axis("attempts_in_trajectory")
        .reset_index(name="trajectory_count")
    )
    threshold_rows = []
    for threshold in [2, 3, 4]:
        subset = trajectory_index[trajectory_index["submission_count"] >= threshold]
        threshold_rows.append(
            {
                "minimum_attempts": threshold,
                "trajectory_count": len(subset),
                "participants": subset["participant_id_hash"].nunique(),
                "problems": subset["problem_id"].nunique(),
            }
        )

    verdict_distribution = (
        submissions["final_verdict"]
        .fillna("<MISSING>")
        .value_counts(dropna=False)
        .rename_axis("final_verdict")
        .reset_index(name="submission_count")
    )
    verdict_distribution["percentage"] = verdict_distribution["submission_count"] / len(submissions)

    exact_hash_problem_counts = submissions.groupby("code_sha256")["problem_id"].nunique()
    ws_hash_problem_counts = submissions.groupby("code_whitespace_normalized_sha256")["problem_id"].nunique()
    exact_code_cross_problem_rows = int(submissions["code_sha256"].map(exact_hash_problem_counts).gt(1).sum())
    ws_code_cross_problem_rows = int(submissions["code_whitespace_normalized_sha256"].map(ws_hash_problem_counts).gt(1).sum())

    exclusions = [
        {"scope": "submission", "rule_id": "S01", "count": int(required_missing.sum()), "status": "exclude", "reason": "Missing one or more required submission fields"},
        {"scope": "submission", "rule_id": "S02", "count": int(invalid_attempt.sum()), "status": "exclude", "reason": "Attempt number is missing, non-integer or non-positive"},
        {"scope": "submission", "rule_id": "S03", "count": int((~submissions["problem_linked"]).sum()), "status": "exclude", "reason": "Problem ID does not link to Problem Data"},
        {"scope": "submission", "rule_id": "S04", "count": int(submissions["duplicate_submission_id"].sum()), "status": "exclude", "reason": "Duplicate submission identifier"},
        {"scope": "submission", "rule_id": "S05", "count": int(submissions["duplicate_attempt_key"].sum()), "status": "exclude", "reason": "Duplicate user-problem-attempt key"},
        {"scope": "submission", "rule_id": "S06", "count": int((~submissions["trace_valid"]).sum()), "status": "exclude from evidence-grounded set", "reason": "Verdict sequence trace missing or malformed"},
        {"scope": "transition", "rule_id": "T01", "count": int((~transitions["is_consecutive"]).sum()), "status": "exclude", "reason": "Adjacent stored rows skip an attempt number"},
        {"scope": "transition", "rule_id": "T02", "count": int((consecutive["language_t"] != consecutive["language_t1"]).sum()), "status": "exclude from single-language primary set", "reason": "Programming language changes between consecutive attempts"},
        {"scope": "transition", "rule_id": "T03", "count": int((~consecutive["evidence_ready"]).sum()), "status": "exclude from evidence-grounded set", "reason": "One or both traces/tests are not parseable"},
        {"scope": "transition", "rule_id": "T04", "count": int(consecutive["code_exact_same"].sum()), "status": "flag; exclude from edited primary set", "reason": "Source code is exactly unchanged across attempts"},
        {"scope": "transition", "rule_id": "T05", "count": int((consecutive["code_whitespace_normalized_same"] & ~consecutive["code_exact_same"]).sum()), "status": "flag", "reason": "Only whitespace changed under a simple normalization"},
        {"scope": "transition", "rule_id": "T06", "count": int(primary["cross_split_code_duplicate"].sum()), "status": "exclude from strict evaluation partitions", "reason": "Exact or whitespace-normalized code occurs across problem-disjoint splits"},
    ]

    missing_rows = []
    for name, frame in [("Submission Data", submissions[REQUIRED_SUBMISSION_COLUMNS]), ("Problem Data", problems[REQUIRED_PROBLEM_COLUMNS])]:
        for column in frame.columns:
            missing_rows.append(
                {
                    "file": name,
                    "field": column,
                    "missing_count": int(frame[column].isna().sum()),
                    "missing_percentage": float(frame[column].isna().mean()),
                }
            )

    summary = {
        "profile_version": PROFILE_VERSION,
        "source_submission_file": args.submissions.name,
        "source_problem_file": args.problems.name,
        "submission_file_sha256": hashlib.sha256(args.submissions.read_bytes()).hexdigest(),
        "problem_file_sha256": hashlib.sha256(args.problems.read_bytes()).hexdigest(),
        "submissions_rows": len(submissions),
        "problem_rows": len(problems),
        "unique_submission_ids": int(submissions["submission_id"].nunique()),
        "unique_participants": int(submissions["user_id"].nunique()),
        "unique_problems_in_submissions": int(submissions["problem_id"].nunique()),
        "languages": sorted(submissions["language_normalized"].dropna().unique().tolist()),
        "all_trajectories": int(submissions.groupby(["user_id", "problem_id"]).ngroups),
        "valid_trajectories": len(trajectory_index),
        "trajectories_at_least_2": int((trajectory_index["submission_count"] >= 2).sum()),
        "trajectories_at_least_3": int((trajectory_index["submission_count"] >= 3).sum()),
        "trajectories_at_least_4": int((trajectory_index["submission_count"] >= 4).sum()),
        "trajectories_with_attempt_gaps": int((~trajectory_index["attempt_numbers_contiguous"]).sum()),
        "trajectories_not_starting_at_one": int((~trajectory_index["starts_at_one"]).sum()),
        "mixed_language_trajectories": int(trajectory_index["mixed_language"].sum()),
        "adjacent_pairs_all": len(transitions),
        "consecutive_transitions_all": len(consecutive),
        "evidence_ready_consecutive_transitions": int(consecutive["evidence_ready"].sum()),
        "primary_language": primary_language,
        "primary_language_selection_rule": "maximize edited transitions multiplied by sqrt(eligible problems x eligible participants)",
        "primary_language_selection_reason": "Balances sample size with problem and participant diversity for problem-disjoint generalization",
        "primary_eligible_transitions_before_cross_split_dedup": len(primary),
        "primary_cross_split_code_duplicate_transitions_removed": int(primary["cross_split_code_duplicate"].sum()),
        "primary_eligible_transitions": len(strict_primary),
        "primary_eligible_trajectories": int(strict_primary["trajectory_id"].nunique()),
        "primary_eligible_participants": int(strict_primary["participant_id_hash"].nunique()),
        "primary_eligible_problems": int(strict_primary["problem_id"].nunique()),
        "split_counts": {k: int(v) for k, v in strict_primary["split_primary"].value_counts().to_dict().items()},
        "split_problem_counts": {k: int(v) for k, v in problem_split_assignments[problem_split_assignments["split_primary"] != "ineligible"]["split_primary"].value_counts().to_dict().items()},
        "missing_required_submission_rows": int(required_missing.sum()),
        "exact_duplicate_submission_rows": int(submissions[REQUIRED_SUBMISSION_COLUMNS].duplicated().sum()),
        "duplicate_submission_id_rows": int(submissions["duplicate_submission_id"].sum()),
        "duplicate_attempt_key_rows": int(submissions["duplicate_attempt_key"].sum()),
        "invalid_attempt_rows": int(invalid_attempt.sum()),
        "unlinked_problem_rows": int((~submissions["problem_linked"]).sum()),
        "malformed_trace_rows": int((~submissions["trace_valid"]).sum()),
        "malformed_problem_test_rows": int((~problems["test_cases_valid"]).sum()),
        "trace_length_matches_test_count_rows": int(submissions["trace_length_matches_test_count"].sum()),
        "trace_last_matches_final_rows": int(submissions["trace_last_matches_final"].sum()),
        "exact_code_duplicate_rows": int(submissions.duplicated("code_sha256", keep=False).sum()),
        "whitespace_normalized_code_duplicate_rows": int(submissions.duplicated("code_whitespace_normalized_sha256", keep=False).sum()),
        "exact_code_cross_problem_rows": exact_code_cross_problem_rows,
        "whitespace_normalized_code_cross_problem_rows": ws_code_cross_problem_rows,
        "near_duplicate_problem_pairs_review": len(near_problem_pairs),
        "near_duplicate_problem_split_violations": near_pair_split_violations,
        "official_tests_available": bool(problems["test_cases_valid"].all()),
        "reference_solutions_available": False,
        "gate_stage4": "PASS" if len(strict_primary) >= 100 and strict_primary["problem_id"].nunique() >= 10 else "REVIEW",
        "gate_stage5": "PASS" if all(validation_checks.values()) else "FAIL",
    }

    file_profile = pd.DataFrame(
        [
            {
                "file": args.submissions.name,
                "rows": len(submissions),
                "columns": len(REQUIRED_SUBMISSION_COLUMNS),
                "unique_primary_key": submissions["submission_id"].nunique(),
                "sha256": summary["submission_file_sha256"],
            },
            {
                "file": args.problems.name,
                "rows": len(problems),
                "columns": len(REQUIRED_PROBLEM_COLUMNS),
                "unique_primary_key": problems["problem_id"].nunique(),
                "sha256": summary["problem_file_sha256"],
            },
        ]
    )

    data_dictionary = pd.DataFrame(
        [
            ("transition_id", "Derived transition", "Stable SHA-256-based pair key", "Audit and joins"),
            ("trajectory_id", "Derived trajectory", "Hashed participant + problem group", "Grouping and clustered analysis"),
            ("participant_id_hash", "Derived trajectory", "Non-identifying learner key", "Student-disjoint checks"),
            ("problem_id", "Source", "Programming task identifier", "Problem-disjoint split"),
            ("attempt_t", "Source", "Earlier attempt number", "Temporal order"),
            ("code_t / verdict_t", "Source", "Earlier program and judge evidence", "Generate and audit old hint"),
            ("attempt_t1", "Source", "Next attempt number; must equal attempt_t + 1", "No skipped revisions"),
            ("code_t1 / verdict_t1", "Source", "Revised program and judge evidence", "Audit old hint"),
            ("language_t / language_t1", "Source", "Normalized C, C++ or Java", "Execution environment and same-language gate"),
            ("trace_t / trace_t1", "Source", "Ordered test-case verdict traces", "Evidence change"),
            ("problem_test_case_count", "Derived", "Number of serialized official evaluation cases", "Trace completeness check"),
            ("lines_added/deleted/replaced", "Derived", "Line-level diff counts", "Revision magnitude"),
            ("code_exact_same", "Derived", "Whether source code is byte-for-byte unchanged", "Flag non-edits"),
            ("evidence_ready", "Derived", "Consecutive pair with parseable traces and tests", "Evidence-grounded benchmark eligibility"),
            ("split_primary", "Derived", "Development, validation or locked test by whole problem", "Prevent problem leakage"),
            ("split_participant_secondary", "Derived", "Secondary split by complete participant", "Student-disjoint sensitivity analysis"),
            ("pair_sha256", "Derived", "Checksum of IDs and code hashes", "Tamper and regeneration check"),
            ("ast_diff_status", "Derived", "AST parsing status", "Documents that only line diff is currently available"),
        ],
        columns=["field", "origin", "meaning", "why_needed"],
    )

    problem_quality = problems[
        ["problem_id", "test_cases_valid", "test_case_items_valid", "test_case_count", "test_case_key_pattern", "test_case_parse_error", "has_reference_solution_field", "description_sha256", "leakage_group_id", "leakage_group_size"]
    ].copy()
    problem_quality["submission_count"] = problem_quality["problem_id"].map(submissions["problem_id"].value_counts()).fillna(0).astype(int)

    write_csv(out / "tables" / "file_profile.csv", file_profile)
    write_csv(out / "tables" / "missingness_by_field.csv", pd.DataFrame(missing_rows))
    write_csv(out / "tables" / "data_dictionary.csv", data_dictionary)
    write_csv(out / "tables" / "language_profile.csv", language_profile)
    write_csv(out / "tables" / "trajectory_length_distribution.csv", trajectory_length_distribution)
    write_csv(out / "tables" / "trajectory_threshold_counts.csv", pd.DataFrame(threshold_rows))
    write_csv(out / "tables" / "verdict_distribution.csv", verdict_distribution)
    write_csv(out / "tables" / "problem_testcase_quality.csv", problem_quality)
    write_csv(out / "tables" / "exclusions_and_flags.csv", pd.DataFrame(exclusions))
    write_csv(out / "tables" / "near_duplicate_problem_candidates.csv", pd.DataFrame(near_problem_pairs, columns=["problem_id_a", "problem_id_b", "exact_normalized_description", "token_jaccard", "review_required"]))
    write_csv(out / "tables" / "cross_split_code_duplicate_audit.csv", pd.DataFrame(cross_split_code_audit_rows, columns=["match_type", "code_hash", "splits", "split_count", "problem_count", "transition_count", "action"]))
    write_csv(out / "data" / "trajectory_index.csv", trajectory_index)
    write_csv(out / "data" / "consecutive_transitions_all.csv", consecutive)
    write_csv(out / "data" / "problem_split_assignments.csv", problem_split_assignments)
    write_csv(out / "data" / "primary_language_transitions_all_splits.csv", primary)
    for split_name in ["development", "validation", "test"]:
        write_csv(out / "data" / f"primary_{split_name}_transitions.csv", strict_primary[strict_primary["split_primary"] == split_name])

    split_audit = (
        strict_primary.groupby("split_primary")
        .agg(
            transitions=("transition_id", "size"),
            trajectories=("trajectory_id", "nunique"),
            participants=("participant_id_hash", "nunique"),
            problems=("problem_id", "nunique"),
        )
        .reset_index()
    )
    write_csv(out / "tables" / "split_audit.csv", split_audit)
    write_csv(
        out / "tables" / "validation_checks.csv",
        pd.DataFrame([{"check": key, "passed": bool(value)} for key, value in validation_checks.items()]),
    )

    test_path = out / "data" / "primary_test_transitions.csv"
    checksum_text = (
        f"{hashlib.sha256(test_path.read_bytes()).hexdigest()}  data/{test_path.name}\n"
        f"{sha256_text('|'.join(sorted(strict_primary.loc[strict_primary['split_primary'] == 'test', 'transition_id'].astype(str))))}  sorted_test_transition_ids\n"
    )
    (out / "checksums" / "test_partition.sha256").write_text(checksum_text, encoding="utf-8")
    (out / "analysis" / "profile_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "analysis" / "validation_results.json").write_text(json.dumps(validation_checks, indent=2), encoding="utf-8")

    workbook_frames = {
        "File Profile": file_profile,
        "Language Profile": language_profile,
        "Trajectory Distribution": trajectory_length_distribution,
        "Trajectory Thresholds": pd.DataFrame(threshold_rows),
        "Missingness": pd.DataFrame(missing_rows),
        "Verdicts": verdict_distribution,
        "Exclusions": pd.DataFrame(exclusions),
        "Problem Quality": problem_quality,
        "Problem Splits": problem_split_assignments,
        "Split Audit": split_audit,
        "Data Dictionary": data_dictionary,
        "Problem Similarity": pd.DataFrame(near_problem_pairs, columns=["problem_id_a", "problem_id_b", "exact_normalized_description", "token_jaccard", "review_required"]),
        "Code Leakage Audit": pd.DataFrame(cross_split_code_audit_rows, columns=["match_type", "code_hash", "splits", "split_count", "problem_count", "transition_count", "action"]),
        "Validation Checks": pd.DataFrame([{"check": key, "passed": bool(value)} for key, value in validation_checks.items()]),
    }
    workbook_payload = {}
    for sheet_name, frame in workbook_frames.items():
        workbook_payload[sheet_name] = {
            "columns": list(frame.columns),
            "rows": json.loads(frame.to_json(orient="values")),
        }
    (out / "analysis" / "workbook_tables.json").write_text(
        json.dumps(workbook_payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    make_flow_diagram(summary, out / "figures" / "data_flow.png")
    make_attempt_distribution(trajectory_index, out / "figures" / "attempt_distribution.png")
    make_language_chart(language_profile, out / "figures" / "language_transition_counts.png")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
