#!/usr/bin/env python3
"""Build the P1.3A slot0/slot1 wheel-root materialization/persistence handoff.

Consumes merged P1D machine contracts without changing their ownership.  The
claim is intentionally narrow: known HDVehicle -> wheel-root materializations
for slot0/slot1 plus direct exact-wheel-root store/push/GPR-copy persistence.
Derived/interior, reconstructed, runtime-generated and indirect aliases remain
outside this handoff.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

FORMAT = "SHIFT.P1A.P13ASlot01WheelRootMaterializationPersistenceHandoff/1"
PERSISTENCE_FORMAT = "SHIFT.P1D.Slot3SixteenCarrierDirectRootPersistence/1"
MATERIALIZATION_FORMAT = "SHIFT.P1D.Slot3MachineWheelRootMaterializationClosure/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"

WHEEL_ROOT_CARRIERS = [
    "FUN_00752fc0",
    "FUN_00755950",
    "FUN_00755a60",
    "FUN_00755f80",
    "FUN_00760b50",
]
EXPECTED_WHEEL_REGISTER_COPIES = [
    {
        "address": "0x00755db3",
        "destination": "ecx",
        "function": "FUN_00755a60",
        "operands": "ecx,esi",
    }
]
WHEEL_RECEIVERS = [
    "HDVehicle+0x400",
    "HDVehicle+0xe80",
    "HDVehicle+0x1900",
    "HDVehicle+0x2380",
]
SLOTS = [
    {
        "slot": 0,
        "wheel_receiver": "HDVehicle+0x400",
        "absolute_target": "HDVehicle+0x938..+0x93f",
        "local_target": "+0x538..+0x53f",
        "explicit_materialization_site": "0x007710fe",
        "explicit_consumer_call": "0x00771107",
        "explicit_consumer": "FUN_00760b50",
        "loop_consumer_call": "0x0076360f",
        "loop_consumer": "FUN_00755f80",
    },
    {
        "slot": 1,
        "wheel_receiver": "HDVehicle+0xe80",
        "absolute_target": "HDVehicle+0x13b8..+0x13bf",
        "local_target": "+0x538..+0x53f",
        "explicit_materialization_site": "0x0077111c",
        "explicit_consumer_call": "0x00771125",
        "explicit_consumer": "FUN_00760b50",
        "loop_consumer_call": "0x0076360f",
        "loop_consumer": "FUN_00755f80",
    },
]


def _require_ready(data: dict, expected_format: str, label: str) -> None:
    if data.get("format") != expected_format:
        raise ValueError(f"unexpected {label} format: {data.get('format')!r}")
    if data.get("ready") is not True:
        raise ValueError(f"{label} evidence is not ready")
    if data.get("authority", {}).get("retail_executable_sha256") != RETAIL_SHA256:
        raise ValueError(f"{label} retail executable hash drift")


def build(persistence: dict, materialization: dict) -> dict:
    _require_ready(persistence, PERSISTENCE_FORMAT, "persistence")
    _require_ready(materialization, MATERIALIZATION_FORMAT, "materialization")

    scope = persistence.get("scope", {})
    functions = scope.get("functions", {})
    if scope.get("carrier_count") != 16:
        raise ValueError("expected complete 16-carrier persistence scope")
    missing = [name for name in WHEEL_ROOT_CARRIERS if name not in functions]
    if missing:
        raise ValueError(f"wheel-root carriers missing from persistence scope: {missing}")

    persistence_adj = persistence.get("adjudication", {})
    if persistence_adj.get("machine_direct_exact_root_storage_16_carrier_subset_complete") is not True:
        raise ValueError("upstream direct-root persistence subset is incomplete")
    for key in (
        "machine_direct_exact_root_nonstack_store_found",
        "machine_direct_exact_root_push_found",
        "machine_direct_exact_root_new_gpr_alias_beyond_ecx_receiver_reload_found",
    ):
        if persistence_adj.get(key) is not False:
            raise ValueError(f"upstream persistence premise changed: {key}")

    surface = persistence.get("direct_exact_root_value_surface", {})
    wheel_stores = [
        row for row in surface.get("memory_stores", [])
        if row.get("function") in WHEEL_ROOT_CARRIERS
    ]
    if wheel_stores:
        raise ValueError(f"unexpected direct exact-wheel-root memory stores: {wheel_stores}")
    if surface.get("push_count") != 0:
        raise ValueError("unexpected direct exact-root push in upstream surface")
    wheel_copies = [
        row for row in surface.get("register_copies", [])
        if row.get("function") in WHEEL_ROOT_CARRIERS
    ]
    if wheel_copies != EXPECTED_WHEEL_REGISTER_COPIES:
        raise ValueError(f"wheel-root register-copy surface drift: {wheel_copies}")

    mat_adj = materialization.get("adjudication", {})
    if mat_adj.get("known_hdvehicle_to_four_wheel_root_materialization_machine_subset_complete") is not True:
        raise ValueError("wheel-root materialization machine subset is incomplete")
    if mat_adj.get("selected_slot3_wheel_root_nonstack_persistence_found") is not False:
        raise ValueError("materialization persistence premise changed")

    layout = materialization.get("wheel_layout", {})
    if layout != {
        "count": 4,
        "root_offsets": ["+0x400", "+0xe80", "+0x1900", "+0x2380"],
        "stride": "+0xa80",
    }:
        raise ValueError(f"wheel layout drift: {layout}")

    loop = materialization.get("fun00763570_loop", {})
    if loop.get("materialized_receivers") != WHEEL_RECEIVERS:
        raise ValueError("FUN_00763570 wheel receiver sequence drift")
    if loop.get("cursor_storage") != "stack-local [EBP-0x4]":
        raise ValueError("FUN_00763570 wheel cursor is no longer stack-local")
    if loop.get("nonstack_wheel_root_store_found") is not False:
        raise ValueError("FUN_00763570 gained non-stack wheel-root persistence")
    if loop.get("consumer") != "FUN_00755f80" or loop.get("callsite") != "0x0076360f":
        raise ValueError("FUN_00763570 loop consumer drift")

    explicit = materialization.get("fun00770e80_explicit", {})
    rows = explicit.get("materializations", [])
    if [row.get("receiver") for row in rows] != WHEEL_RECEIVERS:
        raise ValueError("FUN_00770e80 explicit wheel receiver sequence drift")
    if explicit.get("callee") != "FUN_00760b50":
        raise ValueError("FUN_00770e80 explicit wheel consumer drift")
    if explicit.get("wheel_root_nonstack_store_count") != 0 or explicit.get("wheel_root_push_count") != 0:
        raise ValueError("FUN_00770e80 materialization gained wheel-root persistence")
    if rows[0].get("site") != "0x007710fe" or rows[0].get("calls") != ["0x00771107"]:
        raise ValueError("slot0 explicit materialization drift")
    if rows[1].get("site") != "0x0077111c" or rows[1].get("calls") != ["0x00771125"]:
        raise ValueError("slot1 explicit materialization drift")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1A / P1.3A",
        "upstream_contracts": [PERSISTENCE_FORMAT, MATERIALIZATION_FORMAT],
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": RETAIL_SHA256,
            "machine_bytes_adjudicate_upstream": True,
            "cross_lane_machine_proofs_consumed_without_reowning": True,
        },
        "wheel_layout": layout,
        "slot01": SLOTS,
        "exact_wheel_root_persistence": {
            "carrier_count": len(WHEEL_ROOT_CARRIERS),
            "carriers": WHEEL_ROOT_CARRIERS,
            "direct_memory_store_count": 0,
            "direct_push_count": 0,
            "direct_register_copy_count": len(wheel_copies),
            "direct_register_copies": wheel_copies,
            "new_persistent_gpr_alias_found": False,
        },
        "materialization_surface": {
            "fun00763570_loop_cursor_storage": loop["cursor_storage"],
            "fun00763570_nonstack_wheel_root_store_found": False,
            "fun00770e80_wheel_root_nonstack_store_count": 0,
            "fun00770e80_wheel_root_push_count": 0,
            "known_consumers": ["FUN_00755f80", "FUN_00760b50"],
        },
        "adjudication": {
            "p13a_slot01_known_wheel_root_materialization_subset_complete": True,
            "p13a_slot01_direct_exact_wheel_root_persistence_subset_complete": True,
            "p13a_slot01_exact_wheel_root_nonstack_store_found": False,
            "p13a_slot01_exact_wheel_root_push_found": False,
            "p13a_slot01_exact_wheel_root_new_persistent_gpr_alias_found": False,
            "interior_or_child_alias_storage_ruled_out": False,
            "reconstructed_wheel_pointers_ruled_out": False,
            "runtime_generated_or_copied_pointer_stores_ruled_out": False,
            "callbacks_and_indirect_entry_ruled_out": False,
            "stored_or_escaped_aliases_ruled_out": False,
            "p13a_slot0_complete": False,
            "p13a_slot1_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only the two known machine-proven HDVehicle-to-wheel-root materialization paths and direct exact-wheel-root store/push/immediate-GPR-copy persistence for the five wheel-root carriers.",
            "Slot0 and slot1 are normalized by exact wheel geometry: HDVehicle+0x400/+0xe80 plus local +0x538 equals HDVehicle+0x938/+0x13b8.",
            "Interior aliases such as wheel+0x80/wheel+0x7c8, dereferenced child pointers such as [wheel+0x420], reconstructed pointers, aggregate copies, runtime-generated pointers, callbacks and indirect entry remain open.",
            "No slot completion or aggregate P1.3 gate is promoted by this bounded pointer-persistence result.",
        ],
        "next_step": (
            "Consume the already-machine-bounded wheel interior/child alias tranches where slot-agnostic, "
            "then trace remaining reconstructed/runtime-generated pointers and callback/indirect-entry carriers "
            "before changing the global stored-or-escaped-alias gate."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--persistence",
        type=Path,
        default=Path("evidence/p1d_slot3_16carrier_direct_root_persistence.json"),
    )
    parser.add_argument(
        "--materialization",
        type=Path,
        default=Path("evidence/p1d_slot3_machine_wheel_root_materialization_closure.json"),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    payload = build(
        json.loads(args.persistence.read_text(encoding="utf-8")),
        json.loads(args.materialization.read_text(encoding="utf-8")),
    )
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
