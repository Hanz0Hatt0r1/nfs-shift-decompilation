import importlib.util
import json
import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1d_slot3_fun00758810_source.py"
EVIDENCE = ROOT / "evidence" / "p1d_slot3_fun00758810_source_closure.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_758810", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pinned_object_identity_and_destinations():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["entry"] == {
        "caller": "FUN_0076d100",
        "callsite": "0x0076d193",
        "callee": "FUN_00758810",
        "receiver": "HDVehicle",
        "callee_size": 347,
    }
    identity = data["object_identity"]
    assert identity["fuel_tank_pointer_field"] == "HDVehicle+0x280"
    assert identity["selected_BMW_SDF_fuel_tank_body_index"] == 9
    assert identity["selected_BMW_chassis_BODY0_index"] == 0
    assert identity["fuel_tank_is_chassis_BODY0"] is False
    effect = data["callee_effect"]
    assert effect["direct_persistent_write_owner"] == "fuel_tank BODY record"
    assert effect["direct_persistent_write_offsets"] == ["+0x60", "+0x68", "+0x70"]
    assert effect["selected_slot3_write_found"] is False


def test_global_gates_remain_fail_closed():
    a = json.loads(EVIDENCE.read_text(encoding="utf-8"))["adjudication"]
    assert a["slot3_fun0076d100_to_fun00758810_exact_root_branch_complete"] is True
    assert a["fun00758810_selected_slot3_writer_found"] is False
    assert a["deeper_direct_aliases_ruled_out"] is False
    assert a["stored_or_escaped_aliases_ruled_out"] is False
    assert a["indirect_callback_aliases_ruled_out"] is False
    assert a["slot3_writer_provenance_proven"] is False
    assert a["p1_3d_complete"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7


def test_source_and_sqlite_join_synthetic(monkeypatch, tmp_path):
    m = load_module()
    source = tmp_path / "SHIFT.exe.c"
    source.write_text(
        '''void __thiscall FUN_007615c0(void *this,char *param_1)\n{\n  iVar3 = FUN_007b3da0(*(void **)((int)this + 0x339c),"fuel_tank");\n  *(int *)((int)this + 0x280) = iVar3;\n}\n\nvoid __thiscall FUN_007618f0(){}\n\nvoid __thiscall FUN_0076d100(void *this,char param_1)\n{\n  FUN_00758810((int)this);\n}\n\nvoid __fastcall FUN_0076d3c0(){}\n\nvoid __fastcall FUN_00758810(int param_1)\n{\n  FUN_007aefb0((void *)(*(int *)(param_1 + 0x33a0) + 0xd4),(double *)(param_1 + 0x268),&local_30);\n  pdVar4 = *(double **)(param_1 + 0x280);\n  iVar1 = *(int *)(param_1 + 0x280);\n  *(double *)(iVar1 + 0x60) = *(double *)(iVar1 + 0x60) + local_48;\n  *(double *)(iVar1 + 0x68) = *(double *)(iVar1 + 0x68) + local_40;\n  *(double *)(iVar1 + 0x70) = *(double *)(iVar1 + 0x70) + local_38;\n  FUN_007baaf0(*(void **)(param_1 + 0x33a0),&local_30,&local_48);\n}\n\nvoid __thiscall FUN_00758970(){}\n''',
        encoding="utf-8",
    )
    database = tmp_path / "shift.sqlite"
    db = sqlite3.connect(database)
    db.execute("CREATE TABLE metadata(key TEXT,value TEXT)")
    db.execute("CREATE TABLE functions(address TEXT,name TEXT,raw_json TEXT)")
    db.execute("CREATE TABLE calls(caller TEXT,callee TEXT,callsite TEXT,kind TEXT,raw_json TEXT)")
    db.execute("INSERT INTO metadata VALUES('format','SHIFT.GhidraSQLiteIndex/1')")
    db.execute(
        "INSERT INTO functions VALUES(?,?,?)",
        ("0x00758810", "FUN_00758810", json.dumps({"name":"FUN_00758810","size":347})),
    )
    db.execute(
        "INSERT INTO calls VALUES(?,?,?,?,?)",
        ("0x0076d100", "", "0x0076d193", "call", json.dumps({
            "from_function":"0x0076d100", "instruction":"0x0076d193",
            "to":"0x00758810", "indirect":False,
        })),
    )
    db.commit(); db.close()
    resource = tmp_path / "resource.json"
    resource.write_text(json.dumps({
        "format":m.RESOURCE_FORMAT, "ready":True,
        "sdf":{"bodies":[{"index":0,"name":"body"},{"index":9,"name":"fuel_tank"}]},
    }), encoding="utf-8")
    body = tmp_path / "body.json"
    body.write_text(json.dumps({
        "format":m.BODY0_FORMAT, "ready":True,
        "identity_join":{"chassis_BODY_pointer_field":"HDVehicle+0x33a0","destination_is_retail_BMW_chassis_BODY0":True},
    }), encoding="utf-8")
    real_sha = m.sha256
    monkeypatch.setattr(m, "sha256", lambda path: m.SOURCE_SHA256 if path == source else (m.SQLITE_SHA256 if path == database else real_sha(path)))
    result = m.analyze(source, database, resource, body)
    assert result["callee_effect"]["selected_slot3_write_found"] is False
    assert result["object_identity"]["fuel_tank_is_chassis_BODY0"] is False


def test_fuel_tank_identity_drift_fails_closed(monkeypatch, tmp_path):
    m = load_module()
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["object_identity"]["pointer_fields_are_embedded_target_bytes"] is False
