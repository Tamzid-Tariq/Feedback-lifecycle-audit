# Experiment Status

Updated: 2026-09-29

## Current state

| Component | Status |
|---|---|
| Development-50 annotation and adjudication | Complete |
| Calibration-20 annotation and Rubric v2.0 freeze | Complete; no substantive disagreement |
| Synthetic Stress-20 | Complete diagnostic; reported separately from natural prevalence |
| TEST-197 source cohort | Frozen: 197 transitions, 188 confirmed C, 9 exclusions |
| TEST-168 analytic cohort | Frozen: 168 claim-bearing packets |
| TEST-168 A01/A02 annotation | Complete: 168 rows each |
| TEST-168 blind adjudication | Complete: 24/24 disagreement cases |
| Qwen B/C primary matrix | Complete and frozen: 168 attempts per condition |
| DeepSeek B/C primary matrix | Complete and frozen: 168 attempts per condition |
| `RECOVERY_429_V1` | Complete with recorded errors; one attempt per primary 429 |
| Evaluator evidence parity | PASS: 168/168 |
| Final TEST result audit | PASS: all reported quantities recomputed |

## Natural held-out results

Pre-adjudication lifecycle agreement is 145/168 (86.31%), with unweighted
Cohen kappa 0.7249. The 24 core-field disagreement cases include 23 lifecycle
disagreements and one priority-only disagreement.

Final adjudicated gold contains 100 KEEP, 65 RETIRE, 3 RETRACT, and 0 UNSURE.
Among 165 hints supported at generation time, 65 were resolved by the next
observed revision.

Paired common-decision accuracy:

| Model | Paired n | Condition B | Condition C | C - B |
|---|---:|---:|---:|---:|
| DeepSeek V4.1 Flash | 124 | 117/124 (94.35%) | 119/124 (95.97%) | +1.61 pp |
| Qwen3.8-27B | 115 | 113/115 (98.26%) | 111/115 (96.52%) | -1.74 pp |

The two model-specific effects point in opposite directions. The result supports
no consistent directional advantage; it is not a formal pooled, equivalence, or
null-effect estimate.

## Retention boundary

- Original A01/A02 exports remain byte-for-byte frozen.
- The blind adjudication packet and final adjudicator return are separate.
- Primary first attempts and `RECOVERY_429_V1` remain separate.
- Recovery is limited to primary HTTP 429 outcomes and never replaces a case.
- Provider failures and accepted explicit abstentions remain distinguishable.
- Calibration-20 Qwen/DeepSeek B/C evaluation has not been run.
- No learner-outcome or deployed-tutor-effectiveness claim is supported.

## Primary references

- [Held-out package](../results/heldout_test_197/README.md)
- [Machine-readable verification](../results/heldout_test_197/analysis/verified_test_results.json)
- [Reader-facing verification](../results/heldout_test_197/analysis/verified_test_results.md)
- [Canonical report](reports/README.md)
- [Results highlights](../results/RESULTS_HIGHLIGHTS.md)
