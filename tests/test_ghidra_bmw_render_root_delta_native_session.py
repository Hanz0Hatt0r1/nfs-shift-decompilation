from __future__ import annotations

import hashlib
import importlib.util
import json
import struct
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "ghidra" / "analyze_bmw_render_root_delta_native_session.py"
SPEC = importlib.util.spec_from_file_location("bmw_delta", TOOL)
assert SPEC is not None and SPEC.loader is not None
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def _db(tmp_path: Path) -> Path:
    db = tmp_path / "db"
    db.mkdir()
    (db / "manifest.json").write_text(json.dumps({"format": module.DB_FORMAT, "program": module.PROGRAM}))
    (db / "binary.json").write_text(json.dumps({"format": module.DB_FORMAT, "program_name": module.PROGRAM, "executable_md5": module.PE_MD5}))
    return db


def test_analyze_positive_materializes_exact_zero_delta(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    db = _db(tmp_path)
    source = tmp_path / "SHIFT.exe.c"
    pe = tmp_path / "SHIFT.exe"
    source.write_text("fixture")
    pe.write_bytes(b"fixture")
    monkeypatch.setattr(module, "_validate_functions", lambda _: {"FUN_00795d60": {"address": "0x00795d60"}})
    monkeypatch.setattr(module, "_validate_callgraph", lambda _: {"required_edges_ready": True, "pre_InitVehicle_chain_contains_global_writer": False})
    monkeypatch.setattr(module, "_validate_source", lambda _: {"constructor_zero_offsets": module.DELTA_OFFSETS})
    monkeypatch.setattr(module, "_pe_zero_fill", lambda _p, _a: {"md5": module.PE_MD5, "zero_fill_globals": [{"initial_value": 0.0}] * 3})

    report = module.analyze(db, source, pe, role_index=0, fresh_process_bootstrap=True, session_target=module.SESSION)
    assert report["format"] == module.FORMAT
    assert report["ready"] is True
    assert report["delta_local"]["values_xyz"] == [0.0, 0.0, 0.0]
    assert report["handoff"]["selected_BMW_render_root_delta_numeric_ready"] is True
    assert report["handoff"]["outer_vehicle_root_to_VHF_relation_numeric_matrix_ready"] is False
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False


def test_rejects_nonprimary_role_before_numeric_promotion(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    db = _db(tmp_path)
    with pytest.raises(ValueError, match="primary role/index 0"):
        module.analyze(db, tmp_path / "x", tmp_path / "y", role_index=1, fresh_process_bootstrap=True, session_target=module.SESSION)


def test_rejects_nonfresh_restart_scope(tmp_path: Path):
    db = _db(tmp_path)
    with pytest.raises(ValueError, match="fresh process bootstrap"):
        module.analyze(db, tmp_path / "x", tmp_path / "y", role_index=0, fresh_process_bootstrap=False, session_target=module.SESSION)


def test_rejects_session_target_drift(tmp_path: Path):
    db = _db(tmp_path)
    with pytest.raises(ValueError, match="session_target"):
        module.analyze(db, tmp_path / "x", tmp_path / "y", role_index=0, fresh_process_bootstrap=True, session_target="other")


def test_callgraph_requires_exact_global_writer_caller_set(tmp_path: Path):
    path = tmp_path / "callgraph.jsonl"
    rows = []
    for src, dst in sorted(module.REQUIRED_EDGES):
        rows.append({"from_function": src, "to": dst, "indirect": False})
    for src in sorted(module.GLOBAL_WRITER_CALLERS):
        rows.append({"from_function": src, "to": module.GLOBAL_WRITER, "indirect": False})
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    report = module._validate_callgraph(path)
    assert report["pre_InitVehicle_chain_contains_global_writer"] is False

    rows.append({"from_function": "0x0074ddc3", "to": module.GLOBAL_WRITER, "indirect": False})
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    with pytest.raises(ValueError, match="direct-caller set drift"):
        module._validate_callgraph(path)


def _synthetic_pe() -> bytearray:
    # Small PE32 with .data VirtualSize spanning the retail target RVAs but tiny raw data.
    data = bytearray(0x800)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3C, 0x80)
    data[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<HHIIIHH", data, 0x84, 0x14C, 1, 0, 0, 0, 0xE0, 0)
    opt = 0x98
    struct.pack_into("<H", data, opt, 0x10B)
    struct.pack_into("<I", data, opt + 28, 0x00400000)
    sec = opt + 0xE0
    data[sec:sec + 8] = b".data\0\0\0"
    struct.pack_into("<IIII", data, sec + 8, 0x167040, 0x781000, 0x200, 0x400)
    return data


def test_pe_zero_fill_proves_globals_are_loader_zeroed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    path = tmp_path / "SHIFT.exe"
    payload = _synthetic_pe()
    path.write_bytes(payload)
    monkeypatch.setattr(module, "PE_MD5", hashlib.md5(payload).hexdigest())
    report = module._pe_zero_fill(path, module.GLOBAL_TRIPLE)
    assert [row["initial_value"] for row in report["zero_fill_globals"]] == [0.0, 0.0, 0.0]
    assert all(row["section"] == ".data" for row in report["zero_fill_globals"])


def test_source_witness_checks_constructor_and_primary_override(tmp_path: Path):
    source = tmp_path / "SHIFT.exe.c"
    defs = {
        "FUN_0079bfd0": "void FUN_0079bfd0()\n{\n  param_1[0x67] = 0; param_1[0x68] = 0; param_1[0x69] = 0;\n}",
        "FUN_0074ddc3": "void FUN_0074ddc3()\n{\n  FUN_00797fd0((void *)x,*(int *)(iVar1 + 0x10),'\\0',1); if (*(int *)(iVar1 + 0x10) == 0) { DAT_00c10b34 = x; } FUN_00798df0(x,0);\n}",
        "FUN_00797fd0": "void FUN_00797fd0()\n{\n  *(int *)((int)this + 0x234) = param_1;\n}",
        "FUN_00798df0": "void FUN_00798df0()\n{\n  FUN_00795d60(this,param_1,local_2390,*(void **)((int)this + 0x1d00),param_1);\n}",
        "FUN_00795d60": "void FUN_00795d60()\n{\n  if (*(int *)((int)param_1 + 0x234) == 0) { local_3c = local_28 - (float)_DAT_00c16ab0; local_38 = *(float *)((int)param_1 + 0x1a0) - (float)_DAT_00c16ab8; local_34 = *(float *)((int)param_1 + 0x1a4) - (float)_DAT_00c16ac0; *(float *)((int)param_1 + 0x19c) = local_3c; *(float *)((int)param_1 + 0x1a0) = local_38; *(float *)((int)param_1 + 0x1a4) = local_34; }\n}",
        "FUN_00715240": "void FUN_00715240()\n{\n  FUN_007125e0(piVar5); FUN_0074e1a0(piVar5);\n}",
        "FUN_0078ef00": "void FUN_0078ef00()\n{\n  FUN_007afd20(x,y,(double *)&DAT_00c16ab0,&local_38);\n}",
    }
    source.write_text("\n\n".join(defs.values()))
    report = module._validate_source(source)
    assert report["constructor_zero_offsets"] == module.DELTA_OFFSETS
    assert report["fresh_construct_before_restart"] is True
