import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "p1b_hdvehicle_4330_runtime_callback_coverage_v4.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_callback_v4_counts_and_bsearch_delta():
    data = load_evidence()
    assert data["format"] == "SHIFT.P1B.HDVehicle4330RuntimeCallbackCoverage/4"
    assert data["supersedes"] == "SHIFT.P1B.HDVehicle4330RuntimeCallbackCoverage/3"
    assert data["ready"] is True
    surface = data["surface"]
    assert surface["closed_surface_count"] == 8
    assert surface["bounded_callback_capable_callsite_count"] == 51
    assert surface["unique_possible_callback_entrypoint_count"] == 36
    assert surface["exact_4330_carrier_entrypoint_hit_count"] == 0
    bsearch = [row for row in surface["coverage"] if row["surface"] == "CRT _bsearch comparators"]
    assert bsearch == [{"exact_4330_carrier_hit_count": 0, "physical_callsite_count": 2, "possible_entrypoint_count": 2, "surface": "CRT _bsearch comparators"}]
    assert "0x0053c280" in surface["possible_entrypoints"]
    assert "0x00a5df20" in surface["possible_entrypoints"]


def test_global_indirect_gates_remain_fail_closed():
    adj = load_evidence()["adjudication"]
    assert adj["bounded_runtime_callback_coverage_composed"] is True
    assert adj["bsearch_included_in_runtime_callback_baseline"] is True
    assert adj["bounded_runtime_callback_exact_4330_carrier_hit_found"] is False
    assert adj["runtime_callback_registration_ruled_out"] is False
    assert adj["generic_function_pointer_stores_copies_ruled_out"] is False
    assert adj["computed_or_encoded_code_pointers_ruled_out"] is False
    assert adj["remaining_callback_api_families_ruled_out"] is False
    assert adj["indirect_entry_into_carriers_ruled_out"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
