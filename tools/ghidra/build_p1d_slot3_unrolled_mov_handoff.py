#!/usr/bin/env python3
"""Consume the merged P1A shallow unrolled-MOV machine closure for P1.3D slot3."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

FORMAT = "SHIFT.P1D.P13DSlot3UnrolledMovHandoff/1"
UPSTREAM_FORMAT = "SHIFT.P1A.P13ASlot01UnrolledMovCopyMachineClosure/1"
PE_SHA = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
EXPECTED_FUNCTIONS = [
    "FUN_0076e560", "FUN_007b0710", "FUN_00403d00", "FUN_004e9380", "FUN_00633290",
    "FUN_006333f0", "FUN_0075a8d0", "FUN_007b0580", "FUN_0064fef0", "FUN_007b0450", "_LocaleUpdate",
]


def load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("format") != UPSTREAM_FORMAT:
        raise ValueError(f"expected {UPSTREAM_FORMAT}, got {data.get('format')!r}")
    if data.get("ready") is not True:
        raise ValueError("upstream closure is not ready")
    if data.get("authority", {}).get("retail_executable_sha256") != PE_SHA:
        raise ValueError("retail executable hash drift")
    return data


def build(path: Path) -> dict:
    upstream = load(path)
    inventory = upstream.get("inventory", {})
    adjudication = upstream.get("adjudication", {})
    rows = upstream.get("candidate_adjudication", [])

    if inventory.get("candidate_count") != 11:
        raise ValueError("candidate count drift")
    if inventory.get("candidate_functions") != EXPECTED_FUNCTIONS:
        raise ValueError("candidate set/order drift")
    if len(rows) != 11 or any(row.get("rejected") is not True for row in rows):
        raise ValueError("candidate rejection drift")
    if adjudication.get("shallow_unrolled_mov_copy_semantics_complete") is not True:
        raise ValueError("upstream semantics are not complete")
    if adjudication.get("shallow_unrolled_mov_copy_rejected_count") != 11:
        raise ValueError("rejected count drift")
    if adjudication.get("shallow_unrolled_mov_copy_selected_hdvehicle_slot_writer_found") is not False:
        raise ValueError("upstream unexpectedly found selected writer")

    high = next((row for row in rows if row.get("function") == "FUN_0075a8d0"), None)
    if high is None or high.get("class") != "hdvehicle-root-explicit-high-offset-output":
        raise ValueError("HDVehicle+0x40c8 candidate classification drift")
    high_text = " ".join(high.get("evidence", [])).lower()
    if "hdvehicle+0x40c8" not in high_text or "0x40d7" not in high_text:
        raise ValueError("HDVehicle high-offset destination proof drift")

    rejected = [
        {
            "function": row["function"],
            "class": row["class"],
            "selected_slot3_writer": False,
        }
        for row in rows
    ]
    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": PE_SHA,
            "machine_transfer_adjudicates": True,
            "p1a_contract_consumed_not_reowned": True,
        },
        "upstream_contract": UPSTREAM_FORMAT,
        "slot3": {
            "absolute_target": "HDVehicle+0x28b8",
            "target_byte_range": ["HDVehicle+0x28b8", "HDVehicle+0x28bf"],
            "local_field": "+0x538",
            "width": "f64/qword",
        },
        "shallow_unrolled_mov_surface": {
            "max_direct_call_depth": 4,
            "candidate_count": 11,
            "rejected_count": 11,
            "candidate_rejections": rejected,
            "genuine_hdvehicle_non_target_destination": "HDVehicle+0x40c8..+0x40d7",
            "selected_slot3_writer_found": False,
        },
        "adjudication": {
            "slot3_shallow_straight_line_unrolled_mov_depth4_subset_complete": True,
            "slot3_straight_line_zero_init_surface_complete": False,
            "slot3_sse_vector_custom_copy_surface_complete": False,
            "slot3_non_entry_alias_loop_surface_complete": False,
            "slot3_deeper_direct_alias_paths_complete": False,
            "slot3_indirect_callback_alias_paths_complete": False,
            "slot3_writer_provenance_proven": False,
            "p1_3d_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "P1A machine evidence is consumed only where receiver/destination provenance is slot-agnostic; P1A ownership is unchanged.",
            "This closes only the 11 straight-line ordinary-MOV candidates from direct depth <=4.",
            "Zero-init, SSE/vector/custom transforms, non-entry aliases, deeper direct paths and indirect/callback carriers remain open.",
            "Reachability or numeric offset equality alone never proves selected-HDVehicle identity.",
        ],
        "next_step": "Consume or adjudicate straight-line zero-init and shallow SSE/vector candidates, then trace non-entry aliases and deeper/indirect carriers only from exact selected-wheel-derived destinations.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = build(args.upstream)
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
