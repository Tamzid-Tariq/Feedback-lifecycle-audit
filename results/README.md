# Results layout

- `development_50/`: derived development agreement and technical result summaries.
- `calibration_20/`: validation-selection manifest, Stage-A/Stage-B audit, frozen rubric status, and completed A01/A02 pre-adjudication exports.
- `stress_20/`: verified human-reviewed rare-label diagnostic and aggregate Qwen B/C results.
- `heldout_test_50/`: frozen natural TEST-50 eligibility accounting and release manifest for the 42-case A01/A02 annotation packages; no B/C run.
- `heldout_test_197/`: complete TEST-197 source-cohort and TEST-168 analytic
  package, including frozen human exports, blind and final adjudication,
  Qwen/DeepSeek primary and recovery ledgers, and verified natural results.
- `deepseek_v4_1_flash/`: verified DeepSeek V4.1 Flash Development-50 and Stress-20 substitution aggregates, parity checks, run metadata, and hashes.

Completed calibration annotation exports are retained under `calibration_20/annotator_exports/`; the blinded annotation packet under `annotation/calibration_20/` remains label-free.

The current result highlights are in `RESULTS_HIGHLIGHTS.md`. The final held-out
machine-readable audit is in
`heldout_test_197/analysis/verified_test_results.json`, and publication-facing
reports are under `docs/reports/`.
