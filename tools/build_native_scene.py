#!/usr/bin/env python3
"""Build source-backed static scene resources from one raw SHIFT SGB."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if SRC.is_dir():
    paths = [SRC]
    paths.extend(sorted(
        (path for path in SRC.rglob("*") if path.is_dir()),
        key=lambda path: (len(path.parts), str(path)),
    ))
    for path in reversed(paths):
        value = str(path)
        if value not in sys.path:
            sys.path.insert(0, value)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from offline_native_scene import build_native_scene_files


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sgb", help="raw extracted SGB resource")
    parser.add_argument("ir_root", help="decoded resource IR root containing manifest.json")
    parser.add_argument("-o", "--output", required=True, help="output directory")
    parser.add_argument("--root-consensus", help="optional SGB MultiMatrix root consensus JSON")
    parser.add_argument(
        "--runtime-shader-admission",
        help="optional exact runtime shader admission JSON",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_native_scene_files(
        args.sgb,
        args.ir_root,
        args.output,
        root_consensus_path=args.root_consensus,
        runtime_shader_admission_path=args.runtime_shader_admission,
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "static_resource_ready": report["static_resource_ready"],
        "native_scene_runtime_ready": report["native_scene_runtime_ready"],
        "blocking_reasons": report["blocking_reasons"],
        "summary": report["summary"],
        "artifacts": report.get("artifacts") or {},
    }, ensure_ascii=False, indent=2))
    return 0 if report["static_resource_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
