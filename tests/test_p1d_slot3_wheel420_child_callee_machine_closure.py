import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/ghidra/analyze_p1d_slot3_wheel420_child_callees_pe.py"
EVIDENCE = ROOT / "evidence/p1d_slot3_wheel420_child_callee_machine_closure.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_wheel420_child", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def data():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_entry_receiver_identity_is_child_not_wheel():
    d = data()
    assert d["format"] == "SHIFT.P1D.Slot3Wheel420ChildCalleeMachineClosure/1"
    rows = d["entry_paths"]
    assert rows[0]["receiver_identity"] == "child=[wheel+0x420]"
    assert rows[1]["receiver_identity"] == "child+0xd4"
    assert rows[2]["receiver_identity"] == "child+0xd4"
    assert rows[0]["callsite"] == "0x00760d4b"
    assert rows[1]["callsite"] == "0x00755fb0"
    assert rows[2]["callsite"] == "0x00755fd1"


def test_machine_bodies_and_nested_calls_are_pinned():
    d = data(); b = d["machine_bodies"]
    expected = {
        "FUN_007ba860": (73, 21, "1ad69d788cf63b85923c0340516a83601266ec2c0317de3c9b27f42a9d68c476"),
        "FUN_007ba7e0": (114, 44, "c44dac55776ac266f00822c40762b2d452226a043a0bd687209b67d3bbe947a4"),
        "FUN_007af0a0": (83, 33, "8cd039935dbbe493db7742f7af1859d9abcc7d9c40f212c3f2fa331e992c52cc"),
        "FUN_007af010": (35, 15, "f3256201dee28b97260576ee14c522e236a44d1808516ed8e42efd2e2e2e8324"),
        "FUN_007aefb0": (83, 33, "76c52235cce08d3ec131d43e1b62cda623ac8528944e44f902846a0a71b14f29"),
    }
    for name, (size, insns, sha) in expected.items():
        assert b[name]["size"] == size
        assert b[name]["instruction_count"] == insns
        assert b[name]["machine_bytes_sha256"] == sha
        assert b[name]["child_relative_gpr_load_count"] == 0
        assert b[name]["child_relative_gpr_store_count"] == 0
    assert b["FUN_007ba860"]["direct_calls"] == [{"callsite": "0x007ba8a0", "target": "0x007ba7e0"}]
    assert b["FUN_007ba7e0"]["direct_calls"] == [
        {"callsite": "0x007ba80d", "target": "0x007af0a0"},
        {"callsite": "0x007ba844", "target": "0x007aefb0"},
    ]


def test_child_effects_do_not_promote_selected_writer():
    d = data(); effects = d["child_effects"]
    assert effects["FUN_007ba860_writes"] == [
        "child+0x128 f32", "child+0x12c f32", "child+0x130 f32",
        "child+0x138 f64", "child+0x140 f64", "child+0x148 f64",
    ]
    assert effects["back_pointer_or_wheel_root_recovery_found"] is False
    assert effects["child_pointer_persistence_found"] is False
    assert effects["selected_slot3_target_writer_found"] is False


def test_global_gates_remain_fail_closed():
    g = data()["adjudication"]
    assert g["known_wheel_420_child_callee_subset_complete"] is True
    assert g["known_wheel_420_child_nested_direct_calls_complete"] is True
    assert g["known_wheel_420_child_back_pointer_recovery_found"] is False
    assert g["known_wheel_420_child_pointer_persistence_found"] is False
    assert g["known_wheel_420_child_selected_target_writer_found"] is False
    assert g["other_callee_created_aliases_ruled_out"] is False
    assert g["callee_created_aliases_ruled_out"] is False
    assert g["stored_or_escaped_aliases_ruled_out"] is False
    assert g["slot3_writer_provenance_proven"] is False
    assert g["p1_3d_complete"] is False
    assert g["external_provider_count"] == 7


def test_tool_constants_match_evidence_contract():
    m = load_module()
    assert m.FORMAT == "SHIFT.P1D.Slot3Wheel420ChildCalleeMachineClosure/1"
    assert set(m.FUNCS) == {"FUN_007ba860", "FUN_007ba7e0", "FUN_007af0a0", "FUN_007af010", "FUN_007aefb0"}
