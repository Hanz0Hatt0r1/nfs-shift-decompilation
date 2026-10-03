#!/usr/bin/env python3
"""Verify machine-level receiver-candidate value transfer at class lifetime callsites.

This stage consumes the already-verified vehicle lifetime-pair frontier and the
underlying class lifetime-pair evidence, then reopens a targeted
SHIFT.GhidraFunctionInstructions/2 export.  It proves only narrow x86 value-flow
facts at factory->initializer and deleting-wrapper->teardown callsites.

No allocator, constructor, destructor, owner, same-object-across-lifetime, or
frame-scheduling semantics are promoted by this tool.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.VehicleLifetimePointerTransfer/1"
FRONTIER_FORMAT = "SHIFT.VehicleLifetimePairFrontier/1"
PAIR_FORMAT = "SHIFT-CLASS-LIFETIME-PAIR-EVIDENCE/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
RECEIVER_REGISTER = "ECX"
RETURN_REGISTER = "EAX"
MAX_COPY_HOPS = 8
STATES = {"proven", "verified", "inferred", "ambiguous", "unknown"}
STATE_STRENGTH = {"unknown": 0, "ambiguous": 1, "inferred": 2, "verified": 3, "proven": 4}


def _load_pointer_helper():
    path = Path(__file__).with_name("analyze_vehicle_pointer_origin_frontier.py")
    spec = importlib.util.spec_from_file_location("vehicle_pointer_origin_helper", path)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError(f"cannot load helper: {path}")
    spec.loader.exec_module(module)
    return module


def _load_json(path: Path, expected: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    if payload.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}, found {payload.get('format')}")
    return payload


def _state(value: Any, label: str) -> str:
    if value not in STATES:
        raise ValueError(f"{label}: invalid evidence state {value!r}")
    return str(value)


def _weakest(*values: str) -> str:
    checked = [_state(value, "state merge") for value in values]
    return min(checked, key=lambda value: STATE_STRENGTH[value]) if checked else "unknown"


def _normalize_address(value: Any) -> str:
    if isinstance(value, int):
        number = value
    elif isinstance(value, str):
        token = value.strip()
        if token.upper().startswith("FUN_"):
            number = int(token[4:], 16)
        else:
            number = int(token, 0)
    else:
        raise ValueError(f"invalid address {value!r}")
    if number < 0 or number > 0xFFFFFFFF:
        raise ValueError(f"address outside 32-bit range: {value!r}")
    return f"0x{number:08x}"


def _optional_address(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return _normalize_address(value)
    except (TypeError, ValueError):
        return None


def _function_list(values: Any, label: str) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list):
        raise ValueError(f"{label}: expected list")
    result = []
    for value in values:
        address = _optional_address(value)
        if address is None:
            raise ValueError(f"{label}: invalid function address {value!r}")
        result.append(address)
    return sorted(set(result))


def _pair_index(pair: dict[str, Any]) -> dict[tuple[int, str], list[dict[str, Any]]]:
    rows = pair.get("classes")
    if not isinstance(rows, list):
        raise ValueError("class lifetime-pair evidence classes must be a list")
    result: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("class lifetime-pair evidence contains invalid row")
        descriptor = row.get("descriptor")
        vtable = row.get("own_vtable")
        if not isinstance(descriptor, int) or vtable is None:
            continue
        key = descriptor, _normalize_address(vtable)
        result.setdefault(key, []).append(row)
    return result


def _frontier_rows(frontier: dict[str, Any]) -> list[dict[str, Any]]:
    rows = frontier.get("candidates")
    if not isinstance(rows, list):
        raise ValueError("vehicle lifetime-pair frontier candidates must be a list")
    result = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("vehicle lifetime-pair frontier contains invalid row")
        if row.get("verified_vehicle_lifetime_pair_frontier") is True:
            result.append(row)
    if not result:
        raise ValueError("vehicle lifetime-pair frontier has no verified candidate")
    return result


def _instruction_index(row: dict[str, Any]) -> dict[str, int]:
    function = row.get("function") or {}
    address = function.get("address")
    instructions = row.get("instructions")
    if not isinstance(address, str) or not isinstance(instructions, list):
        raise ValueError("instruction export row malformed")
    result: dict[str, int] = {}
    for index, instruction in enumerate(instructions):
        if not isinstance(instruction, dict) or not isinstance(instruction.get("address"), str):
            raise ValueError(f"{address}: invalid instruction row")
        ins_address = instruction["address"]
        if ins_address in result:
            raise ValueError(f"{address}: duplicate instruction {ins_address}")
        result[ins_address] = index
    return result


def _direct_calls(helper, row: dict[str, Any], callee: str) -> list[tuple[int, dict[str, Any]]]:
    function = row["function"]["address"]
    result = []
    for index, instruction in enumerate(row["instructions"]):
        mnemonic, operands, pcode, opcodes = helper.instruction_parts(instruction, function)
        flows = instruction.get("flows")
        if not isinstance(flows, list):
            raise ValueError(f"{instruction.get('address')}: flows must be a list")
        if callee in flows and "CALL" in opcodes:
            result.append((index, instruction))
    return result


def _single_direct_call(helper, row: dict[str, Any], callee: str) -> dict[str, Any]:
    calls = _direct_calls(helper, row, callee)
    if len(calls) == 1:
        index, instruction = calls[0]
        return {
            "evidence_state": "verified",
            "status": "exact-single-direct-call",
            "index": index,
            "instruction": instruction,
        }
    return {
        "evidence_state": "ambiguous" if calls else "unknown",
        "status": "multiple-direct-calls" if len(calls) > 1 else "direct-call-absent",
        "index": None,
        "instruction": None,
        "candidate_call_instructions": [item[1].get("address") for item in calls],
    }


def _calling_convention(rows: dict[str, dict[str, Any]], function: str) -> str | None:
    row = rows.get(function)
    if row is None:
        return None
    metadata = row.get("function")
    return metadata.get("calling_convention") if isinstance(metadata, dict) else None


def _trace_receiver(
    helper,
    row: dict[str, Any],
    before_index: int,
    *,
    expected_result_call: str | None = None,
    register: str = RECEIVER_REGISTER,
    depth: int = 0,
    visited: set[tuple[int, str]] | None = None,
) -> dict[str, Any]:
    if depth > MAX_COPY_HOPS:
        return {"evidence_state": "ambiguous", "status": "copy-hop-limit", "source": None, "chain": []}
    visited = set() if visited is None else set(visited)
    key = before_index, register
    if key in visited:
        return {"evidence_state": "ambiguous", "status": "copy-cycle", "source": None, "chain": []}
    visited.add(key)
    instructions = row["instructions"]
    function = row["function"]["address"]
    calling_convention = row["function"].get("calling_convention")

    for index in range(before_index - 1, -1, -1):
        instruction = instructions[index]
        mnemonic, operands, pcode, opcodes = helper.instruction_parts(instruction, function)
        address = instruction["address"]

        if "CALL" in opcodes or "CALLIND" in opcodes:
            flows = instruction.get("flows")
            if (
                register == RETURN_REGISTER
                and expected_result_call is not None
                and isinstance(flows, list)
                and expected_result_call in flows
                and "CALL" in opcodes
            ):
                return {
                    "evidence_state": "verified",
                    "status": "exact-direct-call-result-register",
                    "source": {
                        "kind": "direct-call-result-register",
                        "call_instruction": address,
                        "callee": expected_result_call,
                        "register": RETURN_REGISTER,
                        "pointer_semantics_proven": False,
                    },
                    "chain": [],
                }
            return {
                "evidence_state": "ambiguous",
                "status": "call-barrier-before-source",
                "source": None,
                "chain": [],
                "barrier": {"instruction": address, "instruction_text": instruction.get("text")},
            }

        stop = helper.barrier(mnemonic, opcodes)
        if stop:
            return {
                "evidence_state": "ambiguous",
                "status": "control-flow-barrier-before-source",
                "source": None,
                "chain": [],
                "barrier": {"instruction": address, "instruction_text": instruction.get("text"), "reason": stop},
            }

        destination = helper.parse_register(operands[0]) if operands else None
        if destination != register:
            continue
        if mnemonic in helper.NONWRITING_FIRST_OPERAND:
            continue
        if mnemonic != "MOV" or len(operands) < 2:
            return {
                "evidence_state": "ambiguous",
                "status": "unsupported-register-definition-or-clobber",
                "source": None,
                "chain": [],
                "clobber": {"instruction": address, "instruction_text": instruction.get("text"), "mnemonic": mnemonic},
            }

        source_operand = operands[1].strip()
        step = {
            "instruction": address,
            "instruction_text": instruction.get("text"),
            "destination_register": register,
            "source_operand": source_operand,
        }
        source_register = helper.parse_register(source_operand)
        if source_register:
            upstream = _trace_receiver(
                helper,
                row,
                index,
                expected_result_call=expected_result_call,
                register=source_register,
                depth=depth + 1,
                visited=visited,
            )
            return {
                "evidence_state": upstream["evidence_state"],
                "status": "register-copy-chain",
                "source": upstream.get("source"),
                "chain": [step] + list(upstream.get("chain") or []),
                "upstream_status": upstream.get("status"),
                "upstream_barrier": upstream.get("barrier"),
                "upstream_clobber": upstream.get("clobber"),
            }

        memory = helper.parse_memory(source_operand)
        if memory is not None:
            base, displacement = memory
            if "LOAD" not in opcodes:
                return {"evidence_state": "ambiguous", "status": "memory-source-without-load-pcode", "source": None, "chain": [step]}
            return {
                "evidence_state": "verified",
                "status": "register-relative-load-source",
                "source": {
                    "kind": "register-relative-load",
                    "instruction": address,
                    "base_register": base,
                    "displacement": displacement,
                    "displacement_hex": helper.hex_offset(displacement),
                    "object_identity_proven": False,
                },
                "chain": [step],
            }
        return {
            "evidence_state": "ambiguous",
            "status": "unsupported-definition-source",
            "source": {"kind": "unknown", "operand": source_operand},
            "chain": [step],
        }

    return helper.entry_terminal(register, calling_convention)


def _frontier_identity(frontier_row: dict[str, Any]) -> tuple[int, str]:
    descriptor = frontier_row.get("descriptor")
    table = frontier_row.get("stored_table_address")
    if not isinstance(descriptor, int) or table is None:
        raise ValueError("verified lifetime frontier row lacks descriptor/table identity")
    return descriptor, _normalize_address(table)


def _matching_pair(pair_index: dict[tuple[int, str], list[dict[str, Any]]], identity: tuple[int, str]) -> dict[str, Any]:
    matches = pair_index.get(identity, [])
    if len(matches) != 1:
        raise ValueError(
            f"verified lifetime frontier identity {identity} must map to exactly one class lifetime pair; found {len(matches)}"
        )
    return matches[0]


def _validate_frontier_sets(frontier_row: dict[str, Any], pair_row: dict[str, Any]) -> None:
    checks = (
        ("factory_functions", "factory_functions"),
        ("initializer_candidates", "initializer_candidates"),
        ("deleting_wrapper_functions", "deleting_wrapper_functions"),
        ("teardown_transition_functions", "teardown_transition_functions"),
    )
    for frontier_key, pair_key in checks:
        left = _function_list(frontier_row.get(frontier_key), f"frontier.{frontier_key}")
        right = _function_list(pair_row.get(pair_key), f"pair.{pair_key}")
        if left != right:
            raise ValueError(f"lifetime frontier/pair drift for {frontier_key}: {left} != {right}")


def _create_transfers(helper, rows: dict[str, dict[str, Any]], pair_row: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for shape in pair_row.get("create_shapes") or []:
        if not isinstance(shape, dict) or shape.get("create_wrapper_shape") is not True:
            continue
        factory = _optional_address(shape.get("factory_function"))
        initializer = _optional_address(shape.get("initializer_candidate"))
        prehelper = _optional_address(shape.get("immediate_preinitializer_helper"))
        if not factory or not initializer or not prehelper:
            continue
        if factory not in rows or initializer not in rows:
            raise ValueError(f"instruction export missing create lifetime target(s): {factory}, {initializer}")
        factory_row = rows[factory]
        helper_call = _single_direct_call(helper, factory_row, prehelper)
        initializer_call = _single_direct_call(helper, factory_row, initializer)
        child_cc = _calling_convention(rows, initializer)
        abi_state = "inferred" if child_cc == "__thiscall" else "unknown"
        trace = None
        machine_state = "unknown"
        helper_result_match = False
        if initializer_call["index"] is not None and child_cc == "__thiscall":
            trace = _trace_receiver(
                helper,
                factory_row,
                initializer_call["index"],
                expected_result_call=prehelper,
            )
            source = trace.get("source") if isinstance(trace, dict) else None
            helper_result_match = (
                isinstance(source, dict)
                and source.get("kind") == "direct-call-result-register"
                and source.get("callee") == prehelper
                and helper_call["evidence_state"] == "verified"
            )
            machine_state = "verified" if helper_result_match else _state(trace.get("evidence_state", "unknown"), "create trace")
            if machine_state == "verified" and not helper_result_match:
                machine_state = "ambiguous"
        combined = _weakest(
            helper_call["evidence_state"],
            initializer_call["evidence_state"],
            machine_state,
            abi_state,
        )
        result.append(
            {
                "factory_function": factory,
                "initializer_function": initializer,
                "preinitializer_helper": prehelper,
                "source_helper_result_flows_to_initializer": shape.get("helper_result_flows_to_initializer"),
                "source_shape_ghidra_factory_to_helper": shape.get("ghidra_factory_to_helper"),
                "source_shape_ghidra_factory_to_initializer": shape.get("ghidra_factory_to_initializer"),
                "helper_call": helper_call,
                "initializer_call": initializer_call,
                "initializer_calling_convention": child_cc,
                "initializer_receiver_register_candidate": RECEIVER_REGISTER if child_cc == "__thiscall" else None,
                "initializer_receiver_abi_state": abi_state,
                "receiver_source_trace": trace,
                "exact_helper_result_reaches_initializer_receiver_candidate": helper_result_match,
                "machine_value_transfer_state": machine_state,
                "lifetime_transfer_evidence_state": combined,
                "pointer_semantics_proven": False,
                "allocation_semantics_proven": False,
                "constructor_semantics_proven": False,
            }
        )
    return result


def _delete_transfers(helper, rows: dict[str, dict[str, Any]], pair_row: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for shape in pair_row.get("delete_shapes") or []:
        if not isinstance(shape, dict) or shape.get("deleting_wrapper_shape") is not True:
            continue
        wrapper = _optional_address(shape.get("wrapper_function"))
        teardown = _optional_address(shape.get("teardown_transition_function"))
        release = _optional_address(shape.get("release_helper"))
        if not wrapper or not teardown:
            continue
        if wrapper not in rows or teardown not in rows:
            raise ValueError(f"instruction export missing delete lifetime target(s): {wrapper}, {teardown}")
        wrapper_row = rows[wrapper]
        teardown_call = _single_direct_call(helper, wrapper_row, teardown)
        wrapper_cc = _calling_convention(rows, wrapper)
        child_cc = _calling_convention(rows, teardown)
        abi_state = "inferred" if wrapper_cc == "__thiscall" and child_cc == "__thiscall" else "unknown"
        trace = None
        entry_receiver_match = False
        machine_state = "unknown"
        if teardown_call["index"] is not None and child_cc == "__thiscall":
            trace = _trace_receiver(helper, wrapper_row, teardown_call["index"])
            source = trace.get("source") if isinstance(trace, dict) else None
            entry_receiver_match = (
                isinstance(source, dict)
                and source.get("kind") == "function-entry-register"
                and source.get("register") == RECEIVER_REGISTER
                and wrapper_cc == "__thiscall"
            )
            machine_state = "verified" if entry_receiver_match else _state(trace.get("evidence_state", "unknown"), "delete trace")
            if machine_state == "verified" and not entry_receiver_match:
                machine_state = "ambiguous"
        combined = _weakest(teardown_call["evidence_state"], machine_state, abi_state)
        result.append(
            {
                "deleting_wrapper_function": wrapper,
                "teardown_transition_function": teardown,
                "release_helper": release,
                "source_shape_ghidra_teardown_edge": shape.get("ghidra_teardown_edge"),
                "source_shape_ghidra_release_edge": shape.get("ghidra_release_edge"),
                "wrapper_calling_convention": wrapper_cc,
                "teardown_calling_convention": child_cc,
                "teardown_call": teardown_call,
                "teardown_receiver_register_candidate": RECEIVER_REGISTER if child_cc == "__thiscall" else None,
                "teardown_receiver_abi_state": abi_state,
                "receiver_source_trace": trace,
                "exact_wrapper_entry_receiver_reaches_teardown_receiver_candidate": entry_receiver_match,
                "machine_value_transfer_state": machine_state,
                "lifetime_transfer_evidence_state": combined,
                "release_pointer_transfer_proven": False,
                "pointer_semantics_proven": False,
                "destructor_semantics_proven": False,
            }
        )
    return result


def analyze_vehicle_lifetime_pointer_transfer(
    lifetime_frontier_path: Path,
    lifetime_pair_path: Path,
    instruction_export: Path,
) -> dict[str, Any]:
    helper = _load_pointer_helper()
    frontier = _load_json(lifetime_frontier_path, FRONTIER_FORMAT)
    pair = _load_json(lifetime_pair_path, PAIR_FORMAT)
    rows = helper.load_instructions(instruction_export)
    pair_index = _pair_index(pair)

    candidates = []
    blockers = []
    next_targets: dict[str, set[str]] = {}
    for frontier_row in _frontier_rows(frontier):
        identity = _frontier_identity(frontier_row)
        pair_row = _matching_pair(pair_index, identity)
        _validate_frontier_sets(frontier_row, pair_row)

        create = _create_transfers(helper, rows, pair_row)
        delete = _delete_transfers(helper, rows, pair_row)
        create_verified = [row for row in create if row["machine_value_transfer_state"] == "verified"]
        delete_verified = [row for row in delete if row["machine_value_transfer_state"] == "verified"]
        create_semantic = [row for row in create if row["lifetime_transfer_evidence_state"] in {"verified", "inferred"}]
        delete_semantic = [row for row in delete if row["lifetime_transfer_evidence_state"] in {"verified", "inferred"}]

        prehelpers = _function_list(pair_row.get("preinitializer_helpers"), "preinitializer_helpers")
        release_helpers = _function_list(pair_row.get("release_helpers"), "release_helpers")
        for address in prehelpers:
            next_targets.setdefault(address, set()).add(
                f"preinitializer helper for descriptor {identity[0]} / table {identity[1]}; allocation semantics unresolved"
            )
        for address in release_helpers:
            next_targets.setdefault(address, set()).add(
                f"release helper for descriptor {identity[0]} / table {identity[1]}; release pointer transfer unresolved"
            )

        create_state = "verified" if create_verified else (
            _weakest(*(row["machine_value_transfer_state"] for row in create)) if create else "unknown"
        )
        delete_state = "verified" if delete_verified else (
            _weakest(*(row["machine_value_transfer_state"] for row in delete)) if delete else "unknown"
        )
        candidate_state = _weakest(
            _state(frontier_row.get("frontier_evidence_state", "unknown"), "frontier"),
            create_state,
            delete_state,
        )
        row = {
            "descriptor": identity[0],
            "own_vtable": identity[1],
            "class_name": frontier_row.get("lifetime_pair_class_name"),
            "vehicle_pointer_function": frontier_row.get("vehicle_pointer_function"),
            "vehicle_pointer_source_node": frontier_row.get("vehicle_pointer_source_node"),
            "upstream_frontier_evidence_state": frontier_row.get("frontier_evidence_state"),
            "create_transfers": create,
            "delete_transfers": delete,
            "verified_create_machine_transfer_count": len(create_verified),
            "verified_delete_machine_transfer_count": len(delete_verified),
            "create_receiver_candidate_transfer_available": bool(create_semantic),
            "delete_receiver_candidate_transfer_available": bool(delete_semantic),
            "candidate_evidence_state": candidate_state,
            "same_runtime_object_across_create_update_delete_proven": False,
            "allocator_semantics_proven": False,
            "constructor_semantics_proven": False,
            "destructor_semantics_proven": False,
            "release_semantics_proven": False,
            "owner_identity_proven": False,
        }
        candidates.append(row)
        if not create_verified:
            blockers.append({
                "id": "create-receiver-candidate-machine-transfer-not-closed",
                "descriptor": identity[0],
                "own_vtable": identity[1],
                "evidence_state": create_state,
            })
        if not delete_verified:
            blockers.append({
                "id": "delete-receiver-candidate-machine-transfer-not-closed",
                "descriptor": identity[0],
                "own_vtable": identity[1],
                "evidence_state": delete_state,
            })
        blockers.append({
            "id": "same-runtime-object-lifetime-continuity",
            "descriptor": identity[0],
            "own_vtable": identity[1],
            "evidence_state": "unknown",
            "required_evidence": "connect create-side returned/stored pointer identity to the already-proven vehicle update pointer node and connect teardown to release helper pointer identity",
        })

    target_rows = [
        {"address": address, "reasons": sorted(reasons), "promoted": False}
        for address, reasons in sorted(next_targets.items())
    ]
    return {
        "format": FORMAT,
        "vehicle_lifetime_pair_frontier": str(lifetime_frontier_path),
        "class_lifetime_pair_evidence": str(lifetime_pair_path),
        "instruction_export": str(instruction_export),
        "candidate_count": len(candidates),
        "verified_create_machine_transfer_count": sum(row["verified_create_machine_transfer_count"] for row in candidates),
        "verified_delete_machine_transfer_count": sum(row["verified_delete_machine_transfer_count"] for row in candidates),
        "candidates": candidates,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "next_instruction_export_targets": target_rows,
        "next_instruction_export_addresses": [row["address"] for row in target_rows],
        "scope": {
            "exact_direct_call_flow_and_pcode_required": True,
            "x86_thiscall_ecx_role_treated_as_inferred_abi_evidence": True,
            "x86_pointer_return_eax_role_treated_as_machine_register_fact_not_pointer_semantics": True,
            "create_helper_result_to_initializer_receiver_candidate_can_be_machine_verified": True,
            "wrapper_entry_receiver_to_teardown_receiver_candidate_can_be_machine_verified": True,
            "machine_value_transfer_is_constructor_proof": False,
            "machine_value_transfer_is_destructor_proof": False,
            "create_delete_transfer_is_same_runtime_object_proof": False,
            "allocator_semantics_proven": False,
            "release_semantics_proven": False,
            "owner_identity_proven": False,
            "automatic_function_renaming_performed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vehicle_lifetime_pair_frontier", type=Path)
    parser.add_argument("class_lifetime_pair_evidence", type=Path)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--targets-out", type=Path)
    parser.add_argument("--require-create-delete-machine-transfer", action="store_true")
    args = parser.parse_args()
    report = analyze_vehicle_lifetime_pointer_transfer(
        args.vehicle_lifetime_pair_frontier,
        args.class_lifetime_pair_evidence,
        args.instruction_export,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    if args.targets_out:
        args.targets_out.parent.mkdir(parents=True, exist_ok=True)
        args.targets_out.write_text(
            "".join(address + "\n" for address in report["next_instruction_export_addresses"]),
            encoding="utf-8",
        )
    print(f"format: {report['format']}")
    print(f"candidates: {report['candidate_count']}")
    print(f"verified create machine transfers: {report['verified_create_machine_transfer_count']}")
    print(f"verified delete machine transfers: {report['verified_delete_machine_transfer_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    if args.targets_out:
        print(f"targets: {args.targets_out}")
    if args.require_create_delete_machine_transfer:
        if report["verified_create_machine_transfer_count"] == 0 or report["verified_delete_machine_transfer_count"] == 0:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
