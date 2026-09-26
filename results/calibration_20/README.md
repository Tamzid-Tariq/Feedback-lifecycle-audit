# Calibration-20 results

The selection is 20 fresh validation-partition cases, selected before labels. Source-language QC was run before annotation: all 20 are `CONFIRMED_C` under the source-syntax-only rule. Stage-A attempted all 20 with `stealth/space-bunny-alpha`, no fallback, and no automatic retries. Sixteen hints were usable; four failures are preserved. No Qwen B/C predictions were run.

The frozen annotation packet contains only the 16 annotation-eligible cases. Compiler/test replay was unavailable at freeze time; those fields are explicitly `NOT_REPLAYED`, never fabricated as outcomes.
