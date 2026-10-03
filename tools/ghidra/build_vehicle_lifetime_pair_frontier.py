#!/usr/bin/env python3
"""Join vehicle lifecycle-pointer evidence to recovered class lifetime pairs.

This composition stage narrows the next create/delete pointer-transfer targets.
It does not prove allocator, constructor, destructor, ownership, or same-runtime-
object semantics.  Identity is joined by recovered descriptor plus exact numeric
own-vtable address; class names are descriptive metadata only.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.VehicleLifetimePairFrontier/1"
LIFECYCLE_JOIN_FORMAT = "SHIFT.VehicleLifecyclePointerJoin/1"
PAIR_FORMAT = "SHIFT-CLASS-LIFETIME-PAIR-EVIDENCE/1"
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
        raise ValueError(f"address out of 32-bit range: {value!r}")
    return f"0x{number:08x}"


def _function_address(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        token = value.strip()
        if token.upper().startswith("FUN_") or token.lower().startswith("0x"):
            return _normalize_address(token)
    except ValueError:
        return None
    return None


def _function_list(values: Any, label: str) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list):
        raise ValueError(f"{label}: expected list")
    result: set[str] = set()
    for value in values:
        address = _function_address(value)
        if address is None:
            raise ValueError(f"{label}: invalid function address {value!r}")
        result.add(address)
    return sorted(result)


def _pair_state(row: dict[str, Any]) -> str:
    if row.get("ghidra_paired_lifetime_shape") is True:
        return "verified"
    if row.get("paired_lifetime_shape") is True:
        return "inferred"
    return "unknown"


def _index_pairs(pair: dict[str, Any]) -> dict[int, list[dict[str, Any]]]:
    rows = pair.get("classes")
    if not isinstance(rows, list):
        raise ValueError("class lifetime pair evidence: classes must be a list")
    result: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("class lifetime pair evidence: invalid class row")
        descriptor = row.get("descriptor")
        if not isinstance(descriptor, int):
            raise ValueError("class lifetime pair evidence: descriptor missing")
        result.setdefault(descriptor, []).append(row)
    return result


def _normalize_optional_vtable(row: dict[str, Any]) -> str | None:
    value = row.get("own_vtable")
    return _normalize_address(value) if value is not None else None


def build_vehicle_lifetime_pair_frontier(
    lifecycle_join_path: Path,
    lifetime_pair_path: Path,
) -> dict[str, Any]:
    lifecycle = _load(lifecycle_join_path, LIFECYCLE_JOIN_FORMAT)
    pair = _load(lifetime_pair_path, PAIR_FORMAT)
    pairs_by_descriptor = _index_pairs(pair)

    lifecycle_rows = lifecycle.get("candidates")
    if not isinstance(lifecycle_rows, list):
        raise ValueError("vehicle lifecycle-pointer join: candidates must be a list")

    rows: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    next_targets: dict[str, set[str]] = {}

    for lifecycle_row in lifecycle_rows:
        if not isinstance(lifecycle_row, dict):
            raise ValueError("vehicle lifecycle-pointer join: invalid candidate")
        function_raw = lifecycle_row.get("function")
        descriptor = lifecycle_row.get("descriptor")
        stored_table = lifecycle_row.get("stored_table_address")
        join_state = _state(
            lifecycle_row.get("join_evidence_state", "unknown"),
            "vehicle lifecycle-pointer join",
        )
        if not isinstance(function_raw, str):
            raise ValueError("vehicle lifecycle-pointer join: function missing")
        function = _normalize_address(function_raw)
        if not isinstance(descriptor, int):
            blockers.append(
                {
                    "id": "vehicle-lifecycle-descriptor-missing",
                    "function": function,
                    "evidence_state": "unknown",
                }
            )
            continue
        if stored_table is None:
            blockers.append(
                {
                    "id": "vehicle-lifecycle-stored-table-missing",
                    "function": function,
                    "descriptor": descriptor,
                    "evidence_state": "unknown",
                }
            )
            continue
        stored_table = _normalize_address(stored_table)

        pair_rows = pairs_by_descriptor.get(descriptor, [])
        exact_rows = [
            row for row in pair_rows if _normalize_optional_vtable(row) == stored_table
        ]
        descriptor_state = (
            "verified" if len(pair_rows) == 1 else
            "ambiguous" if len(pair_rows) > 1 else
            "unknown"
        )
        exact_state = (
            "verified" if len(exact_rows) == 1 else
            "ambiguous" if len(exact_rows) > 1 else
            "unknown"
        )

        if len(exact_rows) != 1:
            blockers.append(
                {
                    "id": (
                        "descriptor-vtable-lifetime-pair-not-unique"
                        if exact_rows else
                        "descriptor-vtable-lifetime-pair-absent"
                    ),
                    "function": function,
                    "descriptor": descriptor,
                    "stored_table_address": stored_table,
                    "descriptor_pair_count": len(pair_rows),
                    "exact_pair_count": len(exact_rows),
                    "evidence_state": exact_state,
                }
            )

        output_pairs = exact_rows if exact_rows else [None]
        for pair_row in output_pairs:
            lifetime_pair_state = _pair_state(pair_row) if isinstance(pair_row, dict) else "unknown"
            metadata_name_match = None
            lifecycle_name = lifecycle_row.get("class_name")
            pair_name = pair_row.get("class_name") if isinstance(pair_row, dict) else None
            if isinstance(lifecycle_name, str) and isinstance(pair_name, str):
                metadata_name_match = lifecycle_name == pair_name
                if not metadata_name_match:
                    blockers.append(
                        {
                            "id": "class-name-metadata-disagrees",
                            "function": function,
                            "descriptor": descriptor,
                            "stored_table_address": stored_table,
                            "vehicle_lifecycle_class_name": lifecycle_name,
                            "lifetime_pair_class_name": pair_name,
                            "evidence_state": "ambiguous",
                            "note": "class names are metadata only; descriptor+vtable remain the identity keys",
                        }
                    )

            identity_state = exact_state
            if metadata_name_match is False:
                identity_state = "ambiguous"
            overall = _weakest(join_state, identity_state, lifetime_pair_state)

            factories = _function_list(
                pair_row.get("factory_functions") if isinstance(pair_row, dict) else [],
                "factory_functions",
            )
            initializers = _function_list(
                pair_row.get("initializer_candidates") if isinstance(pair_row, dict) else [],
                "initializer_candidates",
            )
            deleting_wrappers = _function_list(
                pair_row.get("deleting_wrapper_functions") if isinstance(pair_row, dict) else [],
                "deleting_wrapper_functions",
            )
            teardowns = _function_list(
                pair_row.get("teardown_transition_functions") if isinstance(pair_row, dict) else [],
                "teardown_transition_functions",
            )
            preinit_helpers = _function_list(
                pair_row.get("preinitializer_helpers") if isinstance(pair_row, dict) else [],
                "preinitializer_helpers",
            )
            release_helpers = _function_list(
                pair_row.get("release_helpers") if isinstance(pair_row, dict) else [],
                "release_helpers",
            )

            target_categories = {
                "factory": factories,
                "initializer": initializers,
                "deleting-wrapper": deleting_wrappers,
                "teardown-transition": teardowns,
            }
            for category, addresses in target_categories.items():
                for address in addresses:
                    next_targets.setdefault(address, set()).add(
                        f"{category} target for descriptor {descriptor} / table {stored_table}"
                    )

            row = {
                "vehicle_pointer_function": function,
                "vehicle_pointer_source_node": lifecycle_row.get("receiver_source_node"),
                "stored_table_address": stored_table,
                "descriptor": descriptor,
                "vehicle_lifecycle_class_name": lifecycle_name,
                "lifetime_pair_class_name": pair_name,
                "class_name_metadata_match": metadata_name_match,
                "vehicle_lifecycle_join_state": join_state,
                "descriptor_pair_count": len(pair_rows),
                "descriptor_match_state": descriptor_state,
                "descriptor_vtable_exact_pair_count": len(exact_rows),
                "descriptor_vtable_match_state": identity_state,
                "paired_lifetime_shape": pair_row.get("paired_lifetime_shape") if isinstance(pair_row, dict) else None,
                "ghidra_paired_lifetime_shape": pair_row.get("ghidra_paired_lifetime_shape") if isinstance(pair_row, dict) else None,
                "lifetime_pair_state": lifetime_pair_state,
                "factory_functions": factories,
                "initializer_candidates": initializers,
                "preinitializer_helpers": preinit_helpers,
                "unambiguous_preinitializer_helper": (
                    _function_address(pair_row.get("unambiguous_preinitializer_helper"))
                    if isinstance(pair_row, dict)
                    else None
                ),
                "deleting_wrapper_functions": deleting_wrappers,
                "teardown_transition_functions": teardowns,
                "release_helpers": release_helpers,
                "unambiguous_release_helper": (
                    _function_address(pair_row.get("unambiguous_release_helper"))
                    if isinstance(pair_row, dict)
                    else None
                ),
                "lifetime_evidence_blockers": (
                    list(pair_row.get("lifetime_evidence_blockers") or [])
                    if isinstance(pair_row, dict)
                    else ["no_exact_lifetime_pair"]
                ),
                "frontier_evidence_state": overall,
                "verified_vehicle_lifetime_pair_frontier": overall == "verified",
                "allocation_transfer_proven": False,
                "initializer_receiver_transfer_proven": False,
                "teardown_receiver_transfer_proven": False,
                "release_transfer_proven": False,
                "same_runtime_object_across_lifetime_proven": False,
                "constructor_semantics_proven": False,
                "destructor_semantics_proven": False,
                "owner_identity_proven": False,
            }
            rows.append(row)
            if overall != "verified":
                blockers.append(
                    {
                        "id": "vehicle-lifetime-pair-frontier-not-verified",
                        "function": function,
                        "descriptor": descriptor,
                        "stored_table_address": stored_table,
                        "vehicle_lifecycle_join_state": join_state,
                        "descriptor_vtable_match_state": identity_state,
                        "lifetime_pair_state": lifetime_pair_state,
                        "evidence_state": overall,
                    }
                )

    rows.sort(
        key=lambda row: (
            row["descriptor"],
            row["stored_table_address"],
            row["vehicle_pointer_function"],
            str(row.get("lifetime_pair_class_name")),
        )
    )
    verified = [row for row in rows if row["verified_vehicle_lifetime_pair_frontier"]]
    target_rows = [
        {"address": address, "reasons": sorted(reasons), "promoted": False}
        for address, reasons in sorted(next_targets.items())
    ]
    return {
        "format": FORMAT,
        "vehicle_lifecycle_pointer_join": str(lifecycle_join_path),
        "class_lifetime_pair_evidence": str(lifetime_pair_path),
        "candidate_count": len(rows),
        "verified_frontier_count": len(verified),
        "candidates": rows,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "next_instruction_export_targets": target_rows,
        "next_instruction_export_addresses": [row["address"] for row in target_rows],
        "scope": {
            "descriptor_is_identity_key": True,
            "exact_numeric_own_vtable_is_second_identity_key": True,
            "class_name_is_identity_key": False,
            "source_only_paired_lifetime_shape_is_verified": False,
            "ghidra_paired_lifetime_shape_required_for_verified_frontier": True,
            "create_delete_shape_pair_is_same_runtime_object_proof": False,
            "factory_initializer_shape_is_constructor_proof": False,
            "teardown_deleting_wrapper_shape_is_destructor_proof": False,
            "allocator_semantics_proven": False,
            "release_semantics_proven": False,
            "ownership_semantics_proven": False,
            "next_step": (
                "Export the exact factory/initializer/deleting-wrapper/teardown functions and prove "
                "pointer-value transfer at those callsites before promoting lifetime semantics."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vehicle_lifecycle_pointer_join", type=Path)
    parser.add_argument("class_lifetime_pair_evidence", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--targets-out", type=Path)
    parser.add_argument("--require-verified-frontier", action="store_true")
    args = parser.parse_args()

    report = build_vehicle_lifetime_pair_frontier(
        args.vehicle_lifecycle_pointer_join,
        args.class_lifetime_pair_evidence,
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
    print(f"verified lifetime-pair frontiers: {report['verified_frontier_count']}")
    print(f"blockers: {report['blocker_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    if args.targets_out:
        print(f"targets: {args.targets_out}")
    if args.require_verified_frontier and not report["verified_frontier_count"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
