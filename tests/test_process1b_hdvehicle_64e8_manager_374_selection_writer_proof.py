import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "hdvehicle_64e8_manager_374_selection_writer_proof.json"
COORD = ROOT / "coordination" / "decomp_blockers.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_and_authority():
    p = _payload()
    assert p["format"] == "SHIFT.HDVehicle64e8Manager374SelectionWriterProof/1"
    assert p["ready"] is True
    assert p["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"


def test_exact_manager_getter_receiver_is_pinned_at_both_callsites():
    w = _payload()["writer"]
    assert w["function"] == "thunk_FUN_00d60660"
    assert [row["function"] for row in w["callers"]] == ["FUN_00465860", "FUN_00468ed0"]
    assert all("thunk_FUN_00444fcc" in row["source_order"] for row in w["callers"])


def test_collection_entry_selection_to_manager_374_is_exact():
    p = _payload()
    assert p["manager"]["collection"] == "+0x2a0"
    assert p["manager"]["selected_slot"] == "+0x374"
    assert p["writer"]["literal_store"] == "*(int **)(this+0x374) = entry"


def test_join_advances_but_hdvehicle_identity_remains_fail_closed():
    j = _payload()["join"]
    assert j["manager_2a0_to_374_selection_relation_proven"] is True
    assert j["manager_374_nonzero_writer_proven"] is True
    assert j["manager_374_equals_hdvehicle_4330"] is False
    assert j["manager_2a0_insertion_producer_complete"] is False
    assert j["external_provider_count"] == 7


def test_coordination_consumes_selection_writer_proof_without_closing_escaped_aliases():
    graph = json.loads(COORD.read_text(encoding="utf-8"))
    p13 = next(row for row in graph["workstreams"] if row["id"] == "P1.3")
    m374 = next(row for row in p13["children"] if row["id"] == "P1.3.manager374")
    m2a0 = next(row for row in p13["children"] if row["id"] == "P1.3.manager2a0")
    assert m374["proven_nonzero_writer"] == "thunk_FUN_00d60660"
    assert m374["manager_plus_0x20_escaped_alias_open"] is True
    assert m2a0["status"] == "selection-writer-proven-registration-identity-open"
    assert "thunk_FUN_00d60660" in m2a0["proven_relation"]
