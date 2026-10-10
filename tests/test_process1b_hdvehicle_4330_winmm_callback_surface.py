import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "p1b_hdvehicle_4330_winmm_callback_surface.json"
ANALYZER = ROOT / "tools" / "ghidra" / "analyze_p1b_hdvehicle_4330_winmm_callback_surface.py"


def _load_analyzer():
    spec = importlib.util.spec_from_file_location("p1b_winmm", ANALYZER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_winmm_surface_counts_and_callbacks():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1B.HDVehicle4330WinMMCallbackSurface/1"
    surface = data["surface"]
    assert surface["physical_callsite_count"] == 6
    assert surface["waveoutopen_callsite_count"] == 3
    assert surface["waveinopen_callsite_count"] == 2
    assert surface["timesetevent_callsite_count"] == 1
    assert surface["null_callback_callsite_count"] == 4
    assert surface["nonnull_callback_callsite_count"] == 2
    assert surface["nonnull_callback_entrypoint_count"] == 2
    assert surface["exact_4330_carrier_callback_count"] == 0
    got = {(row["registration"], row["address"]) for row in surface["nonnull_callbacks"]}
    assert got == {
        ("waveInOpen@0x00999714", "0x0099955b"),
        ("timeSetEvent@0x009a8e7d", "0x009a8d8f"),
    }


def test_winmm_callbacks_are_disjoint_from_canonical_p1b_carriers():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    module = _load_analyzer()
    callbacks = {int(row["address"], 16) for row in data["surface"]["nonnull_callbacks"]}
    assert callbacks == set(module.NONNULL_CALLBACKS.values())
    assert callbacks.isdisjoint(module.EXACT_CARRIERS)
    assert module.EXACT_CARRIERS == {
        0x00769520, 0x0076B130, 0x0076DF50, 0x00768A4D, 0x00756050,
        0x00772200, 0x00772570, 0x007C3B00, 0x0076B280, 0x007618F0,
        0x00769640, 0x007567A0, 0x00756BB0, 0x00771DB0, 0x00771E10,
    }


def test_winmm_global_gates_remain_fail_closed():
    a = json.loads(EVIDENCE.read_text(encoding="utf-8"))["adjudication"]
    assert a["winmm_callback_surface_complete"] is True
    assert a["exact_4330_carrier_reachable_via_winmm"] is False
    assert a["runtime_callback_registration_ruled_out"] is False
    assert a["indirect_entry_into_carriers_ruled_out"] is False
    assert a["global_runtime_derived_4330_alias_surface_complete"] is False
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["last_literal_0x004b86cf_rejected"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
