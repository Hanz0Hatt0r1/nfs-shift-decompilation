import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "p1b_hdvehicle_4330_carrier_self_propagation_closure.json"


def load():
    return json.loads(EVIDENCE.read_text())


def test_contract_and_counts():
    data = load()
    assert data["format"] == "SHIFT.P1B.HDVehicle4330CarrierSelfPropagationClosure/1"
    assert data["ready"] is True
    s = data["surface"]
    assert s["p1b_exact_carrier_count"] == 15
    assert s["carrier_indirect_call_edge_count"] == 0
    assert s["source_address_taken_carrier_count"] == 0
    assert s["source_noncall_carrier_value_use_count"] == 0
    assert s["direct_known_carrier_value_copy_origin_count"] == 0


def test_only_bounded_gate_advances():
    a = load()["adjudication"]
    assert a["bounded_carrier_self_propagation_subset_complete"] is True
    assert a["exact_carrier_outgoing_indirect_dispatch_found"] is False
    assert a["exact_carrier_direct_value_escape_or_copy_origin_found"] is False
    assert a["indirect_entry_into_carriers_ruled_out"] is False
    assert a["runtime_created_or_table_derived_carrier_values_ruled_out"] is False
    assert a["runtime_generated_or_copied_function_pointers_ruled_out"] is False
    assert a["generic_function_pointer_stores_copies_ruled_out"] is False
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["last_literal_0x004b86cf_rejected"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
