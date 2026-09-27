# Model comparison tables

These tables combine the newly evaluated DeepSeek primary pass with the already
reported GLM/Qwen aggregates. Development is a diagnostic reference set: its
50 rows contain 40 `human_annotator_consensus` carry-forwards and 10
`adjudication_review` rows. Stress-20 is a separate one-annotator human-review
diagnostic, not a natural prevalence estimate.

## Development-50

| Model | B operational accuracy | C operational accuracy | Δ C−B | False KEEP B/C | Decision coverage B/C | Total tokens B/C |
|---|---:|---:|---:|---:|---:|---:|
| GLM-5.3 | 50/50 (100%) | 50/50 (100%) | 0 pp | 0/29; 0/29 | 50/50; 50/50 | 427,473; 471,839 |
| Qwen3.8-27B | 48/50 (96%) | 46/50 (92%) | −4 pp | 0/29; 0/29 | 48/50; 47/50 | 537,456; 593,601 |
| **DeepSeek V4.1 Flash** | **48/50 (96%)** | **48/50 (96%)** | **0 pp** | **0/29; 0/29** | **49/50; 49/50** | **430,082; 452,408** |

The Qwen rows are the previously verified primary/operational aggregates;
their original B/C output-budget mismatch remains a documented development
caveat. DeepSeek used the common 16,000-token request setting for both
conditions, with no recovery pass.

## Controlled Stress-20

Operational accuracy counts a matching lifecycle label on the attempted set;
explicit abstention is also reported separately. RETRACT recall, false KEEP,
and UNSURE handling use the same frozen evaluator definitions as the detailed
JSON output.

| Model | B accuracy | C accuracy | RETRACT recall B→C | False KEEP B→C | UNSURE handling B→C |
|---|---:|---:|---:|---:|---:|
| Qwen3.8-27B | 14/20 (70%) | 16/20 (80%) | 80%→100% | 10%→0% | 60%→60% |
| **DeepSeek V4.1 Flash** | **9/20 (45%)** | **15/20 (75%)** | **70%→90%** | **10%→0%** | **20%→60%** |

DeepSeek Stress-20 B/C details: accepted/attempted 19/20 and 20/20;
decision coverage 9/10 and 10/10; selective risk 2/9 and 1/10; explicit
model abstentions 0 and 6; RETRACT precision 7/11 and 9/12; RETRACT F1
66.7% and 81.8%; decision-rule violations 0 and 1. The single C violation
is `STR_011`, recorded as an abstention. The full four-label non-abstaining matrices are in
`development_50/confusion_matrices.csv` and
`stress_20/confusion_matrices.csv`.

## Failure and abstention outcomes

| Dataset/condition | Item | Preserved outcome |
|---|---|---|
| Development B | `DEV_024` | HTTP 200, non-string provider response; no usable prediction |
| Development C | `DEV_024` | HTTP 200, unsupported evidence ID; validator rejection/system abstention |
| Stress B | `STR_008` | HTTP 200, non-string provider response; no usable prediction |
| Stress C | six cases | accepted explicit model abstentions: `STR_002`, `STR_011`, `STR_013`, `STR_014`, `STR_016`, `STR_018` |

No HTTP-status failure, schema-violation, or length/truncation outcome occurred
in this primary pass. No additional provider calls were made.
