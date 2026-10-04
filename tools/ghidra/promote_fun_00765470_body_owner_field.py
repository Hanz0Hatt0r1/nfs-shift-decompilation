#!/usr/bin/env python3
"""Promote the retail FUN_00765470 BODY-loop receiver to a vehicle field edge.

The first receiver analyzer intentionally asked a stricter question: whether ECX
at 0x0076582a is the same pointer as FUN_00765470 entry ECX.  Retail evidence
shows that equality is false.  This promotion proves the actual machine edge:

    entry ECX -> ESI -> [ESI + 0x339c] -> ECX -> FUN_007b2270

It does not claim the pointed object equals the vehicle base, assign a class
name, or admit Phase 698 by itself.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.Fun00765470BodyOwnerFieldProvenance/1"
RECEIVER_FORMAT = "SHIFT.Fun00765470BodyOwnerReceiverProvenance/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
TARGET_ADDRESS = "0x00765470"
TARGET_NAME = "FUN_00765470"
ENTRY_COPY = "0x0076548a"
ENTRY_COPY_BYTES = "8bf1"
OWNER_LOAD = "0x00765824"
OWNER_LOAD_BYTES = "8b8e9c330000"
OWNER_FIELD_OFFSET = 0x339C
BODY_LOOP_CALL = "0x0076582a"
BODY_LOOP_TARGET = "0x007b2270"
EXPECTED_OLD_ORIGIN = "memory:dword ptr [esi + 0x339c]"


def _norm_address(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError(f"invalid address: {value!r}")
    token = value.strip().lower()
    if token.startswith("fun_"):
        token = token[4:]
    if token.startswith("0x"):
        token = token[2:]
    try:
        return f"0x{int(token, 16):08x}"
    except ValueError as exc:
        raise ValueError(f"invalid address: {value!r}") from exc


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _load_instruction_row(path: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
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
            rows.append(value)
    if len(rows) != 1:
        raise ValueError(f"{path}: expected one instruction row; found {len(rows)}")
    return rows[0]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _upper_operands(instruction: dict[str, Any]) -> list[str]:
    operands = instruction.get("operands")
    if not isinstance(operands, list) or any(not isinstance(item, str) for item in operands):
        raise ValueError(f"{instruction.get('address')}: operands must be string list")
    return [" ".join(item.upper().split()) for item in operands]


def _direct_call_target(instruction: dict[str, Any]) -> str | None:
    flows = instruction.get("flows")
    if isinstance(flows, list):
        for item in flows:
            if isinstance(item, str):
                try:
                    if _norm_address(item) == BODY_LOOP_TARGET:
                        return BODY_LOOP_TARGET
                except ValueError:
                    pass
    for item in instruction.get("operands") or []:
        if isinstance(item, str):
            try:
                if _norm_address(item) == BODY_LOOP_TARGET:
                    return BODY_LOOP_TARGET
            except ValueError:
                pass
    return None


def _first_operand_esi_writers_before_load(instructions: list[dict[str, Any]]) -> list[str]:
    """Return machine instructions that can syntactically replace ESI before OWNER_LOAD.

    PUSH/CMP/TEST are read-only for their first operand.  CALL is not included:
    under the IA-32 ABI used by the existing receiver analyzer, ESI is callee
    saved.  Unknown first-operand forms fail closed rather than being ignored.
    """
    read_only = {"PUSH", "CMP", "TEST"}
    writers: list[str] = []
    for instruction in instructions:
        address = _norm_address(instruction.get("address"))
        if int(address, 16) >= int(OWNER_LOAD, 16):
            break
        operands = _upper_operands(instruction)
        if not operands or operands[0] != "ESI":
            continue
        mnemonic = str(instruction.get("mnemonic") or "").upper()
        if mnemonic in read_only:
            continue
        writers.append(address)
    return writers


def promote_fun_00765470_body_owner_field(
    receiver_report_path: Path,
    instruction_export_path: Path,
) -> dict[str, Any]:
    receiver = _load_json(receiver_report_path)
    _require(receiver.get("format") == RECEIVER_FORMAT, f"receiver report must be {RECEIVER_FORMAT}")
    target = receiver.get("target") or {}
    _require(_norm_address(target.get("address")) == TARGET_ADDRESS, "receiver target address drift")
    _require(target.get("function") == TARGET_NAME, "receiver target function drift")
    _require(_norm_address(target.get("body_loop_call_instruction")) == BODY_LOOP_CALL, "BODY-loop call drift")
    _require(_norm_address(target.get("body_loop_target")) == BODY_LOOP_TARGET, "BODY-loop target drift")
    _require(target.get("physical_receiver_register") == "ECX", "BODY-loop receiver register drift")

    analysis = receiver.get("analysis") or {}
    origins = analysis.get("receiver_origins_before_body_loop_call")
    _require(origins == [EXPECTED_OLD_ORIGIN], "receiver report does not expose the exact retail +0x339c field origin")
    _require(analysis.get("receiver_origin_cardinality") == 1, "receiver origin is not unique")
    _require(analysis.get("receiver_equals_half_step_entry_ECX_on_all_reachable_paths") is False, "retail receiver unexpectedly equals entry ECX")
    _require(analysis.get("function_instruction_count") == analysis.get("reachable_instruction_count"), "receiver report does not cover every function instruction")
    scope = receiver.get("scope") or {}
    _require(scope.get("physical_register_provenance_only") is True, "receiver report scope drift")
    _require(scope.get("original_game_executed") is False, "receiver report used original-game execution")
    _require(scope.get("new_runtime_capture_required") is False, "receiver report requires new runtime capture")

    row = _load_instruction_row(instruction_export_path)
    _require(row.get("format") == INSTRUCTION_FORMAT, f"instruction export must be {INSTRUCTION_FORMAT}")
    _require(row.get("found") is True, "FUN_00765470 instruction row was not found")
    function = row.get("function") or {}
    _require(_norm_address(function.get("address")) == TARGET_ADDRESS, "instruction target address drift")
    _require(function.get("name") == TARGET_NAME, "instruction target name drift")
    instructions = row.get("instructions")
    _require(isinstance(instructions, list) and instructions, "instruction list is empty")
    _require(row.get("instruction_count") == len(instructions), "instruction_count mismatch")
    by_address = {_norm_address(item.get("address")): item for item in instructions if isinstance(item, dict)}
    _require(len(by_address) == len(instructions), "instruction addresses are missing or duplicated")

    entry_copy = by_address.get(ENTRY_COPY)
    _require(entry_copy is not None, f"missing entry receiver copy {ENTRY_COPY}")
    _require(str(entry_copy.get("mnemonic") or "").upper() == "MOV", "entry receiver copy is not MOV")
    _require(_upper_operands(entry_copy) == ["ESI", "ECX"], "entry receiver copy is not ESI <- ECX")
    _require(str(entry_copy.get("bytes") or "").lower() == ENTRY_COPY_BYTES, "entry receiver copy bytes drift")

    esi_writers = _first_operand_esi_writers_before_load(instructions)
    _require(esi_writers == [ENTRY_COPY], f"ESI provenance before owner load is not unique: {esi_writers}")

    owner_load = by_address.get(OWNER_LOAD)
    _require(owner_load is not None, f"missing BODY-owner field load {OWNER_LOAD}")
    _require(str(owner_load.get("mnemonic") or "").upper() == "MOV", "BODY-owner field load is not MOV")
    _require(
        _upper_operands(owner_load) == ["ECX", "DWORD PTR [ESI + 0X339C]"],
        "BODY-owner field load operands drift",
    )
    _require(str(owner_load.get("bytes") or "").lower() == OWNER_LOAD_BYTES, "BODY-owner field load bytes drift")
    _require(_norm_address(owner_load.get("fallthrough")) == BODY_LOOP_CALL, "BODY-owner field load is not immediately before BODY-loop call")

    call = by_address.get(BODY_LOOP_CALL)
    _require(call is not None, f"missing BODY-loop call {BODY_LOOP_CALL}")
    _require(str(call.get("mnemonic") or "").upper() == "CALL", "BODY-loop instruction is not CALL")
    _require(_direct_call_target(call) == BODY_LOOP_TARGET, "BODY-loop direct target drift")

    return {
        "format": FORMAT,
        "inputs": {
            "receiver_report": str(receiver_report_path),
            "instruction_export": str(instruction_export_path),
            "instruction_format": INSTRUCTION_FORMAT,
        },
        "target": {
            "function": TARGET_NAME,
            "address": TARGET_ADDRESS,
            "body_loop_call_instruction": BODY_LOOP_CALL,
            "body_loop_target": BODY_LOOP_TARGET,
        },
        "machine_edge": {
            "entry_receiver_register": "ECX",
            "preserved_base_register": "ESI",
            "entry_receiver_copy_instruction": ENTRY_COPY,
            "entry_receiver_copy_bytes": ENTRY_COPY_BYTES,
            "BODY_owner_pointer_field_offset": f"0x{OWNER_FIELD_OFFSET:04x}",
            "BODY_owner_pointer_load_instruction": OWNER_LOAD,
            "BODY_owner_pointer_load_bytes": OWNER_LOAD_BYTES,
            "BODY_owner_pointer_expression": "dword ptr [entry:ECX + 0x339c]",
            "call_receiver_register": "ECX",
            "entry_receiver_equals_call_receiver_pointer": False,
            "entry_receiver_to_BODY_owner_pointer_field_edge_proven": True,
        },
        "handoff": {
            "half_step_entry_ECX_to_BODY_array_owner_field_continuity_proven": True,
            "BODY_array_owner_pointer_field_offset": f"0x{OWNER_FIELD_OFFSET:04x}",
            "global_vehicle_to_BODY_owner_composition_ready": True,
            "phase703_gate_rewrite_ready": True,
            "phase698_positive_selection_admissible_by_this_artifact_alone": False,
            "next_required_composition": "SHIFT.GlobalVehicleComponentBaseIdentity/1 + this field edge + proven BMW chassis BODY 0",
        },
        "blockers": [],
        "scope": {
            "BODY_array_owner_pointer_equals_vehicle_base_proven": False,
            "BODY_owner_semantic_class_name_proven": False,
            "FUN_007b2270_class_identity_proven": False,
            "vehicle_BODY_selection_emitted": False,
            "vehicle_world_transform_mapping_proven": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receiver_report", type=Path)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    report = promote_fun_00765470_body_owner_field(args.receiver_report, args.instruction_export)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
