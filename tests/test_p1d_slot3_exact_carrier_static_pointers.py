import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1d_slot3_exact_carrier_static_pointers.py"
EVIDENCE = ROOT / "evidence" / "p1d_slot3_exact_carrier_static_pointer_surface.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_static_carriers", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_vtable_scanner_surfaces_new_exact_carrier_target():
    module = load_module()
    payload = {
        "format": module.VTABLE_FORMAT,
        "vtables": [
            {
                "address": "0x00aa0000",
                "slots": [
                    {"slot": 0, "target": "0x00765c40", "name": "FUN_00765c40"},
                    {"slot": 1, "target": "0x00123456", "name": "other"},
                ],
            }
        ],
    }
    result = module.scan_vtables(payload)
    assert result["table_count"] == 1
    assert result["slot_count"] == 2
    assert result["hits"] == [
        {"carrier": "FUN_00765c40", "target": "0x00765c40", "vtable": "0x00aa0000", "slot": 0}
    ]


def test_static_scanner_surfaces_new_little_endian_carrier_pointer():
    module = load_module()
    rows = [
        json.dumps({
            "address": "0x00bb0000",
            "data_type": "demo",
            "length": 8,
            "raw_hex": "00000000405c7600",
        })
    ]
    result = module.scan_static_records(rows)
    assert result["record_count"] == 1
    assert result["declared_length_total"] == 8
    assert result["raw_hex_bytes_total"] == 8
    assert result["hits"] == [
        {
            "carrier": "FUN_00765c40",
            "target": "0x00765c40",
            "record_address": "0x00bb0000",
            "data_type": "demo",
            "byte_offset": 4,
        }
    ]


def test_checked_evidence_pins_empty_static_surface_and_fail_closed_gates():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1D.Slot3ExactCarrierStaticPointerSurface/1"
    assert data["carrier_set"]["count"] == 16
    assert data["carrier_set"]["rows"][-1] == {"name": "FUN_00765c40", "address": "0x00765c40"}
    assert data["vtable_surface"]["candidate_table_count"] == 2533
    assert data["vtable_surface"]["slot_count"] == 22416
    assert data["vtable_surface"]["exact_carrier_target_hit_count"] == 0
    assert data["static_table_surface"]["record_count"] == 55066
    assert data["static_table_surface"]["declared_length_total"] == 956464
    assert data["static_table_surface"]["raw_hex_bytes_total"] == 684472
    assert data["static_table_surface"]["exact_carrier_pointer_hit_count"] == 0
    gates = data["adjudication"]
    assert gates["exact_carrier_vtable_slot_target_subset_complete"] is True
    assert gates["exact_carrier_static_table_literal_pointer_subset_complete"] is True
    assert gates["runtime_generated_pointer_stores_ruled_out"] is False
    assert gates["unresolved_indirect_targets_ruled_out"] is False
    assert gates["stored_or_escaped_aliases_ruled_out"] is False
    assert gates["slot3_writer_provenance_proven"] is False
    assert gates["p1_3d_complete"] is False
    assert gates["external_provider_count"] == 7


def test_pinned_hashes_match_known_drive_exports():
    module = load_module()
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["authority"]["vtables_sha256"] == module.VTABLE_SHA256
    assert data["authority"]["static_tables_sha256"] == module.STATIC_SHA256
