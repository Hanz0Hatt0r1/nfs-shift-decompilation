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


def make_v1_db(path: Path, calls: list[dict]) -> None:
    db = sqlite3.connect(path)
    try:
        db.execute("CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
        db.execute("INSERT INTO metadata VALUES('format','SHIFT.GhidraSQLiteIndex/1')")
        db.execute("CREATE TABLE calls(caller TEXT,callee TEXT,callsite TEXT,kind TEXT,raw_json TEXT NOT NULL)")
        for rec in calls:
            db.execute(
                "INSERT INTO calls VALUES(?,?,?,?,?)",
                (rec.get("from_function", ""), rec.get("legacy_callee", ""), rec.get("instruction", ""), "direct", json.dumps(rec)),
            )
        db.commit()
    finally:
        db.close()


def make_machine_proof(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "format": "SHIFT.Fun00755950AbsoluteConsumedFieldMachineProof/1",
                "consumer": {
                    "caller": "FUN_00758b50",
                    "callee": "FUN_00755950",
                    "call_instruction": "0x00758d6b",
                    "wheel_runtime_this_expression": "HDVehicle+0x400+slot*0xa80",
                },
            }
        ),
        encoding="utf-8",
    )


def make_aux_indexes(tmp_path: Path):
    vtables = tmp_path / "vtables.json"
    vtables.write_text(json.dumps({"vtables": [{"address": "0x00aa0000", "slots": []}]}), encoding="utf-8")
    static_tables = tmp_path / "static.jsonl"
    static_tables.write_text(
        json.dumps({"address": "0x00bb0000", "block": ".rdata", "data_type": "dword", "length": 4, "raw_hex": "00000000"}) + "\n",
        encoding="utf-8",
    )
    return vtables, static_tables


def test_v1_raw_json_recovers_known_machine_call(tmp_path):
    module = load_module()
    db = tmp_path / "index.sqlite"
    make_v1_db(
        db,
        [{
            "from_function": "0x00758b50",
            "from_name": "FUN_00758b50",
            "instruction": "0x00758d6b",
            "to": "0x00755950",
            "to_name": "FUN_00755950",
            "indirect": False,
        }],
    )
    machine = tmp_path / "machine.json"
    make_machine_proof(machine)
    vtables, static_tables = make_aux_indexes(tmp_path)

    payload = module.analyze(db, vtables, static_tables, machine)
    cg = payload["sqlite_callgraph"]
    assert cg["index_format"] == "SHIFT.GhidraSQLiteIndex/1"
    assert cg["legacy_callee_column_match_count"] == 0
    assert cg["normalized_match_count"] == 1
    assert cg["callers"][0]["instruction"] == "0x00758d6b"
    assert cg["known_machine_call_covered_after_raw_json_normalization"] is True
    assert cg["legacy_v1_callee_column_population_gap"] is True
    adj = payload["adjudication"]
    assert adj["direct_call_carrier_proven_by_machine"] is True
    assert adj["normalized_sqlite_callgraph_recovers_machine_call"] is True
    assert adj["legacy_v1_column_population_gap_proven"] is True
    assert adj["slot3_writer_provenance_proven"] is False


def test_pinned_retail_evidence_recovers_exact_caller_and_stays_fail_closed():
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.P1D.Slot3DispatchCarrierBoundary/1"
    assert payload["retail_machine_direct_call"] == {
        "caller": "FUN_00758b50",
        "callee": "FUN_00755950",
        "call_instruction": "0x00758d6b",
        "wheel_runtime_this_expression": "HDVehicle+0x400+slot*0xa80",
    }
    cg = payload["sqlite_callgraph"]
    assert cg["index_format"] == "SHIFT.GhidraSQLiteIndex/1"
    assert cg["legacy_callee_column_match_count"] == 0
    assert cg["normalized_match_count"] == 1
    assert cg["callers"] == [{
        "from_function": "0x00758b50",
        "from_name": "FUN_00758b50",
        "instruction": "0x00758d6b",
        "to": "0x00755950",
        "to_name": "FUN_00755950",
        "indirect": False,
    }]
    assert cg["known_machine_call_covered_after_raw_json_normalization"] is True
    assert cg["legacy_v1_callee_column_population_gap"] is True
    assert payload["heuristic_vtables"]["target_slot_hit_count"] == 0
    assert payload["static_tables"]["literal_pointer_hit_count"] == 0
    adj = payload["adjudication"]
    assert adj["normalized_sqlite_callgraph_recovers_machine_call"] is True
    assert adj["vtable_or_static_pointer_misses_prove_carrier_absence"] is False
    assert adj["slot3_writer_provenance_proven"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
