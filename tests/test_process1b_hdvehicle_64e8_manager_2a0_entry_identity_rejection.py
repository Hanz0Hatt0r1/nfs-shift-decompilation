import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "hdvehicle_64e8_manager_2a0_entry_identity_rejection.json"
COORD = ROOT / "coordination" / "decomp_blockers.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_fixed_hdvehicle_embedded_target_is_pinned():
    h = _payload()["hdvehicle_storage"]
    assert h["global_root"] == "0x00c13700"
    assert h["target_subobject"] == "HDVehicle+0x4330"
    assert h["target_absolute"] == "0x00c17a30"
    assert "FUN_0076df50" in h["initialization_call"]


def test_manager_collection_entries_are_allocator_owned():
    m = _payload()["manager_collection_storage"]
    assert m["collection"] == "manager+0x2a0"
    assert "FUN_00486aa0" in m["reset"]
    assert "FUN_0062f2d0" in m["first_chunk"]
    assert "FUN_00886900" in m["first_chunk"]
    assert "chunk_data_base" in m["entry_address"]
    assert m["external_pointer_insertion"] is False


def test_selected_collection_entry_cannot_be_hdvehicle_embedded_pointer():
    s = _payload()["selection_path"]
    assert s["selector"] == "thunk_FUN_00d60660"
    assert s["selected_entry_can_be_hdvehicle_plus_4330"] is False
    a = _payload()["adjudication"]
    assert a["manager_2a0_entry_equals_hdvehicle_4330_rejected"] is True
    assert a["selection_writer_can_establish_manager_374_equals_hdvehicle_4330"] is False
    assert a["manager_2a0_identity_frontier_complete"] is True
    assert a["manager_374_global_identity_to_hdvehicle_4330_complete"] is False
    assert a["external_provider_count"] == 7


def test_coordination_closes_manager2a0_identity_only():
    graph = json.loads(COORD.read_text(encoding="utf-8"))
    p13 = next(row for row in graph["workstreams"] if row["id"] == "P1.3")
    m374 = next(row for row in p13["children"] if row["id"] == "P1.3.manager374")
    m2a0 = next(row for row in p13["children"] if row["id"] == "P1.3.manager2a0")
    assert m2a0["status"] == "entry-identity-rejected-complete"
    assert m2a0["entry_identity_to_hdvehicle_4330"] is False
    assert m374["selection_writer_identity_to_hdvehicle_4330"] is False
    assert m374["manager_plus_0x20_escaped_alias_open"] is True
    assert "FUN_004f5e60" in m374["next"]
    assert m374["participants_lifecycle_direct_target_surface_complete"] is True
