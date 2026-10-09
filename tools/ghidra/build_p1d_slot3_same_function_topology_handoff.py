#!/usr/bin/env python3
"""Consume the merged P1A same-function wheel-topology closure for P1.3D slot3.

This is an ownership/integration bridge.  It reuses a whole-retail machine subset
already adjudicated by P1A without transferring shard ownership.  The result
closes only functions containing both exact +0x400 wheel-base and +0xa80 stride
scalars in the same recovered function; interprocedural and escaped aliases stay
open.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

FORMAT = "SHIFT.P1D.P13DSlot3SameFunctionTopologyHandoff/1"
P1A_FORMAT = "SHIFT.P1A.P13ASlot01SameFunctionTopologyMachineClosure/1"
SLOT3_FORMAT = "SHIFT.P1D.P13DSlot3Wheel538MaterializerHandoff/1"
EXPECTED_ADDRESSES = [
    "0x00757318",
    "0x00763570",
    "0x00765850",
    "0x00765aa0",
    "0x00765c40",
    "0x00769520",
    "0x0076b130",
    "0x0076df50",
    "0x00770e80",
    "0x00a705ae",
]


def load(path: Path, expected_format: str) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("format") != expected_format:
        raise ValueError(f"{path}: expected {expected_format}, got {payload.get('format')!r}")
    if not payload.get("ready"):
        raise ValueError(f"{path}: upstream contract is not ready")
    return payload


def build(p1a_path: Path, slot3_path: Path) -> dict:
    p1a = load(p1a_path, P1A_FORMAT)
    slot3 = load(slot3_path, SLOT3_FORMAT)

    authority = p1a.get("authority", {})
    if authority.get("retail_executable_sha256") != "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1":
        raise ValueError("retail executable hash drift")
    if authority.get("ghidra_sqlite_sha256") != "ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e":
        raise ValueError("Ghidra SQLite hash drift")

    target = slot3.get("slot3", {})
    if target.get("absolute_target") != "HDVehicle+0x28b8":
        raise ValueError("slot3 absolute target drift")
    if target.get("local_field") != "+0x538" or target.get("width") != "f64/qword":
        raise ValueError("slot3 local field/width drift")

    inventory = p1a.get("inventory", {})
    if inventory.get("required_same_function_scalars") != ["0x400", "0xa80"]:
        raise ValueError("same-function topology scalar contract drift")
    if inventory.get("candidate_count") != 10:
        raise ValueError("same-function topology candidate count drift")
    if inventory.get("candidate_addresses") != EXPECTED_ADDRESSES:
        raise ValueError("same-function topology candidate address drift")

    candidates = p1a.get("candidate_adjudication", [])
    if [row.get("address") for row in candidates] != EXPECTED_ADDRESSES:
        raise ValueError("candidate adjudication address drift")
    if any(row.get("rejected") is not True for row in candidates):
        raise ValueError("an upstream same-function topology candidate is no longer rejected")

    upstream_adj = p1a.get("adjudication", {})
    if upstream_adj.get("same_function_wheel_topology_subset_complete") is not True:
        raise ValueError("upstream same-function topology subset is not complete")
    if upstream_adj.get("same_function_topology_target_f64_writer_found") is not False:
        raise ValueError("upstream same-function topology target writer gate changed")

    summarized = [
        {
            "function": row.get("function"),
            "address": row.get("address"),
            "class": row.get("class"),
            "rejected": True,
            "evidence": row.get("evidence", []),
        }
        for row in candidates
    ]

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "upstream_contracts": [P1A_FORMAT, SLOT3_FORMAT],
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": authority.get("retail_executable_sha256"),
            "ghidra_sqlite_sha256": authority.get("ghidra_sqlite_sha256"),
            "machine_transfer_adjudicates": True,
            "p1a_contract_is_consumed_not_reowned": True,
        },
        "slot3": {
            "absolute_target": "HDVehicle+0x28b8",
            "wheel_runtime_receiver": "HDVehicle+0x400+3*0xa80",
            "local_field": "+0x538",
            "width": "f64/qword",
        },
        "same_function_topology_surface": {
            "required_exact_scalars": ["0x400", "0xa80"],
            "candidate_count": 10,
            "rejected_count": 10,
            "candidate_addresses": EXPECTED_ADDRESSES,
            "candidate_adjudication": summarized,
            "selected_slot3_target_f64_writer_found": False,
        },
        "adjudication": {
            "slot3_same_function_wheel_topology_subset_complete": True,
            "slot3_same_function_topology_candidate_count": 10,
            "slot3_same_function_topology_rejected_count": 10,
            "slot3_same_function_topology_target_f64_writer_found": False,
            "slot3_interprocedural_alias_surface_complete": False,
            "slot3_escaped_alias_store_surface_complete": False,
            "slot3_base_plus_delta_alias_surface_complete": False,
            "slot3_overlapping_bulk_copy_surface_complete": False,
            "slot3_indirect_dispatch_surface_complete": False,
            "slot3_writer_provenance_proven": False,
            "retail_input_control_provenance_proven": False,
            "p1_3d_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "The consumed P1A proof is whole-retail and rejects these functions as local wheel target-f64 producers; P1A shard ownership is unchanged.",
            "This closes only recovered functions containing exact +0x400 and +0xa80 scalar uses in the same function.",
            "Caller-derived wheel bases, aliases split across functions, escaped pointers, computed destinations, copy/init ranges and indirect dispatch remain open.",
            "Numeric topology is never selected-HDVehicle object identity by itself.",
        ],
        "next_step": (
            "Trace interprocedural and escaped wheel-base aliases that hide +0x400 or +0xa80, then bound copy/init and indirect-dispatch destinations covering selected HDVehicle+0x28b8..+0x28bf."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("p1a_same_function_closure", type=Path)
    parser.add_argument("slot3_wheel538_handoff", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = build(args.p1a_same_function_closure, args.slot3_wheel538_handoff)
    except ValueError as exc:
        parser.error(str(exc))
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
