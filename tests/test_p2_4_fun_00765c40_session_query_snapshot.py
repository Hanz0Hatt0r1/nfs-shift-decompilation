import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/p2_4_fun_00765c40_session_query_snapshot.json"
HEADER = ROOT / "native_runtime/include/shift_fun_00765c40_external_pass_result.hpp"


def test_selected_session_query_snapshot_prefers_native_input() -> None:
    payload = json.loads(EVIDENCE.read_text())
    assert payload["format"] == "SHIFT.Fun00765c40SessionQuerySnapshot/1"
    assert payload["ready"] is True
    selected = payload["selected_path"]
    assert selected["snapshot_source"] == "Fun00765c40ExternalPassInput.selected_bmw_query_input"
    assert selected["provider_query_input_authoritative_after_validation"] is False
    assert selected["validation_required_before_snapshot"] is True
    assert payload["generic_path"]["provider_query_input_retained_for_compatibility"] is True
    assert payload["runtime_integration"]["selector_ready"] is True
    assert payload["runtime_integration"]["NativeVehicleProviderSession_switched_to_selector"] is False
    assert payload["scope"]["external_provider_count_after"] == 7


def test_header_selector_validates_then_uses_native_selected_query() -> None:
    text = HEADER.read_text()
    selector = text.index("materialize_fun_00765c40_session_query_snapshot")
    validation = text.index("validate_fun_00765c40_external_pass_result(input, result);", selector)
    native_query = text.index("input.selected_bmw_query_input();", validation)
    native_return = text.index("return *native_selected_query;", native_query)
    generic_return = text.index("return result.query_input;", native_return)
    assert selector < validation < native_query < native_return < generic_return
