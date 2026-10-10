import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1b_hdvehicle_4330_thread_start_surface.py"
EVIDENCE = ROOT / "evidence" / "p1b_hdvehicle_4330_thread_start_callback_surface.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1b_thread_surface", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_thread_start_targets_are_disjoint_from_exact_4330_carriers():
    module = load_module()
    assert set(module.THREAD_STARTS.values()).isdisjoint(module.EXACT_CARRIERS)
    assert len(module.THREAD_STARTS) == 9


def test_expected_registration_callsites_are_finite_and_pinned():
    module = load_module()
    assert len(module.EXPECTED_CREATE_THREAD) == 7
    assert len(module.EXPECTED_BEGINTHREADEX) == 3
    assert module.EXPECTED_DYNAMIC_WRAPPER_CALLER == {("0x00939797", "0x0093984a")}


def test_evidence_closes_only_thread_start_subset():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1B.HDVehicle4330ThreadStartCallbackSurface/1"
    surface = data["surface"]
    assert surface["create_thread_direct_callsite_count"] == 7
    assert surface["beginthreadex_direct_callsite_count"] == 3
    assert surface["resolved_thread_start_count"] == 9
    assert surface["exact_4330_carrier_thread_start_count"] == 0

    adj = data["adjudication"]
    assert adj["thread_start_registration_surface_complete"] is True
    assert adj["runtime_thread_start_callback_subset_complete"] is True
    assert adj["exact_4330_carrier_thread_start_found"] is False
    assert adj["runtime_callback_registration_ruled_out"] is False
    assert adj["runtime_computed_carrier_pointers_ruled_out"] is False
    assert adj["runtime_copied_or_encoded_carrier_pointers_ruled_out"] is False
    assert adj["indirect_entry_into_carriers_ruled_out"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7


def test_pinned_source_hashes_match_tool_constants():
    module = load_module()
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["authority"]["ghidra_sqlite_sha256"] == module.SQLITE_SHA256
    assert data["authority"]["shift_exe_c_sha256"] == module.SOURCE_SHA256
