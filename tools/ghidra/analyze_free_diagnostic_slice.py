#!/usr/bin/env python3
"""Trace the retail pool-free diagnostic `%p` back to physical entry storage.

The analyzer targets FUN_00657c30 and the exact diagnostic
`Error freeing small alloc (no head) '0x%p' from pool: '%s'`. It requires a
straight-line nearby CALL with cdecl-style PUSH arguments, then traces simple
register copies and standard EBP-frame stack loads backwards. A positive result
identifies only the physical FUN_00657c30 entry storage supplying `%p`; it does
not yet prove how that value reaches FUN_00657c30 through the release backend
chain, nor does it assign release-flag/delete-kind semantics.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT-MEMORY-FREE-DIAGNOSTIC-SLICE/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/1"
FUNCTION_ADDRESS = "0x00657c30"
FREE_DIAGNOSTIC = re.compile(r"Error freeing .*0x%p.*from pool.*%s", re.IGNORECASE)
SIZE_PREFIX = re.compile(r"^(?:BYTE|WORD|DWORD|QWORD)\s+PTR\s+", re.IGNORECASE)
EBP_MEMORY = re.compile(
    r"^\[EBP(?:\s*([+-])\s*(0X[0-9A-F]+|[0-9]+))?\]$", re.IGNORECASE
)
REGISTER_NAMES = {
    "EAX", "EBX", "ECX", "EDX", "ESI", "EDI", "EBP", "ESP",
    "AL", "AH", "BL", "BH", "CL", "CH", "DL", "DH",
}
VOLATILE_REGISTERS = {"EAX", "ECX", "EDX", "AL", "AH", "CL", "CH", "DL", "DH"}
MAX_CALL_DISTANCE = 12
MAX_BACKTRACE = 64


def _norm_address(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    token = value.strip().lower()
    if token.startswith("fun_"):
        token = token[4:]
    if token.startswith("0x"):
        token = token[2:]
    try:
        return f"0x{int(token, 16):08x}"
    except ValueError:
        return None


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


def _clean_operand(value: str) -> str:
    value = SIZE_PREFIX.sub("", value.strip()).strip()
    return re.sub(r"\s+", " ", value).upper()


def _parse_immediate(value: str) -> int | None:
    token = _clean_operand(value)
    try:
        if token.startswith("0X"):
            return int(token, 16)
        if token.endswith("H") and re.fullmatch(r"[0-9A-F]+H", token):
            return int(token[:-1], 16)
        if re.fullmatch(r"-?[0-9]+", token):
            return int(token, 10)
    except ValueError:
        return None
    return None


def _load_function(path: Path) -> dict[str, Any]:
    for row in _read_jsonl(path):
        if row.get("format") != INSTRUCTION_FORMAT:
            raise ValueError(f"{path}: expected {INSTRUCTION_FORMAT}")
        function = row.get("function")
        if not isinstance(function, dict):
            continue
        if _norm_address(function.get("address")) == FUNCTION_ADDRESS:
            if row.get("found") is not True:
                raise ValueError(f"{path}: {FUNCTION_ADDRESS} is unresolved")
            return row
    raise ValueError(f"{path}: missing {FUNCTION_ADDRESS}")


def _load_diagnostic(root: Path) -> dict[str, Any]:
    path = root / "strings_xrefs.jsonl"
    if not path.is_file():
        raise FileNotFoundError(f"missing required Ghidra file: {path}")
    matches: list[dict[str, Any]] = []
    for row in _read_jsonl(path):
        value = row.get("value")
        if not isinstance(value, str) or not FREE_DIAGNOSTIC.search(value):
            continue
        functions = {
            normalized
            for item in (row.get("functions") or [])
            if (normalized := _norm_address(item)) is not None
        }
        if FUNCTION_ADDRESS not in functions:
            continue
        matches.append(
            {
                "string_address": _norm_address(row.get("address")),
                "value": value,
                "xrefs": [
                    normalized
                    for item in (row.get("xrefs") or [])
                    if (normalized := _norm_address(item)) is not None
                ],
            }
        )
    if len(matches) != 1:
        raise ValueError(
            f"expected exactly one free diagnostic in {FUNCTION_ADDRESS}, found {len(matches)}"
        )
    return matches[0]


def _references_address(instruction: dict[str, Any], address: str | None) -> bool:
    if address is None:
        return False
    return any(
        isinstance(ref, dict) and _norm_address(ref.get("to")) == address
        for ref in (instruction.get("references") or [])
    )


def _call_target(instruction: dict[str, Any]) -> str | None:
    for ref in instruction.get("references") or []:
        if not isinstance(ref, dict):
            continue
        if "CALL" not in str(ref.get("type") or "").upper():
            continue
        target = _norm_address(ref.get("to"))
        if target is not None:
            return target
    for value in instruction.get("flows") or []:
        target = _norm_address(value)
        if target is not None:
            return target
    return None


def _standard_ebp_frame(instructions: list[dict[str, Any]], before: int) -> bool:
    for index in range(min(before, 8)):
        instruction = instructions[index]
        mnemonic = str(instruction.get("mnemonic") or "").upper()
        operands = [_clean_operand(str(value)) for value in (instruction.get("operands") or [])]
        if mnemonic == "MOV" and operands == ["EBP", "ESP"]:
            return any(
                str(instructions[earlier].get("mnemonic") or "").upper() == "PUSH"
                and [_clean_operand(str(value)) for value in (instructions[earlier].get("operands") or [])]
                == ["EBP"]
                for earlier in range(index)
            )
    return False


def _ebp_entry_storage(instructions: list[dict[str, Any]], before: int, operand: str) -> str | None:
    match = EBP_MEMORY.match(_clean_operand(operand))
    if match is None or not _standard_ebp_frame(instructions, before):
        return None
    displacement = 0
    if match.group(2):
        raw = int(match.group(2), 0)
        displacement = -raw if match.group(1) == "-" else raw
    if displacement < 8 or displacement % 4:
        return None
    return f"Stack[0x{displacement - 4:x}]:4"


def _written_register(instruction: dict[str, Any]) -> str | None:
    mnemonic = str(instruction.get("mnemonic") or "").upper()
    operands = [_clean_operand(str(value)) for value in (instruction.get("operands") or [])]
    if not operands or operands[0] not in REGISTER_NAMES:
        return None
    if mnemonic in {"MOV", "LEA", "MOVZX", "MOVSX", "XOR", "ADD", "SUB", "AND", "OR", "POP"}:
        return operands[0]
    return None


def _resolve_register(
    instructions: list[dict[str, Any]], before: int, register: str, depth: int
) -> tuple[str, list[str]]:
    reg = register.upper()
    if depth > 10:
        return "unresolved", ["register recursion limit reached"]
    for index in range(before - 1, max(-1, before - MAX_BACKTRACE - 1), -1):
        instruction = instructions[index]
        mnemonic = str(instruction.get("mnemonic") or "").upper()
        if mnemonic == "CALL" and reg in VOLATILE_REGISTERS:
            return "unresolved", [f"{instruction.get('address')} CALL clobbers {reg}"]
        if _written_register(instruction) != reg:
            continue
        operands = [str(value) for value in (instruction.get("operands") or [])]
        if mnemonic == "MOV" and len(operands) == 2:
            return _resolve_operand(instructions, index, operands[1], depth + 1)
        if mnemonic in {"MOVZX", "MOVSX"} and len(operands) == 2:
            source, reasons = _resolve_operand(instructions, index, operands[1], depth + 1)
            return (f"{mnemonic.lower()}({source})" if source != "unresolved" else source, reasons)
        if mnemonic == "XOR" and len(operands) == 2 and _clean_operand(operands[0]) == _clean_operand(operands[1]):
            return "constant:0x0", []
        return "unresolved", [f"{instruction.get('address')} unsupported write to {reg}: {mnemonic}"]
    if reg in {"ECX", "EDX"}:
        return f"entry:{reg}:4", []
    if reg == "DL":
        return "entry:DL:1", []
    return "unresolved", [f"{reg} has no traceable entry value"]


def _resolve_operand(
    instructions: list[dict[str, Any]], before: int, operand: str, depth: int = 0
) -> tuple[str, list[str]]:
    cleaned = _clean_operand(operand)
    if cleaned in REGISTER_NAMES:
        return _resolve_register(instructions, before, cleaned, depth)
    stack = _ebp_entry_storage(instructions, before, cleaned)
    if stack is not None:
        return f"entry:{stack}", []
    immediate = _parse_immediate(cleaned)
    if immediate is not None:
        return f"constant:0x{immediate & 0xffffffff:x}", []
    return "unresolved", [f"unsupported operand source: {operand}"]


def _find_call_after(instructions: list[dict[str, Any]], start: int) -> int | None:
    for index in range(start + 1, min(len(instructions), start + MAX_CALL_DISTANCE + 1)):
        mnemonic = str(instructions[index].get("mnemonic") or "").upper()
        if mnemonic == "CALL":
            return index
        if mnemonic.startswith("RET") or mnemonic.startswith("J"):
            return None
    return None


def _setup_pushes(instructions: list[dict[str, Any]], call_index: int) -> list[int]:
    pushes: list[int] = []
    for index in range(call_index - 1, max(-1, call_index - MAX_CALL_DISTANCE - 1), -1):
        mnemonic = str(instructions[index].get("mnemonic") or "").upper()
        if mnemonic == "PUSH":
            pushes.append(index)
            continue
        if mnemonic == "CALL" or mnemonic.startswith("RET") or mnemonic.startswith("J"):
            break
    pushes.reverse()
    return pushes


def _entry_storage(source: str) -> str | None:
    return source[6:] if source.startswith("entry:") else None


def _analyze_site(
    instructions: list[dict[str, Any]], xref_index: int, diagnostic: dict[str, Any]
) -> dict[str, Any]:
    call_index = _find_call_after(instructions, xref_index)
    if call_index is None:
        return {
            "xref_instruction": _norm_address(instructions[xref_index].get("address")),
            "diagnostic_call_found": False,
            "pointer_role_proven": False,
            "reasons": ["no straight-line CALL found after diagnostic xref"],
        }
    pushes = _setup_pushes(instructions, call_index)
    arguments: list[dict[str, Any]] = []
    for argument_index, push_index in enumerate(reversed(pushes)):
        instruction = instructions[push_index]
        operands = [str(value) for value in (instruction.get("operands") or [])]
        operand = operands[0] if len(operands) == 1 else ""
        source, reasons = _resolve_operand(instructions, push_index, operand)
        is_format = _references_address(instruction, diagnostic["string_address"])
        arguments.append(
            {
                "argument_index": argument_index,
                "push_instruction": _norm_address(instruction.get("address")),
                "operand": operand,
                "source": "diagnostic-format" if is_format else source,
                "entry_storage": None if is_format else _entry_storage(source),
                "resolved": is_format or source != "unresolved",
                "diagnostic_format": is_format,
                "reasons": reasons,
            }
        )
    shape = bool(len(arguments) >= 3 and arguments[0]["diagnostic_format"] is True)
    pointer_arg = arguments[1] if shape else None
    pool_string_arg = arguments[2] if shape else None
    pointer_storage = pointer_arg.get("entry_storage") if pointer_arg else None
    role_proven = isinstance(pointer_storage, str) and bool(pointer_storage)
    return {
        "xref_instruction": _norm_address(instructions[xref_index].get("address")),
        "diagnostic_call_found": True,
        "diagnostic_call_instruction": _norm_address(instructions[call_index].get("address")),
        "diagnostic_call_target": _call_target(instructions[call_index]),
        "push_argument_count": len(arguments),
        "arguments": arguments,
        "cdecl_style_format_first_stack_shape": shape,
        "pointer_vararg": pointer_arg,
        "pool_string_vararg": pool_string_arg,
        "free_pointer_entry_storage": pointer_storage if role_proven else None,
        "pointer_role_proven": role_proven,
        "argument_slice_proven": bool(shape and role_proven),
        "reasons": [] if shape else [
            "diagnostic format was not recovered as stack argument 0 with `%p` and `%s` varargs"
        ],
    }


def analyze_free_diagnostic_slice(instruction_export: Path, ghidra_export: Path) -> dict[str, Any]:
    row = _load_function(instruction_export)
    diagnostic = _load_diagnostic(ghidra_export)
    instructions = [item for item in (row.get("instructions") or []) if isinstance(item, dict)]
    index_by_address = {
        normalized: index
        for index, item in enumerate(instructions)
        if (normalized := _norm_address(item.get("address"))) is not None
    }
    xref_indices = [index_by_address[xref] for xref in diagnostic["xrefs"] if xref in index_by_address]
    sites = [_analyze_site(instructions, index, diagnostic) for index in xref_indices]
    proven_sites = [site for site in sites if site.get("argument_slice_proven") is True]
    storages = sorted(
        {
            str(site["free_pointer_entry_storage"])
            for site in proven_sites
            if site.get("free_pointer_entry_storage")
        }
    )
    role_proven = len(storages) == 1 and bool(proven_sites)
    return {
        "format": FORMAT,
        "instruction_export": str(instruction_export),
        "ghidra_export": str(ghidra_export),
        "function": FUNCTION_ADDRESS,
        "diagnostic": diagnostic,
        "instruction_count": len(instructions),
        "diagnostic_xref_count": len(diagnostic["xrefs"]),
        "covered_diagnostic_xref_count": len(xref_indices),
        "sites": sites,
        "proven_site_count": len(proven_sites),
        "free_pointer_entry_storage": storages[0] if role_proven else None,
        "free_pointer_role_proven": role_proven,
        "scope": {
            "local_straight_line_x86_slice_used": True,
            "cdecl_style_push_order_required": True,
            "free_pointer_role_proven": role_proven,
            "pool_diagnostic_string_source_observed": any(
                site.get("pool_string_vararg") is not None for site in proven_sites
            ),
            "pool_selector_role_proven": False,
            "release_chain_argument_provenance_proven": False,
            "release_flag_role_proven": False,
            "operator_delete_identity_proven": False,
            "ownership_semantics_proven": False,
            "note": (
                "A positive result identifies only the physical FUN_00657c30 entry storage "
                "supplying the exact retail free diagnostic `%p`. The value must still be "
                "traced through the release backend chain before a wrapper/source argument is "
                "promoted to released-pointer semantics."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("--ghidra-export", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    report = analyze_free_diagnostic_slice(args.instruction_export, args.ghidra_export)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"covered diagnostic xrefs: {report['covered_diagnostic_xref_count']}")
    print(f"proven diagnostic slices: {report['proven_site_count']}")
    print(f"free pointer role proven: {report['free_pointer_role_proven']}")
    print(f"free pointer entry storage: {report['free_pointer_entry_storage']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
