import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "p1b_hdvehicle_4330_known_carrier_copy_origin_closure.json"


def load():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_and_counts():
    data = load()
    assert data["format"] == "SHIFT.P1B.HDVehicle4330KnownCarrierValueCopyOriginClosure/1"
    assert data["ready"] is True
    surface = data["surface"]
    assert surface["p1b_exact_carrier_count"] == 15
    assert surface["source_exact_carrier_symbol_occurrence_count"] == 40
    assert surface["source_address_taken_carrier_count"] == 0
    assert surface["source_noncall_carrier_value_use_count"] == 0
    assert surface["bounded_seed_domain_count"] == 8
    assert surface["bounded_seed_exact_carrier_hit_count"] == 0
    assert surface["direct_known_carrier_value_copy_origin_count"] == 0


def test_only_scoped_copy_origin_gate_advances():
    adjudication = load()["adjudication"]
    assert adjudication["known_exact_carrier_value_copy_origin_subset_complete"] is True
    assert adjudication["known_exact_carrier_value_direct_store_or_copy_seed_found"] is False
    assert adjudication["bounded_known_carrier_value_copy_path_can_seed_runtime_pointer_table"] is False
    assert adjudication["runtime_generated_or_copied_function_pointers_ruled_out"] is False
    assert adjudication["generic_function_pointer_stores_copies_ruled_out"] is False
    assert adjudication["runtime_computed_carrier_pointers_ruled_out"] is False
    assert adjudication["runtime_copied_or_encoded_carrier_pointers_ruled_out"] is False
    assert adjudication["indirect_entry_into_carriers_ruled_out"] is False
    assert adjudication["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adjudication["last_literal_0x004b86cf_rejected"] is False
    assert adjudication["p1_3_control_producer_complete"] is False
    assert adjudication["external_provider_count"] == 7
