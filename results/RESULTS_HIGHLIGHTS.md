# RevGround Results Highlights

This file is the compact results index. Development results are diagnostics, the stress set is a controlled rare-label experiment, and the calibration/held-out stages are not final prevalence estimates.

## Development-50 human annotation

- 50 reference rows: 40 A01/A02 consensus carry-forwards plus 10 adjudication-review rows.
- Current reference lifecycle distribution: 21 `KEEP` (42%), 29 `RETIRE` (58%), 0 `RETRACT`, 0 `UNSURE`.
- Pre-adjudication agreement: original validity 48/50 (96%, κ=0.3243); target state 48/50 (96%, κ=0.9228); lifecycle 48/50 (96%, κ=0.9228); priority 44/50 (88%, κ=0.7608); leakage 45/50 (90%, κ=0).
- Joint agreement across all five fields: 40/50 (80%). Lifecycle disagreements: `DEV_010` and `DEV_012`.
- The 10 review rows are recorded with adjudication-review provenance and must not be described as independent expert-human adjudication without qualified approval.

## Development model diagnostics

| Method | End-to-end lifecycle result | Coverage / abstention | Safety-relevant result |
|---|---:|---:|---|
| GLM-5.3 B | 50/50 (100%) | 50/50 | 0 false KEEP; KEEP recall 21/21 |
| GLM-5.3 C | 50/50 (100%) | 50/50 | 0 false KEEP; KEEP recall 21/21 |
| Qwen3.8-27B B primary | 48/48 accepted (100%); 48/50 end-to-end (96%) | 48/50 decision coverage; 2 no-decision | 0 false KEEP; KEEP recall 19/21 |
| Qwen3.8-27B C operational | 46/49 accepted (93.9%); 46/50 end-to-end (92%) | 47/50 decision coverage; 3 system/model no-decision | 0 false KEEP in accepted KEEP/RETIRE comparison; 1 wrongful removal; KEEP recall 17/21 |

For the 48 primary-run cases with outputs from both Qwen conditions, lifecycle agreement was 46/48 (95.8%); B was 48/48 correct and C was 46/48 correct. Evidence SHA values matched for all 50 items. C's `DEV_024` outcome was a validator-triggered system abstention for an invalid evidence reference, not a gold `UNSURE` label.

The original Qwen B/C development runs used different output limits (B=5,000 and C=12,000 tokens); this is a development-stage implementation caveat. Later work uses identical frozen settings.

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

- Calibration-20: 20 validation cases selected deterministically before labels; 16 usable Stage-A hints and 4 preserved failures; no human annotation completed yet.
- No Qwen B/C calibration run has been performed.
- Held-out TEST-50 remains locked; no annotation or Qwen B/C run has been performed.

## Bottom line

The development set supports strong pre-adjudication human lifecycle agreement and shows no GLM B/C lifecycle difference. Qwen C exhibits useful audit behavior but does not improve natural development accuracy. On the separate synthetic rare-label stress set, Qwen C is better at catching directly refutable claims and avoiding false KEEP decisions, while both conditions remain weak at recognizing evidence-insufficient `UNSURE` cases.
