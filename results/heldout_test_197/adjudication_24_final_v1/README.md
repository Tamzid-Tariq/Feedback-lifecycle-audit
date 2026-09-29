# Final adjudication freeze - 24 TEST-168 disagreements

This directory contains the completed qualified-adjudicator return for the 24
unique A01/A02 core-field disagreements. It is separate from the immutable
blind packet in `../adjudication_24_blind_v1/`.

Validation guarantees:

- exactly 24 unique item IDs;
- exact coverage of the frozen disagreement set;
- all 10 required return fields populated;
- all cited evidence IDs present in the corresponding frozen packet;
- JSON and JSONL exports semantically identical;
- adjudicator ID `03` on every row;
- no modification of the original A01 or A02 exports.

Files:

- `adjudication_final_24.json`: returned 24-row JSON array;
- `adjudication_final_24.jsonl`: equivalent line-delimited records;
- `MANIFEST.json`: validation facts, provenance boundary, byte counts, and
  SHA-256 hashes;
- `SHA256SUMS.txt`: compact checksum file for the two returned exports.

The final adjudication is used only after pre-adjudication reliability is
computed. It must not be used to retroactively alter A01/A02 agreement.
