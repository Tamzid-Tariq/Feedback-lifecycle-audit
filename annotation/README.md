# Human Annotation and Adjudication

Two annotators independently labelled the same 50 fixed development cases. The A01/A02 JSON exports are frozen before comparison; the supervisor resolves disagreements only in the separate adjudicator workflow.

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
- `LIFECYCLE_RUBRIC_v2.md`: operational decision rules
- `ANNOTATOR_TRAINING_AND_BLINDING.md`: independent-rating and blinding protocol
- `decision_table.csv`: lifecycle mapping
- `reason_codes.csv`: evidence-grounded reason codes
- `annotation_schema.json`: JSON export schema
- `annotation_data_dictionary.csv`: output field meanings
- `tools/RevGround_Annotator_A01.html` and `tools/RevGround_Annotator_A02.html`: assigned interfaces
- `revground_annotations_A01.json` and `revground_annotations_A02.json`: untouched independent exports
- `disagreement_cases.csv`: reproducibly generated all-field disagreement index
- `pre_adjudication_summary.md`: short, frozen pilot agreement summary
- `adjudication_cases.json`: evidence plus side-by-side annotations for the adjudicator
- `RevGround_Adjudicator.html`: supervisor adjudication interface

Open the adjudicator through a local static server rooted at `annotation/` so it can load `adjudication_cases.json`; if opened directly, its file chooser provides the same JSON-loading fallback.

## Independence and blinding

Annotators work independently. A01 and A02 exports are frozen before discussion, and disagreements are adjudicated only afterward. Annotator packets omit model/provider identity, method predictions, and the other annotator's answers. The adjudicator page never overwrites either frozen export; it downloads decisions as `revground_adjudication.json`.

## Current status

Independent development annotations are complete. Pre-adjudication lifecycle agreement is 48/50 (96%) with unweighted Cohen's kappa 0.9228; lifecycle disagreements are DEV_010 and DEV_012. Gold lifecycle outcomes remain pending supervisor adjudication.
