import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1b_hdvehicle_4330_exact_carrier_static_tables.py"
EVIDENCE = ROOT / "evidence" / "p1b_hdvehicle_4330_exact_carrier_static_table_surface.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1b_4330_static", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_static_scanner_surfaces_little_endian_exact_carrier_pointer():
    module = load_module()
    rows = [
        json.dumps({
            "address": "0x00bb0000",
            "data_type": "demo",
            "length": 8,
            "raw_hex": "0000000020957600",
        })
    ]
    result = module.scan_static_records(rows)
    assert result["record_count"] == 1
    assert result["declared_length_total"] == 8
    assert result["raw_hex_bytes_total"] == 8
    assert result["hits"] == [
        {
            "carrier": "FUN_00769520",
            "target": "0x00769520",
            "record_address": "0x00bb0000",
            "data_type": "demo",
            "byte_offset": 4,
        }
    ]


def test_checked_evidence_pins_empty_static_table_surface_and_fail_closed_gates():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1B.HDVehicle4330ExactCarrierStaticTableSurface/1"
    assert data["carrier_set"]["count"] == 15
    surface = data["static_table_surface"]
    assert surface["record_count"] == 55066
    assert surface["declared_length_total"] == 956464
    assert surface["raw_hex_bytes_total"] == 684472
    assert surface["exact_carrier_pointer_hit_count"] == 0
    assert surface["hits"] == []

    gates = data["adjudication"]
    assert gates["exact_4330_carrier_static_table_literal_pointer_subset_complete"] is True
    assert gates["static_table_exact_carrier_pointer_found"] is False
    assert gates["runtime_generated_or_copied_function_pointers_ruled_out"] is False
    assert gates["callee_created_4330_aliases_ruled_out"] is False
    assert gates["global_runtime_derived_4330_alias_surface_complete"] is False
    assert gates["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert gates["last_literal_0x004b86cf_rejected"] is False
    assert gates["p1_3_control_producer_complete"] is False
    assert gates["external_provider_count"] == 7


def test_pinned_hash_and_carrier_membership_match_analyzer():
    module = load_module()
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["authority"]["static_tables_sha256"] == module.STATIC_SHA256
    evidence_rows = {(row["name"], int(row["address"], 0)) for row in data["carrier_set"]["rows"]}
    assert evidence_rows == set(module.CARRIERS.items())
