# Development-50 source-language QC sensitivity

The original Development-50 reliability result is preserved: lifecycle agreement was **48/50 (96%)**, with Cohen's κ = **0.9228**. The source-language QC is an additional objective eligibility analysis; it does not rewrite that historical result.

The QC identified `DEV_010` as Java syntax and `DEV_012` as C++ syntax despite both being declared C. Excluding those two objective language-mismatch cases leaves 48 eligible C cases:

| Construct | Agreement after exclusion | Cohen's κ |
|---|---:|---:|
| Original validity | 48/48 | 1.0000 |
| Target state | 48/48 | 1.0000 |
| Lifecycle | 48/48 | 1.0000 |
| Instructional priority | 44/48 | 0.8310 |
| Leakage | 44/48 | 0.0000 |
| Joint agreement across all five fields | 40/48 | — |

The full machine-readable calculation is [language_qc_experiment_impact.json](../../data/qc/language_qc_experiment_impact.json). The primary 48/50 lifecycle result remains the reportable pre-adjudication Development-50 result; this table is a sensitivity analysis.
