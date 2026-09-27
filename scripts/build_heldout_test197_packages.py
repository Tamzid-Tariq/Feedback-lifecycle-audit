#!/usr/bin/env python3
"""Build isolated A01/A02 HTML packages over the identical final packet."""
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import shutil
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--template-a01", type=Path, required=True)
    parser.add_argument("--template-a02", type=Path, required=True)
    parser.add_argument("--rubric", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    packet_bytes = args.packet.read_bytes()
    packet_sha = hashlib.sha256(packet_bytes).hexdigest()
    packet_rows = [json.loads(line) for line in packet_bytes.decode("utf-8").splitlines() if line.strip()]
    if len(packet_rows) != 168 or len({row["item_id"] for row in packet_rows}) != 168:
        raise SystemExit("final packet must contain 168 unique records")
    if any("lifecycle_label" in row or "human_labels" in row or "prediction" in row for row in packet_rows):
        raise SystemExit("reference/model fields detected in packet")
    compressed = base64.b64encode(gzip.compress(packet_bytes, compresslevel=6)).decode("ascii")
    for annotator, template_path in (("A01", args.template_a01), ("A02", args.template_a02)):
        output = args.output_root / annotator
        output.mkdir(parents=True, exist_ok=True)
        packet_target = output / "heldout_test197_evidence_frozen_v1.jsonl"
        rubric_target = output / "LIFECYCLE_RUBRIC_v2.md"
        html_target = output / f"RevGround_Annotator_{annotator}.html"
        packet_target.write_bytes(packet_bytes)
        shutil.copy2(args.rubric, rubric_target)
        html = template_path.read_text(encoding="utf-8")
        start = html.index("const cases = ")
        end = html.index(";\nconst annotatorId", start) + 1
        html = html[:start] + "let cases = [];" + html[end:]
        html = html.replace('const annotatorId = "A01";', f'const annotatorId = "{annotator}";', 1)
        html = html.replace("heldout_test50_pending", "heldout_test197_pending", 1)
        embedded = (
            "\nconst embeddedPacketGzipBase64 = " + json.dumps(compressed) + ";\n"
            "async function loadEmbeddedCases() {\n"
            "  const bytes = Uint8Array.from(atob(embeddedPacketGzipBase64), char => char.charCodeAt(0));\n"
            "  const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream(\"gzip\"));\n"
            "  const text = await new Response(stream).text();\n"
            "  cases = text.split(/\\r?\\n/).filter(Boolean).map(JSON.parse);\n"
            "  render();\n"
            "}\n"
        )
        marker = 'window.addEventListener("beforeunload",saveCurrent);\nrender();'
        if marker not in html:
            raise SystemExit(f"HTML template marker missing: {template_path}")
        html = html.replace(marker, "window.addEventListener('beforeunload',saveCurrent);" + embedded + "loadEmbeddedCases();", 1)
        html_target.write_text(html, encoding="utf-8", newline="\n")
    print(json.dumps({"status": "BUILT", "packet_rows": len(packet_rows), "packet_sha256": packet_sha, "annotators": ["A01", "A02"]}, indent=2))


if __name__ == "__main__":
    main()
