#!/usr/bin/env python3
"""Coverage-aware descriptive evaluation for matched lifecycle predictions."""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

LABELS = ("KEEP", "RETIRE", "RETRACT", "UNSURE")
DECIDABLE = {"KEEP", "RETIRE", "RETRACT"}


def div(a, b):
    return a / b if b else None


def as_bool(value):
    if isinstance(value, bool):
        return value
    v = str(value).strip().lower()
    if v in {"true", "1", "yes"}: return True
    if v in {"false", "0", "no"}: return False
    raise ValueError(f"Invalid boolean: {value!r}")


def wilson(successes, total, z=1.959963984540054):
    if total == 0:
        return [None, None]
    p = successes / total
    den = 1 + z*z/total
    center = (p + z*z/(2*total)) / den
    half = z * math.sqrt(p*(1-p)/total + z*z/(4*total*total)) / den
    return [max(0, center-half), min(1, center+half)]


def score(rows):
    n = len(rows)
    gold = Counter(r["gold_label"] for r in rows)
    pred = Counter(r["predicted_label"] for r in rows)
    cm = Counter((r["gold_label"], r["predicted_label"]) for r in rows if not r["abstain"])
    decidable = [r for r in rows if r["gold_label"] in DECIDABLE]
    actions = [r for r in decidable if not r["abstain"]]
    unsafe = [r for r in rows if r["gold_label"] in {"RETIRE", "RETRACT"}]
    keep = [r for r in rows if r["gold_label"] == "KEEP"]
    retract_predictions = [r for r in rows if not r["abstain"] and r["predicted_label"] == "RETRACT"]
    retract_gold = [r for r in rows if r["gold_label"] == "RETRACT"]
    gold_unsure = [r for r in rows if r["gold_label"] == "UNSURE"]

    f1 = {}
    precision = {}
    recall = {}
    for label in LABELS:
        tp = cm[label, label]
        fp = sum(v for (g,p),v in cm.items() if p == label and g != label)
        fn = sum(1 for r in rows if r["gold_label"] == label and (r["abstain"] or r["predicted_label"] != label))
        precision[label] = div(tp, tp+fp)
        recall[label] = div(tp, tp+fn)
        f1[label] = div(2*tp, 2*tp+fp+fn)

    false_keep_num = sum((not r["abstain"]) and r["predicted_label"] == "KEEP" for r in unsafe)
    wrong_remove_num = sum((not r["abstain"]) and r["predicted_label"] in {"RETIRE","RETRACT"} for r in keep)
    risk_num = sum(r["predicted_label"] != r["gold_label"] for r in actions)
    keep_correct = sum((not r["abstain"]) and r["predicted_label"] == "KEEP" for r in keep)
    retract_correct = sum(r["gold_label"] == "RETRACT" for r in retract_predictions)
    retract_recall_num = sum((not r["abstain"]) and r["predicted_label"] == "RETRACT" for r in retract_gold)
    unsure_withheld = sum(r["abstain"] or r["predicted_label"] == "UNSURE" for r in gold_unsure)
    confident_factual_unsure = sum((not r["abstain"]) and r["predicted_label"] in DECIDABLE and (r["confidence"] is not None and r["confidence"] >= .7) for r in gold_unsure)

    present_f1 = [v for v in f1.values() if v is not None]
    return {
        "n": n,
        "gold_counts": dict(gold),
        "prediction_counts": dict(pred),
        "abstentions": sum(r["abstain"] for r in rows),
        "invalid_or_failed_statuses": sum(r["status"] != "success" for r in rows),
        "confusion_nonabstaining": {g:{p:cm[g,p] for p in LABELS} for g in LABELS},
        "per_class_precision": precision, "per_class_recall": recall, "per_class_f1": f1,
        "macro_f1_present_classes": div(sum(present_f1), len(present_f1)),
        "false_keep": {"numerator":false_keep_num,"denominator":len(unsafe),"rate":div(false_keep_num,len(unsafe)),"wilson_95":wilson(false_keep_num,len(unsafe))},
        "false_keep_by_gold": {
            g:{"numerator":sum((not r["abstain"]) and r["predicted_label"]=="KEEP" for r in rows if r["gold_label"]==g),"denominator":gold[g]}
            for g in ("RETIRE","RETRACT")
        },
        "decision_coverage": {"numerator":len(actions),"denominator":len(decidable),"rate":div(len(actions),len(decidable))},
        "selective_risk": {"numerator":risk_num,"denominator":len(actions),"rate":div(risk_num,len(actions))},
        "keep_recall": {"numerator":keep_correct,"denominator":len(keep),"rate":div(keep_correct,len(keep))},
        "wrongful_removal": {"numerator":wrong_remove_num,"denominator":len(keep),"rate":div(wrong_remove_num,len(keep))},
        "retraction_precision": {"numerator":retract_correct,"denominator":len(retract_predictions),"rate":div(retract_correct,len(retract_predictions))},
        "retraction_recall": {"numerator":retract_recall_num,"denominator":len(retract_gold),"rate":div(retract_recall_num,len(retract_gold))},
        "gold_unsure_withheld": {"numerator":unsure_withheld,"denominator":len(gold_unsure),"rate":div(unsure_withheld,len(gold_unsure))},
        "confident_factual_on_gold_unsure": {"numerator":confident_factual_unsure,"denominator":len(gold_unsure),"rate":div(confident_factual_unsure,len(gold_unsure))},
        "mean_latency_ms": div(sum(r["latency_ms"] for r in rows if r["latency_ms"] is not None), sum(r["latency_ms"] is not None for r in rows)),
        "estimated_cost_usd": sum(r["estimated_cost_usd"] or 0 for r in rows),
    }


def load_rows(path):
    with Path(path).open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError("No predictions. Empty templates are not experimental results.")
    required = {"claim_id","trajectory_id","participant_id_hash","problem_id","problem_family_id","method","gold_label","predicted_label","abstain","confidence","latency_ms","estimated_cost_usd","status"}
    out = []
    for i, r in enumerate(rows, 2):
        missing = [k for k in required if k not in r or r[k] == ""]
        # Nullable numeric fields may be blank.
        missing = [k for k in missing if k not in {"confidence","latency_ms","estimated_cost_usd"}]
        if missing: raise ValueError(f"Row {i} missing: {missing}")
        if r["gold_label"] not in LABELS or r["predicted_label"] not in LABELS:
            raise ValueError(f"Row {i}: invalid label")
        rr = dict(r)
        rr["abstain"] = as_bool(r["abstain"])
        for k in ("confidence","latency_ms","estimated_cost_usd"):
            rr[k] = float(r[k]) if r.get(k,"").strip() else None
        out.append(rr)
    return out


def evaluate(rows):
    by_method = defaultdict(list)
    seen = set()
    for r in rows:
        key = (r["claim_id"], r["method"])
        if key in seen: raise ValueError(f"Duplicate claim/method: {key}")
        seen.add(key); by_method[r["method"]].append(r)
    claim_sets = {m:{r["claim_id"] for r in rs} for m,rs in by_method.items()}
    first = next(iter(claim_sets.values()))
    if any(s != first for s in claim_sets.values()):
        raise ValueError("Methods must preserve identical claim IDs; failures/abstentions cannot be dropped")
    by_claim = defaultdict(list)
    for r in rows: by_claim[r["claim_id"]].append(r)
    for claim, rs in by_claim.items():
        for key in ("gold_label","trajectory_id","participant_id_hash","problem_id","problem_family_id"):
            if len({r[key] for r in rs}) != 1: raise ValueError(f"Inconsistent {key} for {claim}")
    result = {"methods":{},"design_notes":{
        "primary_contrast":"C versus B","inference":"Descriptive paired results; approve clustered uncertainty plan before confirmatory claims.",
        "abstention":"Stored independently of predicted label; all-abstain has zero coverage, not zero risk."}}
    for method, rs in sorted(by_method.items()):
        fam = defaultdict(list); prob = defaultdict(list)
        for r in rs: fam[r["problem_family_id"]].append(r); prob[r["problem_id"]].append(r)
        result["methods"][method] = {"overall":score(rs),"by_problem_family":{k:score(v) for k,v in sorted(fam.items())},"by_problem":{k:score(v) for k,v in sorted(prob.items())},"problem_family_count":len(fam),"problem_count":len(prob)}
    if "B" in by_method and "C" in by_method:
        b={r["claim_id"]:r for r in by_method["B"]}; c={r["claim_id"]:r for r in by_method["C"]}
        paired=[]
        for claim in sorted(b):
            rb,rc=b[claim],c[claim]; gold=rb["gold_label"]
            if gold not in {"RETIRE","RETRACT"}: continue
            fb=(not rb["abstain"] and rb["predicted_label"]=="KEEP")
            fc=(not rc["abstain"] and rc["predicted_label"]=="KEEP")
            paired.append({"claim_id":claim,"problem_family_id":rb["problem_family_id"],"B_false_keep":fb,"C_false_keep":fc})
        result["primary_paired_false_keep"]={
            "eligible":len(paired),"B_only_error":sum(x["B_false_keep"] and not x["C_false_keep"] for x in paired),
            "C_only_error":sum(x["C_false_keep"] and not x["B_false_keep"] for x in paired),
            "both_error":sum(x["B_false_keep"] and x["C_false_keep"] for x in paired),
            "neither_error":sum(not x["B_false_keep"] and not x["C_false_keep"] for x in paired),
            "warning":"Do not apply an ordinary McNemar test unless independence is justified; claims cluster by trajectory, participant and problem."
        }
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument("input_csv",type=Path);p.add_argument("output_json",type=Path);a=p.parse_args()
    a.output_json.write_text(json.dumps(evaluate(load_rows(a.input_csv)),indent=2)+"\n",encoding="utf-8")


if __name__ == "__main__": main()

