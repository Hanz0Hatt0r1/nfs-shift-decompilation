import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "fun_00713630_participant_4b0_nested_copy_rejection.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_static_reference_surface_and_receiver_mapping():
    p = _payload()
    assert p["format"] == "SHIFT.Fun00713630Participant4b0NestedCopyRejection/1"
    c = p["candidate"]
    assert c["site"] == "0x00487d2d"
    assert c["function"] == "FUN_004876f0"
    assert c["selected_physics_participant_writer"] is False
    refs = p["static_reference_closure"]
    assert refs["direct_rel32_calls"] == ["0x0048bc90", "0x0048bca2"]
    assert refs["direct_rel32_call_count"] == 2
    assert refs["direct_rel32_jump_count"] == 0
    assert refs["literal_address_reference_count"] == 0
    assert refs["caller_function"] == "FUN_0048bbc0"


def test_both_actual_receivers_shift_candidate_away_from_root_4b0():
    rows = _payload()["receiver_mapping"]
    assert rows[0]["receiver_setup"] == "lea ECX,[EBX+0x110]"
    assert rows[0]["candidate_storage_in_outer"] == "outer+0x5c0"
    assert rows[1]["receiver_setup"] == "lea ECX,[EBX+0xa00]"
    assert rows[1]["candidate_storage_in_outer"] == "outer+0xeb0"
    assert all(row["candidate_storage_in_outer"] != "outer+0x4b0" for row in rows)


def test_machine_and_source_spans_are_pinned():
    p = _payload()
    assert p["candidate"]["candidate_machine_span"]["sha256"] == "1e30cf6e880b97abe53f0c3da7fc529fff36929dfad2ba65ce5ec7803e599484"
    assert p["static_reference_closure"]["callsite_machine_span"]["sha256"] == "846d098d45891070b81f3c570daa8bda060e287f5d5e52a000407b04cf94afcb"
    assert p["decompiler_proof"]["candidate_function_sha256"] == "46c8d05e77f2b1f30f30268c7a1571abcebf3659b0993a37d95a23746b76f40b"


def test_frontier_reduces_to_two_without_provider_promotion():
    a = _payload()["adjudication"]
    assert a["candidate_static_receiver_surface_closed"] is True
    assert a["candidate_is_selected_physics_participant_root_writer"] is False
    assert a["direct_displacement_site_rejected"] is True
    assert a["remaining_unjoined_direct_site_count"] == 2
    assert a["selected_participant_runtime_plus_0x4b0_writer_closed"] is False
    assert a["p1_1a_complete"] is False
    assert a["p1_1_complete"] is False
    assert a["contact_response_provider_removal_authorized"] is False
    assert a["external_provider_count"] == 7
