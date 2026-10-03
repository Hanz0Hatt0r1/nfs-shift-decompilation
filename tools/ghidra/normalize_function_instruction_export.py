#!/usr/bin/env python3
"""Normalize targeted Ghidra instruction exports for legacy memory analyzers.

The targeted exporter currently emits SHIFT.GhidraFunctionInstructions/2 with
structured p-code. Existing memory analyzers predate that format and consume the
version-1 machine-instruction schema. This tool creates a separate v1-compatible
copy while preserving the original v2 file unchanged for p-code-based analysis.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

FORMAT_V1 = "SHIFT.GhidraFunctionInstructions/1"
FORMAT_V2 = "SHIFT.GhidraFunctionInstructions/2"
SUPPORTED_FORMATS = {FORMAT_V1, FORMAT_V2}


def read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            yield row


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    fmt = row.get("format")
    if fmt not in SUPPORTED_FORMATS:
        raise ValueError(f"unsupported instruction export format: {fmt!r}")

    normalized = dict(row)
    normalized["format"] = FORMAT_V1
    instructions = normalized.get("instructions")
    if isinstance(instructions, list):
        normalized_instructions: list[Any] = []
        for instruction in instructions:
            if not isinstance(instruction, dict):
                normalized_instructions.append(instruction)
                continue
            item = dict(instruction)
            item.pop("pcode", None)
            normalized_instructions.append(item)
        normalized["instructions"] = normalized_instructions
    return normalized


def normalize_export(source: Path, output: Path) -> dict[str, Any]:
    rows = list(read_jsonl(source))
    formats = sorted({str(row.get("format")) for row in rows})
    for row in rows:
        if row.get("format") not in SUPPORTED_FORMATS:
            raise ValueError(
                f"{source}: unsupported instruction export format {row.get('format')!r}"
            )

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(normalize_row(row), separators=(",", ":"), sort_keys=True))
            handle.write("\n")

    return {
        "source": str(source),
        "output": str(output),
        "input_formats": formats,
        "output_format": FORMAT_V1,
        "row_count": len(rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    report = normalize_export(args.source, args.output)
    print(f"rows: {report['row_count']}")
    print(f"input formats: {', '.join(report['input_formats'])}")
    print(f"output format: {report['output_format']}")
    print(f"output: {report['output']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
