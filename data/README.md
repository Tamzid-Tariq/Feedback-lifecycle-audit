# Data

## Source dataset

CodeStream dataset, Mendeley Data record: <https://data.mendeley.com/datasets/n77t7z9zcr/1>

The repository page recorded a CC BY 4.0 licence when profiled on 13 September 2026. Confirm the current source terms before redistribution or reuse.

The original dataset is not duplicated in this repository. For local reproduction, place the files at:

```text
data/raw/Submission Data.csv
data/raw/Problem Data.csv
```

`data/raw/` is ignored by Git.

## Frozen source checksums

```text
d6c191712a927d68c911d83d3f50dfeacbf4ce77c4e7e3ffc2fbe50e4dcb5419  Submission Data.csv
33b7643a344d688f06674aa40294bf7e1a282a1b0406ec9ab97559e4f589ec85  Problem Data.csv
```

Verify locally in PowerShell:

```powershell
Get-FileHash 'data/raw/Submission Data.csv' -Algorithm SHA256
Get-FileHash 'data/raw/Problem Data.csv' -Algorithm SHA256
```

## Tracked data

The compact development annotation manifest is tracked at `data/development_50_manifest.csv`. The official fresh calibration manifest is `data/manifests/calibration_20_manifest.csv` with its JSON companion and `calibration_20_manifest.SHA256SUMS`; it is a deterministic sample from validation, created before labels. The older development-based 25-case proposal is retained under `data/manifests/archive/` and marked SUPERSEDED. Locally rebuilt records belong under `data/derived/` and are ignored. Annotation packets are partitioned under `annotation/`; derived results are partitioned under `results/`.
