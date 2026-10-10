#!/usr/bin/env python3
"""Compose the bounded direct-callee selected-wheel alias subset."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

FORMAT = "SHIFT.P1D.Slot3DirectCalleeAliasSubsetClosure/1"
DIRECT_FORMAT = "SHIFT.P1D.Slot3ExactWheelDirectCarrierClosure/1"
PRIMARY_FORMAT = "SHIFT.P1D.P13DSlot3PrimaryAliasEscape/1"
CHILD_FORMAT = "SHIFT.P1D.Slot3Fun00755f80WheelChildClosure/1"
INDIRECT_FORMAT = "SHIFT.P1D.Slot3ExactCarrierIndirectCallSurface/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"

REQUIRED_CARRIERS = {
    "FUN_00755950",
    "FUN_00755a60",
    "FUN_00752fc0",
    "FUN_00760b50",
    "FUN_00755f80",
}


def load(path: Path, fmt: str) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("format") != fmt or payload.get("ready") is not True:
        raise ValueError(f"{path}: unexpected or unready contract")
    return payload


def build(direct_path: Path, primary_path: Path, child_path: Path, indirect_path: Path) -> dict:
    direct = load(direct_path, DIRECT_FORMAT)
    primary = load(primary_path, PRIMARY_FORMAT)
    child = load(child_path, CHILD_FORMAT)
    indirect = load(indirect_path, INDIRECT_FORMAT)

    for label, payload in (("direct", direct), ("primary", primary), ("child", child)):
        if payload.get("authority", {}).get("retail_executable_sha256") != RETAIL_SHA256:
            raise ValueError(f"{label} retail executable identity drift")

    if direct.get("selected_slot3", {}).get("hdvehicle_offset") != "0x2380":
        raise ValueError("selected slot3 identity drift")

    p55a60 = direct.get("paths", {}).get("fun00755a60", {})
    if (
        p55a60.get("receiver") != "HDVehicle+0x400+slot*0xa80"
        or p55a60.get("slot3_receiver") != "HDVehicle+0x2380"
        or p55a60.get("exact_root_direct_forward") != "FUN_00752fc0"
        or p55a60.get("leaf_has_direct_calls") is not False
        or p55a60.get("target_overlap") is not False
        or "+0x538" in set(p55a60.get("leaf_write_offsets", []))
    ):
        raise ValueError("FUN_00755a60/FUN_00752fc0 exact-root path drift")
    if direct.get("call_inventory", {}).get("FUN_00752fc0") != []:
        raise ValueError("FUN_00752fc0 is no longer a direct-call leaf")

    p60b50 = direct.get("paths", {}).get("fun00760b50", {})
    if (
        p60b50.get("receiver") != "HDVehicle+0x2380"
        or p60b50.get("exact_root_direct_forward") is not None
        or p60b50.get("child_receiver_call") != "FUN_007ba860 receives [wheel+0x420]"
        or p60b50.get("target_overlap") is not False
    ):
        raise ValueError("FUN_00760b50 child-receiver surface drift")

    consumer = primary.get("consumer", {})
    if (
        consumer.get("function") != "FUN_00755950"
        or consumer.get("target_read") != "0x00755958 fld qword [EDX+0x538]"
        or consumer.get("writes_overlap_target_0x538_0x53f") is not False
        or consumer.get("only_direct_callee") != "0x00755983 -> FUN_007555b0"
        or consumer.get("callee_receiver") != "0x00755964 ECX=EDX+0x80"
        or consumer.get("exact_wheel_root_forwarded_to_callee") is not False
    ):
        raise ValueError("FUN_00755950 direct-callee surface drift")

    child_callee = child.get("callee", {})
    if (
        child_callee.get("function") != "FUN_00755f80"
        or child_callee.get("child_pointer_source") != "[wheel+0x420]"
        or set(child_callee.get("child_direct_callees", [])) != {"FUN_007af0a0", "FUN_007af010"}
        or child_callee.get("exact_wheel_root_forwarded_to_direct_callee") is not False
        or child_callee.get("indirect_call_count") != 0
    ):
        raise ValueError("FUN_00755f80 direct-callee surface drift")

    carrier_names = {
        row.get("name") for row in indirect.get("carrier_set", {}).get("functions", [])
    }
    if not REQUIRED_CARRIERS.issubset(carrier_names):
        raise ValueError("required direct-callee carriers missing from indirect-call surface")
    ind_adj = indirect.get("adjudication", {})
    if (
        ind_adj.get("known_exact_carrier_indirect_call_edge_surface_complete") is not True
        or ind_adj.get("known_exact_carrier_indirect_call_edge_surface_empty") is not True
        or indirect.get("indirect_surface", {}).get("carrier_indirect_call_edge_count") != 0
    ):
        raise ValueError("exact-carrier indirect-call surface drift")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "upstream_contracts": [DIRECT_FORMAT, PRIMARY_FORMAT, CHILD_FORMAT, INDIRECT_FORMAT],
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
        "exact_root_direct_callees": {
            "FUN_00755950": {
                "source": "FUN_00758b50 exact per-wheel root",
                "target_field_use": "read-only qword [wheel+0x538]",
                "target_writer_found": False,
                "exact_root_forwarded_further": False,
                "next_receiver": "FUN_007555b0 receives wheel+0x80, not exact wheel root",
            },
            "FUN_00752fc0": {
                "source": "FUN_00755a60 exact wheel root",
                "leaf_write_offsets": p55a60.get("leaf_write_offsets", []),
                "target_writer_found": False,
                "direct_call_count": 0,
                "exact_root_forwarded_further": False,
            },
        },
        "nonroot_direct_callee_receivers": [
            {
                "callee": "FUN_007555b0",
                "receiver": "wheel+0x80",
                "reason_not_exact_root": "derived interior pointer",
            },
            {
                "callee": "FUN_007ba860",
                "receiver": "[wheel+0x420]",
                "reason_not_exact_root": "dereferenced child pointer",
            },
            {
                "callee": "FUN_007af0a0",
                "receiver": "[wheel+0x420]",
                "reason_not_exact_root": "dereferenced child pointer",
            },
            {
                "callee": "FUN_007af010",
                "receiver": "[wheel+0x420]",
                "reason_not_exact_root": "dereferenced child pointer",
            },
        ],
        "adjudication": {
            "known_direct_callee_exact_root_receiver_count": 2,
            "known_direct_callee_created_alias_subset_complete": True,
            "known_direct_callee_selected_target_writer_found": False,
            "known_direct_callee_exact_root_escape_found": False,
            "known_direct_callee_callind_found": False,
            "other_callee_created_aliases_ruled_out": False,
            "callee_created_aliases_ruled_out": False,
            "machine_register_alias_storage_ruled_out": False,
            "aggregate_or_bulk_alias_stores_ruled_out": False,
            "callbacks_registered_outside_carriers_ruled_out": False,
            "stored_or_escaped_aliases_ruled_out": False,
            "slot3_writer_provenance_proven": False,
            "p1_3d_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only direct callees reached from the already-proven exact-wheel carrier paths represented by the upstream contracts.",
            "Interior wheel pointers and dereferenced child pointers are kept distinct from the exact wheel root; numeric offset proximity is not object identity.",
            "Callee-created aliases outside these direct paths, indirect entry, persistent stores, callbacks, and aggregate copies remain open.",
        ],
        "next_step": (
            "Search for exact wheel-root persistence or callback registration outside the known direct-callee paths; "
            "for each positive store, prove the later consumer and selected slot3 identity before promoting any global alias gate."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("direct_carrier", type=Path)
    parser.add_argument("primary_alias", type=Path)
    parser.add_argument("wheel_child", type=Path)
    parser.add_argument("indirect_surface", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = build(
            args.direct_carrier,
            args.primary_alias,
            args.wheel_child,
            args.indirect_surface,
        )
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
