import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "hdvehicle_64e8_manager_374_bulkcopy_participant_rejection.json"
COORD = ROOT / "coordination" / "decomp_blockers.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_authority_and_upstreams():
    p = _payload()
    assert p["format"] == "SHIFT.HDVehicle64e8Manager374BulkCopyParticipantRejection/1"
    assert p["ready"] is True
    assert p["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert "SHIFT.HDVehicle64e8Manager374LiteralWriterRejections/1" in p["upstream_contracts"]
    assert "SHIFT.OuterVehicleRenderSnapshotAffineBridge/1" in p["upstream_contracts"]


def test_participant_a00_callsite_is_rejected_from_manager_root():
    row = _payload()["callsite"]
    assert row["address"] == "0x004848f5"
    assert row["caller"] == "FUN_004848bc"
    assert row["destination"] == "parent+0xa00"
    assert row["proven_parent_domain"] == "SMS participant"
    assert row["proven_destination_domain"] == "participant+0xa00 render snapshot"
    assert row["manager_singleton_destination"] == "0x00bc9fc0"
    assert row["same_root_as_manager_singleton"] is False
    assert row["rejected_as_manager_374_writer"] is True


def test_participant_contract_keeps_its_original_bounded_adjudication():
    a = _payload()["adjudication"]
    assert a["fun_00481e20_callsite_0x004848f5_rejected"] is True
    assert a["remaining_direct_embedded_subobject_callsites"] == [
        "0x0081d335 destination ECX=parent+0x2d0"
    ]
    assert a["fun_00481e20_bulk_copy_still_open"] is True
    assert a["manager_374_literal_writer_surface_complete"] is False
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["external_provider_count"] == 7


def test_coordination_preserves_participant_rejection_after_later_frontier_advances():
    coord = json.loads(COORD.read_text(encoding="utf-8"))
    p13 = next(w for w in coord["workstreams"] if w["id"] == "P1.3")
    row = next(c for c in p13["children"] if c["id"] == "P1.3.manager374")
    assert any("0x004848f5" in item for item in row["rejected_bulk_copy_aliases"])
    assert row["direct_bulk_copy_surface_complete"] is True
    assert row["status"] == "participants-lifecycle-zero-writers-proven-other-indirect-open"
    assert row["participants_lifecycle_direct_target_surface_complete"] is True
