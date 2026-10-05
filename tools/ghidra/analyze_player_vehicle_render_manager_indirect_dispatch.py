#!/usr/bin/env python3
"""Resolve the three proven render-manager indirect receiver calls through the retail primary table.

The direct manager-callee +0xca4 branch is exhaustively negative.  The positive
receiver frontier still contains exactly three first-hop indirect CALL EDX sites.
This pass resolves only those sites.  It does not broaden the callgraph.

Proof chain:

  positive DAT_00bc185c constructor/class identity
    -> FUN_0045ef50 entry receiver saved in ESI
    -> exact primary table store [ESI] = 0x00ab5644
    -> proven manager pointer dereference loads that table into EAX
    -> straight-line MOV EDX,[EAX + slot]
    -> exact static_tables.jsonl pointer at 0x00ab5644 + slot
    -> CALL EDX target identity

A positive report produces only a finite indirect-method instruction worklist.
It does not prove +0xca4 access in those methods, render-owner identity, VHF
root/frame identity, BODY0 bind-frame closure, or vehicle world transform.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

FORMAT = "SHIFT.PlayerVehicleRenderManagerIndirectDispatch/1"
DIRECT_CA4_FORMAT = "SHIFT.PlayerVehicleRenderManagerMethodCa4Access/1"
FRONTIER_FORMAT = "SHIFT.PlayerVehicleRenderManagerReceiverTransferFrontier/2"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
CANDIDATE_GLOBAL = "0x00bc185c"

CONSTRUCTOR = "0x0045ef50"
WRITER = "0x00d36210"
CTOR_RECEIVER_SAVE = "0x0045ef59"
CTOR_PRIMARY_TABLE_STORE = "0x0045ef78"
PRIMARY_TABLE = 0x00AB5644

EXPECTED_CALLERS = {"0x0056bcd0", "0x0056bd30"}
EXPECTED_INDIRECT_CALLS = {
    ("0x0056bcd0", "0x0056bcf2", "EDX", "ECX"),
    ("0x0056bcd0", "0x0056bd09", "EDX", "ECX"),
    ("0x0056bd30", "0x0056bd59", "EDX", "ECX"),
}

_REGISTER = re.compile(r"^(EAX|EBX|ECX|EDX|ESI|EDI|EBP|ESP)$", re.IGNORECASE)
_MEMORY = re.compile(
    r"^\s*(?:(?:byte|word|dword|qword)\s+ptr\s+)?"
    r"\[\s*([A-Za-z][A-Za-z0-9]*)\s*"
    r"(?:([+-])\s*(0x[0-9A-Fa-f]+|[0-9]+))?\s*\]\s*$",
    re.IGNORECASE,
)
_BRANCH_PREFIXES = ("J", "LOOP")
_DESTINATION_WRITERS = {
    "MOV", "MOVZX", "MOVSX", "MOVSXD", "LEA", "XOR", "ADD", "SUB",
    "ADC", "SBB", "AND", "OR", "IMUL", "SHL", "SHR", "SAR", "ROL",
    "ROR", "INC", "DEC", "NEG", "NOT", "POP",
}


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, 1):
            text = raw.strip()
            if not text:
                continue
            try:
                value = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            yield value


def _addr(value: Any, *, field: str = "address") -> str:
    if isinstance(value, int):
        number = value
    elif isinstance(value, str):
        token = value.strip()
        upper = token.upper()
        if upper.startswith("FUN_"):
            token = token[4:]
        if token.lower().startswith("0x"):
            token = token[2:]
        try:
            number = int(token, 16)
        except ValueError as exc:
            raise ValueError(f"{field}: invalid address {value!r}") from exc
    else:
        raise ValueError(f"{field}: invalid address {value!r}")
    if number < 0:
        raise ValueError(f"{field}: negative address")
    return f"0x{number:08x}"


def _retail(report: Mapping[str, Any], *, label: str) -> None:
    retail = report.get("retail")
    if not isinstance(retail, Mapping):
        raise ValueError(f"{label}: retail identity missing")
    if retail.get("program") != PROGRAM or str(retail.get("md5") or "").lower() != PE_MD5:
        raise ValueError(f"{label}: retail identity drift")


def _validate_direct_negative(path: Path) -> dict[str, Any]:
    report = _load_json(path)
    if report.get("format") != DIRECT_CA4_FORMAT:
        raise ValueError(f"{path}: expected {DIRECT_CA4_FORMAT}")
    _retail(report, label="direct-ca4")
    if report.get("ready") is not False:
        raise ValueError("direct +0xca4 branch is not negative")
    provenance = report.get("provenance")
    if not isinstance(provenance, Mapping):
        raise ValueError("direct-ca4 provenance missing")
    if provenance.get("targeted_direct_callee_count") != 17:
        raise ValueError("direct-ca4 artifact does not cover the frozen 17 direct callees")
    if provenance.get("exact_entry_pointer_ca4_access_count") != 0:
        raise ValueError("direct-ca4 artifact contains a positive access and must be consumed first")
    if provenance.get("exact_entry_pointer_ca4_read_count") != 0:
        raise ValueError("direct-ca4 artifact contains a positive read and must be consumed first")
    handoff = report.get("handoff")
    if not isinstance(handoff, Mapping):
        raise ValueError("direct-ca4 handoff missing")
    if handoff.get("player_vehicle_renderables_field_runtime_access_ready") is not False:
        raise ValueError("direct-ca4 artifact unexpectedly preclaims field runtime access")
    return report


def _validate_frontier(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    report = _load_json(path)
    if report.get("format") != FRONTIER_FORMAT or report.get("ready") is not True:
        raise ValueError(f"{path}: expected ready {FRONTIER_FORMAT}")
    _retail(report, label="receiver-frontier")
    handoff = report.get("handoff")
    if not isinstance(handoff, Mapping) or handoff.get("candidate_global_manager_indirect_dispatch_frontier_ready") is not True:
        raise ValueError("receiver-frontier indirect dispatch gate is not ready")
    provenance = report.get("provenance")
    if not isinstance(provenance, Mapping) or provenance.get("indirect_call_receiver_transfer_count") != 3:
        raise ValueError("receiver-frontier does not contain exactly three indirect transfers")
    analysis = report.get("analysis")
    if not isinstance(analysis, Mapping):
        raise ValueError("receiver-frontier analysis missing")
    transfers = []
    for item in analysis.get("call_receiver_transfers") or []:
        if not isinstance(item, Mapping) or item.get("kind") != "indirect-call-manager-receiver-transfer":
            continue
        row = dict(item)
        key = (
            _addr(row.get("function"), field="transfer.function"),
            _addr(row.get("instruction"), field="transfer.instruction"),
            str(row.get("call_operand") or "").upper(),
            str(row.get("source_register") or "").upper(),
        )
        if row.get("manager_receiver_identity_proven") is not True:
            raise ValueError(f"indirect transfer lacks manager identity: {key}")
        transfers.append({**row, "key": key})
    found = {item["key"] for item in transfers}
    if found != EXPECTED_INDIRECT_CALLS:
        raise ValueError(f"indirect transfer set drift: {sorted(found)!r}")

    dereferences = []
    for item in analysis.get("all_sinks") or []:
        if not isinstance(item, Mapping) or item.get("kind") != "manager-pointer-dereference":
            continue
        if int(item.get("displacement") or 0) != 0:
            continue
        function = _addr(item.get("function"), field="dereference.function")
        if function not in EXPECTED_CALLERS:
            continue
        dereferences.append(dict(item))
    if len(dereferences) < 3:
        raise ValueError("receiver-frontier lost primary manager dereference evidence")
    return report, transfers, dereferences


def _load_instruction_rows(path: Path, *, expected: set[str] | None = None) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(path):
        if row.get("format") != INSTRUCTION_FORMAT or row.get("program") != PROGRAM:
            raise ValueError(f"{path}: expected {INSTRUCTION_FORMAT} for {PROGRAM}")
        if row.get("found") is not True:
            raise ValueError(f"{path}: unresolved target {row.get('requested')}")
        function = row.get("function")
        instructions = row.get("instructions")
        if not isinstance(function, Mapping) or not isinstance(instructions, list) or not instructions:
            raise ValueError(f"{path}: malformed instruction row")
        address = _addr(function.get("address"), field="function.address")
        if address in rows:
            raise ValueError(f"{path}: duplicate function {address}")
        if row.get("instruction_count") != len(instructions):
            raise ValueError(f"{address}: instruction count mismatch")
        rows[address] = row
    if expected is not None and set(rows) != expected:
        raise ValueError(
            f"{path}: target set drift; missing={sorted(expected - set(rows))}, extra={sorted(set(rows) - expected)}"
        )
    return rows


def _instruction_map(row: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for instruction in row.get("instructions") or []:
        if not isinstance(instruction, dict):
            raise ValueError("instruction row contains non-object instruction")
        address = _addr(instruction.get("address"), field="instruction.address")
        if address in result:
            raise ValueError(f"duplicate instruction {address}")
        result[address] = instruction
    return result


def _operands(instruction: Mapping[str, Any]) -> list[str]:
    operands = instruction.get("operands")
    if not isinstance(operands, list) or any(not isinstance(item, str) for item in operands):
        raise ValueError(f"{instruction.get('address')}: operands must be string list")
    return operands


def _parse_memory(operand: str) -> tuple[str, int] | None:
    match = _MEMORY.fullmatch(operand)
    if match is None:
        return None
    base = match.group(1).upper()
    sign = match.group(2)
    token = match.group(3)
    displacement = 0 if token is None else int(token, 0)
    if sign == "-":
        displacement = -displacement
    return base, displacement


def _writes_register(instruction: Mapping[str, Any], register: str) -> bool:
    mnemonic = str(instruction.get("mnemonic") or "").upper()
    operands = _operands(instruction)
    register = register.upper()
    if mnemonic == "CALL":
        return register in {"EAX", "ECX", "EDX"}
    if mnemonic not in _DESTINATION_WRITERS or not operands:
        return False
    destination = operands[0].strip().upper()
    return destination == register


def _validate_constructor_primary_table(path: Path) -> dict[str, Any]:
    rows = _load_instruction_rows(path)
    if set(rows) != {WRITER, CONSTRUCTOR}:
        raise ValueError("constructor/writer instruction export must contain exactly FUN_00d36210 and FUN_0045ef50")
    instructions = _instruction_map(rows[CONSTRUCTOR])
    save = instructions.get(CTOR_RECEIVER_SAVE)
    store = instructions.get(CTOR_PRIMARY_TABLE_STORE)
    if save is None or str(save.get("mnemonic") or "").upper() != "MOV" or [x.upper() for x in _operands(save)] != ["ESI", "ECX"]:
        raise ValueError("constructor entry receiver save drift")
    if store is None or str(store.get("mnemonic") or "").upper() != "MOV":
        raise ValueError("constructor primary table store missing")
    operands = _operands(store)
    if len(operands) != 2:
        raise ValueError("constructor primary table store operand drift")
    memory = _parse_memory(operands[0])
    if memory != ("ESI", 0):
        raise ValueError("constructor primary table store no longer targets [ESI]")
    try:
        value = int(operands[1], 0)
    except ValueError as exc:
        raise ValueError("constructor primary table immediate is not numeric") from exc
    if value != PRIMARY_TABLE:
        raise ValueError(f"constructor primary table drift: 0x{value:08x}")
    return rows[CONSTRUCTOR]


def _load_static_pointers(path: Path) -> dict[int, dict[str, Any]]:
    pointers: dict[int, dict[str, Any]] = {}
    for row in _read_jsonl(path):
        address_value = row.get("address")
        if address_value is None:
            continue
        address = int(_addr(address_value), 16)
        if row.get("block") != ".rdata" or row.get("length") != 4 or row.get("raw_truncated") is not False:
            continue
        raw_hex = row.get("raw_hex")
        if not isinstance(raw_hex, str) or len(raw_hex) != 8:
            continue
        try:
            raw = bytes.fromhex(raw_hex)
        except ValueError:
            continue
        target = int.from_bytes(raw, "little")
        pointers[address] = {**row, "decoded_target": target}
    return pointers


def _ordered_instructions(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    items = []
    for instruction in row.get("instructions") or []:
        if not isinstance(instruction, dict):
            raise ValueError("instruction row contains non-object instruction")
        copied = dict(instruction)
        copied["_address_int"] = int(_addr(copied.get("address"), field="instruction.address"), 16)
        items.append(copied)
    items.sort(key=lambda item: item["_address_int"])
    return items


def _select_vtable_load(
    function: str,
    call: str,
    dereferences: list[dict[str, Any]],
) -> dict[str, Any]:
    call_value = int(call, 16)
    candidates = []
    for item in dereferences:
        if _addr(item.get("function"), field="dereference.function") != function:
            continue
        address = _addr(item.get("instruction"), field="dereference.instruction")
        if int(address, 16) >= call_value:
            continue
        text = str(item.get("instruction_text") or "")
        if not text.upper().startswith("MOV EAX,"):
            continue
        candidates.append((int(address, 16), item))
    if not candidates:
        raise ValueError(f"{function}:{call}: no preceding proven manager primary-table dereference")
    return max(candidates, key=lambda pair: pair[0])[1]


def _resolve_call(
    transfer: Mapping[str, Any],
    row: Mapping[str, Any],
    dereferences: list[dict[str, Any]],
    static_pointers: Mapping[int, dict[str, Any]],
) -> dict[str, Any]:
    function = _addr(transfer.get("function"), field="transfer.function")
    call = _addr(transfer.get("instruction"), field="transfer.instruction")
    vtable_sink = _select_vtable_load(function, call, dereferences)
    vtable_load = _addr(vtable_sink.get("instruction"), field="dereference.instruction")
    manager_storage = str(vtable_sink.get("base_register") or "").upper()
    if manager_storage not in {"ECX", "ESI"}:
        raise ValueError(f"{function}:{call}: unsupported manager storage register {manager_storage}")

    instructions = _ordered_instructions(row)
    index = {int(item["_address_int"]): pos for pos, item in enumerate(instructions)}
    vtable_value = int(vtable_load, 16)
    call_value = int(call, 16)
    if vtable_value not in index or call_value not in index or index[vtable_value] >= index[call_value]:
        raise ValueError(f"{function}:{call}: required dispatch instructions missing or reordered")
    start = index[vtable_value]
    end = index[call_value]
    dispatch = instructions[start : end + 1]

    first = dispatch[0]
    if str(first.get("mnemonic") or "").upper() != "MOV":
        raise ValueError(f"{function}:{vtable_load}: expected MOV primary-table load")
    first_ops = _operands(first)
    if len(first_ops) != 2 or first_ops[0].strip().upper() != "EAX" or _parse_memory(first_ops[1]) != (manager_storage, 0):
        raise ValueError(f"{function}:{vtable_load}: primary-table load shape drift")

    last = dispatch[-1]
    if str(last.get("mnemonic") or "").upper() != "CALL" or [x.upper() for x in _operands(last)] != ["EDX"]:
        raise ValueError(f"{function}:{call}: expected CALL EDX")

    # This proof is deliberately limited to a straight-line dispatch window.
    for instruction in dispatch[1:-1]:
        mnemonic = str(instruction.get("mnemonic") or "").upper()
        if mnemonic == "CALL" or mnemonic == "RET" or mnemonic.startswith(_BRANCH_PREFIXES):
            raise ValueError(f"{function}:{call}: control-flow boundary inside dispatch window at {instruction.get('address')}")

    edx_writer = None
    for instruction in reversed(dispatch[:-1]):
        if _writes_register(instruction, "EDX"):
            edx_writer = instruction
            break
    if edx_writer is None:
        raise ValueError(f"{function}:{call}: no EDX producer before indirect call")
    if str(edx_writer.get("mnemonic") or "").upper() != "MOV":
        raise ValueError(f"{function}:{call}: last EDX producer is not MOV")
    edx_ops = _operands(edx_writer)
    if len(edx_ops) != 2 or edx_ops[0].strip().upper() != "EDX":
        raise ValueError(f"{function}:{call}: EDX producer operand drift")
    memory = _parse_memory(edx_ops[1])
    if memory is None or memory[0] != "EAX":
        raise ValueError(f"{function}:{call}: EDX is not loaded from the proven primary-table register EAX")
    displacement = memory[1]
    if displacement < 0 or displacement % 4 != 0 or displacement > 0x400:
        raise ValueError(f"{function}:{call}: invalid primary-table slot displacement {displacement}")

    slot_writer_pos = next(
        pos for pos, instruction in enumerate(dispatch) if instruction is edx_writer
    )
    for instruction in dispatch[1:slot_writer_pos]:
        if _writes_register(instruction, "EAX"):
            raise ValueError(f"{function}:{call}: EAX primary-table pointer clobbered before slot load")
    for instruction in dispatch[slot_writer_pos + 1 : -1]:
        if _writes_register(instruction, "EDX"):
            raise ValueError(f"{function}:{call}: EDX slot target clobbered before CALL")

    slot_address = PRIMARY_TABLE + displacement
    static = static_pointers.get(slot_address)
    if static is None:
        raise ValueError(f"{function}:{call}: static pointer missing at 0x{slot_address:08x}")
    target = int(static["decoded_target"])
    if target == 0:
        raise ValueError(f"{function}:{call}: null primary-table target")

    return {
        "function": function,
        "call_instruction": call,
        "call_instruction_text": transfer.get("instruction_text"),
        "manager_receiver_register_at_call": str(transfer.get("source_register") or "").upper(),
        "manager_storage_register_for_primary_table_load": manager_storage,
        "primary_table_load_instruction": vtable_load,
        "primary_table_load_text": first.get("text"),
        "slot_load_instruction": _addr(edx_writer.get("address"), field="slot-load.address"),
        "slot_load_text": edx_writer.get("text"),
        "primary_table_address": f"0x{PRIMARY_TABLE:08x}",
        "slot_displacement": displacement,
        "slot_displacement_hex": f"0x{displacement:x}",
        "slot_index": displacement // 4,
        "slot_address": f"0x{slot_address:08x}",
        "static_pointer_raw_hex": static.get("raw_hex"),
        "resolved_target": f"0x{target:08x}",
        "manager_receiver_identity_proven": True,
        "constructor_primary_table_identity_proven": True,
        "straight_line_slot_load_proven": True,
        "static_slot_target_proven": True,
        "callee_ca4_access_proven": False,
    }


def analyze(
    direct_ca4_path: Path,
    receiver_frontier_path: Path,
    constructor_instructions_path: Path,
    static_tables_path: Path,
    caller_instructions_path: Path,
) -> dict[str, Any]:
    direct = _validate_direct_negative(direct_ca4_path)
    frontier, transfers, dereferences = _validate_frontier(receiver_frontier_path)
    _validate_constructor_primary_table(constructor_instructions_path)
    static_pointers = _load_static_pointers(static_tables_path)
    callers = _load_instruction_rows(caller_instructions_path, expected=EXPECTED_CALLERS)

    resolved = []
    for transfer in sorted(transfers, key=lambda item: (item["key"][0], item["key"][1])):
        function = transfer["key"][0]
        resolved.append(_resolve_call(transfer, callers[function], dereferences, static_pointers))

    targets = sorted({item["resolved_target"] for item in resolved}, key=lambda value: int(value, 16))
    ready = len(resolved) == len(EXPECTED_INDIRECT_CALLS) and bool(targets)

    blockers = []
    if not ready:
        blockers.append(
            {
                "id": "proven-manager-indirect-dispatch-target-unresolved",
                "evidence_state": "blocked",
                "required_evidence": "all three proven manager CALL EDX sites must resolve through the constructor-backed 0x00ab5644 primary table",
            }
        )
    else:
        blockers.append(
            {
                "id": "indirect-manager-method-ca4-runtime-access-unproven",
                "evidence_state": "unknown",
                "required_evidence": "targeted resolved indirect callees must be checked for entry ECX manager receiver -> p-code-backed +0xca4 access",
            }
        )
    blockers.extend(
        [
            {
                "id": "player-vehicle-renderables-to-render-owner-join-unproven",
                "evidence_state": "unknown",
                "required_evidence": "trace the exact value loaded from a proven manager +0xca4 field into the SMS/RenderHierarchy owner lane",
            },
            {
                "id": "outer-vehicle-root-to-VHF-vehicle-root-frame-relation-unproven",
                "evidence_state": "unknown",
                "required_evidence": "join the proven render owner to canonical BMW VHF root/frame identity",
            },
        ]
    )

    return {
        "format": FORMAT,
        "version": 1,
        "status": "indirect-manager-method-worklist-ready" if ready else "indirect-manager-dispatch-blocked",
        "ready": ready,
        "retail": {"program": PROGRAM, "md5": PE_MD5},
        "candidate_global": {
            "address": CANDIDATE_GLOBAL,
            "render_manager_class_identity_proven": True,
            "non_null_FUN_0045ef50_receiver_proven": True,
        },
        "constructor_primary_table": {
            "function": CONSTRUCTOR,
            "receiver_save_instruction": CTOR_RECEIVER_SAVE,
            "primary_table_store_instruction": CTOR_PRIMARY_TABLE_STORE,
            "primary_table_address": f"0x{PRIMARY_TABLE:08x}",
            "source_backed": True,
        },
        "inputs": {
            "direct_ca4": {
                "format": direct.get("format"),
                "ready": direct.get("ready"),
                "targeted_direct_callee_count": ((direct.get("provenance") or {}).get("targeted_direct_callee_count")),
            },
            "receiver_transfer_frontier": {
                "format": frontier.get("format"),
                "ready": frontier.get("ready"),
                "indirect_call_receiver_transfer_count": ((frontier.get("provenance") or {}).get("indirect_call_receiver_transfer_count")),
            },
            "constructor_instruction_export": {
                "format": INSTRUCTION_FORMAT,
                "required_functions": [WRITER, CONSTRUCTOR],
            },
            "caller_instruction_export": {
                "format": INSTRUCTION_FORMAT,
                "selected_function_count": len(callers),
                "functions": sorted(callers),
            },
            "static_tables": {
                "primary_table_address": f"0x{PRIMARY_TABLE:08x}",
                "exact_slot_pointer_rows_used": True,
            },
        },
        "analysis": {
            "resolved_indirect_calls": resolved,
            "resolved_indirect_call_count": len(resolved),
            "resolved_unique_target_count": len(targets),
        },
        "provenance": {
            "frozen_indirect_receiver_transfer_count": len(EXPECTED_INDIRECT_CALLS),
            "constructor_primary_table_store_proven": True,
            "straight_line_dispatch_resolution_required": True,
            "static_slot_pointer_required": True,
            "resolved_indirect_call_count": len(resolved),
        },
        "targeted_instruction_worklist": {
            "function_count": len(targets),
            "functions": targets,
            "max_functions": 8,
            "neighbors_added": False,
            "selection_rule": "only exact static targets resolved from the three proven manager CALL EDX sites through constructor primary table 0x00ab5644",
        },
        "blockers": blockers,
        "handoff": {
            "candidate_global_manager_indirect_dispatch_resolved": ready,
            "candidate_global_manager_indirect_method_worklist_ready": ready and bool(targets),
            "player_vehicle_renderables_field_runtime_access_ready": False,
            "player_vehicle_renderables_owner_join_ready": False,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "scope": {
            "direct_manager_method_ca4_branch_reopened": False,
            "direct_manager_method_ca4_branch_remains_negative": True,
            "broad_callgraph_neighbors_added": False,
            "indirect_calls_outside_frozen_frontier_considered": False,
            "constructor_primary_table_store_revalidated": True,
            "static_table_pointer_values_used_as_exact_targets": True,
            "callgraph_proximity_promoted_to_identity": False,
            "field_runtime_access_promoted": False,
            "render_owner_promoted": False,
            "VHF_root_or_frame_identity_promoted": False,
            "BODY0_bind_frame_promoted": False,
            "original_game_executed": False,
            "runtime_capture_required": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("direct_ca4_negative", type=Path)
    parser.add_argument("receiver_transfer_frontier_v2", type=Path)
    parser.add_argument("constructor_writer_instructions", type=Path)
    parser.add_argument("static_tables", type=Path)
    parser.add_argument("caller_instructions", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)
    try:
        report = analyze(
            args.direct_ca4_negative,
            args.receiver_transfer_frontier_v2,
            args.constructor_writer_instructions,
            args.static_tables,
            args.caller_instructions,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}")
        return 2
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
