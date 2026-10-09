#!/usr/bin/env python3
"""Consume merged slot-parametric +0x538 proofs for P1.3D slot3."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

FORMAT = "SHIFT.P1D.P13DSlot3Wheel538MaterializerHandoff/1"
P1A_FORMAT = "SHIFT.P1A.P13ASlot01Wheel538ForwardingFrontier/1"
OVERLAP_FORMAT = "SHIFT.P1A.P13ASlot01OverlapStoreClosure/1"
CONSUMER_FORMAT = "SHIFT.Fun00755950AbsoluteConsumedFieldMachineProof/1"


def load(path: Path, expected: str) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}, got {payload.get('format')!r}")
    if not payload.get("ready"):
        raise ValueError(f"{path}: upstream contract is not ready")
    return payload


def build(p1a_path: Path, overlap_path: Path, consumer_path: Path) -> dict:
    p1a = load(p1a_path, P1A_FORMAT)
    overlap = load(overlap_path, OVERLAP_FORMAT)
    consumer = load(consumer_path, CONSUMER_FORMAT)

    local = p1a.get("consumer", {})
    if local.get("receiver") != "HDVehicle+0x400+slot*0xa80":
        raise ValueError("wheel receiver topology drift")
    if local.get("local_field") != "+0x538" or local.get("width") != "f64":
        raise ValueError("wheel-local field/width drift")

    machine_consumer = consumer.get("consumer", {})
    if machine_consumer.get("wheel_runtime_this_expression") != "HDVehicle+0x400+slot*0xa80":
        raise ValueError("consumer machine topology drift")
    slot_offsets = [str(x).lower() for x in machine_consumer.get("slot_offsets", [])]
    if slot_offsets != ["0x938", "0x13b8", "0x1e38", "0x28b8"]:
        raise ValueError(f"consumer slot map drift: {slot_offsets!r}")

    surface = p1a.get("whole_image_surface", {})
    materializers = surface.get("positive_address_materializers", [])
    if surface.get("exact_0x538_scalar_use_count") != 43:
        raise ValueError("exact +0x538 whole-image count drift")
    if surface.get("positive_address_materializer_count") != 4 or len(materializers) != 4:
        raise ValueError("+0x538 materializer count drift")
    upstream_rows = p1a.get("materializer_adjudication", [])
    if len(upstream_rows) != 4 or any(
        not str(row.get("adjudication", "")).startswith("rejected") for row in upstream_rows
    ):
        raise ValueError("+0x538 materializer rejection drift")
    adjudications = [
        {key: row.get(key) for key in ("site", "function", "role", "adjudication")}
        for row in upstream_rows
    ]

    direct = surface.get("direct_qword_store_existing_rejection", {})
    normalized = [str(x).lower() for x in direct.get("normalized_absolute_slots", [])]
    if normalized != ["hdvehicle+0xc80", "hdvehicle+0x1700", "hdvehicle+0x2180", "hdvehicle+0x2c00"]:
        raise ValueError("direct qword-store normalization drift")
    if direct.get("matches_consumer_slots") is not False:
        raise ValueError("direct qword store unexpectedly matches consumer slots")

    target = overlap.get("target", {})
    if target.get("wheel_local_byte_range") != ["0x538", "0x540"] or target.get("width") != "f64/qword":
        raise ValueError("overlap-store target range/width drift")
    inventory = overlap.get("inventory", {})
    expected_counts = {
        "overlapping_store_count": 25,
        "partial_store_count": 24,
        "qword_or_wider_store_count": 1,
        "function_count": 13,
        "unowned_instruction_count": 0,
    }
    for key, value in expected_counts.items():
        if inventory.get(key) != value:
            raise ValueError(f"overlap-store {key} drift")
    overlap_adj = overlap.get("adjudication", {})
    required_true = (
        "exact_literal_overlap_store_surface_complete",
        "all_partial_store_receivers_rejected",
        "known_qword_store_receiver_rejected",
    )
    if any(overlap_adj.get(key) is not True for key in required_true):
        raise ValueError("overlap-store rejection gate drift")
    if overlap_adj.get("selected_slot0_or_slot1_exact_literal_overlap_writer_found") is not False:
        raise ValueError("overlap-store selected writer unexpectedly found")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "upstream_contracts": [P1A_FORMAT, OVERLAP_FORMAT, CONSUMER_FORMAT],
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": p1a.get("authority", {}).get("retail_executable_sha256"),
            "machine_transfer_adjudicates": True,
            "p1a_contracts_are_consumed_not_reowned": True,
        },
        "slot3": {
            "slot": 3,
            "wheel_runtime_receiver": "HDVehicle+0x400+3*0xa80",
            "wheel_runtime_receiver_absolute": "HDVehicle+0x2380",
            "local_field": "+0x538",
            "local_byte_range": ["+0x538", "+0x540"],
            "absolute_target": "HDVehicle+0x28b8",
            "absolute_byte_range": ["HDVehicle+0x28b8", "HDVehicle+0x28c0"],
            "width": "f64/qword",
        },
        "exact_local_surface": {
            "whole_image_exact_0x538_scalar_use_count": 43,
            "positive_address_materializer_count": 4,
            "positive_address_materializers": materializers,
            "materializer_adjudication": adjudications,
            "all_positive_materializers_rejected_as_selected_slot3_f64_producers": True,
            "direct_positive_qword_store": surface.get("direct_qword_store"),
            "direct_positive_qword_store_slot3_destination": "HDVehicle+0x2c00",
            "direct_positive_qword_store_matches_slot3_target": False,
        },
        "exact_literal_overlap_store_surface": {
            "overlapping_store_count": 25,
            "partial_store_count": 24,
            "qword_or_wider_store_count": 1,
            "function_count": 13,
            "unowned_instruction_count": 0,
            "partial_writer_functions": inventory.get("partial_writer_functions", []),
            "all_partial_store_receivers_rejected": True,
            "known_qword_store_receiver_rejected": True,
            "selected_slot3_exact_literal_overlap_writer_found": False,
        },
        "adjudication": {
            "slot3_exact_local_0x538_materializer_callee_subset_complete": True,
            "slot3_exact_literal_overlap_store_surface_complete": True,
            "slot3_direct_positive_qword_0x538_store_rejected": True,
            "slot3_computed_address_store_surface_complete": False,
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
            "Merged P1A contracts are consumed because their whole-image local +0x538 range is slot-parametric; shard ownership is not transferred.",
            "Literal address materializers and every literal store overlapping local bytes +0x538..+0x53f are closed only after exact receiver-domain rejection.",
            "Computed destinations, escaped aliases, nonliteral base-plus-delta paths, bulk-copy/init and indirect dispatch remain open.",
            "Numeric equality alone is never selected-HDVehicle object identity."
        ],
        "next_step": (
            "Trace computed destinations and escaped/base-plus-delta aliases, then overlapping bulk-copy/init and indirect dispatch that can cover selected HDVehicle+0x28b8..+0x28bf. Require exact selected-root provenance before promotion."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("p1a_wheel538", type=Path)
    parser.add_argument("p1a_overlap_store", type=Path)
    parser.add_argument("consumer_machine_proof", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = build(args.p1a_wheel538, args.p1a_overlap_store, args.consumer_machine_proof)
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
