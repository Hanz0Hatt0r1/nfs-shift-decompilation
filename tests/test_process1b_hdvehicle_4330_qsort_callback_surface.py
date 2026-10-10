import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "p1b_hdvehicle_4330_qsort_callback_surface.json"
ANALYZER = ROOT / "tools" / "ghidra" / "analyze_p1b_hdvehicle_4330_qsort_callback_surface.py"


def _load_analyzer():
    spec = importlib.util.spec_from_file_location("p1b_qsort", ANALYZER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_qsort_evidence_contract():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1B.HDVehicle4330QsortCallbackSurface/1"
    assert data["ready"] is True
    surface = data["surface"]
    assert surface["direct_qsort_callsite_count"] == 16
    assert surface["possible_comparator_entrypoint_count"] == 17
    assert surface["exact_4330_carrier_comparator_count"] == 0
    assert surface["switch_resolved_dynamic_comparator_site"] == "0x004baeff"
    assert surface["switch_resolved_dynamic_choices"] == ["FUN_004ba980", "FUN_004bac50"]
    assert surface["stack_materialized_comparator_site"] == "0x009aeec0"
    assert surface["stack_materialized_comparator"] == "LAB_009aede8"


def test_qsort_comparator_set_is_disjoint_from_exact_p1b_carriers():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    module = _load_analyzer()
    got = {int(row["address"], 16) for row in data["surface"]["possible_comparator_entrypoints"]}
    assert got == set(module.COMPARATORS.values())
    assert got.isdisjoint(module.EXACT_CARRIERS)
    assert module.EXACT_CARRIERS == {
        0x00769520, 0x0076B130, 0x0076DF50, 0x00768A4D, 0x00756050,
        0x00772200, 0x00772570, 0x007C3B00, 0x0076B280, 0x007618F0,
        0x00769640, 0x007567A0, 0x00756BB0, 0x00771DB0, 0x00771E10,
    }


def test_qsort_global_gates_stay_fail_closed():
    adjudication = json.loads(EVIDENCE.read_text(encoding="utf-8"))["adjudication"]
    assert adjudication["qsort_callback_surface_complete"] is True
    assert adjudication["exact_4330_carrier_reachable_via_qsort"] is False
    assert adjudication["runtime_callback_registration_ruled_out"] is False
    assert adjudication["indirect_entry_into_carriers_ruled_out"] is False
    assert adjudication["global_runtime_derived_4330_alias_surface_complete"] is False
    assert adjudication["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adjudication["last_literal_0x004b86cf_rejected"] is False
    assert adjudication["p1_3_control_producer_complete"] is False
    assert adjudication["external_provider_count"] == 7
