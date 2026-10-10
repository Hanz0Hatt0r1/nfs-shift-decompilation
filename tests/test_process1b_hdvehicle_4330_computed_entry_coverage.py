import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/ghidra/build_p1b_hdvehicle_4330_computed_entry_coverage.py"
EVIDENCE = ROOT / "evidence/p1b_hdvehicle_4330_computed_entry_coverage.json"
CANONICAL = ROOT / "evidence/p1b_hdvehicle_4330_canonical_eip_capture_surface.json"
X87 = ROOT / "evidence/p1b_hdvehicle_4330_x87_eip_capture_surface.json"
LOADER = ROOT / "evidence/p1b_hdvehicle_4330_pe_loader_entry_surface.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1b_computed_entry_coverage", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_builder_reproduces_committed_coverage():
    module = load_module()
    assert module.build(CANONICAL, X87, LOADER) == load_evidence()
    assert module.FORMAT == "SHIFT.P1B.HDVehicle4330ComputedEntryCoverage/1"


def test_three_bounded_computed_loader_classes_are_zero_hit():
    surface = load_evidence()["surface"]
    assert surface["closed_computed_or_loader_entry_class_count"] == 3
    assert surface["exact_carrier_entry_hit_count"] == 0
    assert all(row["exact_carrier_hit_count"] == 0 for row in surface["classes"])
    assert surface["classes"][0]["candidate_count"] == 1
    assert surface["classes"][0]["derived_value"] == "0x00d31000"
    assert surface["classes"][1]["decoded_site_count"] == 4
    assert surface["classes"][1]["real_env_save_instruction_count"] == 2
    assert surface["classes"][1]["saved_eip_extraction_found"] is False
    assert surface["classes"][2]["export_function_count"] == 509
    assert surface["classes"][2]["tls_callback_count"] == 0
    assert surface["classes"][2]["load_config_present"] is False


def test_noncanonical_runtime_pointer_gates_remain_fail_closed():
    gates = load_evidence()["adjudication"]
    assert gates["bounded_computed_and_loader_entry_coverage_composed"] is True
    assert gates["bounded_computed_or_loader_exact_carrier_hit_found"] is False
    assert gates["canonical_call_pop_eip_capture_complete"] is True
    assert gates["x87_saved_eip_capture_complete"] is True
    assert gates["pe_loader_published_entry_surface_complete"] is True
    assert gates["noncanonical_nonx87_eip_capture_surface_complete"] is False
    assert gates["runtime_computed_carrier_pointers_ruled_out"] is False
    assert gates["runtime_copied_or_encoded_carrier_pointers_ruled_out"] is False
    assert gates["generic_function_pointer_stores_copies_ruled_out"] is False
    assert gates["runtime_callback_registration_ruled_out"] is False
    assert gates["indirect_entry_into_carriers_ruled_out"] is False
    assert gates["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert gates["last_literal_0x004b86cf_rejected"] is False
    assert gates["p1_3_control_producer_complete"] is False
    assert gates["external_provider_count"] == 7
