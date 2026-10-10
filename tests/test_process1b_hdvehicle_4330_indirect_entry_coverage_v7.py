import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_p1b_hdvehicle_4330_indirect_entry_coverage_v7.py"
EVIDENCE = ROOT / "evidence" / "p1b_hdvehicle_4330_indirect_entry_coverage_v7.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1b_ie_v7", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_checked_contract_pins_v7_counts():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/7"
    s = data["surface"]
    assert s["previous_bounded_coverage_class_count"] == 10
    assert s["composed_coverage_class_count"] == 11
    assert s["bounded_exact_carrier_hit_count"] == 0
    assert s["incoming_direct_remaining_unresolved_external_caller_count"] == 0
    assert s["incoming_indirect_navigation_edge_count"] == 19500
    assert s["incoming_indirect_resolved_target_count"] == 0
    assert s["incoming_indirect_unresolved_target_count"] == 19500


def test_v7_keeps_global_gates_fail_closed():
    g = json.loads(EVIDENCE.read_text(encoding="utf-8"))["adjudication"]
    assert g["incoming_entry_frontier_subset_included"] is True
    assert g["incoming_direct_entry_surface_complete"] is True
    assert g["remaining_incoming_entry_blocker_is_unresolved_indirect_target_recovery"] is True
    assert g["indirect_entry_into_carriers_ruled_out"] is False
    assert g["runtime_generated_or_copied_function_pointers_ruled_out"] is False
    assert g["generic_function_pointer_stores_copies_ruled_out"] is False
    assert g["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert g["last_literal_0x004b86cf_rejected"] is False
    assert g["p1_3_control_producer_complete"] is False
    assert g["external_provider_count"] == 7


def test_composer_reproduces_checked_evidence():
    module = load_module()
    out = module.build(
        ROOT / "evidence" / "p1b_hdvehicle_4330_indirect_entry_coverage_v6.json",
        ROOT / "evidence" / "p1b_hdvehicle_4330_incoming_entry_frontier.json",
    )
    assert out == json.loads(EVIDENCE.read_text(encoding="utf-8"))
