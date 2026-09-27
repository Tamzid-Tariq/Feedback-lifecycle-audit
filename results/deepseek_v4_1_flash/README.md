# DeepSeek V4.1 Flash results

This is the completed model-substitution diagnostic using the frozen
Development-50 and Synthetic Stress-20 packets. It does not alter any
reference labels and does not include raw provider responses. Raw per-request
outputs remain in the separate audit workspace; this directory contains the
verified aggregates, parity checks, public run metadata, and hashes.

## Frozen run protocol

- Model: `deepseek/deepseek-v4.1-flash`
- Provider route: OpenRouter Chat Completions
- `max_tokens`: 16,000 for every B/C request
- Temperature: `0`
- `top_p`: not sent, matching the saved Qwen request body
- Timeout: 360 seconds
- Automatic retry: disabled
- Automatic fallback: disabled
- Development calls: 50 B + 50 C
- Stress calls: 20 B + 20 C
- Total primary calls: 140

Dry-run evidence parity passed before provider calls: Development 50/50 and
Stress 20/20. There were 137 accepted outputs and 3 recorded failures. No
recovery pass was performed.

## Main findings

| Dataset | B operational accuracy | C operational accuracy | B/C decision coverage |
|---|---:|---:|---:|
| Development-50 | 48/50 (96%) | 48/50 (96%) | 49/50; 49/50 |
| Stress-20 | 9/20 (45%) | 15/20 (75%) | 9/10; 10/10 |

On Stress-20, C raised RETRACT recall from 70% to 90%, reduced false KEEP
from 10% to 0%, and increased UNSURE handling from 20% to 60%. C also has
one saved decision-rule violation (`STR_011`), represented as an abstention;
this is preserved as a run outcome.

The full comparison is in [comparison_tables.md](comparison_tables.md), and
the complete evaluator outputs are under [`development_50/`](development_50/)
and [`stress_20/`](stress_20/).

Development reference terminology remains bounded: 40 rows are
`human_annotator_consensus` carry-forwards and 10 are
`adjudication_review`; the complete 50-row file is not called expert-human
gold.
