#!/usr/bin/env python3
"""Adapt generic revenginstr scalar-use rows to the established Shift format."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

GENERIC_FORMAT = "REVENGINSTR.GhidraScalarUses/1"
SHIFT_FORMAT = "SHIFT.GhidraScalarUses/1"


def adapt_row(row: dict[str, Any], line_no: int) -> dict[str, Any]:
    if row.get("format") != GENERIC_FORMAT:
        raise ValueError(f"line {line_no}: expected {GENERIC_FORMAT}")
    adapted = dict(row)
    adapted["format"] = SHIFT_FORMAT
    return adapted


def adapt_file(source: Path, destination: Path) -> None:
    with source.open(encoding="utf-8") as input_file, destination.open("w", encoding="utf-8") as output_file:
        for line_no, line in enumerate(input_file, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{source}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{source}:{line_no}: expected an object")
            adapted = adapt_row(row, line_no)
            output_file.write(json.dumps(adapted, ensure_ascii=False, separators=(",", ":")) + "\n")


def main() -> int:
    if len(sys.argv) != 3:
        print(f"Usage: {Path(sys.argv[0]).name} <revenginstr.jsonl> <shift.jsonl>", file=sys.stderr)
        return 2
    try:
        adapt_file(Path(sys.argv[1]), Path(sys.argv[2]))
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
