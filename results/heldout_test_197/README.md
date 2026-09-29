# Held-out Natural TEST-197 / TEST-168 Results

This directory is the self-contained reproducibility package for the final
natural held-out analysis. `TEST-197` names the frozen source partition;
`TEST-168` names the claim-bearing analytic cohort after objective language
exclusions and preserved Stage-A failures.

## Cohort accounting

- Source TEST partition: 197 transitions.
- Objective source-language QC: 188 `CONFIRMED_C`; 9 exclusions.
- Stage A: 190 calls (50 historical Batch 1 plus 140 Batch 2).
- Accepted hints: 170; preserved Stage-A failures: 20.
- Final claim-bearing cohort: 168 cases across 3 problems, 49 trajectories,
  and 42 participants.
- Replacements: 0.
- Locked-runner replays: 252 states for the 126 new packet cases.

Preparation hashes remain in [`SHA256SUMS.txt`](SHA256SUMS.txt). Historical
TEST-50 is preserved as Batch 1.

## Human annotation and adjudication

The original A01 and A02 exports are frozen byte-for-byte under
[`annotations_frozen_v1/`](annotations_frozen_v1/). Each contains 168 rows.

- Original-validity agreement: 161/168; Cohen kappa 0.2170.
- Target-state agreement: 145/168; Cohen kappa 0.7249.
- Lifecycle agreement: 145/168; Cohen kappa 0.7249.
- Instructional-priority agreement: 144/168; Cohen kappa 0.7117.
- Joint agreement on all four core fields: 144/168.
- Unique core-field disagreements: 24, comprising 23 lifecycle disagreements
  and one priority-only disagreement.

The immutable blind packet remains in
[`adjudication_24_blind_v1/`](adjudication_24_blind_v1/). The returned decisions
are frozen separately in
[`adjudication_24_final_v1/`](adjudication_24_final_v1/). The final gold
distribution is 100 `KEEP`, 65 `RETIRE`, 3 `RETRACT`, and 0 `UNSURE`.

## Evaluator runs

All four primary first-attempt runs are frozen under
[`evaluations/`](evaluations/): Qwen B/C and DeepSeek B/C, 168 attempts each,
672 total. Primary files were not overwritten.

`RECOVERY_429_V1` is isolated beneath each model. Recovery contains exactly one
attempt for every primary HTTP 429 and excludes HTTP 400, malformed JSON,
schema rejection, input-size failure, and every other non-429 outcome. Both
conditions use 20 seconds between calls and 90 seconds after another 429, with
automatic retry and fallback disabled.

| Model | Condition | Primary 429 | Recovery calls | Accepted | Errors |
|---|---:|---:|---:|---:|---:|
| DeepSeek V4.1 Flash | B | 90 | 90 | 83 | 7 |
| DeepSeek V4.1 Flash | C | 53 | 53 | 24 | 29 |
| Qwen3.8-27B | B | 51 | 51 | 28 | 23 |
| Qwen3.8-27B | C | 27 | 27 | 8 | 19 |

## Verified results

The deterministic audit in [`analysis/verified_test_results.json`](analysis/verified_test_results.json)
recomputes every reported TEST-set quantity from the frozen artifacts without
provider calls. Its reader-facing summary is
[`analysis/verified_test_results.md`](analysis/verified_test_results.md).

On paired common non-abstaining decisions:

- DeepSeek: B 117/124 (94.35%), C 119/124 (95.97%), C - B = +1.61 points.
- Qwen: B 113/115 (98.26%), C 111/115 (96.52%), C - B = -1.74 points.
- Descriptive cross-model total: B and C are each correct on 230/239 (96.23%).

The model-specific effects point in opposite directions. The supported claim is
that no consistent directional advantage was observed; the analysis does not
establish statistical equivalence or prove a null effect.

## Reproduction

```bash
python scripts/audit_heldout_test197_results.py
python scripts/audit_heldout_test197_results.py --write
python scripts/build_test197_verified_report.py
python scripts/build_test197_verified_pdf.py
```

The canonical editable and PDF reports are under [`docs/reports/`](../../docs/reports/).
