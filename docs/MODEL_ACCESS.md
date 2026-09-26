# Model access and actual run record

API credentials are supplied through environment variables and are never stored in this repository.

## Models actually used

| Role | Model | Provider/route | Actual status |
|---|---|---|---|
| Calibration-20 Stage A | `stealth/space-bunny-alpha` | OpenRouter Chat Completions | 20 calls; 16 usable hints; 4 failures preserved |
| Held-out TEST-50 Stage A | `stealth/space-bunny-alpha` | OpenRouter Chat Completions | 50 calls; 44 usable hints; 6 failures preserved; Qwen B/C not run |
| Development Condition B/C baseline | `glm-5.3` | OpenAI-compatible GLM Coding Plan endpoint | 50 requests per condition; complete technical diagnostic |
| Development Condition B/C comparison | `qwen/qwen3.8-27b` | OpenRouter Chat Completions | Primary runs plus three targeted recovery calls; caveats retained |
| Synthetic Stress-20 B/C | `qwen/qwen3.8-27b` | OpenRouter Chat Completions | 20 requests per condition; identical 16,000-token/360-second settings |

## Boundaries

- Calibration Stage A used only `S_t` input, fallback disabled, and no automatic retries.
- Stress-20 B/C used the same evidence file, model, output budget, timeout, provider/routing policy, and retry policy.
- The original Qwen development B/C primary runs used different output budgets (5,000 and 12,000 tokens); this is explicitly reported as a development-stage caveat.
- No Qwen B/C run has been performed on Calibration-20 or held-out TEST-50.
- Held-out TEST-50 Stage A was completed before the source-language eligibility analysis; the two objective language exclusions and six preserved Stage-A failures leave 42 analyzable natural cases.
- Raw provider responses and per-run output trees remain in the local audit workspace; aggregate results and run metadata are documented in this repository.

See [model_card.json](model_card.json) and [generation_policy.json](generation_policy.json) for the machine-readable run record.
