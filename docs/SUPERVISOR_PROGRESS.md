# RevGround Supervisor Progress

## Completed

- Data profiling completed.
- Primary study language selected: C.
- Development evidence packets prepared.
- Lifecycle Rubric v2.0 used.
- 50 development cases independently annotated by A01 and A02.
- Pre-adjudication agreement calculated.
- Condition B baseline implementation prepared.
- Condition B GLM-5.3 development evaluation completed for all 50 cases.
- Condition C controlled GLM-5.3 audit evaluation completed for all 50 cases.
- Shared B/C normalization and matched-evidence verification completed: 50/50 evidence hashes matched.
- Git checkpoint created before the annotation-layout reorganization: `2b690a4`.
- Annotation tree reorganized into common, Development-50, Calibration-20, Stress-20, and held-out TEST-50 namespaces without changing the original A01/A02 development export bytes.
- Official fresh calibration manifest replaced the older development-based proposal: 20 deterministic validation cases, seed `20260926`; the old 25-case manifest is retained under `data/manifests/archive/` as SUPERSEDED.
- Calibration Stage A attempted all 20 validation cases with `stealth/space-bunny-alpha`, using only S_t fields, fallback disabled, and no automatic retries. Sixteen hints were usable and four failures were preserved.
- Sixteen exact-span focal claims were frozen with extractor `first_explicit_diagnostic_assertion_v1`. The calibration packet contains the 16 annotation-eligible cases; no human annotation has started.
- Synthetic Stress-20 human review was preserved as a completed single-annotator (`A_02`) review: 10 `RETRACT` and 10 `UNSURE`; it is not adjudicated consensus.
- Synthetic Stress-20 Qwen B/C results were verified under identical settings: B 14/20 and C 16/20 operational accuracy; paired agreement 17/19 (89.5%); evidence SHA match 20/20.

## Annotation Results

Development cases: 50
Lifecycle agreement: 48/50 (96%)
Cohen's kappa: 0.9228

Lifecycle disagreements:
- DEV_010
- DEV_012

Cases differing on any decision field:
DEV_004, DEV_007, DEV_010, DEV_012, DEV_027,
DEV_029, DEV_038, DEV_048, DEV_049, DEV_050.

## Model-condition Development Results

- Condition B: 50 canonical merged records; the 48 first-attempt successes plus successful retries for DEV_012 and DEV_046.
- Condition C: 50/50 accepted outputs, zero packet-validation abstentions, and zero lifecycle decision-rule violations.
- Condition C lifecycle distribution: KEEP=21, RETIRE=29.
- Aggregate B/C evaluation uses one shared normalized schema; B is represented with `abstain=false`.
- These are technical development results, not adjudicated accuracy results.

## Synthetic Stress-20 Results

- Condition B: 19/20 outputs, 14/20 operationally correct (70.0%).
- Condition C: 20/20 outputs, 16/20 operationally correct (80.0%).
- C corrected B on `STR_005` and `STR_008`, improved reviewed-RETRACT recall from 80% to 100%, and eliminated false KEEP on reviewed RETRACT cases.
- Both conditions recognized 6/10 UNSURE cases; this limitation remains.
- These results are reported separately from natural CodeStream prevalence.

## Current Requirements

1. Supervisor/qualified adjudication of disagreement cases.
2. Review of rubric before fresh calibration.
3. Preserve the frozen evidence boundary before any validation/test-scale extension.
4. Begin independent A01/A02 calibration annotation from `annotation/calibration_20/`.
5. Do not run Qwen B/C on calibration or held-out TEST yet.

## Next Stage

1. Adjudication
2. Rubric refinement
3. Complete the validation-based Calibration-20 A01/A02 pass
4. Freeze rubric
5. Freeze study splits
6. Natural gold annotation
7. Compare the completed development outputs after adjudication.
