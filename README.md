# RevGround: Auditing Programming Feedback Across Code Revisions

RevGround studies whether an earlier diagnostic programming hint remains valid after a learner's next authentic code revision.


## Research Questions

1. How consistently can programming experts distinguish persistent, resolved, incorrect, and indeterminate feedback claims?
2. Under one fixed retrospective hint policy, how often are claims initially incorrect, resolved, persistent, or indeterminate?
3. At comparable decision coverage, how does an execution-grounded verifier compare with a matched-evidence language-model auditor?

## Current Status — 19 September 2026

| Stage | Status |
|---|---|
| CodeStream profiling | Complete |
| Primary language selection: C | Complete |
| Problem-disjoint split | Complete |
| 50-item development set | Complete |
| Development-only hint generation and claim preparation | Complete |
| Development execution evidence | Complete |
| Annotation package | Prepared |
| Independent human annotation | Pending |
| Fresh 25-case calibration | Next |
| Validation comparison | Not run |
| Final test | Locked / not run |

No human gold lifecycle labels, method predictions, or research performance results are claimed. See [STATUS.md](STATUS.md) for the evidence behind each state.

## Key Dataset Counts

- 5,482 submissions, 202 participants, and 46 problems
- 3,632 consecutive submission pairs
- Primary language: C
- 978 eligible strict C transitions after duplicate controls
- Development: 590; validation: 191; test: 197
- Development-rubric set: 50; fresh calibration set: 25

## Repository Guide

- [Study design](docs/study_design.md)
- [Data and sampling](docs/data_and_sampling.md)
- [Raw-data setup and checksums](data/README.md)
- [Human annotation](annotation/README.md)
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
8. Collect two independent human annotations — **current milestone**.
9. Run the fresh 25-case calibration and freeze the protocol.
10. Evaluate validation, then access the final test only after authorization.

## Important Scope

Hints are retrospective and were not shown to learners. The study evaluates feedback-state validity and tutor bookkeeping; it does not measure feedback uptake, learning gains, or deployed-tutor effectiveness.

## Quick Check

```bash
python -m unittest discover -s tests -v
```

The original CodeStream dataset is not redistributed here. See [data/README.md](data/README.md) for the source record, licence note, expected local paths, and SHA-256 values.
