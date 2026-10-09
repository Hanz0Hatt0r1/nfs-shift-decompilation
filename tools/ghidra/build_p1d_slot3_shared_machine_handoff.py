#!/usr/bin/env python3
"""Consume slot-agnostic P1A machine closures for the P1.3D slot3 frontier.

The upstream P1A contracts retain their ownership. This builder only imports
proofs whose machine destination/receiver rejection is independent of slot0/1.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

FORMAT = "SHIFT.P1D.P13DSlot3SharedMachineHandoff/1"
FORMATS = {
    "overlap": "SHIFT.P1A.P13ASlot01OverlapStoreClosure/1",
    "rep": "SHIFT.P1A.P13ASlot01InlineRepMachineClosure/1",
    "bare": "SHIFT.P1A.P13ASlot01BareStringMachineClosure/1",
    "named": "SHIFT.P1A.P13ASlot01NamedMemoryFrontierEvidence/1",
    "consumer": "SHIFT.Fun00755950AbsoluteConsumedFieldMachineProof/1",
}
EXPECTED_PE = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"


def load(path: Path, expected: str) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}, got {data.get('format')!r}")
    if not data.get("ready"):
        raise ValueError(f"{path}: upstream not ready")
    return data


def build(overlap_path: Path, rep_path: Path, bare_path: Path, named_path: Path, consumer_path: Path) -> dict:
    overlap = load(overlap_path, FORMATS["overlap"])
    rep = load(rep_path, FORMATS["rep"])
    bare = load(bare_path, FORMATS["bare"])
    named = load(named_path, FORMATS["named"])
    consumer = load(consumer_path, FORMATS["consumer"])

    for row in (overlap, rep, bare, named):
        authority = row.get("authority", {})
        pe = authority.get("retail_executable_sha256")
        if pe != EXPECTED_PE:
            raise ValueError(f"retail PE hash drift: {pe!r}")

    c = consumer.get("consumer", {})
    if c.get("wheel_runtime_this_expression") != "HDVehicle+0x400+slot*0xa80":
        raise ValueError("consumer topology drift")
    if [str(x).lower() for x in c.get("slot_offsets", [])] != ["0x938", "0x13b8", "0x1e38", "0x28b8"]:
        raise ValueError("consumer slot map drift")

    oa = overlap.get("adjudication", {})
    if not oa.get("exact_literal_overlap_store_surface_complete"):
        raise ValueError("overlap-store surface is not complete")
    if overlap.get("inventory", {}).get("overlapping_store_count") != 25:
        raise ValueError("overlap-store count drift")
    if overlap.get("inventory", {}).get("function_count") != 13:
        raise ValueError("overlap-store function count drift")
    if not oa.get("all_partial_store_receivers_rejected") or not oa.get("known_qword_store_receiver_rejected"):
        raise ValueError("overlap receiver rejection drift")

    ra = rep.get("adjudication", {})
    if not ra.get("shallow_inline_rep_depth4_surface_complete"):
        raise ValueError("REP surface not complete")
    if ra.get("shallow_inline_rep_candidate_count") != 5 or ra.get("shallow_inline_rep_rejected_count") != 5:
        raise ValueError("REP candidate count drift")
    if any(not row.get("rejected") for row in rep.get("candidate_adjudication", [])):
        raise ValueError("REP rejection drift")

    ba = bare.get("adjudication", {})
    if not ba.get("shallow_canonical_bare_string_depth4_surface_complete"):
        raise ValueError("bare-string surface not complete")
    if ba.get("shallow_canonical_bare_string_candidate_count") != 2 or ba.get("shallow_canonical_bare_string_rejected_count") != 2:
        raise ValueError("bare-string candidate count drift")
    if any(not row.get("rejected") for row in bare.get("candidate_adjudication", [])):
        raise ValueError("bare-string rejection drift")

    summary = named.get("summary", {})
    if summary.get("named_copy_or_set_within_depth4_any_root") is not False:
        raise ValueError("named-memory depth4 result drift")
    roots = named.get("scan", {}).get("roots", [])
    if roots != ["FUN_00758b50", "FUN_0076d100", "FUN_00763570", "FUN_00770e80"]:
        raise ValueError("named-memory root drift")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": EXPECTED_PE,
            "machine_transfer_adjudicates": True,
            "p1a_contracts_consumed_not_reowned": True,
        },
        "upstream_contracts": list(FORMATS.values()),
        "slot3": {
            "wheel_runtime_receiver": "HDVehicle+0x400+3*0xa80",
            "wheel_runtime_receiver_absolute": "HDVehicle+0x2380",
            "local_byte_range": ["+0x538", "+0x53f"],
            "absolute_byte_range": ["HDVehicle+0x28b8", "HDVehicle+0x28bf"],
            "width": "f64/qword",
        },
        "closed_shared_subsets": {
            "exact_literal_overlap_stores": {
                "store_count": 25,
                "function_count": 13,
                "all_receivers_rejected_for_selected_hdvehicle": True,
                "slot3_writer_found": False,
            },
            "named_copy_set_depth4": {
                "roots": roots,
                "named_copy_or_set_within_depth4_any_root": False,
                "navigation_only": True,
            },
            "inline_rep_depth4": {
                "candidate_count": 5,
                "rejected_count": 5,
                "selected_hdvehicle_writer_found": False,
            },
            "bare_string_depth4": {
                "candidate_count": 2,
                "rejected_count": 2,
                "selected_hdvehicle_writer_found": False,
            },
        },
        "adjudication": {
            "slot3_exact_literal_overlap_store_subset_complete": True,
            "slot3_shallow_named_copy_set_depth4_surface_empty": True,
            "slot3_shallow_inline_rep_depth4_subset_complete": True,
            "slot3_shallow_bare_string_depth4_subset_complete": True,
            "slot3_computed_address_store_surface_complete": False,
            "slot3_escaped_alias_store_surface_complete": False,
            "slot3_nonstring_custom_unrolled_copy_init_complete": False,
            "slot3_deeper_direct_copy_init_paths_complete": False,
            "slot3_indirect_dispatch_surface_complete": False,
            "slot3_writer_provenance_proven": False,
            "retail_input_control_provenance_proven": False,
            "p1_3d_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "Only slot-agnostic machine rejections are consumed from P1A; P1A ownership is unchanged.",
            "Direct-call reachability remains navigation evidence and is never object identity.",
            "Computed destinations, escaped aliases, ordinary MOV/unrolled custom copies, deeper direct paths and indirect dispatch remain open.",
            "Numeric overlap with +0x538..+0x53f never proves selected-HDVehicle identity."
        ],
        "next_step": "Trace computed-address and escaped selected-HDVehicle wheel aliases first; only then inspect ordinary MOV/unrolled custom copy/init ranges or deeper/indirect carriers that receive such an alias.",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("overlap", type=Path)
    p.add_argument("rep", type=Path)
    p.add_argument("bare", type=Path)
    p.add_argument("named", type=Path)
    p.add_argument("consumer", type=Path)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    try:
        payload = build(a.overlap, a.rep, a.bare, a.named, a.consumer)
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
