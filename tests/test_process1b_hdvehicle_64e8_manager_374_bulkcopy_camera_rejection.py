import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "hdvehicle_64e8_manager_374_bulkcopy_camera_rejection.json"
COORD = ROOT / "coordination" / "decomp_blockers.json"
CAMERA_RUNTIME = ROOT / "src" / "camera" / "camera_view_update_pipeline_runtime.py"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_and_authority():
    p = _payload()
    assert p["format"] == "SHIFT.HDVehicle64e8Manager374BulkCopyCameraRejection/1"
    assert p["ready"] is True
    assert p["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"


def test_existing_camera_runtime_pins_same_function_and_copy_target():
    text = CAMERA_RUNTIME.read_text(encoding="utf-8")
    assert 'FORMAT = "SHIFT.CameraViewUpdatePipelineRuntime/1"' in text
    assert "Source-order pipeline for FUN_0081d2b0" in text
    assert '"action": "FUN_00481e20"' in text
    assert '"target": "+0x2d0"' in text


def test_camera_view_callsite_is_rejected_from_manager_root():
    p = _payload()
    assert p["navigation"]["ghidra_callsite"] == {
        "caller": "FUN_0081d2b0",
        "callsite": "0x0081d335",
        "callee": "FUN_00481e20",
        "kind": "direct",
    }
    assert p["manager_domain"]["manager_singleton_address"] == "0x00bc9fc0"
    assert p["manager_domain"]["manager_vtable"] == "0x00ab9190"
    assert p["manager_domain"]["fun_0081d2b0_is_manager_vtable_target"] is False
    assert p["adjudication"]["callsite_0x0081d335_rejected_as_manager_root"] is True


def test_direct_bulk_copy_surface_is_closed_but_indirect_paths_remain_open():
    p = _payload()
    s = p["bulk_copy_surface"]
    assert s["remaining_direct_embedded_subobject_callsites"] == []
    assert s["direct_bulk_copy_literal_writer_surface_complete"] is True
    a = p["adjudication"]
    assert a["fun_00481e20_direct_bulk_copy_surface_closed"] is True
    assert a["manager_374_literal_writer_surface_complete"] is True
    assert a["helper_alias_or_non_vtable_indirect_setter_still_possible"] is True
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["external_provider_count"] == 7


def test_coordination_preserves_bulk_copy_closure_after_later_alias_progress():
    coord = json.loads(COORD.read_text(encoding="utf-8"))
    p13 = next(w for w in coord["workstreams"] if w["id"] == "P1.3")
    row = next(c for c in p13["children"] if c["id"] == "P1.3.manager374")
    assert row["direct_bulk_copy_surface_complete"] is True
    assert any("0x0081d335" in item for item in row["rejected_bulk_copy_aliases"])
    assert row["status"] == "participants-lifecycle-zero-writers-proven-other-indirect-open"
    assert row["participants_lifecycle_direct_target_surface_complete"] is True
