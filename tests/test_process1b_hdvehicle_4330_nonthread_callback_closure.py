import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools" / "ghidra" / "build_p1b_hdvehicle_4330_nonthread_callback_closure.py"
T1 = ROOT / "evidence" / "p1b_hdvehicle_4330_nonthread_callback_tranche1.json"
T2 = ROOT / "evidence" / "p1b_hdvehicle_4330_nonthread_callback_tranche2.json"
TW = ROOT / "evidence" / "process1_timer_winsock_apc_surface.json"
OUT = ROOT / "evidence" / "p1b_hdvehicle_4330_nonthread_callback_closure.json"


def load_builder():
    spec = importlib.util.spec_from_file_location("p1b_callback_closure", BUILDER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_selected_nonthread_callback_closure_reproduces_checked_evidence():
    module = load_builder()
    generated = module.build(T1, T2, TW)
    expected = json.loads(OUT.read_text(encoding="utf-8"))
    assert generated == expected


def test_selected_nonthread_callback_frontier_is_11_of_11_complete():
    data = json.loads(OUT.read_text(encoding="utf-8"))
    surface = data["surface"]
    assert surface["frontier_callsite_count"] == 11
    assert surface["resolved_callsite_count"] == 11
    assert surface["remaining_callsite_count"] == 0
    assert surface["nonnull_callback_callsite_count"] == 7
    assert surface["null_callback_callsite_count"] == 4
    assert surface["exact_4330_carrier_callback_count"] == 0


def test_global_gates_remain_fail_closed():
    adj = json.loads(OUT.read_text(encoding="utf-8"))["adjudication"]
    assert adj["selected_nonthread_callback_argument_provenance_complete"] is True
    assert adj["selected_nonthread_callback_frontier_complete"] is True
    assert adj["runtime_callback_registration_ruled_out"] is False
    assert adj["indirect_entry_into_carriers_ruled_out"] is False
    assert adj["global_runtime_derived_4330_alias_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
