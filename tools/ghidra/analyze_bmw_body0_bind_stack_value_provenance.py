#!/usr/bin/env python3
"""Resolve FUN_007b7840 stack argument values at every proven callsite.

Consumes SHIFT.BMWBody0BindPoseWriterABI/1 from Process 1 #1210 and targeted
SHIFT.GhidraFunctionInstructions/2 rows. For every ABI stack slot this pass
walks the unique machine predecessor chain backwards from the exact CALL,
identifies the corresponding IA-32 PUSH, and resolves register PUSH operands to
their nearest older MOV/LEA producer on the same machine lane.

This is mechanical value provenance only. It does not assign BODY/origin/basis
semantics to any parameter and does not promote FUN_007b7840 to a bind
initializer.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.BMWBody0BindStackValueProvenance/1"
ABI_FORMAT = "SHIFT.BMWBody0BindPoseWriterABI/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
POSE_WRITER = "0x007b7840"
WORD_SIZE = 4
MAX_BACKWARD_INSTRUCTIONS = 64

_GENERAL_REGISTERS = {"EAX", "EBX", "ECX", "EDX", "ESI", "EDI", "EBP", "ESP"}
_READ_ONLY_FIRST_OPERAND = {"CMP", "TEST", "PUSH"}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _addr(value: Any, *, field: str = "address") -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field}: expected address string")
    token = value.strip().lower()
    if token.startswith("fun_"):
        token = token[4:]
    if token.startswith("0x"):
        token = token[2:]
    try:
        return f"0x{int(token, 16):08x}"
    except ValueError as exc:
        raise ValueError(f"{field}: invalid address {value!r}") from exc


def _read_json(path: Path, expected: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(value, dict) or value.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_no}: expected object")
        rows.append(value)
    return rows


def _ops(instruction: dict[str, Any]) -> list[str]:
    operands = instruction.get("operands")
    if not isinstance(operands, list) or any(not isinstance(item, str) for item in operands):
        raise ValueError(f"{instruction.get('address')}: operands must be string list")
    return [" ".join(item.upper().split()) for item in operands]


def _function_rows(path: Path) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for row in _read_jsonl(path):
        _require(row.get("format") == INSTRUCTION_FORMAT, f"{path}: instruction format drift")
        _require(row.get("found") is True, f"{path}: targeted function unresolved")
        function = row.get("function")
        _require(isinstance(function, dict), f"{path}: function metadata missing")
        address = _addr(function.get("address"), field="function.address")
        _require(address not in result, f"{path}: duplicate function row {address}")
        instructions = row.get("instructions")
        _require(isinstance(instructions, list) and instructions, f"{address}: instructions missing")
        _require(row.get("instruction_count") == len(instructions), f"{address}: instruction_count mismatch")
        previous = -1
        seen: set[str] = set()
        for ordinal, instruction in enumerate(instructions):
            _require(isinstance(instruction, dict), f"{address}: instruction {ordinal} is not object")
            ins_address = _addr(instruction.get("address"), field="instruction.address")
            numeric = int(ins_address, 0)
            _require(numeric > previous, f"{address}: instruction addresses not strictly increasing")
            _require(ins_address not in seen, f"{address}: duplicate instruction {ins_address}")
            previous = numeric
            seen.add(ins_address)
        result[address] = instructions
    return result


def _direct_target(instruction: dict[str, Any]) -> str | None:
    for value in list(instruction.get("flows") or []) + list(instruction.get("operands") or []):
        if not isinstance(value, str):
            continue
        try:
            if _addr(value, field="call target") == POSE_WRITER:
                return POSE_WRITER
        except ValueError:
            pass
    return None


def _successors(instruction: dict[str, Any], addresses: set[str]) -> set[str]:
    result: set[str] = set()
    fallthrough = instruction.get("fallthrough")
    if isinstance(fallthrough, str):
        try:
            normalized = _addr(fallthrough, field="fallthrough")
            if normalized in addresses:
                result.add(normalized)
        except ValueError:
            pass
    flow_type = str(instruction.get("flow_type") or "").upper()
    if "CALL" not in flow_type:
        flows = instruction.get("flows")
        if isinstance(flows, list):
            for value in flows:
                if not isinstance(value, str):
                    continue
                try:
                    normalized = _addr(value, field="flow")
                except ValueError:
                    continue
                if normalized in addresses:
                    result.add(normalized)
    return result


def _predecessors(instructions: list[dict[str, Any]]) -> dict[str, list[str]]:
    addresses = {_addr(row.get("address"), field="instruction.address") for row in instructions}
    result: dict[str, list[str]] = {address: [] for address in addresses}
    for instruction in instructions:
        source = _addr(instruction.get("address"), field="instruction.address")
        for target in _successors(instruction, addresses):
            result[target].append(source)
    for values in result.values():
        values.sort(key=lambda value: int(value, 0))
    return result


def _index(instructions: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        _addr(instruction.get("address"), field="instruction.address"): instruction
        for instruction in instructions
    }


def _first_operand_writes_register(instruction: dict[str, Any], register: str) -> bool:
    operands = _ops(instruction)
    if not operands or operands[0] != register:
        return False
    mnemonic = str(instruction.get("mnemonic") or "").upper()
    return mnemonic not in _READ_ONLY_FIRST_OPERAND


def _writes_esp(instruction: dict[str, Any]) -> bool:
    mnemonic = str(instruction.get("mnemonic") or "").upper()
    operands = _ops(instruction)
    if mnemonic in {"PUSH", "POP"}:
        return True
    return bool(operands and operands[0] == "ESP" and mnemonic not in _READ_ONLY_FIRST_OPERAND)


def _find_register_source(
    register: str,
    older_lane: list[dict[str, Any]],
) -> dict[str, Any] | None:
    _require(register in _GENERAL_REGISTERS and register != "ESP", f"unsupported pushed register {register}")
    for instruction in older_lane:
        mnemonic = str(instruction.get("mnemonic") or "").upper()
        address = _addr(instruction.get("address"), field="producer.address")
        if mnemonic == "CALL" or "CALL" in str(instruction.get("flow_type") or "").upper():
            raise ValueError(f"{address}: CALL blocks register value provenance for {register}")
        if not _first_operand_writes_register(instruction, register):
            continue
        operands = _ops(instruction)
        _require(
            mnemonic in {"MOV", "LEA"} and len(operands) == 2,
            f"{address}: unsupported {register} writer {mnemonic}",
        )
        source = operands[1]
        _require(source not in _GENERAL_REGISTERS, f"{address}: transitive register source {source} remains unresolved")
        _require("ESP" not in source, f"{address}: ESP-relative source remains stack-position dependent")
        return {
            "producer_instruction": address,
            "producer_mnemonic": mnemonic,
            "producer_operand": source,
            "value_expression": source,
            "value_provenance_ready": True,
        }
    return None


def _validate_abi(abi: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pose_writer = abi.get("pose_writer")
    _require(isinstance(pose_writer, dict), "pose_writer missing")
    _require(_addr(pose_writer.get("address"), field="pose_writer.address") == POSE_WRITER, "pose-writer address drift")

    analysis = abi.get("analysis")
    _require(isinstance(analysis, dict), "ABI analysis missing")
    callsites = analysis.get("callsites")
    _require(isinstance(callsites, list) and callsites, "ABI contains no callsites")
    _require(analysis.get("callsite_count") == len(callsites), "ABI callsite count mismatch")
    _require(analysis.get("all_callsites_parameter_storage_bound") is True, "ABI storage binding incomplete")
    stack_worklist = analysis.get("stack_value_worklist")
    _require(isinstance(stack_worklist, list) and stack_worklist, "ABI has no unresolved stack worklist")

    handoff = abi.get("handoff")
    _require(isinstance(handoff, dict), "ABI handoff missing")
    _require(handoff.get("pose_writer_parameter_storage_binding_ready") is True, "ABI parameter storage not ready")
    _require(handoff.get("pose_writer_stack_argument_locations_ready") is True, "ABI stack locations not ready")
    _require(handoff.get("pose_writer_stack_argument_values_ready") is False, "ABI unexpectedly preclaims stack values")
    _require(handoff.get("BODY0_bind_frame_proof_ready") is False, "ABI unexpectedly preclaims bind frame")

    normalized_worklist: list[dict[str, Any]] = []
    seen_offsets: set[int] = set()
    for row in stack_worklist:
        _require(isinstance(row, dict), "stack worklist row invalid")
        offset = row.get("stack_offset")
        size = row.get("size")
        _require(isinstance(offset, int) and offset >= WORD_SIZE, "invalid stack offset")
        _require(offset % WORD_SIZE == 0, f"unaligned stack offset 0x{offset:x}")
        _require(size == WORD_SIZE, f"unsupported stack slot width at 0x{offset:x}: {size}")
        _require(offset not in seen_offsets, f"duplicate stack worklist offset 0x{offset:x}")
        seen_offsets.add(offset)
        normalized_worklist.append({**row, "stack_offset": offset})
    normalized_worklist.sort(key=lambda row: row["stack_offset"])

    normalized_callsites: list[dict[str, Any]] = []
    seen_callsites: set[tuple[str, str]] = set()
    for index, row in enumerate(callsites):
        _require(isinstance(row, dict), f"callsites[{index}] invalid")
        caller = _addr(row.get("caller"), field=f"callsites[{index}].caller")
        callsite = _addr(row.get("callsite"), field=f"callsites[{index}].callsite")
        target = _addr(row.get("target"), field=f"callsites[{index}].target")
        _require(target == POSE_WRITER, f"{caller}:{callsite}: target drift")
        _require(row.get("parameter_storage_binding_ready") is True, f"{caller}:{callsite}: storage binding not ready")
        _require(row.get("stack_parameter_value_provenance_ready") is False, f"{caller}:{callsite}: stack values unexpectedly preclaimed")
        key = (caller, callsite)
        _require(key not in seen_callsites, f"duplicate ABI callsite {caller}:{callsite}")
        seen_callsites.add(key)
        normalized_callsites.append({**row, "caller": caller, "callsite": callsite})
    normalized_callsites.sort(key=lambda row: (int(row["caller"], 0), int(row["callsite"], 0)))
    return normalized_callsites, normalized_worklist


def _all_register_push_sources_ready(
    pushes: list[dict[str, Any]],
    lane: list[dict[str, Any]],
) -> bool:
    for push in pushes:
        operand = push["push_operand"]
        if operand not in _GENERAL_REGISTERS:
            continue
        source = _find_register_source(operand, lane[push["lane_index"] + 1 :])
        if source is None:
            return False
    return True


def _trace_callsite(
    caller: str,
    callsite: str,
    instructions: list[dict[str, Any]],
    stack_worklist: list[dict[str, Any]],
) -> dict[str, Any]:
    by_address = _index(instructions)
    call = by_address.get(callsite)
    _require(call is not None, f"{caller}: missing ABI callsite {callsite}")
    _require(str(call.get("mnemonic") or "").upper() == "CALL", f"{caller}:{callsite}: not CALL")
    _require(_direct_target(call) == POSE_WRITER, f"{caller}:{callsite}: direct target drift")

    predecessors = _predecessors(instructions)
    needed_pushes = max(row["stack_offset"] for row in stack_worklist) // WORD_SIZE
    pushes: list[dict[str, Any]] = []
    lane: list[dict[str, Any]] = []
    current = callsite

    for _ in range(MAX_BACKWARD_INSTRUCTIONS):
        incoming = predecessors.get(current, [])
        _require(len(incoming) == 1, f"{caller}:{current}: predecessor count {len(incoming)} blocks stack proof")
        previous = incoming[0]
        instruction = by_address[previous]
        mnemonic = str(instruction.get("mnemonic") or "").upper()
        flow_type = str(instruction.get("flow_type") or "").upper()
        if mnemonic == "CALL" or "CALL" in flow_type:
            raise ValueError(f"{caller}:{previous}: CALL encountered before stack provenance resolved")

        lane.append(instruction)
        if mnemonic == "PUSH" and len(pushes) < needed_pushes:
            operands = _ops(instruction)
            _require(len(operands) == 1, f"{caller}:{previous}: malformed PUSH")
            pushes.append(
                {
                    "push_instruction": previous,
                    "push_operand": operands[0],
                    "lane_index": len(lane) - 1,
                    "callee_stack_offset": len(pushes) * WORD_SIZE + WORD_SIZE,
                }
            )
        elif len(pushes) < needed_pushes and _writes_esp(instruction):
            raise ValueError(f"{caller}:{previous}: unsupported ESP mutation before stack worklist resolved")

        if len(pushes) >= needed_pushes and _all_register_push_sources_ready(pushes, lane):
            break
        current = previous
    else:
        raise ValueError(f"{caller}:{callsite}: backward stack proof exceeded instruction bound")

    by_offset: dict[int, dict[str, Any]] = {}
    for push in pushes:
        operand = push["push_operand"]
        if operand in _GENERAL_REGISTERS:
            source = _find_register_source(operand, lane[push["lane_index"] + 1 :])
            _require(source is not None, f"{caller}:{push['push_instruction']}: register source unresolved")
        else:
            source = {
                "producer_instruction": push["push_instruction"],
                "producer_mnemonic": "PUSH",
                "producer_operand": operand,
                "value_expression": operand,
                "value_provenance_ready": True,
            }
        by_offset[push["callee_stack_offset"]] = {**push, **source}

    resolved_slots: list[dict[str, Any]] = []
    for requested in stack_worklist:
        offset = requested["stack_offset"]
        push = by_offset.get(offset)
        _require(push is not None, f"{caller}:{callsite}: no PUSH resolved for stack offset 0x{offset:x}")
        resolved_slots.append(
            {
                "storage": requested.get("storage"),
                "stack_offset": offset,
                "stack_offset_hex": f"0x{offset:x}",
                "size": requested["size"],
                "push_instruction": push["push_instruction"],
                "push_operand": push["push_operand"],
                "value_expression": push["value_expression"],
                "value_producer_instruction": push["producer_instruction"],
                "value_producer_mnemonic": push["producer_mnemonic"],
                "value_provenance_ready": True,
                "semantic_role": None,
                "semantic_role_proven": False,
            }
        )

    return {
        "caller": caller,
        "callsite": callsite,
        "target": POSE_WRITER,
        "unique_predecessor_stack_lane_proven": True,
        "backward_lane_instruction_count": len(lane),
        "resolved_stack_slot_count": len(resolved_slots),
        "resolved_stack_slots": resolved_slots,
        "stack_parameter_value_provenance_ready": True,
        "parameter_semantic_roles_ready": False,
        "BODY0_pointer_proven": False,
        "bind_initializer_semantics_proven": False,
    }


def analyze_bmw_body0_bind_stack_value_provenance(
    abi_path: Path,
    instruction_export_path: Path,
) -> dict[str, Any]:
    abi = _read_json(abi_path, ABI_FORMAT)
    callsites, stack_worklist = _validate_abi(abi)
    instruction_rows = _function_rows(instruction_export_path)

    required_callers = sorted({row["caller"] for row in callsites}, key=lambda value: int(value, 0))
    missing = [caller for caller in required_callers if caller not in instruction_rows]
    _require(not missing, "instruction export missing ABI caller(s): " + ", ".join(missing))

    analyses = [
        _trace_callsite(
            row["caller"],
            row["callsite"],
            instruction_rows[row["caller"]],
            stack_worklist,
        )
        for row in callsites
    ]

    return {
        "format": FORMAT,
        "inputs": {
            "pose_writer_abi": str(abi_path),
            "instruction_export": str(instruction_export_path),
        },
        "target": {
            "pose_writer": POSE_WRITER,
            "callsite_count": len(analyses),
            "stack_slot_count": len(stack_worklist),
            "stack_slots": [row.get("storage") for row in stack_worklist],
        },
        "analysis": {
            "callsites": analyses,
            "all_abi_callsites_analyzed": len(analyses) == len(callsites),
            "all_stack_slots_resolved_at_every_callsite": all(
                row["stack_parameter_value_provenance_ready"] for row in analyses
            ),
            "path_aware_unique_predecessor_model": True,
            "parameter_semantic_roles_ready": False,
            "BODY0_pointer_at_bind_callsite_ready": False,
            "BODY0_bind_origin_basis_values_ready": False,
            "BODY0_bind_frame_proof_ready": False,
        },
        "handoff": {
            "pose_writer_stack_argument_values_ready": True,
            "pose_writer_parameter_value_provenance_ready": True,
            "pose_writer_ABI_semantic_roles_ready": False,
            "BODY0_pointer_at_bind_callsite_ready": False,
            "BODY0_bind_origin_basis_values_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "next_required_join": (
                "FUN_007b7840 machine/p-code parameter-role proof, then exact BODY0 receiver/value join"
            ),
        },
        "blockers": [
            {"id": "pose-writer-parameter-semantic-roles-unproven", "evidence_state": "unknown"},
            {"id": "BODY0-pointer-at-bind-callsite-unproven", "evidence_state": "unknown"},
            {"id": "bind-origin-basis-value-provenance-unproven", "evidence_state": "unknown"},
        ],
        "scope": {
            "stack_slot_location_inferred_from_call_order_without_ABI": False,
            "lexical_window_used_as_path_proof": False,
            "unique_predecessor_machine_lane_required": True,
            "parameter_ordinal_used_as_semantic_role": False,
            "reported_parameter_name_trusted_as_semantics": False,
            "BODY0_pointer_identity_proven": False,
            "pose_writer_candidate_promoted_to_initializer": False,
            "BODY0_bind_matrix_proven": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pose_writer_abi", type=Path)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    report = analyze_bmw_body0_bind_stack_value_provenance(
        args.pose_writer_abi,
        args.instruction_export,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
