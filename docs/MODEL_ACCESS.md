# Model Access

Condition B requires the GLM-5.3 model through the OpenAI-compatible GLM Coding Plan endpoint.

The smoke run freezes:

`glm-5.3`

The Coding Plan route is:

`https://api.z.ai/api/coding/paas/v4/chat/completions`

Before the next experimental run, the project will freeze:

- the exact GLM model identifier
- provider/access configuration
- prompt
- model settings
- evidence inputs
- output schema

A GLM Coding Plan API key is required to run Condition B or Condition C. The key must be supplied through an environment variable such as `GLM_API_KEY`; it is never written to the repository.

The 50-item development runs for Conditions B and C were completed on 2026-09-25. Condition C used the same frozen evidence projection as Condition B, with its explicit audit procedure and post-response decision validation.

Raw provider responses, request metadata, and per-run output directories are retained in the local audit workspace rather than copied into this repository.

API credentials are never stored in this repository.
