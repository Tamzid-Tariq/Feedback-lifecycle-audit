# Completed versus planned

Status date: 2026-09-29

This file separates completed evidence from work that remains outside the
current empirical scope.

## Verified complete

- CodeStream profiling and problem-disjoint C-language split: 590 development,
  191 validation, and 197 test transitions.
- Development-50 annotation, pre-adjudication reliability, adjudication, and
  GLM/Qwen/DeepSeek diagnostic evaluation.
- Calibration-20 preparation and independent annotation: 16 usable packets,
  zero substantive A01/A02 disagreements, and Rubric v2.0 frozen.
- Synthetic Stress-20 Qwen/DeepSeek diagnostics, maintained separately from
  natural prevalence.
- Full TEST-197 preparation: 188 confirmed-C cases, 9 objective exclusions,
  190 Stage-A calls, 170 accepted hints, 20 preserved failures, and 168 final
  claim-bearing packets.
- TEST-168 independent human annotation: 168 A01 rows and 168 A02 rows.
- Pre-adjudication agreement and disagreement accounting: 24 unique core-field
  disagreements, including 23 lifecycle and one priority-only.
- Qualified blind adjudication of all 24 disagreement cases, frozen separately
  from the unchanged human exports and blind packet.
- Final natural gold: 100 KEEP, 65 RETIRE, 3 RETRACT, 0 UNSURE.
- Four primary Qwen/DeepSeek B/C runs: 168 first attempts each, frozen before
  recovery; 672 first attempts total.
- `RECOVERY_429_V1` for both models and both conditions: exactly one recovery
  attempt per primary HTTP 429, identical fixed pacing, no automatic retry,
  no fallback, and no recovery of non-429 failures.
- Deterministic TEST result verification: all reported counts, agreement
  statistics, lifecycle frequencies, recovery accounting, post-recovery
  metrics, and paired comparisons recomputed from frozen artifacts.
- Canonical editable and PDF reports generated from the verified JSON. The PDF
  passed six-page visual inspection; the DOCX passed a zero-finding structural
  accessibility audit.

## Deliberately outside the completed scope

- No Qwen or DeepSeek B/C model evaluation on Calibration-20.
- No inferential equivalence or null-effect claim for natural B versus C; the
  current paired comparison is descriptive.
- No population-prevalence claim for rare RETRACT/UNSURE labels beyond the
  three-problem natural cohort.
- No learner-outcome, learning-gain, or deployed-tutor-effectiveness claim.
- Stress-20 remains a controlled, single-annotator rare-label diagnostic and
  must not be described as natural adjudicated prevalence.

## Publication boundary

The reproducibility package is self-contained for the final TEST analysis.
Primary and recovery ledgers must remain separate, TEST-197 and TEST-168 naming
must remain explicit, and the correct RQ3 wording is "no consistent directional
advantage observed," not "equivalence established" or "the null was proven."
