import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "tools/ghidra/analyze_p1b_hdvehicle_4330_getprocaddress_static_resolution.py"
EVIDENCE = ROOT / "evidence/p1b_hdvehicle_4330_getprocaddress_static_resolution.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1b_gpa", ANALYZER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_static_resolution_surface_counts_and_names():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1B.HDVehicle4330GetProcAddressStaticResolutionSurface/1"
    assert data["ready"] is True
    surface = data["getprocaddress_surface"]
    assert surface["iat_va"] == "0x00aa62fc"
    assert surface["whole_image_iat_dword_occurrence_count"] == 19
    assert surface["classified_instruction_reference_count"] == 19
    assert surface["direct_iat_call_reference_count"] == 12
    assert surface["iat_load_reference_count"] == 7
    assert surface["register_loaded_callsite_count"] == 86
    assert surface["physical_getprocaddress_callsite_count"] == 98
    assert surface["generic_wrapper"] == "0x0093dd2b"
    assert surface["generic_wrapper_getprocaddress_callsite"] == "0x0093dd43"
    assert surface["generic_wrapper_direct_caller_count"] == 12
    assert surface["known_name_instance_count"] == 109
    assert surface["known_unique_name_count"] == 105
    assert surface["known_patch_api_name_hits"] == []

    names = set(surface["known_unique_names"])
    assert "IsWow64Process" in names
    assert "_FMODGetCodecDescription@0" in names
    assert "GetActiveWindow" in names
    assert "alGetProcAddress" in names
    assert "alcGetProcAddress" in names
    assert "EnumDisplayDevicesA" in names


def test_scoped_gates_advance_while_global_gates_remain_closed():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    adj = data["adjudication"]
    assert adj["static_getprocaddress_iat_reference_surface_complete"] is True
    assert adj["register_loaded_getprocaddress_call_surface_complete"] is True
    assert adj["generic_wrapper_direct_caller_name_surface_complete"] is True
    assert adj["known_getprocaddress_patch_api_resolution_found"] is False
    assert adj["dynamic_getprocaddress_resolution_ruled_out"] is False
    assert adj["runtime_patching_or_generated_code_ruled_out"] is False
    assert adj["runtime_computed_carrier_pointers_ruled_out"] is False
    assert adj["runtime_copied_or_encoded_carrier_pointers_ruled_out"] is False
    assert adj["indirect_entry_into_carriers_ruled_out"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7


def test_helper_parsers_are_bounded():
    module = load_module()
    assert module.parse_immediate("eax,0x1234") == 0x1234
    assert module.parse_immediate("eax,ebx") is None
    assert module.destination_register({"mnemonic": "mov", "operands": "esi,eax"}) == "esi"
    assert module.destination_register({"mnemonic": "cmp", "operands": "esi,eax"}) is None
