import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00713630_participant_4b0_frontier.json"
DOC = ROOT / "docs/PROCESS_1_FUN_00713630_PARTICIPANT_4B0_FRONTIER.md"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_and_fail_closed_gate():
    p = _payload()
    assert p["format"] == "SHIFT.Fun00713630Participant4b0Frontier/1"
    assert p["ready"] is True
    assert p["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    a = p["adjudication"]
    assert a["manager_record_to_actual_participant_identity_closed"] is True
    assert a["selected_participant_runtime_plus_0x4b0_writer_closed"] is False
    assert a["p1_1a_complete"] is False
    assert a["p1_1_complete"] is False
    assert a["contact_response_provider_removal_authorized"] is False
    assert a["external_provider_count"] == 7


def test_selected_participant_root_and_pre_constructor_zero_are_precise():
    p = _payload()
    root = p["selected_participant_identity"]
    assert root["manager_record_stride"] == "0x1fa0"
    assert root["manager_record_offset0"] == "actual PhysicsParticipant pointer"
    assert root["allocation_size"] == "0x2b90"
    assert root["allocation_flags"] == "0x20"
    assert root["participant_constructor"] == "FUN_0072ed20"
    zero = p["pre_constructor_state"]
    assert zero["participant_plus_0x4b0_inside_allocation"] is True
    assert zero["participant_plus_0x4b0_bits_immediately_after_zero_fill"] == "0x00000000"
    assert zero["survives_all_constructor_or_runtime_paths_proven"] is False


def test_direct_displacement_writer_surface_is_bounded_without_identity_promotion():
    p = _payload()
    surface = p["retail_direct_displacement_store_surface"]
    assert surface["site_count"] == 16
    assert len(surface["sites"]) == 16
    assert surface["physics_tweaker_candidate_rejected"] is True
    rejected = next(row for row in surface["sites"] if row["site"] == "0x00748956")
    assert rejected["function"] == "FUN_00748280"
    assert rejected["selected_participant_writer"] is False
    assert surface["remaining_sites_joined_to_selected_participant"] == 0
    assert surface["direct_displacement_surface_identity_complete"] is False
    assert surface["computed_or_alias_writes_excluded"] is False


def test_constructor_body_does_not_overclaim_callee_surface():
    c = _payload()["constructor_surface"]
    assert c["function"] == "FUN_0072ed20"
    assert c["direct_receiver_plus_0x4b0_store_in_body"] is False
    assert c["callee_or_alias_writer_excluded"] is False
    text = DOC.read_text(encoding="utf-8")
    assert "remaining 15 direct-displacement" in text
    assert "Provider reduction remains forbidden" in text
