import importlib.util
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1a_slot01_named_memory_frontier.py"
EVIDENCE = ROOT / "evidence" / "p1a_p13a_slot01_named_memory_frontier.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1a_named_memory", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_v1_db(path: Path, calls: list[dict]) -> None:
    db = sqlite3.connect(path)
    try:
        db.execute("CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
        db.execute("INSERT INTO metadata VALUES('format','SHIFT.GhidraSQLiteIndex/1')")
        db.execute("CREATE TABLE calls(caller TEXT,callee TEXT,callsite TEXT,kind TEXT,raw_json TEXT NOT NULL)")
        for rec in calls:
            db.execute(
                "INSERT INTO calls VALUES(?,?,?,?,?)",
                ("", "", rec["instruction"], "indirect" if rec.get("indirect") else "direct", json.dumps(rec)),
            )
        db.commit()
    finally:
        db.close()


def edge(src, dst, site, *, indirect=False):
    return {
        "from_function": src,
        "from_name": src,
        "instruction": site,
        "to": dst,
        "to_name": dst,
        "indirect": indirect,
    }


def test_nearest_named_memory_paths_use_shortest_direct_edges(tmp_path):
    module = load_module()
    db = tmp_path / "index.sqlite"
    make_v1_db(
        db,
        [
            edge("ROOT", "A", "0x1000"),
            edge("A", "B", "0x1010"),
            edge("B", "_memcpy_s", "0x1020"),
            edge("ROOT", "C", "0x1030"),
            edge("C", "_memset", "0x1040"),
            edge("ROOT", "_memmove", "0x1050", indirect=True),
        ],
    )
    payload = module.analyze(db, roots=("ROOT",), max_depth=4)
    result = payload["root_results"][0]
    assert result["copy_family"]["nearest_depth"] == 3
    assert result["copy_family"]["nearest_symbols"] == ["_memcpy_s"]
    assert result["copy_family"]["nearest_paths"][0]["nodes"] == ["ROOT", "A", "B", "_memcpy_s"]
    assert result["set_family"]["nearest_depth"] == 2
    assert result["set_family"]["nearest_paths"][0]["callsites"] == ["0x1030", "0x1040"]
    assert "_memmove" not in result["copy_family"]["nearest_symbols"]


def test_invalid_depth_is_rejected(tmp_path):
    module = load_module()
    db = tmp_path / "index.sqlite"
    make_v1_db(db, [])
    try:
        module.analyze(db, roots=("ROOT",), max_depth=0)
    except ValueError as exc:
        assert "max_depth" in str(exc)
    else:
        raise AssertionError("invalid max depth accepted")


def test_pinned_drive_result_keeps_slot_gates_fail_closed():
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.P1A.P13ASlot01NamedMemoryFrontierEvidence/1"
    assert payload["authority"]["source_index_sha256"] == "ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
    summary = payload["summary"]
    assert summary["wheel_update_root_nearest_copy_depth"] == 10
    assert summary["physics_pass_root_nearest_copy_depth"] == 6
    assert summary["four_wheel_feedback_root_nearest_copy_depth"] == 7
    assert summary["outer_scheduler_root_nearest_copy_depth"] == 7
    assert summary["named_copy_or_set_within_depth4_any_root"] is False
    adj = payload["adjudication"]
    assert adj["named_memory_navigation_frontier_captured"] is True
    assert adj["slot0_selected_root_alias_callee_bulk_copy_complete"] is False
    assert adj["slot1_selected_root_alias_callee_bulk_copy_complete"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
