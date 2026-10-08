import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "fun_00755950_remaining_slot_direct_writer_frontier.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_and_targets():
    p = _payload()
    assert p["format"] == "SHIFT.Fun00755950RemainingSlotDirectWriterFrontier/1"
    assert p["ready"] is True
    assert p["targets"] == {
        "slot0": "HDVehicle+0x938",
        "slot1": "HDVehicle+0x13b8",
        "slot3": "HDVehicle+0x28b8",
    }


def test_slot0_candidates_rejected_by_owner_or_base_normalization():
    s = _payload()["slot0"]
    assert len(s["direct_literal_candidates"]) == 2
    assert s["direct_literal_candidates"][0]["function"] == "FUN_00791020"
    assert s["direct_literal_candidates"][0]["adjudication"] == "rejected"
    c = s["direct_literal_candidates"][1]
    assert c["function"] == "FUN_007572f0"
    assert c["store"] == "0x007576b0 fstp f32 [EDI+0x938]"
    assert c["normalized_destination"] == "entry_root+0xd38+slot_index*0xa80"
    assert c["same_as_entry_root_plus_0x938"] is False
    assert s["remaining_direct_literal_root_candidate"] is False


def test_slot1_qword_candidate_is_vehicle_load_data_collision():
    s = _payload()["slot1"]
    c = s["direct_qword_literal_candidate"]
    assert c["store"] == "0x007c4984 fstp qword [ESI+0x13b8]"
    assert c["receiver_proof"] == "0x007c3b21 ESI = ECX = VehicleLoadData"
    assert c["normalized_destination"] == "VehicleLoadData+0x13b8"
    assert c["same_as_selected_hdvehicle_plus_0x13b8"] is False
    assert s["remaining_direct_qword_root_candidate"] is False


def test_slot3_has_no_direct_literal_store():
    s = _payload()["slot3"]
    assert s["full_pe_direct_literal_store_count"] == 0
    assert s["remaining_direct_literal_root_candidate"] is False
    assert s["next_writer_class"] == "alias/callee/bulk-copy"


def test_fail_closed_p1_3_gate():
    a = _payload()["adjudication"]
    assert a["slot0_direct_literal_surface_exhausted"] is True
    assert a["slot1_direct_qword_literal_surface_exhausted"] is True
    assert a["slot3_direct_literal_surface_exhausted"] is True
    assert a["remaining_slots_require_alias_or_callee_provenance"] is True
    assert a["retail_input_control_provenance_proven"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
