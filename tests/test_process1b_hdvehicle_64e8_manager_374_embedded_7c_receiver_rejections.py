import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "hdvehicle_64e8_manager_374_embedded_7c_receiver_rejections.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text())


def test_parent_constructor_uses_only_fresh_heap_or_fixed_global_paths():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Manager374Embedded7cReceiverRejections/1"
    parent = data["parent_constructor"]
    assert parent["known_machine_entry_path_count"] == 3
    assert parent["child_0_receiver"] == "0x007c31a3 lea ecx,[esi+0x8]"
    assert parent["child_1_receiver"] == "0x007c320b lea ecx,[esi+0xfe8]"
    assert [p["callsite"] for p in parent["known_machine_entry_paths"]] == [
        "0x0076dfcc", "0x00798e74", "0x00a8ca65"
    ]
    assert [p.get("allocation_size") for p in parent["known_machine_entry_paths"][:2]] == ["0x3848", "0x3848"]
    assert parent["known_machine_entry_paths"][2]["receiver_transfer"] == "0x00a8ca60 mov ecx,0x00c1c568"


def test_two_literal_sites_are_not_participants_manager_receivers():
    data = load_evidence()
    rows = data["rejections"]
    assert [r["site"] for r in rows] == ["0x007c0fa0", "0x007c1ace"]
    assert rows[0]["receiver_identity"] == "FUN_007c3170 parent+0x8"
    assert rows[1]["receiver_identity"] == "FUN_007c3170 parent+0xfe8"
    assert rows[0]["fixed_global_receiver_if_static_path"] == "0x00c1c570"
    assert rows[1]["fixed_global_receiver_if_static_path"] == "0x00c1d550"
    assert all(r["receiver_equals_participants_manager"] is False for r in rows)


def test_worklist_reduces_10_to_8_and_gates_stay_fail_closed():
    data = load_evidence()
    adj = data["adjudication"]
    assert data["upstream"]["actionable_before_this_contract"] == 10
    assert adj["new_sites_closed_negative"] == 2
    assert adj["literal_receiver_worklist_before"] == 10
    assert adj["literal_receiver_worklist_after"] == 8
    assert adj["embedded_7c_receivers_can_be_participants_manager"] is False
    assert adj["computed_address_writer_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
