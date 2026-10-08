import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_manager_374_simple_arithmetic_reconstruction_surface.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_authority_and_upstream():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Manager374SimpleArithmeticReconstructionSurface/1"
    assert data["ready"] is True
    assert data["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert data["upstream_contract"] == "SHIFT.HDVehicle64e8Manager374DirectSingletonReferenceSurface/1"


def test_whole_text_simple_arithmetic_inventory_is_pinned():
    scan = load_evidence()["scan"]
    assert scan["mov_immediate_seed_count"] == 38128
    assert scan["known_exact_literal_seed_count"] == 3
    assert scan["same_register_arithmetic_transition_count"] == 499
    assert scan["non_literal_chains_reconstructing_exact_singleton_count"] == 0
    assert scan["known_literal_sites"] == ["0x00489ae3", "0x00489afa", "0x00a9c5a0"]


def test_simple_arithmetic_surface_closes_but_complex_dataflow_remains_open():
    adj = load_evidence()["adjudication"]
    assert adj["simple_immediate_arithmetic_reconstruction_surface_complete"] is True
    assert adj["simple_non_literal_reconstruction_site_count"] == 0
    assert adj["surface_can_create_unrelated_manager_root"] is False
    assert adj["getter_result_persistence_surface_complete"] is True
    assert adj["direct_singleton_immediate_surface_complete"] is True
    assert adj["load_or_table_derived_reconstruction_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
