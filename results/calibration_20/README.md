# Calibration-20 results

The selection is 20 fresh validation-partition cases, selected before labels. Source-language QC was run before annotation: all 20 are `CONFIRMED_C` under the source-syntax-only rule. Stage-A attempted all 20 with `stealth/space-bunny-alpha`, no fallback, and no automatic retries. Sixteen hints were usable; four failures are preserved. A01 and A02 independently annotated the 16 eligible rows, with zero substantive disagreements across all five fields. `rubric_change_required=false`; no adjudication was required or performed. Rubric v2.0 is frozen as final. No Qwen or DeepSeek B/C predictions were run.

The frozen annotation packet contains only the 16 annotation-eligible cases. Stage-B evidence replay is now complete in the pinned `revground-c-runner:2.0` locked runner: 32 state replays, 23 compile successes, 9 compile errors, and 450 official test-state entries. The four Stage-A failures remain outside the annotation packet and are preserved in the Stage-A error/eligibility artifacts.

The build audit is [calibration_20_build_manifest.json](calibration_20_build_manifest.json); raw locked-runner results are under [`runs/`](runs/). The original A01/A02 exports and their hashes are under [`annotator_exports/`](annotator_exports/). No Qwen or DeepSeek B/C predictions were run.
