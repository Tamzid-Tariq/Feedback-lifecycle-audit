# Condition B: matched-evidence LLM baseline

This is the evidence-aware baseline for the RevGround comparison. It sends a fixed prompt and a whitelist projection of each frozen evidence packet to GLM-5.3 through an OpenAI-compatible GLM endpoint. It does not read annotation exports, adjudication data, expected lifecycle labels, or RevGround decision rules.

The input is the frozen development packet file at `../../annotation/development_50_evidence_frozen_v1.jsonl`. A bare run is intentionally limited to the first five development cases as a smoke test. Full development execution requires an explicit larger `--limit`.

## Run

From this directory, set the GLM key and run the five-case smoke test:

```powershell
$env:GLM_API_KEY = "<your key>"
python run_baseline.py
```

The default model is `glm-5.3` and the default endpoint is the GLM Coding Plan route, `https://api.z.ai/api/coding/paas/v4/chat/completions`. Set `CONDITION_B_MODEL`, `GLM_API_ENDPOINT`, or pass `--model`/`--endpoint` to use an explicitly selected compatible route without changing the prompt or evidence projection.

Every bare run gets a fresh directory under `outputs/runs/`, so reruns do not require manual cleanup. For a named run directory, use `--run-dir`; `--overwrite` is then required if its artifacts already exist.

```powershell
python run_baseline.py --limit 50
```

For a no-provider structural check of the five-case smoke selection:

```powershell
python run_baseline.py --dry-run
```

## Evidence boundary

For every packet, the sole model payload contains the problem statement, fixed focal claim, `S_t`, `S_t+1`, textual diff, compiler evidence, official tests and their outputs, stored traces, and claim-relevant trace. The original hint and all human/reference-answer fields are excluded. The projection is defined in `project_evidence()`; no other packet fields can reach the request.

Before calling the provider, the runner verifies each frozen packet's SHA-256 digest. It also rejects a response unless it has the exact required JSON keys, valid label values, the requested item ID, and only evidence IDs actually supplied to the model.

A malformed or failed provider response is retained in `raw_responses.jsonl`, `errors.jsonl`, and `request_metadata.jsonl`; the run continues to the remaining smoke cases and ends non-zero if any item lacks a valid prediction.

Each run directory contains predictions, raw responses, errors, per-request metadata, and a run summary. Request metadata records prompt/evidence/request hashes, supplied evidence IDs, model/endpoint, provider response identifiers, and timing; it never records the API key.

## Output contract

Each line has exactly these fields:

```json
{
  "item_id": "DEV_008",
  "original_validity": "SUPPORTED",
  "target_state_t1": "RESOLVED",
  "lifecycle_label": "RETIRE",
  "instructional_priority": "LOW",
  "leakage_label": "ABSENT",
  "evidence_ids": ["source:DEV_008:S_t", "source:DEV_008:S_t+1", "diff:DEV_008"],
  "short_reason": "The focal missing-case defect is corrected in the later submission."
}
```
