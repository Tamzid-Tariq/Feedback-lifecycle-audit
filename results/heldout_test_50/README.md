# Held-out TEST-50 results

Stage A is complete for the frozen 50-case natural sample: 44 usable hints and 6 preserved generation failures. Source-language QC then identified two objective exclusions, `726478f13ad8e011c4a0cfa2` (Java syntax) and `bda05da230eecfb67fa3a104` (C++ syntax), leaving 48 eligible C cases and 42 final analyzable cases after the six eligible Stage-A failures.

Label-independent A01/A02 annotation packages are released under [`annotation/heldout_test_50/`](../../annotation/heldout_test_50/) for the 42 claim-bearing cases. They contain only the frozen evidence packet, Rubric v2.0, and annotator HTML; no labels, predictions, other-annotator outputs, or adjudication information are included. Natural annotation is pending. No Qwen or DeepSeek B/C held-out TEST run was performed. See [the eligibility calculation](language_qc_eligibility.md), [the release manifest](heldout_test_42_release_manifest.json), and [the QC audit](../../data/qc/language_qc_summary.json).
