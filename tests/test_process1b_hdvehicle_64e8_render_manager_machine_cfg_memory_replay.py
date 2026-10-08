import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_render_manager_machine_cfg_memory_replay.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_machine_replay_inventory_and_authority():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8RenderManagerMachineCfgMemoryReplay/1"
    assert data["ready"] is True
    assert data["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    inv = data["inventory"]
    assert inv["whole_text_direct_exact_load_count"] == 112
    assert inv["seed_local_cfg_seed_count"] == 112
    assert inv["seed_scan_cap_hit_count"] == 0
    assert inv["max_visited_states_per_seed"] == 380


def test_all_boundary_gap_seeds_are_included():
    cross = load_evidence()["boundary_crosscheck"]
    assert cross["sqlite_mapped_seed_count"] == 91
    assert cross["sqlite_unmapped_boundary_gap_seed_count"] == 21
    assert cross["nominal_entry_reachable_mapped_seed_count"] == 88
    assert cross["nominal_entry_unreachable_mapped_seed_count"] == 3
    assert cross["seed_local_scan_includes_boundary_gap_and_nominally_unreachable_seeds"] is True


def test_no_direct_exact_root_memory_store_but_call_frontier_remains():
    data = load_evidence()
    inv = data["inventory"]
    assert inv["call_boundary_count"] == 303
    assert inv["seed_with_call_boundary_count"] == 82
    assert inv["memory_store_count"] == 0
    assert inv["destination_kind_counts"] == {}
    adj = data["adjudication"]
    assert adj["direct_exact_global_cross_block_memory_persistence_closed_negative"] is True
    assert adj["exact_outer_alias_memory_store_found"] is False
    assert adj["opaque_callee_created_or_returned_alias_surface_complete"] is False
    assert adj["external_or_unknown_origin_alias_surface_complete"] is False
    assert adj["exhaustive_ghidra_v2_memory_escape_replay_replaced"] is False


def test_p13_remains_fail_closed():
    adj = load_evidence()["adjudication"]
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
