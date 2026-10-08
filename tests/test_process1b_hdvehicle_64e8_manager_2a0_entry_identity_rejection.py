import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "hdvehicle_64e8_manager_2a0_entry_identity_rejection.json"
POPULATION = ROOT / "evidence" / "hdvehicle_64e8_manager_2a0_population_producer_proof.json"
BOOTSTRAP = ROOT / "evidence" / "hdvehicle_64e8_bootstrap_sentinel.json"
COORD = ROOT / "coordination" / "decomp_blockers.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_contract_authority_and_upstreams():
    p = _load(EVIDENCE)
    assert p["format"] == "SHIFT.HDVehicle64e8Manager2a0EntryIdentityRejection/1"
    assert p["ready"] is True
    assert p["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert "SHIFT.HDVehicle64e8Manager2a0PopulationProducerProof/1" in p["upstream_contracts"]
    assert "SHIFT.HDVehicle64e8BootstrapSentinel/1" in p["upstream_contracts"]


def test_population_contract_pins_22e0_element_stride():
    population = _load(POPULATION)
    assert population["population_helper"]["element_size"] == "0x22e0"
    assert population["population_helper"]["element_alignment"] == "0x20"
    p = _load(EVIDENCE)
    assert p["manager_collection_entry"]["element_stride"] == "0x22e0"
    assert p["manager_collection_entry"]["element_initializer"] == "FUN_00481a10"


def test_selected_record_machine_owner_and_constructor_are_reused():
    bootstrap = _load(BOOTSTRAP)
    assert bootstrap["constructor_chain"]["selected_hdvehicle_call"] == "0x0076b241 ECX = HDVehicle+0x4330; 0x0076b247 call FUN_00772200"
    p = _load(EVIDENCE)
    assert p["selected_hdvehicle_record"]["machine_constructor_call"] == bootstrap["constructor_chain"]["selected_hdvehicle_call"]
    assert p["selected_hdvehicle_record"]["constructor"] == "FUN_00772200"
    assert "record+0x2360 = 0.5f" in p["selected_hdvehicle_record"]["source_order_high_writes"]


def test_layout_extent_is_mathematically_incompatible():
    p = _load(EVIDENCE)
    assert int(p["manager_collection_entry"]["element_stride"], 16) == 0x22E0
    assert int(p["selected_hdvehicle_record"]["minimum_constructor_extent_from_last_dword_write"], 16) == 0x2364
    assert 0x2364 - 0x22E0 == 0x84
    assert p["layout_contradiction"]["difference"] == "0x84"
    assert p["layout_contradiction"]["identity_possible"] is False


def test_identity_route_is_rejected_but_control_provenance_remains_open():
    p = _load(EVIDENCE)
    a = p["adjudication"]
    assert a["manager_2a0_entry_identity_to_hdvehicle_4330_rejected"] is True
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is True
    assert a["manager_374_join_result"] == "rejected"
    assert a["exact_hdvehicle_64e8_non_sentinel_writer_proven"] is False
    assert a["retail_input_control_provenance_proven"] is False
    assert a["external_provider_count"] == 7


def test_coordination_retires_manager_identity_route():
    graph = _load(COORD)
    p13 = next(row for row in graph["workstreams"] if row["id"] == "P1.3")
    manager374 = next(row for row in p13["children"] if row["id"] == "P1.3.manager374")
    manager2a0 = next(row for row in p13["children"] if row["id"] == "P1.3.manager2a0")
    assert manager374["hdvehicle_4330_identity"] == "rejected-layout-contradiction"
    assert manager2a0["entry_identity"] == "rejected-hdvehicle+0x4330"
    assert "HDVehicle+0x64e8" in manager374["next"]
