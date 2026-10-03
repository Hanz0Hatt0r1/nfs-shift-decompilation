#!/usr/bin/env python3
"""Build renderer IR directly from SHIFT BFF/ZIP/directory inputs."""
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

from offline_scene_ir import SCENE_IR_EXTENSIONS, build_scene_ir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="+", help="BFF, ZIP, or directory inputs")
    parser.add_argument("-o", "--output", required=True, help="IR output directory")
    parser.add_argument(
        "--ext",
        nargs="+",
        default=list(SCENE_IR_EXTENSIONS),
        help="resource extensions to materialize",
    )
    parser.add_argument("--fail-fast", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_scene_ir(
        args.input,
        args.output,
        extensions=args.ext,
        fail_fast=args.fail_fast,
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "archive_count": report["archive_count"],
        "manifest_resource_count": report["manifest_resource_count"],
        "manifest_error_count": report["manifest_error_count"],
        "blocking_reasons": report["blocking_reasons"],
        "artifacts": report["artifacts"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
