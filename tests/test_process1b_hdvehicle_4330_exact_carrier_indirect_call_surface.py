import hashlib
import importlib.util
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1b_hdvehicle_4330_exact_carrier_indirect_calls.py"
EVIDENCE = ROOT / "evidence" / "p1b_hdvehicle_4330_exact_carrier_indirect_call_surface.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1b_4330_indirect", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_checked_evidence_pins_empty_carrier_callind_surface_and_fail_closed_gates():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1B.HDVehicle4330ExactCarrierIndirectCallSurface/1"
    assert data["carrier_set"]["count"] == 15
    surface = data["indirect_surface"]
    assert surface["whole_index_indirect_call_edge_count"] == 19500
    assert surface["carrier_indirect_call_edge_count"] == 0
    assert surface["carrier_indirect_call_edges"] == []

    gates = data["adjudication"]
    assert gates["sqlite_indirect_call_edge_class_present"] is True
    assert gates["known_exact_4330_carrier_indirect_call_edge_surface_complete"] is True
    assert gates["known_exact_4330_carrier_indirect_call_edge_surface_empty"] is True
    assert gates["indirect_entry_into_carriers_ruled_out"] is False
    assert gates["callbacks_registered_outside_carriers_ruled_out"] is False
    assert gates["runtime_generated_or_copied_function_pointers_ruled_out"] is False
    assert gates["global_runtime_derived_4330_alias_surface_complete"] is False
    assert gates["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert gates["last_literal_0x004b86cf_rejected"] is False
    assert gates["p1_3_control_producer_complete"] is False
    assert gates["external_provider_count"] == 7


def test_pinned_hash_and_fingerprints_match_analyzer_constants():
    module = load_module()
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["authority"]["ghidra_sqlite_sha256"] == module.SQLITE_SHA256
    rows = {
        row["address"]: (row["name"], row["size"], row["mnemonic_sha256"])
        for row in data["carrier_set"]["functions"]
    }
    expected = {
        address: (module.CARRIERS[address], size, digest)
        for address, (size, digest) in module.EXPECTED.items()
    }
    assert rows == expected


def test_analyzer_surfaces_indirect_edge_from_exact_carrier(tmp_path, monkeypatch):
    module = load_module()
    db_path = tmp_path / "demo.sqlite"
    db = sqlite3.connect(db_path)
    try:
        db.execute("CREATE TABLE metadata (key TEXT, value TEXT)")
        db.execute("CREATE TABLE functions (address TEXT, name TEXT, raw_json TEXT)")
        db.execute("CREATE TABLE calls (raw_json TEXT)")
        db.execute("INSERT INTO metadata VALUES (?, ?)", ("format", "SHIFT.GhidraSQLiteIndex/1"))
        address = "0x00769520"
        name = "FUN_00769520"
        digest = "demo-digest"
        db.execute(
            "INSERT INTO functions VALUES (?, ?, ?)",
            (address, name, json.dumps({"size": 7, "mnemonic_sha256": digest})),
        )
        db.execute(
            "INSERT INTO calls VALUES (?)",
            (json.dumps({"indirect": True, "from_function": address, "from_name": name, "instruction": "0x00769530"}),),
        )
        db.commit()
    finally:
        db.close()

    file_hash = hashlib.sha256(db_path.read_bytes()).hexdigest()
    monkeypatch.setattr(module, "SQLITE_SHA256", file_hash)
    monkeypatch.setattr(module, "CARRIERS", {address: name})
    monkeypatch.setattr(module, "EXPECTED", {address: (7, digest)})

    result = module.analyze(db_path)
    surface = result["indirect_surface"]
    assert surface["whole_index_indirect_call_edge_count"] == 1
    assert surface["carrier_indirect_call_edge_count"] == 1
    assert surface["carrier_indirect_call_edges"] == [
        {"from_function": address, "from_name": name, "instruction": "0x00769530"}
    ]
    assert result["adjudication"]["known_exact_4330_carrier_indirect_call_edge_surface_empty"] is False
