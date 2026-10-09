import importlib.util
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1d_controller1_module_literal_reachability.py"
EVIDENCE = ROOT / "evidence" / "p1d_controller1_module_literal_reachability.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_module_literal", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_db(path: Path) -> None:
    db = sqlite3.connect(path)
    try:
        db.executescript(
            """
            CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            INSERT INTO metadata VALUES('format','SHIFT.GhidraSQLiteIndex/1');
            CREATE TABLE calls(caller TEXT,callee TEXT,callsite TEXT,kind TEXT,raw_json TEXT NOT NULL);
            CREATE TABLE strings(value TEXT,address TEXT,containing_function TEXT,raw_json TEXT NOT NULL);
            """
        )
        calls = [
            {"from_function":"0x00662880","from_name":"FUN_00662880","instruction":"0x00662890","to":"0x1000","to_name":"FUN_00001000","indirect":False},
            {"from_function":"0x1000","from_name":"FUN_00001000","instruction":"0x1004","to":"0x2000","to_name":"FUN_00002000","indirect":False},
            {"from_function":"0x2000","from_name":"FUN_00002000","instruction":"0x2004","to":"0x3000","to_name":"GetProcAddress","indirect":False},
            {"from_function":"0x4000","from_name":"FUN_00004000","instruction":"0x4004","to":"0x3000","to_name":"GetProcAddress","indirect":False},
        ]
        for rec in calls:
            db.execute(
                "INSERT INTO calls VALUES(?,?,?,?,?)",
                (rec["from_function"], "", rec["instruction"], "direct", json.dumps(rec)),
            )
        for value, address, owner in [
            ("KERNEL32.DLL", "0x5000", "0x2000"),
            ("EncodePointer", "0x5010", "0x2000"),
            ("ntdll.dll", "0x5020", "0x4000"),
        ]:
            raw = json.dumps({"value":value,"address":address,"functions":[owner]})
            db.execute("INSERT INTO strings VALUES(?,?,?,?)", (value,address,owner,raw))
        db.commit()
    finally:
        db.close()


def test_direct_reachable_module_owner_is_joined_to_resolver_surface(tmp_path):
    module = load_module()
    db = tmp_path / "shift.sqlite"
    make_db(db)
    payload = module.analyze(db)
    surface = payload["surface"]
    assert surface["unique_literal_owner_count"] == 2
    assert surface["direct_worker_reachable_literal_owner_count"] == 1
    assert surface["direct_worker_reachable_literal_owners_outside_getprocaddress_surface"] == 0
    reachable = [row for row in surface["owners"] if row["direct_worker_reachable"]]
    assert reachable[0]["function"] == "0x2000"
    assert reachable[0]["is_getprocaddress_caller"] is True
    assert reachable[0]["shortest_direct_path"] == ["0x00662880", "0x1000", "0x2000"]
    adj = payload["adjudication"]
    assert adj["direct_literal_module_surface_adds_no_new_candidate"] is True
    assert adj["peb_walk_without_literal_module_name_ruled_out"] is False
    assert adj["native_or_syscall_injection_ruled_out"] is False
    assert adj["external_provider_count"] == 7


def test_pinned_retail_evidence_stays_fail_closed():
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.P1D.Controller1ModuleLiteralReachability/1"
    surface = payload["surface"]
    assert surface["literal_row_count"] == 8
    assert surface["unique_literal_owner_count"] == 7
    assert surface["ntdll_literal_row_count"] == 0
    assert surface["direct_worker_reachable_literal_owner_count"] == 4
    assert surface["direct_worker_reachable_literal_owners_outside_getprocaddress_surface"] == 0
    reachable = [row for row in surface["owners"] if row["direct_worker_reachable"]]
    assert {row["function"] for row in reachable} == {
        "0x0090aa27", "0x0090aa9e", "0x0090abb8", "0x009189cd"
    }
    assert all(row["is_getprocaddress_caller"] for row in reachable)
    adj = payload["adjudication"]
    assert adj["direct_literal_module_name_surface_bounded"] is True
    assert adj["direct_literal_module_surface_adds_no_new_candidate"] is True
    assert adj["controller1_timing_exhaustive"] is False
    assert adj["p1_3d_complete"] is False
    assert adj["external_provider_count"] == 7
