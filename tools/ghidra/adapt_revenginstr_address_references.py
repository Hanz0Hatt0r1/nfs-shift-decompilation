#!/usr/bin/env python3
"""Adapt generic revenginstr address rows to the established Shift JSONL contract."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

GENERIC_FORMAT = "REVENGINSTR.GhidraAddressReferences/1"
SHIFT_FORMAT = "SHIFT.GhidraGlobalReferences/1"
ROW_FIELDS = (
    "program", "executable_md5", "requested", "resolved_address", "found",
    "primary_symbol", "data_type", "data_length", "reference_count",
    "function_addresses",
)
REFERENCE_FIELDS = (
    "from", "type", "operand_index", "primary",
    "function_address", "function_name", "instruction",
)


def adapt_row(row: dict[str, Any], line_no: int) -> dict[str, Any]:
    if row.get("format") != GENERIC_FORMAT:
        raise ValueError(f"line {line_no}: expected {GENERIC_FORMAT}")
    if not isinstance(row.get("references"), list):
        raise ValueError(f"line {line_no}: references must be a list")

    references = []
    for index, reference in enumerate(row["references"]):
        if not isinstance(reference, dict):
            raise ValueError(f"line {line_no} reference {index}: expected an object")
        missing = [field for field in REFERENCE_FIELDS if field not in reference]
        if missing:
            raise ValueError(f"line {line_no} reference {index}: missing {', '.join(missing)}")
        references.append({field: reference[field] for field in REFERENCE_FIELDS})

    missing = [field for field in ROW_FIELDS if field not in row]
    if missing:
        raise ValueError(f"line {line_no}: missing {', '.join(missing)}")
    return {
        "format": SHIFT_FORMAT,
        **{field: row[field] for field in ROW_FIELDS},
        "references": references,
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
