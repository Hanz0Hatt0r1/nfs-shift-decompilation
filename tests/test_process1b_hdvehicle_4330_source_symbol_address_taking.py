import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/ghidra/analyze_p1b_hdvehicle_4330_source_symbol_address_taking.py"
EVIDENCE = ROOT / "evidence/p1b_hdvehicle_4330_source_symbol_address_taking.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1b_source_symbol_address_taking", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_exact_carrier_symbol_reference_surface_is_zero_value_use():
    data = load_evidence()
    surface = data["surface"]
    assert data["format"] == "SHIFT.P1B.HDVehicle4330SourceSymbolAddressTaking/1"
    assert surface["exact_carrier_symbol_count"] == 15
    assert surface["total_exact_carrier_symbol_occurrence_count"] == 40
    assert surface["call_or_definition_form_occurrence_count"] == 40
    assert surface["source_visible_noncall_symbol_value_use_count"] == 0
    assert surface["source_visible_address_taken_carrier_symbol_count"] == 0
    assert len(surface["symbols"]) == 15
    assert all(row["noncall_symbol_value_use_count"] == 0 for row in surface["symbols"])


def test_analyzer_pins_exact_occurrence_grammar():
    module = load_module()
    assert len(module.EXPECTED_OCCURRENCES) == 15
    assert sum(module.EXPECTED_OCCURRENCES.values()) == 40
    assert module.EXPECTED_TOTAL_OCCURRENCES == 40
    expected = {row["symbol"]: row["occurrence_count"] for row in load_evidence()["surface"]["symbols"]}
    assert module.EXPECTED_OCCURRENCES == expected


def test_global_pointer_and_indirect_gates_remain_fail_closed():
    gates = load_evidence()["adjudication"]
    assert gates["source_visible_exact_carrier_symbol_reference_surface_complete"] is True
    assert gates["source_visible_exact_carrier_symbol_address_taken_found"] is False
    assert gates["source_visible_exact_carrier_symbol_value_store_found"] is False
    assert gates["generic_function_pointer_stores_copies_ruled_out"] is False
    assert gates["computed_or_encoded_code_pointers_ruled_out"] is False
    assert gates["runtime_callback_registration_ruled_out"] is False
    assert gates["indirect_entry_into_carriers_ruled_out"] is False
    assert gates["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert gates["last_literal_0x004b86cf_rejected"] is False
    assert gates["p1_3_control_producer_complete"] is False
    assert gates["external_provider_count"] == 7
