#!/usr/bin/env python3
"""Validate targeted SHIFT Ghidra function-instruction JSONL exports."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable

FORMAT_V1 = "SHIFT.GhidraFunctionInstructions/1"
FORMAT_V2 = "SHIFT.GhidraFunctionInstructions/2"
FORMAT = FORMAT_V2
SUPPORTED_FORMATS = {FORMAT_V1, FORMAT_V2}
_HEX_BYTES = re.compile(r"(?:[0-9a-f]{2})+")
_ADDRESS = re.compile(r"^(?:0x)?([0-9a-fA-F]+)$")
_FUNCTION = re.compile(r"^FUN_([0-9a-fA-F]+)$", re.IGNORECASE)


def normalize_target(value: str) -> str:
    token = value.strip()
    match = _FUNCTION.fullmatch(token)
    if match:
        token = match.group(1)
    match = _ADDRESS.fullmatch(token)
    if not match:
        raise ValueError(f"invalid function address: {value}")
    return f"0x{int(match.group(1), 16):08x}"


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


def validate_instruction(
    instruction: dict[str, Any],
    function_address: str,
    export_format: str = FORMAT_V1,
) -> None:
    address = instruction.get("address")
    if not isinstance(address, str) or not address.startswith("0x"):
        raise ValueError(f"{function_address}: instruction missing address")
    payload = instruction.get("bytes")
    if not isinstance(payload, str) or _HEX_BYTES.fullmatch(payload) is None:
        raise ValueError(f"{function_address}: invalid instruction bytes at {address}")
    if not isinstance(instruction.get("mnemonic"), str) or not instruction["mnemonic"]:
        raise ValueError(f"{function_address}: missing mnemonic at {address}")
    if not isinstance(instruction.get("text"), str) or not instruction["text"]:
        raise ValueError(f"{function_address}: missing instruction text at {address}")
    if not isinstance(instruction.get("operands"), list):
        raise ValueError(f"{function_address}: operands must be a list at {address}")
    if not isinstance(instruction.get("references"), list):
        raise ValueError(f"{function_address}: references must be a list at {address}")
    if not isinstance(instruction.get("flows"), list):
        raise ValueError(f"{function_address}: flows must be a list at {address}")

    if export_format == FORMAT_V2:
        pcode = instruction.get("pcode")
        if not isinstance(pcode, list):
            raise ValueError(f"{function_address}: pcode must be a list at {address}")
        for operation in pcode:
            if not isinstance(operation, dict):
                raise ValueError(f"{function_address}: pcode operation must be an object at {address}")
            opcode = operation.get("opcode")
            text = operation.get("text")
            if not isinstance(opcode, str) or not opcode:
                raise ValueError(f"{function_address}: pcode opcode missing at {address}")
            if not isinstance(text, str) or not text:
                raise ValueError(f"{function_address}: pcode text missing at {address}")


def validate_export(path: Path, expected_targets: list[str]) -> dict[str, Any]:
    expected = [normalize_target(value) for value in expected_targets]
    if len(set(expected)) != len(expected):
        raise ValueError("duplicate requested function addresses")

    rows = list(read_jsonl(path))
    if len(rows) != len(expected):
        raise ValueError(
            f"{path}: expected {len(expected)} rows, found {len(rows)}"
        )

    observed_formats = {row.get("format") for row in rows}
    unsupported = sorted(
        str(value) for value in observed_formats if value not in SUPPORTED_FORMATS
    )
    if unsupported:
        raise ValueError(
            f"{path}: unsupported instruction export format(s): {', '.join(unsupported)}"
        )
    if len(observed_formats) != 1:
        raise ValueError(f"{path}: mixed instruction export formats are not allowed")
    export_format = next(iter(observed_formats), FORMAT_V1)

    by_address: dict[str, dict[str, Any]] = {}
    total_instructions = 0
    for row in rows:
        if row.get("found") is not True:
            raise ValueError(f"{path}: unresolved target {row.get('requested')}")
        function = row.get("function")
        if not isinstance(function, dict):
            raise ValueError(f"{path}: missing function metadata")
        function_address = normalize_target(str(function.get("address")))
        if function_address in by_address:
            raise ValueError(f"{path}: duplicate function row {function_address}")

        instructions = row.get("instructions")
        if not isinstance(instructions, list) or not instructions:
            raise ValueError(f"{function_address}: instruction list is empty")
        if row.get("instruction_count") != len(instructions):
            raise ValueError(f"{function_address}: instruction_count mismatch")
        if normalize_target(str(instructions[0].get("address"))) != function_address:
            raise ValueError(f"{function_address}: first instruction is not function entry")

        previous = -1
        for instruction in instructions:
            if not isinstance(instruction, dict):
                raise ValueError(f"{function_address}: invalid instruction row")
            validate_instruction(instruction, function_address, export_format)
            current = int(normalize_target(instruction["address"]), 16)
            if current <= previous:
                raise ValueError(f"{function_address}: instruction addresses not increasing")
            previous = current
        total_instructions += len(instructions)
        by_address[function_address] = row

    missing = [address for address in expected if address not in by_address]
    expected_set = set(expected)
    extra = [address for address in by_address if address not in expected_set]
    if missing or extra:
        raise ValueError(f"target mismatch: missing={missing}, extra={extra}")

    return {
        "format": export_format,
        "function_count": len(rows),
        "instruction_count": total_instructions,
        "functions": expected,
        "pcode_available": export_format == FORMAT_V2,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export", type=Path)
    parser.add_argument("targets", nargs="+")
    args = parser.parse_args()
    report = validate_export(args.export, args.targets)
    print(f"format: {report['format']}")
    print(f"functions: {report['function_count']}")
    print(f"instructions: {report['instruction_count']}")
    print(f"pcode available: {str(report['pcode_available']).lower()}")
    print("function instruction export: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
