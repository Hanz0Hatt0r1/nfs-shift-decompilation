#!/usr/bin/env python3
"""Consume P1A's slot-agnostic same-function wheel-topology machine closure for P1.3D."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

FORMAT = "SHIFT.P1D.P13DSlot3SameFunctionTopologyHandoff/1"
UPSTREAM = "SHIFT.P1A.P13ASlot01SameFunctionTopologyMachineClosure/1"
EXPECTED_PE = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
EXPECTED_ADDRESSES = [
    "0x00757318", "0x00763570", "0x00765850", "0x00765aa0", "0x00765c40",
    "0x00769520", "0x0076b130", "0x0076df50", "0x00770e80", "0x00a705ae",
]


def build(path: Path) -> dict:
    src = json.loads(path.read_text(encoding="utf-8"))
    if src.get("format") != UPSTREAM or not src.get("ready"):
        raise ValueError("upstream same-function topology contract is unavailable")
    if src.get("authority", {}).get("retail_executable_sha256") != EXPECTED_PE:
        raise ValueError("retail PE hash drift")
    inv = src.get("inventory", {})
    adj = src.get("adjudication", {})
    if inv.get("required_same_function_scalars") != ["0x400", "0xa80"]:
        raise ValueError("wheel topology scalar drift")
    if inv.get("candidate_count") != 10 or inv.get("candidate_addresses") != EXPECTED_ADDRESSES:
        raise ValueError("same-function topology candidate drift")
    rows = src.get("candidate_adjudication", [])
    if len(rows) != 10 or any(not row.get("rejected") for row in rows):
        raise ValueError("same-function topology rejection drift")
    if not adj.get("same_function_wheel_topology_subset_complete") or adj.get("same_function_topology_target_f64_writer_found") is not False:
        raise ValueError("same-function topology adjudication drift")
    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "upstream_contract": UPSTREAM,
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": EXPECTED_PE,
            "p1a_contract_consumed_not_reowned": True,
            "machine_transfer_adjudicates": True,
        },
        "slot3": {
            "wheel_receiver": "HDVehicle+0x400+3*0xa80",
            "absolute_target": "HDVehicle+0x28b8",
            "local_field": "+0x538",
        },
        "surface": {
            "required_same_function_scalars": ["0x400", "0xa80"],
            "candidate_count": 10,
            "rejected_count": 10,
            "candidate_addresses": EXPECTED_ADDRESSES,
            "target_f64_writer_found": False,
        },
        "adjudication": {
            "slot3_same_function_wheel_topology_subset_complete": True,
            "slot3_same_function_topology_target_f64_writer_found": False,
            "slot3_interprocedural_wheel_alias_surface_complete": False,
            "slot3_overlapping_bulk_copy_surface_complete": False,
            "slot3_writer_provenance_proven": False,
            "p1_3d_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only recovered functions containing exact machine scalars +0x400 and +0xa80 in the same function.",
            "Interprocedural aliases, caller-derived bases and copy/init destinations that hide one or both constants remain open.",
            "P1A ownership is unchanged."
        ],
        "next_step": "Trace interprocedural selected-wheel aliases where wheel-base derivation and target write occur in different functions; then inspect only copy/init carriers reached by those aliases."
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", type=Path)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    try:
        payload = build(a.input)
    except ValueError as exc:
        p.error(str(exc))
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if a.output:
        a.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
