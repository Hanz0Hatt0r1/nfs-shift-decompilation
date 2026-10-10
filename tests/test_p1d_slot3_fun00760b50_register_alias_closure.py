import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1d_slot3_fun00760b50_register_alias_pe.py"
EVIDENCE = ROOT / "evidence" / "p1d_slot3_fun00760b50_register_alias_closure.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_fun00760b50_register_alias", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pinned_fun00760b50_register_alias_does_not_explicitly_escape():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1D.Slot3Fun00760b50RegisterAliasClosure/1"
    assert data["upstream_contracts"] == [
        "SHIFT.P1D.Slot3ExactWheelDirectCarrierClosure/1",
        "SHIFT.P1D.Slot3RegisterAliasSubsetClosure/1",
    ]
    assert data["selected_slot3"]["wheel_receiver"] == "HDVehicle+0x2380"
    fn = data["function"]
    assert fn["root_capture"]["instruction"] == "mov esi,ecx"
    assert fn["esi_use_count"] == 35
    assert fn["post_capture_pre_restore_esi_use_count"] == 32
    assert fn["post_capture_pre_restore_esi_uses_are_memory_base_only"] is True
    assert fn["explicit_root_value_copy_after_capture_found"] is False
    assert fn["explicit_root_push_after_capture_found"] is False
    assert fn["explicit_root_nonlocal_store_after_capture_found"] is False
    assert fn["explicit_root_forward_to_direct_callee_found"] is False
    child = data["child_handoff"]
    assert child["source"] == "[wheel+0x420]"
    assert child["callee"] == "FUN_007ba860"
    assert child["is_exact_wheel_root"] is False


def test_global_alias_and_writer_gates_remain_fail_closed():
    a = json.loads(EVIDENCE.read_text(encoding="utf-8"))["adjudication"]
    assert a["fun00760b50_exact_selected_wheel_register_alias_subset_complete"] is True
    assert a["fun00760b50_exact_selected_wheel_explicit_register_escape_found"] is False
    assert a["fun00760b50_child_pointer_handoff_distinguished"] is True
    assert a["machine_register_alias_storage_ruled_out"] is False
    assert a["callee_created_aliases_ruled_out"] is False
    assert a["stored_or_escaped_aliases_ruled_out"] is False
    assert a["slot3_writer_provenance_proven"] is False
    assert a["p1_3d_complete"] is False
    assert a["external_provider_count"] == 7


def test_synthetic_explicit_register_copy_fails_closed(monkeypatch, tmp_path):
    m = load_module()
    direct = tmp_path / "direct.json"
    direct.write_text(json.dumps({
        "format": m.DIRECT_FORMAT,
        "ready": True,
        "authority": {"retail_executable_sha256": m.PE_SHA256},
        "selected_slot3": {"hdvehicle_offset": "0x2380", "local_target": "+0x538"},
        "paths": {"fun00760b50": {
            "receiver": "HDVehicle+0x2380",
            "target_overlap": False,
            "child_receiver_call": "FUN_007ba860 receives [wheel+0x420]",
        }},
    }), encoding="utf-8")
    register_subset = tmp_path / "register_subset.json"
    register_subset.write_text(json.dumps({
        "format": m.REGISTER_SUBSET_FORMAT,
        "ready": True,
        "selected_slot3": {"wheel_receiver": "HDVehicle+0x2380", "local_target": "+0x538"},
        "adjudication": {
            "machine_proven_register_alias_subset_complete": True,
            "other_register_aliases_ruled_out": False,
        },
    }), encoding="utf-8")
    exe = tmp_path / "SHIFT.exe"
    exe.write_bytes(b"synthetic")
    ins = {m.START: "push ebx"}
    for site in m.EXPECTED_ESI_USE_SITES:
        ins[site] = "fld QWORD PTR [esi+0x350]"
    for row in m.EXPECTED_CALLS:
        ins[int(row["site"], 16)] = f"call {row['target']}"
    ins.update(m.ANCHORS)
    ins[0x00760B6C] = "mov eax,esi"
    monkeypatch.setattr(m, "sha256", lambda path: m.PE_SHA256)
    monkeypatch.setattr(m, "disassemble", lambda exe, objdump: ins)
    try:
        m.analyze(exe, direct, register_subset)
    except ValueError as exc:
        assert "explicit exact-wheel register escape candidate" in str(exc)
    else:
        raise AssertionError("explicit selected-wheel register copy must fail closed")
