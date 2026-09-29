# Verified held-out TEST results

## Scope and verdict

The source partition is **TEST-197**. After objective language exclusions and
preserved Stage-A failures, the claim-bearing analytic cohort is **TEST-168**.
Every numerical TEST-set result in the audited report recomputes from the frozen
repository artifacts. No false quantitative result was detected.

This is a deterministic, no-provider-call audit. Primary failures remain
failures; only separately recorded `RECOVERY_429_V1` predictions are combined
with primary accepted outputs.

## Human annotation and final gold

- A01/A02 rows: 168 each.
- Unique core-field disagreements: 24
  (23 lifecycle; 1 priority-only).
- Original-validity agreement: 161/168,
  kappa 0.2170.
- Target-state agreement: 145/168,
  kappa 0.7249.
- Lifecycle agreement: 145/168,
  kappa 0.7249.
- Priority agreement: 144/168,
  kappa 0.7117.
- All four core fields agree on 144/168.
- Final gold: 100 KEEP,
  65 RETIRE,
  3 RETRACT,
  0 UNSURE.

## Post-recovery model results

| Model | Condition | Usable | Abstain | Decisions | Correct | Accuracy | False KEEP | Wrongful removal |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| DeepSeek | B | 154 | 0 | 154 | 146 | 94.81% | 1 | 6 |
| DeepSeek | C | 135 | 3 | 132 | 127 | 96.21% | 0 | 5 |
| Qwen | B | 136 | 0 | 136 | 133 | 97.79% | 0 | 3 |
| Qwen | C | 141 | 4 | 137 | 132 | 96.35% | 1 | 4 |

## Paired comparisons

| Model | Paired n | B correct | C correct | B accuracy | C accuracy | C-B |
|---|---:|---:|---:|---:|---:|---:|
| DeepSeek | 124 | 117 | 119 | 94.35% | 95.97% | +1.61 pp |
| Qwen | 115 | 113 | 111 | 98.26% | 96.52% | -1.74 pp |

Across the 239 paired model-case
comparisons, B and C are each correct on 230
(96.23%); both are correct on the
same case in 228 comparisons.
The model-specific effects have opposite signs, so the supported interpretation
is **no consistent directional advantage observed**. This audit does not
establish statistical equivalence or prove a null effect.

## Provenance boundary

- The blind adjudication packet remains unchanged under `adjudication_24_blind_v1/`.
- The completed return is frozen separately under `adjudication_24_final_v1/`.
- The four 168-attempt primary runs remain separate from both models' recovery namespaces.
- Recovery was limited to exactly one attempt per primary HTTP 429; non-429 failures were not recovered.
