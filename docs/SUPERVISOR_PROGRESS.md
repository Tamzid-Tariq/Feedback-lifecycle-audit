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
- Protocol amendment `test197_full_eligible_cohort_v1` is frozen before any additional held-out labels or model results. Historical TEST-50 is preserved as Batch 1; all 197 TEST transitions are retained in the final cohort manifest.
- Objective source-only QC across TEST-197 found 188 `CONFIRMED_C` cases and 9 preserved language exclusions. The remaining Batch 2 contains 147 cases, of which 140 required Stage-A generation.
- Stage-A Batch 2 used only `stealth/space-bunny-alpha` under the frozen prompt/settings: 140 calls, 126 accepted hints, and 14 preserved failures, with no retries, fallback, or replacement. Combined with Batch 1, 190 calls yielded 170 accepted hints, 20 failures, and 168 successful C claim-bearing cases.
- Final claim-bearing profile: 168 cases, 3 problems, 49 trajectories, and 42 participants. All 126 new cases were replayed in the locked Docker C runner (252 state replays); the final evidence packet SHA-256 is recorded in `results/heldout_test_197/final_packet_manifest.json` and `SHA256SUMS.txt`.
- Isolated A01/A02 TEST-197 packages were built over identical packet bytes and contain no reference labels, model predictions, other-annotator outputs, or adjudication information.
- TEST-168 A01/A02 annotation is complete with 168 rows per annotator. The four core fields agree jointly on 144/168 cases; 24 unique disagreements were identified, including 23 lifecycle disagreements and one priority-only disagreement.
- Qualified blind adjudication is complete for all 24 disagreement cases. The returned JSON/JSONL is frozen separately from the unchanged blind packet and A01/A02 exports; final gold is 100 KEEP, 65 RETIRE, 3 RETRACT, and 0 UNSURE.
- The Qwen and DeepSeek primary B/C matrix is complete and frozen: four runs, 168 first attempts each, 672 total. Primary files were not overwritten.
- Qwen and DeepSeek `RECOVERY_429_V1` are complete with recorded errors. Every primary HTTP 429 received exactly one recovery attempt; no non-429 primary failure was recovered.
- The deterministic final audit recomputed all reported TEST-set metrics from frozen artifacts with zero provider calls and passed.

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
2. Preserve historical TEST-50 Batch 1 and the 197-row source cohort without replacement.
3. Preserve A01/A02, blind adjudication, final adjudication, primary attempts, and recovery as separate immutable namespaces.
4. Keep Calibration-20 Qwen/DeepSeek B/C evaluation outside the completed scope unless separately authorized.
5. Report natural paired effects descriptively; do not claim equivalence or a proven null effect.

## Next Stage

1. Integrate the verified TEST tables and figures into the manuscript.
2. Add paired uncertainty estimates only if a formal inferential claim is needed.
3. Maintain the repository hashes and retention boundaries during manuscript revision.
