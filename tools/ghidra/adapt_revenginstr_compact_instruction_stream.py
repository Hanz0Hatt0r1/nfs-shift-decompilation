#!/usr/bin/env python3
"""Adapt generic revenginstr compact instruction rows to the existing SHIFT tag."""
from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path
from typing import Any, TextIO

GENERIC_FORMAT = "REVENGINSTR.GhidraCompactInstructionStream/1"
SHIFT_FORMAT = "SHIFT.GhidraCompactInstructionStream/1"


def open_text(path: Path, mode: str) -> TextIO:
    if path.suffix == ".gz":
        return gzip.open(path, mode, encoding="utf-8")
    return path.open(mode, encoding="utf-8")


def adapt_row(row: dict[str, Any], line_no: int) -> dict[str, Any]:
    if row.get("format") != GENERIC_FORMAT:
        raise ValueError(f"line {line_no}: expected {GENERIC_FORMAT}")
    if row.get("kind") not in {"header", "instruction"}:
        raise ValueError(f"line {line_no}: unexpected row kind")
    adapted = dict(row)
    adapted["format"] = SHIFT_FORMAT
    return adapted


def adapt_file(source: Path, destination: Path) -> None:
    with open_text(source, "rt") as input_file, open_text(destination, "wt") as output_file:
        for line_no, line in enumerate(input_file, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{source}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{source}:{line_no}: expected an object")
            output_file.write(
                json.dumps(adapt_row(row, line_no), ensure_ascii=False, separators=(",", ":")) + "\n"
            )


def main() -> int:
    if len(sys.argv) != 3:
        print(f"Usage: {Path(sys.argv[0]).name} <revenginstr.jsonl[.gz]> <shift.jsonl[.gz]>", file=sys.stderr)
        return 2
    try:
        adapt_file(Path(sys.argv[1]), Path(sys.argv[2]))
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
