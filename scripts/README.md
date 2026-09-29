# Reproduction Entry Points

Run commands from the repository root. Original raw CodeStream data and scratch
run outputs are ignored by Git; explicitly frozen result ledgers are retained
under `results/`.

## 1. Profile and split

```bash
python scripts/profile_and_split.py \
  --submissions "data/raw/Submission Data.csv" \
  --problems "data/raw/Problem Data.csv" \
  --output data/derived/stage4_5
```

## 2. Rebuild the unannotated development records

```bash
python scripts/rebuild_development_records.py --mode write
python scripts/rebuild_development_records.py --mode check
```

## 3. Verify or run hint generation

The default input is the locally rebuilt `data/derived/development_50_records_unannotated.jsonl`. Verification makes no provider call.

```bash
python scripts/generate_hints_openrouter.py --mode verify
```

Do not regenerate the frozen development run. `--mode run` is for an explicitly authorized new partition, requires `OPENROUTER_API_KEY`, and writes outputs under the corresponding `results/<set>/` directory.

## 4. Verify or replay execution evidence

Build the locked-down runner once:

```bash
docker build -t revground-c-runner:2.0 scripts/utils
python scripts/replay_development_50.py --mode verify
```

`--mode run` compiles each code state once, runs every test under an individual two-second program limit, and uses a separate 60-second host/Docker timeout. New outputs go under the corresponding `results/<set>/` directory.

## 5. Evaluate matched predictions

```bash
python scripts/evaluate_claims.py predictions.csv results.json
```

The evaluator rejects empty inputs, duplicate claim/method rows, and unmatched claim sets. No evaluation should be run before human gold labels and method predictions exist.

## 6. Recompute annotation agreement

```bash
python scripts/compute_agreement.py
```

This reads the two frozen A01/A02 JSON exports and regenerates the agreement table, lifecycle confusion matrix, and all-field disagreement index. It never modifies either input export.

## 7. Verify final held-out TEST results

```bash
python scripts/audit_heldout_test197_results.py
python scripts/audit_heldout_test197_results.py --write
```

The audit makes no provider calls. It validates the frozen annotations and
adjudication, combines accepted primary outputs only with accepted
`RECOVERY_429_V1` outputs, and recomputes the complete natural TEST result.

## 8. Rebuild the canonical TEST report

```bash
python scripts/build_test197_verified_report.py
python scripts/build_test197_verified_pdf.py
```

Both builders read the verified JSON. The DOCX is the editable report; the PDF
is the canonical reader copy.
