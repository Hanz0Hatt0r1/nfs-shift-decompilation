#!/usr/bin/env python3
"""Analyze the narrow S5 BManager/cPhysicsManager dispatch-registration slice.

This analyzer is intentionally fail-closed.  It can prove only what is visible
in a targeted SHIFT.GhidraFunctionInstructions/2 export plus exact ABI metadata
and the already-positive SHIFT.PhysicsManagerSchedulerEntryOwner/1 handoff.
It does not infer a Tick slot from address ordering and it never promotes host
pacing to retail cadence.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.BManagerPhysicsManagerDispatchFrontier/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
OWNER_FORMAT = "SHIFT.PhysicsManagerSchedulerEntryOwner/1"

TARGETS = {
    0x00647B70: "FUN_00647b70",  # Activate semantic anchor
    0x00647C60: "FUN_00647c60",  # Disable semantic anchor
    0x00647CF0: "FUN_00647cf0",  # Restart semantic anchor
    0x00647DA0: "FUN_00647da0",  # unresolved lifecycle wrapper
    0x0065BB50: "FUN_0065bb50",  # controller helper -> 00647da0
    0x00D36000: "FUN_00d36000",  # Controller #1/#2 registration candidate
    0x006485B0: "FUN_006485b0",  # BManager controller API
    0x00662600: "FUN_00662600",  # duplicate-check/core add path
    0x0070FE90: "FUN_0070fe90",  # Physics Manager accessor
}

LIFECYCLE_CALLS = {
    0x00647B70: 0x00647C0C,
    0x00647C60: 0x00647C87,
    0x00647CF0: 0x00647D47,
    0x00647DA0: 0x00647E23,
}
CONTROLLER_HELPER_CALL = 0x0065BB96
CONTROLLER_HELPER_TARGET = 0x00647DA0
REGISTRATION_CALLER = 0x00D36000
PHYSICS_MANAGER_ACCESSOR = 0x0070FE90
CONTROLLER_API = 0x006485B0
CONTROLLER_CORE = 0x00662600
CONTROLLER_CORE_CALL = 0x00648607

_SLOT_RE = re.compile(r"\[\s*([A-Za-z][A-Za-z0-9]*)\s*(?:\+\s*(0x[0-9a-fA-F]+|[0-9]+|[0-9a-fA-F]+h))?\s*\]")


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
            raise ValueError(f"{path}: unresolved targeted function {row.get('requested')}")
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
            f"targeted slice mismatch: missing={[ _hex(v) for v in missing ]}, "
            f"extra={[ _hex(v) for v in extra ]}"
        )
    for address, expected_name in TARGETS.items():
        name = result[address]["function"].get("name")
        if name != expected_name:
            raise ValueError(f"{_hex(address)}: expected {expected_name}, got {name!r}")
    return result


def _function_db(path: Path) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for row in _read_jsonl(path):
        address = _norm(row.get("address"))
        if address is not None:
            result[address] = row
    return result


def _instructions(row: dict[str, Any]) -> list[dict[str, Any]]:
    return row["instructions"]


def _find_instruction(row: dict[str, Any], address: int) -> dict[str, Any]:
    matches = [item for item in _instructions(row) if _norm(item.get("address")) == address]
    if len(matches) != 1:
        raise ValueError(f"{_hex(address)}: expected one machine instruction, found {len(matches)}")
    return matches[0]


def _pcode_opcodes(instruction: dict[str, Any]) -> list[str]:
    pcode = instruction.get("pcode")
    if not isinstance(pcode, list):
        raise ValueError(f"{instruction.get('address')}: pcode missing")
    result: list[str] = []
    for operation in pcode:
        if not isinstance(operation, dict) or not isinstance(operation.get("opcode"), str):
            raise ValueError(f"{instruction.get('address')}: malformed pcode")
        result.append(operation["opcode"].upper())
    return result


def _slot_operand(instruction: dict[str, Any]) -> dict[str, Any]:
    mnemonic = str(instruction.get("mnemonic") or "").upper()
    if mnemonic != "CALL":
        raise ValueError(f"{instruction.get('address')}: expected CALL, got {mnemonic or '<missing>'}")
    if "CALLIND" not in _pcode_opcodes(instruction):
        raise ValueError(f"{instruction.get('address')}: expected p-code CALLIND")
    operands = instruction.get("operands")
    if not isinstance(operands, list) or len(operands) != 1 or not isinstance(operands[0], str):
        raise ValueError(f"{instruction.get('address')}: expected one textual CALL operand")
    operand = operands[0]
    match = _SLOT_RE.search(operand)
    if match is None:
        return {"operand": operand, "base_register": None, "displacement": None, "parsed": False}
    displacement_token = match.group(2)
    displacement = 0
    if displacement_token:
        token = displacement_token.lower()
        if token.endswith("h"):
            displacement = int(token[:-1], 16)
        elif token.startswith("0x"):
            displacement = int(token, 16)
        else:
            displacement = int(token, 10)
    return {
        "operand": operand,
        "base_register": match.group(1).upper(),
        "displacement": displacement,
        "parsed": True,
    }


def _flow_targets(instruction: dict[str, Any]) -> set[int]:
    targets: set[int] = set()
    for value in instruction.get("flows", []):
        address = _norm(value)
        if address is not None:
            targets.add(address)
    for reference in instruction.get("references", []):
        if isinstance(reference, dict):
            for key in ("to", "target", "address"):
                address = _norm(reference.get(key))
                if address is not None:
                    targets.add(address)
    return targets


def _direct_calls(row: dict[str, Any], target: int) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    for index, instruction in enumerate(_instructions(row)):
        if str(instruction.get("mnemonic") or "").upper() != "CALL":
            continue
        if "CALLIND" in _pcode_opcodes(instruction):
            continue
        if target in _flow_targets(instruction):
            address = _norm(instruction.get("address"))
            if address is not None:
                result.append((index, address))
    return result


def _writes_eax(instruction: dict[str, Any]) -> bool:
    mnemonic = str(instruction.get("mnemonic") or "").upper()
    if mnemonic in {"CALL", "RET", "PUSH", "CMP", "TEST", "JMP"} or mnemonic.startswith("J"):
        return mnemonic == "CALL"
    operands = instruction.get("operands")
    if not isinstance(operands, list) or not operands or not isinstance(operands[0], str):
        return False
    first = operands[0].strip().upper()
    return first in {"EAX", "AX", "AL", "AH"}


def _accessor_returns_eax(row: dict[str, Any]) -> dict[str, Any]:
    instructions = _instructions(row)
    ret_seen = any(str(item.get("mnemonic") or "").upper().startswith("RET") for item in instructions)
    eax_write = any(_writes_eax(item) and str(item.get("mnemonic") or "").upper() != "CALL" for item in instructions)
    return {
        "ret_observed": ret_seen,
        "eax_definition_observed": eax_write,
        "return_register_surface_proven": ret_seen and eax_write,
    }


def _nearest_accessor_to_api_transfer(row: dict[str, Any]) -> dict[str, Any]:
    instructions = _instructions(row)
    accessor_calls = _direct_calls(row, PHYSICS_MANAGER_ACCESSOR)
    api_calls = _direct_calls(row, CONTROLLER_API)
    candidates: list[dict[str, Any]] = []
    for api_index, api_address in api_calls:
        preceding = [(idx, addr) for idx, addr in accessor_calls if idx < api_index]
        if not preceding:
            continue
        accessor_index, accessor_address = preceding[-1]
        window = instructions[accessor_index + 1 : api_index]
        push_positions = [
            i for i, item in enumerate(window)
            if str(item.get("mnemonic") or "").upper() == "PUSH"
            and isinstance(item.get("operands"), list)
            and item["operands"]
            and str(item["operands"][0]).strip().upper() == "EAX"
        ]
        if not push_positions:
            candidates.append({
                "accessor_call": _hex(accessor_address),
                "controller_api_call": _hex(api_address),
                "push_eax_observed": False,
                "eax_unclobbered_before_push": False,
                "proven": False,
            })
            continue
        push_pos = push_positions[-1]
        before_push = window[:push_pos]
        unclobbered = not any(_writes_eax(item) for item in before_push)
        candidates.append({
            "accessor_call": _hex(accessor_address),
            "controller_api_call": _hex(api_address),
            "push_eax_observed": True,
            "eax_unclobbered_before_push": unclobbered,
            "intervening_instruction_count": len(window),
            "proven": unclobbered,
        })
    proven = [item for item in candidates if item["proven"]]
    return {
        "candidate_pairs": candidates,
        "proven_pairs": proven,
        "accessor_return_passed_as_stack_argument_to_controller_api": bool(proven),
    }


def _validate_abi(functions: dict[int, dict[str, Any]]) -> dict[str, Any]:
    accessor = functions.get(PHYSICS_MANAGER_ACCESSOR)
    api = functions.get(CONTROLLER_API)
    core = functions.get(CONTROLLER_CORE)
    if accessor is None or api is None or core is None:
        raise ValueError("required ABI rows missing from functions.jsonl")
    if accessor.get("calling_convention") != "__stdcall" or accessor.get("parameters") != []:
        raise ValueError("FUN_0070fe90 ABI drift")
    params = api.get("parameters")
    if api.get("calling_convention") != "__thiscall" or not isinstance(params, list) or len(params) != 2:
        raise ValueError("FUN_006485b0 ABI drift")
    if params[0].get("storage") != "ECX:4 (auto)" or params[1].get("storage") != "Stack[0x4]:4":
        raise ValueError("FUN_006485b0 physical parameter storage drift")
    core_params = core.get("parameters")
    if core.get("calling_convention") != "__fastcall" or not isinstance(core_params, list) or len(core_params) != 2:
        raise ValueError("FUN_00662600 ABI drift")
    return {
        "physics_manager_accessor": {
            "address": _hex(PHYSICS_MANAGER_ACCESSOR),
            "calling_convention": accessor["calling_convention"],
            "parameter_count": 0,
            "verified": True,
        },
        "controller_api": {
            "address": _hex(CONTROLLER_API),
            "calling_convention": api["calling_convention"],
            "this_storage": params[0]["storage"],
            "manager_argument_storage": params[1]["storage"],
            "verified": True,
        },
        "controller_core": {
            "address": _hex(CONTROLLER_CORE),
            "calling_convention": core["calling_convention"],
            "verified": True,
        },
    }


def analyze(export: Path, functions_path: Path, owner_path: Path) -> dict[str, Any]:
    rows = _instruction_rows(export)
    functions = _function_db(functions_path)
    owner = _read_json(owner_path)
    if owner.get("format") != OWNER_FORMAT or owner.get("ready") is not True:
        raise ValueError(f"owner handoff must be positive {OWNER_FORMAT}")
    scheduler = owner.get("scheduler_entry")
    if not isinstance(scheduler, dict) or scheduler.get("owner_proven") is not True:
        raise ValueError("owner handoff scheduler entry is not proven")
    owner_slot = scheduler.get("slot_offset")
    if not isinstance(owner_slot, int):
        raise ValueError("owner handoff slot_offset missing")

    abi = _validate_abi(functions)

    lifecycle: dict[str, Any] = {}
    for function, callsite in LIFECYCLE_CALLS.items():
        instruction = _find_instruction(rows[function], callsite)
        lifecycle[TARGETS[function]] = {
            "function": _hex(function),
            "callsite": _hex(callsite),
            **_slot_operand(instruction),
        }

    candidate = lifecycle[TARGETS[0x00647DA0]]
    candidate_slot_matches_owner = (
        candidate["parsed"] is True and candidate["displacement"] == owner_slot
    )

    helper_call = _find_instruction(rows[0x0065BB50], CONTROLLER_HELPER_CALL)
    helper_calls_candidate = CONTROLLER_HELPER_TARGET in _flow_targets(helper_call)

    accessor_surface = _accessor_returns_eax(rows[PHYSICS_MANAGER_ACCESSOR])
    registration_transfer = _nearest_accessor_to_api_transfer(rows[REGISTRATION_CALLER])

    core_call = _find_instruction(rows[CONTROLLER_API], CONTROLLER_CORE_CALL)
    controller_api_reaches_core = CONTROLLER_CORE in _flow_targets(core_call)

    dispatch_registration_ready = (
        candidate_slot_matches_owner
        and helper_calls_candidate
        and accessor_surface["return_register_surface_proven"]
        and registration_transfer["accessor_return_passed_as_stack_argument_to_controller_api"]
        and controller_api_reaches_core
    )

    blockers: list[str] = []
    if not candidate_slot_matches_owner:
        blockers.append("FUN_00647da0-indirect-call-not-proven-to-use-cPhysicsManager-owner-slot-plus-0x18")
    if not helper_calls_candidate:
        blockers.append("controller-helper-to-FUN_00647da0-edge-not-proven-in-targeted-export")
    if not accessor_surface["return_register_surface_proven"]:
        blockers.append("physics-manager-accessor-return-register-surface-not-proven")
    if not registration_transfer["accessor_return_passed_as_stack_argument_to_controller_api"]:
        blockers.append("physics-manager-accessor-return-to-controller-api-manager-argument-not-proven")
    if not controller_api_reaches_core:
        blockers.append("controller-api-to-BManager-core-add-path-not-proven")
    blockers.append("scheduler-entry-elapsed-or-accumulator-producer-not-proven")

    return {
        "format": FORMAT,
        "version": 1,
        "status": "dispatch-registration-ready" if dispatch_registration_ready else "blocked-dispatch-registration-proof",
        "ready": dispatch_registration_ready,
        "input_format": INSTRUCTION_FORMAT,
        "owner_handoff": {
            "format": OWNER_FORMAT,
            "slot_offset": owner_slot,
            "target": scheduler.get("target"),
            "verified": True,
        },
        "abi": abi,
        "lifecycle_indirect_calls": lifecycle,
        "slot_join": {
            "FUN_00647da0_matches_source_backed_cPhysicsManager_slot": candidate_slot_matches_owner,
            "matched_slot_offset": owner_slot if candidate_slot_matches_owner else None,
            "semantic_name_tick_promoted": False,
        },
        "controller_dispatch": {
            "helper": "FUN_0065bb50",
            "callsite": _hex(CONTROLLER_HELPER_CALL),
            "calls_FUN_00647da0": helper_calls_candidate,
        },
        "physics_manager_registration": {
            "caller": "FUN_00d36000",
            "accessor": "FUN_0070fe90",
            "controller_api": "FUN_006485b0",
            "controller_core": "FUN_00662600",
            "accessor_surface": accessor_surface,
            "value_transfer": registration_transfer,
            "controller_api_reaches_core": controller_api_reaches_core,
            "registration_api_argument_proven": (
                accessor_surface["return_register_surface_proven"]
                and registration_transfer["accessor_return_passed_as_stack_argument_to_controller_api"]
                and controller_api_reaches_core
            ),
        },
        "handoff": {
            "bmanager_controller_to_owner_slot_plus_0x18_proven": candidate_slot_matches_owner and helper_calls_candidate,
            "physics_manager_registration_api_argument_proven": (
                accessor_surface["return_register_surface_proven"]
                and registration_transfer["accessor_return_passed_as_stack_argument_to_controller_api"]
                and controller_api_reaches_core
            ),
            "dispatch_registration_ready": dispatch_registration_ready,
            "scheduler_entry_elapsed_or_accumulator_input_proven": False,
            "retail_cadence_admitted": False,
            "consumer": "S5 timer/accumulator provenance into the already-proven cPhysicsManager scheduler entry",
        },
        "blocking_reasons": blockers,
        "limits": {
            "FUN_00647da0_called_tick_from_address_order": False,
            "diagnostic_frequency_promoted_to_cadence": False,
            "host_1_60_promoted": False,
            "rendered_frame_equivalence_claimed": False,
            "scheduler_timer_or_accumulator_value_guessed": False,
            "runtime_capture_used": False,
            "original_game_executed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("functions", type=Path)
    parser.add_argument("owner_handoff", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = analyze(args.instruction_export, args.functions, args.owner_handoff)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
