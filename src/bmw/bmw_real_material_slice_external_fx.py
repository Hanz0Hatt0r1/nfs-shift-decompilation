#!/usr/bin/env python3
"""Build a real BMW M3 material slice using an external bodywork.fx."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from bmw_real_material_slice import build_real_bmw_material_slice


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Build BMW M3 MaterialSlice/1 from BFFs plus an external FX source"
    )
    ap.add_argument("archive", type=Path)
    ap.add_argument("golden_manifest", type=Path)
    ap.add_argument("shader_source", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--primitive-index", type=int, default=1)
    ap.add_argument("--supplemental-bff", action="append", default=[])
    args = ap.parse_args()
    report = build_real_bmw_material_slice(
        args.archive,
        args.golden_manifest,
        primitive_index=args.primitive_index,
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
        "primitive_index": report["primitive_index"],
        "blocking_reasons": report["blocking_reasons"],
        "shader_source": report["material_binding"].get("shader_source"),
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
