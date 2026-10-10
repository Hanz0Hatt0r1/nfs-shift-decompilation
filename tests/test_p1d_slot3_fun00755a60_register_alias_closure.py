import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1d_slot3_fun00755a60_register_alias_pe.py"
EVIDENCE = ROOT / "evidence" / "p1d_slot3_fun00755a60_register_alias_closure.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_fun00755a60_register_alias", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pinned_fun00755a60_root_and_7c8_aliases_are_bounded():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1D.Slot3Fun00755a60RegisterAliasClosure/1"
    assert data["selected_slot3"]["wheel_receiver"] == "HDVehicle+0x2380"
    root = data["fun00755a60"]
    assert root["esi_use_count"] == 70
    assert root["exact_root_value_transfers_after_capture"] == [
        "0x00755db3 ECX=ESI -> 0x00755db5 FUN_00752fc0"
    ]
    assert root["unexpected_exact_root_transfer_found"] is False
    assert root["derived_subfield_alias"] == "0x00755c04 ECX=ESI+0x7c8"
    assert root["derived_subfield_alias_persists_to_call"] == "0x00755dae FUN_00753620"
    clamp = data["fun00753620"]
    assert clamp["receiver"] == "selected wheel+0x7c8"
    assert clamp["write_offsets"] == ["+0x0"]
    assert clamp["absolute_selected_wheel_write_offsets"] == ["+0x7c8"]
    assert clamp["direct_call_count"] == 0
    assert clamp["selected_target_overlap"] is False


def test_global_escape_and_writer_gates_remain_fail_closed():
    a = json.loads(EVIDENCE.read_text(encoding="utf-8"))["adjudication"]
    assert a["fun00755a60_exact_root_register_alias_subset_complete"] is True
    assert a["fun00755a60_unexpected_exact_root_register_escape_found"] is False
    assert a["fun00755a60_wheel_7c8_derived_alias_subset_complete"] is True
    assert a["fun00753620_selected_target_writer_found"] is False
    assert a["machine_register_alias_storage_ruled_out"] is False
    assert a["callee_created_aliases_ruled_out"] is False
    assert a["stored_or_escaped_aliases_ruled_out"] is False
    assert a["slot3_writer_provenance_proven"] is False
    assert a["p1_3d_complete"] is False
    assert a["external_provider_count"] == 7


def test_synthetic_extra_exact_root_transfer_fails_closed(monkeypatch, tmp_path):
    m = load_module()
    direct = tmp_path / "direct.json"
    direct.write_text(json.dumps({
        "format": m.DIRECT_FORMAT,
        "ready": True,
        "authority": {"retail_executable_sha256": m.PE_SHA256},
        "paths": {"fun00755a60": {
            "receiver": "HDVehicle+0x400+slot*0xa80",
            "slot3_receiver": "HDVehicle+0x2380",
            "exact_root_direct_forward": "FUN_00752fc0",
            "target_overlap": False,
            "leaf_has_direct_calls": False,
        }},
    }), encoding="utf-8")
    register = tmp_path / "register.json"
    register.write_text(json.dumps({
        "format": m.REGISTER_SUBSET_FORMAT,
        "ready": True,
        "adjudication": {
            "machine_proven_register_alias_subset_complete": True,
            "other_register_aliases_ruled_out": False,
        },
    }), encoding="utf-8")
    exe = tmp_path / "SHIFT.exe"
    exe.write_bytes(b"synthetic")
    root = {m.ROOT_START: "push ebx"}
    for site in m.EXPECTED_ESI_USE_SITES:
        root[site] = "fld QWORD PTR [esi+0x350]"
    anchors = {
        m.SAVE_SITE: "push esi",
        m.CAPTURE_SITE: "mov esi,ecx",
        m.DERIVED_SITE: "lea ecx,[esi+0x7c8]",
        m.DERIVED_CALL_SITE: "call 0x753620",
        m.ROOT_FORWARD_SITE: "mov ecx,esi",
        m.ROOT_FORWARD_CALL_SITE: "call 0x752fc0",
        m.RESTORE_SITE: "pop esi",
    }
    root.update(anchors)
    for site, text in m.EXPECTED_ECX_DERIVED_WINDOW:
        root[site] = text
    root[0x00755A87] = "mov eax,esi"
    clamp = {m.CLAMP_START: "push ebp"}
    clamp.update(m.EXPECTED_CLAMP)
    monkeypatch.setattr(m, "sha256", lambda path: m.PE_SHA256)
    monkeypatch.setattr(m, "disassemble", lambda exe, start, size, objdump: root if start == m.ROOT_START else clamp)
    try:
        m.analyze(exe, direct, register)
    except ValueError as exc:
        assert "unexpected exact-root register transfer" in str(exc)
    else:
        raise AssertionError("extra exact-root register transfer must fail closed")
