# RevGround annotation layout

The annotation tree is partitioned by study phase while shared rubric material is kept in `common/`.

- `common/`: shared schema, field definitions, rubric, reason codes, and annotator blinding guidance.
- `development_50/`: frozen Development-50 packet, unchanged A01/A02 exports, and adjudication materials.
- `calibration_20/`: frozen validation-based calibration packet and isolated A01/A02 HTML tools. Completed annotation exports are retained under `results/calibration_20/annotator_exports/`; this packet directory remains label-free.
- `stress_20/`: preserved A02 human-review CSV for the completed Synthetic Stress-20 diagnostic; it is not an independent consensus or adjudicated gold package.
- `heldout_test_50/`: released A01/A02 packages for the 42 successful C claim-bearing cases from the frozen TEST-50 cohort. The packages contain only the frozen evidence packet, rubric, and annotator HTML; no labels, predictions, or adjudication information.

The calibration package contains the 16 annotation-eligible packets from a deterministic 20-case validation selection. A01 and A02 agree on all five decision fields, so `rubric_change_required = false` and no adjudication was performed. Four Stage-A generation failures remain preserved in `results/calibration_20/` and were not replaced.
