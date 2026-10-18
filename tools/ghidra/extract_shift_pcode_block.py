#!/usr/bin/env python3
"""Extract one contiguous P-code block from a SHIFT Ghidra function row.

Ghidra can split a machine-level loop across function entries and non-contiguous
blocks. This adapter emits a bounded synthetic entry row when runtime dispatch
needs an address inside a larger Ghidra function to be exported independently.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


FORMAT = "SHIFT.GhidraFunctionInstructions/2"
TERMINAL_FLOWS = {
    "CALL_TERMINATOR",
    "COMPUTED_JUMP",
    "TERMINATOR",
    "UNCONDITIONAL_JUMP",
}


def _address(value: str) -> int:
    return int(value, 16)


def extract_block(source_path: Path, start: str, end: str) -> dict:
    start_value = _address(start)
    end_value = _address(end)
    if end_value < start_value:
        raise ValueError("block end precedes its entry")

    source_row = None
    selected = []
    with source_path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            row = json.loads(line)
            if row.get("format") != FORMAT or row.get("found") is not True:
                continue
            instructions = row.get("instructions")
            if not isinstance(instructions, list):
                continue
            matches = [instruction for instruction in instructions
                       if start_value <= _address(instruction["address"]) <= end_value]
            if matches:
                if source_row is not None:
                    raise ValueError("block instructions are split across source functions")
                source_row = row
                selected = matches

    if source_row is None or not selected:
        raise ValueError("source export does not contain the requested block")
    if _address(selected[0]["address"]) != start_value:
        raise ValueError("source export does not start at the requested block entry")

    expected = start_value
    for instruction in selected:
        address = _address(instruction["address"])
        if address != expected:
            raise ValueError(f"instruction coverage has a gap at 0x{expected:08x}")
        instruction_size = len(instruction["bytes"]) // 2
        if instruction_size == 0 or len(instruction["bytes"]) % 2:
            raise ValueError(f"invalid instruction bytes at 0x{address:08x}")
        expected = address + instruction_size
    if expected - 1 != end_value:
        raise ValueError("requested block end is not the final instruction byte")
    if selected[-1].get("flow_type") not in TERMINAL_FLOWS:
        raise ValueError("block must end with a terminal control-flow instruction")

    entry = f"0x{start_value:08x}"
    return {
        "format": FORMAT,
        "program": source_row["program"],
        "requested": entry,
        "found": True,
        "function": {
            "address": entry,
            "name": f"FUN_{start_value:08x}",
            "size": end_value - start_value + 1,
            "calling_convention": source_row["function"].get(
                "calling_convention", "unknown"),
        },
        "instruction_count": len(selected),
        "instructions": selected,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("start")
    parser.add_argument("end", help="inclusive final byte address")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    row = extract_block(args.source, args.start, args.end)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(row, separators=(",", ":")) + "\n",
                           encoding="utf-8")
    print(f"extracted {row['instruction_count']} instructions at {row['requested']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
