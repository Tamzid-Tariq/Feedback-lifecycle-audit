# Human Annotation

Two annotators independently label the same 50 fixed development cases. The standalone pages run locally without a server and store A01/A02 progress under separate browser keys.

## Annotation order

1. Inspect the problem, S_t code, original hint, and fixed focal claim span.
2. Assign original validity: SUPPORTED, REFUTED, or INDETERMINATE.
3. Inspect S_t+1, the diff, compiler messages, tests, outputs, and trace identifiers.
4. Assign target state: PRESENT, RESOLVED, INDETERMINATE, or NOT_APPLICABLE.
5. Assign lifecycle: KEEP, RETIRE, RETRACT, or UNSURE.
6. Label instructional priority and leakage separately.
7. Record evidence IDs, confidence, and a short justification.

## Files

- `development_50_evidence_frozen_v1.jsonl`: sanitized fixed evidence packets
- `lifecycle_rubric_v2.md`: operational decision rules
- `decision_table.csv`: lifecycle mapping
- `annotation_schema.json`: JSON export schema
- `annotation_data_dictionary.csv`: output field meanings
- `tools/RevGround_Annotator_A01.html` and `tools/RevGround_Annotator_A02.html`: assigned interfaces

## Independence and blinding

Annotators work independently. A01 and A02 exports are frozen before discussion, and disagreements are adjudicated only afterward. Annotator packets omit model/provider identity, method predictions, and the other annotator's answers.

## Current status

Materials are prepared, but no human labels or gold lifecycle outcomes have been collected. Add `annotation/labels/` only after both independent exports are complete; add adjudication files only after those originals are frozen.
