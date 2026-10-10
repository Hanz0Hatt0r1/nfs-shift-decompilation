import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/ghidra/build_p1b_hdvehicle_4330_runtime_callback_coverage.py"
EVIDENCE = ROOT / "evidence/p1b_hdvehicle_4330_runtime_callback_coverage.json"
THREAD = ROOT / "evidence/p1b_hdvehicle_4330_thread_start_callback_surface.json"
NONTHREAD = ROOT / "evidence/p1b_hdvehicle_4330_nonthread_callback_closure.json"
MASSIVE = ROOT / "evidence/p1b_hdvehicle_4330_massive_thread_callback_wrapper.json"
QSORT = ROOT / "evidence/p1b_hdvehicle_4330_qsort_callback_surface.json"
WINMM = ROOT / "evidence/p1b_hdvehicle_4330_winmm_callback_surface.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1b_runtime_callback_coverage", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_builder_reproduces_committed_coverage():
    module = load_module()
    built = module.build(THREAD, NONTHREAD, MASSIVE, QSORT, WINMM)
    assert built == load_evidence()
    assert module.FORMAT == "SHIFT.P1B.HDVehicle4330RuntimeCallbackCoverage/1"
    assert module.EXPECTED_TOTAL_CALLSITES == 45
    assert module.EXPECTED_UNIQUE_ENTRYPOINTS == 33


def test_bounded_runtime_callback_coverage_is_zero_hit():
    data = load_evidence()
    surface = data["surface"]
    assert surface["closed_surface_count"] == 5
    assert surface["bounded_callback_capable_callsite_count"] == 45
    assert surface["unique_possible_callback_entrypoint_count"] == 33
    assert surface["exact_4330_carrier_entrypoint_hit_count"] == 0
    assert all(row["exact_4330_carrier_hit_count"] == 0 for row in surface["coverage"])


def test_global_callback_and_indirect_gates_stay_fail_closed():
    gates = load_evidence()["adjudication"]
    assert gates["bounded_runtime_callback_coverage_composed"] is True
    assert gates["bounded_runtime_callback_exact_4330_carrier_hit_found"] is False
    assert gates["runtime_callback_registration_ruled_out"] is False
    assert gates["generic_function_pointer_stores_copies_ruled_out"] is False
    assert gates["computed_or_encoded_code_pointers_ruled_out"] is False
    assert gates["remaining_callback_api_families_ruled_out"] is False
    assert gates["indirect_entry_into_carriers_ruled_out"] is False
    assert gates["global_runtime_derived_4330_alias_surface_complete"] is False
    assert gates["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert gates["last_literal_0x004b86cf_rejected"] is False
    assert gates["p1_3_control_producer_complete"] is False
    assert gates["external_provider_count"] == 7
