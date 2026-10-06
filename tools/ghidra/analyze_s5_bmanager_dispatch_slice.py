#!/usr/bin/env python3
"""Prove the corrected BManager -> cPhysicsManager default dispatch topology.

The analyzer is deliberately narrow. It consumes an exact nine-function
SHIFT.GhidraFunctionInstructions/2 slice and the already-positive
SHIFT.PhysicsManagerSchedulerEntryOwner/1 handoff. It proves registration into
the active Controller list, list iteration through the per-manager timing gate,
and the default BManager mode dispatch through the source-backed +0x18 slot.
It does not promote the worker 10 ms poll sleep or any host timer to retail
physics cadence.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.BManagerPhysicsManagerDispatchFrontier/2"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
OWNER_FORMAT = "SHIFT.PhysicsManagerSchedulerEntryOwner/1"
TARGETS = {
    0x00647D80: "FUN_00647d80",
    0x00647EF0: "FUN_00647ef0",
    0x0065B8B0: "FUN_0065b8b0",
    0x006626A0: "FUN_006626a0",
    0x00662880: "FUN_00662880",
    0x00D36000: "FUN_00d36000",
    0x006485B0: "FUN_006485b0",
    0x00662600: "FUN_00662600",
    0x0070FE90: "FUN_0070fe90",
}


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


def _compact(value: Any) -> str:
    return re.sub(r"\s+", "", str(value)).lower()


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
        address = _norm(function.get("address") if isinstance(function, dict) else None)
        if address is None:
            raise ValueError(f"{path}: invalid function row")
        instructions = row.get("instructions")
        if not isinstance(instructions, list) or not instructions:
            raise ValueError(f"{_hex(address)}: instruction list missing")
        if row.get("instruction_count") != len(instructions):
            raise ValueError(f"{_hex(address)}: instruction_count mismatch")
        if address in result:
            raise ValueError(f"{_hex(address)}: duplicate target")
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


def _find_instruction(row: dict[str, Any], address: int) -> dict[str, Any]:
    matches = [
        item for item in row["instructions"]
        if _norm(item.get("address")) == address
    ]
    if len(matches) != 1:
        raise ValueError(
            f"{_hex(address)}: expected one machine instruction, found {len(matches)}"
        )
    return matches[0]


def _expect(
    row: dict[str, Any],
    address: int,
    mnemonic: str,
    *operands: str,
) -> dict[str, Any]:
    instruction = _find_instruction(row, address)
    actual_mnemonic = str(instruction.get("mnemonic") or "").upper()
    if actual_mnemonic != mnemonic.upper():
        raise ValueError(
            f"{_hex(address)}: expected {mnemonic}, got {actual_mnemonic or '<missing>'}"
        )
    actual_operands = instruction.get("operands")
    if not isinstance(actual_operands, list):
        raise ValueError(f"{_hex(address)}: operands missing")
    if operands and [_compact(value) for value in actual_operands] != [
        _compact(value) for value in operands
    ]:
        raise ValueError(
            f"{_hex(address)}: operand drift: expected {list(operands)!r}, "
            f"got {actual_operands!r}"
        )
    return instruction


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


def _direct_call(row: dict[str, Any], address: int, target: int) -> None:
    instruction = _expect(row, address, "CALL")
    if target not in _flow_targets(instruction):
        raise ValueError(
            f"{_hex(address)}: direct call target drift; expected {_hex(target)}"
        )


def _validate_abi(functions: dict[int, dict[str, Any]]) -> dict[str, str]:
    api = functions.get(0x006485B0)
    core = functions.get(0x00662600)
    iterator = functions.get(0x0065B8B0)
    if api is None or core is None or iterator is None:
        raise ValueError("required ABI rows missing from functions.jsonl")

    params = api.get("parameters")
    if (
        api.get("calling_convention") != "__thiscall"
        or not isinstance(params, list)
        or len(params) != 2
        or params[0].get("storage") != "ECX:4 (auto)"
        or params[1].get("storage") != "Stack[0x4]:4"
    ):
        raise ValueError("FUN_006485b0 ABI drift")

    params = core.get("parameters")
    if (
        core.get("calling_convention") != "__fastcall"
        or not isinstance(params, list)
        or len(params) != 2
        or params[0].get("storage") != "ECX:4"
        or params[1].get("storage") != "EDX:4"
    ):
        raise ValueError("FUN_00662600 ABI drift")

    params = iterator.get("parameters")
    if (
        iterator.get("calling_convention") != "__stdcall"
        or not isinstance(params, list)
        or len(params) != 1
        or params[0].get("storage") != "Stack[0x4]:4"
    ):
        raise ValueError("FUN_0065b8b0 ABI drift")

    return {
        "FUN_006485b0": "__thiscall ECX=this(manager), Stack[0x4]=controller id",
        "FUN_00662600": "__fastcall ECX=controller, EDX=manager",
        "FUN_0065b8b0": "__stdcall Stack[0x4]=manager list",
    }


def analyze(
    export: Path,
    functions_path: Path,
    owner_path: Path,
) -> dict[str, Any]:
    rows = _instruction_rows(export)
    abi = _validate_abi(_function_db(functions_path))
    owner = _read_json(owner_path)
    if owner.get("format") != OWNER_FORMAT or owner.get("ready") is not True:
        raise ValueError(f"owner handoff must be positive {OWNER_FORMAT}")
    scheduler = owner.get("scheduler_entry")
    if (
        not isinstance(scheduler, dict)
        or scheduler.get("owner_proven") is not True
        or scheduler.get("slot_offset") != 0x18
        or scheduler.get("target_address") != "0x00711b50"
    ):
        raise ValueError("owner +0x18 scheduler slot drift")

    # FUN_0070fe90 return becomes FUN_006485b0 ECX/this. The controller id
    # remains the stack argument. This explicitly rejects the old PUSH-EAX model.
    _direct_call(rows[0x00D36000], 0x00D36051, 0x0070FE90)
    _expect(rows[0x00D36000], 0x00D36068, "MOV", "ECX", "EAX")
    _direct_call(rows[0x00D36000], 0x00D3606A, 0x006485B0)

    # Controller API caches manager=this in EDI, resolves controller into ESI,
    # then enters the fastcall core as ECX=controller, EDX=manager.
    _expect(rows[0x006485B0], 0x006485B5, "MOV", "EDI", "ECX")
    _direct_call(rows[0x006485B0], 0x006485D4, 0x0065B840)
    _expect(rows[0x006485B0], 0x006485D9, "MOV", "ESI", "EAX")
    _expect(rows[0x006485B0], 0x00648603, "MOV", "EDX", "EDI")
    _expect(rows[0x006485B0], 0x00648605, "MOV", "ECX", "ESI")
    _direct_call(rows[0x006485B0], 0x00648607, 0x00662600)

    # Core add uses controller+0x58 and retains manager at node+0xc.
    _expect(rows[0x00662600], 0x00662605, "MOV", "EBX", "EDX")
    _expect(rows[0x00662600], 0x0066260D, "LEA", "EDI", "[ECX + 0x58]")
    _expect(
        rows[0x00662600],
        0x00662630,
        "CMP",
        "EBX",
        "dword ptr [ESI + 0xc]",
    )
    _expect(rows[0x00662600], 0x0066264C, "MOV", "EDX", "EBX")
    _expect(rows[0x00662600], 0x0066264E, "MOV", "ECX", "EDI")
    _direct_call(rows[0x00662600], 0x00662650, 0x004F5E60)

    # Active Controller state 6 consumes exactly the same +0x58 list.
    _expect(
        rows[0x006626A0],
        0x006626A8,
        "CMP",
        "dword ptr [ESI + 0x98]",
        "0x6",
    )
    _expect(rows[0x006626A0], 0x006626B2, "LEA", "EAX", "[ESI + 0x58]")
    _expect(rows[0x006626A0], 0x006626B5, "PUSH", "EAX")
    _direct_call(rows[0x006626A0], 0x006626BD, 0x0065B8B0)

    # Iterator recovers the stored manager at node+0xc and calls timing gate.
    _expect(
        rows[0x0065B8B0],
        0x0065B8E0,
        "MOV",
        "ECX",
        "dword ptr [ESI + 0xc]",
    )
    _direct_call(rows[0x0065B8B0], 0x0065B8FC, 0x00647EF0)

    # Timing gate consumes +0xe8 period and reaches the corrected selector.
    _expect(
        rows[0x00647EF0],
        0x00647FA2,
        "MOV",
        "EAX",
        "dword ptr [ESI + 0xe8]",
    )
    _direct_call(rows[0x00647EF0], 0x00647FBD, 0x00647D80)

    # Correct selector: nonzero global +0x529 -> +0x1c;
    # default zero -> source-backed scheduler slot +0x18.
    _expect(
        rows[0x00647D80],
        0x00647D88,
        "CMP",
        "byte ptr [EAX + 0x529]",
        "0x0",
    )
    _expect(
        rows[0x00647D80],
        0x00647D96,
        "MOV",
        "EDX",
        "dword ptr [EAX + 0x1c]",
    )
    _expect(rows[0x00647D80], 0x00647D99, "JMP", "EDX")
    _expect(
        rows[0x00647D80],
        0x00647D9B,
        "MOV",
        "EDX",
        "dword ptr [EAX + 0x18]",
    )
    _expect(rows[0x00647D80], 0x00647D9E, "JMP", "EDX")

    # Worker loop repeats, but 10 ms is a poll sleep, not physics cadence.
    _direct_call(rows[0x00662880], 0x006629FC, 0x006626A0)
    _expect(rows[0x00662880], 0x00662A76, "MOV", "DL", "0x1")
    _expect(rows[0x00662880], 0x00662A7E, "MOV", "ECX", "0xa")
    _direct_call(rows[0x00662880], 0x00662A83, 0x00649780)
    loop = _find_instruction(rows[0x00662880], 0x00662A8C)
    if str(loop.get("mnemonic") or "").upper() not in {"JZ", "JE"}:
        raise ValueError("FUN_00662880 worker back-edge mnemonic drift")
    if 0x006628E8 not in _flow_targets(loop):
        raise ValueError("FUN_00662880 worker back-edge target drift")

    return {
        "format": FORMAT,
        "version": 2,
        "status": "dispatch-registration-ready",
        "ready": True,
        "input_format": INSTRUCTION_FORMAT,
        "abi": abi,
        "owner_handoff": {
            "format": OWNER_FORMAT,
            "slot_offset": 0x18,
            "target": "FUN_00711b50",
            "verified": True,
        },
        "registration": {
            "accessor_callsite": "0x00d36051",
            "accessor": "FUN_0070fe90",
            "controller_api_callsite": "0x00d3606a",
            "controller_api": "FUN_006485b0",
            "accessor_return_becomes_controller_api_this_ECX": True,
            "accessor_return_is_stack_argument": False,
            "controller_core": "FUN_00662600",
            "controller_list_offset": "0x58",
            "manager_node_value_offset": "0x0c",
            "proven": True,
        },
        "active_dispatch": {
            "controller_state_value": 6,
            "controller_list_offset": "0x58",
            "iterator": "FUN_0065b8b0",
            "timing_gate": "FUN_00647ef0",
            "period_field_offset": "0xe8",
            "selector": "FUN_00647d80",
            "mode_flag_offset": "0x529",
            "default_mode_flag_value": 0,
            "default_slot_offset": "0x18",
            "alternate_slot_offset": "0x1c",
            "default_slot_matches_source_backed_cPhysicsManager_owner_slot": True,
            "proven": True,
        },
        "worker_loop": {
            "function": "FUN_00662880",
            "active_dispatch_callsite": "0x006629fc",
            "poll_sleep_ms": 10,
            "back_edge": "0x00662a8c -> 0x006628e8",
            "repeating": True,
            "poll_sleep_promoted_to_physics_cadence": False,
        },
        "handoff": {
            "bmanager_controller_to_cPhysicsManager_slot_plus_0x18_proven": True,
            "dispatch_registration_ready": True,
            "retail_cadence_admitted": False,
            "consumer": "SHIFT.RetailOuterUpdateCadence/1",
        },
        "blocking_reasons": [
            "manager-period-units-and-scheduler-argument-producer-are-outside-this-nine-function-slice"
        ],
        "corrections": {
            "FUN_00647da0_plus_0x18_rejected": True,
            "FUN_00647da0_actual_indirect_slot": "0x20",
            "correct_default_dispatcher": "FUN_00647d80",
            "FUN_0070fe90_return_as_stack_argument_rejected": True,
            "correct_FUN_006485b0_receiver": "ECX/this",
        },
        "limits": {
            "worker_poll_10ms_promoted": False,
            "host_1_60_promoted": False,
            "rendered_frame_equivalence_claimed": False,
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
