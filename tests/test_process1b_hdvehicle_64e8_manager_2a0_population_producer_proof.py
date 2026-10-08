import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "hdvehicle_64e8_manager_2a0_population_producer_proof.json"
COORD = ROOT / "coordination" / "decomp_blockers.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_exact_manager_root_population_callsite():
    p = _payload()
    assert p["format"] == "SHIFT.HDVehicle64e8Manager2a0PopulationProducerProof/1"
    r = p["root_callsite"]
    assert r["caller"] == "FUN_004978f0"
    assert r["manager_getter"] == "thunk_FUN_00444fcc()"
    assert "thunk_FUN_00d61e00" in r["source_order"]
    assert r["count_source"] == "DAT_00bbc628"


def test_collection_population_layout_and_loop_are_pinned():
    h = _payload()["population_helper"]
    assert h["function"] == "thunk_FUN_00d61e00"
    assert h["collection"] == "manager+0x2a0"
    assert h["append_helper"] == "thunk_FUN_00d61d10"
    assert h["element_size"] == "0x22e0"
    assert h["element_alignment"] == "0x20"
    assert h["element_initializer"] == "FUN_00481a10"
    assert any("param_3 times" in step for step in h["steps"])


def test_population_producer_contract_remains_bounded_to_its_original_frontier():
    a = _payload()["adjudication"]
    assert a["manager_2a0_population_producer_proven"] is True
    assert a["manager_2a0_insertion_producer_complete"] is True
    assert a["manager_2a0_entry_identity_to_hdvehicle_4330_proven"] is False
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["external_provider_count"] == 7


def test_coordination_preserves_population_proof_after_identity_adjudication():
    graph = json.loads(COORD.read_text(encoding="utf-8"))
    p13 = next(row for row in graph["workstreams"] if row["id"] == "P1.3")
    node = next(row for row in p13["children"] if row["id"] == "P1.3.manager2a0")
    producer = node["proven_population_producer"]
    assert "FUN_004978f0" in producer
    assert "thunk_FUN_00d61e00" in producer
    assert node["element_size"] == "0x22e0"
    assert node["insertion_producer_complete"] is True
    assert node["entry_identity"] == "rejected-hdvehicle+0x4330"
