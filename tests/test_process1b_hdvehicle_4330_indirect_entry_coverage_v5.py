import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "p1b_hdvehicle_4330_indirect_entry_coverage_v5.json"


def load():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_v5_contract_and_counts():
    data = load()
    assert data["format"] == "SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/5"
    assert data["supersedes"] == "SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/4"
    assert data["ready"] is True
    surface = data["surface"]
    assert surface["p1b_exact_carrier_count"] == 15
    assert surface["previous_bounded_coverage_class_count"] == 7
    assert surface["composed_coverage_class_count"] == 9
    assert surface["bounded_exact_carrier_hit_count"] == 0
    assert surface["statically_reachable_getprocaddress_callsite_count"] == 101
    assert surface["known_carrier_direct_copy_origin_count"] == 0


def test_global_gates_remain_fail_closed():
    adjudication = load()["adjudication"]
    assert adjudication["bounded_indirect_entry_coverage_composed"] is True
    assert adjudication["bounded_indirect_entry_exact_4330_carrier_hit_found"] is False
    assert adjudication["bounded_getprocaddress_storage_included"] is True
    assert adjudication["known_exact_carrier_value_copy_origin_subset_included"] is True
    assert adjudication["runtime_generated_or_copied_function_pointers_ruled_out"] is False
    assert adjudication["generic_function_pointer_stores_copies_ruled_out"] is False
    assert adjudication["memory_table_derived_carrier_pointers_ruled_out"] is False
    assert adjudication["runtime_computed_carrier_pointers_ruled_out"] is False
    assert adjudication["runtime_copied_or_encoded_carrier_pointers_ruled_out"] is False
    assert adjudication["runtime_patching_or_generated_code_ruled_out"] is False
    assert adjudication["indirect_entry_into_carriers_ruled_out"] is False
    assert adjudication["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adjudication["last_literal_0x004b86cf_rejected"] is False
    assert adjudication["p1_3_control_producer_complete"] is False
    assert adjudication["external_provider_count"] == 7
