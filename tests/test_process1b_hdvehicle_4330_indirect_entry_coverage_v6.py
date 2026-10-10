import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "p1b_hdvehicle_4330_indirect_entry_coverage_v6.json"


def load():
    return json.loads(EVIDENCE.read_text())


def test_contract_and_counts():
    data = load()
    assert data["format"] == "SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/6"
    assert data["ready"] is True
    assert data["supersedes"] == "SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/5"
    s = data["surface"]
    assert s["p1b_exact_carrier_count"] == 15
    assert s["previous_bounded_coverage_class_count"] == 9
    assert s["composed_coverage_class_count"] == 10
    assert s["bounded_exact_carrier_hit_count"] == 0
    assert s["carrier_self_propagation_outgoing_indirect_edge_count"] == 0
    assert s["carrier_self_propagation_direct_copy_origin_count"] == 0


def test_global_gates_remain_fail_closed():
    a = load()["adjudication"]
    assert a["bounded_indirect_entry_coverage_composed"] is True
    assert a["carrier_self_propagation_subset_included"] is True
    assert a["bounded_indirect_entry_exact_4330_carrier_hit_found"] is False
    assert a["indirect_entry_into_carriers_ruled_out"] is False
    assert a["runtime_generated_or_copied_function_pointers_ruled_out"] is False
    assert a["generic_function_pointer_stores_copies_ruled_out"] is False
    assert a["memory_table_derived_carrier_pointers_ruled_out"] is False
    assert a["runtime_patching_or_generated_code_ruled_out"] is False
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["last_literal_0x004b86cf_rejected"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
