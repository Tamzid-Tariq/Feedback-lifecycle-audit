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
| Adjudication | Pending |
| Fresh calibration | Validation-based 20-case selection prepared; 16 annotation-eligible packets and 4 preserved Stage-A failures |
| Condition B/C development runs | Existing development artifacts retained; no calibration or held-out Qwen B/C run |
| Calibration Stage A | 20 validation cases attempted with `stealth/space-bunny-alpha`; 16 usable hints, 4 preserved failures |
| Calibration compiler/test replay | Not performed; packet fields are explicitly marked `NOT_REPLAYED` |
| Calibration annotation | Not started |
| Synthetic Stress-20 | Human review preserved; Qwen B/C results verified and reported separately from natural prevalence |

### Current lifecycle disagreements

DEV_010 and DEV_012.

See [docs/SUPERVISOR_PROGRESS.md](docs/SUPERVISOR_PROGRESS.md) for the current research checkpoint.
See [docs/EXPERIMENT_STATUS.md](docs/EXPERIMENT_STATUS.md) for the model-condition run status and retention boundary.

## Key Dataset Counts

- 5,482 submissions, 202 participants, and 46 problems
- 3,632 consecutive submission pairs
- Primary language: C
- 978 eligible strict C transitions after duplicate controls
- Development: 590; validation: 191; test: 197
- Development-rubric set: 50; fresh calibration selection: 20 from validation (16 usable annotation packets)

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
- [Synthetic Stress-20 results](results/stress_20/stress_20_results_summary.md)
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
9. Adjudicate development disagreements and review the rubric — **current milestone**.
10. Begin the validation-based 20-case calibration using the isolated A01/A02 package.
11. Freeze the final protocol.
12. Report the completed Synthetic Stress-20 diagnostic separately from natural results.
13. Do not run Qwen B/C on calibration or held-out TEST until separately authorized.

## Important Scope

Hints are retrospective and were not shown to learners. The study evaluates feedback-state validity and tutor bookkeeping; it does not measure feedback uptake, learning gains, or deployed-tutor effectiveness.

## Quick Check

```bash
python -m unittest discover -s tests -v
```

The original CodeStream dataset is not redistributed here. See [data/README.md](data/README.md) for the source record, licence note, expected local paths, and SHA-256 values.
