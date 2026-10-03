#!/usr/bin/env python3
"""Trace the proven free-diagnostic pointer backwards through release backends.

The free-diagnostic slice independently identifies which physical entry storage
of FUN_00657c30 supplies `%p`. This analyzer then follows that exact storage
backwards across the direct transfer from FUN_0064f3a0 and the release thunk
0x0064f4c0. It proves only physical value provenance. It does not assign any
semantic role to DL or infer delete-kind, release flags, operator delete or
ownership behavior.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT-MEMORY-RELEASE-POINTER-CHAIN/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/1"
FREE_SLICE_FORMAT = "SHIFT-MEMORY-FREE-DIAGNOSTIC-SLICE/1"
RELEASE_THUNK = "0x0064f4c0"
RELEASE_BACKEND = "0x0064f3a0"
FREE_BACKEND = "0x00657c30"
SIZE_PREFIX = re.compile(r"^(?:BYTE|WORD|DWORD|QWORD)\s+PTR\s+", re.IGNORECASE)
STACK_STORAGE = re.compile(r"^Stack\[0x([0-9a-fA-F]+)\]:(\d+)$")
EBP_MEMORY = re.compile(
    r"^\[EBP(?:\s*([+-])\s*(0X[0-9A-F]+|[0-9]+))?\]$", re.IGNORECASE
)
REGISTER_NAMES = {
    "EAX", "EBX", "ECX", "EDX", "ESI", "EDI", "EBP", "ESP",
    "AL", "AH", "BL", "BH", "CL", "CH", "DL", "DH",
}
VOLATILE_REGISTERS = {"EAX", "ECX", "EDX", "AL", "AH", "CL", "CH", "DL", "DH"}
MAX_BACKTRACE = 80
MAX_PUSH_SCAN = 16


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


def _load_rows(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(path):
        if row.get("format") != INSTRUCTION_FORMAT:
            raise ValueError(f"{path}: expected {INSTRUCTION_FORMAT}")
        if row.get("found") is not True:
            continue
        function = row.get("function")
        if not isinstance(function, dict):
            continue
        address = _norm_address(function.get("address"))
        if address is not None:
            rows[address] = row
    missing = [address for address in (RELEASE_THUNK, RELEASE_BACKEND, FREE_BACKEND) if address not in rows]
    if missing:
        raise ValueError("instruction export missing release-chain functions: " + ", ".join(missing))
    return rows


def _load_free_slice(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("format") != FREE_SLICE_FORMAT:
        raise ValueError(f"{path}: expected {FREE_SLICE_FORMAT}")
    return value


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


def _standard_ebp_frame(instructions: list[dict[str, Any]], before: int) -> bool:
    for index in range(min(before, 8)):
        mnemonic = str(instructions[index].get("mnemonic") or "").upper()
        operands = [_clean_operand(str(v)) for v in (instructions[index].get("operands") or [])]
        if mnemonic == "MOV" and operands == ["EBP", "ESP"]:
            return any(
                str(instructions[i].get("mnemonic") or "").upper() == "PUSH"
                and [_clean_operand(str(v)) for v in (instructions[i].get("operands") or [])] == ["EBP"]
                for i in range(index)
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
    operands = [_clean_operand(str(v)) for v in (instruction.get("operands") or [])]
    if not operands or operands[0] not in REGISTER_NAMES:
        return None
    if mnemonic in {"MOV", "LEA", "MOVZX", "MOVSX", "XOR", "ADD", "SUB", "AND", "OR", "POP"}:
        return operands[0]
    return None


def _resolve_register(
    instructions: list[dict[str, Any]], before: int, register: str, depth: int = 0
) -> tuple[str, list[str]]:
    reg = register.upper()
    if depth > 10:
        return "unresolved", ["register recursion limit reached"]
    for index in range(before - 1, max(-1, before - MAX_BACKTRACE - 1), -1):
        ins = instructions[index]
        mnemonic = str(ins.get("mnemonic") or "").upper()
        if mnemonic == "CALL" and reg in VOLATILE_REGISTERS:
            return "unresolved", [f"{ins.get('address')} CALL clobbers {reg}"]
        if _written_register(ins) != reg:
            continue
        operands = [str(v) for v in (ins.get("operands") or [])]
        if mnemonic == "MOV" and len(operands) == 2:
            return _resolve_operand(instructions, index, operands[1], depth + 1)
        if mnemonic in {"MOVZX", "MOVSX"} and len(operands) == 2:
            source, reasons = _resolve_operand(instructions, index, operands[1], depth + 1)
            return (f"{mnemonic.lower()}({source})" if source != "unresolved" else source, reasons)
        if mnemonic == "XOR" and len(operands) == 2 and _clean_operand(operands[0]) == _clean_operand(operands[1]):
            return "constant:0x0", []
        return "unresolved", [f"{ins.get('address')} unsupported write to {reg}: {mnemonic}"]
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


def _transfer_target(instruction: dict[str, Any]) -> str | None:
    for ref in instruction.get("references") or []:
        if not isinstance(ref, dict):
            continue
        ref_type = str(ref.get("type") or "").upper()
        if "CALL" not in ref_type and "JUMP" not in ref_type:
            continue
        target = _norm_address(ref.get("to"))
        if target is not None:
            return target
    for value in instruction.get("flows") or []:
        target = _norm_address(value)
        if target is not None:
            return target
    return None


def _find_transfer(instructions: list[dict[str, Any]], target: str, allowed: set[str]) -> tuple[int, str] | None:
    matches: list[tuple[int, str]] = []
    for index, ins in enumerate(instructions):
        mnemonic = str(ins.get("mnemonic") or "").upper()
        if mnemonic not in allowed:
            continue
        if _transfer_target(ins) == target:
            matches.append((index, mnemonic))
    return matches[0] if len(matches) == 1 else None


def _setup_pushes_backwards(instructions: list[dict[str, Any]], transfer_index: int) -> list[int]:
    pushes: list[int] = []
    for index in range(transfer_index - 1, max(-1, transfer_index - MAX_PUSH_SCAN - 1), -1):
        mnemonic = str(instructions[index].get("mnemonic") or "").upper()
        if mnemonic == "PUSH":
            pushes.append(index)
            continue
        if mnemonic == "CALL" or mnemonic.startswith("RET") or mnemonic.startswith("J"):
            break
    return pushes


def _source_for_target_storage(
    instructions: list[dict[str, Any]], transfer_index: int, storage: str, *, tail: bool
) -> tuple[str, list[str]]:
    if storage.startswith("Stack["):
        if tail:
            return "unresolved", ["stack-parameter tail-transfer mapping is not modeled"]
        match = STACK_STORAGE.match(storage)
        if match is None:
            return "unresolved", [f"unsupported target stack storage: {storage}"]
        offset = int(match.group(1), 16)
        if offset < 4 or offset % 4:
            return "unresolved", [f"invalid target stack storage: {storage}"]
        argument_index = offset // 4 - 1
        pushes = _setup_pushes_backwards(instructions, transfer_index)
        if argument_index >= len(pushes):
            return "unresolved", [f"missing PUSH for target {storage}"]
        push = instructions[pushes[argument_index]]
        operands = [str(v) for v in (push.get("operands") or [])]
        if len(operands) != 1:
            return "unresolved", [f"{push.get('address')} malformed PUSH"]
        return _resolve_operand(instructions, pushes[argument_index], operands[0])

    register = storage.split(":", 1)[0].upper()
    if register not in REGISTER_NAMES:
        return "unresolved", [f"unsupported target storage: {storage}"]
    return _resolve_register(instructions, transfer_index, register)


def _entry_storage(source: str) -> str | None:
    return source[6:] if source.startswith("entry:") else None


def _hop(
    row: dict[str, Any], source_function: str, target_function: str, target_storage: str, allowed: set[str]
) -> dict[str, Any]:
    instructions = [item for item in (row.get("instructions") or []) if isinstance(item, dict)]
    transfer = _find_transfer(instructions, target_function, allowed)
    if transfer is None:
        return {
            "from": source_function,
            "to": target_function,
            "target_storage": target_storage,
            "proven": False,
            "source_entry_storage": None,
            "reasons": ["expected exactly one direct transfer to target"],
        }
    index, mnemonic = transfer
    source, reasons = _source_for_target_storage(
        instructions, index, target_storage, tail=mnemonic == "JMP"
    )
    entry = _entry_storage(source)
    return {
        "from": source_function,
        "to": target_function,
        "instruction": _norm_address(instructions[index].get("address")),
        "transfer_kind": "tail-call" if mnemonic == "JMP" else "call",
        "target_storage": target_storage,
        "source": source,
        "source_entry_storage": entry,
        "proven": entry is not None,
        "reasons": reasons,
    }


def analyze_release_pointer_chain(instruction_export: Path, free_slice_path: Path) -> dict[str, Any]:
    rows = _load_rows(instruction_export)
    free_slice = _load_free_slice(free_slice_path)
    free_role_proven = free_slice.get("free_pointer_role_proven") is True
    free_storage = (
        str(free_slice.get("free_pointer_entry_storage"))
        if free_role_proven and free_slice.get("free_pointer_entry_storage")
        else None
    )

    backend_hop = None
    thunk_hop = None
    backend_storage = None
    thunk_storage = None
    if free_storage is not None:
        backend_hop = _hop(
            rows[RELEASE_BACKEND], RELEASE_BACKEND, FREE_BACKEND, free_storage, {"CALL"}
        )
        if backend_hop["proven"]:
            backend_storage = backend_hop["source_entry_storage"]
            thunk_hop = _hop(
                rows[RELEASE_THUNK], RELEASE_THUNK, RELEASE_BACKEND, backend_storage, {"JMP", "CALL"}
            )
            if thunk_hop["proven"]:
                thunk_storage = thunk_hop["source_entry_storage"]

    chain_proven = bool(
        free_role_proven
        and backend_hop is not None
        and backend_hop.get("proven") is True
        and thunk_hop is not None
        and thunk_hop.get("proven") is True
        and thunk_storage is not None
    )
    missing: list[str] = []
    if not free_role_proven:
        missing.append("free_diagnostic_pointer_storage_not_proven")
    if free_role_proven and (backend_hop is None or backend_hop.get("proven") is not True):
        missing.append("release_backend_to_free_backend_pointer_not_proven")
    if backend_storage is not None and (thunk_hop is None or thunk_hop.get("proven") is not True):
        missing.append("release_thunk_to_backend_pointer_not_proven")

    return {
        "format": FORMAT,
        "instruction_export": str(instruction_export),
        "free_diagnostic_slice": str(free_slice_path),
        "free_pointer_storage": free_storage,
        "release_backend_pointer_storage": backend_storage,
        "release_thunk_pointer_storage": thunk_storage,
        "release_pointer_chain_proven": chain_proven,
        "hops": [hop for hop in (backend_hop, thunk_hop) if hop is not None],
        "missing": missing,
        "scope": {
            "free_diagnostic_pointer_role_used": free_role_proven,
            "inter_function_physical_forwarding_used": True,
            "release_pointer_chain_proven": chain_proven,
            "wrapper_source_pointer_role_proven": False,
            "release_flag_role_proven": False,
            "delete_kind_role_proven": False,
            "operator_delete_identity_proven": False,
            "ownership_semantics_proven": False,
            "note": (
                "A positive chain proves only that one physical input of the release thunk "
                "flows through FUN_0064f3a0 to the FUN_00657c30 entry storage independently "
                "identified as the free diagnostic `%p`. Wrapper/source mapping is a separate "
                "join and DL semantics remain unassigned."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("--free-diagnostic-slice", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    report = analyze_release_pointer_chain(args.instruction_export, args.free_diagnostic_slice)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"release pointer chain proven: {report['release_pointer_chain_proven']}")
    print(f"release thunk pointer storage: {report['release_thunk_pointer_storage']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
