import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "hdvehicle_64e8_manager_2a0_direct_surface.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_and_authority():
    p = _payload()
    assert p["format"] == "SHIFT.HDVehicle64e8Manager2a0DirectSurface/1"
    assert p["ready"] is True
    assert p["authority"]["platform"] == "PC retail 1.02"
    assert p["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"


def test_bounded_surface_shape():
    p = _payload()["bounded_surface"]
    assert p["direct_manager_receiver_calls"] == 44
    assert p["direct_manager_receiver_unique_targets"] == 12
    assert p["manager_vtable_slots"] == 18
    assert p["manager_vtable_unique_targets"] == 17
    assert p["functions_with_literal_plus_0x2a0_reference"] == ["FUN_00488a60"]
    assert p["vtable_targets_with_literal_plus_0x2a0_reference"] == []


def test_fun_00488a60_is_iteration_path():
    p = _payload()["fun_00488a60"]
    assert "0x00488a6a lea esi,[ecx+0x2a0]" in p["instructions"]
    assert "0x00488a80 call FUN_0052cce0" in p["instructions"]
    assert "0x00488aba call FUN_0052cce0" in p["instructions"]
    assert p["container_store_found"] is False


def test_iterator_helper_does_not_directly_store_container_receiver():
    p = _payload()["iterator_helper"]
    assert p["entry"] == "FUN_0052cce0"
    assert p["delegate"] == "FUN_0052ca50"
    assert p["delegate_writes_stack_iterator_descriptor"] is True
    assert p["delegate_direct_store_to_container_receiver"] is False


def test_fail_closed_gates():
    p = _payload()["adjudication"]
    assert p["direct_manager_root_registration_found"] is False
    assert p["manager_vtable_registration_found"] is False
    assert p["bounded_direct_and_vtable_registration_surface_exhausted"] is True
    assert p["escaped_subobject_alias_registration_still_possible"] is True
    assert p["manager_2a0_entry_identity_to_hdvehicle_4330_complete"] is False
    assert p["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert p["retail_input_control_provenance_proven"] is False
    assert p["p1_3_control_producer_complete"] is False
    assert p["external_provider_count"] == 7
