import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_p1b_hdvehicle_4330_incoming_entry_frontier.py"
EVIDENCE = ROOT / "evidence" / "p1b_hdvehicle_4330_incoming_entry_frontier.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1b_incoming_entry", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_checked_contract_pins_direct_and_indirect_frontier():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1B.HDVehicle4330IncomingEntryFrontier/1"
    s = data["surface"]
    assert s["p1b_exact_carrier_count"] == 15
    assert (s["incoming_direct_callsite_count"], s["incoming_direct_internal_callsite_count"], s["incoming_direct_external_callsite_count"]) == (25, 14, 11)
    assert s["incoming_direct_remaining_unresolved_external_caller_count"] == 0
    assert s["navigation_index_indirect_edge_count"] == 19500
    assert s["navigation_index_resolved_indirect_target_count"] == 0
    assert s["navigation_index_unresolved_indirect_target_count"] == 19500


def test_frontier_stays_fail_closed_for_indirect_entry():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    g = data["adjudication"]
    assert g["incoming_direct_entry_surface_complete"] is True
    assert g["incoming_direct_external_receiver_provenance_complete"] is True
    assert g["incoming_direct_preexisting_4330_alias_found"] is False
    assert g["remaining_incoming_entry_blocker_is_unresolved_indirect_target_recovery"] is True
    assert g["incoming_indirect_index_has_resolved_target_coverage"] is False
    assert g["indirect_entry_into_carriers_ruled_out"] is False
    assert g["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert g["last_literal_0x004b86cf_rejected"] is False
    assert g["p1_3_control_producer_complete"] is False
    assert g["external_provider_count"] == 7


def test_composer_reproduces_checked_evidence():
    module = load_module()
    out = module.build(
        ROOT / "evidence" / "p1b_hdvehicle_4330_incoming_direct_call_frontier.json",
        ROOT / "evidence" / "p1b_hdvehicle_4330_external_caller_final_tranche.json",
        ROOT / "evidence" / "p1a_p13a_exact_carrier_incoming_indirect_index_frontier.json",
    )
    checked = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert out == checked
