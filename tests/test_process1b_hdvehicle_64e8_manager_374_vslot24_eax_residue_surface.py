import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_manager_374_vslot24_eax_residue_surface.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_authority_and_exact_vslot_identity():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Manager374VSlot24EaxResidueSurface/1"
    assert data["ready"] is True
    assert data["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    obj = data["object_identity"]
    assert obj["vtable"] == "0x00ac1860"
    assert obj["slot_offset"] == "+0x24"
    assert obj["slot_cell"] == "0x00ac1884"
    assert obj["slot_target"] == "FUN_004d1640"
    assert obj["owner_store"] == "0x004689b1 [outer+0xc4c]=constructed object"


def test_slot_body_root_is_local_eax_residue_not_admitted_output():
    body = load_evidence()["slot_body"]
    assert body["manager_getter_callsite"] == "0x004d16e9"
    assert body["local_use"] == "0x004d16f0 [EAX+0x434]=0"
    assert body["eax_at_return_can_equal_manager_root"] is True
    assert body["eax_root_is_explicit_function_result"] is False
    assert body["machine_span_sha256"] == "033b9a5aa87e443eb84fcd1baf980ecaf4fb0f8ed82433a8b8fd4f4efead2c5c"


def test_exact_dispatch_clobbers_exact_root_value():
    dispatch = load_evidence()["exact_dispatch"]
    assert dispatch["callsite"] == "0x004b75bc"
    assert dispatch["post_call_clobber"] == "0x004b75be mov al,1"
    assert dispatch["exact_manager_root_preserved_after_dispatch"] is False
    assert dispatch["dispatch_span_sha256"] == "4625cd0eec35a453cb2a3a80a7b1dffb2dd42331cec226b15f94706eb2d0c7c3"


def test_frontier_stays_fail_closed_for_remaining_runtime_aliases():
    adj = load_evidence()["adjudication"]
    assert adj["vslot_24_identity_closed"] is True
    assert adj["slot_body_can_leave_manager_root_in_eax"] is True
    assert adj["exact_dispatch_preserves_exact_manager_root_return"] is False
    assert adj["vslot_24_can_export_exact_manager_root_to_its_observed_consumer"] is False
    assert adj["fun_0045b130_slot_0c_surface_complete"] is False
    assert adj["runtime_created_or_opaque_manager_root_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
