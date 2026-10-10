import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/ghidra/analyze_p1b_hdvehicle_4330_createfiber_callback_surface.py"
EVIDENCE = ROOT / "evidence/p1b_hdvehicle_4330_createfiber_callback_surface.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1b_createfiber_callback", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_single_fixed_createfiber_start_routine():
    data = load_evidence()
    surface = data["surface"]
    assert data["format"] == "SHIFT.P1B.HDVehicle4330CreateFiberCallbackSurface/1"
    assert surface["physical_callsite_count"] == 1
    assert surface["callsite"] == "0x00a62a43"
    assert surface["caller"] == "0x00a62940"
    assert surface["start_routine"] == "0x00a62710"
    assert surface["start_routine_name"] == "lpStartAddress_00a62710"
    assert surface["exact_4330_carrier_start_routine_count"] == 0


def test_analyzer_contract_pins_canonical_carrier_set():
    module = load_module()
    assert module.EXPECTED_CALL == ("0x00a62940", "FUN_00a62940", "0x00a62a43")
    assert module.START_ROUTINE == 0x00A62710
    assert len(module.EXACT_CARRIERS) == 15
    assert module.START_ROUTINE not in module.EXACT_CARRIERS
    assert module.SOURCE_FRAGMENT == "CreateFiber(*(SIZE_T *)(*piVar4 + 8),lpStartAddress_00a62710,piVar4 + 2);"


def test_global_runtime_entry_gates_remain_fail_closed():
    gates = load_evidence()["adjudication"]
    assert gates["createfiber_callback_surface_complete"] is True
    assert gates["exact_4330_carrier_reachable_via_createfiber"] is False
    assert gates["runtime_callback_registration_ruled_out"] is False
    assert gates["generic_function_pointer_stores_copies_ruled_out"] is False
    assert gates["computed_or_encoded_code_pointers_ruled_out"] is False
    assert gates["remaining_callback_api_families_ruled_out"] is False
    assert gates["indirect_entry_into_carriers_ruled_out"] is False
    assert gates["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert gates["last_literal_0x004b86cf_rejected"] is False
    assert gates["p1_3_control_producer_complete"] is False
    assert gates["external_provider_count"] == 7
