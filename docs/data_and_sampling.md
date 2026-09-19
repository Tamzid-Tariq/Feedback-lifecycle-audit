# Data and Sampling

## Source and profile

The study uses the CodeStream dataset: 5,482 submissions from 202 participants over 46 programming problems. These form 1,848 participant–problem trajectories and 3,632 consecutive submission pairs with usable evidence.

C was selected as the primary language using a frozen rule balancing edited-transition volume with problem and participant diversity. After eligibility checks and cross-partition duplicate controls, 978 strict C transitions remain.

## Problem-disjoint split

| Partition | Transitions | Trajectories | Participants | Problems | Problem families |
|---|---:|---:|---:|---:|---:|
| Development | 590 | 220 | 84 | 19 | 16 |
| Validation | 191 | 76 | 54 | 5 | 4 |
| Test | 197 | 57 | 49 | 5 | 4 |

Problems and near-duplicate problem families are assigned atomically. This is not a random row split. Seventeen cross-partition code-duplicate transitions were removed, and the audited split has no near-duplicate problem-family violations.

## Research subsets

- Development-rubric set: 50 cases for definition and interface refinement
- Fresh calibration: 25 disjoint cases for the post-revision reliability gate
- Validation census: 191 transitions
- Final test census: 197 transitions, locked
- Conditional long-horizon extension: 20 reserved development trajectories

The development 50 is deliberately varied and is not a prevalence sample. Natural lifecycle-frequency claims belong to the later census partitions after the protocol is frozen.

Authoritative manifests are in [`data/manifests/`](../data/manifests/). Raw-data setup and checksums are documented in [`data/README.md`](../data/README.md).
