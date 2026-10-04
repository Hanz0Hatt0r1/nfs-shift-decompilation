#!/usr/bin/env python3
"""Inventory simple x86 register-relative memory accesses from targeted Ghidra p-code.

This analyzer is deliberately syntactic. A row such as [ECX + 0x18] is kept as
base register ECX plus displacement 0x18; ECX is not promoted to `this`, BODY,
vehicle, wheel or any other object without independent pointer-provenance
evidence.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT.GhidraRegisterRelativeAccesses/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
_GENERAL_REGISTERS = {"EAX", "EBX", "ECX", "EDX", "ESI", "EDI", "EBP", "ESP"}
_MEMORY_OPERAND = re.compile(
    r"^\s*(?:(?:byte|word|dword|qword|tword|xmmword|float|double)\s+ptr\s+)?"
    r"\[\s*([A-Za-z][A-Za-z0-9]*)\s*"
    r"(?:([+-])\s*(0x[0-9A-Fa-f]+|[0-9]+))?\s*\]\s*$",
    re.IGNORECASE,
)


def _read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
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


def _parse_displacement(sign: str | None, token: str | None) -> int:
    if token is None:
        return 0
    value = int(token, 0)
    return -value if sign == "-" else value


def _format_displacement(value: int) -> str:
    if value < 0:
        return f"-0x{-value:x}"
    return f"0x{value:x}"


def _parse_memory_operand(operand: str) -> tuple[str, int] | None:
    match = _MEMORY_OPERAND.fullmatch(operand)
    if match is None:
        return None
    register = match.group(1).upper()
    if register not in _GENERAL_REGISTERS:
        return None
    return register, _parse_displacement(match.group(2), match.group(3))


def _validate_pcode(pcode: Any, address: str) -> list[dict[str, str]]:
    if not isinstance(pcode, list):
        raise ValueError(f"{address}: pcode must be a list")
    result: list[dict[str, str]] = []
    for operation in pcode:
        if not isinstance(operation, dict):
            raise ValueError(f"{address}: pcode operation must be an object")
        opcode = operation.get("opcode")
        text = operation.get("text")
        if not isinstance(opcode, str) or not opcode:
            raise ValueError(f"{address}: pcode opcode missing")
        if not isinstance(text, str) or not text:
            raise ValueError(f"{address}: pcode text missing")
        result.append({"opcode": opcode.upper(), "text": text})
    return result


def _pcode_memory_kinds(pcode: list[dict[str, str]]) -> set[str]:
    return {
        operation["opcode"]
        for operation in pcode
        if operation["opcode"] in {"LOAD", "STORE"}
    }


def _access_kind(kinds: set[str]) -> str | None:
    if "LOAD" in kinds and "STORE" in kinds:
        return "read-write"
    if "STORE" in kinds:
        return "write"
    if "LOAD" in kinds:
        return "read"
    return None


def analyze_register_relative_accesses(
    export: Path,
    base_registers: Iterable[str] | None = None,
) -> dict[str, Any]:
    rows = list(_read_jsonl(export))
    if not rows:
        raise ValueError(f"{export}: empty instruction export")

    formats = {row.get("format") for row in rows}
    if formats != {INSTRUCTION_FORMAT}:
        found = ", ".join(sorted(map(str, formats)))
        raise ValueError(
            f"{export}: p-code access analysis requires {INSTRUCTION_FORMAT}; found {found}"
        )

    requested_registers = None
    if base_registers is not None:
        requested_registers = {value.upper() for value in base_registers}
        unknown = sorted(requested_registers - _GENERAL_REGISTERS)
        if unknown:
            raise ValueError("unsupported x86 base register(s): " + ", ".join(unknown))
        if not requested_registers:
            raise ValueError("base_registers filter must not be empty")

    accesses: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    unparsed: list[dict[str, Any]] = []
    filtered_access_count = 0
    function_count = 0
    instruction_count = 0

    for row in rows:
        if row.get("found") is not True:
            raise ValueError(f"{export}: unresolved target {row.get('requested')}")
        function = row.get("function")
        if not isinstance(function, dict) or not isinstance(function.get("address"), str):
            raise ValueError(f"{export}: function metadata missing")
        instructions = row.get("instructions")
        if not isinstance(instructions, list) or not instructions:
            raise ValueError(f"{function.get('address')}: instructions missing")
        function_count += 1
        instruction_count += len(instructions)

        for instruction in instructions:
            if not isinstance(instruction, dict):
                raise ValueError(f"{function.get('address')}: invalid instruction row")
            address = instruction.get("address")
            operands = instruction.get("operands")
            if not isinstance(address, str):
                raise ValueError(f"{function.get('address')}: instruction address missing")
            if not isinstance(operands, list) or any(not isinstance(value, str) for value in operands):
                raise ValueError(f"{address}: operands must be strings")
            pcode = _validate_pcode(instruction.get("pcode"), address)

            pcode_kinds = _pcode_memory_kinds(pcode)
            kind = _access_kind(pcode_kinds)
            for operand_index, operand in enumerate(operands):
                parsed = _parse_memory_operand(operand)
                if parsed is None:
                    if "[" in operand or "]" in operand:
                        unparsed.append(
                            {
                                "function": function.get("address"),
                                "function_name": function.get("name"),
                                "instruction": address,
                                "instruction_text": instruction.get("text"),
                                "operand_index": operand_index,
                                "operand": operand,
                                "status": "complex-or-unparsed-memory-operand",
                                "promoted": False,
                            }
                        )
                    continue

                base_register, displacement = parsed
                if requested_registers is not None and base_register not in requested_registers:
                    filtered_access_count += 1
                    continue

                common = {
                    "function": function.get("address"),
                    "function_name": function.get("name"),
                    "instruction": address,
                    "instruction_text": instruction.get("text"),
                    "operand_index": operand_index,
                    "operand": operand,
                    "base_register": base_register,
                    "displacement": displacement,
                    "displacement_hex": _format_displacement(displacement),
                    "pcode": pcode,
                    "pcode_memory_ops": sorted(pcode_kinds),
                    "promoted": False,
                }
                if kind is None:
                    blockers.append(
                        {
                            **common,
                            "status": "memory-operand-without-pcode-load-store",
                        }
                    )
                    continue
                accesses.append(
                    {
                        **common,
                        "access": kind,
                        "status": "syntactic-register-relative-memory-access",
                    }
                )

    accesses.sort(
        key=lambda row: (
            str(row["function"]),
            int(str(row["instruction"]), 16),
            int(row["operand_index"]),
        )
    )
    blockers.sort(key=lambda row: (str(row["function"]), str(row["instruction"])))
    unparsed.sort(key=lambda row: (str(row["function"]), str(row["instruction"])))

    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in accesses:
        grouped[(row["base_register"], row["displacement"])].append(row)
    access_groups = [
        {
            "base_register": base,
            "displacement": displacement,
            "displacement_hex": _format_displacement(displacement),
            "access_count": len(group_rows),
            "read_count": sum(row["access"] in {"read", "read-write"} for row in group_rows),
            "write_count": sum(row["access"] in {"write", "read-write"} for row in group_rows),
            "function_addresses": sorted({str(row["function"]) for row in group_rows}),
            "accesses": group_rows,
            "promoted": False,
        }
        for (base, displacement), group_rows in sorted(
            grouped.items(), key=lambda item: (item[0][0], item[0][1])
        )
    ]

    return {
        "format": FORMAT,
        "instruction_export": str(export),
        "instruction_export_format": INSTRUCTION_FORMAT,
        "base_register_filter": sorted(requested_registers) if requested_registers else None,
        "function_count": function_count,
        "instruction_count": instruction_count,
        "access_count": len(accesses),
        "access_group_count": len(access_groups),
        "write_access_count": sum(row["access"] in {"write", "read-write"} for row in accesses),
        "read_access_count": sum(row["access"] in {"read", "read-write"} for row in accesses),
        "filtered_access_count": filtered_access_count,
        "pcode_classification_blocker_count": len(blockers),
        "unparsed_memory_operand_count": len(unparsed),
        "accesses": accesses,
        "access_groups": access_groups,
        "pcode_classification_blockers": blockers,
        "unparsed_memory_operands": unparsed,
        "scope": {
            "pcode_load_store_required": True,
            "structured_pcode_opcode_used": True,
            "pcode_text_parsing_used_for_classification": False,
            "simple_register_plus_constant_operands_only": True,
            "x86_32_general_base_registers_only": True,
            "base_register_is_object_pointer": False,
            "base_register_is_this_pointer": False,
            "body_or_vehicle_identity_proven": False,
            "field_semantics_proven": False,
            "pointer_aliases_resolved": False,
            "persistent_state_writer_proven": False,
            "note": (
                "This artifact proves only that a selected machine instruction contains a simple "
                "x86 register-relative memory operand and that Ghidra p-code reports LOAD and/or "
                "STORE for that instruction. Object identity, pointer provenance, persistence and "
                "physical meaning require independent evidence."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument(
        "--base-register",
        dest="base_registers",
        action="append",
        help="optional x86 base-register filter; repeatable (for example ECX)",
    )
    parser.add_argument("--json-out", type=Path)
    parser.add_argument(
        "--fail-on-blocker",
        action="store_true",
        help="return non-zero when a simple memory operand lacks LOAD/STORE p-code or a memory operand cannot be parsed",
    )
    args = parser.parse_args()

    report = analyze_register_relative_accesses(
        args.instruction_export,
        base_registers=args.base_registers,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")

    print(f"format: {report['format']}")
    print(f"functions: {report['function_count']}")
    print(f"register-relative accesses: {report['access_count']}")
    print(f"access groups: {report['access_group_count']}")
    print(f"pcode blockers: {report['pcode_classification_blocker_count']}")
    print(f"unparsed memory operands: {report['unparsed_memory_operand_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    if args.fail_on_blocker and (
        report["pcode_classification_blocker_count"]
        or report["unparsed_memory_operand_count"]
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
