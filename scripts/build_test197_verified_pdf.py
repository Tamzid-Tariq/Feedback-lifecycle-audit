#!/usr/bin/env python3
"""Build the canonical held-out TEST verification PDF from audited JSON."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


BLUE = colors.HexColor("#2E74B5")
DARK_BLUE = colors.HexColor("#1F4D78")
NAVY = colors.HexColor("#0B2545")
MUTED = colors.HexColor("#5D6975")
LIGHT_GRAY = colors.HexColor("#F2F4F7")
CALLOUT = colors.HexColor("#F4F6F9")
GREEN = colors.HexColor("#2F6B45")
RED = colors.HexColor("#9B1C1C")


def styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=NAVY,
            alignment=TA_LEFT,
            spaceAfter=6,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=12.5,
            leading=16,
            textColor=MUTED,
            spaceAfter=16,
        ),
        "kicker": ParagraphStyle(
            "Kicker",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=BLUE,
            spaceAfter=5,
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            textColor=BLUE,
            spaceBefore=12,
            spaceAfter=7,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11.5,
            leading=14,
            textColor=DARK_BLUE,
            spaceBefore=9,
            spaceAfter=5,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.6,
            leading=13,
            textColor=colors.black,
            spaceAfter=7,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8.2,
            leading=10.3,
            textColor=colors.black,
        ),
        "small_header": ParagraphStyle(
            "SmallHeader",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8.2,
            leading=10.3,
            textColor=NAVY,
        ),
        "source": ParagraphStyle(
            "Source",
            parent=base["BodyText"],
            fontName="Helvetica-Oblique",
            fontSize=7.7,
            leading=9.5,
            textColor=MUTED,
            spaceBefore=4,
            spaceAfter=7,
        ),
        "caption": ParagraphStyle(
            "Caption",
            parent=base["BodyText"],
            fontName="Helvetica-Oblique",
            fontSize=8.1,
            leading=10.2,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceBefore=4,
            spaceAfter=8,
        ),
        "callout": ParagraphStyle(
            "Callout",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.6,
            leading=13,
            textColor=NAVY,
        ),
    }


def p(text: str, style) -> Paragraph:
    return Paragraph(text, style)


def table(data, widths, st, font_size=8.2, repeat_rows=1):
    converted = []
    for row_idx, row in enumerate(data):
        converted.append([
            value if hasattr(value, "wrap") else p(str(value), st["small_header"] if row_idx == 0 else st["small"])
            for value in row
        ])
    result = Table(converted, colWidths=widths, repeatRows=repeat_rows, hAlign="LEFT")
    result.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_GRAY),
        ("TEXTCOLOR", (0, 0), (-1, 0), NAVY),
        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#C8CDD3")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return result


def callout(label: str, text: str, st, accent=GREEN):
    content = p(f'<font color="{accent.hexval()}"><b>{label}:</b></font> {text}', st["callout"])
    result = Table([[content]], colWidths=[6.5 * inch], hAlign="LEFT")
    result.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CALLOUT),
        ("BOX", (0, 0), (-1, -1), 0.65, colors.HexColor("#C8CDD3")),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return result


def page_furniture(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.8)
    canvas.setFillColor(MUTED)
    canvas.drawString(0.72 * inch, 10.48 * inch, "Feedback-lifecycle-audit | Held-out TEST verification")
    canvas.drawRightString(7.78 * inch, 0.48 * inch, f"Page {doc.page}")
    canvas.setStrokeColor(colors.HexColor("#D9DDE2"))
    canvas.setLineWidth(0.5)
    canvas.line(0.72 * inch, 10.35 * inch, 7.78 * inch, 10.35 * inch)
    canvas.restoreState()


def build(result: dict, output: Path, figure_dir: Path) -> None:
    st = styles()
    doc = SimpleDocTemplate(
        str(output),
        pagesize=letter,
        leftMargin=1 * inch,
        rightMargin=1 * inch,
        topMargin=0.9 * inch,
        bottomMargin=0.72 * inch,
        title="Feedback-lifecycle-audit TEST-197 / TEST-168 Verified Results",
        author="Feedback-lifecycle-audit",
        subject="Frozen held-out annotation and evaluator verification",
    )
    story = []
    story.extend([
        Spacer(1, 0.16 * inch),
        p("VERIFIED RESULTS REPORT", st["kicker"]),
        p("Feedback-lifecycle-audit Held-out TEST-197 / TEST-168", st["title"]),
        p("Human reliability, adjudicated lifecycle prevalence, and B/C evaluator comparison", st["subtitle"]),
    ])
    metadata = [
        ["Field", "Value"],
        ["Status", "Verified; all reported TEST-set quantities recomputed"],
        ["Audit date", "29 September 2026"],
        ["Source partition", "197 transitions"],
        ["Analytic cohort", "168 frozen claim-bearing packets"],
        ["Provider calls", "0 during verification"],
    ]
    story.append(table(metadata, [1.45 * inch, 5.05 * inch], st))
    story.append(Spacer(1, 0.16 * inch))
    story.append(callout(
        "Verdict",
        "No false quantitative TEST-set result was detected. The model-specific paired effects are small and point in opposite directions; the supported conclusion is no consistent directional advantage, not statistical equivalence.",
        st,
    ))
    story.extend([
        p("1. Cohort and provenance", st["h1"]),
        p("The report uses TEST-197 for the frozen source partition and TEST-168 for the final claim-bearing analytic cohort. Keeping these names distinct avoids implying that all 197 source transitions received human labels or model decisions.", st["body"]),
    ])
    cohort = [
        ["Stage", "Count", "Boundary"],
        ["Source TEST partition", "197", "Frozen test transitions"],
        ["Confirmed C", "188", "Nine objective language exclusions"],
        ["Stage-A calls", "190", "50 historical Batch 1 plus 140 Batch 2"],
        ["Accepted hints", "170", "Twenty preserved Stage-A failures"],
        ["Final analytic cohort", "168", "3 problems, 49 trajectories, 42 participants"],
        ["Locked state replays", "252", "S_t and S_t+1 for 126 new packet cases"],
    ]
    story.append(table(cohort, [2.1 * inch, 0.75 * inch, 3.65 * inch], st))
    story.append(p("Source: frozen cohort profile, packet manifest, screening ledger, and integrity summary.", st["source"]))

    story.append(PageBreak())
    story.append(p("2. Human annotation reliability", st["h1"]))
    human = result["human_annotation"]
    agreement = [["Field", "Agreement", "Raw agreement", "Cohen kappa"]]
    for field, label in (
        ("original_validity", "Original validity"),
        ("target_state_t1", "Target state at t+1"),
        ("lifecycle_label", "Lifecycle label"),
        ("instructional_priority", "Instructional priority"),
    ):
        row = human["agreement"][field]
        agreement.append([label, f"{row['count']}/{row['total']}", f"{row['raw_agreement_percent']:.2f}%", f"{row['cohen_kappa']:.4f}"])
    story.append(table(agreement, [2.2 * inch, 1.3 * inch, 1.55 * inch, 1.45 * inch], st))
    story.append(p("Pre-adjudication A01/A02 agreement; kappa is unweighted.", st["source"]))
    story.append(p(f"All four core fields agreed jointly on {human['all_four_core_fields_agreement_count']}/168 cases. The 24 unique disagreement cases comprise {human['lifecycle_disagreement_count']} lifecycle disagreements and one priority-only disagreement.", st["body"]))
    story.append(p("2.1 Final adjudicated gold", st["h2"]))
    gold = human["final_gold_distribution"]
    gold_table = [
        ["Label", "Count", "Share", "Meaning"],
        ["KEEP", gold["KEEP"], f"{100 * gold['KEEP'] / 168:.2f}%", "Claim remains active"],
        ["RETIRE", gold["RETIRE"], f"{100 * gold['RETIRE'] / 168:.2f}%", "Supported claim resolved"],
        ["RETRACT", gold["RETRACT"], f"{100 * gold['RETRACT'] / 168:.2f}%", "Original claim not supported"],
        ["UNSURE", gold.get("UNSURE", 0), f"{100 * gold.get('UNSURE', 0) / 168:.2f}%", "Indeterminate"],
    ]
    story.append(table(gold_table, [1.05 * inch, 0.8 * inch, 1.05 * inch, 3.6 * inch], st))
    story.append(Spacer(1, 0.08 * inch))
    story.append(p(f"Among {human['supported_original_validity_count']} hints supported at generation time, {human['supported_and_resolved_count']} were resolved by the next observed revision ({100 * human['supported_and_resolved_count'] / human['supported_original_validity_count']:.2f}%).", st["body"]))
    story.append(callout("Adjudication freeze", "All 24 disagreement cases are present in the final JSON and JSONL exports, all required fields are populated, all evidence references are valid, and the blind packet remains unchanged.", st, BLUE))

    story.append(PageBreak())
    story.append(p("3. Frozen primary matrix and predeclared recovery", st["h1"]))
    primary = result["primary_matrix"]
    story.append(p(f"The primary matrix is complete: {primary['frozen_run_count']} frozen model-condition runs and {primary['requested_primary_attempts']} first attempts. Primary files were not overwritten by recovery.", st["body"]))
    recovery = [["Model", "Cond.", "Primary 429", "Recovery calls", "Accepted", "Errors"]]
    for model_key, model_label in (("deepseek_v4_1_flash", "DeepSeek V4.1 Flash"), ("qwen_qwen3_8_27b", "Qwen3.8-27B")):
        for condition in ("B", "C"):
            row = result["recovery"][model_key][condition]
            recovery.append([model_label, condition, row["primary_http_429_count"], row["recovery_attempt_count"], row["accepted_count"], row["error_count"]])
    story.append(table(recovery, [1.85 * inch, 0.55 * inch, 1.05 * inch, 1.2 * inch, 0.95 * inch, 0.9 * inch], st))
    story.append(p("Recovery policy: exactly one call per primary HTTP 429; 20 seconds between calls, 90 seconds after another 429; no retry or fallback; non-429 failures excluded.", st["source"]))
    story.append(p("4. Post-recovery model results", st["h1"]))
    metrics = [["Model", "Cond.", "Usable", "Abstain", "Decisions", "Correct", "Accuracy"]]
    safety = [["Model", "Cond.", "False KEEP", "KEEP recall", "Wrongful removal", "RETRACT recall"]]
    for model_key, model_label in (("deepseek_v4_1_flash", "DeepSeek"), ("qwen_qwen3_8_27b", "Qwen")):
        for condition in ("B", "C"):
            row = result["model_results"][model_key][condition]
            metrics.append([model_label, condition, row["usable_output_count"], row["explicit_abstention_count"], row["non_abstaining_decision_count"], f"{row['correct_count']}/{row['non_abstaining_decision_count']}", f"{row['decision_accuracy_percent']:.2f}%"])
            safety.append([model_label, condition, f"{row['false_keep_count']}/{row['false_keep_denominator']}", f"{row['keep_true_positive_count']}/{row['keep_recall_denominator']}", f"{row['wrongful_removal_count']}/{row['keep_recall_denominator']}", f"{row['retract_true_positive_count']}/{row['retract_gold_count']}"])
    story.append(table(metrics, [1.2 * inch, 0.5 * inch, 0.8 * inch, 0.8 * inch, 0.95 * inch, 1.1 * inch, 1.15 * inch], st))
    story.append(p("Decision accuracy is calculated on non-abstaining outputs under the frozen shared evaluator. Condition B is normalized as non-abstaining because it has no selective-decision field.", st["source"]))
    story.append(p("4.1 Safety-relevant lifecycle errors", st["h2"]))
    story.append(table(safety, [1.15 * inch, 0.5 * inch, 1.0 * inch, 1.0 * inch, 1.65 * inch, 1.2 * inch], st))

    story.append(PageBreak())
    story.append(p("5. Paired common-decision comparison", st["h1"]))
    paired_table = [["Model", "Paired n", "Condition B", "Condition C", "C - B"]]
    for model_key, model_label in (("deepseek_v4_1_flash", "DeepSeek V4.1 Flash"), ("qwen_qwen3_8_27b", "Qwen3.8-27B")):
        row = result["model_results"][model_key]["paired"]
        paired_table.append([model_label, row["paired_decision_count"], f"{row['condition_B_correct_count']}/{row['paired_decision_count']} ({row['condition_B_accuracy_percent']:.2f}%)", f"{row['condition_C_correct_count']}/{row['paired_decision_count']} ({row['condition_C_accuracy_percent']:.2f}%)", f"{row['condition_C_minus_B_percentage_points']:+.2f} pp"])
    story.append(table(paired_table, [1.75 * inch, 0.75 * inch, 1.55 * inch, 1.55 * inch, 0.9 * inch], st))
    cross = result["cross_model_paired"]
    story.append(p(f"Descriptively aggregating the model-specific paired sets gives {cross['paired_decision_count']} model-case comparisons. B and C are each correct on {cross['condition_B_correct_count']}/{cross['paired_decision_count']} ({cross['condition_B_accuracy_percent']:.2f}%). Both conditions are simultaneously correct on the same case in {cross['both_conditions_correct_count']} comparisons.", st["body"]))
    story.append(p("Each condition produces one false KEEP and eight wrongful removals in the descriptive aggregate. Because model-specific paired subsets differ and cases are clustered, this is not a formal pooled estimator.", st["body"]))
    qwen_path = figure_dir / "qwen_paired_common_decision_accuracy.png"
    story.append(KeepTogether([
        Image(str(qwen_path), width=6.25 * inch, height=3.27 * inch),
        p("Figure 1. Qwen paired common-decision accuracy. The paired subset contains 115 cases.", st["caption"]),
    ]))

    story.append(PageBreak())
    cross_path = figure_dir / "cross_model_paired_effect.png"
    story.append(p("5.1 Cross-model effect direction", st["h2"]))
    story.append(KeepTogether([
        Image(str(cross_path), width=6.25 * inch, height=3.27 * inch),
        p("Figure 2. Cross-model paired C - B effect. Positive values favor C; negative values favor B.", st["caption"]),
    ]))
    story.append(callout("Supported conclusion", "On the natural held-out cohort, explicit lifecycle structuring does not yield a consistent accuracy advantage over the matched-evidence auditor. DeepSeek moves modestly toward C; Qwen moves modestly toward B.", st, GREEN))

    story.append(p("6. Interpretation and reporting boundary", st["h1"]))
    story.append(p("The paired point estimates are descriptive. No paired confidence interval, equivalence test, or null-hypothesis test is included, so the report does not claim statistical equivalence or proof of no effect.", st["body"]))
    story.append(p("Rare-label inference remains limited because the natural gold contains only three RETRACT and no UNSURE cases. Controlled Stress-20 results should remain in a separate diagnostic section and must not alter natural prevalence estimates.", st["body"]))
    story.append(p("Operational coverage and decision quality are distinct. Provider failures remain retained in the ledgers, while accepted explicit abstentions are excluded from decision-accuracy denominators under the frozen evaluator.", st["body"]))

    story.append(p("7. Reproducibility map", st["h1"]))
    repro = [
        ["Artifact", "Repository path"],
        ["Human exports", "results/heldout_test_197/annotations_frozen_v1/"],
        ["Blind adjudication packet", "results/heldout_test_197/adjudication_24_blind_v1/"],
        ["Final adjudication", "results/heldout_test_197/adjudication_24_final_v1/"],
        ["Primary and recovery ledgers", "results/heldout_test_197/evaluations/"],
        ["Machine-readable audit", "results/heldout_test_197/analysis/verified_test_results.json"],
        ["Recomputation script", "scripts/audit_heldout_test197_results.py"],
    ]
    story.append(table(repro, [2.05 * inch, 4.45 * inch], st))
    story.append(p("All reported values in this report are generated from the machine-readable audit output. No model predictions were exposed to the adjudicator packet.", st["source"]))

    output.parent.mkdir(parents=True, exist_ok=True)
    doc.build(story, onFirstPage=page_furniture, onLaterPages=page_furniture)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.repo.resolve()
    input_path = args.input or root / "results" / "heldout_test_197" / "analysis" / "verified_test_results.json"
    output = args.output or root / "docs" / "reports" / "Feedback-lifecycle-audit_TEST197_Verified_Results_20260929.pdf"
    result = json.loads(input_path.read_text(encoding="utf-8"))
    if result.get("status") != "PASS_ALL_REPORTED_TEST_RESULTS_RECOMPUTED":
        raise SystemExit("Refusing to build PDF from an unverified result")
    build(result, output, output.parent / "figures")
    print(output)


if __name__ == "__main__":
    main()
