#!/usr/bin/env python3
"""Freeze indirect provider-dispatch callsites from targeted Ghidra instructions.

The analyzer intentionally proves only the machine-level virtual slot and keeps
object identity separate.  Source/PE contracts may cross-check the result later;
a matching displacement by itself is never promoted to provider ownership.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT.GhidraProviderDispatchCallsites/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"

EXPECTED: dict[int, tuple[int, ...]] = {
    0x007B3820: (0x14,),
    0x007B2210: (0x1C,),
    0x007B3F40: (0x20, 0x18),
}

SLOT_ROLES = {
    0x14: "acceptance",
    0x18: "solve",
    0x1C: "per-scalar-reset",
    0x20: "cleanup",
}

_MEMORY_CALL = re.compile(
    r"\[\s*([A-Za-z][A-Za-z0-9]*)\s*(?:\+\s*(0x[0-9A-Fa-f]+|[0-9]+))?\s*\]",
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


def _address(value: Any) -> int:
    if not isinstance(value, str):
        raise ValueError(f"expected hex address string, got {value!r}")
    return int(value, 16)


def _normalize_pcode(value: Any, address: str) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise ValueError(f"{address}: pcode must be a list")
    result: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError(f"{address}: invalid pcode operation")
        opcode = item.get("opcode")
        text = item.get("text")
        if not isinstance(opcode, str) or not isinstance(text, str):
            raise ValueError(f"{address}: invalid pcode opcode/text")
        result.append({"opcode": opcode.upper(), "text": text})
    return result


def _parse_indirect_slot(instruction: dict[str, Any]) -> tuple[str, int] | None:
    mnemonic = instruction.get("mnemonic")
    text = instruction.get("text")
    operands = instruction.get("operands")
    if not isinstance(mnemonic, str):
        if isinstance(text, str):
            mnemonic = text.split(None, 1)[0] if text.strip() else ""
        else:
            mnemonic = ""
    if mnemonic.upper() != "CALL":
        return None
    if not isinstance(operands, list) or not operands:
        raise ValueError(f"{instruction.get('address')}: CALL operands missing")
    if any(not isinstance(value, str) for value in operands):
        raise ValueError(f"{instruction.get('address')}: CALL operands must be strings")

    operand = operands[0]
    match = _MEMORY_CALL.search(operand)
    if match is None:
        return None
    base = match.group(1).upper()
    displacement = int(match.group(2), 0) if match.group(2) is not None else 0
    return base, displacement


def analyze(export: Path, context_before: int = 6) -> dict[str, Any]:
    if context_before < 0:
        raise ValueError("context_before must be non-negative")
    rows = list(_read_jsonl(export))
    if not rows:
        raise ValueError(f"{export}: empty instruction export")

    found_functions: set[int] = set()
    callsites: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []

    for row in rows:
        if row.get("format") != INSTRUCTION_FORMAT:
            raise ValueError(
                f"{export}: expected {INSTRUCTION_FORMAT}, found {row.get('format')!r}"
            )
        if row.get("found") is not True:
            raise ValueError(f"{export}: unresolved target {row.get('requested')}")
        function = row.get("function")
        if not isinstance(function, dict):
            raise ValueError(f"{export}: function metadata missing")
        function_address = _address(function.get("address"))
        if function_address not in EXPECTED:
            continue
        found_functions.add(function_address)

        instructions = row.get("instructions")
        if not isinstance(instructions, list) or not instructions:
            raise ValueError(f"0x{function_address:08x}: instructions missing")

        for index, instruction in enumerate(instructions):
            if not isinstance(instruction, dict):
                raise ValueError(f"0x{function_address:08x}: invalid instruction")
            parsed = _parse_indirect_slot(instruction)
            if parsed is None:
                continue
            base_register, slot = parsed
            if slot not in EXPECTED[function_address]:
                continue
            address = instruction.get("address")
            if not isinstance(address, str):
                raise ValueError(f"0x{function_address:08x}: callsite address missing")
            pcode = _normalize_pcode(instruction.get("pcode"), address)
            window = instructions[max(0, index - context_before):index]
            callsites.append(
                {
                    "function": f"0x{function_address:08x}",
                    "function_name": function.get("name"),
                    "instruction": address,
                    "instruction_text": instruction.get("text"),
                    "operand": instruction.get("operands", [None])[0],
                    "vtable_base_register": base_register,
                    "vtable_slot": f"0x{slot:02x}",
                    "role": SLOT_ROLES[slot],
                    "pcode": pcode,
                    "context_before": [
                        {
                            "address": item.get("address"),
                            "text": item.get("text"),
                            "operands": item.get("operands"),
                            "pcode": item.get("pcode"),
                        }
                        for item in window
                    ],
                    "slot_evidence_state": "verified",
                    "provider_identity_state": "unknown",
                    "promoted": False,
                }
            )

    missing_functions = sorted(set(EXPECTED) - found_functions)
    if missing_functions:
        raise ValueError(
            "missing required function export(s): "
            + ", ".join(f"0x{value:08x}" for value in missing_functions)
        )

    by_pair = {
        (int(row["function"], 16), int(row["vtable_slot"], 16)): row
        for row in callsites
    }
    for function, slots in EXPECTED.items():
        for slot in slots:
            if (function, slot) not in by_pair:
                blockers.append(
                    {
                        "function": f"0x{function:08x}",
                        "vtable_slot": f"0x{slot:02x}",
                        "role": SLOT_ROLES[slot],
                        "state": "unknown",
                        "reason": "expected indirect CALL not found in targeted instruction export",
                    }
                )

    duplicates: list[dict[str, Any]] = []
    for function, slots in EXPECTED.items():
        for slot in slots:
            matches = [
                row for row in callsites
                if int(row["function"], 16) == function
                and int(row["vtable_slot"], 16) == slot
            ]
            if len(matches) > 1:
                duplicates.append(
                    {
                        "function": f"0x{function:08x}",
                        "vtable_slot": f"0x{slot:02x}",
                        "role": SLOT_ROLES[slot],
                        "state": "ambiguous",
                        "instruction_addresses": [row["instruction"] for row in matches],
                    }
                )

    ready = not blockers and not duplicates and len(callsites) == 4
    return {
        "format": FORMAT,
        "instruction_export": str(export),
        "instruction_export_format": INSTRUCTION_FORMAT,
        "ready": ready,
        "callsite_count": len(callsites),
        "callsites": callsites,
        "blockers": blockers,
        "ambiguities": duplicates,
        "evidence_boundary": {
            "vtable_slot_from_instruction": "verified when ready",
            "provider_object_identity_from_slot_syntax": "unknown",
            "ownership_from_pointer_similarity": "unknown",
            "semantic_crosscheck_required": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--context-before", type=int, default=6)
    args = parser.parse_args()

    result = analyze(args.instruction_export, args.context_before)
    payload = json.dumps(result, indent=2, sort_keys=True)
    if args.json_out is None:
        print(payload)
    else:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload + "\n", encoding="utf-8")
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
