import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_hdvehicle_root_literal_persistence_surface.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_literal_root_inventory_and_sinks():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8HDVehicleRootLiteralPersistenceSurface/1"
    assert data["ready"] is True
    inv = data["inventory"]
    assert inv["raw_little_endian_occurrence_count"] == 71
    assert inv["literal_mov_seed_count"] == 69
    assert inv["direct_memory_numeric_occurrence_count"] == 2
    assert inv["seed_reaching_direct_call_boundary_count"] == 61
    assert inv["memory_store_of_exact_root_value_count"] == 0
    assert inv["push_exact_root_after_seed_count"] == 0
    assert inv["same_block_persistent_escape_count"] == 0


def test_fail_closed_callee_and_two_unknown_frontiers_remain():
    adj = load_evidence()["adjudication"]
    assert adj["literal_hdvehicle_root_same_block_persistence_closed_negative"] is True
    assert adj["literal_hdvehicle_root_persistent_memory_copy_found"] is False
    assert adj["literal_hdvehicle_root_stack_escape_found"] is False
    assert adj["callee_side_alias_creation_surface_complete"] is False
    assert adj["two_unknown_origin_hdvehicle_4330_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
