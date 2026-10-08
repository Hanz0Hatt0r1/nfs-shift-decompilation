import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "fun_00713630_participant_4b0_account_record_rejections.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_stack_local_candidate_is_rejected():
    p = _payload()
    rows = {row["site"]: row for row in p["sites"]}
    row = rows["0x005b0ea6"]
    assert row["function"] == "FUN_005b0e60"
    assert row["selected_physics_participant_writer"] is False
    proof = row["receiver_proof"]
    assert proof["sole_direct_callsite"] == "0x005b3057"
    assert proof["setup"] == "lea ECX,[ESP+0xb4]; call FUN_005b0e60"
    assert proof["receiver_domain"] == "caller stack-local record"
    assert proof["machine_span"]["sha256"] == "53d2fd751af09be36c3ea3bec236138b75cd02b09c69db25e9fca0fa5150ec41"


def test_vtable_owned_candidate_is_rejected():
    p = _payload()
    rows = {row["site"]: row for row in p["sites"]}
    row = rows["0x005b0b1b"]
    assert row["function"] == "FUN_005b0af0"
    assert row["selected_physics_participant_writer"] is False
    proof = row["receiver_proof"]
    assert proof["sole_direct_callsite"] == "0x005b4c00"
    assert proof["setup"] == "lea ECX,[ESI+0x10]; call FUN_005b0af0"
    assert proof["caller_vtable_slot"] == "0x00adb49c -> 0x005b4be0"
    assert proof["vtable_root"] == "PTR_LAB_00adb440"
    assert "allocates 0x4bc" in proof["allocation_root"]
    assert proof["machine_span"]["sha256"] == "85d5b1dab232b6528e0b39ce60e51548094fe86191dead4850b9fd5c4c59b3c1"
    assert proof["vtable_span"]["sha256"] == "ba85bc797cc59accf5fa36a692c8d00cd3992153eac9886ef8784ffe5ab49a53"


def test_source_bodies_are_pinned():
    d = _payload()["decompiler_proof"]
    assert d["fun_005b0af0_sha256"] == "f6d787ca1c87796c70782fb88103c7a85e945e049ea6d650e112bcda777cc49e"
    assert d["fun_005b0e60_sha256"] == "fd3c688d94fe7f4458782663bfd2e592974101c6a2de4eaf4fb78708680870aa"
    assert d["fun_005b1b00_sha256"] == "605f0c946fe84eb20d4b982656d57a5b82c1f011583e310056d75cf025743c51"


def test_frontier_reduces_to_four_without_provider_promotion():
    p = _payload()
    assert p["format"] == "SHIFT.Fun00713630Participant4b0AccountRecordRejections/1"
    a = p["adjudication"]
    assert a["both_receiver_domains_closed"] is True
    assert a["site_0x005b0b1b_rejected"] is True
    assert a["site_0x005b0ea6_rejected"] is True
    assert a["remaining_unjoined_direct_site_count"] == 4
    assert a["selected_participant_runtime_plus_0x4b0_writer_closed"] is False
    assert a["p1_1a_complete"] is False
    assert a["p1_1_complete"] is False
    assert a["contact_response_provider_removal_authorized"] is False
    assert a["external_provider_count"] == 7
