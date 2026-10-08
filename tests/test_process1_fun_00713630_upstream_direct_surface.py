import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00713630_upstream_direct_surface.json"
DOC = ROOT / "docs/PROCESS_1_FUN_00713630_UPSTREAM_DIRECT_SURFACE.md"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_authority_and_fail_closed_gate():
    p = _payload()
    assert p["format"] == "SHIFT.Fun00713630UpstreamDirectSurface/1"
    assert p["authority"]["platform"] == "PC retail 1.02"
    a = p["adjudication"]
    assert a["p1_1a_complete"] is False
    assert a["p1_1_complete"] is False
    assert a["contact_response_provider_removal_authorized"] is False
    assert a["external_provider_count"] == 7


def test_cadence_chain_is_exact_and_receiver_preserving():
    c = _payload()["cadence_chain"]
    assert c["caller_callsite"] == "0x0071557d"
    assert c["cadence_function"] == "FUN_007144a0"
    assert c["cadence_counter"] == "receiver+0x158"
    assert c["writer_callsite"] == "0x007144bd"
    assert c["writer"] == "FUN_00713630"
    assert c["receiver_preserved"] is True


def test_config_direct_literal_surface_is_bounded_but_not_promoted():
    p = _payload()
    rows = p["config_globals"]
    assert len(rows) == 7
    assert all(row["literal_occurrences_in_image"] == 1 for row in rows)
    assert all(row["direct_literal_writer_found"] is False for row in rows)
    assert p["adjudication"]["seven_direct_literal_read_sites_closed"] is True
    assert p["adjudication"]["config_global_owner_or_alias_writer_closed"] is False


def test_sample_history_writer_has_exact_two_direct_callers():
    s = _payload()["sample_history_writer"]
    assert s["function"] == "FUN_00727870"
    assert s["direct_caller_count"] == 2
    assert [row["callsite"] for row in s["direct_callers"]] == ["0x0073f293", "0x0074752c"]
    assert s["selected_participant_root_join_complete"] is False


def test_plus_4b0_candidate_stays_identity_fail_closed():
    c = _payload()["participant_scalar_candidate"]
    assert c["candidate_function"] == "FUN_00748280"
    assert c["candidate_store"] == "0x00748956 fstp dword [esi+0x4b0]"
    assert c["same_object_identity_as_FUN_00713630_participant_proven"] is False
    text = DOC.read_text(encoding="utf-8")
    assert "matching `+0x4b0` offsets do not prove" in text
