# Held-out TEST-50 source-language eligibility

The frozen natural TEST sample contains 50 cases. Source-only QC identified exactly two objective exclusions:

- `726478f13ad8e011c4a0cfa2`: Java syntax in a transition declared C.
- `bda05da230eecfb67fa3a104`: C++ syntax in a transition declared C.

Therefore the frozen sample has **48 eligible `CONFIRMED_C` cases**. The completed Stage-A run used all 50 frozen cases and recorded 44 usable hints plus 6 preserved generation failures. None of those six failures was one of the two language exclusions, so the exact downstream count is:

`50 frozen − 2 language exclusions = 48 eligible C − 6 Stage-A failures = 42 final analyzable natural cases.`

No Qwen B/C run has been performed on TEST-50. The machine-readable calculation is [language_qc_experiment_impact.json](../../data/qc/language_qc_experiment_impact.json).
