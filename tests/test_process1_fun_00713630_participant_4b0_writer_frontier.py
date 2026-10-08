import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00713630_participant_4b0_writer_frontier.json"
DOC = ROOT / "docs/PROCESS_1_FUN_00713630_PARTICIPANT_4B0_WRITER_FRONTIER.md"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_exact_participant_root_and_fail_closed_gate():
    p = _payload()
    assert p["format"] == "SHIFT.Fun00713630Participant4b0WriterFrontier/1"
    root = p["selected_participant_construction"]
    assert root["wrapper_array"] == "manager+0x140"
    assert root["allocation_size"] == "0x2b90"
    assert root["participant_constructor"] == "FUN_0072ed20"
    assert root["actual_participant_store"] == "0x0071263e mov [esi],eax"
    a = p["adjudication"]
    assert a["selected_participant_root_construction_closed"] is True
    assert a["actual_selected_participant_plus_0x4b0_writer_closed"] is False
    assert a["p1_1a_complete"] is False
    assert a["p1_1_complete"] is False
    assert a["contact_response_provider_removal_authorized"] is False
    assert a["external_provider_count"] == 7


def test_4b0_is_exact_subobject_170():
    s = _payload()["participant_subobject"]
    assert s["offset"] == "0x340"
    assert s["constructor"] == "FUN_0079c1c0"
    assert s["final_vtable"] == "0x00b0b744"
    assert s["participant_plus_0x4b0_equals_subobject_plus_0x170"] is True
    assert s["known_direct_read"] == "0x007928d1 fld dword [esi+0x170] in FUN_007927c0"


def test_false_candidates_are_receiver_rejected():
    rows = _payload()["rejected_candidates"]
    assert len(rows) == 4
    assert all(row["selected_participant_writer"] is False for row in rows)
    text = "\n".join(row["candidate"] for row in rows)
    assert "FUN_00748280" in text
    assert "FUN_007c3b00" in text
    assert "FUN_00747c30" in text
    assert "FUN_007215b0" in text


def test_checked_direct_surface_and_generic_reflection_candidate_are_fail_closed():
    p = _payload()
    surface = p["constructor_and_selected_runtime_direct_surface"]
    assert surface["direct_subobject_plus_0x170_store_found"] is False
    assert "alias/computed/bulk/indirect paths remain open" in surface["meaning"]
    reflection = p["reflection_candidate_rejection"]
    assert reflection["function"] == "FUN_0072a2d0"
    assert reflection["registry_receiver"] == "DAT_00b8d1b4"
    assert reflection["fun_0072a2d0_fun_0063a280_registration_count"] == 189
    assert reflection["name_argument"] == "Add Pressure - Steer From Wall"
    assert reflection["selected_participant_subobject_identity_joined"] is False
    assert reflection["rejected_as_writer_proof"] is True
    assert p["adjudication"]["generic_reflection_0x170_candidate_rejected_as_identity_proof"] is True
    assert "computed-address" in DOC.read_text(encoding="utf-8")


def test_machine_spans_are_pinned():
    p = _payload()
    assert p["selected_participant_construction"]["machine_span"]["sha256"] == "a82eca170826886527125d22242da2eb78171dd0cb0aa2ea2aa5db6bb344f2dc"
    assert p["participant_subobject"]["constructor_machine_span"]["sha256"] == "9a2bd50fcbce77b097220107f501d7962b290952b6cedbb67e74af3b09887c69"
    assert p["participant_subobject"]["read_machine_span"]["sha256"] == "f5dbb9305fc5da276eecbb0627aabaced12ad76dea172c609604cdca02e613e1"
