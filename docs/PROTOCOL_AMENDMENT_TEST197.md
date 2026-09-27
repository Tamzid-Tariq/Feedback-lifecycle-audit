# Protocol amendment: complete TEST-partition natural cohort

Amendment ID: `test197_full_eligible_cohort_v1`
Frozen before any additional held-out labels or model results were inspected: 2026-09-27.

This amendment expands the final natural evaluation cohort to every eligible transition in the existing 197-case TEST partition. It does not replace the historical TEST-50 selection.

## Frozen sampling and provenance

- Source partition: `test`
- Source manifest: `data/manifests/final_test_197_manifest.csv`
- Final partition size: 197 transitions
- Selection rule: census of the existing TEST partition; no sampling or replacement
- Historical Batch 1: the original 50-case manifest is preserved byte-for-byte at `data/manifests/archive/heldout_natural50_manifest_batch1.json`
- Batch 2: the remaining 147 TEST transitions
- Labels read during selection: false
- Original Batch 1 cases are retained in the final manifest and are never replaced.

## Objective language QC

QC is run from source syntax in `code_t` and `code_t1` only, using the frozen classifier and no lifecycle labels, annotator outputs, model predictions, or model performance. All nine non-C signatures in TEST are retained as objective exclusions in the cohort ledger; they are not deleted or replaced.

The frozen cohort manifest records all 197 transitions, their Batch 1/Batch 2 provenance, QC status, and final C eligibility. It reports 188 eligible `CONFIRMED_C` transitions, including 48 in Batch 1 and 140 remaining eligible Batch 2 transitions.

## Stage-A policy

For the 140 remaining eligible Batch 2 transitions, use exactly the existing TEST-50 Stage-A policy:

- Model: `stealth/space-bunny-alpha`
- Endpoint: OpenRouter Chat Completions
- Prompt SHA-256: `3916584eb94f1ffa7749bbc94a2b51e1584a9d2eca97d1f197780ee8d956eaee`
- `max_tokens`: 512
- Timeout: 90 seconds
- Fallback: disabled
- Automatic retry: disabled
- Acceptance rule: the frozen JSON schema and diagnostic-hint acceptance rule used for TEST-50; accepted diagnostic hints must contain a 20–60 word hint and required claim fields
- No generator substitution, recovery pass, or replacement case is permitted.

Every Stage-A attempt, including empty, length-violation, transport, HTTP, schema, model-mismatch, and other generation failures, is preserved in the raw response, request metadata, and error artifacts. Successful hints are frozen with `first_explicit_diagnostic_assertion_v1`.

## Evidence and annotation boundary

For every successful claim-bearing hint, build the same frozen evidence packet schema used by Development-50 and the existing TEST-50 package: `S_t`, `S_t+1`, unified diff, compiler replay, official tests with comparator outcomes, stored judge traces, evidence IDs, toolchain metadata, and per-packet SHA-256.

The final evidence inventory and cohort profile must report cases, problems, trajectories, and participants. A01 and A02 receive isolated packages over the identical final successful claim-bearing cohort, containing only the rubric, frozen evidence packet, and annotator HTML. No model predictions, labels, other-annotator outputs, or adjudication information may enter those packages. No Condition B/C model evaluation is authorized by this amendment.
