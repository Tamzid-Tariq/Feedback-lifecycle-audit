# Condition B: matched-evidence LLM baseline

This is the evidence-aware baseline for the RevGround comparison. It sends a fixed prompt and a whitelist projection of each frozen evidence packet to one OpenAI-compatible OpenRouter endpoint. It does not read annotation exports, adjudication data, expected lifecycle labels, or RevGround decision rules.

The default input is the 50 frozen development packets at `../../annotation/development_50_evidence_frozen_v1.jsonl`. The default output is `outputs/condition_B_dev_predictions.jsonl`, with one validated JSON object per item.

## Run

From this directory, set an OpenRouter key and run the script:

```powershell
$env:OPENROUTER_API_KEY = "<your key>"
python run_baseline.py
```

The default model is the repository's existing OpenRouter model (`stealth/union-alpha`). Set `CONDITION_B_MODEL` or pass `--model` to use a different model. `--endpoint` and `--api-key-env` support another OpenAI-compatible provider without changing the prompt or evidence projection.

The runner refuses to overwrite a completed output. To intentionally replace it:

```powershell
python run_baseline.py --overwrite
```

For a no-provider structural check:

```powershell
python run_baseline.py --dry-run
```

## Evidence boundary

For every packet, the sole model payload contains the problem statement, original hint, fixed focal claim, `S_t`, `S_t+1`, textual diff, compiler evidence, official tests and their outputs, stored traces, and claim-relevant trace. The projection is defined in `project_evidence()`; no other packet fields can reach the request.

Before calling the provider, the runner verifies each frozen packet's SHA-256 digest. It also rejects a response unless it has the exact required JSON keys, valid label values, the requested item ID, and only evidence IDs actually supplied to the model. A malformed or failed provider response stops the run without publishing a partial prediction file.

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
