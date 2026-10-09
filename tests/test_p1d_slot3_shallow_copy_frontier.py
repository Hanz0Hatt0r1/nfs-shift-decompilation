import importlib.util
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1d_slot3_shallow_copy_frontier.py"
EVIDENCE = ROOT / "evidence" / "p1d_slot3_shallow_copy_frontier.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_slot3_copy", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_db(path: Path, calls: list[dict]) -> None:
    db = sqlite3.connect(path)
    try:
        db.execute("CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
        db.execute("INSERT INTO metadata VALUES('format','SHIFT.GhidraSQLiteIndex/1')")
        db.execute("CREATE TABLE calls(caller TEXT,callee TEXT,callsite TEXT,kind TEXT,raw_json TEXT NOT NULL)")
        for rec in calls:
            db.execute(
                "INSERT INTO calls VALUES(?,?,?,?,?)",
                (
                    rec.get("from_function", ""),
                    "",
                    rec.get("instruction", ""),
                    "indirect" if rec.get("indirect") else "direct",
                    json.dumps(rec),
                ),
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


def test_named_copy_is_found_with_exact_shortest_depth(tmp_path):
    module = load_module()
    db = tmp_path / "index.sqlite"
    make_db(
        db,
        [
            edge("ROOT", "A", "0x1000"),
            edge("A", "B", "0x1010"),
            edge("B", "_memcpy", "0x1020"),
        ],
    )
    payload = module.analyze(db, roots=("ROOT",), max_depth=4)
    result = payload["root_results"][0]
    assert result["named_copy_hit_count"] == 1
    hit = result["named_copy_hits"][0]
    assert hit["depth"] == 3
    assert hit["callee"] == "_memcpy"
    assert hit["path"] == ["ROOT", "A", "B", "_memcpy"]
    assert payload["adjudication"]["shallow_named_memcpy_memmove_surface_empty"] is False


def test_indirect_copy_edge_is_not_promoted_as_direct_reachability(tmp_path):
    module = load_module()
    db = tmp_path / "index.sqlite"
    make_db(db, [edge("ROOT", "_memmove", "0x2000", indirect=True)])
    payload = module.analyze(db, roots=("ROOT",), max_depth=4)
    assert payload["summary"]["named_copy_hits_within_depth"] == 0
    adj = payload["adjudication"]
    assert adj["shallow_named_memcpy_memmove_surface_empty"] is True
    assert adj["indirect_copy_dispatch_ruled_out"] is False


def test_depth_bound_does_not_become_semantic_rejection(tmp_path):
    module = load_module()
    db = tmp_path / "index.sqlite"
    make_db(
        db,
        [
            edge("ROOT", "A", "0x3000"),
            edge("A", "B", "0x3010"),
            edge("B", "C", "0x3020"),
            edge("C", "D", "0x3030"),
            edge("D", "memcpy", "0x3040"),
        ],
    )
    payload = module.analyze(db, roots=("ROOT",), max_depth=4)
    assert payload["summary"]["named_copy_hits_within_depth"] == 0
    adj = payload["adjudication"]
    assert adj["deeper_direct_copy_paths_ruled_out"] is False
    assert adj["slot3_writer_provenance_proven"] is False


def test_pinned_retail_frontier_counts_and_fail_closed_state():
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.P1D.Slot3ShallowCopyFrontier/1"
    assert payload["max_direct_call_depth"] == 4
    expected = {
        "FUN_00758b50": (23, {"0": 1, "1": 10, "2": 6, "3": 5, "4": 1}),
        "FUN_0076d100": (151, {"0": 1, "1": 8, "2": 41, "3": 52, "4": 49}),
        "FUN_00763570": (48, {"0": 1, "1": 8, "2": 6, "3": 10, "4": 23}),
        "FUN_00770e80": (325, {"0": 1, "1": 20, "2": 61, "3": 111, "4": 132}),
    }
    for result in payload["root_results"]:
        count, depths = expected[result["root"]]
        assert result["reachable_unique_node_count"] == count
        assert result["nodes_by_min_depth"] == depths
        assert result["named_copy_hit_count"] == 0
    assert payload["summary"]["named_copy_hits_within_depth"] == 0
    adj = payload["adjudication"]
    assert adj["shallow_named_memcpy_memmove_surface_empty"] is True
    assert adj["inline_or_custom_bulk_copy_ruled_out"] is False
    assert adj["indirect_copy_dispatch_ruled_out"] is False
    assert adj["deeper_direct_copy_paths_ruled_out"] is False
    assert adj["slot3_writer_provenance_proven"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
