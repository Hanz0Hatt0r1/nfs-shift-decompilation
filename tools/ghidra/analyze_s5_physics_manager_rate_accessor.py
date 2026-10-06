#!/usr/bin/env python3
"""Prove the narrow Physics Manager accessor alias feeding scheduler +0x388.

Consumes an exact SHIFT.GhidraFunctionInstructions/2 slice for the scheduler
consumer and the four-function accessor/initializer chain.  The proof is
intentionally fail-closed: it can establish that the pointer returned at
FUN_00713050:0x0071307c is the constructor-backed Physics Manager singleton and
that the source-visible +0x388 load is based on that pointer.

It does not name +0x388 as a frequency field, assign physical units, equate one
scheduler invocation with one rendered frame, or admit retail cadence.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.PhysicsManagerRateAccessorAlias/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
OWNER_FORMAT = "SHIFT.PhysicsManagerSchedulerEntryOwner/1"
MANAGER_FORMAT = "SHIFT.PhysicsManagerRuntime/1"

CONSUMER = 0x00713050
ACCESSOR = 0x0070FE90
WRAPPER = 0x0041903C
SINGLETON = 0x0070FE99
CONSTRUCTOR = 0x0070FAE0
RATE_OFFSET = 0x388

TARGETS = {
    CONSUMER: "FUN_00713050",
    ACCESSOR: "FUN_0070fe90",
    WRAPPER: "FUN_0041903c",
    SINGLETON: "FUN_0070fe99",
    CONSTRUCTOR: "FUN_0070fae0",
}

CALLS = {
    CONSUMER: (0x0071307C, ACCESSOR),
    ACCESSOR: (0x0070FE93, WRAPPER),
    WRAPPER: (0x00419042, SINGLETON),
    SINGLETON: (0x0070FEC7, CONSTRUCTOR),
}

CONSTRUCTOR_FINGERPRINT = "072f0f9df5e4b00b2ff7cdbf991923afacaa82bcdac508310f3eb0a3e5941859"
_REGISTERS = {
    "EAX", "AX", "AL", "AH", "EBX", "BX", "BL", "BH", "ECX", "CX", "CL", "CH",
    "EDX", "DX", "DL", "DH", "ESI", "EDI", "EBP", "ESP",
}
_MEM_RE = re.compile(r"\[\s*([^\]]+)\s*\]")
_EAX_RATE_RE = re.compile(
    r"\[\s*EAX\s*\+\s*(?:0x388|388h|904)\s*\]", re.IGNORECASE
)


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
            raise ValueError(f"{path}: expected {INSTRUCTION_FORMAT}")
        if row.get("found") is not True:
            raise ValueError(f"{path}: unresolved target {row.get('requested')}")
        function = row.get("function")
        if not isinstance(function, Mapping):
            raise ValueError(f"{path}: function metadata missing")
        address = _norm(function.get("address"))
        instructions = row.get("instructions")
        if address is None or not isinstance(instructions, list) or not instructions:
            raise ValueError(f"{path}: malformed instruction row")
        if row.get("instruction_count") != len(instructions):
            raise ValueError(f"{_hex(address)}: instruction_count mismatch")
        result[address] = row
    if set(result) != set(TARGETS):
        missing = sorted(set(TARGETS) - set(result))
        extra = sorted(set(result) - set(TARGETS))
        raise ValueError(
            f"targeted slice mismatch: missing={[ _hex(v) for v in missing ]}, "
            f"extra={[ _hex(v) for v in extra ]}"
        )
    for address, name in TARGETS.items():
        if result[address]["function"].get("name") != name:
            raise ValueError(f"{_hex(address)}: function-name drift")
    return result


def _function_db(path: Path) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for row in _read_jsonl(path):
        address = _norm(row.get("address"))
        if address is not None:
            result[address] = row
    return result


def _pcode_opcodes(instruction: Mapping[str, Any]) -> set[str]:
    pcode = instruction.get("pcode")
    if not isinstance(pcode, list):
        raise ValueError(f"{instruction.get('address')}: p-code missing")
    result: set[str] = set()
    for operation in pcode:
        if not isinstance(operation, Mapping) or not isinstance(operation.get("opcode"), str):
            raise ValueError(f"{instruction.get('address')}: malformed p-code")
        result.add(str(operation["opcode"]).upper())
    return result


def _flow_targets(instruction: Mapping[str, Any]) -> set[int]:
    result: set[int] = set()
    for value in instruction.get("flows", []):
        address = _norm(value)
        if address is not None:
            result.add(address)
    references = instruction.get("references", [])
    if isinstance(references, list):
        for reference in references:
            if not isinstance(reference, Mapping):
                continue
            for key in ("to", "target", "address"):
                address = _norm(reference.get(key))
                if address is not None:
                    result.add(address)
    return result


def _find_call(row: Mapping[str, Any], address: int, target: int) -> tuple[int, dict[str, Any]]:
    instructions = row["instructions"]
    matches: list[tuple[int, dict[str, Any]]] = []
    for index, instruction in enumerate(instructions):
        if _norm(instruction.get("address")) != address:
            continue
        if str(instruction.get("mnemonic") or "").upper() != "CALL":
            continue
        if "CALLIND" in _pcode_opcodes(instruction):
            continue
        if target not in _flow_targets(instruction):
            continue
        matches.append((index, instruction))
    if len(matches) != 1:
        raise ValueError(
            f"{_hex(address)}: expected one direct call to {_hex(target)}, found {len(matches)}"
        )
    return matches[0]


def _varnode_is_eax(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    text = str(value.get("text") or "").strip().upper()
    return text in {"EAX", "AX", "AL", "AH"}


def _writes_eax(instruction: Mapping[str, Any]) -> bool:
    mnemonic = str(instruction.get("mnemonic") or "").upper()
    if mnemonic == "CALL":
        return True
    pcode = instruction.get("pcode")
    if isinstance(pcode, list):
        for operation in pcode:
            if isinstance(operation, Mapping) and _varnode_is_eax(operation.get("output")):
                return True
    operands = instruction.get("operands")
    if isinstance(operands, list) and operands and isinstance(operands[0], str):
        first = operands[0].strip().upper()
        if first in {"EAX", "AX", "AL", "AH"}:
            return True
    return False


def _is_branch(instruction: Mapping[str, Any]) -> bool:
    mnemonic = str(instruction.get("mnemonic") or "").upper()
    if mnemonic.startswith("J") or mnemonic.startswith("LOOP"):
        return True
    return bool(_pcode_opcodes(instruction) & {"BRANCH", "CBRANCH", "BRANCHIND"})


def _passthrough_return(row: Mapping[str, Any], callsite: int, target: int) -> dict[str, Any]:
    call_index, call = _find_call(row, callsite, target)
    instructions = row["instructions"]
    blockers: list[dict[str, Any]] = []
    ret: dict[str, Any] | None = None
    for instruction in instructions[call_index + 1 :]:
        mnemonic = str(instruction.get("mnemonic") or "").upper()
        if mnemonic.startswith("RET"):
            ret = instruction
            break
        if mnemonic == "CALL" or _is_branch(instruction) or _writes_eax(instruction):
            blockers.append(
                {
                    "instruction": instruction.get("address"),
                    "instruction_text": instruction.get("text"),
                    "reason": "EAX-clobber-or-control-barrier",
                }
            )
            break
    proven = ret is not None and not blockers
    return {
        "call_instruction": call.get("address"),
        "callee": _hex(target),
        "ret_instruction": ret.get("address") if ret else None,
        "barriers": blockers,
        "callee_eax_reaches_return_unchanged": proven,
    }


def _memory_token(operand: Any) -> str | None:
    if not isinstance(operand, str):
        return None
    match = _MEM_RE.search(operand)
    if match is None:
        return None
    inner = re.sub(r"\s+", "", match.group(1)).lower()
    upper = inner.upper()
    if any(re.search(rf"(?:^|[^A-Z0-9_]){reg}(?:$|[^A-Z0-9_])", upper) for reg in _REGISTERS):
        return None
    return inner


def _mov_store_eax(instruction: Mapping[str, Any]) -> str | None:
    if str(instruction.get("mnemonic") or "").upper() != "MOV":
        return None
    operands = instruction.get("operands")
    if not isinstance(operands, list) or len(operands) != 2:
        return None
    if str(operands[1]).strip().upper() != "EAX":
        return None
    token = _memory_token(operands[0])
    if token is None or "STORE" not in _pcode_opcodes(instruction):
        return None
    return token


def _mov_load_eax(instruction: Mapping[str, Any]) -> str | None:
    if str(instruction.get("mnemonic") or "").upper() != "MOV":
        return None
    operands = instruction.get("operands")
    if not isinstance(operands, list) or len(operands) != 2:
        return None
    if str(operands[0]).strip().upper() != "EAX":
        return None
    token = _memory_token(operands[1])
    if token is None or "LOAD" not in _pcode_opcodes(instruction):
        return None
    return token


def _singleton_return_alias(row: Mapping[str, Any]) -> dict[str, Any]:
    call_index, call = _find_call(row, CALLS[SINGLETON][0], CONSTRUCTOR)
    instructions = row["instructions"]

    store: dict[str, Any] | None = None
    storage: str | None = None
    for instruction in instructions[call_index + 1 :]:
        mnemonic = str(instruction.get("mnemonic") or "").upper()
        if mnemonic == "CALL" or mnemonic.startswith("RET") or _is_branch(instruction):
            break
        token = _mov_store_eax(instruction)
        if token is not None:
            store = instruction
            storage = token
            break
        if _writes_eax(instruction):
            break

    load: dict[str, Any] | None = None
    if storage is not None:
        for index, instruction in enumerate(instructions):
            if index <= call_index:
                continue
            if _mov_load_eax(instruction) != storage:
                continue
            safe = True
            ret_seen = False
            for tail in instructions[index + 1 :]:
                mnemonic = str(tail.get("mnemonic") or "").upper()
                if mnemonic.startswith("RET"):
                    ret_seen = True
                    break
                if mnemonic == "CALL" or _is_branch(tail) or _writes_eax(tail):
                    safe = False
                    break
            if safe and ret_seen:
                load = instruction

    guard_read = False
    guard_branch = False
    if storage is not None:
        for instruction in instructions[:call_index]:
            operands = instruction.get("operands")
            if isinstance(operands, list) and any(_memory_token(op) == storage for op in operands):
                guard_read = True
            if guard_read and _is_branch(instruction):
                guard_branch = True
                break

    proven = storage is not None and store is not None and load is not None and guard_read and guard_branch
    return {
        "constructor_call": call.get("address"),
        "singleton_storage": storage,
        "constructor_return_store": store.get("address") if store else None,
        "common_return_load": load.get("address") if load else None,
        "guard_reads_same_storage": guard_read,
        "guard_has_control_split": guard_branch,
        "constructor_return_populates_returned_singleton_storage": proven,
    }


def _consumer_rate_read(row: Mapping[str, Any]) -> dict[str, Any]:
    call_index, call = _find_call(row, CALLS[CONSUMER][0], ACCESSOR)
    hits: list[dict[str, Any]] = []
    barrier: dict[str, Any] | None = None
    for instruction in row["instructions"][call_index + 1 :]:
        operands = instruction.get("operands")
        texts = [str(value) for value in operands] if isinstance(operands, list) else []
        if any(_EAX_RATE_RE.search(text) for text in texts) and "LOAD" in _pcode_opcodes(instruction):
            hits.append(
                {
                    "instruction": instruction.get("address"),
                    "instruction_text": instruction.get("text"),
                }
            )
            break
        mnemonic = str(instruction.get("mnemonic") or "").upper()
        if mnemonic == "CALL" or _is_branch(instruction) or _writes_eax(instruction):
            barrier = {
                "instruction": instruction.get("address"),
                "instruction_text": instruction.get("text"),
            }
            break
    return {
        "accessor_call": call.get("address"),
        "base_register": "EAX",
        "displacement": RATE_OFFSET,
        "displacement_hex": "0x388",
        "load_candidates": hits,
        "barrier_before_rate_load": barrier,
        "accessor_return_directly_bases_plus_0x388_load": len(hits) == 1 and barrier is None,
    }


def _validate_static_contracts(
    functions: Mapping[int, Mapping[str, Any]], owner_path: Path, runtime_source_path: Path
) -> dict[str, Any]:
    owner = _read_json(owner_path)
    if owner.get("format") != OWNER_FORMAT or owner.get("ready") is not True:
        raise ValueError(f"owner handoff must be positive {OWNER_FORMAT}")
    if owner.get("owner") != "MWL::Core::cPhysicsManager":
        raise ValueError("Physics Manager owner drift")
    provenance = owner.get("provenance")
    if not isinstance(provenance, Mapping) or provenance.get("source_manager_contract") != MANAGER_FORMAT:
        raise ValueError("Physics Manager source contract missing")

    expected_abi = {
        ACCESSOR: ("__stdcall", 0),
        WRAPPER: ("__stdcall", 0),
        SINGLETON: ("__stdcall", 0),
        CONSTRUCTOR: ("__fastcall", 1),
    }
    abi: dict[str, Any] = {}
    for address, (calling_convention, parameter_count) in expected_abi.items():
        row = functions.get(address)
        if not isinstance(row, Mapping):
            raise ValueError(f"{_hex(address)} ABI row missing")
        parameters = row.get("parameters")
        if row.get("calling_convention") != calling_convention or not isinstance(parameters, list):
            raise ValueError(f"{_hex(address)} ABI drift")
        if len(parameters) != parameter_count:
            raise ValueError(f"{_hex(address)} parameter-count drift")
        abi[TARGETS[address]] = {
            "address": _hex(address),
            "calling_convention": calling_convention,
            "parameter_count": parameter_count,
        }
    constructor = functions[CONSTRUCTOR]
    if constructor.get("mnemonic_sha256") != CONSTRUCTOR_FINGERPRINT:
        raise ValueError("FUN_0070fae0 fingerprint drift")
    if constructor["parameters"][0].get("storage") != "ECX:4":
        raise ValueError("FUN_0070fae0 receiver storage drift")

    runtime_source = runtime_source_path.read_text(encoding="utf-8")
    required_markers = [
        'MANAGER_FORMAT = "SHIFT.PhysicsManagerRuntime/1"',
        '"FUN_0070fae0"',
        'MANAGER_VTABLE = "PTR_FUN_00b04524"',
        '"named_object": "Physics Manager"',
    ]
    missing = [marker for marker in required_markers if marker not in runtime_source]
    if missing:
        raise ValueError(f"Physics Manager runtime source contract drift: {missing}")
    return {"owner_format": OWNER_FORMAT, "manager_format": MANAGER_FORMAT, "abi": abi}


def analyze(
    instruction_export: Path,
    functions_path: Path,
    owner_path: Path,
    runtime_source_path: Path,
) -> dict[str, Any]:
    rows = _instruction_rows(instruction_export)
    functions = _function_db(functions_path)
    static_contracts = _validate_static_contracts(functions, owner_path, runtime_source_path)

    consumer = _consumer_rate_read(rows[CONSUMER])
    accessor_forward = _passthrough_return(rows[ACCESSOR], *CALLS[ACCESSOR])
    wrapper_forward = _passthrough_return(rows[WRAPPER], *CALLS[WRAPPER])
    singleton = _singleton_return_alias(rows[SINGLETON])

    alias_proven = (
        accessor_forward["callee_eax_reaches_return_unchanged"]
        and wrapper_forward["callee_eax_reaches_return_unchanged"]
        and singleton["constructor_return_populates_returned_singleton_storage"]
    )
    plus_388_owner_proven = alias_proven and consumer[
        "accessor_return_directly_bases_plus_0x388_load"
    ]

    blockers: list[str] = []
    if not alias_proven:
        blockers.append("FUN_0070fe90-return-alias-to-Physics-Manager-constructor-not-proven")
    if not consumer["accessor_return_directly_bases_plus_0x388_load"]:
        blockers.append("FUN_00713050-plus-0x388-load-not-directly-based-on-accessor-EAX")
    blockers.extend(
        [
            "cPhysicsManager-plus-0x388-writer-value-provenance-not-proven",
            "cPhysicsManager-plus-0x388-physical-units-not-proven",
            "retail-cadence-dynamic-multiplicity-not-proven",
        ]
    )

    return {
        "format": FORMAT,
        "ready": plus_388_owner_proven,
        "status": "accessor-alias-and-plus-0x388-owner-proven" if plus_388_owner_proven else "blocked",
        "inputs": {
            "instruction_export": str(instruction_export),
            "functions": str(functions_path),
            "scheduler_owner": str(owner_path),
            "manager_runtime_source": str(runtime_source_path),
        },
        "static_contracts": static_contracts,
        "direct_call_chain": [
            {"from": _hex(function), "instruction": _hex(callsite), "to": _hex(target)}
            for function, (callsite, target) in CALLS.items()
        ],
        "wrapper_return_provenance": {
            "FUN_0070fe90": accessor_forward,
            "FUN_0041903c": wrapper_forward,
            "FUN_0070fe99": singleton,
        },
        "consumer_rate_read": consumer,
        "adjudication": {
            "FUN_0070fe90_return_aliases_source_backed_cPhysicsManager_instance": alias_proven,
            "plus_0x388_is_cPhysicsManager_field": plus_388_owner_proven,
            "plus_0x388_semantic_name_frequency": False,
            "plus_0x388_value_or_units_proven": False,
            "fixed_timestep_semantics_proven": False,
            "retail_cadence_admitted": False,
        },
        "blocking_reasons": sorted(set(blockers)),
        "next_exact_question": (
            "enumerate exact cPhysicsManager +0x388 writers and backward-slice the stored value "
            "to a source with physical units; independently retain dynamic scheduler multiplicity proof"
        ),
        "limits": {
            "offset_adjacency_used_as_field_identity": False,
            "frequency_name_promoted": False,
            "host_1_60_promoted": False,
            "rendered_frame_equivalence_claimed": False,
            "runtime_capture_used": False,
            "original_game_executed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("functions_jsonl", type=Path)
    parser.add_argument("scheduler_owner", type=Path)
    parser.add_argument("manager_runtime_source", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = analyze(
        args.instruction_export,
        args.functions_jsonl,
        args.scheduler_owner,
        args.manager_runtime_source,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"status: {report['status']}")
    print(f"ready: {str(report['ready']).lower()}")
    print(
        "retail_cadence_admitted: "
        f"{str(report['adjudication']['retail_cadence_admitted']).lower()}"
    )
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
