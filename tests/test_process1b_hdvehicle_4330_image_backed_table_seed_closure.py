import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools/ghidra/build_p1b_hdvehicle_4330_image_backed_table_seed_closure.py"
WHOLE = ROOT / "evidence/p1b_hdvehicle_4330_whole_image_literal_pointer_surface.json"
STATIC = ROOT / "evidence/p1b_hdvehicle_4330_exact_carrier_static_table_surface.json"
EVIDENCE = ROOT / "evidence/p1b_hdvehicle_4330_image_backed_table_seed_closure.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1b_image_table_seed", BUILDER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_builder_reproduces_committed_evidence():
    module = load_module()
    assert module.build(WHOLE, STATIC) == json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_direct_image_backed_va_and_rva_table_seed_subset_closes_only_bounded_class():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1B.HDVehicle4330ImageBackedTableSeedClosure/1"
    surface = data["surface"]
    assert surface["p1b_exact_carrier_count"] == 15
    assert surface["retail_file_size"] == 8_801_792
    assert surface["whole_image_raw_bytes_scanned"] == 8_801_792
    assert surface["whole_image_exact_carrier_absolute_va_hit_count"] == 0
    assert surface["whole_image_exact_carrier_rva_hit_count"] == 0
    assert surface["static_table_record_count"] == 55_066
    assert surface["static_table_raw_bytes_scanned"] == 684_472
    assert surface["static_table_exact_carrier_absolute_va_hit_count"] == 0
    assert surface["direct_image_backed_exact_va_table_seed_count"] == 0
    assert surface["direct_image_backed_exact_rva_table_seed_count"] == 0

    adj = data["adjudication"]
    assert adj["image_backed_direct_table_exact_carrier_seed_subset_complete"] is True
    assert adj["image_backed_exact_carrier_va_table_seed_found"] is False
    assert adj["image_backed_exact_carrier_rva_table_seed_found"] is False
    assert adj["direct_imagebase_plus_image_table_exact_rva_seed_path_ruled_out"] is True
    assert adj["memory_table_derived_carrier_pointers_ruled_out"] is False
    assert adj["computed_or_encoded_code_pointers_ruled_out"] is False
    assert adj["runtime_copied_or_encoded_carrier_pointers_ruled_out"] is False
    assert adj["generic_function_pointer_stores_copies_ruled_out"] is False
    assert adj["indirect_entry_into_carriers_ruled_out"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
