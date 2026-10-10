import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "tools/ghidra/analyze_p1b_hdvehicle_4330_direct_win32_runtime_patching.py"
EVIDENCE = ROOT / "evidence/p1b_hdvehicle_4330_direct_win32_runtime_patching.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1b_runtime_patch", ANALYZER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_committed_surface_and_fail_closed_global_gates():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1B.HDVehicle4330DirectWin32RuntimePatchingSurface/1"
    assert data["ready"] is True

    imports = data["import_surface"]
    assert imports["import_descriptor_count"] == 26
    assert imports["imported_function_count"] == 411
    assert imports["virtualalloc_imported"] is True
    assert imports["virtualalloc_iat_va"] == "0x00aa6288"
    assert imports["getprocaddress_imported"] is True
    assert not any(imports["patch_api_import_presence"].values())
    assert not any(imports["patch_api_ascii_string_hit_counts"].values())

    surface = data["virtualalloc_surface"]
    assert surface["iat_address_whole_image_occurrence_count"] == 8
    assert surface["direct_iat_callsite_count"] == 8
    assert surface["unknown_protection_callsite_count"] == 0
    assert surface["executable_protection_callsite_count"] == 0
    assert {row["fl_protect"] for row in surface["callsites"]} == {"0x00000004"}
    assert all(row["executable_protection"] is False for row in surface["callsites"])

    adj = data["adjudication"]
    assert adj["direct_standard_win32_runtime_patching_subset_complete"] is True
    assert adj["direct_imported_code_page_protection_api_found"] is False
    assert adj["direct_virtualalloc_executable_allocation_found"] is False
    assert adj["virtualalloc_static_reference_surface_complete"] is True
    assert adj["runtime_patching_or_generated_code_ruled_out"] is False
    assert adj["runtime_computed_carrier_pointers_ruled_out"] is False
    assert adj["runtime_copied_or_encoded_carrier_pointers_ruled_out"] is False
    assert adj["indirect_entry_into_carriers_ruled_out"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7


def test_virtualalloc_argument_classifier_and_executable_values():
    module = load_module()
    instructions = [
        {"address": 0x1000, "mnemonic": "push", "operands": "0x40"},
        {"address": 0x1002, "mnemonic": "push", "operands": "0x1000"},
        {"address": 0x1007, "mnemonic": "push", "operands": "eax"},
        {"address": 0x1008, "mnemonic": "push", "operands": "0x0"},
        {"address": 0x100A, "mnemonic": "call", "operands": "dword ptr ds:0xaa6288"},
    ]
    rows = module.virtualalloc_call_rows(instructions, 0x00AA6288)
    assert len(rows) == 1
    assert rows[0]["fl_protect_value"] == 0x40
    assert 0x40 in module.EXECUTABLE_PAGE_PROTECTIONS


def test_classifier_stops_at_control_transfer_boundary():
    module = load_module()
    instructions = [
        {"address": 0x2000, "mnemonic": "push", "operands": "0x40"},
        {"address": 0x2002, "mnemonic": "jmp", "operands": "0x2010"},
        {"address": 0x2010, "mnemonic": "push", "operands": "0x1000"},
        {"address": 0x2015, "mnemonic": "push", "operands": "eax"},
        {"address": 0x2016, "mnemonic": "push", "operands": "0x0"},
        {"address": 0x2018, "mnemonic": "call", "operands": "dword ptr ds:0xaa6288"},
    ]
    rows = module.virtualalloc_call_rows(instructions, 0x00AA6288)
    assert rows[0]["fl_protect_value"] is None
