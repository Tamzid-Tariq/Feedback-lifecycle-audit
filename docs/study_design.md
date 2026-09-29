# Study Design

## Bounded contribution

RevGround audits the lifecycle status of an earlier diagnostic programming
claim across an authentic adjacent code revision, using fixed claim-specific
evidence and independently adjudicated human labels.

## Research questions

1. How consistently can programming experts distinguish persistent, resolved,
   incorrect, and indeterminate feedback claims, and what explains disagreement?
2. Under one fixed retrospective hint-generation policy, how often are claims
   initially incorrect, resolved after the next revision, persistent, or
   indeterminate?
3. At comparable decision coverage, how does an execution-grounded verifier
   differ from a matched-evidence language-model auditor in unsafe retention,
   wrongful removal, abstention, and execution cost?

The RQ3 hypothesis - that the execution-grounded verifier would make fewer
unsafe KEEP decisions without excessive abstention - was specified as a
prediction. Final natural results are reported as descriptive paired estimates,
not as a claim of statistical equivalence.

## Scope

- Dataset: CodeStream.
- Primary language: C.
- Unit of analysis: one focal diagnostic claim over an adjacent S_t to S_t+1
  submission pair.
- Hint condition: one fixed retrospective generator and prompt using S_t
  information only.
- Lifecycle labels: KEEP, RETIRE, RETRACT, and UNSURE.
- Independent constructs: original validity, target state at S_t+1,
  instructional priority, and leakage when evaluated.

Hints were not shown to learners and did not cause the observed revisions.
Claims are therefore limited to feedback-state validity and tutor bookkeeping,
not learner behaviour or learning effects.

## Annotation and evaluation sequence

The 50-case development set supports rubric refinement. Two annotators label it
independently before discussion, and the supplied final reference contains 40
consensus carry-forwards plus 10 `adjudication_review` rows.

Calibration-20 was sampled deterministically from validation before labels were
read. Sixteen hints were usable, four failures were preserved, A01 and A02
agreed on all eligible cases, and Rubric v2.0 was frozen without calibration
adjudication.

Historical TEST-50 remains Batch 1 of the complete 197-case TEST partition.
Source-only QC preserves nine language exclusions; 190 Stage-A calls yield 170
accepted hints and 20 failures, leaving 168 claim-bearing packets across 3
problems, 49 trajectories, and 42 participants.

A01 and A02 independently annotated all 168 packets. Their 24 unique core-field
disagreements were sent to a qualified adjudicator using only the blind frozen
evidence packet. The returned decisions are frozen separately and produce final
gold of 100 KEEP, 65 RETIRE, 3 RETRACT, and 0 UNSURE.

Qwen and DeepSeek each received one frozen primary attempt on all 168 packets
under Conditions B and C. After all four primary runs were frozen, the separate
`RECOVERY_429_V1` namespace recorded exactly one recovery attempt for each
primary HTTP 429. Non-429 failures were not recovered and primary files were
not overwritten. Final paired comparisons use common non-abstaining decisions.

The separate Synthetic Stress-20 set is a controlled rare-label diagnostic
derived from development packets. Its completed human review contains 10
`RETRACT` and 10 `UNSURE` cases from one annotator (`A_02`), not an independent
consensus or adjudicated gold set. Stress results are reported separately and
do not alter natural prevalence estimates.

Method comparisons preserve identical claim sets and record explicit
abstention separately from predicted UNSURE. Evaluation emphasizes decision
coverage, false KEEP decisions on RETIRE/RETRACT gold cases, wrongful removal
of KEEP cases, selective risk, and per-class descriptive results.
