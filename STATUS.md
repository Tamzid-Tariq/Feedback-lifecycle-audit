# Project Status

## Current milestone — Annotation Ready (19 September 2026)

Dataset profiling, C-language selection, problem-disjoint partitioning, development-50 construction, development-only hint generation, claim preparation, and execution-evidence preparation are complete. The 50-case human annotation package is frozen and ready. Independent A01/A02 annotation and adjudication have not been completed, so no human gold lifecycle labels or research performance results are claimed.

| Work item | State | Evidence |
|---|---|---|
| Dataset profiling | Complete | [`artifacts/dataset_profile_v2.json`](artifacts/dataset_profile_v2.json) |
| Language selection | Complete: C | [`docs/data_and_sampling.md`](docs/data_and_sampling.md) |
| Problem-disjoint split | Complete | [`data/manifests/split_summary.csv`](data/manifests/split_summary.csv) |
| Development-50 selection | Complete | [`data/manifests/rubric_development_50_manifest.csv`](data/manifests/rubric_development_50_manifest.csv) |
| Development hint generation | Complete for development only | [`artifacts/generation_summary.json`](artifacts/generation_summary.json) |
| Claim recovery/amendment | Complete | [`artifacts/recovery_summary.json`](artifacts/recovery_summary.json) |
| Execution evidence | Complete for development 50 | [`annotation/development_50_evidence_frozen_v1.jsonl`](annotation/development_50_evidence_frozen_v1.jsonl) |
| Annotation interface | Complete | [`annotation/tools/`](annotation/tools/) |
| Annotator A labels | Pending | — |
| Annotator B labels | Pending | — |
| Adjudication | Pending | — |
| Fresh calibration 25 | Prepared, not labelled | [`data/manifests/fresh_calibration_25_manifest.csv`](data/manifests/fresh_calibration_25_manifest.csv) |
| Validation 191 | Not evaluated | [`data/manifests/main_validation_191_manifest.csv`](data/manifests/main_validation_191_manifest.csv) |
| Test 197 | Locked / not evaluated | [`data/manifests/final_test_197_manifest.csv`](data/manifests/final_test_197_manifest.csv) |

The six amended development positions are documented in `artifacts/recovery_summary.json`. They use source-grounded curated replacement hints; they are not silently represented as provider-generated outputs.

`artifacts/current_status.json` is the machine-readable source of truth. Superseded progress narratives from the working archive are intentionally not included.
