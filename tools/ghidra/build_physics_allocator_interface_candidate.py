#!/usr/bin/env python3
"""Join the proven PhysicsAllocator boundary to heuristic Ghidra vtable candidates.

The exact malloc/free identities come from SHIFT-PHYSICS-ALLOCATOR-BOUNDARY/1.
This tool asks a weaker, separate question: does the heuristic vtable inventory
contain one table which includes both proven members, and at which slots?

No unknown slot receives a semantic name.  The generic vtable dataset remains
heuristic and does not participate in proving the allocator boundary itself.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT-PHYSICS-ALLOCATOR-INTERFACE-CANDIDATE/1"
BOUNDARY_FORMAT = "SHIFT-PHYSICS-ALLOCATOR-BOUNDARY/1"
VTABLE_FORMAT = "SHIFT.GhidraVtableCandidates/1"


def _load_json(path: Path, expected: str) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}")
    return report


def _member_addresses(boundary: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for member in boundary.get("members") or []:
        if not isinstance(member, dict):
            continue
        role = member.get("role")
        address = member.get("address")
        if isinstance(role, str) and isinstance(address, str):
            result[role] = address
    return result


def build_physics_allocator_interface_candidate(
    boundary_path: Path,
    ghidra_export: Path,
) -> dict[str, Any]:
    boundary = _load_json(boundary_path, BOUNDARY_FORMAT)
    vtables_path = ghidra_export / "vtables.json"
    if not vtables_path.is_file():
        raise FileNotFoundError(f"missing heuristic Ghidra vtable inventory: {vtables_path}")
    vtables = _load_json(vtables_path, VTABLE_FORMAT)
    if vtables.get("status") != "heuristic-candidates":
        raise ValueError(f"{vtables_path}: expected heuristic-candidates status")

    addresses = _member_addresses(boundary)
    malloc_address = addresses.get("malloc-method-anchor")
    free_address = addresses.get("free-method-anchor")
    if malloc_address is None or free_address is None:
        raise ValueError("boundary does not contain both malloc/free member roles")

    candidates: list[dict[str, Any]] = []
    for table in vtables.get("vtables") or []:
        if not isinstance(table, dict):
            continue
        slots = [slot for slot in (table.get("slots") or []) if isinstance(slot, dict)]
        targets = {slot.get("target") for slot in slots}
        if malloc_address not in targets or free_address not in targets:
            continue
        rows: list[dict[str, Any]] = []
        for slot in slots:
            target = slot.get("target")
            semantic_role = None
            semantic_source = None
            if target == malloc_address:
                semantic_role = "PhysicsAllocator::malloc"
                semantic_source = "exact-boundary-member"
            elif target == free_address:
                semantic_role = "PhysicsAllocator::free"
                semantic_source = "exact-boundary-member"
            rows.append(
                {
                    "slot": slot.get("slot"),
                    "target": target,
                    "ghidra_name": slot.get("name"),
                    "semantic_role": semantic_role,
                    "semantic_source": semantic_source,
                    "unknown_member": semantic_role is None,
                }
            )
        candidates.append(
            {
                "address": table.get("address"),
                "block": table.get("block"),
                "slot_count": table.get("slot_count"),
                "function_xrefs": table.get("function_xrefs") or [],
                "slots": rows,
                "malloc_slots": sorted(
                    int(slot["slot"])
                    for slot in rows
                    if slot["target"] == malloc_address and isinstance(slot.get("slot"), int)
                ),
                "free_slots": sorted(
                    int(slot["slot"])
                    for slot in rows
                    if slot["target"] == free_address and isinstance(slot.get("slot"), int)
                ),
                "unknown_slot_count": sum(slot["unknown_member"] is True for slot in rows),
            }
        )

    candidates.sort(key=lambda row: str(row.get("address") or ""))
    unique = candidates[0] if len(candidates) == 1 else None
    boundary_confirmed = boundary.get("physics_allocator_boundary_confirmed") is True
    interface_candidate = bool(boundary_confirmed and unique is not None)

    return {
        "format": FORMAT,
        "boundary": str(boundary_path),
        "ghidra_export": str(ghidra_export),
        "vtable_inventory_status": vtables.get("status"),
        "boundary_confirmed": boundary_confirmed,
        "malloc_address": malloc_address,
        "free_address": free_address,
        "shared_vtable_candidate_count": len(candidates),
        "unique_shared_vtable_candidate": unique is not None,
        "physics_allocator_interface_candidate": interface_candidate,
        "candidate": unique,
        "candidates": candidates,
        "scope": {
            "exact_member_semantics_from_boundary_only": True,
            "generic_vtable_inventory_is_heuristic": True,
            "vtable_candidate_used_to_prove_boundary": False,
            "unknown_slot_semantics_proven": False,
            "class_identity_proven_by_vtable": False,
            "virtual_dispatch_runtime_use_proven": False,
            "note": (
                "A positive interface candidate means the already-proven malloc/free "
                "boundary members co-occur in exactly one generic heuristic vtable "
                "candidate. Only those two slot semantics are inherited from the exact "
                "boundary. All other slots and the table's class/dispatch identity remain "
                "unresolved until corroborated independently."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("boundary", type=Path, help=f"{BOUNDARY_FORMAT} JSON")
    parser.add_argument("--ghidra-export", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = build_physics_allocator_interface_candidate(args.boundary, args.ghidra_export)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"shared vtable candidates: {report['shared_vtable_candidate_count']}")
    print(f"interface candidate: {report['physics_allocator_interface_candidate']}")
    if report.get("candidate"):
        print(f"candidate address: {report['candidate'].get('address')}")
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
