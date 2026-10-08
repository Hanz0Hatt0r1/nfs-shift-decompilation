import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00713630_participant_4b0_subobject_alias_frontier.json"
DOC = ROOT / "docs/PROCESS_1_FUN_00713630_PARTICIPANT_4B0_SUBOBJECT_ALIAS_FRONTIER.md"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_exact_subobject_alias_and_fail_closed_gate():
    p = _payload()
    assert p["format"] == "SHIFT.Fun00713630Participant4b0SubobjectAliasFrontier/1"
    s = p["participant_subobject"]
    assert s["offset"] == "0x340"
    assert s["constructor"] == "FUN_0079c1c0"
    assert s["final_vtable"] == "0x00b0b744"
    assert s["participant_plus_0x4b0_equals_subobject_plus_0x170"] is True
    assert s["known_direct_read"] == "0x007928d1 fld dword [esi+0x170] in FUN_007927c0"
    a = p["adjudication"]
    assert a["participant_plus_0x4b0_to_subobject_plus_0x170_identity_closed"] is True
    assert a["selected_participant_runtime_plus_0x4b0_writer_closed"] is False
    assert a["p1_1a_complete"] is False
    assert a["p1_1_complete"] is False
    assert a["contact_response_provider_removal_authorized"] is False
    assert a["external_provider_count"] == 7


def test_false_alias_candidates_are_receiver_rejected():
    rows = _payload()["rejected_alias_candidates"]
    assert len(rows) == 2
    assert all(row["selected_participant_writer"] is False for row in rows)
    text = "\n".join(row["candidate"] for row in rows)
    assert "FUN_00747c30" in text
    assert "FUN_007215b0" in text
    assert "participant+0x2404" in rows[1]["reason"]


def test_generic_reflection_candidate_is_not_promoted_by_offset_equality():
    r = _payload()["reflection_candidate_rejection"]
    assert r["function"] == "FUN_0072a2d0"
    assert r["registry_receiver"] == "DAT_00b8d1b4"
    assert r["registry_reference_count"] == 192
    assert r["fun_0072a2d0_fun_0063a280_registration_count"] == 189
    assert r["observed_offset_0x170_registration"].startswith("0x0072c3b3")
    assert r["name_argument"] == "Add Pressure - Steer From Wall"
    assert r["selected_participant_subobject_identity_joined"] is False
    assert r["rejected_as_writer_proof"] is True


def test_direct_surface_remains_narrow_and_open_paths_are_explicit():
    p = _payload()
    surface = p["checked_selected_surface"]
    assert surface["direct_subobject_plus_0x170_store_found"] is False
    assert surface["computed_alias_bulk_indirect_paths_excluded"] is False
    assert "SHIFT.Fun00713630Participant4b0Frontier/1" in p["upstream_contracts"]
    doc = DOC.read_text(encoding="utf-8")
    assert "computed-address" in doc
    assert "bulk-copy" in doc
    assert "provider count: **7**" in doc


def test_machine_spans_are_pinned():
    p = _payload()
    assert p["participant_subobject"]["constructor_machine_span"]["sha256"] == "9a2bd50fcbce77b097220107f501d7962b290952b6cedbb67e74af3b09887c69"
    assert p["participant_subobject"]["read_machine_span"]["sha256"] == "f5dbb9305fc5da276eecbb0627aabaced12ad76dea172c609604cdca02e613e1"
    rows = p["rejected_alias_candidates"]
    assert rows[0]["root_machine_span"]["sha256"] == "06787cd2f504259a8decdd43fb5740f6f8f733bad669a7663fcc4bed03a81962"
    assert rows[1]["receiver_machine_span"]["sha256"] == "56921b3a2d8714f35546ff9c82b0247178a9e643fe9700b745d6c22095c0cbb4"
