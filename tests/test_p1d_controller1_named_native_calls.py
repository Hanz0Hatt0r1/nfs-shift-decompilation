import importlib.util
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1d_controller1_named_native_calls.py"
EVIDENCE = ROOT / "evidence" / "p1d_controller1_named_native_call_surface.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_named_native", TOOL)
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
            """
        )
        rows = [
            {"from_function":"0x00662880","instruction":"0x00662890","to":"0x1000","to_name":"FUN_00001000","indirect":False},
            {"from_function":"0x1000","instruction":"0x1004","to":"0x2000","to_name":"NtQueueApcThread","indirect":False},
            {"from_function":"0x3000","instruction":"0x3004","to":"0x4000","to_name":"RtlUnwind","indirect":False},
            {"from_function":"0x00662880","instruction":"0x006628a0","to":"0x5000","to_name":"ZwQueueApcThread","indirect":True},
        ]
        for rec in rows:
            db.execute(
                "INSERT INTO calls VALUES(?,?,?,?,?)",
                (rec["from_function"], "", rec["instruction"], "indirect" if rec["indirect"] else "direct", json.dumps(rec)),
            )
        db.commit()
    finally:
        db.close()


def test_named_native_surface_distinguishes_reachable_and_indirect(tmp_path):
    module = load_module()
    db = tmp_path / "shift.sqlite"
    make_db(db)
    payload = module.analyze(db)
    assert payload["counts"] == {
        "direct_named_native_call_count": 2,
        "unique_named_native_target_count": 2,
        "direct_worker_reachable_named_native_call_count": 1,
        "apc_capable_name_match_count": 1,
        "direct_worker_reachable_apc_capable_name_match_count": 1,
    }
    rows = {row["target_name"]: row for row in payload["calls"]}
    assert rows["NtQueueApcThread"]["direct_worker_reachable_caller"] is True
    assert rows["NtQueueApcThread"]["shortest_direct_path_to_caller"] == ["0x00662880", "0x1000"]
    assert rows["RtlUnwind"]["direct_worker_reachable_caller"] is False
    adj = payload["adjudication"]
    assert adj["direct_named_native_call_surface_bounded"] is True
    assert adj["direct_worker_reachable_named_native_surface_contains_apc_target_name"] is True
    assert adj["direct_syscall_surface_ruled_out"] is False
    assert adj["indirect_ntdll_pointer_surface_ruled_out"] is False
    assert adj["controller1_timing_exhaustive"] is False
    assert adj["external_provider_count"] == 7


def test_pinned_retail_named_native_surface_is_negative_for_controller1_apc():
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.P1D.Controller1NamedNativeCallSurface/1"
    assert payload["counts"] == {
        "direct_named_native_call_count": 4,
        "unique_named_native_target_count": 1,
        "direct_worker_reachable_named_native_call_count": 0,
        "apc_capable_name_match_count": 0,
        "direct_worker_reachable_apc_capable_name_match_count": 0,
    }
    assert {row["target_name"] for row in payload["calls"]} == {"RtlUnwind"}
    assert all(row["direct_worker_reachable_caller"] is False for row in payload["calls"])
    adj = payload["adjudication"]
    assert adj["direct_named_native_surface_adds_no_controller1_apc_candidate"] is True
    assert adj["direct_syscall_surface_ruled_out"] is False
    assert adj["indirect_ntdll_pointer_surface_ruled_out"] is False
    assert adj["controller1_timing_exhaustive"] is False
    assert adj["p1_3d_complete"] is False
    assert adj["external_provider_count"] == 7
