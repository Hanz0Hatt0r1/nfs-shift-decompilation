#!/usr/bin/env python3
"""Reuse the target-agnostic base/indexed writable .data near-transfer proof for P1B carriers."""
from __future__ import annotations
import argparse, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UPSTREAM = ROOT / "evidence" / "p1a_p13a_fun005ffc50_base_indexed_data_near_transfer.json"
FORMAT = "SHIFT.P1B.HDVehicle4330BaseIndexedWritableNearTransfer/1"


def build() -> dict:
    up = json.loads(UPSTREAM.read_text(encoding="utf-8"))
    assert up["format"] == "SHIFT.P1A.P13AFun005ffc50BaseIndexedDataNearTransfer/1"
    inv = up["inventory"]
    assert inv["base_indexed_data_load_count"] == 63
    assert inv["unique_effective_address_count"] == 51
    assert inv["same_register_indirect_transfer_count"] == 0
    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "authority": up["authority"],
        "upstream_contracts": [up["format"]],
        "surface": {
            "p1b_exact_carrier_count": 15,
            "decoded_instruction_count": inv["decoded_instruction_count"],
            "base_indexed_writable_data_load_count": inv["base_indexed_data_load_count"],
            "unique_effective_address_count": inv["unique_effective_address_count"],
            "destination_register_counts": inv["destination_register_counts"],
            "same_register_indirect_transfer_count": inv["same_register_indirect_transfer_count"],
            "exact_carrier_target_hit_count": 0,
            "termination_reason_counts": inv["termination_reason_counts"],
            "forward_window_decoded_instructions": up["scope"]["forward_window_decoded_instructions"],
        },
        "adjudication": {
            "base_indexed_writable_same_register_near_transfer_subset_complete": True,
            "base_indexed_writable_same_register_can_target_exact_p1b_carrier": False,
            "register_copy_or_transform_after_base_indexed_load_remains_open": True,
            "base_indexed_stack_spill_reload_remains_open": True,
            "base_indexed_inter_block_carry_remains_open": True,
            "indirect_entry_into_carriers_ruled_out": False,
            "runtime_generated_or_copied_function_pointers_ruled_out": False,
            "generic_function_pointer_stores_copies_ruled_out": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only same-register indirect CALL/JMP within the upstream 16-instruction straight-line window after exact base/index-addressed writable .data loads.",
            "Register copies/transforms, stack spills/reloads, inter-block carry, aliases, heap/runtime values and arbitrary mutation remain open.",
        ],
        "next_step": "Compose this near-transfer negative into P1B indirect-entry coverage, then follow copied/transformed/spilled base-indexed writable values.",
    }


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--output",type=Path); a=p.parse_args()
    text=json.dumps(build(),indent=2,sort_keys=True)+"\n"
    a.output.write_text(text,encoding="utf-8") if a.output else print(text,end="")
    return 0

if __name__ == "__main__": raise SystemExit(main())
