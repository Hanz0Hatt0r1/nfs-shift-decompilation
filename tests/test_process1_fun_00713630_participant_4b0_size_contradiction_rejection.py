import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "fun_00713630_participant_4b0_size_contradiction_rejection.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_candidate_and_same_receiver_far_access_are_pinned():
    p = _payload()
    assert p["format"] == "SHIFT.Fun00713630Participant4b0SizeContradictionRejection/1"
    c = p["candidate"]
    assert c["site"] == "0x00832f46"
    assert c["function"] == "FUN_00832a80"
    assert c["selected_physics_participant_writer"] is False
    assert c["machine_span"]["sha256"] == "2f863cbbf6a03bd4a47bbbe793fecf91115bac8a42dd71eacc89a6bee88b8db5"
    r = p["receiver_size_contradiction"]
    assert r["selected_participant_allocation_size"] == "0x2b90"
    assert r["same_receiver_far_access"] == "receiver+0x3960"
    assert r["computed_byte_offset"] == "0x3960"
    assert r["machine_expression"] == "0x00832fe1 lea EDI,[ESI+0x3960]"
    assert r["machine_span"]["sha256"] == "75faff00fbbe167d622350da9840840d1da8b1be56969f65ecac309f0aec27b4"


def test_decompiler_body_is_pinned():
    d = _payload()["decompiler_proof"]
    assert d["function_lines"] == "904408-904865"
    assert d["function_sha256"] == "8c59edec061e4c859ae55e901e4fcbbc3add48d25abb006c2de5c80dc45e4032"


def test_frontier_reduces_to_three_without_provider_promotion():
    a = _payload()["adjudication"]
    assert a["candidate_receiver_identity_rejected_by_size"] is True
    assert a["candidate_is_selected_physics_participant"] is False
    assert a["direct_displacement_site_rejected"] is True
    assert a["remaining_unjoined_direct_site_count"] == 3
    assert a["selected_participant_runtime_plus_0x4b0_writer_closed"] is False
    assert a["p1_1a_complete"] is False
    assert a["p1_1_complete"] is False
    assert a["contact_response_provider_removal_authorized"] is False
    assert a["external_provider_count"] == 7
