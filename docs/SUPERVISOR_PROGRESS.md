# RevGround Supervisor Progress

## Completed

- Source-language QC completed on the full strict-C pool using only source syntax. The audit contains 978 rows: 954 `CONFIRMED_C`, 13 `NON_C_CPP`, 9 `NON_C_JAVA`, and 2 `AMBIGUOUS`.
- Objective exclusions were preserved rather than deleted: Development `DEV_010` is Java and `DEV_012` is C++; frozen TEST-50 exclusions are `726478f13ad8e011c4a0cfa2` (Java) and `bda05da230eecfb67fa3a104` (C++).
- Calibration-20 language QC found 20/20 `CONFIRMED_C` cases.
- TEST-50 Stage A eligibility was calculated without rerunning generations: 50 frozen cases minus 2 language exclusions leaves 48 eligible C cases; all 6 Stage-A failures are among eligible cases, leaving 42 analyzable natural cases.

- Data profiling completed.
- Primary study language selected: C.
- Development evidence packets prepared.
- Lifecycle Rubric v2.0 used.
- 50 development cases independently annotated by A01 and A02.
- Pre-adjudication agreement calculated.
- Development-50 adjudication completed from the supplied final reference: 40 consensus carry-forwards and 10 adjudicated review rows; final reference SHA-256 `8fbcebe1e0e200f8d4ae52f30df597da086330e20be3493c80b4e603bcd5b07d`.
- Condition B baseline implementation prepared.
- Condition B GLM-5.3 development evaluation completed for all 50 cases.
- Condition C controlled GLM-5.3 audit evaluation completed for all 50 cases.
- Shared B/C normalization and matched-evidence verification completed: 50/50 evidence hashes matched.
- Git checkpoint created before the annotation-layout reorganization: `2b690a4`.
- Annotation tree reorganized into common, Development-50, Calibration-20, Stress-20, and held-out TEST-50 namespaces without changing the original A01/A02 development export bytes.
- Official fresh calibration manifest replaced the older development-based proposal: 20 deterministic validation cases, seed `20260926`; the old 25-case manifest is retained under `data/manifests/archive/` as SUPERSEDED.
- Calibration Stage A attempted all 20 validation cases with `stealth/space-bunny-alpha`, using only S_t fields, fallback disabled, and no automatic retries. Sixteen hints were usable and four failures were preserved.
- Sixteen exact-span focal claims were frozen with extractor `first_explicit_diagnostic_assertion_v1`. The calibration packet contains the 16 annotation-eligible cases.
- Calibration Stage-B evidence replay is complete for those 16 cases: 32 locked-runner state replays and 450 official test-state entries were attached using `revground-c-runner:2.0`. The four Stage-A failures remain preserved outside the packet.
- Calibration-20 A01 and A02 annotation is complete for all 16 eligible rows. All five decision fields agree on every row; `rubric_change_required=false`, adjudication was not required, and Rubric v2.0 is frozen as final.
- Held-out TEST-50 annotation packages are released for the 42 successful claim-bearing C cases. They are label-independent and contain no model predictions, other-annotator outputs, intended labels, or adjudication information.
- DeepSeek V4.1 Flash substitution is complete on Development-50 and Stress-20: 140 primary calls, 137 accepted outputs, 3 preserved primary failures, no recovery pass. Stress C has one recorded decision-rule violation (`STR_011`) represented as an abstention.
- Synthetic Stress-20 human review was preserved as a completed single-annotator (`A_02`) review: 10 `RETRACT` and 10 `UNSURE`; it is not adjudicated consensus.
- Synthetic Stress-20 Qwen B/C results were verified under identical settings: B 14/20 and C 16/20 operational accuracy; paired agreement 17/19 (89.5%); evidence SHA match 20/20.

## Annotation Results

Development cases: 50
Lifecycle agreement: 48/50 (96%)
Cohen's kappa: 0.9228

The final adjudication reference is complete: `DEV_010` is `RETIRE`, `DEV_012` is `KEEP`, and the file contains 40 consensus carry-forwards plus 10 adjudicated review rows.

Historical pre-adjudication lifecycle disagreements:
- DEV_010
- DEV_012

The historical Development-50 lifecycle result remains 48/50 (96%), κ=0.9228. The source-language sensitivity analysis excluding the two objective mismatch cases is 48/48, κ=1.0000; this is additional sensitivity analysis, not a replacement of the primary result.

Cases differing on any decision field:
DEV_004, DEV_007, DEV_010, DEV_012, DEV_027,
DEV_029, DEV_038, DEV_048, DEV_049, DEV_050.

## Model-condition Development Results

- Condition B: 50 canonical merged records; the 48 first-attempt successes plus successful retries for DEV_012 and DEV_046.
- Condition C: 50/50 accepted outputs, zero packet-validation abstentions, and zero lifecycle decision-rule violations.
- Condition C lifecycle distribution: KEEP=21, RETIRE=29.
- Aggregate B/C evaluation uses one shared normalized schema; B is represented with `abstain=false`.
- These are technical development diagnostics against the finalized adjudication reference, not held-out natural estimates.

DeepSeek V4.1 Flash used the same frozen B/C settings (`max_tokens=16000`, timeout 360 seconds, fallback/recovery disabled) and completed 100 Development-50 primary calls. B and C each had 49 accepted outputs and 48/50 operational accuracy; B failed on `DEV_024` with a non-string response and C rejected `DEV_024` for an unsupported evidence ID. The complete aggregate, parity audit, sanitized run metadata, and failure taxonomy are in [`results/deepseek_v4_1_flash/`](../results/deepseek_v4_1_flash/).

## Synthetic Stress-20 Results

- Condition B: 19/20 outputs, 14/20 operationally correct (70.0%).
- Condition C: 20/20 outputs, 16/20 operationally correct (80.0%).
- C corrected B on `STR_005` and `STR_008`, improved reviewed-RETRACT recall from 80% to 100%, and eliminated false KEEP on reviewed RETRACT cases.
- Both conditions recognized 6/10 UNSURE cases; this limitation remains.
- These results are reported separately from natural CodeStream prevalence.

DeepSeek Stress-20 used the same frozen settings for both conditions. B accepted 19/20 and reached 9/20 operational accuracy; C accepted 20/20 and reached 15/20 operational accuracy. DeepSeek C reduced false KEEP from 10% to 0% and raised reviewed-RETRACT recall from 70% to 90%, while six explicit UNSURE abstentions were recorded. One C decision-rule violation on `STR_011` is retained in the run record.

## Current Requirements

1. Rubric v2.0 is frozen after Calibration-20; no calibration adjudication was required.
2. Complete independent A01/A02 annotation on the released held-out natural packages.
3. Preserve the 50-case held-out sample and its 42-case claim-bearing cohort without replacement.
4. Do not run Qwen or DeepSeek B/C on Calibration-20 or held-out TEST yet.

## Next Stage

1. Annotate the released 42-case held-out natural package independently with A01 and A02.
2. Compare completed development and calibration outputs under the frozen Rubric v2.0.
3. Only after annotation gates are complete, authorize final held-out B/C evaluation.
