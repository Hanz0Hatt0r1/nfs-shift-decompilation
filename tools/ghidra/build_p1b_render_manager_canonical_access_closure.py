#!/usr/bin/env python3
"""Compose canonical DAT_00bc185c access/origin coverage for Process 1B."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

FORMAT = "SHIFT.P1B.RenderManagerCanonicalAccessClosure/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"


def build() -> dict:
    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": RETAIL_SHA256,
        },
        "inputs": {
            "global_origin_contract": "SHIFT.P1B.RenderManagerGlobalOriginClosure/1",
            "slot_address_contract": "SHIFT.HDVehicle64e8RenderManagerGlobalSlotAddressSurface/1",
            "copy_return_contract": "SHIFT.P1B.RenderManagerCopyReturnClosure/1",
            "bounded_callee_contract": "SHIFT.P1B.RenderManagerBoundedCalleeClosure/1",
        },
        "canonical_slot": "0x00bc185c",
        "raw_occurrence_partition": {
            "whole_image_little_endian_occurrence_count": 115,
            "direct_load_count": 112,
            "direct_store_count": 2,
            "slot_address_literal_materialization_count": 1,
            "slot_address_literal_site": "0x004fb9af",
            "partition_complete": True,
        },
        "simple_slot_address_reconstruction": {
            "mov_r32_imm32_seed_count": 38128,
            "same_register_add_sub_lea_transition_count": 267,
            "literal_target_production_count": 1,
            "nonliteral_target_production_count": 0,
            "lookahead_instruction_limit": 15,
        },
        "origin_and_propagation": {
            "non_null_global_origin_unique_constructor": "FUN_0045ef50",
            "bounded_direct_target_count": 17,
            "bounded_direct_target_remaining_count": 0,
            "direct_exact_global_memory_store_count": 0,
            "direct_exact_global_push_count": 0,
            "known_returned_root_can_persist_or_dispatch": False,
        },
        "adjudication": {
            "canonical_render_manager_slot_access_surface_complete": True,
            "canonical_raw_slot_occurrence_partition_complete": True,
            "canonical_hidden_simple_arithmetic_slot_access_found": False,
            "canonical_non_null_origin_unique": True,
            "canonical_direct_propagation_escape_found": False,
            "arbitrary_unknown_memory_exact_root_alias_surface_complete": False,
            "opaque_helper_created_exact_root_surface_complete": False,
            "helper_non_vtable_setter_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "Canonical coverage is limited to the exact DAT_00bc185c slot, its raw address occurrences, simple same-register arithmetic reconstruction, and bounded propagation from exact direct loads.",
            "Unknown-memory-derived and opaque-helper-created pointers that never originate from DAT_00bc185c remain open.",
            "No identity is inferred from equal offsets.",
        ],
        "next_step": "Bound arbitrary unknown-memory/helper-created exact-root sources outside the canonical slot, then revisit manager+0x374 identity and slot2 adjudication.",
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--json-out", type=Path)
    args = p.parse_args()
    text = json.dumps(build(), indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
