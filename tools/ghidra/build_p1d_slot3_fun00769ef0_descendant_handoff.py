#!/usr/bin/env python3
"""Compose merged retail proofs for the FUN_00769ef0 exact-HDVehicle descendant tranche.

This is a P1.3D ownership bridge. It consumes existing source/machine-backed
contracts and closes only the explicitly proven descendant state destinations;
it does not claim complete FUN_00769ef0 semantics or global alias exhaustion.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

FORMAT = "SHIFT.P1D.Slot3Fun00769ef0DescendantHandoff/1"
BODY_DEST_FORMAT = "SHIFT.Fun007682c0Body0DeltaDestination/1"
NODE_CACHE_FORMAT = "SHIFT.Fun007675f0SurfaceProbeNodeCache/1"
DISTANCE_FORMAT = "SHIFT.Fun007675f0DistanceStateOwnership/1"
PE_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
TARGET_START = 0x28B8
TARGET_END = 0x28BF


def load(path: Path, expected_format: str) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("format") != expected_format or not payload.get("ready"):
        raise ValueError(f"{path}: unexpected or unready contract")
    return payload


def overlaps_qword(offset: int) -> bool:
    return offset <= TARGET_END and offset + 7 >= TARGET_START


def build(body_dest_path: Path, node_cache_path: Path, distance_path: Path) -> dict:
    body = load(body_dest_path, BODY_DEST_FORMAT)
    cache = load(node_cache_path, NODE_CACHE_FORMAT)
    distance = load(distance_path, DISTANCE_FORMAT)

    source = cache.get("source", {})
    if source.get("sha256") != PE_SHA256:
        raise ValueError("node-cache retail identity drift")
    if source.get("caller") != "FUN_00769ef0" or source.get("consumer") != "FUN_007675f0":
        raise ValueError("FUN_00769ef0 -> FUN_007675f0 identity drift")
    if cache.get("caller_join", {}).get("only_direct_call_to_FUN_007675f0") != "0x0076a1c7":
        raise ValueError("FUN_007675f0 callsite drift")

    chain = {row.get("function"): row for row in body.get("receiver_chain", [])}
    if "FUN_0076d100" not in chain or "FUN_00769ef0" not in chain:
        raise ValueError("pass-tail receiver chain drift")
    if "FUN_00769ef0(this)" not in str(chain["FUN_0076d100"].get("fact", "")):
        raise ValueError("FUN_0076d100 exact receiver forwarding no longer proven")
    if "forwarded vehicle receiver" not in str(chain["FUN_00769ef0"].get("fact", "")):
        raise ValueError("FUN_00769ef0 forwarded vehicle receiver no longer proven")

    retail_state = cache.get("retail_state", {})
    if retail_state.get("node_owner") != "HDVehicle" or retail_state.get("node_offset") != "0x120":
        raise ValueError("surface-probe node owner drift")
    last_offsets = [int(x, 16) for x in retail_state.get("last_body_position_offsets", [])]
    if last_offsets != [0x128, 0x130, 0x138]:
        raise ValueError("surface-probe last-position offsets drift")

    distance_state = distance.get("retail_state", {})
    if distance_state.get("owner") != "HDVehicle" or distance_state.get("offset") != "0x4080":
        raise ValueError("FUN_007675f0 distance-state owner drift")

    destination = body.get("destination", {})
    identity = body.get("identity_join", {})
    if destination.get("function") != "FUN_007682c0":
        raise ValueError("FUN_007682c0 destination contract drift")
    if destination.get("vehicle_pointer_field") != "HDVehicle+0x33a0":
        raise ValueError("FUN_007682c0 vehicle BODY pointer field drift")
    if destination.get("body_record_offset") != "0x50":
        raise ValueError("FUN_007682c0 BODY record destination drift")
    if identity.get("destination_is_retail_BMW_chassis_BODY0") is not True:
        raise ValueError("FUN_007682c0 BODY0 identity no longer proven")

    hdvehicle_qword_offsets = [0x120, 0x128, 0x130, 0x138, 0x4080]
    if any(overlaps_qword(x) for x in hdvehicle_qword_offsets):
        raise ValueError("known descendant HDVehicle state unexpectedly overlaps selected slot3")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "upstream_contracts": [BODY_DEST_FORMAT, NODE_CACHE_FORMAT, DISTANCE_FORMAT],
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": PE_SHA256,
            "upstream_source_machine_contracts_consumed_not_reowned": True,
        },
        "selected_slot3": {
            "absolute_target": "HDVehicle+0x28b8..+0x28bf",
            "width": "f64/qword",
        },
        "exact_root_chain": {
            "pass_tail_callsite": "0x0076d2c1",
            "pass_tail": "FUN_0076d100 -> FUN_00769ef0",
            "receiver": "HDVehicle",
            "descendant_calls": [
                {"callsite": "0x0076a1c7", "callee": "FUN_007675f0", "receiver_domain": "HDVehicle pass state"},
                {"callsite": "0x0076a1e8", "callee": "FUN_007682c0", "receiver_domain": "forwarded HDVehicle -> chassis BODY0 pointer field"},
            ],
        },
        "proven_descendant_destinations": {
            "FUN_007675f0_hdvehicle_state_offsets": ["+0x120", "+0x128", "+0x130", "+0x138", "+0x4080"],
            "FUN_007675f0_selected_slot3_overlap": False,
            "FUN_007682c0_vehicle_pointer_field": "HDVehicle+0x33a0",
            "FUN_007682c0_destination_owner": "retail BMW chassis BODY0",
            "FUN_007682c0_body_record_write_offset": "+0x50",
            "FUN_007682c0_writes_selected_hdvehicle_slot3": False,
        },
        "adjudication": {
            "slot3_fun00769ef0_known_descendant_tranche_complete": True,
            "slot3_fun00769ef0_known_descendant_writer_found": False,
            "fun00769ef0_complete_write_surface_proven": False,
            "fun00758810_exact_root_branch_complete": False,
            "deeper_direct_aliases_ruled_out": False,
            "stored_or_escaped_aliases_ruled_out": False,
            "indirect_callback_aliases_ruled_out": False,
            "slot3_writer_provenance_proven": False,
            "p1_3d_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only the already-proven FUN_00769ef0 descendant destinations carried by the three upstream contracts.",
            "It does not claim every write performed directly inside FUN_00769ef0 has been exhaustively classified.",
            "FUN_00758810 remains a separate exact-HDVehicle branch from FUN_0076d100.",
            "BODY0 +0x50 is a distinct object destination and is never equated with HDVehicle+0x28b8 by numeric coincidence.",
        ],
        "next_step": "Adjudicate FUN_0076d100 0x0076d193 -> FUN_00758810 by exact HDVehicle receiver flow, then continue only stored/escaped or indirect carriers that preserve selected-wheel identity.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("body0_destination", type=Path)
    parser.add_argument("surface_probe_cache", type=Path)
    parser.add_argument("distance_state", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = build(args.body0_destination, args.surface_probe_cache, args.distance_state)
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
