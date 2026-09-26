
# Annotation workflow

Two trained programming annotators label independently. They see the task, S_t, S_t+1, the unedited hint, exact focal claim, textual diff, and one fixed evidence packet. They do not see generator/model identity, method predictions, or each other's ratings. Randomize order using the recorded packet seed. Preserve both initial files unchanged before discussion. A supervisor or another qualified adjudicator resolves disagreements; uncertainty remains a valid adjudicated outcome.

Use 50 deliberately varied development cases to improve the rubric. Measure minutes and disagreement reasons. Then use a fresh 20-case validation calibration set selected before labels. If more than 20% of eligible fresh cases require changing a label definition, pause scale-up and simplify the construct. This is an internal gate, not a universal validity threshold. Report pre-adjudication raw agreement, nominal unweighted Cohen kappa, the rater confusion matrix, label marginals, per-label agreement, missing ratings and uncertainty intervals when justified. Never report adjudicated agreement as reliability.
