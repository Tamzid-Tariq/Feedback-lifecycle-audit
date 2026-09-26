# RevGround development-results verification

Verification date: 2026-09-26

## Verdict

The supplied results are substantially consistent with the local run artifacts when “accuracy” is interpreted as lifecycle-decision accuracy. The report is consistent with the Qwen primary runs and the final GLM canonical outputs. The caveats below should be retained with the results.

## Reference file

- Source: `C:\Users\User\Downloads\revground_adjudication_final.jsonl`
- Repository copy: `annotation/revground_adjudication_final.jsonl`
- SHA-256: `8FBCEBE1E0E200F8D4AE52F30DF597DA086330E20BE3493C80B4E603BCD5B07D`
- Rows: 50 unique rows, `DEV_001` through `DEV_050`, with no duplicates or missing IDs.
- Lifecycle: 21 `KEEP`, 29 `RETIRE`, 0 `RETRACT`, 0 `UNSURE`.
- Status: 40 `consensus_carry_forward`, 10 `adjudicated`.
- Provenance: 40 `human_annotator_consensus`, 10 `adjudication_review`.

The 10 review rows are `DEV_004`, `DEV_007`, `DEV_010`, `DEV_012`, `DEV_027`, `DEV_029`, `DEV_038`, `DEV_048`, `DEV_049`, and `DEV_050`.

## A01/A02 checks

The reported pre-adjudication agreement values reproduce from `Annotation/revground_annotations_A01.json` and `Annotation/revground_annotations_A02.json`:

| Construct | Agreement | Raw agreement | Cohen kappa |
|---|---:|---:|---:|
| Original validity | 48/50 | 96.0% | 0.3243 |
| Target state | 48/50 | 96.0% | 0.9228 |
| Lifecycle | 48/50 | 96.0% | 0.9228 |
| Priority | 44/50 | 88.0% | 0.7608 |
| Leakage | 45/50 | 90.0% | 0.0000 |

Joint agreement is 40/50 (80.0%), and the lifecycle disagreements are `DEV_010` and `DEV_012`. The lifecycle confusion matrix in the supplied report also matches the annotation files.

## Lifecycle-result checks

| Method/artifact | Result reproduced |
|---|---|
| GLM-5.3 B canonical | 50/50 lifecycle-correct; 21 KEEP and 29 RETIRE |
| GLM-5.3 C | 50/50 lifecycle-correct; 21 KEEP and 29 RETIRE |
| Qwen B primary | 48 accepted, all 48 lifecycle-correct; missing `DEV_024` and `DEV_046`; 48/50 end-to-end; 19/21 KEEP recall |
| Qwen C primary/operational | 49 accepted rows, 46/49 lifecycle-correct; 46/50 end-to-end; 47/50 decision coverage; 1/47 selective errors; 17/21 KEEP recall; 1/21 wrongful removal |

The Qwen C operational interpretation is consistent with the requested validator semantics: `DEV_004` and `DEV_012` are accepted model abstentions, while `DEV_024` is an evaluator-side system abstention caused by an invalid evidence reference. It is not a gold `UNSURE` label.

The Qwen B/C primary-run overlap is 48 cases, with 46/48 lifecycle agreement. The only differences are `DEV_004` and `DEV_012`. Evidence SHA values match for all 50 requested items.

## Runtime checks

The run metadata reproduces the supplied primary-run values:

- Qwen B: 50 requests, mean latency 43.4 s, 537,456 total tokens.
- Qwen C: 50 requests, mean latency 75.0 s, 593,601 total tokens.
- GLM B: 50 requests, mean latency 19.9 s, 427,473 total tokens.
- GLM C: 50 requests, mean latency 25.8 s, 471,839 total tokens.
