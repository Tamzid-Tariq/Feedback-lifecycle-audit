# Synthetic Stress-20 Results

## Scope and reference labels

This is a controlled rare-label stress set derived from the existing development packets. It is not part of the natural CodeStream prevalence estimate and must be reported separately.

The metrics below were independently recomputed from the retained B/C outputs against the supplied human-review CSV. The labels match the construction-intended 10/10 split, but the file itself is one-annotator review and not adjudicated consensus.

The preserved human-review file is [synthetic_stress_20_human_review.csv](../../annotation/stress_20/synthetic_stress_20_human_review.csv). It contains one completed review by annotator `A_02`: 10 `RETRACT` and 10 `UNSURE` labels. These are human-reviewed labels, not an independent A01/A02 consensus or adjudicated gold set.

## Qwen B/C results

Both conditions used the same 20 packets and the same frozen settings: `qwen/qwen3.8-27b`, `max_tokens=16000`, 360-second timeout, fallback disabled, and the same provider/routing and error policy.

| Metric | Condition B | Condition C |
|---|---:|---:|
| Completed outputs | 19/20 | 20/20 |
| Operational accuracy | 14/20 (70.0%) | 16/20 (80.0%) |
| RETRACT precision | 8/11 (72.7%) | 10/13 (76.9%) |
| RETRACT recall | 8/10 (80.0%) | 10/10 (100.0%) |
| RETRACT F1 | 0.762 | 0.870 |
| UNSURE precision | 100.0% | 100.0% |
| UNSURE recognition | 6/10 (60.0%) | 6/10 (60.0%) |
| UNSURE F1 | 0.750 | 0.750 |
| False KEEP on reviewed RETRACT | 1/10 (10.0%) | 0/10 (0.0%) |
| Selective risk on decidable RETRACT cases | 2/10 (20.0%) | 0/10 (0.0%) |

### Fair paired comparison

On the 19 cases with outputs from both methods:

- B: 14/19 correct (73.7%).
- C: 16/19 correct (84.2%).
- B/C lifecycle agreement: 17/19 (89.5%).
- Difference favoring C: +10.5 percentage points.
- C corrected B's two RETRACT misses: `STR_005` and `STR_008`.
- Both methods missed the same three UNSURE cases as RETRACT: `STR_006`, `STR_010`, and `STR_012`.
- `STR_020` was B's unusable-output case; C returned `KEEP` against the human-reviewed `UNSURE` label.

## Experimental controls and efficiency

- Model requested in both: `qwen/qwen3.8-27b`.
- Maximum output tokens: 16,000 in both.
- Evidence SHA match: 20/20 (100%).
- Forbidden reference fields: none.
- Condition C decision-rule violations: 0.
- Condition C packet-validation abstentions: 0.
- Mean latency: B 102.8 seconds/call; C 74.1 seconds/call.
- Total tokens: B 200,664; C 170,982.
- Errors: B 1; C 0.

Condition C used 14.8% fewer tokens and had 27.9% lower mean latency in this run.

## Interpretation boundary

On this controlled rare-label stress set, C improved operational accuracy and RETRACT recall and eliminated false KEEP on reviewed RETRACT cases. UNSURE recognition remained 60% in both conditions, so the structured audit helped more with directly refutable claims than with evidence-insufficiency cases. These results do not estimate authentic CodeStream RETRACT/UNSURE prevalence.

The raw provider outputs remain in the local supervisor workspace; this repository records the human-review file, the verified aggregate results, and the interpretation boundary.
