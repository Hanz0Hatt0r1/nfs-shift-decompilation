#!/usr/bin/env python3
"""Build a conservative static boundary for retail MWL PhysicsAllocator.

The boundary is anchored by exact method-name strings plus direct Ghidra
function/call/string observations.  It proves the paired malloc/free API surface
and its physical entry-storage shape, but deliberately does not assign a
semantic role to the lone explicit stack parameter or infer return/ownership
ABI.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT-PHYSICS-ALLOCATOR-BOUNDARY/1"

MEMBERS: tuple[dict[str, Any], ...] = (
    {
        "role": "malloc-method-anchor",
        "address": "0x0079cd90",
        "name": "FUN_0079cd90",
        "method_anchor": "MWL::Core::PhysicsAllocator::malloc",
        "calling_convention": "__thiscall",
        "parameter_storage": ["ECX:4 (auto)", "Stack[0x4]:4"],
        "required_shared_strings": [
            "pPool",
            ".\\Source\\System\\PhysXSupport.cpp",
            "No BMemPool available",
        ],
    },
    {
        "role": "free-method-anchor",
        "address": "0x0079ce30",
        "name": "FUN_0079ce30",
        "method_anchor": "MWL::Core::PhysicsAllocator::free",
        "calling_convention": "__thiscall",
        "parameter_storage": ["ECX:4 (auto)", "Stack[0x4]:4"],
        "required_shared_strings": [
            "pPool",
            ".\\Source\\System\\PhysXSupport.cpp",
            "No BMemPool available",
        ],
    },
)


def _read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            yield row


def _storage(function: dict[str, Any] | None) -> list[str]:
    if function is None:
        return []
    return [
        str(parameter.get("storage"))
        for parameter in (function.get("parameters") or [])
        if isinstance(parameter, dict) and parameter.get("storage") is not None
    ]


def _load_export(root: Path) -> dict[str, Any]:
    required = ["functions.jsonl", "strings_xrefs.jsonl", "callgraph.jsonl"]
    missing = [name for name in required if not (root / name).is_file()]
    if missing:
        raise FileNotFoundError("missing required Ghidra files: " + ", ".join(missing))

    functions: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(root / "functions.jsonl"):
        address = row.get("address")
        if isinstance(address, str):
            functions[address] = row

    strings_by_function: dict[str, list[dict[str, Any]]] = {}
    for row in _read_jsonl(root / "strings_xrefs.jsonl"):
        for function in row.get("functions") or []:
            if isinstance(function, str):
                strings_by_function.setdefault(function, []).append(row)

    calls_by_function: dict[str, list[dict[str, Any]]] = {}
    for row in _read_jsonl(root / "callgraph.jsonl"):
        source = row.get("from_function")
        if row.get("indirect") is False and isinstance(source, str):
            calls_by_function.setdefault(source, []).append(row)
    for rows in calls_by_function.values():
        rows.sort(key=lambda row: (str(row.get("instruction") or ""), str(row.get("to") or "")))

    return {
        "functions": functions,
        "strings_by_function": strings_by_function,
        "calls_by_function": calls_by_function,
    }


def _inspect_member(spec: dict[str, Any], export: dict[str, Any]) -> dict[str, Any]:
    address = spec["address"]
    function = export["functions"].get(address)
    string_rows = export["strings_by_function"].get(address, [])
    values = sorted(
        {
            str(row.get("value"))
            for row in string_rows
            if isinstance(row.get("value"), str)
        }
    )
    method_rows = [row for row in string_rows if row.get("value") == spec["method_anchor"]]
    method_exact = len(method_rows) == 1
    method_single_function = bool(
        method_exact
        and sorted(method_rows[0].get("functions") or []) == [address]
    )
    shared = {
        value: value in values for value in spec["required_shared_strings"]
    }
    observed_storage = _storage(function)
    cc_match = bool(
        function is not None
        and function.get("calling_convention") == spec["calling_convention"]
    )
    storage_match = bool(function is not None and observed_storage == spec["parameter_storage"])
    direct_calls = [
        {
            "instruction": row.get("instruction"),
            "target": row.get("to"),
            "target_name": row.get("to_name"),
        }
        for row in export["calls_by_function"].get(address, [])
    ]
    member_confirmed = bool(
        function is not None
        and method_exact
        and method_single_function
        and cc_match
        and storage_match
        and all(shared.values())
    )
    blockers: list[str] = []
    if function is None:
        blockers.append("function_missing")
    if not method_exact:
        blockers.append("exact_method_anchor_missing_or_duplicated")
    elif not method_single_function:
        blockers.append("method_anchor_not_unique_to_function")
    if function is not None and not cc_match:
        blockers.append("calling_convention_mismatch")
    if function is not None and not storage_match:
        blockers.append("parameter_storage_mismatch")
    blockers.extend(
        f"missing_shared_string:{value}" for value, present in shared.items() if not present
    )

    return {
        "role": spec["role"],
        "address": address,
        "name": function.get("name") if function else spec["name"],
        "function_present": function is not None,
        "size": function.get("size") if function else None,
        "thunk": function.get("thunk") if function else None,
        "mnemonic_sha256": function.get("mnemonic_sha256") if function else None,
        "calling_convention": function.get("calling_convention") if function else None,
        "expected_calling_convention": spec["calling_convention"],
        "calling_convention_match": cc_match,
        "parameter_storage": observed_storage,
        "expected_parameter_storage": spec["parameter_storage"],
        "parameter_storage_match": storage_match,
        "reported_signature": function.get("signature") if function else None,
        "reported_parameter_types": [
            str(parameter.get("type"))
            for parameter in (function.get("parameters") or [])
            if isinstance(parameter, dict) and parameter.get("type") is not None
        ] if function else [],
        "semantic_parameter_types_used_for_promotion": False,
        "method_anchor": spec["method_anchor"],
        "method_anchor_exact_once": method_exact,
        "method_anchor_unique_to_function": method_single_function,
        "method_anchor_string_addresses": sorted(
            str(row.get("address")) for row in method_rows if row.get("address") is not None
        ),
        "required_shared_strings": shared,
        "observed_strings": values,
        "direct_calls": direct_calls,
        "direct_call_targets": sorted(
            {row["target"] for row in direct_calls if isinstance(row.get("target"), str)}
        ),
        "member_confirmed": member_confirmed,
        "blockers": blockers,
    }


def build_physics_allocator_boundary(root: Path) -> dict[str, Any]:
    export = _load_export(root)
    members = [_inspect_member(spec, export) for spec in MEMBERS]
    malloc = members[0]
    free = members[1]
    same_entry_shape = bool(
        malloc["calling_convention"] == free["calling_convention"] == "__thiscall"
        and malloc["parameter_storage"] == free["parameter_storage"] == [
            "ECX:4 (auto)",
            "Stack[0x4]:4",
        ]
    )
    shared_required_strings = sorted(
        set(MEMBERS[0]["required_shared_strings"])
        & set(MEMBERS[1]["required_shared_strings"])
    )
    boundary_confirmed = bool(
        all(member["member_confirmed"] for member in members)
        and same_entry_shape
    )

    return {
        "format": FORMAT,
        "ghidra_export": str(root),
        "member_count": len(members),
        "confirmed_member_count": sum(member["member_confirmed"] is True for member in members),
        "physics_allocator_boundary_confirmed": boundary_confirmed,
        "same_entry_storage_shape": same_entry_shape,
        "shared_required_strings": shared_required_strings,
        "members": members,
        "scope": {
            "exact_method_name_strings_used": True,
            "shared_pool_diagnostic_strings_used": True,
            "calling_convention_used": True,
            "physical_parameter_storage_used": True,
            "direct_call_neighborhood_recorded": True,
            "direct_call_target_semantics_proven": False,
            "ghidra_semantic_parameter_types_trusted": False,
            "explicit_stack_parameter_role_proven": False,
            "return_value_abi_proven": False,
            "allocation_result_semantics_proven": False,
            "free_argument_pointer_role_proven": False,
            "pool_ownership_semantics_proven": False,
            "physx_allocator_interface_boundary_proven": boundary_confirmed,
            "note": (
                "A confirmed boundary proves that the paired retail functions carry "
                "the exact MWL::Core::PhysicsAllocator::malloc/free method strings, "
                "share the expected pool/source diagnostics and have the same physical "
                "thiscall entry-storage shape. The meaning of Stack[0x4], return-value "
                "ABI, ownership and individual backend callees remain separate evidence."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = build_physics_allocator_boundary(args.ghidra_export)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"confirmed members: {report['confirmed_member_count']}/{report['member_count']}")
    print(f"allocator boundary confirmed: {report['physics_allocator_boundary_confirmed']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
