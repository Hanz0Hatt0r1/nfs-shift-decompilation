import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_manager_374_direct_singleton_reference_surface.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_authority_and_singleton():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Manager374DirectSingletonReferenceSurface/1"
    assert data["ready"] is True
    assert data["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert data["manager_singleton"]["address"] == "0x00bc9fc0"
    assert data["manager_singleton"]["target_offset"] == "+0x374"


def test_exact_three_immediate_references_are_pinned():
    surface = load_evidence()["whole_image_immediate_reference_surface"]
    assert surface["reference_count"] == 3
    refs = surface["references"]
    assert {r["instruction_address"] for r in refs} == {"0x00489ae3", "0x00489afa", "0x00a9c5a0"}
    assert all(r["creates_independent_manager_root"] is False for r in refs)


def test_cleanup_thunk_is_not_runtime_reconstruction():
    refs = load_evidence()["whole_image_immediate_reference_surface"]["references"]
    cleanup = next(r for r in refs if r["instruction_address"] == "0x00a9c5a0")
    assert cleanup["role"] == "registered static cleanup thunk"
    assert "0x00489aed" in cleanup["registered_from"]
    assert "FUN_004891b0" in cleanup["instruction"]


def test_frontier_stays_fail_closed():
    adj = load_evidence()["adjudication"]
    assert adj["direct_singleton_immediate_reference_count"] == 3
    assert adj["independent_runtime_singleton_reconstruction_site_count"] == 0
    assert adj["direct_singleton_reconstruction_surface_complete"] is True
    assert adj["surface_can_create_new_manager_plus_0x374_value"] is False
    assert adj["object_field_or_global_persistence_of_manager_root_complete"] is False
    assert adj["non_immediate_manager_root_reconstruction_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
