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


def make_machine_proof(path: Path, call_instruction: str = "0x00758d6b") -> None:
    path.write_text(
        json.dumps(
            {
                "format": "SHIFT.Fun00755950AbsoluteConsumedFieldMachineProof/1",
                "consumer": {
                    "caller": "FUN_00758b50",
                    "callee": "FUN_00755950",
                    "call_instruction": call_instruction,
                    "wheel_runtime_this_expression": "HDVehicle+0x400+slot*0xa80",
                },
            }
        ),
        encoding="utf-8",
    )


def make_aux_indexes(tmp_path: Path, *, include_target: bool = False):
    vtables = tmp_path / "vtables.json"
    slots = [{"slot": 3, "target": "0x00755950", "name": "FUN_00755950"}] if include_target else []
    vtables.write_text(json.dumps({"vtables": [{"address": "0x00aa0000", "slots": slots}]}), encoding="utf-8")
    static_tables = tmp_path / "static.jsonl"
    raw_hex = "50597500" if include_target else "00000000"
    static_tables.write_text(
        json.dumps({"address": "0x00bb0000", "block": ".rdata", "data_type": "pointer[1]", "length": 4, "raw_hex": raw_hex}) + "\n",
        encoding="utf-8",
    )
    return vtables, static_tables


def test_machine_proof_overrides_empty_sqlite_caller_surface(tmp_path):
    module = load_module()
    db = tmp_path / "index.sqlite"
    make_db(db, [])
    machine = tmp_path / "machine.json"
    make_machine_proof(machine)
    vtables, static_tables = make_aux_indexes(tmp_path)

    payload = module.analyze(db, vtables, static_tables, machine)
    assert payload["retail_machine_direct_call"]["caller"] == "FUN_00758b50"
    assert payload["sqlite_direct_callgraph"]["caller_count"] == 0
    assert payload["sqlite_direct_callgraph"]["known_machine_call_covered"] is False
    assert payload["sqlite_direct_callgraph"]["coverage_gap_against_machine_proof"] is True
    adj = payload["adjudication"]
    assert adj["direct_call_carrier_proven_by_machine"] is True
    assert adj["sqlite_direct_callgraph_complete_for_target"] is False
    assert adj["index_misses_can_prove_carrier_absence"] is False


def test_index_can_cover_machine_call_without_promoting_writer(tmp_path):
    module = load_module()
    db = tmp_path / "index.sqlite"
    make_db(db, [{"from_function": "0x00758b50", "instruction": "0x00758d6b", "to": "0x00755950", "to_name": "FUN_00755950"}])
    machine = tmp_path / "machine.json"
    make_machine_proof(machine)
    vtables, static_tables = make_aux_indexes(tmp_path, include_target=True)

    payload = module.analyze(db, vtables, static_tables, machine)
    assert payload["sqlite_direct_callgraph"]["known_machine_call_covered"] is True
    assert payload["heuristic_vtables"]["target_slot_hit_count"] == 1
    assert payload["static_tables"]["literal_pointer_hit_count"] == 1
    adj = payload["adjudication"]
    assert adj["sqlite_direct_callgraph_complete_for_target"] is True
    assert adj["slot3_writer_provenance_proven"] is False
    assert adj["p1_3_control_producer_complete"] is False


def test_pinned_retail_evidence_records_index_gap_and_stays_fail_closed():
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.P1D.Slot3DispatchCarrierBoundary/1"
    assert payload["retail_machine_direct_call"] == {
        "caller": "FUN_00758b50",
        "callee": "FUN_00755950",
        "call_instruction": "0x00758d6b",
        "wheel_runtime_this_expression": "HDVehicle+0x400+slot*0xa80",
    }
    assert payload["sqlite_direct_callgraph"]["caller_count"] == 0
    assert payload["sqlite_direct_callgraph"]["coverage_gap_against_machine_proof"] is True
    assert payload["heuristic_vtables"]["table_count"] == 2533
    assert payload["heuristic_vtables"]["slot_count"] == 22416
    assert payload["heuristic_vtables"]["target_slot_hit_count"] == 0
    assert payload["static_tables"]["record_count"] == 55066
    assert payload["static_tables"]["exported_byte_count"] == 956464
    assert payload["static_tables"]["literal_pointer_hit_count"] == 0
    adj = payload["adjudication"]
    assert adj["direct_call_carrier_proven_by_machine"] is True
    assert adj["sqlite_direct_callgraph_complete_for_target"] is False
    assert adj["index_misses_can_prove_carrier_absence"] is False
    assert adj["slot3_writer_provenance_proven"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
