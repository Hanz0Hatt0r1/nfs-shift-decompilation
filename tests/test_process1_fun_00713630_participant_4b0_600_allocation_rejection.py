import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "fun_00713630_participant_4b0_600_allocation_rejection.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_exact_candidate_and_sole_direct_root():
    p = _payload()
    assert p["format"] == "SHIFT.Fun00713630Participant4b0Allocation600Rejection/1"
    assert p["candidate"]["site"] == "0x004dbf73"
    assert p["candidate"]["function"] == "FUN_004dbdb0"
    assert p["candidate"]["selected_physics_participant_writer"] is False
    s = p["direct_call_surface"]
    assert s["direct_call_count"] == 1
    assert s["caller"] == "FUN_00549c00"
    assert s["callsite"] == "0x00549c56"
    assert s["allocation_size"] == "0x600"
    assert s["selected_participant_allocation_size"] == "0x2b90"
    assert s["same_object_identity"] is False


def test_machine_spans_are_pinned():
    p = _payload()
    assert p["direct_call_surface"]["machine_span"]["sha256"] == "e36377c3fb241d8db09c4ac220978273810d39233ebb6d27396af223a2ec25d2"
    assert p["constructor"]["machine_head_sha256"] == "153d262a6345057366e84d5328f0f0aab360b5be3d42ba1db15db68b5f9983fe"
    assert p["constructor"]["writer_window_sha256"] == "393f67c90a99248ceb83b86392070350b25c755340aa353f15e61870ba6080da"


def test_frontier_reduces_to_ten_without_opening_provider_gate():
    a = _payload()["adjudication"]
    assert a["candidate_receiver_identity_closed"] is True
    assert a["candidate_is_0x600_allocation"] is True
    assert a["candidate_is_selected_physics_participant"] is False
    assert a["direct_displacement_site_rejected"] is True
    assert a["remaining_unjoined_direct_site_count"] == 10
    assert a["selected_participant_runtime_plus_0x4b0_writer_closed"] is False
    assert a["p1_1a_complete"] is False
    assert a["p1_1_complete"] is False
    assert a["contact_response_provider_removal_authorized"] is False
    assert a["external_provider_count"] == 7
