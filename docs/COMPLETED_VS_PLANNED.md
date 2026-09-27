# Completed versus planned

Status date: 2026-09-27

This file distinguishes verified work from planned or deliberately unrun work. Development and Stress-20 metrics are diagnostics; they are not final natural prevalence or held-out effect estimates.

## Verified complete

- CodeStream profiling and the problem-disjoint C-language split: 590 development, 191 validation, and 197 test transitions.
- Development-50 evidence packets and independent A01/A02 annotation exports.
- Development pre-adjudication agreement: lifecycle 48/50 (96%), Cohen's kappa 0.9228; joint five-field agreement 40/50 (80%).
- Development-50 adjudication: complete in `annotation/development_50/revground_adjudication_final.jsonl` (50 rows; 40 consensus carry-forwards and 10 adjudicated review rows; SHA-256 `8fbcebe1e0e200f8d4ae52f30df597da086330e20be3493c80b4e603bcd5b07d`).
- GLM-5.3 Condition B and Condition C development evaluations: 50/50 lifecycle-correct against the current development reference file for both conditions.
- Qwen3.8-27B development diagnostics: primary B 48 accepted outputs and primary C 49 accepted/operational records, with the documented targeted recovery and validator-abstention caveats.
- Validation-based Calibration-20 manifest: 20 cases selected deterministically before labels with seed `20260926`.
- Calibration Stage A with `stealth/space-bunny-alpha`: 20 calls, 16 usable hints, and 4 preserved failures; no automatic retries or fallback.
- Calibration focal-claim freezing with `first_explicit_diagnostic_assertion_v1`: 16 claims and 16 annotation-eligible packets.
- Calibration-20 Stage-B evidence replay: 32 state replays and 450 official test-state entries through `revground-c-runner:2.0`; compiler/test outcomes are attached to the frozen packets.
- Synthetic Stress-20 human review: 20 A02-reviewed rows, 10 `RETRACT` and 10 `UNSURE`; not independent consensus or adjudicated gold.
- Synthetic Stress-20 Qwen B/C run: identical settings, B 14/20 and C 16/20 operational accuracy, with evidence SHA match 20/20.
- Non-destructive annotation/results repository reorganization and byte-preservation checks for the original development A01/A02 exports.
- Source-language QC of the full 978-row strict-C pool using code syntax only: 954 `CONFIRMED_C`, 13 `NON_C_CPP`, 9 `NON_C_JAVA`, and 2 `AMBIGUOUS`.
- Development sensitivity analysis preserving the historical 48/50 (96%), κ=0.9228 result and reporting 48/48, κ=1.0000 after excluding objective `DEV_010` and `DEV_012` language mismatches.
- Frozen TEST-50 eligibility accounting: two objective exclusions leave 48 C-eligible cases; the six recorded Stage-A failures are all eligible, leaving 42 final analyzable natural cases.
- Calibration-20 source-language QC: all 20 selected validation cases are `CONFIRMED_C`.
- Calibration-20 independent annotation: A01 and A02 each supplied 16 eligible rows; all five decision fields agree on all 16 rows, so `rubric_change_required=false`, adjudication was not required, and no adjudication was performed.
- Rubric v2.0 is frozen as the final annotation rubric after Calibration-20.
- Held-out natural annotation packages were released for 42 successful, C-eligible TEST cases; they contain only the frozen packets, rubric, and annotator HTML.
- TEST-197 protocol amendment is frozen before additional held-out labels or evaluator results: the historical TEST-50 manifest remains Batch 1, the complete TEST partition has 197 rows, source-only QC preserves 9 objective language exclusions, and Batch 2 contains 147 cases.
- Final TEST-197 Stage-A preparation is complete with the frozen `stealth/space-bunny-alpha` policy: 140 new calls, 126 accepted hints, 14 preserved failures; combined with historical Batch 1 this is 190 calls, 170 accepted hints, 20 preserved failures, and 168 successful C claim-bearing packets.
- Locked Docker replay is complete for the 126 new packet cases (252 state replays); the final claim-bearing profile is 168 cases, 3 problems, 49 trajectories, and 42 participants. Isolated A01/A02 packages contain only the identical frozen packet, Rubric v2.0, and annotator HTML.
- DeepSeek V4.1 Flash substitution diagnostics are complete for Development-50 and Stress-20: 140 primary calls, 137 accepted outputs, and 3 preserved primary failures; no recovery pass was run. Stress Condition C has one recorded decision-rule violation (`STR_011`) represented as an abstention.

## Prepared but not empirically complete

- The final TEST-197 A01/A02 natural annotation is prepared but not yet complete.
- The final natural TEST-197 B/C evaluation remains locked and unrun for both Qwen and DeepSeek.

## Deliberately not done; do not describe as results

- No Qwen or DeepSeek B/C run has been performed on Calibration-20.
- No Qwen or DeepSeek B/C run has been performed on held-out TEST-197.
- No natural held-out prevalence/effect estimate is available.
- No learner outcome, learning-gain, or deployed-tutor-effectiveness claim is supported.
- The single-annotator Stress-20 review must not be described as adjudicated human gold.
