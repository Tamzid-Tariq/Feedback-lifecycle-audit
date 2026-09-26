# Development Condition B/C Results Summary

Status: complete for the frozen 50-item development set.

## Run coverage

| Condition | Items | Accepted outputs | Errors | Abstentions | Decision-rule violations |
|---|---:|---:|---:|---:|---:|
| B | 50 | 50 canonical merged records | 0 in canonical file | 0 | Not applicable |
| C | 50 | 50 | 0 | 0 | 0 |

The canonical B file merges the 48 first-attempt successes with the successful retries for `DEV_012` and `DEV_046`. B records are normalized at evaluation time with `abstain=false` and an empty `abstention_reason`; the original B artifacts remain unchanged outside this repository.

## Condition C summary

- Model: `glm-5.3`
- Evidence packet: `development_50_evidence_frozen_v1.jsonl`
- Lifecycle outputs: `KEEP=21`, `RETIRE=29`
- Prompt tokens: `355,322`
- Completion tokens: `116,517`
- Reasoning tokens: `101,019`
- Total tokens: `471,839`
- Mean latency: `25.8 seconds per request`

No C packet-validation abstentions, JSON/schema errors, forbidden reference fields, or lifecycle decision-table violations occurred in the final 50-item run.

## Matched evidence

The per-item B/C evidence hashes matched for all 50 development cases: `50/50 TRUE` (`match_rate=1.0`). This verifies that the two primary conditions received identical projected evidence packets. See [matched_evidence_summary.json](matched_evidence_summary.json).

## Interpretation boundary

These are development-run outputs, not adjudicated accuracy results. A01/A02 labels remain independent annotations, and adjudication is still required before treating any comparison against human gold as a final result.
