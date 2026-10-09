import json
from pathlib import Path

EVIDENCE = Path("evidence/hdvehicle_64e8_manager_374_direct_write_dsp_rejection.json")


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_direct_write_target_and_owner_are_pinned():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Manager374DirectWriteDspRejection/1"
    assert data["target"]["site"] == "0x00985bd3"
    assert data["target"]["function"] == "FUN_00985bc0"
    assert data["descriptor_owner"]["descriptor_base"] == "0x00b98c88"
    assert data["descriptor_owner"]["callback"] == "0x0093fa0f"
    assert data["descriptor_owner"]["descriptor_size_field"] == "0x00b98cf8 = 0x76c"


def test_exact_receiver_chain_is_complete():
    data = load_evidence()
    chain = data["machine_receiver_chain"]
    assert "0x0093fa13 lea eax,[arg1-0x1c]" in chain
    assert "0x0093f5d4 lea ebx,[esi+0x12c]" in chain
    assert "0x00986b88 call FUN_00985bc0" in chain
    assert "0x00985bd3 add esi,0x374" in chain
    calls = data["call_surface"]
    assert calls["FUN_00986a67_direct_caller_count"] == 1
    assert calls["FUN_00985bc0_direct_caller_count"] == 1


def test_receiver_is_not_promoted_from_numeric_offset():
    identity = load_evidence()["identity_adjudication"]
    assert identity["receiver_expression"] == "descriptor callback state (arg1-0x1c) + 0x12c"
    assert identity["receiver_is_participants_manager_root"] is False
    assert identity["receiver_is_participants_manager_subobject"] is False
    assert identity["site_can_write_participants_manager_plus_0x374"] is False
    assert identity["numeric_offset_used_as_identity_evidence"] is False


def test_remaining_frontier_stays_fail_closed():
    a = load_evidence()["adjudication"]
    assert a["direct_write_through_computed_candidate_complete"] is True
    assert a["direct_write_through_computed_candidate_rejected"] is True
    assert a["remaining_computed_runtime_path_count"] == 18
    assert a["returned_pointer_escape_complete"] is False
    assert a["callee_forwarding_surface_complete"] is False
    assert a["computed_address_manager_374_writer_surface_complete"] is False
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["last_literal_0x004b86cf_rejected"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
