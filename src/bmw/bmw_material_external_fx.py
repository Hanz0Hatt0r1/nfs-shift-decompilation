#!/usr/bin/env python3
"""Build the real BMW M3 material binding with an external bodywork.fx file."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from bmw_material_from_bff import build_real_bmw_material_binding


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Build the BMW M3 MaterialBinding using BFF data plus an external FX source"
    )
    ap.add_argument("archive", type=Path, help="primary BMW_M3_E36.bff")
    ap.add_argument("shader_source", type=Path, help="external bodywork.fx source")
    ap.add_argument("output", type=Path, help="SHIFT.RealBMWMaterialBindingEvidence/1 JSON")
    ap.add_argument("--supplemental-bff", action="append", default=[])
    args = ap.parse_args()
    report = build_real_bmw_material_binding(
        args.archive,
        supplemental_bffs=args.supplemental_bff,
        shader_source_file=args.shader_source,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "blocking_reasons": report["blocking_reasons"],
        "shader_source": report["provenance"]["shader_source"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
