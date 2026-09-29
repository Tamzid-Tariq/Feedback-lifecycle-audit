# Canonical verified TEST report

This directory contains the publication-facing held-out TEST report generated
from `results/heldout_test_197/analysis/verified_test_results.json`.

- `Feedback-lifecycle-audit_TEST197_Verified_Results_20260929.pdf` is the canonical reader
  copy. All six pages were rendered to PNG and visually inspected for clipping,
  overlap, table breakage, missing glyphs, and figure placement.
- `Feedback-lifecycle-audit_TEST197_Verified_Results_20260929.docx` is the editable copy. It
  passed the structural accessibility audit with zero findings.
- `figures/` contains the two previously missing paired-comparison figures as
  standalone high-resolution PNG files.
- `REPORT_SHA256SUMS.txt` freezes the reports, figures, and analysis outputs.

The report deliberately distinguishes the 197-transition source partition from
the 168-packet analytic cohort. It reports "no consistent directional advantage
observed" and does not claim statistical equivalence or a proven null effect.

Rebuild commands:

```bash
python scripts/audit_heldout_test197_results.py --write
python scripts/build_test197_verified_report.py
python scripts/build_test197_verified_pdf.py
```
