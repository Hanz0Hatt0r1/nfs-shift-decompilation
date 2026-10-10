import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/ghidra/build_p1b_hdvehicle_4330_static_pointer_materialization_coverage.py"
EVIDENCE = ROOT / "evidence/p1b_hdvehicle_4330_static_pointer_materialization_coverage.json"
VTABLE = ROOT / "evidence/p1b_hdvehicle_4330_exact_carrier_vtable_surface.json"
STATIC = ROOT / "evidence/p1b_hdvehicle_4330_exact_carrier_static_table_surface.json"
LITERAL = ROOT / "evidence/p1b_hdvehicle_4330_whole_image_literal_pointer_surface.json"
SOURCE = ROOT / "evidence/p1b_hdvehicle_4330_source_symbol_address_taking.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1b_static_pointer_materialization_coverage", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_builder_reproduces_committed_coverage():
    module = load_module()
    assert module.build(VTABLE, STATIC, LITERAL, SOURCE) == load_evidence()
    assert module.FORMAT == "SHIFT.P1B.HDVehicle4330StaticFunctionPointerMaterializationCoverage/1"


def test_four_static_source_visible_classes_are_zero_hit():
    surface = load_evidence()["surface"]
    assert surface["exact_carrier_count"] == 15
    assert surface["closed_materialization_class_count"] == 4
    assert surface["exact_carrier_materialization_hit_count"] == 0
    assert all(row["exact_carrier_hit_count"] == 0 for row in surface["classes"])
    assert surface["classes"][0]["bounded_unit_count"] == 22416
    assert surface["classes"][1]["bounded_unit_count"] == 55066
    assert surface["classes"][1]["scanned_raw_byte_count"] == 684472
    assert surface["classes"][2]["bounded_unit_count"] == 8801792
    assert surface["classes"][3]["bounded_unit_count"] == 40


def test_runtime_pointer_gates_remain_fail_closed():
    gates = load_evidence()["adjudication"]
    assert gates["static_and_source_visible_exact_carrier_pointer_materialization_coverage_composed"] is True
    assert gates["bounded_static_pointer_materialization_exact_carrier_hit_found"] is False
    assert gates["generic_function_pointer_stores_copies_ruled_out"] is False
    assert gates["runtime_generated_or_copied_function_pointers_ruled_out"] is False
    assert gates["computed_or_encoded_code_pointers_ruled_out"] is False
    assert gates["runtime_callback_registration_ruled_out"] is False
    assert gates["indirect_entry_into_carriers_ruled_out"] is False
    assert gates["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert gates["last_literal_0x004b86cf_rejected"] is False
    assert gates["p1_3_control_producer_complete"] is False
    assert gates["external_provider_count"] == 7
