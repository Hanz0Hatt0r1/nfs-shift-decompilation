from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/process1_controller1_manager_apc_reachability.json"
DOC = ROOT / "docs/PROCESS_1_CONTROLLER1_MANAGER_APC_REACHABILITY.md"
ANALYZER = ROOT / "tools/ghidra/analyze_process1_controller1_manager_apc_reachability.py"


def load_evidence() -> dict[str, object]:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_controller1_has_exact_three_direct_startup_managers() -> None:
    payload = load_evidence()
    attached = payload["controller1_manager_attachments"]
    assert payload["format"] == "SHIFT.Process1Controller1ManagerApcReachability/1"
    assert payload["ready"] is True
    assert attached["startup_function"] == "thunk_FUN_00d36000"
    assert attached["attach_function"] == "FUN_006485b0"
    assert attached["direct_attached_manager_count"] == 3
    assert attached["managers"] == [
        "Physics Manager",
        "Camera Manager",
        "CameraScriptManager",
    ]


def test_default_update_slots_and_direct_closures_are_exact() -> None:
    payload = load_evidence()
    slots = payload["default_update_slots"]
    assert slots["Physics Manager"]["slot_0x18_target"] == "0x00711b50"
    assert slots["Camera Manager"]["slot_0x18_target"] == "0x0080c990"
    assert slots["Camera Manager"]["normalized_source_root"] == "FUN_0080c920"
    assert slots["Camera Manager"]["slot_target_is_jump_thunk"] is True
    assert slots["CameraScriptManager"]["slot_0x18_target"] == "0x0050b5d0"

    closures = payload["direct_named_call_closure"]
    expected_counts = {
        "FUN_00711b50": 2896,
        "FUN_0080c920": 428,
        "FUN_0050b5d0": 452,
    }
    for root, count in expected_counts.items():
        assert closures[root]["reachable_named_function_count"] == count
        assert closures[root]["known_async_file_target_hits"] == []
        assert closures[root]["read_write_file_ex_body_hits"] == []


def test_manager_apc_negative_result_keeps_indirect_frontier_open() -> None:
    payload = load_evidence()
    adjudication = payload["adjudication"]
    assert adjudication["all_three_controller1_default_manager_updates_checked"] is True
    assert adjudication["direct_named_path_to_known_async_file_initiators_proven"] is False
    assert adjudication["direct_named_path_to_readfileex_or_writefileex_proven"] is False
    assert adjudication["indirect_virtual_or_function_pointer_path_ruled_out"] is False
    assert adjudication["render_frame_equivalence_proven"] is False
    assert payload["next_blocker"]["process"] == 1

    doc = DOC.read_text(encoding="utf-8")
    assert "direct named-call" in doc
    assert "not a whole-program no-APC proof" in doc
    assert "queue object identity" in doc


def test_machine_spans_and_analyzer_are_fail_closed() -> None:
    payload = load_evidence()
    expected_hashes = {
        "controller1_three_manager_attach_block": "41fc5d4aa0d621d1b1f32af54087c85729b6647af7377c06d35fedea9620b2e2",
        "physics_manager_vtable_prefix": "293d9126240759ea921c9b79c0447bfcfdac61f0f37a9b57b5fd6659ec16b429",
        "camera_manager_vtable_prefix": "4d750ec25258427105a8e998620e277f456b2c116d766936f68a3242bd9a19d8",
        "camera_script_manager_vtable_prefix": "b41f45822227cc60999bf05de7e0e382e245ccd8d2fecd89866f8202ecb5d3d1",
        "camera_manager_update_thunk": "9cc93e53ab12b3dbfb32b000cab1c98e0ee480a32b4bab6d5ca0d7d06b1590bc",
    }
    spans = payload["machine_spans"]
    assert {name: span["sha256"] for name, span in spans.items()} == expected_hashes

    analyzer = ANALYZER.read_text(encoding="utf-8")
    assert 'expected_counts = {' in analyzer
    assert '"FUN_00711b50": 2896' in analyzer
    assert '"FUN_0080c920": 428' in analyzer
    assert '"FUN_0050b5d0": 452' in analyzer
    assert 'raise ValueError(f"direct APC/file-I/O reachability appeared for {root}")' in analyzer
