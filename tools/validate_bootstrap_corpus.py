#!/usr/bin/env python3
"""Validate high-level track/vehicle bootstrap targets across an offline catalog."""
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

from offline_bootstrap_corpus_validation import (
    build_bootstrap_corpus_validation_files,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("catalog", help="SHIFT.OfflineResourceCatalog/1 JSON")
    parser.add_argument("graph", help="SHIFT.OfflineResourceDependencyGraph/1 JSON")
    parser.add_argument("-o", "--output", required=True, help="validation JSON output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_bootstrap_corpus_validation_files(
        args.catalog,
        args.graph,
        args.output,
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "summary": report["summary"],
        "blocking_reasons": report["blocking_reasons"],
        "output": str(Path(args.output)),
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
