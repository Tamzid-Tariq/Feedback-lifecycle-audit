# Completed versus planned

Status date: 2026-09-26

This file distinguishes verified work from planned or deliberately unrun work. Development and Stress-20 metrics are diagnostics; they are not final natural prevalence or held-out effect estimates.

## Verified complete

- CodeStream profiling and the problem-disjoint C-language split: 590 development, 191 validation, and 197 test transitions.
- Development-50 evidence packets and independent A01/A02 annotation exports.
- Development pre-adjudication agreement: lifecycle 48/50 (96%), Cohen's kappa 0.9228; joint five-field agreement 40/50 (80%).
- GLM-5.3 Condition B and Condition C development evaluations: 50/50 lifecycle-correct against the current development reference file for both conditions.
- Qwen3.8-27B development diagnostics: primary B 48 accepted outputs and primary C 49 accepted/operational records, with the documented targeted recovery and validator-abstention caveats.
- Validation-based Calibration-20 manifest: 20 cases selected deterministically before labels with seed `20260926`.
- Calibration Stage A with `stealth/space-bunny-alpha`: 20 calls, 16 usable hints, and 4 preserved failures; no automatic retries or fallback.
- Calibration focal-claim freezing with `first_explicit_diagnostic_assertion_v1`: 16 claims and 16 annotation-eligible packets.
- Synthetic Stress-20 human review: 20 A02-reviewed rows, 10 `RETRACT` and 10 `UNSURE`; not independent consensus or adjudicated gold.
- Synthetic Stress-20 Qwen B/C run: identical settings, B 14/20 and C 16/20 operational accuracy, with evidence SHA match 20/20.
- Non-destructive annotation/results repository reorganization and byte-preservation checks for the original development A01/A02 exports.

## Prepared but not empirically complete

- Calibration-20 A01/A02 annotation has not started.
- Calibration packet compiler/test replay was unavailable at freeze time; those fields are explicitly `NOT_REPLAYED`.
- Development disagreement adjudication remains pending qualified supervisor/adjudicator review.
- The final natural test partition remains locked and has not been evaluated.

## Deliberately not done; do not describe as results

- No Qwen B/C run has been performed on Calibration-20.
- No Qwen B/C run has been performed on held-out TEST-50.
- No natural held-out prevalence/effect estimate is available.
- No learner outcome, learning-gain, or deployed-tutor-effectiveness claim is supported.
- The single-annotator Stress-20 review must not be described as adjudicated human gold.
