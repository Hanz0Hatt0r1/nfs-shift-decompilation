#!/usr/bin/env python3
"""Compose bounded P1B carrier recovery over direct absolute writable .data transfers."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPOSITION = ROOT / "evidence" / "p1a_p13a_fun005ffc50_direct_absolute_writable_slots.json"
PAIR = ROOT / "evidence" / "p1a_p13a_fun005ffc50_writable_callback_pair.json"
NVAPI = ROOT / "evidence" / "p1a_p13a_fun005ffc50_nvapi_writable_table.json"
FORMAT = "SHIFT.P1B.HDVehicle4330DirectAbsoluteWritableIndirectRecovery/1"
CARRIERS = {
    "0x00769520", "0x0076b130", "0x0076df50", "0x00768a4d", "0x00756050",
    "0x00772200", "0x00772570", "0x007c3b00", "0x0076b280", "0x007618f0",
    "0x00769640", "0x007567a0", "0x00756bb0", "0x00771db0", "0x00771e10",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build() -> dict:
    comp, pair, nvapi = load(COMPOSITION), load(PAIR), load(NVAPI)
    assert comp["format"] == "SHIFT.P1A.P13AFun005ffc50DirectAbsoluteWritableTransferComposition/1"
    assert pair["format"] == "SHIFT.P1A.P13AFun005ffc50WritableCallbackPairStaticProvenance/1"
    assert nvapi["format"] == "SHIFT.P1A.P13AFun005ffc50NvapiWritableDispatchTable/1"

    inv = comp["direct_absolute_writable_transfer_inventory"]
    assert inv["unique_slot_count"] == 259 and inv["transfer_count"] == 334
    assert inv["all_unique_slots_partitioned"] is True

    wp = pair["writable_callback_pair"]
    callback_values = set(wp["direct_static_slot_A_candidate_values"]) | set(wp["direct_static_slot_B_candidate_values"])
    assert len(callback_values) == 6
    callback_hits = sorted(callback_values & CARRIERS)

    fixed_rows = inv["groups"]["fixed_bridge_slots"]["rows"]
    fixed_values = {row["initial_target"] for row in fixed_rows.values()}
    assert sum(row["direct_absolute_writer_count"] for row in fixed_rows.values()) == 0
    fixed_hits = sorted(fixed_values & CARRIERS)

    nt = nvapi["nvapi_table"]
    assert nt["record_count"] == 255 and nt["direct_table_indirect_transfer_count"] == 255
    assert nt["module_name"].lower() == "nvapi.dll"
    assert nt["query_symbol"] == "nvapi_QueryInterface"
    nvapi_initial = nt["initial_pointer"]
    nvapi_initial_hits = [nvapi_initial] if nvapi_initial in CARRIERS else []

    bounded_values = callback_values | fixed_values | {nvapi_initial}
    bounded_hits = sorted(bounded_values & CARRIERS)
    assert not bounded_hits

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": comp["authority"]["retail_executable_sha256"],
        },
        "upstream_contracts": [comp["format"], pair["format"], nvapi["format"]],
        "carrier_set": {"count": len(CARRIERS), "addresses": sorted(CARRIERS)},
        "surface": {
            "direct_absolute_writable_transfer_count": inv["transfer_count"],
            "unique_writable_slot_count": inv["unique_slot_count"],
            "fixed_bridge_slot_count": 2,
            "fixed_bridge_transfer_count": 2,
            "fixed_bridge_initial_targets": sorted(fixed_values),
            "fixed_bridge_direct_absolute_writer_count": 0,
            "fixed_bridge_exact_carrier_hit_count": len(fixed_hits),
            "callback_pair_slot_count": 2,
            "callback_pair_transfer_count": 77,
            "callback_pair_direct_static_candidate_value_count": len(callback_values),
            "callback_pair_direct_static_candidate_values": sorted(callback_values),
            "callback_pair_exact_carrier_hit_count": len(callback_hits),
            "nvapi_slot_count": nt["record_count"],
            "nvapi_transfer_count": nt["direct_table_indirect_transfer_count"],
            "nvapi_initial_internal_stub": nvapi_initial,
            "nvapi_initial_exact_carrier_hit_count": len(nvapi_initial_hits),
            "nvapi_runtime_value_provider": "external nvapi_QueryInterface",
            "bounded_internal_or_static_candidate_value_count": len(bounded_values),
            "bounded_internal_or_static_exact_carrier_hit_count": len(bounded_hits),
        },
        "adjudication": {
            "direct_absolute_writable_indirect_slot_inventory_complete": True,
            "bounded_internal_static_provider_subset_complete": True,
            "bounded_internal_static_provider_exact_carrier_hit_found": False,
            "nvapi_external_runtime_provider_remains_open": True,
            "callback_pair_alias_or_indirect_writers_remain_open": True,
            "register_loaded_or_base_indexed_writable_targets_remain_open": True,
            "indirect_entry_into_carriers_ruled_out": False,
            "runtime_generated_or_copied_function_pointers_ruled_out": False,
            "generic_function_pointer_stores_copies_ruled_out": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This reuses the complete direct absolute writable .data transfer inventory but closes only bounded internal/static value provenance for those slots.",
            "Nonzero NVAPI table values come from external nvapi_QueryInterface and are intentionally not reclassified as internal carrier negatives without runtime module/provider evidence.",
            "Alias/indirect writers, register-loaded/base-indexed writable pointers, runtime mutation and other writable-memory target classes remain open.",
        ],
        "next_step": "Compose this bounded writable-data target recovery into P1B indirect-entry coverage, then continue register-loaded/base-indexed and alias-writer target provenance.",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    text = json.dumps(build(), indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
