import importlib.util
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "tools" / "ghidra" / "analyze_p1d_slot3_dispatch_carriers.py"
EVIDENCE = ROOT / "evidence" / "p1d_slot3_dispatch_carrier_boundary.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_slot3_dispatch_carriers", ANALYZER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_db(path: Path, calls: list[dict]) -> None:
    db = sqlite3.connect(path)
    try:
        db.execute("CREATE TABLE calls(caller TEXT, callee TEXT, callsite TEXT, kind TEXT, raw_json TEXT NOT NULL)")
        for rec in calls:
            db.execute(
                "INSERT INTO calls VALUES(?,?,?,?,?)",
                (rec.get("from_function"), rec.get("to"), rec.get("instruction"), "direct", json.dumps(rec)),
            )
        db.commit()
    finally:
        db.close()


def test_analyzer_finds_all_three_carrier_classes(tmp_path):
    module = load_module()
    db = tmp_path / "index.sqlite"
    make_db(
        db,
        [{"from_function": "0x00401000", "instruction": "0x00401010", "to": "0x00755950", "to_name": "FUN_00755950"}],
    )
    vtables = tmp_path / "vtables.json"
    vtables.write_text(
        json.dumps({"vtables": [{"address": "0x00aa0000", "slots": [{"slot": 3, "target": "0x00755950", "name": "FUN_00755950"}]}]}),
        encoding="utf-8",
    )
    static_tables = tmp_path / "static.jsonl"
    static_tables.write_text(
        json.dumps({"address": "0x00bb0000", "block": ".rdata", "data_type": "pointer[1]", "length": 4, "raw_hex": "50597500"}) + "\n",
        encoding="utf-8",
    )

    payload = module.analyze(db, vtables, static_tables)
    assert payload["direct_callgraph"]["caller_count"] == 1
    assert payload["heuristic_vtables"]["target_slot_hit_count"] == 1
    assert payload["static_tables"]["literal_pointer_hit_count"] == 1
    assert payload["adjudication"]["known_exported_static_carriers_empty"] is False
    assert payload["adjudication"]["runtime_or_code_built_indirect_dispatch_ruled_out"] is False


def test_analyzer_empty_static_surfaces_stay_fail_closed(tmp_path):
    module = load_module()
    db = tmp_path / "index.sqlite"
    make_db(db, [])
    vtables = tmp_path / "vtables.json"
    vtables.write_text(json.dumps({"vtables": []}), encoding="utf-8")
    static_tables = tmp_path / "static.jsonl"
    static_tables.write_text(json.dumps({"address": "0x00bb0000", "block": ".rdata", "data_type": "dword", "length": 4, "raw_hex": "00000000"}) + "\n", encoding="utf-8")

    payload = module.analyze(db, vtables, static_tables)
    adj = payload["adjudication"]
    assert adj["known_exported_static_carriers_empty"] is True
    assert adj["consumer_unreachable_proven"] is False
    assert adj["slot3_writer_provenance_proven"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7


def test_pinned_retail_evidence_remains_fail_closed():
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.P1D.Slot3DispatchCarrierBoundary/1"
    assert payload["target"] == {"address": "0x00755950", "name": "FUN_00755950"}
    assert payload["direct_callgraph"]["caller_count"] == 0
    assert payload["heuristic_vtables"]["table_count"] == 2533
    assert payload["heuristic_vtables"]["slot_count"] == 22416
    assert payload["heuristic_vtables"]["target_slot_hit_count"] == 0
    assert payload["static_tables"]["record_count"] == 55066
    assert payload["static_tables"]["exported_byte_count"] == 956464
    assert payload["static_tables"]["literal_pointer_hit_count"] == 0
    adj = payload["adjudication"]
    assert adj["known_exported_static_carriers_empty"] is True
    assert adj["runtime_or_code_built_indirect_dispatch_ruled_out"] is False
    assert adj["consumer_unreachable_proven"] is False
    assert adj["slot3_writer_provenance_proven"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
