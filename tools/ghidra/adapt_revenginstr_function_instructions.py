#!/usr/bin/env python3
"""Adapt generic revenginstr instruction rows to the established Shift JSONL contract."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

GENERIC_FORMAT = "REVENGINSTR.GhidraFunctionInstructions/1"
SHIFT_FORMAT = "SHIFT.GhidraFunctionInstructions/2"


def adapt_row(row: dict[str, Any], line_no: int) -> dict[str, Any]:
    if row.get("format") != GENERIC_FORMAT:
        raise ValueError(f"line {line_no}: expected {GENERIC_FORMAT}")
    if not isinstance(row.get("program"), str) or not isinstance(row.get("requested"), str):
        raise ValueError(f"line {line_no}: missing program or requested target")
    if not isinstance(row.get("found"), bool):
        raise ValueError(f"line {line_no}: found must be boolean")

    if row["found"]:
        function = row.get("function")
        address = row.get("resolved_address")
        if not isinstance(function, dict) or not isinstance(address, str):
            raise ValueError(f"line {line_no}: found row has no resolved function address")
        if function.get("address") != address:
            raise ValueError(f"line {line_no}: resolved address does not match function address")
        return {
            "format": SHIFT_FORMAT,
            "program": row["program"],
            "requested": address,
            "found": True,
            "function": function,
            "instruction_count": row.get("instruction_count"),
            "instructions": row.get("instructions"),
        }

    if row.get("function") is not None:
        raise ValueError(f"line {line_no}: missing target must not have function metadata")
    return {
        "format": SHIFT_FORMAT,
        "program": row["program"],
        "requested": row["requested"],
        "resolved_address": row.get("resolved_address"),
        "found": False,
        "function": None,
        "instruction_count": row.get("instruction_count"),
        "instructions": row.get("instructions"),
    }


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
    adapt_file(Path(sys.argv[1]), Path(sys.argv[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
