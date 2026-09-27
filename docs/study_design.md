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

The 50-case development set supports rubric refinement. Two annotators label it independently before discussion, and the supplied final reference contains 40 consensus carry-forwards plus 10 `adjudication_review` rows. The fresh calibration selection is 20 cases sampled deterministically from the validation partition before labels are read. Source-language QC is applied from code syntax only before annotation or held-out analysis. Stage-A generation attempted all 20 calibration cases with the frozen S_t-only protocol; 16 hints were usable and four failures were preserved. A01 and A02 independently annotated the 16 eligible cases; all five decision fields agreed, so no adjudication was required and Rubric v2.0 was frozen. The historical TEST-50 Stage-A run remains preserved as Batch 1. A protocol amendment then froze the complete 197-case TEST partition: 188 cases are confirmed C after nine objective language exclusions, 140 remaining eligible cases received one frozen Stage-A call each, and 14 new failures were preserved. Combined with Batch 1, 168 successful C claim-bearing packets remain after 20 total Stage-A failures, with a profile of 168 cases, 3 problems, 49 trajectories, and 42 participants. Isolated A01/A02 packages are prepared, but natural annotation and all Qwen/DeepSeek B/C held-out runs remain pending.

The separate Synthetic Stress-20 set is a controlled rare-label diagnostic derived from development packets. Its completed human review contains 10 `RETRACT` and 10 `UNSURE` cases from one annotator (`A_02`), not an independent consensus or adjudicated gold set. Qwen B/C results for this set are reported separately and are not used for natural prevalence estimates.

Method comparisons must preserve identical claim sets and record abstention separately from predicted UNSURE. Evaluation emphasizes decision coverage, false KEEP decisions on RETIRE/RETRACT gold cases, wrongful removal of KEEP cases, selective risk, and per-class descriptive results.
