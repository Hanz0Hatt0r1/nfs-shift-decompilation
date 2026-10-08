import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "hdvehicle_64e8_manager_374_literal_writer_rejections.json"
COORD = ROOT / "coordination" / "decomp_blockers.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_and_authority():
    p = _payload()
    assert p["format"] == "SHIFT.HDVehicle64e8Manager374LiteralWriterRejections/1"
    assert p["ready"] is True
    assert p["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"


def test_fixed_singleton_writer_is_not_manager():
    row = next(r for r in _payload()["rejections"] if r["function"] == "FUN_0051efa0")
    assert row["proven_receiver"] == "0x00be1680"
    assert row["manager_receiver"] == "0x00bc9fc0"
    assert row["same_receiver"] is False
    assert row["rejected_as_manager_374_writer"] is True


def test_small_allocated_object_is_not_manager():
    row = next(r for r in _payload()["rejections"] if r["function"] == "FUN_005dec70")
    assert row["allocated_size"] == "0x37c"
    assert "+0x37c" in row["layout_contradiction"]
    assert row["rejected_as_manager_374_writer"] is True


def test_remaining_bulk_copy_stays_open_and_gates_fail_closed():
    p = _payload()
    assert p["remaining_candidate"]["function"] == "FUN_00481e20"
    assert p["remaining_candidate"]["status"] == "open-alias-bulk-copy"
    a = p["adjudication"]
    assert a["fun_00481e20_bulk_copy_still_open"] is True
    assert a["manager_374_literal_writer_surface_complete"] is False
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["retail_input_control_provenance_proven"] is False
    assert a["external_provider_count"] == 7


def test_coordination_points_to_bulk_copy_alias_closure():
    graph = json.loads(COORD.read_text(encoding="utf-8"))
    p13 = next(row for row in graph["workstreams"] if row["id"] == "P1.3")
    node = next(row for row in p13["children"] if row["id"] == "P1.3.manager374")
    assert node["status"] == "two-literal-writers-rejected-bulk-copy-open"
    assert "FUN_00481e20" in node["next"]
