#!/usr/bin/env python3
"""Consume P1A shallow ordinary-MOV loop closures for P1.3D slot3.

Only exact machine receiver/destination rejections that are also disjoint from
HDVehicle+0x28b8 are imported. P1A ownership remains unchanged.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

FORMAT = "SHIFT.P1D.P13DSlot3ShallowMovLoopHandoff/1"
RECEIVER_FORMAT = "SHIFT.P1A.P13ASlot01ReceiverLoopMachineClosure/1"
ORDINARY_FORMAT = "SHIFT.P1A.P13ASlot01OrdinaryMovLoopMachineClosure/1"
EXPECTED_PE = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"


def load(path: Path, expected: str) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("format") != expected or not data.get("ready"):
        raise ValueError(f"invalid upstream contract {path}")
    if data.get("authority", {}).get("retail_executable_sha256") != EXPECTED_PE:
        raise ValueError("retail PE hash drift")
    return data


def build(receiver_path: Path, ordinary_path: Path) -> dict:
    receiver = load(receiver_path, RECEIVER_FORMAT)
    ordinary = load(ordinary_path, ORDINARY_FORMAT)

    ra = receiver.get("adjudication", {})
    oa = ordinary.get("adjudication", {})
    if not ra.get("shallow_receiver_loop_depth4_surface_complete"):
        raise ValueError("receiver-loop surface incomplete")
    if ra.get("shallow_receiver_loop_candidate_count") != 8 or ra.get("shallow_receiver_loop_rejected_count") != 8:
        raise ValueError("receiver-loop count drift")
    if any(not row.get("rejected") for row in receiver.get("candidate_adjudication", [])):
        raise ValueError("receiver-loop rejection drift")
    if not oa.get("shallow_ordinary_mov_copy_init_depth4_surface_complete"):
        raise ValueError("ordinary-MOV loop surface incomplete")
    if oa.get("candidate_function_count") != 5 or oa.get("rejected_candidate_count") != 5:
        raise ValueError("ordinary-MOV loop count drift")
    if any(not row.get("rejected") for row in ordinary.get("candidate_adjudication", [])):
        raise ValueError("ordinary-MOV rejection drift")

    # The two upstream contracts prove exact destination domains. The HDVehicle
    # domains that survive receiver identity are +0xea..+0xf9, +0x3fe0,
    # +0x407c/+0x3660/+0x3678 and +0x35c8 cursor storage; none overlaps slot3.
    hdvehicle_domains = [
        "HDVehicle+0xea..+0xf9",
        "HDVehicle+0x3fe0",
        "HDVehicle+0x407c/+0x3660/+0x3678",
        "HDVehicle+0x35c8 ordinary-MOV cursor range",
    ]

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "upstream_contracts": [RECEIVER_FORMAT, ORDINARY_FORMAT],
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": EXPECTED_PE,
            "machine_transfer_adjudicates": True,
            "p1a_contracts_consumed_not_reowned": True,
        },
        "slot3": {
            "absolute_target": "HDVehicle+0x28b8",
            "target_byte_range": ["HDVehicle+0x28b8", "HDVehicle+0x28bf"],
            "local_field": "+0x538",
        },
        "receiver_loop_surface": {
            "max_direct_call_depth": 4,
            "candidate_count": 8,
            "rejected_count": 8,
            "selected_slot3_writer_found": False,
        },
        "ordinary_mov_loop_surface": {
            "max_direct_call_depth": 4,
            "candidate_count": 5,
            "rejected_count": 5,
            "selected_slot3_writer_found": False,
        },
        "proven_hdvehicle_destination_domains": hdvehicle_domains,
        "adjudication": {
            "slot3_shallow_receiver_loop_depth4_subset_complete": True,
            "slot3_shallow_ordinary_mov_loop_depth4_subset_complete": True,
            "slot3_shallow_mov_loop_writer_found": False,
            "slot3_straight_line_unrolled_mov_surface_complete": False,
            "slot3_sse_custom_copy_surface_complete": False,
            "slot3_non_entry_alias_loop_surface_complete": False,
            "slot3_deeper_direct_copy_init_paths_complete": False,
            "slot3_indirect_dispatch_surface_complete": False,
            "slot3_writer_provenance_proven": False,
            "p1_3d_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only the two merged depth<=4 backward-loop detector families.",
            "Acyclic/unrolled stores, SSE/custom transforms, non-entry aliases, deeper direct paths and indirect/callback dispatch remain open.",
            "Reachability and numeric offset equality are never selected-HDVehicle identity.",
            "P1A ownership remains unchanged."
        ],
        "next_step": "Inventory shallow straight-line unrolled MOV/FST/SSE copy-init shapes and non-entry-alias loops, then widen only exact selected-wheel-derived deeper or indirect carriers."
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("receiver_loop", type=Path)
    p.add_argument("ordinary_mov_loop", type=Path)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    try:
        payload = build(a.receiver_loop, a.ordinary_mov_loop)
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
