# RevGround annotation layout

The annotation tree is partitioned by study phase while shared rubric material is kept in `common/`.

- `common/`: shared schema, field definitions, rubric, reason codes, and annotator blinding guidance.
- `development_50/`: frozen Development-50 packet, unchanged A01/A02 exports, and adjudication materials.
- `calibration_20/`: blinded validation-based calibration packet and isolated A01/A02 HTML tools. It contains no model results, labels, adjudication data, or annotation exports.
- `stress_20/`: preserved A02 human-review CSV for the completed Synthetic Stress-20 diagnostic; it is not an independent consensus or adjudicated gold package.
- `heldout_test_50/`: reserved held-out-test annotation location; no test access or annotation has been performed.

The calibration package contains the 16 annotation-eligible packets from a deterministic 20-case validation selection. Four Stage-A generation failures remain preserved in `results/calibration_20/` and were not replaced.
