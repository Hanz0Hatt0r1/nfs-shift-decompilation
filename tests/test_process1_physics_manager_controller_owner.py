from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/process1_physics_manager_controller_owner.json"
DOC = ROOT / "docs/PROCESS_1_PHYSICS_MANAGER_CONTROLLER_OWNER.md"
PRIOR = ROOT / "evidence/process1_fun_0079b2d0_virtual_dispatch.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_process1_physics_manager_controller_owner_is_exact_pc_retail() -> None:
    payload = _load(EVIDENCE)
    assert payload["format"] == "SHIFT.Process1PhysicsManagerControllerOwner/1"
    assert payload["ready"] is True
    assert payload["source"]["authority"] == "PC retail 1.02"
    assert payload["source"]["retail_executable_md5"] == "705af8b420e5eb1e3834ac43d5533c6b"
    assert payload["source"]["retail_executable_sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )
    assert payload["source"]["retail_source_sha256"] == (
        "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
    )
    assert payload["source"]["xbox_recomp_required"] is False


def test_physics_manager_identity_and_update_slot_are_frozen() -> None:
    payload = _load(EVIDENCE)
    manager = payload["physics_manager"]
    assert manager["registered_name"] == "Physics Manager"
    assert manager["singleton_object"] == "DAT_00c104e0"
    assert manager["vtable"] == "0x00b04524"
    assert manager["update_slot_offset"] == "0x18"
    assert manager["update_slot_cell"] == "0x00b0453c"
    assert manager["update_target"] == "FUN_00711b50"
    assert manager["machine_spans"]["update_slot_pointer"]["sha256"] == (
        "934b96a464cfc0f2bd606065dc0721d407659ffc0add2c8f4796f55d1fa992e0"
    )


def test_controller1_registration_and_worker_owner_path_are_exact() -> None:
    payload = _load(EVIDENCE)
    registration = payload["controller_registration"]
    worker = payload["controller_worker"]
    assert registration["controller_name"] == "Controller #1"
    assert registration["manager_attach"] == "FUN_006485b0"
    assert registration["manager_controller_owner_offset"] == "0x14c"
    assert registration["machine_spans"]["controller1_to_physics_attach"]["sha256"] == (
        "e8d6f2f17e32b9fc652912d7a264e901b1d04e48024a9349c65f26e795caef2f"
    )

    assert worker["worker_slot_offset"] == "0x4"
    assert worker["worker_target"] == "FUN_00662880"
    assert worker["active_controller_state_offset"] == "0x98"
    assert worker["active_controller_state_value"] == 6
    assert worker["manager_list_offset"] == "0x58"
    assert worker["manager_list_runner"] == "FUN_0065b8b0"
    assert worker["manager_scheduler"] == "FUN_00647ef0"


def test_manager_scheduler_dispatch_is_proven_without_render_cadence_promotion() -> None:
    payload = _load(EVIDENCE)
    scheduler = payload["manager_scheduler"]
    promotion = payload["promotion"]

    assert scheduler["slot_dispatch"] == "FUN_00647d80"
    assert scheduler["default_virtual_slot_offset"] == "0x18"
    assert scheduler["alternate_virtual_slot_offset"] == "0x1c"
    assert scheduler["may_dispatch_multiple_updates_per_invocation"] is True
    assert scheduler["machine_spans"]["slot_dispatch"]["sha256"] == (
        "a3fcaf6ea972f5f3e62f44cbaaedb0a694c08dc2966585165078bfbb84d21f71"
    )

    assert promotion["physics_manager_controller_owner_proven"] is True
    assert promotion["manager_auto_update_configuration_proven"] is True
    assert promotion["render_frame_cadence_proven"] is False
    assert promotion["one_manager_update_per_render_frame_proven"] is False
    assert promotion["exact_controller_wakeup_frequency_proven"] is False
    assert promotion["config_value_6_is_frequency_proven"] is False


def test_owner_path_joins_previous_process1_virtual_dispatch_contract() -> None:
    payload = _load(EVIDENCE)
    prior = _load(PRIOR)
    path = payload["promoted_owner_path"]

    assert prior["format"] == "SHIFT.Process1Fun0079b2d0VirtualDispatch/1"
    assert prior["ready"] is True
    assert "FUN_00713050" in path
    assert "SHIFT.Process1Fun0079b2d0VirtualDispatch/1" in path
    assert path[-2:] == ["FUN_0079b2d0", "FUN_00770e80"]


def test_documentation_preserves_fail_closed_cadence_boundary() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert '"Controller #1"' in text
    assert "`Physics Manager`" in text
    assert "FUN_00647ef0" in text
    assert "vtable `+0x18`" in text
    assert "does **not** claim" in text
    assert "one Physics Manager update per rendered frame" in text
    assert "configuration value `6` is a frequency" in text
    assert "external wake/synchronization cadence" in text
