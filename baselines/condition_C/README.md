# Condition C: deterministic evidence checks plus GLM-5.3 audit

Condition C is a controlled extension of Condition B. It imports Condition B's frozen-packet loader and `project_evidence()` projection, so the model receives the same evidence packet and no additional student/test information.

The added stages are:

1. deterministic packet validation before a provider call;
2. an explicit RevGround lifecycle-audit prompt;
3. post-LLM decision validation against the lifecycle table;
4. selective abstention with `UNSURE` when evidence is unusable, insufficient, conflicting, or the returned lifecycle is inconsistent.

The runner writes predictions, raw responses, request metadata, errors, and run metadata using the same audit-friendly JSONL conventions as Condition B. Deterministic packet failures are recorded as abstention predictions and as errors; GLM is not called for those items.

The default completion budget is 12,000 tokens because the explicit audit procedure is longer than Condition B's baseline prompt and the known long-response B retries used that budget. Override it with `--max-tokens` when a matched budget is required for a separate experiment.

## Local dry-run

From `condition_B_glm53_work`:

```powershell
python source_snapshot\baselines\condition_C\run_condition_c.py --item-ids DEV_001,DEV_002,DEV_003,DEV_004,DEV_005 --dry-run
```

This validates the frozen packets and prints the projected evidence keys and IDs without contacting GLM. The default selection is five packets. Remove `--dry-run` only when a real Condition C call is explicitly requested.

## Shared evaluation and matched-evidence artifact

The existing canonical B predictions are normalized at evaluation time; B is not rerun or rewritten. After a C run, use:

```powershell
python source_snapshot\evaluation\normalize_conditions.py `
  --b-predictions outputs\condition_B_development50_final.jsonl `
  --c-predictions source_snapshot\baselines\condition_C\outputs\runs\<run-id>\predictions.jsonl `
  --b-request-metadata outputs\runs\all50_20260925_glm53\request_metadata.jsonl `
  --c-request-metadata source_snapshot\baselines\condition_C\outputs\runs\<run-id>\request_metadata.jsonl `
  --evaluation-output source_snapshot\baselines\condition_C\outputs\runs\<run-id>\shared_evaluation.jsonl `
  --matched-evidence-output source_snapshot\baselines\condition_C\outputs\runs\<run-id>\matched_evidence.jsonl `
  --summary-output source_snapshot\baselines\condition_C\outputs\runs\<run-id>\evaluation_summary.json
```

The shared record contains `condition`, `item_id`, `original_validity`, `target_state_t1`, `predicted_lifecycle`, `abstain`, `final_action`, `evidence_ids`, `short_reason`, and `abstention_reason`. The matched-evidence file compares `B_evidence_sha256` and `C_evidence_sha256` item by item.

## Model output versus final output

GLM receives only the ten-field schema described in `prompt.txt`. The runner adds `model_lifecycle_label`, `rule_expected_lifecycle`, `decision_rule_violation`, `decision_validation`, and packet-validation information only to the saved audit record after the model response has been parsed.
