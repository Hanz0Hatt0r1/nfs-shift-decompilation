import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/ghidra/analyze_p1d_slot3_fun007555b0_interior_alias_pe.py"
EVIDENCE = ROOT / "evidence/p1d_slot3_fun007555b0_interior_alias_closure.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_7555b0_alias", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_machine_body_and_receiver_translation_are_pinned():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1D.Slot3Fun007555b0InteriorAliasClosure/1"
    assert data["path"]["callee_receiver"] == "selected wheel+0x80"
    assert data["path"]["selected_target_from_callee_receiver"] == "+0x4b8"
    callee = data["callee"]
    assert callee["size"] == 364
    assert callee["instruction_count"] == 115
    assert callee["machine_bytes_sha256"] == "43aff676522a3b6b558980b56e29e289926893d266bf71e063b25d401d1e4881"
    assert callee["receiver_relative_memory_offsets"][-1] == "+0x260"
    assert "+0x4b8" not in callee["receiver_relative_memory_offsets"]


def test_write_surface_stays_far_from_selected_target():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["callee"]["receiver_relative_write_offsets"] == ["+0x248", "+0x250", "+0x258", "+0x260"]
    assert data["selected_wheel_write_offsets"] == ["+0x2c8", "+0x2d0", "+0x2d8", "+0x2e0"]
    assert data["callee"]["direct_call_count"] == 0
    assert data["callee"]["receiver_value_reconstruction_or_mutation_count"] == 0


def test_global_alias_gates_remain_fail_closed():
    gates = json.loads(EVIDENCE.read_text(encoding="utf-8"))["adjudication"]
    assert gates["fun007555b0_wheel_80_interior_alias_subset_complete"] is True
    assert gates["fun007555b0_reconstructs_exact_wheel_root"] is False
    assert gates["fun007555b0_selected_slot3_target_writer_found"] is False
    assert gates["fun007555b0_forwards_interior_or_reconstructed_root_to_callee"] is False
    assert gates["other_callee_created_aliases_ruled_out"] is False
    assert gates["callee_created_aliases_ruled_out"] is False
    assert gates["stored_or_escaped_aliases_ruled_out"] is False
    assert gates["slot3_writer_provenance_proven"] is False
    assert gates["p1_3d_complete"] is False
    assert gates["external_provider_count"] == 7


def test_target_translation_is_exact():
    module = load_module()
    assert module.TARGET_FROM_WHEEL == 0x538
    assert module.RECEIVER_FROM_WHEEL == 0x80
    assert module.TARGET_FROM_RECEIVER == 0x4B8
