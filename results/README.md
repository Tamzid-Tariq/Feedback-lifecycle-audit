# Results layout

- `development_50/`: derived development agreement and technical result summaries.
- `calibration_20/`: validation-selection manifest, Stage-A/Stage-B audit, frozen rubric status, and completed A01/A02 pre-adjudication exports.
- `stress_20/`: verified human-reviewed rare-label diagnostic and aggregate Qwen B/C results.
- `heldout_test_50/`: frozen natural TEST-50 eligibility accounting and release manifest for the 42-case A01/A02 annotation packages; no B/C run.
- `deepseek_v4_1_flash/`: verified DeepSeek V4.1 Flash Development-50 and Stress-20 substitution aggregates, parity checks, run metadata, and hashes.

Completed calibration annotation exports are retained under `calibration_20/annotator_exports/`; the blinded annotation packet under `annotation/calibration_20/` remains label-free.

The current result highlights and update-specific hashes are in `RESULTS_HIGHLIGHTS.md` and `RESULTS_HIGHLIGHTS.SHA256SUMS`.
