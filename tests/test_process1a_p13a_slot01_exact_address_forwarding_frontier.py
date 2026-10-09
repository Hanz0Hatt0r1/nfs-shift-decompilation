import json
from pathlib import Path

EVIDENCE = Path("evidence/p1a_p13a_slot01_exact_address_forwarding_frontier.json")


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_exact_scalar_materializer_surface_is_bounded():
    data = load_evidence()
    assert data["format"] == "SHIFT.P1A.P13ASlot01ExactAddressForwardingFrontier/1"
    surface = data["whole_image_exact_scalar_surface"]
    assert surface["slot0_0x938"]["exact_scalar_use_count"] == 6
    assert surface["slot0_0x938"]["address_materializer_count"] == 0
    assert surface["slot1_0x13b8"]["exact_scalar_use_count"] == 35
    assert surface["slot1_0x13b8"]["address_materializer_count"] == 3
    assert surface["slot1_0x13b8"]["address_materializers"] == [
        "0x007726b3 lea eax,[esi+0x13b8]",
        "0x00772763 lea edx,[esi+0x13b8]",
        "0x007bfaa0 lea ecx,[edi+0x13b8]",
    ]


def test_slot1_forwarding_candidates_do_not_write_selected_target():
    data = load_evidence()
    candidates = {row["site"]: row for row in data["slot1_materializer_adjudication"]}
    assert candidates["0x007726b3"]["callee_writes_target_base_qword"] is False
    assert candidates["0x00772763"]["callee_writes_target_base_qword"] is False

    real_writer = candidates["0x007bfaa0"]
    assert real_writer["callee_writes_target_base_qword"] is True
    prov = real_writer["destination_provenance"]
    assert prov["fun_007bf790_direct_caller_count"] == 1
    assert prov["hdvehicle_call_group"]["third_argument"] == "HDVehicle+0x4330"
    assert prov["hdvehicle_call_group"]["normalized_qword_destination"] == "HDVehicle+0x56e8"
    assert prov["hdvehicle_call_group"]["equals_selected_hdvehicle_plus_0x13b8"] is False
    assert prov["non_hdvehicle_call_group"]["third_argument"] == "stack local EBP-0x238c"
    assert prov["non_hdvehicle_call_group"]["equals_selected_hdvehicle_plus_0x13b8"] is False


def test_frontier_reduces_without_opening_slot_or_global_gates():
    a = load_evidence()["adjudication"]
    assert a["slot0_exact_displacement_address_materializer_surface_exhausted"] is True
    assert a["slot1_exact_displacement_address_materializer_surface_exhausted"] is True
    assert a["slot1_exact_displacement_callee_writers_rejected"] is True
    assert a["slot0_selected_root_alias_callee_bulk_copy_complete"] is False
    assert a["slot1_selected_root_alias_callee_bulk_copy_complete"] is False
    assert a["p13a_slot0_complete"] is False
    assert a["p13a_slot1_complete"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
