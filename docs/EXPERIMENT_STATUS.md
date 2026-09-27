# Experiment Status

Updated: 2026-09-27

## Current state

The frozen 50-item development evidence set has been evaluated under both primary model conditions.

| Component | Status |
|---|---|
| Frozen development evidence packets | Complete |
| Condition B GLM-5.3 baseline | Complete; canonical 50-record output retained in the local audit workspace |
| Condition C controlled extension | Complete; 50/50 accepted outputs |
| Shared B/C evaluator | Complete |
| Matched evidence verification | Complete; 50/50 TRUE |
| C packet validation | Complete; 50/50 passed |
| C lifecycle decision validation | Complete; 0 violations |
| Source-language QC | Complete; 978 strict-C rows classified from source syntax only |
| Adjudicated human gold | Pending |
| Validation-based Calibration-20 Stage A | 20 attempted; 16 usable hints; 4 failures preserved |
| Calibration-20 Stage-B evidence replay | Complete; 32 locked-runner state replays; 23 compile successes and 9 compile errors |
| Calibration A01/A02 annotation | Complete for 16/16 eligible rows per annotator; zero substantive disagreements; no adjudication required |
| Rubric v2.0 | Frozen final after Calibration-20; `rubric_change_required=false` |
| Synthetic Stress-20 human review | 20 reviewed by A02; 10 RETRACT / 10 UNSURE; not adjudicated consensus |
| Synthetic Stress-20 Qwen B/C | Complete; B 14/20, C 16/20; reported separately |
| DeepSeek V4.1 Flash Development-50 B/C | Complete; 100 primary calls, 98 accepted, 2 preserved failures |
| DeepSeek V4.1 Flash Stress-20 B/C | Complete; 40 primary calls, 39 accepted, 1 preserved failure; C has one recorded decision-rule violation |
| Held-out TEST-50 Stage A | Complete; 44 usable hints and 6 preserved failures |
| Held-out natural annotation packages | Released for 42 claim-bearing cases; annotation pending |
| Calibration/test-scale Qwen/DeepSeek B/C | Not run |

## Conditions

Condition B receives the frozen evidence packet and returns a lifecycle prediction. Condition C receives the same projected packet, applies deterministic evidence checks, follows the explicit RevGround decision procedure, and validates the returned lifecycle decision after the model response.

Both conditions enter the evaluator through the same normalized schema. B is represented as non-selective (`abstain=false`); C preserves abstention and final-action information.

## Development result

Condition C produced 50 accepted outputs with no errors, no packet abstentions, and no decision-rule violations. Its lifecycle distribution was `KEEP=21`, `RETIRE=29`. The B/C evidence hash comparison matched all 50 items.

These are technical development results only. They do not establish agreement or accuracy against A01/A02 or adjudicated gold labels.

## Source-language QC and eligibility impact

The full strict-C pool was classified using only source syntax in `code_t` and `code_t1`; lifecycle labels, annotator results, and model performance were not inputs to the classifier. The 978 rows produced 954 `CONFIRMED_C`, 13 `NON_C_CPP`, 9 `NON_C_JAVA`, and 2 `AMBIGUOUS` records. The audit files and hashes are in [`data/qc/`](../data/qc/).

The Development-50 history is unchanged: lifecycle agreement remains 48/50 (96%), κ=0.9228. A separate sensitivity analysis excluding objective `DEV_010` (Java) and `DEV_012` (C++) gives 48/48 lifecycle agreement, κ=1.0000.

The frozen TEST-50 has exactly two objective language exclusions (`726478f13ad8e011c4a0cfa2` Java and `bda05da230eecfb67fa3a104` C++), leaving 48 eligible C cases. The six Stage-A failures are all among those eligible cases, yielding 42 final analyzable natural cases. No Qwen B/C TEST run has occurred.

Calibration-20 now has a complete frozen evidence packet for the 16 usable Stage-A hints. The packet includes S_t, S_t+1, the unified diff, stored traces, official tests, and locked-runner compiler/test evidence. The four Stage-A failures remain preserved and are not represented as annotation decisions. A01 and A02 independently annotated all 16 eligible rows with zero substantive disagreements; Rubric v2.0 is frozen and no adjudication was required.

## Synthetic Stress-20 result

The controlled rare-label stress run used identical Qwen settings for B and C. On the 19 paired cases, B/C lifecycle agreement was 17/19 (89.5%); B was correct on 14/19 and C on 16/19. C raised reviewed-RETRACT recall from 80% to 100% and reduced false KEEP from 10% to 0%, while UNSURE recognition remained 60% for both. This is a diagnostic stress result, not a natural prevalence estimate. See [the full stress summary](../results/stress_20/stress_20_results_summary.md).

## Reproducibility and retention

The repository contains the runners, prompts, evaluator, and aggregate summaries. Raw provider responses and per-run output trees are intentionally kept outside the public repository in the local audit workspace.

See:

- [Condition C README](../baselines/condition_C/README.md)
- [Development results summary](../results/development_50/development_results_summary.md)
- [Matched evidence summary](../results/development_50/matched_evidence_summary.json)
- [Calibration results](../results/calibration_20/README.md)
- [DeepSeek V4.1 Flash results](../results/deepseek_v4_1_flash/README.md)
- [Source-language QC](../data/qc/language_qc_summary.json)
- [Development QC sensitivity](../results/development_50/language_qc_sensitivity.md)
- [Held-out QC eligibility](../results/heldout_test_50/language_qc_eligibility.md)
- [Results highlights](../results/RESULTS_HIGHLIGHTS.md)
- [Synthetic Stress-20 results](../results/stress_20/stress_20_results_summary.md)
- [Supervisor progress](SUPERVISOR_PROGRESS.md)
