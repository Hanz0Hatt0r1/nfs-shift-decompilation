#!/usr/bin/env python3
"""Compose the bounded machine-proven selected-wheel register-alias subset."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

FORMAT = "SHIFT.P1D.Slot3RegisterAliasSubsetClosure/1"
PRIMARY_FORMAT = "SHIFT.P1D.P13DSlot3PrimaryAliasEscape/1"
CHILD_FORMAT = "SHIFT.P1D.Slot3Fun00755f80WheelChildClosure/1"
INDIRECT_FORMAT = "SHIFT.P1D.Slot3ExactCarrierIndirectCallSurface/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"

REQUIRED_INDIRECT_CARRIERS = {
    "FUN_00758b50",
    "FUN_00755950",
    "FUN_00755f80",
}


def load(path: Path, fmt: str) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("format") != fmt or payload.get("ready") is not True:
        raise ValueError(f"{path}: unexpected or unready contract")
    return payload


def build(primary_path: Path, child_path: Path, indirect_path: Path) -> dict:
    primary = load(primary_path, PRIMARY_FORMAT)
    child = load(child_path, CHILD_FORMAT)
    indirect = load(indirect_path, INDIRECT_FORMAT)

    if primary.get("authority", {}).get("retail_executable_sha256") != RETAIL_SHA256:
        raise ValueError("primary retail executable identity drift")
    if child.get("authority", {}).get("retail_executable_sha256") != RETAIL_SHA256:
        raise ValueError("wheel-child retail executable identity drift")

    loop = primary.get("primary_loop", {})
    if (
        loop.get("function") != "FUN_00758b50"
        or loop.get("selected_wheel_materialization")
        != "0x00758ccf ECX=ESI-0x448=HDVehicle+0x400+slot*0xa80"
        or loop.get("selected_wheel_direct_call") != "0x00758d6b -> FUN_00755950"
        or loop.get("exact_selected_wheel_root_forwarded_to_other_direct_callee") is not False
    ):
        raise ValueError("FUN_00758b50 exact-wheel register surface drift")

    consumer = primary.get("consumer", {})
    if (
        consumer.get("function") != "FUN_00755950"
        or consumer.get("entry_root_copy") != "0x00755956 EDX=ECX"
        or consumer.get("target_read") != "0x00755958 fld qword [EDX+0x538]"
        or consumer.get("writes_overlap_target_0x538_0x53f") is not False
        or consumer.get("exact_wheel_root_forwarded_to_callee") is not False
    ):
        raise ValueError("FUN_00755950 register alias surface drift")

    child_caller = child.get("caller", {})
    child_callee = child.get("callee", {})
    if (
        child_caller.get("function") != "FUN_00763570"
        or child_caller.get("wheel_seed") != "HDVehicle+0x400"
        or child_caller.get("stride") != "0xa80"
        or child_caller.get("iteration_count") != 4
        or child_caller.get("slot3_receiver") != "HDVehicle+0x2380"
        or child_caller.get("callee") != "FUN_00755f80"
    ):
        raise ValueError("FUN_00763570 wheel topology drift")
    if (
        child_callee.get("function") != "FUN_00755f80"
        or child_callee.get("exact_wheel_root_capture") != "ESI=ECX"
        or child_callee.get("wheel_root_write_count") != 0
        or child_callee.get("wheel_root_stored_or_pushed_after_capture") is not False
        or child_callee.get("exact_wheel_root_forwarded_to_direct_callee") is not False
        or child_callee.get("indirect_call_count") != 0
    ):
        raise ValueError("FUN_00755f80 register alias surface drift")

    primary_adj = primary.get("adjudication", {})
    if (
        primary_adj.get("primary_loop_exact_wheel_root_one_hop_forwarding_complete") is not True
        or primary_adj.get("primary_loop_exact_wheel_root_only_direct_target_is_FUN_00755950") is not True
        or primary_adj.get("FUN_00755950_exact_wheel_root_does_not_escape_to_direct_callee") is not True
    ):
        raise ValueError("primary alias adjudication drift")

    child_adj = child.get("adjudication", {})
    if (
        child_adj.get("slot3_fun00763570_to_fun00755f80_exact_wheel_path_complete") is not True
        or child_adj.get("fun00755f80_exact_wheel_escape_found") is not False
    ):
        raise ValueError("FUN_00755f80 child adjudication drift")

    ind_adj = indirect.get("adjudication", {})
    carrier_names = {
        row.get("name") for row in indirect.get("carrier_set", {}).get("functions", [])
    }
    if not REQUIRED_INDIRECT_CARRIERS.issubset(carrier_names):
        raise ValueError("required register-alias carriers missing from indirect-call surface")
    if (
        ind_adj.get("sqlite_indirect_call_edge_class_present") is not True
        or ind_adj.get("known_exact_carrier_indirect_call_edge_surface_complete") is not True
        or ind_adj.get("known_exact_carrier_indirect_call_edge_surface_empty") is not True
        or indirect.get("indirect_surface", {}).get("carrier_indirect_call_edge_count") != 0
    ):
        raise ValueError("exact-carrier indirect-call surface drift")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "upstream_contracts": [PRIMARY_FORMAT, CHILD_FORMAT, INDIRECT_FORMAT],
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": RETAIL_SHA256,
            "machine_contracts_adjudicate_object_identity": True,
            "sqlite_call_surface_is_navigation_crosscheck": True,
        },
        "selected_slot3": {
            "wheel_receiver": "HDVehicle+0x2380",
            "local_target": "+0x538",
            "absolute_target": "HDVehicle+0x28b8..+0x28bf",
        },
        "register_aliases": {
            "FUN_00758b50": {
                "materialization": "0x00758ccf ECX=ESI-0x448=HDVehicle+0x400+slot*0xa80",
                "consumer": "0x00758d6b -> FUN_00755950",
                "forwarded_to_other_direct_callee": False,
                "known_exact_carrier_callind_edges": 0,
                "persistent_store_proven": False,
            },
            "FUN_00755950": {
                "capture": "0x00755956 EDX=ECX",
                "target_use": "0x00755958 fld qword [EDX+0x538]",
                "target_is_read_only_in_consumer": True,
                "exact_root_forwarded_to_direct_callee": False,
                "known_exact_carrier_callind_edges": 0,
                "persistent_store_proven": False,
            },
            "FUN_00755f80": {
                "capture": "ESI=ECX",
                "machine_proven_selected_iteration_receiver": "HDVehicle+0x2380",
                "wheel_root_write_count": 0,
                "wheel_root_stored_or_pushed_after_capture": False,
                "exact_root_forwarded_to_direct_callee": False,
                "known_exact_carrier_callind_edges": 0,
                "persistent_store_proven": False,
            },
        },
        "adjudication": {
            "machine_proven_register_alias_subset_complete": True,
            "machine_proven_register_alias_subset_persistent_store_found": False,
            "machine_proven_register_alias_subset_new_forward_found": False,
            "machine_proven_register_alias_subset_callind_found": False,
            "machine_register_alias_storage_ruled_out": False,
            "other_register_aliases_ruled_out": False,
            "callee_created_aliases_ruled_out": False,
            "aggregate_or_bulk_alias_stores_ruled_out": False,
            "callbacks_registered_outside_carriers_ruled_out": False,
            "stored_or_escaped_aliases_ruled_out": False,
            "slot3_writer_provenance_proven": False,
            "p1_3d_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only three exact register-resident alias paths already proven by merged retail machine contracts.",
            "Zero CALLIND edges inside the known carrier set does not rule out aliases created in other callees, indirect entry, later callbacks, or persistent stores outside these paths.",
            "No decompiler variable type or numeric offset coincidence is used as selected-wheel identity.",
        ],
        "next_step": (
            "Inventory callee-created selected-wheel aliases and register aliases outside FUN_00758b50, "
            "FUN_00755950 and FUN_00755f80; join any positive persistence or callback registration "
            "to its later consumer before changing global stored/escaped-alias gates."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("primary_alias", type=Path)
    parser.add_argument("wheel_child", type=Path)
    parser.add_argument("indirect_surface", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = build(args.primary_alias, args.wheel_child, args.indirect_surface)
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
