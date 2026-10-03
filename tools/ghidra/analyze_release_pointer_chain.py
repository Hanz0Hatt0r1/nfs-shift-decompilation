#!/usr/bin/env python3
"""Trace the proven pool-free `%p` input back through the release wrapper chain.

Inputs:
- targeted backend instructions containing FUN_0064f4c0, FUN_0064f3a0 and
  FUN_00657c30;
- SHIFT-MEMORY-FREE-DIAGNOSTIC-SLICE/1, which proves the physical
  FUN_00657c30 entry storage supplying the `%p` diagnostic vararg;
- SHIFT-MEMORY-WRAPPER-FORWARDING/1, which proves wrapper -> 0x0064f4c0
  physical argument forwarding.

The analyzer deliberately proves only pointer provenance.  It does not assign
meaning to DL, infer delete-kind/release flags, or claim allocator ownership.
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
FORWARDING_FORMAT = "SHIFT-MEMORY-WRAPPER-FORWARDING/1"

THUNK = "0x0064f4c0"
RELEASE_BACKEND = "0x0064f3a0"
FREE_DIAGNOSTIC_FUNCTION = "0x00657c30"

SIZE_PREFIX = re.compile(r"^(?:BYTE|WORD|DWORD|QWORD)\s+PTR\s+", re.IGNORECASE)
EBP_MEMORY = re.compile(
    r"^\[EBP(?:\s*([+-])\s*(0X[0-9A-F]+|[0-9]+))?\]$", re.IGNORECASE
)
STACK_STORAGE = re.compile(r"^Stack\[0x([0-9a-fA-F]+)\]:(\d+)$")
REGISTER_NAMES = {
    "EAX", "EBX", "ECX", "EDX", "ESI", "EDI", "EBP", "ESP",
    "AL", "AH", "BL", "BH", "CL", "CH", "DL", "DH",
}
VOLATILE = {"EAX", "ECX", "EDX", "AL", "AH", "CL", "CH", "DL", "DH"}
MAX_BACKTRACE = 96
MAX_STACK_SCAN = 24


def _norm_address(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    token = value.strip().lower()
    if token.startswith("fun_"):
        token = token[4:]
    if token.startswith("thunk_fun_"):
        token = token[10:]
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


def _load_json(path: Path, expected_format: str) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("format") != expected_format:
        raise ValueError(f"{path}: expected {expected_format}")
    return report


def _load_instruction_rows(path: Path) -> dict[str, dict[str, Any]]:
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
    missing = [address for address in (THUNK, RELEASE_BACKEND, FREE_DIAGNOSTIC_FUNCTION) if address not in rows]
    if missing:
        raise ValueError("instruction export missing release-chain functions: " + ", ".join(missing))
    return rows


def _clean_operand(value: str) -> str:
    return re.sub(r"\s+", " ", SIZE_PREFIX.sub("", value.strip()).strip()).upper()


def _standard_ebp_frame(instructions: list[dict[str, Any]], before: int) -> bool:
    for index in range(min(before, 10)):
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
    instructions: list[dict[str, Any]], before: int, register: str, depth: int = 0
) -> tuple[str, list[str]]:
    reg = register.upper()
    if depth > 12:
        return "unresolved", ["register recursion limit reached"]
    for index in range(before - 1, max(-1, before - MAX_BACKTRACE - 1), -1):
        instruction = instructions[index]
        mnemonic = str(instruction.get("mnemonic") or "").upper()
        if mnemonic == "CALL" and reg in VOLATILE:
            return "unresolved", [f"{instruction.get('address')} CALL clobbers {reg}"]
        written = _written_register(instruction)
        if written != reg and not (reg == "DL" and written == "EDX"):
            continue
        operands = [str(value) for value in (instruction.get("operands") or [])]
        if mnemonic == "MOV" and len(operands) == 2:
            source, reasons = _resolve_operand(instructions, index, operands[1], depth + 1)
            if reg == "DL" and written == "EDX" and source != "unresolved":
                return f"low8({source})", reasons
            return source, reasons
        if mnemonic in {"MOVZX", "MOVSX"} and len(operands) == 2:
            source, reasons = _resolve_operand(instructions, index, operands[1], depth + 1)
            if source == "unresolved":
                return source, reasons
            return f"{mnemonic.lower()}({source})", reasons
        if mnemonic == "XOR" and len(operands) == 2 and _clean_operand(operands[0]) == _clean_operand(operands[1]):
            return "constant:0x0", []
        return "unresolved", [f"{instruction.get('address')} unsupported write to {reg}: {mnemonic}"]
    if reg in {"ECX", "EDX"}:
        return f"entry:{reg}:4", []
    if reg == "DL":
        return "entry:DL:1", []
    return "unresolved", [f"{reg} has no traceable entry value"]


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
    mnemonic = str(instruction.get("mnemonic") or "").upper()
    if mnemonic not in {"CALL", "JMP"}:
        return None
    for ref in instruction.get("references") or []:
        if not isinstance(ref, dict):
            continue
        target = _norm_address(ref.get("to"))
        if target is not None:
            return target
    for value in instruction.get("flows") or []:
        target = _norm_address(value)
        if target is not None:
            return target
    operands = instruction.get("operands") or []
    if operands:
        return _norm_address(str(operands[0]))
    return None


def _stack_argument_source(
    instructions: list[dict[str, Any]], transfer_index: int, storage: str
) -> tuple[str, list[str]]:
    match = STACK_STORAGE.match(storage)
    if match is None or int(match.group(2)) != 4:
        return "unresolved", [f"unsupported callee stack storage: {storage}"]
    offset = int(match.group(1), 16)
    if offset < 4 or offset % 4:
        return "unresolved", [f"invalid callee stack storage: {storage}"]
    argument_index = (offset - 4) // 4
    transfer_mnemonic = str(instructions[transfer_index].get("mnemonic") or "").upper()
    if transfer_mnemonic != "CALL":
        return "unresolved", ["callee stack arguments across tail JMP are not modeled"]
    pushes: list[int] = []
    for index in range(transfer_index - 1, max(-1, transfer_index - MAX_STACK_SCAN - 1), -1):
        mnemonic = str(instructions[index].get("mnemonic") or "").upper()
        if mnemonic == "PUSH":
            pushes.append(index)
            continue
        if mnemonic in {"CALL", "JMP"} or mnemonic.startswith("RET") or mnemonic.startswith("J"):
            break
    if argument_index >= len(pushes):
        return "unresolved", [f"missing PUSH for {storage}"]
    push_index = pushes[argument_index]
    operands = [str(value) for value in (instructions[push_index].get("operands") or [])]
    if len(operands) != 1:
        return "unresolved", [f"malformed PUSH at {instructions[push_index].get('address')}"]
    return _resolve_operand(instructions, push_index, operands[0])


def _storage_source(
    instructions: list[dict[str, Any]], transfer_index: int, storage: str
) -> tuple[str, list[str]]:
    if storage.startswith("Stack["):
        return _stack_argument_source(instructions, transfer_index, storage)
    register = storage.split(":", 1)[0].upper()
    if register not in REGISTER_NAMES:
        return "unresolved", [f"unsupported physical storage: {storage}"]
    return _resolve_register(instructions, transfer_index, register)


def _entry_storage(source: str) -> str | None:
    if source.startswith("entry:"):
        return source[6:]
    return None


def _trace_function_transfer(
    row: dict[str, Any], target: str, callee_storage: str
) -> dict[str, Any]:
    instructions = [item for item in (row.get("instructions") or []) if isinstance(item, dict)]
    sites: list[dict[str, Any]] = []
    for index, instruction in enumerate(instructions):
        if _transfer_target(instruction) != target:
            continue
        source, reasons = _storage_source(instructions, index, callee_storage)
        sites.append(
            {
                "instruction": _norm_address(instruction.get("address")),
                "transfer_kind": "tail-call" if str(instruction.get("mnemonic") or "").upper() == "JMP" else "call",
                "target": target,
                "callee_storage": callee_storage,
                "source": source,
                "caller_entry_storage": _entry_storage(source),
                "resolved": _entry_storage(source) is not None,
                "reasons": reasons,
            }
        )
    resolved = [site for site in sites if site["resolved"]]
    unresolved = [site for site in sites if not site["resolved"]]
    storages = sorted({site["caller_entry_storage"] for site in resolved if site["caller_entry_storage"]})
    proven = bool(sites) and not unresolved and len(storages) == 1
    return {
        "target": target,
        "callee_storage": callee_storage,
        "site_count": len(sites),
        "sites": sites,
        "caller_entry_storage": storages[0] if proven else None,
        "transfer_proven": proven,
        "reasons": [] if proven else (
            ["no matching transfer found"] if not sites else
            ["one or more transfer sites were unresolved"] if unresolved else
            ["matching transfer sites resolve to multiple caller entry storages"]
        ),
    }


def _wrapper_paths(forwarding: dict[str, Any], thunk_storage: str | None) -> list[dict[str, Any]]:
    if not isinstance(thunk_storage, str):
        return []
    paths: list[dict[str, Any]] = []
    for wrapper in forwarding.get("wrappers") or []:
        if not isinstance(wrapper, dict) or wrapper.get("forwarding_confirmed") is not True:
            continue
        for site in wrapper.get("call_sites") or []:
            if not isinstance(site, dict) or _norm_address(site.get("target")) != THUNK:
                continue
            argument = next(
                (
                    item for item in (site.get("arguments") or [])
                    if isinstance(item, dict) and item.get("storage") == thunk_storage
                ),
                None,
            )
            source = argument.get("source") if isinstance(argument, dict) else None
            proven = isinstance(source, str) and source.startswith("input:") and argument.get("resolved") is True
            paths.append(
                {
                    "wrapper": wrapper.get("name"),
                    "wrapper_address": _norm_address(wrapper.get("address")),
                    "transfer_instruction": _norm_address(site.get("instruction")),
                    "transfer_kind": site.get("transfer_kind"),
                    "thunk_storage": thunk_storage,
                    "wrapper_input_source": source if proven else None,
                    "wrapper_input_storage": source[6:] if proven else None,
                    "released_pointer_path_proven": proven,
                }
            )
    paths.sort(key=lambda row: (row.get("wrapper_address") or "", row.get("transfer_instruction") or ""))
    return paths


def analyze_release_pointer_chain(
    instruction_export: Path,
    free_slice_path: Path,
    forwarding_path: Path,
) -> dict[str, Any]:
    rows = _load_instruction_rows(instruction_export)
    free_slice = _load_json(free_slice_path, FREE_SLICE_FORMAT)
    forwarding = _load_json(forwarding_path, FORWARDING_FORMAT)

    free_storage = free_slice.get("free_pointer_entry_storage") if free_slice.get("free_pointer_role_proven") is True else None
    backend_trace = (
        _trace_function_transfer(rows[RELEASE_BACKEND], FREE_DIAGNOSTIC_FUNCTION, free_storage)
        if isinstance(free_storage, str)
        else {
            "target": FREE_DIAGNOSTIC_FUNCTION,
            "callee_storage": free_storage,
            "site_count": 0,
            "sites": [],
            "caller_entry_storage": None,
            "transfer_proven": False,
            "reasons": ["free diagnostic `%p` entry storage is not proven"],
        }
    )
    backend_pointer_storage = backend_trace.get("caller_entry_storage")
    thunk_trace = (
        _trace_function_transfer(rows[THUNK], RELEASE_BACKEND, backend_pointer_storage)
        if backend_trace.get("transfer_proven") is True and isinstance(backend_pointer_storage, str)
        else {
            "target": RELEASE_BACKEND,
            "callee_storage": backend_pointer_storage,
            "site_count": 0,
            "sites": [],
            "caller_entry_storage": None,
            "transfer_proven": False,
            "reasons": ["release backend pointer entry storage is not proven"],
        }
    )
    thunk_pointer_storage = thunk_trace.get("caller_entry_storage")
    wrapper_paths = _wrapper_paths(forwarding, thunk_pointer_storage)
    proven_wrapper_paths = [row for row in wrapper_paths if row["released_pointer_path_proven"] is True]
    chain_proven = bool(
        free_slice.get("free_pointer_role_proven") is True
        and backend_trace.get("transfer_proven") is True
        and thunk_trace.get("transfer_proven") is True
        and proven_wrapper_paths
    )

    return {
        "format": FORMAT,
        "instruction_export": str(instruction_export),
        "free_diagnostic_slice": str(free_slice_path),
        "wrapper_forwarding": str(forwarding_path),
        "free_pointer_diagnostic_storage": free_storage,
        "release_backend_trace": backend_trace,
        "release_thunk_trace": thunk_trace,
        "release_thunk_pointer_entry_storage": thunk_pointer_storage,
        "wrapper_path_count": len(wrapper_paths),
        "proven_wrapper_path_count": len(proven_wrapper_paths),
        "wrapper_paths": wrapper_paths,
        "release_pointer_to_wrapper_storage_proven": chain_proven,
        "scope": {
            "free_diagnostic_pointer_role_used": free_slice.get("free_pointer_role_proven") is True,
            "inter_function_instruction_trace_used": True,
            "wrapper_forwarding_used": True,
            "released_pointer_role_proven": chain_proven,
            "release_flag_role_proven": False,
            "delete_kind_role_proven": False,
            "pool_selector_role_proven": False,
            "operator_delete_identity_proven": False,
            "ownership_semantics_proven": False,
            "note": (
                "A positive result proves that the value printed by the retail pool-free `%p` "
                "diagnostic can be traced through FUN_0064f3a0 and the 0x0064f4c0 thunk to "
                "specific wrapper entry storage. It does not assign semantics to DL or prove "
                "delete kind, allocator ABI, or ownership policy."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("--free-slice", type=Path, required=True)
    parser.add_argument("--forwarding", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = analyze_release_pointer_chain(args.instruction_export, args.free_slice, args.forwarding)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"wrapper paths: {report['wrapper_path_count']}")
    print(f"proven wrapper paths: {report['proven_wrapper_path_count']}")
    print(f"release pointer to wrapper storage proven: {report['release_pointer_to_wrapper_storage_proven']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
