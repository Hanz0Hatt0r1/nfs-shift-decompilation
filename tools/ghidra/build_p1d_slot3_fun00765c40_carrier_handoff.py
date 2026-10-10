#!/usr/bin/env python3
"""Compose merged FUN_00765c40 ownership proofs into the P1.3D slot3 frontier.

The upstream Process 1/P1A contracts remain semantic authority. This builder only
checks that their complete HDVehicle write/side-effect surfaces are disjoint from
selected slot3 HDVehicle+0x28b8..+0x28bf and records the missing carrier handoff.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

FORMAT = "SHIFT.P1D.Slot3Fun00765c40CarrierHandoff/1"
OWNERSHIP_FORMAT = "SHIFT.Fun00765c40ResidualOwnershipFrontier/1"
WRITE_FORMAT = "SHIFT.Fun00765c40DirectMachineWriteSurface/1"
WHEEL_FORMAT = "SHIFT.Fun00752fa0WheelStateMachineProof/1"
TAIL_FORMAT = "SHIFT.Fun007584f0MachineSideEffectProof/1"
PE_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
TARGET_START = 0x28B8
TARGET_END = 0x28BF


def load(path: Path, expected: str) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("format") != expected or not payload.get("ready"):
        raise ValueError(f"{path}: unexpected or unready contract")
    authority = payload.get("authority", {})
    retail = authority.get("retail_executable_sha256")
    if retail is not None and retail != PE_SHA256:
        raise ValueError(f"{path}: retail executable identity drift")
    return payload


def parse_offset(value: str) -> int:
    text = value.strip().lower().split()[0]
    if text.startswith("+"):
        text = text[1:]
    return int(text, 0)


def overlaps(offset: int, width: int) -> bool:
    return offset <= TARGET_END and offset + width - 1 >= TARGET_START


def build(ownership_path: Path, write_path: Path, wheel_path: Path, tail_path: Path) -> dict:
    ownership = load(ownership_path, OWNERSHIP_FORMAT)
    writes = load(write_path, WRITE_FORMAT)
    wheel = load(wheel_path, WHEEL_FORMAT)
    tail = load(tail_path, TAIL_FORMAT)

    if ownership.get("authority", {}).get("retail_executable_sha256") != PE_SHA256:
        raise ValueError("ownership retail identity drift")
    if ownership.get("side_effect_surface", {}).get("direct_machine_writes_closed") is not True:
        raise ValueError("direct machine write surface not closed upstream")
    if ownership.get("side_effect_surface", {}).get("callee_mediated_object_side_effects_closed") is not True:
        raise ValueError("callee-mediated side effects not closed upstream")
    if ownership.get("side_effect_surface", {}).get("unclassified_callees") != []:
        raise ValueError("unclassified FUN_00765c40 callees remain upstream")

    if writes.get("authority", {}).get("function") != "FUN_00765c40":
        raise ValueError("write-surface function drift")
    if writes.get("direct_write_surface_complete_for_machine_body") is not True:
        raise ValueError("direct write surface incomplete")
    if writes.get("callee_mediated_side_effects_complete") is not True:
        raise ValueError("callee write surface incomplete")

    direct_lanes = []
    width_map = {"byte": 1, "dword": 4, "float": 4, "qword": 8}
    for row in writes.get("closed_preexisting_writes", []):
        offset = parse_offset(row["offset"]); width = width_map[row["width"]]
        direct_lanes.append((offset, width, row["offset"]))
    for group in writes.get("direct_write_groups", []):
        if "offsets" in group:
            width = 8 if "qword" in group.get("kind", "") else 4
            for text in group["offsets"]:
                direct_lanes.append((parse_offset(text), width, text))
        elif "offset" in group:
            width = width_map[group["width"]]
            direct_lanes.append((parse_offset(group["offset"]), width, group["offset"]))
        elif group.get("kind") == "contact_record_pointer_array":
            start = parse_offset(group["base_offset"])
            for index in range(group["count"]):
                direct_lanes.append((start + index * 4, 4, f"+0x{start + index * 4:x}"))
        elif group.get("kind") == "contact_scalar_qword_array":
            start = parse_offset(group["base_offset"])
            for index in range(group["count"]):
                direct_lanes.append((start + index * 8, 8, f"+0x{start + index * 8:x}"))
        elif "base_offset" in group and group.get("stride") == "0x0a80":
            start = parse_offset(group["base_offset"])
            for index in range(group["count"]):
                direct_lanes.append((start + index * 0xA80, 8, f"+0x{start + index * 0xA80:x}"))
        elif "base_offsets" in group:
            for base_text in group["base_offsets"]:
                start = parse_offset(base_text)
                for index in range(group["count"]):
                    direct_lanes.append((start + index * 0xA80, 8, f"+0x{start + index * 0xA80:x}"))

    direct_overlaps = [text for offset, width, text in direct_lanes if overlaps(offset, width)]
    if direct_overlaps:
        raise ValueError(f"direct FUN_00765c40 write unexpectedly overlaps slot3: {direct_overlaps}")

    wheel_offsets = []
    for key, width in (("index_dword_offsets", 4), ("qword_offsets", 8)):
        for text in wheel.get("vehicle_relative_writes", {}).get(key, []):
            offset = parse_offset(text)
            wheel_offsets.append((offset, width, text))
    if any(overlaps(offset, width) for offset, width, _ in wheel_offsets):
        raise ValueError("FUN_00752fa0 wheel-state write overlaps slot3")
    if wheel.get("callee_side_effect_surface_closed") is not True:
        raise ValueError("FUN_00752fa0 side-effect surface incomplete")

    tail_offsets = []
    for row in tail.get("persistent_object_writes", []):
        width = width_map[row["width"]]
        values = row.get("hdvehicle_offsets") or [row.get("hdvehicle_offset")]
        for text in values:
            offset = parse_offset(text)
            tail_offsets.append((offset, width, text))
    if any(overlaps(offset, width) for offset, width, _ in tail_offsets):
        raise ValueError("FUN_007584f0 persistent write overlaps slot3")
    if tail.get("adjudication", {}).get("persistent_object_write_surface_complete") is not True:
        raise ValueError("FUN_007584f0 persistent write surface incomplete")
    if tail.get("adjudication", {}).get("nested_object_side_effect_surface_complete") is not True:
        raise ValueError("FUN_007584f0 nested side effects incomplete")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "upstream_contracts": [OWNERSHIP_FORMAT, WRITE_FORMAT, WHEEL_FORMAT, TAIL_FORMAT],
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": PE_SHA256,
            "upstream_machine_contracts_consumed_not_reowned": True,
        },
        "carrier": {
            "function": "FUN_00765c40",
            "entry": "0x00765c40",
            "receiver_domain": "HDVehicle",
            "lifecycle_parent": "FUN_0076d100",
            "direct_callsite": "0x0076d12b",
            "previous_p1d_exact_carrier_count": 15,
            "expanded_p1d_exact_carrier_count": 16,
        },
        "selected_slot3": {
            "absolute_target": "HDVehicle+0x28b8",
            "target_byte_range": ["HDVehicle+0x28b8", "HDVehicle+0x28bf"],
            "width": "f64/qword",
        },
        "write_surface": {
            "direct_machine_write_surface_complete": True,
            "direct_target_overlap": False,
            "callee_mediated_object_side_effects_complete": True,
            "unclassified_callees": [],
            "fun00752fa0_target_overlap": False,
            "fun007584f0_target_overlap": False,
        },
        "adjudication": {
            "fun00765c40_exact_hdvehicle_carrier_handoff_complete": True,
            "fun00765c40_selected_slot3_writer_found": False,
            "p1d_exact_carrier_set_expanded_to_16": True,
            "source_storage_replay_for_16_carriers_complete": False,
            "runtime_generated_pointer_stores_ruled_out": False,
            "callee_created_aliases_ruled_out": False,
            "stored_or_escaped_aliases_ruled_out": False,
            "slot3_writer_provenance_proven": False,
            "p1_3d_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This consumes the already-complete Process 1/P1A FUN_00765c40 ownership and side-effect contracts; ownership is unchanged.",
            "The prior 15-carrier source-storage replay is not silently promoted to 16 carriers; FUN_00765c40 source-storage replay remains a separate fail-closed task.",
            "Runtime/generated pointers, callee-created aliases and unresolved indirect entry remain open."
        ],
        "next_step": "Rerun the P1D storage/indirect/static-pointer carrier inventories with FUN_00765c40 included, then continue callee-created/runtime pointer aliases.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ownership", type=Path)
    parser.add_argument("write_surface", type=Path)
    parser.add_argument("wheel_state", type=Path)
    parser.add_argument("tail_side_effect", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = build(args.ownership, args.write_surface, args.wheel_state, args.tail_side_effect)
    except ValueError as exc:
        parser.error(str(exc))
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
