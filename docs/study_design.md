# Study Design

## Bounded contribution

RevGround audits the lifecycle status of an earlier diagnostic programming claim across an authentic adjacent code revision, using fixed claim-specific evidence and independently adjudicated human labels.

## Research questions

1. How consistently can programming experts distinguish persistent, resolved, incorrect, and indeterminate feedback claims, and what explains disagreement?
2. Under one fixed retrospective hint-generation policy, how often are claims initially incorrect, resolved after the next revision, persistent, or indeterminate?
3. At comparable decision coverage, how does an execution-grounded verifier differ from a matched-evidence language-model auditor in unsafe retention, wrongful removal, abstention, and execution cost?

The RQ3 hypothesis—that the execution-grounded verifier will make fewer unsafe KEEP decisions without excessive abstention—is a prediction, not a result.

## Scope

- Dataset: CodeStream
- Primary language: C
- Unit of analysis: one focal diagnostic claim over an adjacent S_t → S_t+1 submission pair
- Hint condition: one fixed retrospective generator and prompt using S_t information only
- Lifecycle labels: KEEP, RETIRE, RETRACT, and UNSURE
- Independent constructs: original validity, target state at S_t+1, instructional priority, and leakage when evaluated

Hints were not shown to learners and did not cause the observed revisions. Claims are therefore limited to feedback-state validity and tutor bookkeeping, not learner behaviour or learning effects.

## Annotation and evaluation sequence

The 50-case development set supports rubric refinement. Two annotators label it independently before discussion. A fresh disjoint 25-case calibration set is the post-revision reliability gate. Validation contains the natural 191-case census. The 197-case final test remains locked until the rubric and methods are frozen and access is authorized.

Method comparisons must preserve identical claim sets and record abstention separately from predicted UNSURE. Evaluation emphasizes decision coverage, false KEEP decisions on RETIRE/RETRACT gold cases, wrongful removal of KEEP cases, selective risk, and per-class descriptive results.
