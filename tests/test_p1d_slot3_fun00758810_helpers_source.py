import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1d_slot3_fun00758810_helpers_source.py"
EVIDENCE = ROOT / "evidence" / "p1d_slot3_fun00758810_helper_effects.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_758810_helpers", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pinned_helper_effects_are_disjoint_from_slot3():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1D.Slot3Fun00758810HelperEffects/1"
    assert data["helpers"]["FUN_007aefb0"]["writes_only_output_param"] is True
    assert data["helpers"]["FUN_00753590"]["FUN_00758810_outputs_are_stack_local"] is True
    assert data["helpers"]["FUN_007535f0"]["FUN_00758810_outputs_are_stack_local"] is True
    assert data["helpers"]["FUN_007baaf0"]["direct_write_offsets"] == [
        "+0x48", "+0x50", "+0x58", "+0x60", "+0x68", "+0x70"
    ]
    assert data["helpers"]["FUN_007baaf0"]["writes_HDVehicle_slot3"] is False


def test_helper_gate_is_narrow_and_global_gates_stay_closed():
    a = json.loads(EVIDENCE.read_text(encoding="utf-8"))["adjudication"]
    assert a["fun00758810_direct_helper_side_effect_surface_complete"] is True
    assert a["helper_selected_slot3_writer_found"] is False
    assert a["slot3_writer_provenance_proven"] is False
    assert a["p1_3d_complete"] is False
    assert a["external_provider_count"] == 7


def test_helper_analyzer_rejects_source_hash_drift(monkeypatch, tmp_path):
    module = load_module()
    source = tmp_path / "SHIFT.exe.c"
    source.write_text("not retail", encoding="utf-8")
    monkeypatch.setattr(module, "sha256", lambda path: "0" * 64)
    try:
        module.analyze(source)
    except ValueError as exc:
        assert "unexpected SHIFT.exe.c SHA-256" in str(exc)
    else:
        raise AssertionError("source hash drift must fail closed")
