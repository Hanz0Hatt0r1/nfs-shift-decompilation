import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
EVIDENCE = ROOT / "evidence" / "p1b_hdvehicle_4330_carrier_seed_provenance_coverage.json"


def load():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_seed_coverage_contract_and_counts():
    data = load()
    assert data["format"] == "SHIFT.P1B.HDVehicle4330CarrierSeedProvenanceCoverage/1"
    assert data["ready"] is True
    surface = data["surface"]
    assert surface["p1b_exact_carrier_count"] == 15
    assert surface["composed_seed_class_count"] == 4
    assert surface["exact_carrier_seed_hit_count"] == 0
    assert [row["exact_carrier_hit_count"] for row in surface["classes"]] == [0, 0, 0, 0]
    assert surface["classes"][2]["physical_callsite_count"] == 51
    assert surface["classes"][2]["possible_entrypoint_count"] == 36
    assert surface["classes"][3]["carrier_superset_count"] == 16
    assert surface["classes"][3]["exact_carrier_rva_scalar_use_count"] == 0


def test_bounded_seed_gates_promote_but_global_gates_remain_closed():
    adj = load()["adjudication"]
    assert adj["bounded_known_carrier_seed_provenance_composed"] is True
    assert adj["static_source_visible_seed_classes_complete"] is True
    assert adj["canonical_computed_loader_seed_classes_complete"] is True
    assert adj["bounded_runtime_callback_seed_classes_complete"] is True
    assert adj["exact_imagebase_plus_exact_rva_immediate_seed_subset_complete"] is True
    assert adj["known_bounded_seed_exact_carrier_hit_found"] is False

    for key in (
        "runtime_generated_or_copied_function_pointers_ruled_out",
        "generic_function_pointer_stores_copies_ruled_out",
        "computed_or_encoded_code_pointers_ruled_out",
        "runtime_computed_carrier_pointers_ruled_out",
        "runtime_copied_or_encoded_carrier_pointers_ruled_out",
        "runtime_callback_registration_ruled_out",
        "indirect_entry_into_carriers_ruled_out",
        "global_runtime_derived_4330_alias_surface_complete",
        "manager_374_join_to_hdvehicle_4330_complete",
        "last_literal_0x004b86cf_rejected",
        "p1_3_control_producer_complete",
    ):
        assert adj[key] is False
    assert adj["external_provider_count"] == 7
