#!/usr/bin/env python3
"""Consume merged P1A ordinary-MOV zero-init closure for P1.3D slot3."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

FORMAT = "SHIFT.P1D.P13DSlot3OrdinaryMovZeroInitHandoff/1"
UPSTREAM = "SHIFT.P1A.P13ASlot01OrdinaryMovZeroInitMachineClosure/1"
PE_SHA = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
EXPECTED = ["FUN_00887580", "FUN_00647a10", "FUN_0070fae0", "FUN_0087aa00", "FUN_00886e10", "FUN_0088f110"]


def build(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("format") != UPSTREAM or data.get("ready") is not True:
        raise ValueError("upstream format/readiness drift")
    if data.get("authority", {}).get("retail_executable_sha256") != PE_SHA:
        raise ValueError("retail PE hash drift")
    inventory = data.get("inventory", {})
    rows = data.get("candidate_adjudication", [])
    adj = data.get("adjudication", {})
    if inventory.get("candidate_functions") != EXPECTED or inventory.get("candidate_count") != 6:
        raise ValueError("zero-init candidate set drift")
    if len(rows) != 6 or any(row.get("rejected") is not True for row in rows):
        raise ValueError("zero-init rejection drift")
    if adj.get("shallow_ordinary_mov_zero_init_depth4_surface_complete") is not True or adj.get("rejected_count") != 6:
        raise ValueError("zero-init closure drift")
    if adj.get("selected_hdvehicle_slot01_writer_found") is not False:
        raise ValueError("upstream unexpectedly found a selected writer")

    service = next(row for row in rows if row.get("function") == "FUN_0087aa00")
    service_text = " ".join(service.get("evidence", [])).lower()
    if "hdvehicle+0x6730" not in service_text:
        raise ValueError("HDVehicle+0x6730 service proof drift")

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
        "upstream_contract": UPSTREAM,
        "slot3": {
            "absolute_target": "HDVehicle+0x28b8",
            "target_byte_range": ["HDVehicle+0x28b8", "HDVehicle+0x28bf"],
            "local_field": "+0x538",
        },
        "ordinary_mov_zero_init_surface": {
            "max_direct_call_depth": 4,
            "candidate_count": 6,
            "rejected_count": 6,
            "candidate_rejections": [
                {"function": row["function"], "class": row["class"], "selected_slot3_writer": False}
                for row in rows
            ],
            "selected_slot3_writer_found": False,
        },
        "adjudication": {
            "slot3_shallow_ordinary_mov_zero_init_depth4_subset_complete": True,
            "slot3_x87_zero_init_surface_complete": False,
            "slot3_sse_vector_zero_init_surface_complete": False,
            "slot3_deeper_direct_alias_paths_complete": False,
            "slot3_indirect_callback_alias_paths_complete": False,
            "slot3_writer_provenance_proven": False,
            "p1_3d_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "Only slot-agnostic P1A receiver/destination rejections are consumed; P1A ownership is unchanged.",
            "This closes ordinary MOV zero stores outside backward loops within direct depth <=4 only.",
            "x87 FLDZ/FST, SSE/vector zero stores, deeper direct and indirect/callback paths remain open.",
            "Numeric offset coincidence is never selected-HDVehicle identity."
        ],
        "next_step": "Bound shallow x87 FLDZ/FST and SSE/vector zero-init/copy surfaces, then widen only exact selected-wheel-derived deeper or indirect aliases.",
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
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
