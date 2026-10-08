import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "hdvehicle_64e8_manager_374_owner_child_818157_rejection.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text())


def test_direct_call_surface_and_physical_ecx_preservation_are_pinned():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Manager374OwnerChild818157Rejection/1"
    calls = data["direct_call_surface"]
    assert calls["callsite_count"] == 2
    assert calls["callsites"] == ["0x0081851f", "0x0081860f"]
    preserve = data["physical_receiver_preservation"]
    assert preserve["intermediate_call"] == "FUN_00816570"
    assert preserve["nested_call"] == "0x008165c9 call FUN_00816550"
    assert preserve["intermediate_post_call_use"] == "0x008165d1 mov [ecx+0x37c],eax"
    assert "never writes ECX" in preserve["nested_behavior"]


def test_target_is_same_non_manager_owner_child_and_writes_zero():
    data = load_evidence()
    target = data["target"]
    assert target["site"] == "0x00818157"
    assert target["function_mnemonic_sha256"] == "bdf034dc13276fada174c9e1f1240641c4d3d7d2623d0cb2118a67825139ec79"
    assert target["stored_value"].startswith("zero")
    owner = data["owner_identity"]
    assert owner["receiver_vptr"] == "0x00b16158"
    assert owner["receiver_is_participants_manager_root"] is False
    assert owner["receiver_is_participants_manager_subobject"] is False


def test_worklist_reduces_8_to_7_and_fail_closed_gates_remain():
    data = load_evidence()
    adj = data["adjudication"]
    assert adj["site_closed_negative"] is True
    assert adj["literal_receiver_worklist_before"] == 8
    assert adj["literal_receiver_worklist_after"] == 7
    assert adj["computed_address_writer_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
