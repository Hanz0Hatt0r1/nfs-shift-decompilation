import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools/ghidra/build_p1b_hdvehicle_4330_indirect_entry_coverage_v4.py"
BASE = ROOT / "evidence/p1b_hdvehicle_4330_indirect_entry_coverage_v3.json"
DIRECT_TABLE = ROOT / "evidence/p1b_hdvehicle_4330_image_backed_table_seed_closure.json"
TEXT_DELTA = ROOT / "evidence/p1b_hdvehicle_4330_text_base_delta_table_seed_surface.json"
EVIDENCE = ROOT / "evidence/p1b_hdvehicle_4330_indirect_entry_coverage_v4.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1b_ie_v4", BUILDER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_builder_reproduces_committed_evidence():
    module = load_module()
    assert module.build(BASE, DIRECT_TABLE, TEXT_DELTA) == json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_v4_adds_two_bounded_table_seed_classes_and_keeps_global_gates_closed():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/4"
    assert data["supersedes"] == "SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/3"
    assert data["surface"]["p1b_exact_carrier_count"] == 15
    assert data["surface"]["composed_coverage_class_count"] == 7
    assert data["surface"]["bounded_exact_carrier_hit_count"] == 0

    direct = data["surface"]["coverage"][-2]
    assert direct["class"] == "direct image-backed exact VA/RVA table seeds"
    assert direct["whole_image_raw_bytes_scanned"] == 8_801_792
    assert direct["static_table_record_count"] == 55_066
    assert direct["exact_va_seed_count"] == 0
    assert direct["exact_rva_seed_count"] == 0
    assert direct["exact_carrier_hit_count"] == 0

    delta = data["surface"]["coverage"][-1]
    assert delta["class"] == "image-backed .text-base delta table seeds"
    assert delta["raw_diagnostic_count"] == 1
    assert delta["non_executable_table_seed_count"] == 0
    assert delta["rel32_diagnostic_count"] == 1
    assert delta["unclassified_executable_diagnostic_count"] == 0
    assert delta["exact_carrier_hit_count"] == 0

    adj = data["adjudication"]
    assert adj["image_backed_direct_table_seed_subset_included"] is True
    assert adj["image_backed_text_base_delta_table_seed_subset_included"] is True
    assert adj["memory_table_derived_carrier_pointers_ruled_out"] is False
    assert adj["computed_or_encoded_code_pointers_ruled_out"] is False
    assert adj["runtime_computed_carrier_pointers_ruled_out"] is False
    assert adj["runtime_copied_or_encoded_carrier_pointers_ruled_out"] is False
    assert adj["runtime_generated_or_copied_function_pointers_ruled_out"] is False
    assert adj["generic_function_pointer_stores_copies_ruled_out"] is False
    assert adj["runtime_callback_registration_ruled_out"] is False
    assert adj["remaining_callback_api_families_ruled_out"] is False
    assert adj["indirect_entry_into_carriers_ruled_out"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
