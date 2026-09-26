#!/usr/bin/env python3
"""Install the non-model, blinded annotation package derivatives."""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    common = root / "annotation" / "common"
    dev = root / "annotation" / "development_50"
    calibration = root / "annotation" / "calibration_20"
    packet_path = calibration / "calibration_20_evidence_frozen_v1.jsonl"
    packets = [json.loads(line) for line in packet_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    safe_cases = json.dumps(packets, ensure_ascii=False, separators=(",", ":"))
    safe_cases = safe_cases.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    calibration.joinpath("tools").mkdir(parents=True, exist_ok=True)
    shutil.copy2(common / "LIFECYCLE_RUBRIC_v2.md", calibration / "LIFECYCLE_RUBRIC_v2.md")
    for annotator in ("A01", "A02"):
        source = dev / "tools" / f"RevGround_Annotator_{annotator}.html"
        text = source.read_text(encoding="utf-8-sig")
        replacement = f"const cases = {safe_cases};\nconst annotatorId"
        text = re.sub(r"const cases = .*?;\nconst annotatorId", lambda _match: replacement, text, count=1, flags=re.DOTALL)
        text = text.replace("RevGround Human Annotation", "RevGround Validation Calibration Annotation")
        text = text.replace("revground_annotation_v2_", "revground_calibration_20_annotation_v2_")
        calibration.joinpath("tools", f"RevGround_Annotator_{annotator}.html").write_text(text, encoding="utf-8")
    # Calibration packages must contain no adjudication, predictions, raw
    # provider responses, request metadata, or other-annotator exports.
    allowed = {"LIFECYCLE_RUBRIC_v2.md", "calibration_20_evidence_frozen_v1.jsonl", "tools"}
    unexpected = {path.name for path in calibration.iterdir()} - allowed
    if unexpected:
        raise SystemExit(f"Calibration package contains unexpected files: {sorted(unexpected)}")
    print(json.dumps({"status": "INSTALLED", "packet_rows": len(packets), "files": sorted(allowed)}))


if __name__ == "__main__":
    main()
