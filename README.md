# RevGround: Auditing Programming Feedback Across Code Revisions

RevGround studies whether an earlier diagnostic programming hint remains valid after a learner's next authentic code revision.


## Research Questions

1. How consistently can programming experts distinguish persistent, resolved, incorrect, and indeterminate feedback claims?
2. Under one fixed retrospective hint policy, how often are claims initially incorrect, resolved, persistent, or indeterminate?
3. At comparable decision coverage, how does an execution-grounded verifier compare with a matched-evidence language-model auditor?

## Current Study Status

| Component | Status |
|---|---|
| Data profiling | Complete |
| Development evidence packets | Complete |
| Lifecycle rubric v2.0 | Complete |
| A01 development annotation | 50/50 complete |
| A02 development annotation | 50/50 complete |
| Pre-adjudication comparison | Complete |
| Lifecycle agreement | 48/50 (96%) |
| Lifecycle Cohen's kappa | 0.9228 |
| Adjudication | Complete; final 50-row development reference supplied |
| Source-language QC | Complete; 978 strict-C rows classified from source syntax only; Development-50 and TEST-50 each have 2 objective exclusions; Calibration-20 has 20/20 confirmed C |
| Fresh calibration | 20 validation cases selected; 16 annotation-eligible packets and 4 preserved Stage-A failures |
| Condition B/C development runs | GLM/Qwen history retained; DeepSeek substitution complete; no calibration or held-out Qwen/DeepSeek B/C run |
| Calibration Stage A | 20 validation cases attempted with `stealth/space-bunny-alpha`; 16 usable hints, 4 preserved failures |
| Held-out TEST-50 Stage A | Complete; 50 attempts, 44 usable hints, 6 preserved failures; 48 C-eligible after QC and 42 final analyzable |
| Calibration compiler/test replay | Complete in pinned locked runner; 32 state replays and 450 official test-state entries |
| Calibration annotation | Complete for 16 eligible rows; zero substantive disagreements; no adjudication required |
| Rubric v2.0 | Frozen as final after Calibration-20 |
| DeepSeek V4.1 Flash substitution | Development-50 and Stress-20 complete; 140 primary calls, 137 accepted, 3 preserved failures |
| Held-out natural annotation | Packages released for 42 claim-bearing cases; annotation pending |
| Synthetic Stress-20 | Human review preserved; Qwen B/C results verified and reported separately from natural prevalence |

### Historical pre-adjudication lifecycle disagreements

DEV_010 and DEV_012.

The supplied final reference preserves the historical 48/50 pre-adjudication reliability result and resolves those two cases through adjudication. It contains 40 consensus carry-forwards and 10 `adjudication_review` rows.

See [docs/SUPERVISOR_PROGRESS.md](docs/SUPERVISOR_PROGRESS.md) for the current research checkpoint.
See [docs/EXPERIMENT_STATUS.md](docs/EXPERIMENT_STATUS.md) for the model-condition run status and retention boundary.

## Key Dataset Counts

- 5,482 submissions, 202 participants, and 46 problems
- 3,632 consecutive submission pairs
- Primary language: C
- 978 eligible strict C transitions after duplicate controls
- Development: 590; validation: 191; test: 197
- Development-rubric set: 50; fresh calibration selection: 20 from validation (16 usable annotation packets)
- Source-language QC: 954 `CONFIRMED_C`, 13 `NON_C_CPP`, 9 `NON_C_JAVA`, and 2 `AMBIGUOUS` in the 978-row strict-C pool
- Frozen TEST-50 QC: 48 eligible C cases; after the completed Stage-A failures, 42 natural cases are analyzable

## Repository Guide

- [Study design](docs/study_design.md)
- [Data and sampling](docs/data_and_sampling.md)
- [Raw-data setup and checksums](data/README.md)
- [Annotation layout](annotation/README.md)
- [Supervisor progress](docs/SUPERVISOR_PROGRESS.md)
- [Experiment status](docs/EXPERIMENT_STATUS.md)
- [Condition B baseline](baselines/condition_B/README.md)
- [Condition C audit extension](baselines/condition_C/README.md)
- [Shared condition evaluator](evaluation/normalize_conditions.py)
- [Development results summary](results/development_50/development_results_summary.md)
- [Results highlights](results/RESULTS_HIGHLIGHTS.md)
- [Calibration-20 results](results/calibration_20/README.md)
- [DeepSeek V4.1 Flash results](results/deepseek_v4_1_flash/README.md)
- [Held-out TEST-50 release](results/heldout_test_50/README.md)
- [Synthetic Stress-20 results](results/stress_20/stress_20_results_summary.md)
- [Source-language QC](data/qc/language_qc_summary.json)
- [Development QC sensitivity](results/development_50/language_qc_sensitivity.md)
- [Held-out TEST-50 QC eligibility](results/heldout_test_50/language_qc_eligibility.md)
- [Completed versus planned](docs/COMPLETED_VS_PLANNED.md)
- [Readiness gates](docs/readiness_gates.csv)
- [Supervisor requirements traceability](docs/SUPERVISOR_REQUIREMENTS_TRACEABILITY.csv)
- [Sampling plan](data/sampling_plan.json)
- [Generation policy](docs/generation_policy.json)
- [Model card](docs/model_card.json)
- [Development adjudicator packet](annotation/development_50/RevGround_Adjudicator.html)
- [Reproduction entry points](scripts/)
- [Machine-readable status](artifacts/current_status.json)

## Workflow

1. Profile CodeStream.
2. Select C and construct consecutive transitions.
3. Freeze the problem-disjoint development/validation/test split.
4. Select 50 development cases.
5. Generate hints using S_t evidence only.
6. Build fixed S_t → S_t+1 execution evidence.
7. Freeze annotation packets.
8. Collect two independent development annotations — **complete**.
9. Complete Development-50 adjudication and preserve the historical pre-adjudication result.
10. Complete the validation-based 20-case calibration: 16 usable packets were independently annotated; four Stage-A failures were preserved.
11. Freeze Rubric v2.0 after calibration; no rubric change was required.
12. Release the label-independent held-out natural annotation packages for the 42 eligible claim-bearing TEST cases.
13. Report DeepSeek and Synthetic Stress-20 diagnostics separately from natural prevalence results.
14. Apply source-language QC before annotation or held-out analysis; preserve objective exclusions.
15. Keep final Qwen/DeepSeek B/C evaluation on Calibration-20 and held-out TEST outside the completed scope.

## Important Scope

Hints are retrospective and were not shown to learners. The study evaluates feedback-state validity and tutor bookkeeping; it does not measure feedback uptake, learning gains, or deployed-tutor effectiveness.

## Quick Check

```bash
python -m unittest discover -s tests -v
```

The original CodeStream dataset is not redistributed here. See [data/README.md](data/README.md) for the source record, licence note, expected local paths, and SHA-256 values.
