import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/ghidra/analyze_p1b_hdvehicle_4330_unhandled_exception_filter_surface.py"
EVIDENCE = ROOT / "evidence/p1b_hdvehicle_4330_unhandled_exception_filter_surface.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1b_unhandled_exception_filter", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_surface_is_three_null_registrations():
    data = load_evidence()
    assert data["format"] == "SHIFT.P1B.HDVehicle4330UnhandledExceptionFilterSurface/1"
    surface = data["surface"]
    assert surface["direct_callsite_count"] == 3
    assert surface["null_filter_registration_count"] == 3
    assert surface["nonnull_filter_registration_count"] == 0
    assert surface["exact_4330_carrier_filter_count"] == 0
    assert [row["callsite"] for row in surface["callsites"]] == [
        "0x0090a5e6", "0x0090a7ac", "0x00916f56"
    ]
    assert all(row["registered_filter"] == "NULL" for row in surface["callsites"])


def test_expected_machine_call_contract_is_pinned():
    module = load_module()
    assert module.EXPECTED_CALLS == {
        ("0x0090a532", "__invoke_watson", "0x0090a5e6"),
        ("0x0090a6d1", "_abort", "0x0090a7ac"),
        ("0x00916e88", "___report_gsfailure", "0x00916f56"),
    }
    assert module.NULL_SOURCE_CALL == "SetUnhandledExceptionFilter((LPTOP_LEVEL_EXCEPTION_FILTER)0x0);"


def test_global_runtime_entry_gates_remain_fail_closed():
    gates = load_evidence()["adjudication"]
    assert gates["set_unhandled_exception_filter_surface_complete"] is True
    assert gates["exact_4330_carrier_reachable_via_unhandled_exception_filter"] is False
    assert gates["runtime_callback_registration_ruled_out"] is False
    assert gates["generic_function_pointer_stores_copies_ruled_out"] is False
    assert gates["computed_or_encoded_code_pointers_ruled_out"] is False
    assert gates["remaining_callback_api_families_ruled_out"] is False
    assert gates["indirect_entry_into_carriers_ruled_out"] is False
    assert gates["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert gates["last_literal_0x004b86cf_rejected"] is False
    assert gates["p1_3_control_producer_complete"] is False
    assert gates["external_provider_count"] == 7
