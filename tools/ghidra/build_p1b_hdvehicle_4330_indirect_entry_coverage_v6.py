#!/usr/bin/env python3
import json
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/6"
EXPECTED_PREV = "SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/5"
EXPECTED_SELF = "SHIFT.P1B.HDVehicle4330CarrierSelfPropagationClosure/1"
EXPECTED_PROVIDER_COUNT = 7


def load(path: Path):
    return json.loads(path.read_text())


def build(prev_path: Path, self_path: Path):
    prev = load(prev_path)
    selfc = load(self_path)
    assert prev["format"] == EXPECTED_PREV
    assert selfc["format"] == EXPECTED_SELF
    assert prev["ready"] is True
    assert selfc["ready"] is True
    assert prev["surface"]["p1b_exact_carrier_count"] == 15
    assert prev["surface"]["composed_coverage_class_count"] == 9
    assert prev["surface"]["bounded_exact_carrier_hit_count"] == 0
    assert selfc["surface"]["p1b_exact_carrier_count"] == 15
    assert selfc["surface"]["carrier_indirect_call_edge_count"] == 0
    assert selfc["surface"]["direct_known_carrier_value_copy_origin_count"] == 0
    return {
        "format": FORMAT,
        "version": 6,
        "ready": True,
        "owner": "Process 1B / P1.3B aggregate integration",
        "supersedes": EXPECTED_PREV,
        "upstream_contracts": [EXPECTED_PREV, EXPECTED_SELF],
        "surface": {
            "p1b_exact_carrier_count": 15,
            "previous_bounded_coverage_class_count": 9,
            "composed_coverage_class_count": 10,
            "bounded_exact_carrier_hit_count": 0,
            "carrier_self_propagation_outgoing_indirect_edge_count": 0,
            "carrier_self_propagation_direct_copy_origin_count": 0,
            "coverage_addition": {
                "class": "bounded exact-carrier self-propagation",
                "outgoing_indirect_edge_count": 0,
                "direct_exact_carrier_copy_origin_count": 0,
            },
        },
        "adjudication": {
            "bounded_indirect_entry_coverage_composed": True,
            "carrier_self_propagation_subset_included": True,
            "bounded_indirect_entry_exact_4330_carrier_hit_found": False,
            "indirect_entry_into_carriers_ruled_out": False,
            "runtime_generated_or_copied_function_pointers_ruled_out": False,
            "generic_function_pointer_stores_copies_ruled_out": False,
            "memory_table_derived_carrier_pointers_ruled_out": False,
            "runtime_patching_or_generated_code_ruled_out": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": EXPECTED_PROVIDER_COUNT,
        },
        "limits": [
            "This supersedes /5 by adding the bounded exact-carrier self-propagation subset.",
            "Incoming indirect entry, unrelated runtime-populated tables, cross-block/table-derived reconstruction, runtime patching and opaque/external pointer sources remain open.",
        ],
        "next_step": "Inventory unrelated runtime-populated function-pointer tables or bound incoming indirect-entry candidates before promoting global indirect-entry/store-copy gates.",
    }


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("previous")
    p.add_argument("self_propagation")
    p.add_argument("--output", required=True)
    a = p.parse_args()
    out = build(Path(a.previous), Path(a.self_propagation))
    Path(a.output).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
