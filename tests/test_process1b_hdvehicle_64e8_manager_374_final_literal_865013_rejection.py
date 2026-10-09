import json
from pathlib import Path

EVIDENCE = Path("evidence/hdvehicle_64e8_manager_374_final_literal_865013_rejection.json")


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_final_literal_site_is_pinned():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Manager374FinalLiteral865013Rejection/1"
    assert data["target"]["site"] == "0x00865013"
    assert data["target"]["function"] == "FUN_00864c10"
    assert data["target"]["store"] == "fstp dword [esi+0x374]"


def test_receiver_virtual_probe_has_no_stack_argument():
    data = load_evidence()
    flow = data["target_receiver_flow"]
    assert flow["first_stack_argument_capture"] == "0x00864c67 mov esi,[ebx+0x8]"
    assert "0x00864c89 mov eax,[eax+0x20]" in flow["virtual_probe"]
    assert "0x00864c94 call eax" in flow["virtual_probe"]
    assert flow["stack_argument_pushed_before_virtual_probe"] is False


def test_participants_manager_slot20_requires_stack_argument():
    data = load_evidence()
    manager = data["participants_manager_root"]
    assert manager["vptr"] == "0x00ab9190"
    assert manager["vslot_0x20_cell"] == "0x00ab91b0"
    assert manager["vslot_0x20_target"] == "FUN_006383c0"
    assert "0x006383c3 mov ecx,[ebp+0x8]" in manager["target_machine_abi"]
    assert "0x006383cc ret 4" in manager["target_machine_abi"]
    assert manager["requires_one_stack_argument"] is True


def test_identity_is_rejected_by_machine_abi_not_offset_equality():
    data = load_evidence()
    adjudication = data["identity_adjudication"]
    assert adjudication["manager_dispatch_stack_effect_compatible_with_callsite"] is False
    assert adjudication["esi_can_be_participants_manager_root_at_0x00864c94"] is False
    assert adjudication["site_0x00865013_can_write_manager_plus_0x374"] is False


def test_literal_surface_closes_but_project_remains_fail_closed():
    data = load_evidence()["adjudication"]
    assert data["literal_base_plus_0x374_receiver_surface_complete"] is True
    assert data["remaining_literal_manager_374_site_count"] == 0
    assert data["computed_address_manager_374_writer_surface_complete"] is False
    assert data["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert data["last_literal_0x004b86cf_rejected"] is False
    assert data["p1_3_control_producer_complete"] is False
    assert data["external_provider_count"] == 7
