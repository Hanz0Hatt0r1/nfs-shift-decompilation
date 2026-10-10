import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1b_hdvehicle_4330_exact_carrier_vtables.py"
EVIDENCE = ROOT / "evidence" / "p1b_hdvehicle_4330_exact_carrier_vtable_surface.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1b_4330_vtables", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_vtable_scanner_surfaces_exact_4330_carrier():
    module = load_module()
    payload = {
        "format": module.VTABLE_FORMAT,
        "vtables": [
            {
                "address": "0x00aa0000",
                "slots": [
                    {"slot": 0, "target": "0x00769520", "name": "FUN_00769520"},
                    {"slot": 1, "target": "0x00123456", "name": "other"},
                ],
            }
        ],
    }
    result = module.scan_vtables(payload)
    assert result["table_count"] == 1
    assert result["slot_count"] == 2
    assert result["hits"] == [
        {
            "carrier": "FUN_00769520",
            "target": "0x00769520",
            "vtable": "0x00aa0000",
            "slot": 0,
        }
    ]


def test_checked_evidence_pins_empty_vtable_surface_and_fail_closed_gates():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1B.HDVehicle4330ExactCarrierVtableSurface/1"
    assert data["carrier_set"]["count"] == 15
    assert data["vtable_surface"]["candidate_table_count"] == 2533
    assert data["vtable_surface"]["slot_count"] == 22416
    assert data["vtable_surface"]["exact_carrier_target_hit_count"] == 0
    assert data["vtable_surface"]["hits"] == []

    gates = data["adjudication"]
    assert gates["exact_4330_carrier_vtable_target_subset_complete"] is True
    assert gates["static_vtable_exact_carrier_target_found"] is False
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
    assert data["authority"]["vtables_sha256"] == module.VTABLE_SHA256
    evidence_rows = {(row["name"], int(row["address"], 0)) for row in data["carrier_set"]["rows"]}
    assert evidence_rows == set(module.CARRIERS.items())
