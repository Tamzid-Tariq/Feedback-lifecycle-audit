# Experiment Status

Updated: 2026-09-26

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
| Validation-based Calibration-20 Stage A | 20 attempted; 16 usable hints; 4 failures preserved |
| Calibration A01/A02 annotation | Not started |
| Synthetic Stress-20 human review | 20 reviewed by A02; 10 RETRACT / 10 UNSURE; not adjudicated consensus |
| Synthetic Stress-20 Qwen B/C | Complete; B 14/20, C 16/20; reported separately |
| Calibration/test-scale Qwen B/C | Not run |

## Conditions

Condition B receives the frozen evidence packet and returns a lifecycle prediction. Condition C receives the same projected packet, applies deterministic evidence checks, follows the explicit RevGround decision procedure, and validates the returned lifecycle decision after the model response.

Both conditions enter the evaluator through the same normalized schema. B is represented as non-selective (`abstain=false`); C preserves abstention and final-action information.

## Development result

Condition C produced 50 accepted outputs with no errors, no packet abstentions, and no decision-rule violations. Its lifecycle distribution was `KEEP=21`, `RETIRE=29`. The B/C evidence hash comparison matched all 50 items.

These are technical development results only. They do not establish agreement or accuracy against A01/A02 or adjudicated gold labels.

## Synthetic Stress-20 result

The controlled rare-label stress run used identical Qwen settings for B and C. On the 19 paired cases, B/C lifecycle agreement was 17/19 (89.5%); B was correct on 14/19 and C on 16/19. C raised reviewed-RETRACT recall from 80% to 100% and reduced false KEEP from 10% to 0%, while UNSURE recognition remained 60% for both. This is a diagnostic stress result, not a natural prevalence estimate. See [the full stress summary](../results/stress_20/stress_20_results_summary.md).

## Reproducibility and retention

The repository contains the runners, prompts, evaluator, and aggregate summaries. Raw provider responses and per-run output trees are intentionally kept outside the public repository in the local audit workspace.

See:

- [Condition C README](../baselines/condition_C/README.md)
- [Development results summary](../results/development_50/development_results_summary.md)
- [Matched evidence summary](../results/development_50/matched_evidence_summary.json)
- [Calibration results](../results/calibration_20/README.md)
- [Results highlights](../results/RESULTS_HIGHLIGHTS.md)
- [Synthetic Stress-20 results](../results/stress_20/stress_20_results_summary.md)
- [Supervisor progress](SUPERVISOR_PROGRESS.md)
