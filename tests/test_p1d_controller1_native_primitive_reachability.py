import importlib.util
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1d_controller1_native_primitive_reachability.py"
READINESS = ROOT / "evidence" / "p1d_controller1_native_primitive_reachability_readiness.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_native_reachability", TOOL)
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
        for rec in [
            {"from_function":"0x00662880","instruction":"0x00662890","to":"0x1000","indirect":False},
            {"from_function":"0x1000","instruction":"0x1004","to":"0x2000","indirect":False},
            {"from_function":"0x00662880","instruction":"0x006628a0","to":"0x3000","indirect":True},
        ]:
            db.execute(
                "INSERT INTO calls VALUES(?,?,?,?,?)",
                (rec["from_function"], "", rec["instruction"], "direct", json.dumps(rec)),
            )
        db.commit()
    finally:
        db.close()


def make_frontier(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "format": "SHIFT.P1D.Controller1NativeApcPrimitiveFrontier/1",
                "candidate_functions": [
                    {
                        "function": "FUN_00002000",
                        "function_address": "0x2000",
                        "manual_export_walk_candidate": True,
                        "direct_native_call_candidate": False,
                        "peb_access_sites": ["0x2004"],
                        "sysenter_sites": [],
                        "int2e_sites": [],
                    },
                    {
                        "function": "FUN_00003000",
                        "function_address": "0x3000",
                        "manual_export_walk_candidate": False,
                        "direct_native_call_candidate": True,
                        "peb_access_sites": [],
                        "sysenter_sites": ["0x3004"],
                        "int2e_sites": [],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def test_join_separates_direct_reachable_from_indirect_only_candidate(tmp_path):
    module = load_module()
    db = tmp_path / "shift.sqlite"
    frontier = tmp_path / "frontier.json"
    make_db(db)
    make_frontier(frontier)
    payload = module.analyze(frontier, db)
    assert payload["counts"] == {
        "primitive_candidate_function_count": 2,
        "direct_worker_reachable_candidate_count": 1,
        "direct_worker_reachable_manual_export_walk_candidate_count": 1,
        "direct_worker_reachable_native_transition_candidate_count": 0,
    }
    rows = {row["function_address"]: row for row in payload["candidate_functions"]}
    assert rows["0x2000"]["direct_worker_reachable"] is True
    assert rows["0x2000"]["shortest_direct_path"] == ["0x00662880", "0x1000", "0x2000"]
    assert rows["0x3000"]["direct_worker_reachable"] is False
    adj = payload["adjudication"]
    assert adj["direct_reachability_join_complete_for_frontier_candidates"] is True
    assert adj["unreachable_candidate_rejected_from_direct_worker_surface"] is True
    assert adj["reachable_candidate_presence_proves_apc_injection"] is False
    assert adj["indirect_callgraph_surface_ruled_out"] is False
    assert adj["controller1_timing_exhaustive"] is False
    assert adj["external_provider_count"] == 7


def test_wrong_frontier_format_is_rejected(tmp_path):
    module = load_module()
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"format":"wrong","candidate_functions":[]}), encoding="utf-8")
    try:
        module.load_frontier(bad)
    except ValueError as exc:
        assert "unexpected primitive frontier format" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_readiness_contract_remains_fail_closed():
    payload = json.loads(READINESS.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.P1D.Controller1NativePrimitiveReachabilityReadiness/1"
    assert payload["tooling_ready"] is True
    assert payload["retail_primitive_frontier_captured"] is False
    assert payload["retail_reachability_join_captured"] is False
    adj = payload["adjudication"]
    assert adj["manual_export_walking_ruled_out"] is False
    assert adj["native_or_syscall_apc_injection_ruled_out"] is False
    assert adj["controller1_timing_exhaustive"] is False
    assert adj["p1_3d_complete"] is False
    assert adj["external_provider_count"] == 7
