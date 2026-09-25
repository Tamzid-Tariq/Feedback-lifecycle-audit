# Experiment Status

Updated: 2026-09-25

## Current state

The frozen 50-item development evidence set has been evaluated under both primary model conditions.

| Component | Status |
|---|---|
| Frozen development evidence packets | Complete |
| Condition B GLM-5.3 baseline | Complete; canonical 50-record output retained in the local audit workspace |
| Condition C controlled extension | Complete; 50/50 accepted outputs |
| Shared B/C evaluator | Complete |
| Matched evidence verification | Complete; 50/50 TRUE |
| C packet validation | Complete; 50/50 passed |
| C lifecycle decision validation | Complete; 0 violations |
| Adjudicated human gold | Pending |
| Validation/test-scale evaluation | Not started |

## Conditions

Condition B receives the frozen evidence packet and returns a lifecycle prediction. Condition C receives the same projected packet, applies deterministic evidence checks, follows the explicit RevGround decision procedure, and validates the returned lifecycle decision after the model response.

Both conditions enter the evaluator through the same normalized schema. B is represented as non-selective (`abstain=false`); C preserves abstention and final-action information.

## Development result

Condition C produced 50 accepted outputs with no errors, no packet abstentions, and no decision-rule violations. Its lifecycle distribution was `KEEP=21`, `RETIRE=29`. The B/C evidence hash comparison matched all 50 items.

These are technical development results only. They do not establish agreement or accuracy against A01/A02 or adjudicated gold labels.

## Reproducibility and retention

The repository contains the runners, prompts, evaluator, and aggregate summaries. Raw provider responses and per-run output trees are intentionally kept outside the public repository in the local audit workspace.

See:

- [Condition C README](../baselines/condition_C/README.md)
- [Development results summary](../artifacts/development_results_summary.md)
- [Matched evidence summary](../artifacts/matched_evidence_summary.json)
- [Supervisor progress](SUPERVISOR_PROGRESS.md)
