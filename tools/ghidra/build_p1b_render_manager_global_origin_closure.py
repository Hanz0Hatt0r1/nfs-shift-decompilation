#!/usr/bin/env python3
"""Compose the bounded DAT_00bc185c origin proof into a Process 1B handoff."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

FORMAT = "SHIFT.P1B.RenderManagerGlobalOriginClosure/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"


def build() -> dict:
    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": RETAIL_SHA256,
            "source_contract": "SHIFT.PlayerVehicleRenderManagerGlobalConstructorIdentity/1",
            "source_proof_doc": "docs/PROCESS_1_PLAYER_VEHICLE_RENDER_MANAGER_CONSTRUCTOR_WRITER_PROOF.md",
        },
        "candidate_global": "0x00bc185c",
        "writer_inventory": {
            "exact_xref_count": 116,
            "selected_function_count": 80,
            "write_reference_count": 2,
            "writer_function": "FUN_00d36210",
            "writes": [
                {
                    "site": "0x00d362ec",
                    "operation": "MOV [0x00bc185c],EAX",
                    "value_origin": "FUN_0045ef50 return == entry ECX",
                    "non_null_constructor_receiver": True,
                },
                {
                    "site": "0x00d362f3",
                    "operation": "MOV dword ptr [0x00bc185c],ESI",
                    "value_origin": "0x00d36224 XOR ESI,ESI",
                    "null_store": True,
                },
            ],
        },
        "constructor_identity": {
            "constructor": "FUN_0045ef50",
            "allocation_size": "0x46e0",
            "all_reachable_returns_eax_origin": "entry:ECX",
            "layout_anchor_store": "0x0045f1bf MOV [ESI+0xca4],EAX",
            "non_null_global_value_has_constructor_identity": True,
        },
        "composition": {
            "bounded_direct_callee_contract": "SHIFT.P1B.RenderManagerBoundedCalleeClosure/1",
            "derived_subobject_contract": "SHIFT.P1B.RenderManagerDerivedSubobjectClosure/1",
            "copy_return_contract": "SHIFT.P1B.RenderManagerCopyReturnClosure/1",
            "runtime_root_frontier_contract": "SHIFT.P1B.Manager374RuntimeRootFrontier/1",
        },
        "adjudication": {
            "candidate_global_writer_surface_complete": True,
            "candidate_global_non_null_origin_unique": True,
            "external_or_unknown_origin_through_candidate_global_complete": True,
            "external_or_unknown_origin_through_candidate_global_found": False,
            "arbitrary_unknown_memory_exact_root_alias_surface_complete": False,
            "memory_load_opaque_runtime_reconstruction_complete": False,
            "helper_non_vtable_setter_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes origin ambiguity only for values sourced through DAT_00bc185c.",
            "Pointers loaded from unrelated or unknown memory are not promoted to the proven singleton root.",
            "No identity is inferred from matching numeric offsets.",
        ],
        "next_step": "Bound unknown-memory/helper-created exact-root candidates that do not originate at DAT_00bc185c, then revisit the manager+0x374 identity join and slot2 adjudication.",
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--json-out", type=Path)
    args = p.parse_args()
    data = build()
    text = json.dumps(data, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
