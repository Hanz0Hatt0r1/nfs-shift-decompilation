import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_constant_4330_reconstruction_surface.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_authority_and_target():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Constant4330ReconstructionSurface/1"
    assert data["ready"] is True
    assert data["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert data["upstream_contract"] == "SHIFT.HDVehicle64e8Static4330PointerOccurrenceSurface/1"
    assert data["target"]["subobject_address"] == "0x00c17a30"


def test_constant_reconstruction_inventory_is_pinned_and_negative():
    scan = load_evidence()["scan"]
    assert scan["mov_immediate_seed_count"] == 38128
    assert scan["known_exact_literal_production_count"] == 4
    assert scan["known_literal_sites"] == ["0x00702715", "0x0070274d", "0x00702776", "0x007027ac"]
    assert scan["same_register_arithmetic_transition_count"] == 499
    assert scan["same_register_non_literal_exact_target_count"] == 0
    assert scan["constant_multi_register_transition_count"] == 834
    assert scan["constant_multi_register_non_literal_exact_target_count"] == 0


def test_runtime_derived_alias_frontier_remains_fail_closed():
    adj = load_evidence()["adjudication"]
    assert adj["constant_only_4330_reconstruction_surface_complete"] is True
    assert adj["constant_only_non_literal_4330_production_count"] == 0
    assert adj["surface_creates_new_hdvehicle_4330_alias"] is False
    assert adj["static_exact_4330_pointer_cell_surface_complete"] is True
    assert adj["runtime_memory_or_opaque_4330_alias_surface_complete"] is False
    assert adj["global_non_literal_hdvehicle_64e8_writer_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
