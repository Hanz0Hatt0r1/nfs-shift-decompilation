import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "tools" / "ghidra" / "analyze_p1b_hdvehicle_4330_massive_thread_callback_wrapper.py"
EVIDENCE = ROOT / "evidence" / "p1b_hdvehicle_4330_massive_thread_callback_wrapper.json"


def load_analyzer():
    spec = importlib.util.spec_from_file_location("p1b_massive_thread", ANALYZER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_checked_evidence_pins_two_concrete_callbacks():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    surface = data["surface"]
    assert surface["direct_caller_count"] == 2
    assert surface["resolved_callback_count"] == 2
    assert {row["address"] for row in surface["resolved_callbacks"]} == {
        "0x0060b457",
        "0x0061d300",
    }
    assert surface["fixed_thread_start"] == "0x0061cd93"
    assert surface["exact_4330_carrier_callback_count"] == 0
    assert surface["exact_4330_carrier_thread_start"] is False


def test_analyzer_uses_canonical_p1b_carrier_set():
    module = load_analyzer()
    expected = {
        0x00769520, 0x0076B130, 0x0076DF50, 0x00768A4D, 0x00756050,
        0x00772200, 0x00772570, 0x007C3B00, 0x0076B280, 0x007618F0,
        0x00769640, 0x007567A0, 0x00756BB0, 0x00771DB0, 0x00771E10,
    }
    assert module.P1B_EXACT_CARRIERS == expected
    assert set(module.CALLBACKS.values()).isdisjoint(expected)
    assert module.THREAD_START not in expected


def test_global_gates_remain_fail_closed():
    adj = json.loads(EVIDENCE.read_text(encoding="utf-8"))["adjudication"]
    assert adj["massive_thread_callback_wrapper_surface_complete"] is True
    assert adj["runtime_callback_registration_ruled_out"] is False
    assert adj["indirect_entry_into_carriers_ruled_out"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
