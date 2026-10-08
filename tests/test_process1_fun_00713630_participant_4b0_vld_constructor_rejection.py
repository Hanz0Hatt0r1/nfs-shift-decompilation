import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00713630_participant_4b0_vehicle_load_data_constructor_rejection.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_candidate_is_exactly_rejected_and_gate_stays_closed():
    p = _payload()
    assert p["format"] == "SHIFT.Fun00713630Participant4b0VehicleLoadDataConstructorRejection/1"
    c = p["candidate"]
    assert c["site"] == "0x007c0fe2"
    assert c["function"] == "FUN_007c0db0"
    assert c["selected_physics_participant_writer"] is False
    a = p["adjudication"]
    assert a["candidate_receiver_identity_closed"] is True
    assert a["candidate_is_vehicle_load_data_family"] is True
    assert a["candidate_is_selected_physics_participant"] is False
    assert a["direct_displacement_site_rejected"] is True
    assert a["remaining_unjoined_direct_site_count"] == 13
    assert a["selected_participant_runtime_plus_0x4b0_writer_closed"] is False
    assert a["p1_1a_complete"] is False
    assert a["p1_1_complete"] is False
    assert a["contact_response_provider_removal_authorized"] is False
    assert a["external_provider_count"] == 7


def test_constructor_bridge_maps_store_to_allocation_plus_4b8():
    b = _payload()["constructor_bridge"]
    assert b["receiver_capture"] == "0x007c318a ESI=ECX"
    assert b["nested_receiver"] == "0x007c31a3 lea ECX,[ESI+0x8]"
    assert b["callsite"] == "0x007c31aa call FUN_007c0db0"
    assert "allocation+0x4b8" in b["meaning"]


def test_both_roots_allocate_3848_and_store_outside_participant_root():
    roots = _payload()["allocation_roots"]
    assert {r["function"] for r in roots} == {"FUN_0076df50", "FUN_00798df0"}
    assert all(r["allocation_size"] == "0x3848" for r in roots)
    assert roots[0]["owner_store"] == "0x0076dfda [HDVehicle+0x66b4]=constructed object"
    assert roots[1]["owner_store"] == "0x00798e85 [selected subobject+0x1d00]=constructed object"


def test_machine_spans_are_pinned():
    p = _payload()
    assert p["constructor_bridge"]["machine_span"]["sha256"] == "683d58203d5326775ec1e9e9ffa6f732876017e663780e0934f8822cef0b6db4"
    roots = p["allocation_roots"]
    assert roots[0]["machine_span"]["sha256"] == "d9c852fff318bb09157e5bca652c5861b8ed43ddae229e2bc161089952d2a8ad"
    assert roots[1]["machine_span"]["sha256"] == "1e0ffded528ce797e0e9af6ed51df428a8aaf7827c7b0cd522eb71334ccd9826"
    assert p["writer_span"]["sha256"] == "d788cc142fe72a6f2817739d1cdb2a0bad95145a63e792909b11e872fb267df7"
