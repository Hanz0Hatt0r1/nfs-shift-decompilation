#!/usr/bin/env python3
import json
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330CarrierSelfPropagationClosure/1"
EXPECTED_INDIRECT = "SHIFT.P1B.HDVehicle4330ExactCarrierIndirectCallSurface/1"
EXPECTED_COPY = "SHIFT.P1B.HDVehicle4330KnownCarrierValueCopyOriginClosure/1"
EXPECTED_PROVIDER_COUNT = 7


def load(path: Path):
    return json.loads(path.read_text())


def build(indirect_path: Path, copy_path: Path):
    indirect = load(indirect_path)
    copy = load(copy_path)
    assert indirect["format"] == EXPECTED_INDIRECT
    assert copy["format"] == EXPECTED_COPY
    assert indirect["ready"] is True
    assert copy["ready"] is True
    assert indirect["carrier_set"]["count"] == 15
    assert indirect["indirect_surface"]["carrier_indirect_call_edge_count"] == 0
    assert copy["surface"]["p1b_exact_carrier_count"] == 15
    assert copy["surface"]["source_address_taken_carrier_count"] == 0
    assert copy["surface"]["source_noncall_carrier_value_use_count"] == 0
    assert copy["surface"]["direct_known_carrier_value_copy_origin_count"] == 0
    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "upstream_contracts": [EXPECTED_INDIRECT, EXPECTED_COPY],
        "surface": {
            "p1b_exact_carrier_count": 15,
            "carrier_indirect_call_edge_count": 0,
            "source_address_taken_carrier_count": 0,
            "source_noncall_carrier_value_use_count": 0,
            "direct_known_carrier_value_copy_origin_count": 0,
        },
        "adjudication": {
            "bounded_carrier_self_propagation_subset_complete": True,
            "exact_carrier_outgoing_indirect_dispatch_found": False,
            "exact_carrier_direct_value_escape_or_copy_origin_found": False,
            "indirect_entry_into_carriers_ruled_out": False,
            "runtime_created_or_table_derived_carrier_values_ruled_out": False,
            "runtime_generated_or_copied_function_pointers_ruled_out": False,
            "generic_function_pointer_stores_copies_ruled_out": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": EXPECTED_PROVIDER_COUNT,
        },
        "limits": [
            "This closes only self-propagation from the already-proven canonical 15 P1B carrier functions.",
            "Incoming indirect entry, callbacks registered outside the carrier set, runtime-created/table-derived carrier values, runtime patching and opaque external pointer sources remain open.",
            "The indirect-call input is a Ghidra SQLite navigation index; semantic carrier identity remains established by merged retail machine contracts.",
        ],
        "next_step": "Inventory unrelated runtime-populated function-pointer tables or bound incoming indirect-entry candidates before promoting global pointer-store/copy or indirect-entry gates.",
    }


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("indirect")
    p.add_argument("copy")
    p.add_argument("--output", required=True)
    a = p.parse_args()
    out = build(Path(a.indirect), Path(a.copy))
    Path(a.output).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
