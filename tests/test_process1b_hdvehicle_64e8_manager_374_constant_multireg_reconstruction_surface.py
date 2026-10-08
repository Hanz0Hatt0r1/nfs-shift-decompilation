import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_manager_374_constant_multireg_reconstruction_surface.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_authority_and_upstreams():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Manager374ConstantMultiRegisterReconstructionSurface/1"
    assert data["ready"] is True
    assert data["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert data["upstream_contracts"] == [
        "SHIFT.HDVehicle64e8Manager374SimpleArithmeticReconstructionSurface/1",
        "SHIFT.HDVehicle64e8Manager374StaticPointerOccurrenceSurface/1",
    ]


def test_constant_multireg_inventory_is_pinned_and_negative():
    scan = load_evidence()["scan"]
    assert scan["known_literal_production_count"] == 3
    assert scan["known_literal_sites"] == ["0x00489ae3", "0x00489afa", "0x00a9c5a0"]
    assert scan["constant_arithmetic_transition_count"] == 834
    assert scan["non_literal_exact_root_production_count"] == 0


def test_runtime_derived_reconstruction_remains_fail_closed():
    adj = load_evidence()["adjudication"]
    assert adj["constant_only_multi_register_reconstruction_surface_complete"] is True
    assert adj["constant_only_non_literal_manager_root_count"] == 0
    assert adj["surface_can_create_unrelated_manager_root"] is False
    assert adj["memory_load_or_opaque_runtime_reconstruction_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
