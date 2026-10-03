#!/usr/bin/env python3
"""Join verified local table-pointer alias evidence to class lifecycle evidence.

This stage intentionally reuses SHIFT.VehicleVtablePointerAlias/1 instead of
re-implementing register continuity.  A lifecycle join is admitted only when an
exact literal candidate-table STORE has verified same-pointer continuity to the
receiver source, that exact receiver-source node already exists in
SHIFT.VehiclePointerValueClosure/1, and the stored address maps uniquely to one
PE-backed class lifecycle row.

The result still does not promote C++ vptr, constructor/destructor, whole-life
class identity, ownership, input, or scheduler semantics.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.VehicleLifecyclePointerJoin/1"
POINTER_FORMAT = "SHIFT.VehiclePointerValueClosure/1"
ALIAS_FORMAT = "SHIFT.VehicleVtablePointerAlias/1"
LIFECYCLE_FORMAT = "SHIFT-CLASS-LIFECYCLE-SOURCE-EVIDENCE/1"

STATES = {"proven", "verified", "inferred", "ambiguous", "unknown"}
STATE_STRENGTH = {"unknown": 0, "ambiguous": 1, "inferred": 2, "verified": 3, "proven": 4}


def _load(path: Path, expected: str) -> dict[str, Any]:
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
    if not values:
        return "unknown"
    checked = [_state(value, "state merge") for value in values]
    return min(checked, key=lambda value: STATE_STRENGTH[value])


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
        raise ValueError(f"address out of 32-bit range: {value!r}")
    return f"0x{number:08x}"


def _function_address(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    token = value.strip()
    try:
        if token.upper().startswith("FUN_") or token.lower().startswith("0x"):
            return _normalize_address(token)
    except ValueError:
        return None
    return None


def _closure_nodes(pointer: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = pointer.get("nodes")
    if not isinstance(rows, list):
        raise ValueError("pointer closure: nodes must be a list")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            raise ValueError("pointer closure: invalid node")
        node_id = row["id"]
        if node_id in result:
            raise ValueError(f"pointer closure: duplicate node {node_id}")
        result[node_id] = row
    return result


def _lifecycle_index(lifecycle: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    rows = lifecycle.get("targets")
    if not isinstance(rows, list):
        raise ValueError("class lifecycle evidence: targets must be a list")
    result: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("class lifecycle evidence: invalid target row")
        if row.get("own_vtable") is None:
            continue
        address = _normalize_address(row["own_vtable"])
        result.setdefault(address, []).append(row)
    return result


def _receiver_source_node(candidate: dict[str, Any]) -> str:
    function = candidate.get("function")
    instruction = candidate.get("receiver_source_instruction")
    base = candidate.get("receiver_source_base_register")
    displacement = candidate.get("receiver_source_displacement")
    if not isinstance(function, str):
        raise ValueError("alias candidate function missing")
    if not isinstance(instruction, str) or not isinstance(base, str) or not isinstance(displacement, int):
        raise ValueError(f"{function}: receiver source identity incomplete")
    function = _normalize_address(function)
    instruction = _normalize_address(instruction)
    return f"memory-source:{function}:{instruction}:{base.upper()}:{displacement}"


def _role(class_row: dict[str, Any], function: str) -> dict[str, Any]:
    initializer = _function_address(class_row.get("initializer_candidate"))
    if initializer == function and class_row.get("initializer_writes_own_vtable") is True:
        return {
            "role": "initializer-candidate",
            "evidence_state": "verified",
            "constructor_semantics_proven": False,
        }
    teardown = [
        row
        for row in class_row.get("teardown_transition_candidates") or []
        if isinstance(row, dict) and _function_address(row.get("function")) == function
    ]
    if teardown:
        return {
            "role": "teardown-transition-candidate",
            "evidence_state": "ambiguous",
            "candidate_count": len(teardown),
            "destructor_semantics_proven": False,
        }
    writers = {
        address
        for address in (_function_address(value) for value in class_row.get("own_vtable_writer_functions") or [])
        if address is not None
    }
    if function in writers:
        return {
            "role": "own-vtable-writer",
            "evidence_state": "verified",
            "lifecycle_semantics_proven": False,
        }
    return {
        "role": "unclassified-table-store-function",
        "evidence_state": "unknown",
        "lifecycle_semantics_proven": False,
    }


def _lifecycle_neighbors(class_row: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    initializer = _function_address(class_row.get("initializer_candidate"))
    if initializer:
        result.add(initializer)
    for row in class_row.get("initializer_callers") or []:
        if isinstance(row, dict):
            address = _function_address(row.get("function"))
            if address:
                result.add(address)
    for row in class_row.get("teardown_transition_candidates") or []:
        if isinstance(row, dict):
            address = _function_address(row.get("function"))
            if address:
                result.add(address)
    return result


def build_vehicle_lifecycle_pointer_join(
    pointer_closure_path: Path,
    vtable_pointer_alias_path: Path,
    class_lifecycle_path: Path,
) -> dict[str, Any]:
    pointer = _load(pointer_closure_path, POINTER_FORMAT)
    alias = _load(vtable_pointer_alias_path, ALIAS_FORMAT)
    lifecycle = _load(class_lifecycle_path, LIFECYCLE_FORMAT)

    nodes = _closure_nodes(pointer)
    classes_by_vtable = _lifecycle_index(lifecycle)
    alias_rows = alias.get("candidates")
    if not isinstance(alias_rows, list):
        raise ValueError("vtable pointer alias: candidates must be a list")

    candidates: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    next_targets: dict[str, set[str]] = {}

    for alias_row in alias_rows:
        if not isinstance(alias_row, dict):
            raise ValueError("vtable pointer alias: invalid candidate")
        function = alias_row.get("function")
        store_instruction = alias_row.get("vtable_store_instruction")
        if not isinstance(function, str) or not isinstance(store_instruction, str):
            raise ValueError("vtable pointer alias: candidate identity missing")
        function = _normalize_address(function)
        store_instruction = _normalize_address(store_instruction)

        store_shape = alias_row.get("store_shape")
        if not isinstance(store_shape, dict):
            raise ValueError(f"{function}: store_shape missing")
        stored_address = store_shape.get("stored_address")
        stored_matches = store_shape.get("stored_address_matches_reference")
        store_state = _state(store_shape.get("evidence_state", "unknown"), "table store shape")
        if stored_address is not None:
            stored_address = _normalize_address(stored_address)

        same_pointer_state = _state(
            alias_row.get("same_pointer_table_store_state", "unknown"),
            "same-pointer table store",
        )
        if same_pointer_state == "verified":
            if store_state != "verified" or stored_matches is not True or stored_address is None:
                raise ValueError(
                    f"{function}@{store_instruction}: verified alias lacks verified exact literal table STORE"
                )
            if alias_row.get("destination_base_matches_receiver_source_base") is not True:
                raise ValueError(
                    f"{function}@{store_instruction}: verified alias lacks base-register match"
                )

        source_node = _receiver_source_node(alias_row)
        source_node_present = source_node in nodes
        pointer_closure_state = same_pointer_state if source_node_present else "unknown"
        if not source_node_present:
            blockers.append(
                {
                    "id": "alias-receiver-source-absent-from-pointer-closure",
                    "function": function,
                    "store_instruction": store_instruction,
                    "source_node": source_node,
                    "evidence_state": "unknown",
                }
            )
        if same_pointer_state != "verified":
            blockers.append(
                {
                    "id": "local-table-pointer-alias-not-verified",
                    "function": function,
                    "store_instruction": store_instruction,
                    "source_node": source_node,
                    "evidence_state": same_pointer_state,
                    "continuity_status": (alias_row.get("base_register_value_continuity") or {}).get("status"),
                    "store_shape_status": store_shape.get("status"),
                }
            )

        class_rows = classes_by_vtable.get(stored_address, []) if stored_address is not None else []
        class_state = "verified" if len(class_rows) == 1 else ("ambiguous" if len(class_rows) > 1 else "unknown")
        if len(class_rows) != 1:
            blockers.append(
                {
                    "id": "class-vtable-match-not-unique" if class_rows else "stored-table-absent-from-lifecycle-evidence",
                    "function": function,
                    "store_instruction": store_instruction,
                    "stored_address": stored_address,
                    "class_candidate_count": len(class_rows),
                    "evidence_state": class_state,
                }
            )

        rows_for_output = class_rows if class_rows else [None]
        for class_row in rows_for_output:
            role = _role(class_row, function) if isinstance(class_row, dict) else {
                "role": "no-class-lifecycle-match",
                "evidence_state": "unknown",
                "lifecycle_semantics_proven": False,
            }
            join_state = _weakest(class_state, pointer_closure_state)
            candidate = {
                "function": function,
                "vtable_store_instruction": store_instruction,
                "stored_table_address": stored_address,
                "same_pointer_table_store_state": same_pointer_state,
                "same_pointer_offset_zero_table_store_verified": alias_row.get(
                    "same_pointer_offset_zero_table_store_verified"
                ) is True,
                "receiver_source_node": source_node,
                "receiver_source_node_present_in_pointer_closure": source_node_present,
                "pointer_closure_join_state": pointer_closure_state,
                "class_name": class_row.get("class_name") if isinstance(class_row, dict) else None,
                "descriptor": class_row.get("descriptor") if isinstance(class_row, dict) else None,
                "class_lifecycle_complete": class_row.get("complete") if isinstance(class_row, dict) else None,
                "class_vtable_match_state": class_state,
                "lifecycle_role": role,
                "join_evidence_state": join_state,
                "verified_lifecycle_pointer_join": join_state == "verified",
                "vptr_semantics_proven": False,
                "constructor_semantics_proven": False,
                "destructor_semantics_proven": False,
                "whole_lifetime_class_identity_proven": False,
                "owner_identity_proven": False,
            }
            candidates.append(candidate)

            if isinstance(class_row, dict):
                for address in _lifecycle_neighbors(class_row):
                    if address == function:
                        continue
                    next_targets.setdefault(address, set()).add(
                        f"lifecycle neighbor of unique stored table {stored_address} ({class_row.get('class_name')})"
                    )

    candidates.sort(
        key=lambda row: (
            row["function"],
            row["vtable_store_instruction"],
            str(row.get("stored_table_address")),
            str(row.get("class_name")),
        )
    )
    verified = [row for row in candidates if row["verified_lifecycle_pointer_join"]]
    target_rows = [
        {"address": address, "reasons": sorted(reasons), "promoted": False}
        for address, reasons in sorted(next_targets.items())
    ]
    return {
        "format": FORMAT,
        "pointer_value_closure": str(pointer_closure_path),
        "vtable_pointer_alias": str(vtable_pointer_alias_path),
        "class_lifecycle_source_evidence": str(class_lifecycle_path),
        "candidate_count": len(candidates),
        "verified_lifecycle_pointer_join_count": len(verified),
        "candidates": candidates,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "next_instruction_export_targets": target_rows,
        "next_instruction_export_addresses": [row["address"] for row in target_rows],
        "scope": {
            "local_table_pointer_continuity_is_imported_not_reimplemented": True,
            "exact_literal_table_store_required_for_verified_alias": True,
            "pointer_join_requires_exact_existing_memory_source_node": True,
            "class_join_requires_unique_numeric_pe_vtable_match": True,
            "same_pointer_offset_zero_table_store_is_vptr_proof": False,
            "initializer_candidate_is_constructor_proof": False,
            "teardown_transition_candidate_is_destructor_proof": False,
            "whole_lifetime_class_identity_proven": False,
            "owner_identity_proven": False,
            "input_control_provenance_proven": False,
            "scheduler_identity_proven": False,
            "automatic_function_renaming_performed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pointer_value_closure", type=Path)
    parser.add_argument("vtable_pointer_alias", type=Path)
    parser.add_argument("class_lifecycle_source_evidence", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--targets-out", type=Path)
    parser.add_argument("--require-verified-join", action="store_true")
    args = parser.parse_args()

    report = build_vehicle_lifecycle_pointer_join(
        args.pointer_value_closure,
        args.vtable_pointer_alias,
        args.class_lifecycle_source_evidence,
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
    print(f"verified lifecycle-pointer joins: {report['verified_lifecycle_pointer_join_count']}")
    print(f"blockers: {report['blocker_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    if args.targets_out:
        print(f"targets: {args.targets_out}")
    if args.require_verified_join and not report["verified_lifecycle_pointer_join_count"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
