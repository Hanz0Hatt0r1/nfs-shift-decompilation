#!/usr/bin/env python3
"""Compose the bounded live exact-root call-boundary closure for Process 1B."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORMAT = "SHIFT.P1B.RenderManagerLiveCallBoundaryClosure/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"

INPUTS = {
    "canonical": ROOT / "evidence/p1b_render_manager_canonical_access_closure.json",
    "call_boundary": ROOT / "evidence/hdvehicle_64e8_render_manager_machine_cfg_call_boundary_reconciliation.json",
    "vslot": ROOT / "evidence/hdvehicle_64e8_manager_374_vslot0c_dispatch_closure.json",
    "bounded_callee": ROOT / "evidence/p1b_render_manager_bounded_callee_closure.json",
}

EXPECTED_FORMATS = {
    "canonical": "SHIFT.P1B.RenderManagerCanonicalAccessClosure/1",
    "call_boundary": "SHIFT.HDVehicle64e8RenderManagerMachineCfgCallBoundaryReconciliation/1",
    "vslot": "SHIFT.HDVehicle64e8Manager374VSlot0cDispatchClosure/1",
    "bounded_callee": "SHIFT.P1B.RenderManagerBoundedCalleeClosure/1",
}


def _load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not data.get("ready"):
        raise ValueError(f"upstream contract not ready: {path}")
    return data


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def build() -> dict:
    data = {name: _load(path) for name, path in INPUTS.items()}

    for name, expected in EXPECTED_FORMATS.items():
        _require(data[name].get("format") == expected, f"{name}: format drift")

    canonical = data["canonical"]
    call_boundary = data["call_boundary"]
    vslot = data["vslot"]
    bounded = data["bounded_callee"]

    _require(canonical["authority"]["retail_executable_sha256"] == RETAIL_SHA256, "canonical retail hash drift")
    _require(call_boundary["authority"]["retail_executable_sha256"] == RETAIL_SHA256, "call-boundary retail hash drift")
    _require(vslot["authority"]["retail_executable_sha256"] == RETAIL_SHA256, "vslot retail hash drift")

    inv = call_boundary["inventory"]
    indirect = call_boundary["indirect_calls"]
    vslot_surface = vslot["exhaustive_exact_manager_first_hop"]
    direct = bounded["bounded_direct_receiver_targets"]

    _require(inv["caller_saved_indirect_callsite_count"] == 3, "indirect callsite count drift")
    _require(len(indirect) == 3, "indirect callsite inventory drift")
    _require(vslot_surface["proven_indirect_receiver_transfer_count"] == 3, "vslot indirect transfer count drift")
    _require(vslot_surface["target_slot_plus_0x0c_dispatch_count"] == 0, "target +0x0c dispatch reappeared")
    _require(call_boundary["adjudication"]["all_machine_wide_indirect_exact_root_calls_match_merged_vslot_closure"] is True,
             "machine-wide indirect calls no longer match vslot closure")
    _require(call_boundary["adjudication"]["machine_wide_new_indirect_exact_root_dispatch_found"] is False,
             "new indirect exact-root dispatch appeared")
    _require(vslot["adjudication"]["exact_manager_first_hop_indirect_surface_complete"] is True,
             "exact-manager indirect surface no longer complete")
    _require(direct["total"] == 17 and direct["closed"] == 17 and direct["remaining"] == 0,
             "bounded direct-callee closure drift")
    _require(bounded["adjudication"]["bounded_direct_callee_can_export_or_recreate_exact_outer_root"] is False,
             "bounded direct callee gained exact-root export/recreation")
    _require(canonical["adjudication"]["canonical_render_manager_slot_access_surface_complete"] is True,
             "canonical slot access closure not complete")
    _require(canonical["adjudication"]["canonical_direct_propagation_escape_found"] is False,
             "canonical direct propagation escape appeared")
    _require(canonical["adjudication"]["external_provider_count"] == 7,
             "provider count changed without Process 2 proof")

    indirect_rows = [
        {
            "callsite": row["callsite"],
            "exact_alias_registers": row["exact_alias_registers"],
            "dispatch_register": row["dispatch_register"],
            "vslot_offset": row["merged_vslot_offset"],
        }
        for row in indirect
    ]

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": RETAIL_SHA256,
        },
        "inputs": {name: EXPECTED_FORMATS[name] for name in EXPECTED_FORMATS},
        "canonical_slot": canonical["canonical_slot"],
        "live_call_boundary_inventory": {
            "call_boundary_observation_count": inv["call_boundary_observation_count"],
            "unique_callsite_count": inv["unique_callsite_count"],
            "callee_saved_only_unique_callsite_count": inv["callee_saved_only_unique_callsite_count"],
            "caller_saved_exact_alias_unique_callsite_count": inv["caller_saved_exact_alias_unique_callsite_count"],
            "caller_saved_direct_callsite_count": inv["caller_saved_direct_callsite_count"],
            "caller_saved_indirect_callsite_count": inv["caller_saved_indirect_callsite_count"],
            "eax_only_unique_callsite_count": inv["eax_only_unique_callsite_count"],
            "ecx_or_edx_receiver_like_unique_callsite_count": inv["ecx_or_edx_receiver_like_unique_callsite_count"],
            "direct_ecx_or_edx_receiver_like_unique_callsite_count": inv["direct_ecx_or_edx_receiver_like_unique_callsite_count"],
        },
        "indirect_exact_root_calls": {
            "count": len(indirect_rows),
            "calls": indirect_rows,
            "all_match_known_vtable_slots": True,
            "known_vtable_offsets": sorted({row["vslot_offset"] for row in indirect_rows}),
            "non_vtable_indirect_call_count": 0,
            "target_vslot_plus_0x0c_dispatch_count": vslot_surface["target_slot_plus_0x0c_dispatch_count"],
        },
        "direct_exact_root_callees": {
            "bounded_target_count": direct["total"],
            "closed_target_count": direct["closed"],
            "remaining_target_count": direct["remaining"],
            "byaddress_local_helper_paths_closed": direct["byaddress_local_helper_paths_closed"],
            "can_export_or_recreate_exact_outer_root": False,
        },
        "adjudication": {
            "canonical_lineage_live_call_boundary_surface_complete": True,
            "all_live_exact_root_indirect_calls_classified": True,
            "canonical_lineage_live_exact_root_non_vtable_indirect_setter_surface_complete": True,
            "canonical_lineage_live_exact_root_non_vtable_indirect_setter_found": False,
            "bounded_direct_callee_alias_surface_complete": True,
            "opaque_helper_created_exact_root_surface_complete": False,
            "arbitrary_unknown_memory_exact_root_alias_surface_complete": False,
            "helper_non_vtable_setter_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes call boundaries only when an exact canonical render-manager alias is already live in the machine-CFG replay.",
            "The three indirect callsites are known vtable dispatches at +0x1c/+0x20; this does not prove that an opaque callee cannot synthesize the exact root from unrelated unknown inputs.",
            "Unknown-memory/helper-created roots that never originate from the canonical lineage remain open.",
            "No identity is inferred from numeric offset equality.",
        ],
        "next_step": "Bound opaque helper returns and unrelated unknown-memory exact-root synthesis outside the canonical lineage, then revisit manager+0x374 identity and slot2 adjudication.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    result = build()
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
