# Held-out Natural TEST-197 Preparation

This directory records the frozen, label-independent preparation of the full
197-transition TEST partition. The historical TEST-50 selection is preserved
as Batch 1; the remaining 147 transitions are Batch 2.

## Frozen accounting

- TEST partition: 197 transitions
- Objective source-language QC: 188 `CONFIRMED_C`, 9 exclusions
- Stage A: 190 calls total (50 historical Batch 1 + 140 Batch 2)
- Accepted hints: 170; preserved Stage-A failures: 20
- Successful C claim-bearing evidence packets: 168
- Profile: 168 cases, 3 problems, 49 trajectories, 42 participants
- Replacements: 0

Stage A used only `stealth/space-bunny-alpha` with the frozen prompt, 512-token
budget, 90-second timeout, fallback disabled, and no automatic retries. Focal
claims use `first_explicit_diagnostic_assertion_v1`.

The new 126 packet cases were replayed in `revground-c-runner:2.0` for both
S_t and S_t+1. The final packet and all preparation artifacts are hashed in
[`SHA256SUMS.txt`](SHA256SUMS.txt). A01 and A02 packages are isolated under
`annotation/heldout_test_197/` and contain no labels or model predictions.

Qwen and DeepSeek B/C evaluator calls have not been run on this cohort.
