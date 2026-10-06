#!/usr/bin/env python3
"""Analyze the remaining S5 scheduler-accumulator producer slice.

The input is a targeted SHIFT.GhidraFunctionInstructions/2 export containing
only FUN_007155e9, FUN_00715380 and FUN_00713050 plus the matching ABI database
and the already-positive Physics Manager scheduler-entry owner handoff.

This stage is deliberately conservative.  It may prove an exact machine STORE
surface for displacement +0x348 and the exact stack-argument setup entering
FUN_00715380, but it does not name that value as elapsed time and it never
promotes host/render cadence to retail cadence.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.SchedulerAccumulatorProducerFrontier/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
OWNER_FORMAT = "SHIFT.PhysicsManagerSchedulerEntryOwner/1"

UPPER = 0x007155E9
OWNER = 0x00715380
BATCH = 0x00713050
TARGETS = {
    UPPER: "FUN_007155e9",
    OWNER: "FUN_00715380",
    BATCH: "FUN_00713050",
}
UPPER_OWNER_CALL = 0x00715602
OWNER_BATCH_CALL = 0x00715434
ACCUMULATOR_DISPLACEMENT = 0x348

_MEMORY_RE = re.compile(
    r"^\s*(?:(?:byte|word|dword|qword|tword|xmmword|float|double)\s+ptr\s+)?"
    r"\[\s*([A-Za-z][A-Za-z0-9]*)\s*"
    r"(?:([+-])\s*(0x[0-9A-Fa-f]+|[0-9]+))?\s*\]\s*$",
    re.IGNORECASE,
)
_GPR = {"EAX", "EBX", "ECX", "EDX", "ESI", "EDI", "EBP", "ESP"}
_NO_WRITE = {"NOP", "CMP", "TEST", "PUSH", "PREFETCH", "CLD", "STD", "CLC", "STC", "CMC"}


def _norm(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return None
    token = value.strip().lower()
    if token.startswith("fun_"):
        token = token[4:]
    if token.startswith("0x"):
        token = token[2:]
    try:
        return int(token, 16)
    except ValueError:
        return None


def _hex(value: int) -> str:
    return f"0x{value:08x}"


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_no}: expected JSON object")
        rows.append(value)
    return rows


def _instruction_rows(path: Path) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for row in _read_jsonl(path):
        if row.get("format") != INSTRUCTION_FORMAT:
            raise ValueError(f"{path}: exact S5 analysis requires {INSTRUCTION_FORMAT}")
        if row.get("found") is not True:
            raise ValueError(f"{path}: unresolved target {row.get('requested')}")
        function = row.get("function")
        if not isinstance(function, dict):
            raise ValueError(f"{path}: function metadata missing")
        address = _norm(function.get("address"))
        if address is None:
            raise ValueError(f"{path}: invalid function address")
        instructions = row.get("instructions")
        if not isinstance(instructions, list) or not instructions:
            raise ValueError(f"{_hex(address)}: instruction list missing")
        if row.get("instruction_count") != len(instructions):
            raise ValueError(f"{_hex(address)}: instruction_count mismatch")
        result[address] = row
    if set(result) != set(TARGETS):
        missing = sorted(set(TARGETS) - set(result))
        extra = sorted(set(result) - set(TARGETS))
        raise ValueError(
            f"targeted slice mismatch: missing={[_hex(v) for v in missing]}, "
            f"extra={[_hex(v) for v in extra]}"
        )
    for address, expected in TARGETS.items():
        if result[address]["function"].get("name") != expected:
            raise ValueError(f"{_hex(address)}: function-name drift")
    return result


def _function_db(path: Path) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for row in _read_jsonl(path):
        address = _norm(row.get("address"))
        if address is not None:
            result[address] = row
    return result


def _pcode_opcodes(instruction: dict[str, Any]) -> set[str]:
    pcode = instruction.get("pcode")
    if not isinstance(pcode, list):
        raise ValueError(f"{instruction.get('address')}: pcode missing")
    result: set[str] = set()
    for operation in pcode:
        if not isinstance(operation, dict) or not isinstance(operation.get("opcode"), str):
            raise ValueError(f"{instruction.get('address')}: malformed pcode")
        result.add(operation["opcode"].upper())
    return result


def _flow_targets(instruction: dict[str, Any]) -> set[int]:
    result: set[int] = set()
    for value in instruction.get("flows", []):
        address = _norm(value)
        if address is not None:
            result.add(address)
    return result


def _find_exact_direct_call(row: dict[str, Any], address: int, target: int) -> tuple[int, dict[str, Any]]:
    matches: list[tuple[int, dict[str, Any]]] = []
    for index, instruction in enumerate(row["instructions"]):
        if _norm(instruction.get("address")) != address:
            continue
        if str(instruction.get("mnemonic") or "").upper() != "CALL":
            continue
        opcodes = _pcode_opcodes(instruction)
        if "CALL" not in opcodes or "CALLIND" in opcodes:
            continue
        if target not in _flow_targets(instruction):
            continue
        matches.append((index, instruction))
    if len(matches) != 1:
        raise ValueError(
            f"{_hex(address)}: expected one direct CALL to {_hex(target)}, found {len(matches)}"
        )
    return matches[0]


def _parse_memory(operand: str) -> tuple[str, int] | None:
    match = _MEMORY_RE.fullmatch(operand)
    if match is None:
        return None
    base = match.group(1).upper()
    if base not in _GPR:
        return None
    displacement = 0
    if match.group(3) is not None:
        displacement = int(match.group(3), 0)
        if match.group(2) == "-":
            displacement = -displacement
    return base, displacement


def _memory_kind(opcodes: set[str]) -> str | None:
    if "LOAD" in opcodes and "STORE" in opcodes:
        return "read-write"
    if "STORE" in opcodes:
        return "write"
    if "LOAD" in opcodes:
        return "read"
    return None


def _canonical_register(value: str) -> str | None:
    token = value.strip().upper()
    aliases = {
        "EAX": "EAX", "AX": "EAX", "AL": "EAX", "AH": "EAX",
        "EBX": "EBX", "BX": "EBX", "BL": "EBX", "BH": "EBX",
        "ECX": "ECX", "CX": "ECX", "CL": "ECX", "CH": "ECX",
        "EDX": "EDX", "DX": "EDX", "DL": "EDX", "DH": "EDX",
        "ESI": "ESI", "SI": "ESI", "EDI": "EDI", "DI": "EDI",
        "EBP": "EBP", "BP": "EBP", "ESP": "ESP", "SP": "ESP",
    }
    return aliases.get(token)


def _base_to_entry_ecx(row: dict[str, Any], before_index: int, register: str) -> dict[str, Any]:
    tracked = register
    chain: list[dict[str, Any]] = []
    instructions = row["instructions"]
    for index in range(before_index - 1, -1, -1):
        instruction = instructions[index]
        mnemonic = str(instruction.get("mnemonic") or "").upper()
        operands = instruction.get("operands")
        if not isinstance(operands, list) or any(not isinstance(v, str) for v in operands):
            raise ValueError(f"{instruction.get('address')}: operands missing")
        opcodes = _pcode_opcodes(instruction)
        if "CALL" in opcodes or "CALLIND" in opcodes or mnemonic.startswith("J") or mnemonic.startswith("RET"):
            return {
                "proven": False,
                "status": "barrier-before-entry",
                "tracked_register": tracked,
                "barrier": instruction.get("address"),
                "chain": chain,
            }
        destination = _canonical_register(operands[0]) if operands else None
        if destination != tracked or mnemonic in _NO_WRITE:
            continue
        if mnemonic == "MOV" and len(operands) >= 2:
            source = _canonical_register(operands[1])
            if source is not None:
                chain.append({
                    "instruction": instruction.get("address"),
                    "text": instruction.get("text"),
                    "destination": tracked,
                    "source": source,
                })
                tracked = source
                continue
        return {
            "proven": False,
            "status": "unsupported-definition-before-entry",
            "tracked_register": tracked,
            "definition": instruction.get("address"),
            "chain": chain,
        }
    return {
        "proven": tracked == "ECX",
        "status": "function-entry-ecx" if tracked == "ECX" else "different-entry-register",
        "tracked_register": tracked,
        "chain": chain,
    }


def _accumulator_accesses(row: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for index, instruction in enumerate(row["instructions"]):
        operands = instruction.get("operands")
        if not isinstance(operands, list):
            raise ValueError(f"{instruction.get('address')}: operands missing")
        opcodes = _pcode_opcodes(instruction)
        kind = _memory_kind(opcodes)
        for operand_index, operand in enumerate(operands):
            if not isinstance(operand, str):
                raise ValueError(f"{instruction.get('address')}: non-string operand")
            parsed = _parse_memory(operand)
            if parsed is None:
                continue
            base, displacement = parsed
            if displacement != ACCUMULATOR_DISPLACEMENT:
                continue
            provenance = _base_to_entry_ecx(row, index, base)
            result.append({
                "instruction": instruction.get("address"),
                "instruction_text": instruction.get("text"),
                "operand_index": operand_index,
                "operand": operand,
                "base_register": base,
                "displacement": ACCUMULATOR_DISPLACEMENT,
                "access": kind,
                "pcode_opcodes": sorted(opcodes),
                "base_to_entry_ecx": provenance,
                "this_relative_access_proven": kind is not None and provenance["proven"] is True,
            })
    return result


def _argument_setup(row: dict[str, Any], call_index: int) -> dict[str, Any]:
    # FUN_00715380 has exactly one explicit 4-byte stack parameter.  Accept only
    # a direct PUSH setup with no intervening call/control barrier.  Do not name
    # the pushed value semantically.
    instructions = row["instructions"]
    for index in range(call_index - 1, -1, -1):
        instruction = instructions[index]
        mnemonic = str(instruction.get("mnemonic") or "").upper()
        opcodes = _pcode_opcodes(instruction)
        if "CALL" in opcodes or "CALLIND" in opcodes or mnemonic.startswith("J") or mnemonic.startswith("RET"):
            return {
                "proven": False,
                "status": "barrier-before-explicit-argument",
                "barrier": instruction.get("address"),
            }
        operands = instruction.get("operands")
        if mnemonic == "PUSH":
            if not isinstance(operands, list) or len(operands) != 1 or not isinstance(operands[0], str):
                return {"proven": False, "status": "malformed-push"}
            operand = operands[0]
            register = _canonical_register(operand)
            origin = None
            if register is not None:
                origin = _base_to_entry_ecx(row, index, register)
            return {
                "proven": True,
                "status": "single-explicit-stack-argument-push",
                "instruction": instruction.get("address"),
                "instruction_text": instruction.get("text"),
                "operand": operand,
                "register_origin": origin,
                "semantic_elapsed_value_proven": False,
            }
    return {"proven": False, "status": "function-entry-before-explicit-argument"}


def _validate_abi(functions: dict[int, dict[str, Any]]) -> dict[str, Any]:
    upper = functions.get(UPPER)
    owner = functions.get(OWNER)
    batch = functions.get(BATCH)
    if upper is None or owner is None or batch is None:
        raise ValueError("required S5 ABI rows missing from functions.jsonl")

    upper_params = upper.get("parameters")
    if upper.get("calling_convention") != "__fastcall" or not isinstance(upper_params, list) or len(upper_params) != 1:
        raise ValueError("FUN_007155e9 ABI drift")
    if upper_params[0].get("storage") != "ECX:4":
        raise ValueError("FUN_007155e9 receiver storage drift")

    owner_params = owner.get("parameters")
    if owner.get("calling_convention") != "__thiscall" or not isinstance(owner_params, list) or len(owner_params) != 2:
        raise ValueError("FUN_00715380 ABI drift")
    if owner_params[0].get("storage") != "ECX:4 (auto)" or owner_params[1].get("storage") != "Stack[0x4]:4":
        raise ValueError("FUN_00715380 physical parameter storage drift")

    batch_params = batch.get("parameters")
    if batch.get("calling_convention") != "__thiscall" or not isinstance(batch_params, list) or len(batch_params) != 2:
        raise ValueError("FUN_00713050 ABI drift")
    if batch_params[0].get("storage") != "ECX:4 (auto)":
        raise ValueError("FUN_00713050 receiver storage drift")

    return {
        "upper": {"address": _hex(UPPER), "calling_convention": upper["calling_convention"], "receiver_storage": upper_params[0]["storage"]},
        "owner": {"address": _hex(OWNER), "calling_convention": owner["calling_convention"], "this_storage": owner_params[0]["storage"], "explicit_argument_storage": owner_params[1]["storage"], "explicit_argument_type": owner_params[1].get("type")},
        "batch": {"address": _hex(BATCH), "calling_convention": batch["calling_convention"], "this_storage": batch_params[0]["storage"]},
    }


def analyze(export: Path, functions_path: Path, owner_handoff_path: Path) -> dict[str, Any]:
    rows = _instruction_rows(export)
    functions = _function_db(functions_path)
    owner_handoff = _read_json(owner_handoff_path)
    if owner_handoff.get("format") != OWNER_FORMAT or owner_handoff.get("ready") is not True:
        raise ValueError(f"owner handoff must be positive {OWNER_FORMAT}")
    handoff = owner_handoff.get("handoff")
    if not isinstance(handoff, dict) or handoff.get("exact_direct_chain_to_FUN_00713050_proven") is not True:
        raise ValueError("owner handoff no longer proves the direct chain to FUN_00713050")

    abi = _validate_abi(functions)
    upper_call_index, upper_call = _find_exact_direct_call(rows[UPPER], UPPER_OWNER_CALL, OWNER)
    _, owner_call = _find_exact_direct_call(rows[OWNER], OWNER_BATCH_CALL, BATCH)
    argument = _argument_setup(rows[UPPER], upper_call_index)

    owner_accesses = _accumulator_accesses(rows[OWNER])
    batch_accesses = _accumulator_accesses(rows[BATCH])
    owner_writes = [
        item for item in owner_accesses
        if item["access"] in {"write", "read-write"} and item["this_relative_access_proven"]
    ]
    batch_reads = [
        item for item in batch_accesses
        if item["access"] in {"read", "read-write"} and item["this_relative_access_proven"]
    ]

    blockers: list[str] = []
    if len(owner_writes) != 1:
        blockers.append("unique-FUN_00715380-this-plus-0x348-writer-not-proven")
    if not batch_reads:
        blockers.append("FUN_00713050-this-plus-0x348-read-not-machine-proven")
    if argument.get("proven") is not True:
        blockers.append("FUN_007155e9-to-FUN_00715380-explicit-argument-setup-not-proven")

    # Even a unique STORE surface does not prove that its value is the explicit
    # float parameter.  Keep this as the next exact value-provenance question.
    blockers.append("FUN_00715380-param1-to-this-plus-0x348-stored-value-provenance-not-proven")
    blockers.append("scheduler-accumulator-physical-units-not-proven")
    blockers.append("retail-cadence-dynamic-multiplicity-not-proven")

    surface_ready = len(owner_writes) == 1 and bool(batch_reads) and argument.get("proven") is True
    return {
        "format": FORMAT,
        "ready": surface_ready,
        "status": "accumulator-writer-surface-ready" if surface_ready else "blocked",
        "inputs": {
            "instruction_export": str(export),
            "functions": str(functions_path),
            "scheduler_entry_owner": str(owner_handoff_path),
        },
        "abi": abi,
        "exact_calls": {
            "FUN_007155e9_to_FUN_00715380": {"instruction": upper_call.get("address"), "verified": True},
            "FUN_00715380_to_FUN_00713050": {"instruction": owner_call.get("address"), "verified": True},
        },
        "upper_to_owner_argument": argument,
        "accumulator": {
            "displacement": ACCUMULATOR_DISPLACEMENT,
            "displacement_hex": "0x348",
            "owner_accesses": owner_accesses,
            "batch_accesses": batch_accesses,
            "proven_owner_write_count": len(owner_writes),
            "proven_batch_read_count": len(batch_reads),
            "unique_owner_writer_surface_proven": len(owner_writes) == 1,
            "batch_reader_surface_proven": bool(batch_reads),
            "stored_value_from_FUN_00715380_param1_proven": False,
        },
        "blocking_reasons": sorted(set(blockers)),
        "next_exact_question": (
            "trace the unique FUN_00715380 this+0x348 STORE value backward to the "
            "entry Stack[0x4] float parameter, then join that parameter's producer "
            "at 0x00715602 to the already-proven BManager/Physics Manager scheduler path"
        ),
        "handoff": {
            "scheduler_accumulator_writer_surface_ready": surface_ready,
            "scheduler_entry_elapsed_or_accumulator_input_proven": False,
            "retail_cadence_admitted": False,
        },
        "limits": {
            "host_fixed_step_substitution_allowed": False,
            "rendered_frame_equivalence_proven": False,
            "physical_time_units_proven": False,
            "semantic_elapsed_name_promoted": False,
            "original_game_executed": False,
            "runtime_capture_used": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("functions", type=Path)
    parser.add_argument("scheduler_entry_owner", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = analyze(args.instruction_export, args.functions, args.scheduler_entry_owner)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"status: {report['status']}")
    print(f"ready: {str(report['ready']).lower()}")
    print(f"retail_cadence_admitted: {str(report['handoff']['retail_cadence_admitted']).lower()}")
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
