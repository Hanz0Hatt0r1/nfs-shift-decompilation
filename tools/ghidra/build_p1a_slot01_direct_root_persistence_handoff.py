#!/usr/bin/env python3
"""Build the P1.3A direct exact-HDVehicle-root persistence handoff.

This consumes the merged P1D machine proof for the complete 16-carrier direct
exact-root value surface, but reuses only the 11 carriers whose exact root is
HDVehicle itself. Wheel-root carriers stay outside this handoff.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

FORMAT = "SHIFT.P1A.P13ADirectHDVehicleRootPersistenceHandoff/1"
UPSTREAM_FORMAT = "SHIFT.P1D.Slot3SixteenCarrierDirectRootPersistence/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"

HDVEHICLE_ROOT_CARRIERS = [
    "FUN_00758810",
    "FUN_00758b50",
    "FUN_00758fc0",
    "FUN_00763570",
    "FUN_00765c40",
    "FUN_00766510",
    "FUN_007675f0",
    "FUN_007682c0",
    "FUN_00769ef0",
    "FUN_0076d100",
    "FUN_00770e80",
]

EXCLUDED_WHEEL_ROOT_CARRIERS = [
    "FUN_00752fc0",
    "FUN_00755950",
    "FUN_00755a60",
    "FUN_00755f80",
    "FUN_00760b50",
]


def build(upstream: dict) -> dict:
    if upstream.get("format") != UPSTREAM_FORMAT:
        raise ValueError(f"unexpected upstream format: {upstream.get('format')!r}")
    if upstream.get("ready") is not True:
        raise ValueError("upstream direct-root persistence evidence is not ready")

    authority = upstream.get("authority", {})
    if authority.get("retail_executable_sha256") != RETAIL_SHA256:
        raise ValueError("upstream retail executable hash drift")

    scope = upstream.get("scope", {})
    if scope.get("carrier_count") != 16:
        raise ValueError("expected complete 16-carrier upstream scope")
    functions = scope.get("functions", {})
    expected_all = set(HDVEHICLE_ROOT_CARRIERS) | set(EXCLUDED_WHEEL_ROOT_CARRIERS)
    if set(functions) != expected_all:
        missing = sorted(expected_all - set(functions))
        extra = sorted(set(functions) - expected_all)
        raise ValueError(f"carrier-set drift: missing={missing} extra={extra}")

    upstream_adj = upstream.get("adjudication", {})
    required_false = [
        "machine_direct_exact_root_nonstack_store_found",
        "machine_direct_exact_root_push_found",
        "machine_direct_exact_root_new_gpr_alias_beyond_ecx_receiver_reload_found",
    ]
    if upstream_adj.get("machine_direct_exact_root_storage_16_carrier_subset_complete") is not True:
        raise ValueError("upstream 16-carrier direct-root subset is incomplete")
    for key in required_false:
        if upstream_adj.get(key) is not False:
            raise ValueError(f"upstream fail-closed premise changed: {key}")

    surface = upstream.get("direct_exact_root_value_surface", {})
    if surface.get("memory_store_count") != 2:
        raise ValueError("unexpected direct exact-root memory-store count")
    if surface.get("nonstack_or_unknown_memory_store_count") != 0:
        raise ValueError("non-stack direct exact-root store appeared")
    if surface.get("push_count") != 0:
        raise ValueError("direct exact-root push appeared")
    if surface.get("register_copy_count") != 23:
        raise ValueError("unexpected direct exact-root register-copy count")
    if surface.get("register_copy_destinations") != ["ecx"]:
        raise ValueError("new direct exact-root GPR alias class appeared")

    root_stores = []
    for row in surface.get("memory_stores", []):
        if row.get("function") not in HDVEHICLE_ROOT_CARRIERS:
            raise ValueError("direct exact-root memory store escaped HDVehicle-root subset")
        if row.get("storage") != "stack-local":
            raise ValueError("HDVehicle-root pointer store is not stack-local")
        root_stores.append(row)

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1A / P1.3A",
        "upstream_contract": UPSTREAM_FORMAT,
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": RETAIL_SHA256,
            "machine_bytes_adjudicate_upstream": True,
            "cross_lane_machine_proof_consumed_without_reowning": True,
        },
        "scope": {
            "upstream_carrier_count": 16,
            "consumed_exact_hdvehicle_root_carrier_count": len(HDVEHICLE_ROOT_CARRIERS),
            "consumed_exact_hdvehicle_root_carriers": HDVEHICLE_ROOT_CARRIERS,
            "excluded_exact_wheel_root_carrier_count": len(EXCLUDED_WHEEL_ROOT_CARRIERS),
            "excluded_exact_wheel_root_carriers": EXCLUDED_WHEEL_ROOT_CARRIERS,
            "slot0_target": "HDVehicle+0x938..+0x93f",
            "slot1_target": "HDVehicle+0x13b8..+0x13bf",
            "wheel_local_target": "+0x538..+0x53f",
        },
        "direct_exact_hdvehicle_root_value_surface": {
            "memory_store_count": len(root_stores),
            "memory_stores": root_stores,
            "nonstack_or_unknown_memory_store_count": 0,
            "push_count": 0,
            "new_gpr_alias_beyond_ecx_receiver_reload_found": False,
            "upstream_total_register_copy_count": 23,
            "upstream_register_copy_destinations": ["ecx"],
        },
        "adjudication": {
            "p13a_direct_exact_hdvehicle_root_persistence_subset_complete": True,
            "p13a_direct_exact_hdvehicle_root_nonstack_store_found": False,
            "p13a_direct_exact_hdvehicle_root_push_found": False,
            "p13a_direct_exact_hdvehicle_root_new_gpr_alias_found": False,
            "derived_wheel_or_interior_alias_storage_ruled_out": False,
            "runtime_generated_or_copied_pointer_stores_ruled_out": False,
            "callee_created_aliases_ruled_out": False,
            "callbacks_and_indirect_entry_ruled_out": False,
            "stored_or_escaped_aliases_ruled_out": False,
            "p13a_slot0_complete": False,
            "p13a_slot1_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This consumes only the 11 exact-HDVehicle-root carriers from the merged 16-carrier machine proof.",
            "The five exact-wheel-root carriers are intentionally excluded and remain part of the separate derived/wheel-root alias frontier.",
            "The upstream direct-value proof classifies only stable exact-root register stores, pushes and immediate GPR copies; derived/interior addresses, aggregate copies, reconstructed pointers, callbacks, indirect entry and callee-created aliases remain open.",
            "No slot completion or aggregate P1.3 gate is promoted by pointer-persistence absence alone.",
        ],
        "next_step": (
            "Close the exact wheel-root persistence/materialization subset for slot0/slot1, "
            "then trace derived/interior and runtime-generated pointer aliases before changing "
            "the global stored-or-escaped-alias gate."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--upstream",
        type=Path,
        default=Path("evidence/p1d_slot3_16carrier_direct_root_persistence.json"),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    upstream = json.loads(args.upstream.read_text(encoding="utf-8"))
    payload = build(upstream)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
