#!/usr/bin/env python3
"""Build the current fail-closed boundary for vehicle create return semantics.

The project now proves a long create-side machine chain:

    source-backed allocation request
      -> FUN_00886900
      -> exact create backend exit
      -> exact inner return-origin target

It also independently proves an allocation-size input role at FUN_00638020 and
aggregates that source role for FUN_00886900.  None of those facts proves the
semantic role of the value returned in EAX.

This builder composes the existing artifacts and publishes that distinction as a
stable contract.  It intentionally cannot promote an allocated-pointer return
role from diagnostic text, argument semantics, function names, callgraph shape,
or machine return provenance alone.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.VehicleReturnedAllocationPointerBoundary/1"
FRONTIER_FORMAT = "SHIFT.VehicleCreateBackendReturnOriginFrontier/1"
CATALOG_FORMAT = "SHIFT.VehicleCreateBackendReturnTargetCatalog/1"
STATIC_FORMAT = "SHIFT-MEMORY-RETAIL-STATIC-SUMMARY/1"
SOURCE_FORMAT = "SHIFT-MEMORY-SOURCE-SEMANTIC-SUMMARY/1"

CREATE_HELPER = "FUN_00886900"
ALLOCATION_BACKEND = "FUN_00638020"
ALLOCATION_BACKEND_ADDRESS = "0x00638020"


def _load(path: Path, expected: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}")
    return value


def _norm(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    token = value.strip().lower()
    if token.startswith("fun_"):
        token = token[4:]
    if token.startswith("0x"):
        token = token[2:]
    try:
        return f"0x{int(token, 16):08x}"
    except ValueError:
        return None


def _frontier_targets(report: dict[str, Any]) -> list[str]:
    if report.get("all_backend_machine_return_origins_resolved") is not True:
        raise ValueError("backend return-origin frontier is not fully resolved")
    raw = report.get("next_backend_return_targets")
    if not isinstance(raw, list) or not raw:
        raise ValueError("backend return-origin frontier has no next targets")
    targets: list[str] = []
    for value in raw:
        address = _norm(value)
        if address is None:
            raise ValueError(f"invalid backend return target: {value!r}")
        targets.append(address)
    if len(set(targets)) != len(targets):
        raise ValueError("backend return-origin frontier contains duplicate targets")
    if targets != sorted(targets):
        raise ValueError("backend return-origin frontier targets must be sorted")
    return targets


def _catalog_targets(report: dict[str, Any]) -> tuple[list[str], list[str]]:
    rows = report.get("targets")
    if not isinstance(rows, list) or not rows:
        raise ValueError("return target catalog has no targets")
    targets: list[str] = []
    eligible: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("return target catalog contains invalid target row")
        address = _norm(row.get("address"))
        if address is None:
            raise ValueError("return target catalog contains invalid address")
        targets.append(address)
        if row.get("instruction_export_eligible") is True:
            eligible.append(address)
        if row.get("returned_allocation_pointer_role_proven") is True:
            raise ValueError(
                "target catalog unexpectedly claims returned allocation-pointer semantics"
            )
    declared = report.get("instruction_export_addresses")
    if not isinstance(declared, list):
        raise ValueError("return target catalog instruction_export_addresses must be a list")
    normalized_declared = []
    for value in declared:
        address = _norm(value)
        if address is None:
            raise ValueError("return target catalog has invalid instruction export address")
        normalized_declared.append(address)
    if normalized_declared != eligible:
        raise ValueError("return target catalog instruction worklist drift")
    return targets, eligible


def _static_allocation_facts(report: dict[str, Any]) -> dict[str, Any]:
    roles = report.get("proven_physical_roles")
    if not isinstance(roles, dict):
        raise ValueError("static memory summary proven_physical_roles missing")
    allocation = roles.get("allocation_size")
    if not isinstance(allocation, dict):
        raise ValueError("static memory summary allocation_size role missing")
    return {
        "static_evidence_chain_complete": report.get("static_evidence_chain_complete") is True,
        "allocation_size_role_proven": allocation.get("proven") is True,
        "function": allocation.get("function"),
        "entry_storage": allocation.get("entry_storage"),
        "semantic_anchor": allocation.get("semantic_anchor"),
        "allocator_abi_proven": (report.get("scope") or {}).get("allocator_abi_proven") is True,
        "operator_new_identity_proven": (
            (report.get("scope") or {}).get("operator_new_identity_proven") is True
        ),
    }


def _source_allocation_profile(report: dict[str, Any]) -> dict[str, Any] | None:
    profiles = report.get("wrapper_profiles")
    if not isinstance(profiles, list):
        raise ValueError("source semantic summary wrapper_profiles missing")
    matches = [
        row
        for row in profiles
        if isinstance(row, dict) and row.get("wrapper") == CREATE_HELPER
    ]
    if len(matches) > 1:
        raise ValueError(f"source semantic summary has duplicate {CREATE_HELPER} profiles")
    if not matches:
        return None
    profile = matches[0]
    allocation = profile.get("allocation_size")
    if allocation is not None and not isinstance(allocation, dict):
        raise ValueError(f"{CREATE_HELPER}: invalid allocation_size profile")
    return {
        "wrapper": CREATE_HELPER,
        "allocation_size": allocation,
        "proven_source_roles": list(profile.get("proven_source_roles") or []),
        "blockers": list(profile.get("blockers") or []),
    }


def _backend_frontier_record(report: dict[str, Any]) -> dict[str, Any]:
    rows = report.get("backends")
    if not isinstance(rows, list):
        raise ValueError("backend return-origin frontier backends missing")
    matches = [
        row
        for row in rows
        if isinstance(row, dict) and _norm(row.get("address")) == ALLOCATION_BACKEND_ADDRESS
    ]
    if len(matches) != 1:
        raise ValueError("expected exactly one FUN_00638020 backend frontier row")
    row = matches[0]
    if row.get("machine_return_origins_resolved") is not True:
        raise ValueError("FUN_00638020 machine return origins are not resolved")
    if row.get("allocated_pointer_return_proven") is True:
        raise ValueError("backend frontier unexpectedly claims allocated-pointer return semantics")
    return row


def build_vehicle_returned_allocation_pointer_boundary(
    frontier_path: Path,
    catalog_path: Path,
    static_summary_path: Path,
    source_summary_path: Path,
) -> dict[str, Any]:
    frontier = _load(frontier_path, FRONTIER_FORMAT)
    catalog = _load(catalog_path, CATALOG_FORMAT)
    static = _load(static_summary_path, STATIC_FORMAT)
    source = _load(source_summary_path, SOURCE_FORMAT)

    frontier_targets = _frontier_targets(frontier)
    catalog_targets, instruction_targets = _catalog_targets(catalog)
    if catalog_targets != frontier_targets:
        raise ValueError("return target catalog does not match backend return-origin frontier")

    backend = _backend_frontier_record(frontier)
    static_facts = _static_allocation_facts(static)
    source_profile = _source_allocation_profile(source)

    blockers: list[str] = []
    if not static_facts["static_evidence_chain_complete"]:
        blockers.append("static_memory_evidence_chain_incomplete")
    if not static_facts["allocation_size_role_proven"]:
        blockers.append("allocation_size_physical_role_not_proven")
    if static_facts["function"] != ALLOCATION_BACKEND:
        blockers.append("allocation_size_role_not_at_FUN_00638020")

    source_allocation = source_profile.get("allocation_size") if source_profile else None
    source_role_proven = bool(
        source.get("allocation_size_role_proven") is True
        and isinstance(source_allocation, dict)
        and source_allocation.get("source_argument_index_consistent") is True
        and "allocation-size" in (source_profile.get("proven_source_roles") or [])
    )
    if not source_role_proven:
        blockers.append("FUN_00886900_source_allocation_size_role_not_proven")

    if not instruction_targets:
        blockers.append("no_internal_return_origin_targets_for_instruction_analysis")
    if catalog.get("all_targets_instruction_export_eligible") is not True:
        blockers.append("one_or_more_return_origin_targets_not_instruction_export_eligible")

    # This is the central boundary: the available static/source artifacts prove
    # argument roles and machine provenance, but none carries an independently
    # proven semantic role for the value returned by the inner target(s).
    blockers.append("returned_allocation_pointer_semantic_role_not_proven")

    vehicle_contexts = frontier.get("vehicle_create_bridges")
    if not isinstance(vehicle_contexts, list):
        raise ValueError("backend return-origin frontier vehicle_create_bridges must be a list")
    joined_contexts: list[dict[str, Any]] = []
    for row in vehicle_contexts:
        if not isinstance(row, dict):
            raise ValueError("backend return-origin frontier contains invalid vehicle context")
        joined = dict(row)
        joined["returned_allocation_pointer_role_state"] = "unknown"
        joined["returned_allocation_pointer_role_proven"] = False
        joined["returned_allocation_pointer_required_instruction_targets"] = list(
            instruction_targets
        )
        joined_contexts.append(joined)

    requirements = [
        {
            "id": "machine-return-origin",
            "satisfied": backend.get("machine_return_origins_resolved") is True,
            "evidence": "SHIFT.VehicleCreateBackendReturnOriginFrontier/1",
        },
        {
            "id": "allocation-size-physical-role",
            "satisfied": static_facts["allocation_size_role_proven"],
            "evidence": "SHIFT-MEMORY-RETAIL-STATIC-SUMMARY/1",
        },
        {
            "id": "allocation-size-source-role",
            "satisfied": source_role_proven,
            "evidence": "SHIFT-MEMORY-SOURCE-SEMANTIC-SUMMARY/1",
        },
        {
            "id": "inner-target-instruction-worklist",
            "satisfied": bool(instruction_targets),
            "evidence": "SHIFT.VehicleCreateBackendReturnTargetCatalog/1",
        },
        {
            "id": "returned-allocation-pointer-semantic-role",
            "satisfied": False,
            "evidence": None,
        },
    ]

    return {
        "format": FORMAT,
        "inputs": {
            "backend_return_origin_frontier": str(frontier_path),
            "backend_return_target_catalog": str(catalog_path),
            "memory_retail_static_summary": str(static_summary_path),
            "memory_source_semantic_summary": str(source_summary_path),
        },
        "allocation_backend": ALLOCATION_BACKEND,
        "allocation_backend_address": ALLOCATION_BACKEND_ADDRESS,
        "allocation_backend_machine_return_origin_state": "verified",
        "allocation_backend_exit_count": backend.get("exit_count"),
        "allocation_backend_return_value_semantics_state": "unknown",
        "static_allocation_facts": static_facts,
        "source_create_helper_allocation_profile": source_profile,
        "source_allocation_size_role_proven": source_role_proven,
        "return_origin_targets": frontier_targets,
        "required_instruction_targets": instruction_targets,
        "proof_requirements": requirements,
        "returned_allocation_pointer_role_state": "unknown",
        "returned_allocation_pointer_role_proven": False,
        "vehicle_create_bridges": joined_contexts,
        "blockers": sorted(set(blockers)),
        "scope": {
            "machine_return_origin_proven": True,
            "allocation_size_physical_role_can_be_proven": True,
            "allocation_size_source_role_can_be_proven": True,
            "diagnostic_text_is_return_semantic_proof": False,
            "argument_role_is_return_semantic_proof": False,
            "callgraph_shape_is_return_semantic_proof": False,
            "function_name_is_return_semantic_proof": False,
            "returned_allocation_pointer_role_proven": False,
            "allocator_abi_proven": False,
            "operator_new_identity_proven": False,
            "object_size_proven": False,
            "constructor_semantics_proven": False,
            "ownership_semantics_proven": False,
            "same_runtime_object_as_vehicle_update_proven": False,
            "note": (
                "The current corpus proves create-side argument semantics and machine return "
                "origins, but has no independent evidence assigning allocated-pointer semantics "
                "to the returned EAX value. The remaining exact instruction targets are emitted "
                "for the next proof pass; no semantic promotion is performed here."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backend_return_origin_frontier", type=Path)
    parser.add_argument("backend_return_target_catalog", type=Path)
    parser.add_argument("memory_retail_static_summary", type=Path)
    parser.add_argument("memory_source_semantic_summary", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--targets-out", type=Path)
    args = parser.parse_args()

    report = build_vehicle_returned_allocation_pointer_boundary(
        args.backend_return_origin_frontier,
        args.backend_return_target_catalog,
        args.memory_retail_static_summary,
        args.memory_source_semantic_summary,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    if args.targets_out:
        args.targets_out.parent.mkdir(parents=True, exist_ok=True)
        args.targets_out.write_text(
            "".join(address + "\n" for address in report["required_instruction_targets"]),
            encoding="utf-8",
        )

    print(f"format: {report['format']}")
    print(
        "returned allocation-pointer role: "
        f"{report['returned_allocation_pointer_role_state']}"
    )
    print(f"remaining instruction targets: {len(report['required_instruction_targets'])}")
    if args.json_out:
        print(f"output: {args.json_out}")
    if args.targets_out:
        print(f"targets: {args.targets_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
