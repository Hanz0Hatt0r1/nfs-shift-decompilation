import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "hdvehicle_64e8_manager_378_selection.json"
COORD = ROOT / "coordination" / "decomp_blockers.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_and_exact_manager_root():
    p = _payload()
    assert p["format"] == "SHIFT.HDVehicle64e8Manager378Selection/1"
    assert p["ready"] is True
    assert p["structural_relation"]["manager_root"] == "FUN_00489ad0() == 0x00bc9fc0"
    assert p["structural_relation"]["collection"] == "manager+0x2a0"
    assert p["structural_relation"]["destination"] == "manager+0x378"


def test_machine_value_transfer_is_pinned():
    chain = _payload()["machine_chain"]
    assert "0x0045da84 call FUN_00489ad0" in chain
    assert "0x0045daa3 lea ECX,[ESI+0x2a0]" in chain
    assert "0x0045daa9 call FUN_0054ed00" in chain
    assert "0x0045daae mov [ESI+0x378],EAX" in chain
    assert "0x0045da98 mov [ESI+0x378],EAX" in chain


def test_selection_relation_remains_fail_closed():
    a = _payload()["adjudication"]
    assert a["manager_378_indexed_selection_relation_proven"] is True
    assert a["manager_378_entry_identity_to_hdvehicle_4330_proven"] is False
    assert a["manager_2a0_insertion_identity_complete"] is False
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["exact_hdvehicle_64e8_non_sentinel_writer_proven"] is False
    assert a["retail_input_control_provenance_proven"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7


def test_vtable_candidate_is_navigation_only():
    g = _payload()["ghidra_navigation"]
    assert g["vtable_candidate"] == "0x00ab563c"
    assert g["slot"] == 0
    assert g["class_identity"] == "unproven"
    assert g["vtable_semantic_promotion"] is False


def test_coordination_advances_to_population_producer_entry_identity_surface():
    graph = json.loads(COORD.read_text(encoding="utf-8"))
    p13 = next(row for row in graph["workstreams"] if row["id"] == "P1.3")
    node = next(row for row in p13["children"] if row["id"] == "P1.3.manager2a0")
    assert node["status"] == "population-producer-proven-entry-identity-open"
    assert "manager+0x378" in node["proven_relation"]
    assert "thunk_FUN_00d60660" in node["proven_relation"]
    assert node["insertion_producer_complete"] is True
    assert node["element_size"] == "0x22e0"
    assert "HDVehicle+0x4330" in node["next"]
