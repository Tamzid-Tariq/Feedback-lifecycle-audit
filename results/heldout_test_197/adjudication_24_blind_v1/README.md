# Feedback-lifecycle-audit blind adjudication packet — 24 cases

Open `Feedback-lifecycle-audit_Adjudicator_24_BLIND.html` in a current Chrome or Edge browser.
The tool is self-contained, saves unfinished work in that browser, validates the
decision table, and exports the required 24-row JSON or JSONL return.

Review every case de novo. Use only the displayed frozen evidence: problem,
focal claim, S_t, S_t+1, code diff, compiler output, official tests and outputs,
stored judge traces, and any claim-relevant trace. Do not consult A01, A02, Qwen,
DeepSeek, or any other method output. None of those decisions or outputs is
included in this packet.

Required return fields, in order:

1. item_id
2. original_validity
3. target_state_t1
4. lifecycle_label
5. instructional_priority
6. confidence
7. reason_code
8. evidence_ids
9. adjudication_reason
10. adjudicator_id

The blank machine-readable template is `adjudication_return_template_24.json`.
The allowed values are enforced by `adjudication_return_schema.json` and by the
browser tool. The evidence is also supplied separately as JSON and JSONL for
auditability.
