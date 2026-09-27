
# RevGround lifecycle rubric v2.0

## Unit of analysis
One focal diagnostic claim from one unedited retrospective hint, audited from submission S_t to the next authentic submission S_t+1. Preserve the hint, exact claim span, target, time and scope. Questions, general encouragement and advice with no factual diagnosis are screened as non-diagnostic and retained in the flow denominator.

## Rate three constructs separately
1. Original validity at S_t: SUPPORTED, REFUTED, or INDETERMINATE.
2. Target state at S_t+1: PRESENT, RESOLVED, or INDETERMINATE.
3. Instructional priority at S_t+1: HIGH, LOW, or UNKNOWN. Priority never changes the factual lifecycle label.

## Derived lifecycle label
- RETRACT: admissible, claim-specific evidence refutes the original diagnosis or a substantive assertion in its stated scope.
- KEEP: the original diagnosis is supported and the same target remains present at S_t+1.
- RETIRE: the original diagnosis is supported and sufficiently specific evidence shows the target is resolved at S_t+1.
- UNSURE: the claim is too ambiguous, evidence conflicts, or admissible evidence cannot support another label.

## Decision order
1. Can the claim be interpreted and mapped to a target? If no, UNSURE.
2. Does claim-specific evidence refute the original diagnosis? If yes, RETRACT.
3. Is the original claim adequately supported? If no or evidence conflicts, UNSURE.
4. Does the same faulty behavior persist, including after relocation or refactoring? If yes, KEEP.
5. Is the same target resolved under sufficiently specific evidence? If yes, RETIRE.
6. Otherwise, UNSURE.

## Evidence limits
A program failure witness proves a failure on an input; it does not by itself prove or refute the claimed cause. A claim witness must address the exact diagnosis. Passing a finite suite supports only claims within its tested scope. Stored CodeStream traces are contextual evidence until replayed and validated. Code movement alone never proves resolution. Record the evidence IDs and a reason code.

## Gold uncertainty and model abstention
Gold UNSURE means trained experts cannot decide from the admissible packet. A system abstention is stored in a separate field and may occur even when experts can decide. Never convert abstention automatically into predicted UNSURE.
