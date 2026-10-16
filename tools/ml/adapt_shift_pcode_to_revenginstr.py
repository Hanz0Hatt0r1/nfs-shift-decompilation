#!/usr/bin/env python3
"""Adapt retained SHIFT portable P-code rows to the revenginstr outer format.

This migration adapter changes only the outer ``format`` identifier.  The
``model_text``, metrics, join metadata and row order remain byte-for-byte values at
the JSON value level so old and generic audit/guard behavior can be compared on the
same retained 1000-function population.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SOURCE_FORMAT = "SHIFT.MlPcodeCorpus/1"
TARGET_FORMAT = "REVENGINSTR.PcodeCorpus/1"


def adapt(source: Path, output: Path) -> dict[str, int]:
    rows = 0
    ok = 0
    with source.open("r", encoding="utf-8") as inp, output.open("w", encoding="utf-8") as out:
        for line_no, raw in enumerate(inp, 1):
            if not raw.strip():
                continue
            row: Any = json.loads(raw)
            if not isinstance(row, dict):
                raise ValueError(f"{source}:{line_no}: expected object")
            if row.get("format") != SOURCE_FORMAT:
                raise ValueError(
                    f"{source}:{line_no}: expected {SOURCE_FORMAT}, got {row.get('format')!r}"
                )
            payload = dict(row)
            payload["format"] = TARGET_FORMAT
            out.write(json.dumps(payload, sort_keys=True) + "\n")
            rows += 1
            if row.get("decompile_status") == "ok":
                ok += 1
    if rows == 0:
        raise ValueError("source corpus is empty")
    return {"rows": rows, "ok": ok}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    stats = adapt(args.source, args.output)
    print("source format:", SOURCE_FORMAT)
    print("target format:", TARGET_FORMAT)
    print("rows:", stats["rows"])
    print("ok:", stats["ok"])
    print("output:", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
