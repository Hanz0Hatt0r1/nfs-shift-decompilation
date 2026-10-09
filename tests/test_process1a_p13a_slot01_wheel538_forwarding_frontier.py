import json
from pathlib import Path

EVIDENCE = Path("evidence/p1a_p13a_slot01_wheel538_forwarding_frontier.json")


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_local_538_surface_is_exact_and_bounded():
    data = load_evidence()
    assert data["format"] == "SHIFT.P1A.P13ASlot01Wheel538ForwardingFrontier/1"
    assert data["consumer"]["receiver"] == "HDVehicle+0x400+slot*0xa80"
    assert data["consumer"]["local_field"] == "+0x538"
    surface = data["whole_image_surface"]
    assert surface["exact_0x538_scalar_use_count"] == 43
    assert surface["positive_address_materializer_count"] == 4
    assert surface["positive_address_materializers"] == [
        "0x006c1b8a lea ebx,[ecx+0x538]",
        "0x008fe259 lea ecx,[esi+0x538]",
        "0x008fe2c4 lea ebx,[esi+0x538]",
        "0x00958c28 lea eax,[ebx+0x538]",
    ]
    assert surface["direct_qword_store_existing_rejection"]["matches_consumer_slots"] is False


def test_all_four_materializers_are_negative_for_selected_wheel_f64():
    data = load_evidence()
    candidates = {row["site"]: row for row in data["materializer_adjudication"]}
    assert candidates["0x006c1b8a"]["forwards_materialized_pointer_as_write_destination"] is False
    assert candidates["0x006c1b8a"]["writes_qword_at_materialized_base"] is False
    assert candidates["0x008fe259"]["callee_receiver_store_count"] == 0
    assert candidates["0x008fe259"]["writes_qword_at_materialized_base"] is False

    pool = candidates["0x008fe2c4"]
    assert pool["writes_materialized_base"] is True
    assert pool["target_function_direct_caller_count"] == 1
    assert pool["receiver_provenance"]["allocator_state_materializer"].endswith("= 0x00c2b1ec")
    assert pool["receiver_provenance"]["constructor_vptr_store"] == "0x008fe2b9 mov [esi],0x00b35e6c"
    assert pool["receiver_provenance"]["receiver_is_hdvehicle_wheel_runtime"] is False

    codec = candidates["0x00958c28"]
    assert codec["call_shape"]["writer_capable"] is True
    assert codec["call_shape"]["count"] == 64
    assert codec["receiver_provenance"]["descriptor_name"] == "FMOD IT Codec"
    assert codec["receiver_provenance"]["receiver_is_hdvehicle_wheel_runtime"] is False


def test_frontier_reduces_but_slot_and_global_gates_remain_closed():
    a = load_evidence()["adjudication"]
    assert a["wheel_local_0x538_positive_materializer_surface_exhausted"] is True
    assert a["wheel_local_0x538_materializer_writers_rejected"] is True
    assert a["slot0_selected_root_alias_callee_bulk_copy_complete"] is False
    assert a["slot1_selected_root_alias_callee_bulk_copy_complete"] is False
    assert a["p13a_slot0_complete"] is False
    assert a["p13a_slot1_complete"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
