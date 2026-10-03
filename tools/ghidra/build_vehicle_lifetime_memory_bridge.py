#!/usr/bin/env python3
"""Join vehicle lifetime callsite evidence to proven retail memory-helper roles.

This composition stage does not re-prove memory helper semantics. It requires the
canonical SHIFT-MEMORY-WRAPPER-RUNTIME-MANIFEST/1 and joins its exact helper
identity/parameter roles to a verified vehicle lifetime frontier and machine
callsite transfer report.

The strongest create-side result is an evidence-backed allocation-request
argument value adjacent to the initializer path. It is not promoted to object
size. The strongest delete-side result is the exact source-argument index and
entry storage whose semantic role is released-pointer; caller-to-helper argument
transport remains a separate proof gate.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.VehicleLifetimeMemoryBridge/1"
FRONTIER_FORMAT = "SHIFT.VehicleLifetimePairFrontier/1"
CALLSITE_FORMAT = "SHIFT.VehicleLifetimeCallsiteTransfer/1"
CREATE_FORMAT = "SHIFT-CLASS-CREATE-WRAPPER-EVIDENCE/1"
MEMORY_FORMAT = "SHIFT-MEMORY-WRAPPER-RUNTIME-MANIFEST/1"

STATES = {"proven", "verified", "inferred", "ambiguous", "unknown"}
STATE_STRENGTH = {"unknown": 0, "ambiguous": 1, "inferred": 2, "verified": 3, "proven": 4}
_INTEGER = re.compile(r"^\s*(0x[0-9A-Fa-f]+|[0-9]+)(?:[uUlL]+)?\s*$")


def _load(path: Path, expected: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}")
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
        raise ValueError(f"invalid address value {value!r}")
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


def _address_set(values: Any, label: str) -> set[str]:
    if not isinstance(values, list):
        raise ValueError(f"{label}: expected list")
    result: set[str] = set()
    for value in values:
        address = _optional_address(value)
        if address is None:
            raise ValueError(f"{label}: invalid address {value!r}")
        result.add(address)
    return result


def _frontier_by_descriptor(report: dict[str, Any]) -> dict[int, list[dict[str, Any]]]:
    rows = report.get("candidates")
    if not isinstance(rows, list):
        raise ValueError("lifetime frontier: candidates must be a list")
    result: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("descriptor"), int):
            raise ValueError("lifetime frontier: invalid candidate row")
        if row.get("verified_vehicle_lifetime_pair_frontier") is True:
            result[row["descriptor"]].append(row)
    if not result:
        raise ValueError("lifetime frontier contains no verified candidate")
    return result


def _matching_frontier(
    by_descriptor: dict[int, list[dict[str, Any]]],
    descriptor: int,
    *,
    create: tuple[str, str] | None = None,
    delete: tuple[str, str] | None = None,
) -> dict[str, Any]:
    matches = []
    for row in by_descriptor.get(descriptor, []):
        if create is not None:
            factory, initializer = create
            if factory not in _address_set(row.get("factory_functions"), "factory_functions"):
                continue
            if initializer not in _address_set(row.get("initializer_candidates"), "initializer_candidates"):
                continue
        if delete is not None:
            wrapper, teardown = delete
            if wrapper not in _address_set(row.get("deleting_wrapper_functions"), "deleting_wrapper_functions"):
                continue
            if teardown not in _address_set(row.get("teardown_transition_functions"), "teardown_transition_functions"):
                continue
        matches.append(row)
    if len(matches) != 1:
        raise ValueError(
            f"descriptor {descriptor}: callsite transfer must map to exactly one verified lifetime frontier; found {len(matches)}"
        )
    return matches[0]


def _manifest_helpers(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = report.get("wrappers")
    if not isinstance(rows, list):
        raise ValueError("memory runtime manifest: wrappers must be a list")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("memory runtime manifest: invalid wrapper row")
        address = _optional_address(row.get("address"))
        if address is None:
            continue
        if address in result:
            raise ValueError(f"memory runtime manifest: duplicate helper {address}")
        result[address] = row
    return result


def _semantic_parameter(helper: dict[str, Any], role: str) -> dict[str, Any] | None:
    rows = helper.get("parameters")
    if not isinstance(rows, list):
        raise ValueError(f"memory helper {helper.get('name')}: parameters must be a list")
    matches = [
        row for row in rows
        if isinstance(row, dict)
        and row.get("semantic_role") == role
        and row.get("semantic_role_proven") is True
    ]
    if len(matches) > 1:
        raise ValueError(f"memory helper {helper.get('name')}: duplicate proven role {role}")
    return matches[0] if matches else None


def _split_top_level_arguments(text: str | None) -> list[str] | None:
    if not isinstance(text, str):
        return None
    text = text.strip()
    if not text:
        return []
    result: list[str] = []
    start = 0
    paren = bracket = brace = 0
    quote: str | None = None
    escaped = False
    for index, ch in enumerate(text):
        if quote is not None:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
            continue
        if ch in {"'", '"'}:
            quote = ch
            continue
        if ch == "(":
            paren += 1
        elif ch == ")":
            paren -= 1
        elif ch == "[":
            bracket += 1
        elif ch == "]":
            bracket -= 1
        elif ch == "{":
            brace += 1
        elif ch == "}":
            brace -= 1
        elif ch == "," and paren == bracket == brace == 0:
            result.append(text[start:index].strip())
            start = index + 1
        if min(paren, bracket, brace) < 0:
            return None
    if quote is not None or paren or bracket or brace:
        return None
    result.append(text[start:].strip())
    return result


def _exact_integer(expression: str | None) -> int | None:
    if not isinstance(expression, str):
        return None
    match = _INTEGER.fullmatch(expression)
    if match is None:
        return None
    try:
        return int(match.group(1), 0)
    except ValueError:
        return None


def _create_evidence_index(report: dict[str, Any]) -> dict[tuple[int, str, str, str], list[dict[str, Any]]]:
    rows = report.get("links")
    if not isinstance(rows, list):
        raise ValueError("create-wrapper evidence: links must be a list")
    result: dict[tuple[int, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if not isinstance(row, dict) or row.get("create_wrapper_shape") is not True:
            continue
        descriptor = row.get("descriptor")
        factory = _optional_address(row.get("factory_function"))
        initializer = _optional_address(row.get("initializer_candidate"))
        helper = _optional_address(row.get("immediate_preinitializer_helper"))
        if isinstance(descriptor, int) and factory and initializer and helper:
            result[(descriptor, factory, helper, initializer)].append(row)
    return result


def _unique_create_source(
    index: dict[tuple[int, str, str, str], list[dict[str, Any]]],
    descriptor: int,
    factory: str,
    helper: str,
    initializer: str,
) -> dict[str, Any]:
    rows = index.get((descriptor, factory, helper, initializer), [])
    if len(rows) != 1:
        raise ValueError(
            f"descriptor {descriptor}: create callsite must map to exactly one create-wrapper source row; found {len(rows)}"
        )
    return rows[0]


def build_vehicle_lifetime_memory_bridge(
    lifetime_frontier_path: Path,
    lifetime_callsite_transfer_path: Path,
    create_wrapper_evidence_path: Path,
    memory_runtime_manifest_path: Path,
) -> dict[str, Any]:
    frontier = _load(lifetime_frontier_path, FRONTIER_FORMAT)
    callsite = _load(lifetime_callsite_transfer_path, CALLSITE_FORMAT)
    create = _load(create_wrapper_evidence_path, CREATE_FORMAT)
    memory = _load(memory_runtime_manifest_path, MEMORY_FORMAT)

    frontier_index = _frontier_by_descriptor(frontier)
    helpers = _manifest_helpers(memory)
    create_index = _create_evidence_index(create)
    memory_contract_ready = memory.get("runtime_contract_status") == "source-joined-semantic-roles"

    create_rows: list[dict[str, Any]] = []
    delete_rows: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    next_targets: dict[str, set[str]] = defaultdict(set)

    raw_create = callsite.get("create_transfers")
    if not isinstance(raw_create, list):
        raise ValueError("lifetime callsite transfer: create_transfers must be a list")
    for transfer in raw_create:
        if not isinstance(transfer, dict) or not isinstance(transfer.get("descriptor"), int):
            raise ValueError("lifetime callsite transfer: invalid create row")
        descriptor = transfer["descriptor"]
        factory = _normalize_address(transfer.get("factory_function"))
        helper = _normalize_address(transfer.get("preinitializer_helper"))
        initializer = _normalize_address(transfer.get("initializer_candidate"))
        frontier_row = _matching_frontier(
            frontier_index, descriptor, create=(factory, initializer)
        )
        source_row = _unique_create_source(
            create_index, descriptor, factory, helper, initializer
        )

        helper_row = helpers.get(helper)
        allocation_param = (
            _semantic_parameter(helper_row, "allocation-size")
            if helper_row is not None
            else None
        )
        role_state = "verified" if (
            memory_contract_ready
            and helper_row is not None
            and helper_row.get("forwarding_confirmed") is True
            and allocation_param is not None
        ) else "unknown"

        argument_index = (
            allocation_param.get("source_argument_index")
            if allocation_param is not None
            else None
        )
        arguments = _split_top_level_arguments(source_row.get("helper_arguments"))
        expression = None
        literal = None
        literal_state = "unknown"
        if isinstance(argument_index, int) and not isinstance(argument_index, bool):
            if arguments is not None and 0 <= argument_index < len(arguments):
                expression = arguments[argument_index]
                literal = _exact_integer(expression)
                literal_state = "verified" if literal is not None else "unknown"

        machine_state = _state(
            transfer.get("machine_receiver_value_path_state", "unknown"),
            "create machine receiver path",
        )
        create_state = _state(
            transfer.get("create_value_transfer_state", "unknown"),
            "create value transfer",
        )
        request_state = _weakest(role_state, literal_state, machine_state, create_state)
        row = {
            "descriptor": descriptor,
            "class_name": frontier_row.get("lifetime_pair_class_name"),
            "vehicle_pointer_function": frontier_row.get("vehicle_pointer_function"),
            "vehicle_pointer_source_node": frontier_row.get("vehicle_pointer_source_node"),
            "stored_table_address": frontier_row.get("stored_table_address"),
            "factory_function": factory,
            "preinitializer_helper": helper,
            "initializer_candidate": initializer,
            "memory_helper_manifest_present": helper_row is not None,
            "memory_helper_forwarding_confirmed": (
                helper_row.get("forwarding_confirmed") if helper_row else None
            ),
            "allocation_size_parameter": allocation_param,
            "allocation_size_role_state": role_state,
            "allocation_size_argument_expression": expression,
            "allocation_size_argument_literal_value": literal,
            "allocation_size_argument_literal_state": literal_state,
            "machine_helper_result_to_initializer_receiver_state": machine_state,
            "create_value_transfer_state": create_state,
            "initializer_backing_allocation_request_state": request_state,
            "initializer_backing_allocation_request_value": literal if request_state != "unknown" else None,
            "allocation_value_unit_proven": False,
            "helper_return_is_allocated_pointer_proven": False,
            "object_size_proven": False,
            "constructor_semantics_proven": False,
            "same_runtime_object_as_vehicle_update_proven": False,
        }
        create_rows.append(row)
        next_targets[helper].add(
            f"descriptor {descriptor}: prove helper return-value semantics; allocation-size parameter role is already joined"
        )
        if role_state != "verified":
            blockers.append({
                "id": "create-helper-allocation-size-role-not-joined",
                "descriptor": descriptor,
                "helper": helper,
                "evidence_state": role_state,
            })
        if literal_state != "verified":
            blockers.append({
                "id": "allocation-size-source-argument-not-exact-integer-literal",
                "descriptor": descriptor,
                "helper": helper,
                "source_argument_index": argument_index,
                "expression": expression,
                "evidence_state": literal_state,
            })
        blockers.append({
            "id": "helper-return-allocation-pointer-semantics-open",
            "descriptor": descriptor,
            "helper": helper,
            "evidence_state": "unknown",
        })

    raw_delete = callsite.get("delete_transfers")
    if not isinstance(raw_delete, list):
        raise ValueError("lifetime callsite transfer: delete_transfers must be a list")
    for transfer in raw_delete:
        if not isinstance(transfer, dict) or not isinstance(transfer.get("descriptor"), int):
            raise ValueError("lifetime callsite transfer: invalid delete row")
        descriptor = transfer["descriptor"]
        wrapper = _normalize_address(transfer.get("deleting_wrapper_function"))
        teardown = _normalize_address(transfer.get("teardown_transition_function"))
        release = _normalize_address(transfer.get("release_helper"))
        frontier_row = _matching_frontier(
            frontier_index, descriptor, delete=(wrapper, teardown)
        )

        helper_row = helpers.get(release)
        released_param = (
            _semantic_parameter(helper_row, "released-pointer")
            if helper_row is not None
            else None
        )
        role_state = "verified" if (
            memory_contract_ready
            and helper_row is not None
            and helper_row.get("forwarding_confirmed") is True
            and released_param is not None
        ) else "unknown"
        entry_storage = released_param.get("entry_storage") if released_param else None
        storage_state = "verified" if role_state == "verified" and isinstance(entry_storage, str) and entry_storage else "unknown"
        upstream_transport = _state(
            transfer.get("release_argument_value_transfer_state", "unknown"),
            "release argument transfer",
        )

        row = {
            "descriptor": descriptor,
            "class_name": frontier_row.get("lifetime_pair_class_name"),
            "vehicle_pointer_function": frontier_row.get("vehicle_pointer_function"),
            "vehicle_pointer_source_node": frontier_row.get("vehicle_pointer_source_node"),
            "stored_table_address": frontier_row.get("stored_table_address"),
            "deleting_wrapper_function": wrapper,
            "teardown_transition_function": teardown,
            "release_helper": release,
            "memory_helper_manifest_present": helper_row is not None,
            "memory_helper_forwarding_confirmed": (
                helper_row.get("forwarding_confirmed") if helper_row else None
            ),
            "released_pointer_parameter": released_param,
            "released_pointer_parameter_role_state": role_state,
            "released_pointer_entry_storage": entry_storage,
            "released_pointer_entry_storage_state": storage_state,
            "upstream_release_argument_value_transfer_state": upstream_transport,
            "release_argument_transport_state": upstream_transport,
            "release_argument_value_transfer_proven": upstream_transport in {"verified", "proven"},
            "release_semantics_proven": role_state == "verified",
            "destructor_semantics_proven": False,
            "same_runtime_object_as_vehicle_update_proven": False,
        }
        delete_rows.append(row)
        next_targets[wrapper].add(
            f"descriptor {descriptor}: trace caller value into release helper parameter index {released_param.get('source_argument_index') if released_param else 'unknown'} / storage {entry_storage or 'unknown'}"
        )
        if role_state != "verified":
            blockers.append({
                "id": "release-helper-released-pointer-role-not-joined",
                "descriptor": descriptor,
                "helper": release,
                "evidence_state": role_state,
            })
        if upstream_transport not in {"verified", "proven"}:
            blockers.append({
                "id": "release-pointer-call-argument-transport-open",
                "descriptor": descriptor,
                "wrapper": wrapper,
                "release_helper": release,
                "source_argument_index": (
                    released_param.get("source_argument_index") if released_param else None
                ),
                "entry_storage": entry_storage,
                "evidence_state": upstream_transport,
            })

    if not create_rows and not delete_rows:
        raise ValueError("lifetime callsite transfer contains no create/delete rows")

    descriptors = sorted({row["descriptor"] for row in create_rows + delete_rows})
    for descriptor in descriptors:
        blockers.append({
            "id": "same-runtime-object-create-update-delete-continuity-open",
            "descriptor": descriptor,
            "evidence_state": "unknown",
        })

    create_rows.sort(key=lambda row: (row["descriptor"], row["factory_function"]))
    delete_rows.sort(key=lambda row: (row["descriptor"], row["deleting_wrapper_function"]))
    target_rows = [
        {"address": address, "reasons": sorted(reasons), "promoted": False}
        for address, reasons in sorted(next_targets.items())
    ]
    return {
        "format": FORMAT,
        "vehicle_lifetime_pair_frontier": str(lifetime_frontier_path),
        "vehicle_lifetime_callsite_transfer": str(lifetime_callsite_transfer_path),
        "create_wrapper_evidence": str(create_wrapper_evidence_path),
        "memory_runtime_manifest": str(memory_runtime_manifest_path),
        "memory_runtime_contract_status": memory.get("runtime_contract_status"),
        "create_bridge_count": len(create_rows),
        "delete_bridge_count": len(delete_rows),
        "create_bridges": create_rows,
        "delete_bridges": delete_rows,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "next_instruction_export_targets": target_rows,
        "next_instruction_export_addresses": [row["address"] for row in target_rows],
        "scope": {
            "memory_helper_semantics_reproven_here": False,
            "exact_memory_helper_identity_required": True,
            "allocation_size_parameter_role_can_be_joined": True,
            "exact_source_integer_argument_can_be_recorded": True,
            "allocation_request_value_is_object_size_proof": False,
            "helper_return_is_allocated_pointer_proven": False,
            "released_pointer_parameter_role_can_be_joined": True,
            "released_pointer_entry_storage_can_be_joined": True,
            "released_pointer_role_is_caller_argument_transport_proof": False,
            "same_runtime_object_across_lifetime_proven": False,
            "same_runtime_object_as_vehicle_update_proven": False,
            "constructor_semantics_proven": False,
            "destructor_semantics_proven": False,
            "owner_identity_proven": False,
            "next_step": (
                "Trace the exact deleting-wrapper value into the proven released-pointer entry storage, "
                "and inspect the create helper return path before attempting whole-lifetime object identity."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vehicle_lifetime_pair_frontier", type=Path)
    parser.add_argument("vehicle_lifetime_callsite_transfer", type=Path)
    parser.add_argument("create_wrapper_evidence", type=Path)
    parser.add_argument("memory_runtime_manifest", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--targets-out", type=Path)
    args = parser.parse_args()

    report = build_vehicle_lifetime_memory_bridge(
        args.vehicle_lifetime_pair_frontier,
        args.vehicle_lifetime_callsite_transfer,
        args.create_wrapper_evidence,
        args.memory_runtime_manifest,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    if args.targets_out:
        args.targets_out.parent.mkdir(parents=True, exist_ok=True)
        args.targets_out.write_text(
            "".join(row["address"] + "\n" for row in report["next_instruction_export_targets"]),
            encoding="utf-8",
        )
    print(f"format: {report['format']}")
    print(f"create bridges: {report['create_bridge_count']}")
    print(f"delete bridges: {report['delete_bridge_count']}")
    print(f"blockers: {report['blocker_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    if args.targets_out:
        print(f"targets: {args.targets_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
