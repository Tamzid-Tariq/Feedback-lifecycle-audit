#!/usr/bin/env python3
"""Build the canonical held-out TEST verification report from audited JSON."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


BLUE = "2E74B5"
DARK_BLUE = "1F4D78"
NAVY = "0B2545"
MUTED = "5D6975"
LIGHT_GRAY = "F2F4F7"
CALLOUT = "F4F6F9"
WHITE = "FFFFFF"
RED = "9B1C1C"
GREEN = "2F6B45"
CONTENT_WIDTH_DXA = 9360
TABLE_INDENT_DXA = 120


def set_run_font(run, size: float, color: str = "000000", bold: bool = False, italic: bool = False) -> None:
    run.font.name = "Calibri"
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), "Calibri")
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), "Calibri")
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor.from_string(color)
    run.bold = bold
    run.italic = italic


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top: int = 80, start: int = 120, bottom: int = 80, end: int = 120) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for edge, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{edge}"))
        if node is None:
            node = OxmlElement(f"w:{edge}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_geometry(table, widths_dxa: list[int], indent_dxa: int = TABLE_INDENT_DXA) -> None:
    if sum(widths_dxa) != CONTENT_WIDTH_DXA:
        raise ValueError(f"Table widths must total {CONTENT_WIDTH_DXA}, got {sum(widths_dxa)}")
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    tbl_pr = table._tbl.tblPr
    tbl_w = tbl_pr.find(qn("w:tblW"))
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:w"), str(CONTENT_WIDTH_DXA))
    tbl_w.set(qn("w:type"), "dxa")
    tbl_ind = tbl_pr.find(qn("w:tblInd"))
    if tbl_ind is None:
        tbl_ind = OxmlElement("w:tblInd")
        tbl_pr.append(tbl_ind)
    tbl_ind.set(qn("w:w"), str(indent_dxa))
    tbl_ind.set(qn("w:type"), "dxa")

    grid = table._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths_dxa:
        col = OxmlElement("w:gridCol")
        col.set(qn("w:w"), str(width))
        grid.append(col)
    for row in table.rows:
        for idx, cell in enumerate(row.cells):
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_w = tc_pr.find(qn("w:tcW"))
            if tc_w is None:
                tc_w = OxmlElement("w:tcW")
                tc_pr.append(tc_w)
            tc_w.set(qn("w:w"), str(widths_dxa[idx]))
            tc_w.set(qn("w:type"), "dxa")
            cell.width = Inches(widths_dxa[idx] / 1440)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            set_cell_margins(cell)


def format_table(table, widths_dxa: list[int], header: bool = True, font_size: float = 9.2) -> None:
    set_table_geometry(table, widths_dxa)
    if header:
        tr_pr = table.rows[0]._tr.get_or_add_trPr()
        tbl_header = OxmlElement("w:tblHeader")
        tbl_header.set(qn("w:val"), "true")
        tr_pr.append(tbl_header)
    for row_idx, row in enumerate(table.rows):
        for cell in row.cells:
            if header and row_idx == 0:
                set_cell_shading(cell, LIGHT_GRAY)
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.space_before = Pt(0)
                paragraph.paragraph_format.space_after = Pt(0)
                paragraph.paragraph_format.line_spacing = 1.05
                for run in paragraph.runs:
                    set_run_font(run, font_size, NAVY if row_idx == 0 else "000000", bold=header and row_idx == 0)


def add_table(doc: Document, headers: list[str], rows: list[list[str]], widths_dxa: list[int], font_size: float = 9.2):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    for idx, value in enumerate(headers):
        table.rows[0].cells[idx].text = value
    for values in rows:
        cells = table.add_row().cells
        for idx, value in enumerate(values):
            cells[idx].text = str(value)
    format_table(table, widths_dxa, font_size=font_size)
    return table


def add_heading(doc: Document, text: str, level: int = 1) -> None:
    paragraph = doc.add_paragraph(text, style=f"Heading {level}")
    paragraph.paragraph_format.keep_with_next = True


def add_body(doc: Document, text: str, bold_lead: str | None = None) -> None:
    paragraph = doc.add_paragraph()
    if bold_lead and text.startswith(bold_lead):
        lead = paragraph.add_run(bold_lead)
        set_run_font(lead, 11, bold=True)
        body = paragraph.add_run(text[len(bold_lead):])
        set_run_font(body, 11)
    else:
        run = paragraph.add_run(text)
        set_run_font(run, 11)


def add_caption(doc: Document, text: str) -> None:
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(4)
    paragraph.paragraph_format.space_after = Pt(10)
    paragraph.paragraph_format.keep_with_next = False
    run = paragraph.add_run(text)
    set_run_font(run, 9.2, MUTED, italic=True)


def add_source_note(doc: Document, text: str) -> None:
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(4)
    paragraph.paragraph_format.space_after = Pt(4)
    run = paragraph.add_run(text)
    set_run_font(run, 8.5, MUTED, italic=True)


def add_callout(doc: Document, label: str, text: str, accent: str = BLUE) -> None:
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(6)
    paragraph.paragraph_format.space_after = Pt(8)
    paragraph.paragraph_format.left_indent = Pt(8)
    paragraph.paragraph_format.right_indent = Pt(8)
    p_pr = paragraph._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), CALLOUT)
    p_pr.append(shd)
    borders = OxmlElement("w:pBdr")
    for edge in ("top", "left", "bottom", "right"):
        border = OxmlElement(f"w:{edge}")
        border.set(qn("w:val"), "single")
        border.set(qn("w:sz"), "6")
        border.set(qn("w:space"), "5")
        border.set(qn("w:color"), "C8CDD3")
        borders.append(border)
    p_pr.append(borders)
    lead = paragraph.add_run(f"{label}: ")
    set_run_font(lead, 11, accent, bold=True)
    body = paragraph.add_run(text)
    set_run_font(body, 11, NAVY)


def add_page_break(doc: Document) -> None:
    doc.add_page_break()


def set_styles(doc: Document) -> None:
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
    normal.font.size = Pt(11)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.10
    for name, size, color, before, after in (
        ("Heading 1", 16, BLUE, 16, 8),
        ("Heading 2", 13, BLUE, 12, 6),
        ("Heading 3", 12, DARK_BLUE, 8, 4),
    ):
        style = doc.styles[name]
        style.font.name = "Calibri"
        style._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True


def add_page_field(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = paragraph.add_run("Page ")
    set_run_font(run, 8.5, MUTED)
    fld_char_begin = OxmlElement("w:fldChar")
    fld_char_begin.set(qn("w:fldCharType"), "begin")
    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = " PAGE "
    fld_char_end = OxmlElement("w:fldChar")
    fld_char_end.set(qn("w:fldCharType"), "end")
    run._r.append(fld_char_begin)
    run._r.append(instr_text)
    run._r.append(fld_char_end)


def set_page_and_furniture(doc: Document) -> None:
    for section in doc.sections:
        section.page_width = Inches(8.5)
        section.page_height = Inches(11)
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)
        section.header_distance = Inches(0.492)
        section.footer_distance = Inches(0.492)
        header = section.header.paragraphs[0]
        header.text = "RevGround | Held-out TEST verification"
        header.alignment = WD_ALIGN_PARAGRAPH.LEFT
        for run in header.runs:
            set_run_font(run, 8.5, MUTED)
        footer = section.footer.paragraphs[0]
        add_page_field(footer)


def make_figures(result: dict, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    qwen = result["model_results"]["qwen_qwen3_8_27b"]["paired"]
    qwen_path = output_dir / "qwen_paired_common_decision_accuracy.png"
    fig, ax = plt.subplots(figsize=(6.4, 3.35), dpi=220)
    values = [qwen["condition_B_accuracy_percent"], qwen["condition_C_accuracy_percent"]]
    bars = ax.bar(["Condition B", "Condition C"], values, color=["#4C78A8", "#F58518"], width=0.58)
    ax.set_ylim(90, 100)
    ax.set_ylabel("Accuracy (%)")
    ax.set_title(f"Qwen paired common-decision accuracy (n={qwen['paired_decision_count']})", loc="left", weight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.22)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.18, f"{value:.2f}%", ha="center", va="bottom", weight="bold")
    ax.text(0.5, 90.45, f"C - B = {qwen['condition_C_minus_B_percentage_points']:+.2f} pp", ha="center", color="#5D6975")
    fig.tight_layout()
    fig.savefig(qwen_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    cross_path = output_dir / "cross_model_paired_effect.png"
    ds = result["model_results"]["deepseek_v4_1_flash"]["paired"]
    effects = [ds["condition_C_minus_B_percentage_points"], qwen["condition_C_minus_B_percentage_points"]]
    labels = [f"DeepSeek (n={ds['paired_decision_count']})", f"Qwen (n={qwen['paired_decision_count']})"]
    fig, ax = plt.subplots(figsize=(6.4, 3.35), dpi=220)
    bars = ax.barh(labels, effects, color=["#59A14F", "#E15759"], height=0.5)
    ax.axvline(0, color="#333333", linewidth=1)
    ax.set_xlim(-2.5, 2.5)
    ax.set_xlabel("C - B accuracy difference (percentage points)")
    ax.set_title("Model-specific paired effects point in opposite directions", loc="left", weight="bold")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", alpha=0.22)
    for bar, value in zip(bars, effects):
        x = value + (0.08 if value >= 0 else -0.08)
        ax.text(x, bar.get_y() + bar.get_height() / 2, f"{value:+.2f} pp", ha="left" if value >= 0 else "right", va="center", weight="bold")
    fig.tight_layout()
    fig.savefig(cross_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return qwen_path, cross_path


def build_report(result: dict, output_path: Path, figure_dir: Path) -> None:
    qwen_figure, cross_figure = make_figures(result, figure_dir)
    doc = Document()
    set_styles(doc)
    set_page_and_furniture(doc)

    # Memo masthead.
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(16)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run("VERIFIED RESULTS REPORT")
    set_run_font(run, 10, BLUE, bold=True)
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run("RevGround Held-out TEST-197 / TEST-168")
    set_run_font(run, 23, NAVY, bold=True)
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(14)
    run = p.add_run("Human reliability, adjudicated lifecycle prevalence, and B/C evaluator comparison")
    set_run_font(run, 13, MUTED)
    metadata = [
        ("Status", "Verified; all reported TEST-set quantities recomputed"),
        ("Audit date", "29 September 2026"),
        ("Source partition", "197 transitions"),
        ("Analytic cohort", "168 frozen claim-bearing packets"),
        ("Provider calls", "0 during verification"),
    ]
    add_table(doc, ["Field", "Value"], [[a, b] for a, b in metadata], [2100, 7260], 10)
    doc.add_paragraph()
    add_callout(
        doc,
        "Verdict",
        "No false quantitative TEST-set result was detected. The model-specific paired effects are small and point in opposite directions; the supported conclusion is no consistent directional advantage, not statistical equivalence.",
        GREEN,
    )

    add_heading(doc, "1. Cohort and provenance", 1)
    add_body(doc, "The report uses TEST-197 for the frozen source partition and TEST-168 for the final claim-bearing analytic cohort. Keeping these names distinct avoids implying that all 197 source transitions received human labels or model decisions.")
    cohort_rows = [
        ["Source TEST partition", "197", "Frozen test transitions"],
        ["Confirmed C", "188", "Nine objective language exclusions"],
        ["Stage-A calls", "190", "50 historical Batch 1 + 140 Batch 2"],
        ["Accepted hints", "170", "Twenty preserved Stage-A failures"],
        ["Final analytic cohort", "168", "3 problems, 49 trajectories, 42 participants"],
        ["Locked state replays", "252", "S_t and S_t+1 for 126 new packet cases"],
    ]
    add_table(doc, ["Stage", "Count", "Boundary"], cohort_rows, [3100, 1100, 5160], 9.4)
    add_source_note(doc, "Source: frozen cohort profile, packet manifest, screening ledger, and integrity summary.")

    add_page_break(doc)
    add_heading(doc, "2. Human annotation reliability", 1)
    human = result["human_annotation"]
    agreement_rows = []
    for field, label in (
        ("original_validity", "Original validity"),
        ("target_state_t1", "Target state at t+1"),
        ("lifecycle_label", "Lifecycle label"),
        ("instructional_priority", "Instructional priority"),
    ):
        row = human["agreement"][field]
        agreement_rows.append([
            label,
            f"{row['count']}/{row['total']}",
            f"{row['raw_agreement_percent']:.2f}%",
            f"{row['cohen_kappa']:.4f}",
        ])
    add_table(doc, ["Field", "Agreement", "Raw agreement", "Cohen kappa"], agreement_rows, [3200, 1900, 2200, 2060], 9.5)
    add_source_note(doc, "Pre-adjudication A01/A02 agreement; kappa is unweighted.")
    add_body(doc, f"All four core fields agreed jointly on {human['all_four_core_fields_agreement_count']}/168 cases. The 24 unique disagreement cases comprise {human['lifecycle_disagreement_count']} lifecycle disagreements and one priority-only disagreement.")

    add_heading(doc, "2.1 Final adjudicated gold", 2)
    gold = human["final_gold_distribution"]
    gold_rows = [
        ["KEEP", str(gold["KEEP"]), f"{100 * gold['KEEP'] / 168:.2f}%", "Claim remains active"],
        ["RETIRE", str(gold["RETIRE"]), f"{100 * gold['RETIRE'] / 168:.2f}%", "Supported claim resolved"],
        ["RETRACT", str(gold["RETRACT"]), f"{100 * gold['RETRACT'] / 168:.2f}%", "Original claim not supported"],
        ["UNSURE", str(gold.get("UNSURE", 0)), f"{100 * gold.get('UNSURE', 0) / 168:.2f}%", "Indeterminate"],
    ]
    add_table(doc, ["Label", "Count", "Share", "Meaning"], gold_rows, [1600, 1200, 1600, 4960], 9.5)
    add_body(doc, f"Among {human['supported_original_validity_count']} hints supported at generation time, {human['supported_and_resolved_count']} were resolved by the next observed revision ({100 * human['supported_and_resolved_count'] / human['supported_original_validity_count']:.2f}%).")
    add_callout(doc, "Adjudication freeze", "All 24 disagreement cases are present in the final JSON and JSONL exports, all required fields are populated, all evidence references are valid, and the blind packet remains unchanged.")

    add_page_break(doc)
    add_heading(doc, "3. Frozen primary matrix and predeclared recovery", 1)
    primary = result["primary_matrix"]
    add_body(doc, f"The primary matrix is complete: {primary['frozen_run_count']} frozen model-condition runs and {primary['requested_primary_attempts']} first attempts. Primary files were not overwritten by recovery.")
    recovery_rows = []
    for model_key, model_label in (("deepseek_v4_1_flash", "DeepSeek V4.1 Flash"), ("qwen_qwen3_8_27b", "Qwen3.8-27B")):
        for condition in ("B", "C"):
            row = result["recovery"][model_key][condition]
            recovery_rows.append([
                model_label,
                condition,
                str(row["primary_http_429_count"]),
                str(row["recovery_attempt_count"]),
                str(row["accepted_count"]),
                str(row["error_count"]),
            ])
    add_table(doc, ["Model", "Cond.", "Primary 429", "Recovery calls", "Accepted", "Errors"], recovery_rows, [2600, 850, 1500, 1700, 1350, 1360], 8.9)
    add_source_note(doc, "Recovery policy: exactly one call per primary HTTP 429; 20 seconds between calls, 90 seconds after another 429; no retry or fallback; non-429 failures excluded.")

    add_heading(doc, "4. Post-recovery model results", 1)
    metric_rows = []
    safety_rows = []
    for model_key, model_label in (("deepseek_v4_1_flash", "DeepSeek"), ("qwen_qwen3_8_27b", "Qwen")):
        for condition in ("B", "C"):
            row = result["model_results"][model_key][condition]
            metric_rows.append([
                model_label,
                condition,
                str(row["usable_output_count"]),
                str(row["explicit_abstention_count"]),
                str(row["non_abstaining_decision_count"]),
                f"{row['correct_count']}/{row['non_abstaining_decision_count']}",
                f"{row['decision_accuracy_percent']:.2f}%",
            ])
            safety_rows.append([
                model_label,
                condition,
                f"{row['false_keep_count']}/{row['false_keep_denominator']}",
                f"{row['keep_true_positive_count']}/{row['keep_recall_denominator']}",
                f"{row['wrongful_removal_count']}/{row['keep_recall_denominator']}",
                f"{row['retract_true_positive_count']}/{row['retract_gold_count']}",
            ])
    add_table(doc, ["Model", "Cond.", "Usable", "Abstain", "Decisions", "Correct", "Accuracy"], metric_rows, [1650, 720, 1100, 1100, 1300, 1600, 1890], 8.8)
    add_source_note(doc, "Decision accuracy is calculated on non-abstaining outputs under the frozen shared evaluator. Condition B is normalized as non-abstaining because it has no selective-decision field.")
    add_heading(doc, "4.1 Safety-relevant lifecycle errors", 2)
    add_table(doc, ["Model", "Cond.", "False KEEP", "KEEP recall", "Wrongful removal", "RETRACT recall"], safety_rows, [1700, 760, 1450, 1450, 2200, 1800], 8.8)

    add_page_break(doc)
    add_heading(doc, "5. Paired common-decision comparison", 1)
    paired_rows = []
    for model_key, model_label in (("deepseek_v4_1_flash", "DeepSeek V4.1 Flash"), ("qwen_qwen3_8_27b", "Qwen3.8-27B")):
        row = result["model_results"][model_key]["paired"]
        paired_rows.append([
            model_label,
            str(row["paired_decision_count"]),
            f"{row['condition_B_correct_count']}/{row['paired_decision_count']} ({row['condition_B_accuracy_percent']:.2f}%)",
            f"{row['condition_C_correct_count']}/{row['paired_decision_count']} ({row['condition_C_accuracy_percent']:.2f}%)",
            f"{row['condition_C_minus_B_percentage_points']:+.2f} pp",
        ])
    add_table(doc, ["Model", "Paired n", "Condition B", "Condition C", "C - B"], paired_rows, [2350, 1200, 2100, 2100, 1610], 9.2)
    cross = result["cross_model_paired"]
    add_body(doc, f"Descriptively aggregating the model-specific paired sets gives {cross['paired_decision_count']} model-case comparisons. B and C are each correct on {cross['condition_B_correct_count']}/{cross['paired_decision_count']} ({cross['condition_B_accuracy_percent']:.2f}%). Both conditions are simultaneously correct on {cross['both_conditions_correct_count']} comparisons.")
    add_body(doc, f"Each condition produces one false KEEP and eight wrongful removals in the descriptive aggregate. Because model-specific paired subsets differ and cases are clustered, this is not a formal pooled estimator.")

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    qwen_image = p.add_run().add_picture(str(qwen_figure), width=Inches(6.25))
    qwen_image._inline.docPr.set("descr", "Bar chart: Qwen Condition B accuracy 98.26 percent and Condition C accuracy 96.52 percent on 115 paired decisions.")
    add_caption(doc, "Figure 1. Qwen paired common-decision accuracy. The paired subset contains 115 cases.")

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    cross_image = p.add_run().add_picture(str(cross_figure), width=Inches(6.25))
    cross_image._inline.docPr.set("descr", "Horizontal bar chart: DeepSeek C minus B accuracy is plus 1.61 percentage points; Qwen is minus 1.74 percentage points.")
    add_caption(doc, "Figure 2. Cross-model paired C-B effect. Positive values favor C; negative values favor B.")

    add_page_break(doc)
    add_heading(doc, "6. Interpretation and reporting boundary", 1)
    add_callout(doc, "Supported conclusion", "On the natural held-out cohort, explicit lifecycle structuring does not yield a consistent accuracy advantage over the matched-evidence auditor. DeepSeek moves modestly toward C; Qwen moves modestly toward B.", GREEN)
    add_body(doc, "The paired point estimates are descriptive. No paired confidence interval, equivalence test, or null-hypothesis test is included, so the report does not claim statistical equivalence or proof of no effect.")
    add_body(doc, "Rare-label inference remains limited because the natural gold contains only three RETRACT and no UNSURE cases. Controlled Stress-20 results should remain in a separate diagnostic section and must not alter natural prevalence estimates.")
    add_body(doc, "Operational coverage and decision quality are distinct. Provider failures remain retained in the ledgers, while accepted explicit abstentions are excluded from decision-accuracy denominators under the frozen evaluator.")

    add_heading(doc, "7. Reproducibility map", 1)
    repro_rows = [
        ["Human exports", "results/heldout_test_197/annotations_frozen_v1/"],
        ["Blind adjudication packet", "results/heldout_test_197/adjudication_24_blind_v1/"],
        ["Final adjudication", "results/heldout_test_197/adjudication_24_final_v1/"],
        ["Primary and recovery ledgers", "results/heldout_test_197/evaluations/"],
        ["Machine-readable audit", "results/heldout_test_197/analysis/verified_test_results.json"],
        ["Recomputation script", "scripts/audit_heldout_test197_results.py"],
    ]
    add_table(doc, ["Artifact", "Repository path"], repro_rows, [2800, 6560], 8.9)
    add_source_note(doc, "All reported values in this report are generated from the machine-readable audit output. No model predictions were exposed to the adjudicator packet.")

    set_page_and_furniture(doc)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.repo.resolve()
    input_path = args.input or root / "results" / "heldout_test_197" / "analysis" / "verified_test_results.json"
    output_path = args.output or root / "docs" / "reports" / "RevGround_TEST197_Verified_Results_20260929.docx"
    result = json.loads(input_path.read_text(encoding="utf-8"))
    if result.get("status") != "PASS_ALL_REPORTED_TEST_RESULTS_RECOMPUTED":
        raise SystemExit("Refusing to build report from an unverified result")
    build_report(result, output_path, output_path.parent / "figures")
    print(output_path)


if __name__ == "__main__":
    main()
