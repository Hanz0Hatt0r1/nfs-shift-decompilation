import importlib.util
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1d_slot3_exact_carrier_indirect_calls.py"
EVIDENCE = ROOT / "evidence" / "p1d_slot3_exact_carrier_indirect_call_surface.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_exact_carrier_indirect", TOOL)
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_pinned_retail_surface():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["carrier_set"]["count"] == 16
    assert data["carrier_set"]["functions"][-1] == {
        "address": "0x00765c40",
        "name": "FUN_00765c40",
        "size": 2249,
        "mnemonic_sha256": "dcebcb4d773245033351265d65f7e2212cb60d097f323b84379bd2000a5a1df4",
    }
    assert data["indirect_surface"]["whole_index_indirect_call_edge_count"] == 19500
    assert data["indirect_surface"]["carrier_indirect_call_edge_count"] == 0
    assert data["adjudication"]["known_exact_carrier_indirect_call_edge_surface_complete"] is True
    assert data["adjudication"]["known_exact_carrier_indirect_call_edge_surface_empty"] is True


def test_global_gates_remain_fail_closed():
    a = json.loads(EVIDENCE.read_text(encoding="utf-8"))["adjudication"]
    assert a["stored_or_escaped_aliases_ruled_out"] is False
    assert a["indirect_entry_into_carriers_ruled_out"] is False
    assert a["callbacks_registered_outside_carriers_ruled_out"] is False
    assert a["global_indirect_dispatch_ruled_out"] is False
    assert a["slot3_writer_provenance_proven"] is False
    assert a["p1_3d_complete"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7


def test_synthetic_indirect_edge_is_not_hidden(monkeypatch, tmp_path):
    m = load_module()
    db_path = tmp_path / "shift.sqlite"
    db = sqlite3.connect(db_path)
    db.execute("CREATE TABLE metadata(key TEXT,value TEXT)")
    db.execute("CREATE TABLE functions(address TEXT,name TEXT,raw_json TEXT)")
    db.execute("CREATE TABLE calls(caller TEXT,callee TEXT,callsite TEXT,kind TEXT,raw_json TEXT)")
    db.execute("INSERT INTO metadata VALUES('format','SHIFT.GhidraSQLiteIndex/1')")
    for addr, name in m.CARRIERS.items():
        size, digest = m.EXPECTED[addr]
        db.execute("INSERT INTO functions VALUES(?,?,?)", (addr, name, json.dumps({"size":size,"mnemonic_sha256":digest})))
    db.execute("INSERT INTO calls VALUES(?,?,?,?,?)", ("0x00765c40","","0x00765d00","call",json.dumps({"from_function":"0x00765c40","from_name":"FUN_00765c40","instruction":"0x00765d00","indirect":True,"to":None,"to_name":None})))
    db.commit(); db.close()
    monkeypatch.setattr(m, "sha256", lambda path: m.SQLITE_SHA256)
    result = m.analyze(db_path)
    assert result["indirect_surface"]["whole_index_indirect_call_edge_count"] == 1
    assert result["indirect_surface"]["carrier_indirect_call_edge_count"] == 1
    assert result["adjudication"]["known_exact_carrier_indirect_call_edge_surface_empty"] is False
