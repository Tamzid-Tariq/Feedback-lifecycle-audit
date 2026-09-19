# RevGround lifecycle rubric v2.0

## Unit of analysis

One fixed focal diagnostic claim from one unedited retrospective hint, audited from S_t to the next authentic submission S_t+1. Preserve the original hint, claim span, target, time, and scope.

## Label separately

1. Original validity at S_t: **SUPPORTED**, **REFUTED**, or **INDETERMINATE**.
2. Target state at S_t+1: **PRESENT**, **RESOLVED**, **INDETERMINATE**, or **NOT_APPLICABLE** when the original claim is refuted.
3. Instructional priority at S_t+1: **HIGH**, **LOW**, or **UNKNOWN**. Priority never changes the factual lifecycle label.
4. Hint leakage, when assigned: **ABSENT**, **PRESENT**, or **NOT_EVALUATED**. Leakage never changes validity, target state, or lifecycle.

## Lifecycle mapping

- **KEEP:** original claim SUPPORTED and the same target PRESENT at S_t+1.
- **RETIRE:** original claim SUPPORTED and the same target RESOLVED at S_t+1.
- **RETRACT:** original claim REFUTED and target state NOT_APPLICABLE.
- **UNSURE:** the claim is ambiguous, evidence conflicts, or the admissible packet cannot support another label.

## Evidence rules

A compile error is a compiler finding; an infrastructure timeout is not. A completed FAIL differs from PROGRAM_TIMEOUT, RUNTIME_ERROR, INFRA_TIMEOUT, and NOT_RUN_COMPILE_ERROR. A failing test proves failure on that input but does not by itself prove the claimed cause. Passing finite tests support only claims within their tested scope. Stored judge traces are contextual evidence. Code movement alone does not prove resolution.

Select the evidence IDs actually used, rate confidence from 1 to 5, and provide a short reason. If the exact claim cannot be decided from the fixed packet, use an indeterminate choice and UNSURE rather than guessing.

## Blinding

Do not use model/provider identity, method predictions, or another annotator's labels. These values are intentionally absent from the annotator packets.
