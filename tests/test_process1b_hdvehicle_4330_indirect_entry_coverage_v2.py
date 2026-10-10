import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "p1b_hdvehicle_4330_indirect_entry_coverage_v2.json"


def load():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_v2_updates_bounded_baseline_without_carrier_hits():
    data = load()
    assert data["format"] == "SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/2"
    assert data["supersedes"] == "SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/1"
    assert data["ready"] is True
    s = data["surface"]
    assert s["p1b_exact_carrier_count"] == 15
    assert s["composed_coverage_class_count"] == 4
    assert s["bounded_exact_carrier_hit_count"] == 0
    assert s["coverage"][2]["physical_callsite_count"] == 51
    assert s["coverage"][2]["possible_entrypoint_count"] == 36
    assert s["coverage"][3]["exact_carrier_rva_scalar_use_count"] == 0


def test_v2_keeps_global_gates_fail_closed():
    a = load()["adjudication"]
    assert a["bounded_indirect_entry_coverage_composed"] is True
    assert a["bounded_indirect_entry_exact_4330_carrier_hit_found"] is False
    assert a["bsearch_closed_and_included"] is True
    assert a["exact_imagebase_plus_exact_rva_immediate_seed_subset_included"] is True
    for key in (
        "runtime_generated_or_copied_function_pointers_ruled_out",
        "generic_function_pointer_stores_copies_ruled_out",
        "computed_or_encoded_code_pointers_ruled_out",
        "runtime_computed_carrier_pointers_ruled_out",
        "runtime_copied_or_encoded_carrier_pointers_ruled_out",
        "runtime_callback_registration_ruled_out",
        "remaining_callback_api_families_ruled_out",
        "indirect_entry_into_carriers_ruled_out",
        "global_runtime_derived_4330_alias_surface_complete",
        "manager_374_join_to_hdvehicle_4330_complete",
        "last_literal_0x004b86cf_rejected",
        "p1_3_control_producer_complete",
    ):
        assert a[key] is False
    assert a["external_provider_count"] == 7
