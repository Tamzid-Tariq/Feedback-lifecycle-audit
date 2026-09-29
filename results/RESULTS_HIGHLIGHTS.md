# Feedback-lifecycle-audit Results Highlights

This file is the compact results index. Development results are diagnostics,
Stress-20 is a controlled rare-label experiment, Calibration-20 freezes the
rubric, and TEST-168 supplies the final natural held-out estimates.

## Development-50 human annotation

- 50 reference rows: 40 A01/A02 consensus carry-forwards plus 10 adjudication-review rows.
- Current reference lifecycle distribution: 21 `KEEP` (42%), 29 `RETIRE` (58%), 0 `RETRACT`, 0 `UNSURE`.
- Pre-adjudication agreement: original validity 48/50 (96%, κ=0.3243); target state 48/50 (96%, κ=0.9228); lifecycle 48/50 (96%, κ=0.9228); priority 44/50 (88%, κ=0.7608); leakage 45/50 (90%, κ=0).
- Joint agreement across all five fields: 40/50 (80%). Lifecycle disagreements: `DEV_010` and `DEV_012`.
- The supplied final reference contains 40 consensus carry-forwards and 10 rows with `status=adjudicated` and `provenance=adjudication_review`. The 10 review rows are therefore adjudicated; the provenance is retained to distinguish them from direct A01/A02 consensus.

## Development model diagnostics

| Method | End-to-end lifecycle result | Coverage / abstention | Safety-relevant result |
|---|---:|---:|---|
| GLM-5.3 B | 50/50 (100%) | 50/50 | 0 false KEEP; KEEP recall 21/21 |
| GLM-5.3 C | 50/50 (100%) | 50/50 | 0 false KEEP; KEEP recall 21/21 |
| Qwen3.8-27B B primary | 48/48 accepted (100%); 48/50 end-to-end (96%) | 48/50 decision coverage; 2 no-decision | 0 false KEEP; KEEP recall 19/21 |
| Qwen3.8-27B C operational | 46/49 accepted (93.9%); 46/50 end-to-end (92%) | 47/50 decision coverage; 3 system/model no-decision | 0 false KEEP in accepted KEEP/RETIRE comparison; 1 wrongful removal; KEEP recall 17/21 |

For the 48 primary-run cases with outputs from both Qwen conditions, lifecycle agreement was 46/48 (95.8%); B was 48/48 correct and C was 46/48 correct. Evidence SHA values matched for all 50 items. C's `DEV_024` outcome was a validator-triggered system abstention for an invalid evidence reference, not a gold `UNSURE` label.

The original Qwen B/C development runs used different output limits (B=5,000 and C=12,000 tokens); this is a development-stage implementation caveat. Later work uses identical frozen settings.

## Source-language QC and natural eligibility

- The full strict-C pool was scanned with a source-syntax-only classifier, never using lifecycle labels, annotator results, or model performance.
- Across 978 strict-C transitions: 954 are `CONFIRMED_C`, 13 are `NON_C_CPP`, 9 are `NON_C_JAVA`, and 2 are `AMBIGUOUS`.
- Development-50 preserves the original lifecycle reliability result of 48/50 (96%), κ=0.9228. Excluding objective `DEV_010` (Java) and `DEV_012` (C++) as a sensitivity analysis gives 48/48, κ=1.0000.
- The frozen TEST-50 excludes exactly `726478f13ad8e011c4a0cfa2` (Java) and `bda05da230eecfb67fa3a104` (C++), leaving 48 eligible C cases. The six completed Stage-A failures are all eligible, so 42 final natural cases are analyzable.
- Calibration-20 has 20/20 `CONFIRMED_C` cases. These QC records and SHA-256 hashes are in [`data/qc/`](../data/qc/).

## Synthetic Stress-20

The stress result is documented separately in [stress_20_results_summary.md](stress_20/stress_20_results_summary.md), and the completed human review is preserved in [annotation/stress_20/synthetic_stress_20_human_review.csv](../annotation/stress_20/synthetic_stress_20_human_review.csv).

- Human review: 10 `RETRACT`, 10 `UNSURE`; one annotator (`A_02`), not adjudicated consensus.
- Qwen B: 14/20 (70.0%) operational accuracy; 19/20 outputs.
- Qwen C: 16/20 (80.0%) operational accuracy; 20/20 outputs.
- Paired 19-case comparison: B 14/19, C 16/19, B/C agreement 17/19 (89.5%).
- C improved RETRACT recall from 80% to 100%, removed false KEEP on reviewed RETRACT cases (10% to 0%), and reduced decidable-case selective risk (20% to 0%).
- UNSURE recognition stayed at 60% for both conditions.
- This is a controlled rare-label diagnostic, not a natural prevalence estimate.

## Calibration and held-out status

- Calibration-20: 20 validation cases selected deterministically before labels; 16 usable Stage-A hints and 4 preserved failures. A01 and A02 each annotated all 16 eligible rows, with zero substantive disagreements across the five decision fields. `rubric_change_required=false`; no adjudication was required or performed, and Rubric v2.0 is frozen as final.
- Calibration-20 packet build: 16 focal claims frozen and 32 locked-runner state replays attached, with 450 official test-state evidence entries; four Stage-A failures remain outside the packet.
- No Qwen B/C calibration run has been performed.
- Historical TEST-50 remains preserved as Batch 1. The full TEST-197 source partition yields 168 claim-bearing packets after nine objective language exclusions and 20 preserved Stage-A failures.

## Final natural TEST-197 / TEST-168 results

- A01 and A02 each annotated all 168 claim-bearing packets.
- Pre-adjudication lifecycle agreement: 145/168 (86.31%), Cohen kappa 0.7249.
- Unique core-field disagreements: 24; 23 lifecycle and one priority-only.
- All 24 disagreement cases were adjudicated from the blind evidence packet and frozen separately from A01/A02.
- Final lifecycle distribution: 100 `KEEP` (59.52%), 65 `RETIRE` (38.69%), 3 `RETRACT` (1.79%), and 0 `UNSURE`.
- All four Qwen/DeepSeek B/C primary runs are frozen at 168 first attempts each. `RECOVERY_429_V1` contains exactly one attempt per primary HTTP 429 and does not replace any primary outcome.

Paired common-decision results:

| Model | Paired n | B accuracy | C accuracy | C - B |
|---|---:|---:|---:|---:|
| DeepSeek V4.1 Flash | 124 | 117/124 (94.35%) | 119/124 (95.97%) | +1.61 pp |
| Qwen3.8-27B | 115 | 113/115 (98.26%) | 111/115 (96.52%) | -1.74 pp |

Descriptively, each condition is correct on 230/239 model-case comparisons
(96.23%). The model-specific directions differ, so the supported interpretation
is no consistent directional advantage. This is not a statistical equivalence
claim or a formal pooled estimate. See
[`heldout_test_197/analysis/verified_test_results.md`](heldout_test_197/analysis/verified_test_results.md).

## DeepSeek V4.1 Flash substitution diagnostics

- Development-50: 100 primary calls under identical B/C settings (`max_tokens=16000`, 360-second timeout, fallback/recovery disabled); B and C each accepted 49/50 and reached 48/50 operational accuracy. `DEV_024` failed in B with a non-string response and in C with an unsupported evidence-ID validator rejection.
- Stress-20: 40 primary calls; B accepted 19/20 and reached 9/20 operational accuracy, while C accepted 20/20 and reached 15/20. False KEEP fell from 10% to 0%, reviewed-RETRACT recall rose from 70% to 90%, and C recorded six explicit UNSURE abstentions. The one C decision-rule violation (`STR_011`) is retained as a recorded abstention.
- DeepSeek primary total: 140 calls, 137 accepted outputs, 3 preserved failures, and no recovery pass. See [`results/deepseek_v4_1_flash/`](deepseek_v4_1_flash/).

## Bottom line

The study now has a frozen rubric, completed natural held-out annotation and
adjudication, four frozen TEST-168 primary evaluator runs, isolated 429 recovery,
and a deterministic no-provider-call verification audit. Natural paired effects
are small and model-dependent. Stress-20 remains separate evidence that the
structured condition is most useful when refutation and uncertainty are
deliberately represented.
