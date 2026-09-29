# RECOVERY_429_V1

This is a separate recovery namespace for the frozen held-out TEST-197
DeepSeek primary runs. It must never overwrite either primary run.

- Primary source: `../condition_B` and `../condition_C`
- Recovery scope: exactly the primary records with `http_status=429`
- Scope at preparation: Condition B = 90 records; Condition C = 53 records
- Model: `deepseek/deepseek-v4.1-flash`
- Evidence: `../../../evidence_frozen_v1.jsonl`
- Maximum output tokens: `16000`
- Temperature: `0`
- Timeout: `360` seconds
- Fixed pacing for both B and C: `20` seconds between requests and `90`
  seconds after a recorded HTTP 429
- Automatic retries/fallbacks: disabled; one recovery attempt per selected ID
- Validator: the existing Condition B/C runners and validator paths

Recovery completed for all 143 selected IDs exactly once. Condition B had 90
attempts: 83 accepted predictions and 7 recorded errors (including the two
initial HTTP 401 outcomes, which were preserved and not retried). Condition C
had 53 attempts: 24 accepted predictions and 29 recorded errors, with zero
decision-rule violations. No recovery errors were retried.

The final coverage and integrity audit is recorded in
`recovery_429_v1_summary.json`. It confirms exact primary HTTP-429 coverage,
one attempt per selected ID, and unchanged primary artifact hashes.
