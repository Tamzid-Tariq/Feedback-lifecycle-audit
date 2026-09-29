# Qwen RECOVERY_429_V1

This namespace contains exactly one recovery attempt for each primary HTTP-429 outcome in the frozen Qwen B/C runs. No HTTP 400, malformed JSON, schema rejection, input-size failure, or other primary failure was selected.

## Settings

- Model: `qwen/qwen3.8-27b`
- Maximum completion tokens: 16,000
- Temperature: 0
- Per-call timeout: 360 seconds
- Pacing: 20 seconds between calls; 90 seconds after a recovery HTTP 429
- Automatic retry: disabled
- Fallback: disabled
- Primary files: untouched and hash-verified after recovery

## Outcomes

- Condition B: 51 attempts covering 51 primary 429s; 28 accepted, 23 recorded errors.
- Condition C: 27 attempts covering 27 primary 429s; 8 accepted, 19 recorded errors.

Recovery failures were retained as final outcomes and were not retried or replaced. See `recovery_429_v1_summary.json` and the condition ledgers for the audited record.
