import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/ghidra/analyze_p1a_exact_carrier_incoming_indirect_index.py"
EVIDENCE = ROOT / "evidence/p1a_p13a_exact_carrier_incoming_indirect_index_frontier.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1a_incoming_indirect", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_drive_index_counts_and_capability_gap_are_pinned():
    module = load_module()
    data = load_evidence()
    assert module.INDEX_SHA256 == "ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
    assert len(module.CARRIERS) == 16
    assert data["format"] == "SHIFT.P1A.P13AExactCarrierIncomingIndirectIndexFrontier/1"
    surface = data["incoming_indirect_surface"]
    assert surface["call_record_count"] == 200598
    assert surface["indirect_edge_count"] == 19500
    assert surface["resolved_indirect_target_count"] == 0
    assert surface["unresolved_indirect_target_count"] == 19500
    assert surface["resolved_exact_carrier_incoming_count"] == 0
    assert surface["resolved_exact_carrier_incoming"] == []


def test_synthetic_resolved_carrier_target_would_be_surfaced():
    module = load_module()
    carrier_name, carrier_address = module.CARRIERS[0]
    rows = [
        {"caller":"FUN_A","callsite":"0x1000","indirect":True,"target_address":"","target_name":""},
        {"caller":"FUN_B","callsite":"0x2000","indirect":True,"target_address":carrier_address,"target_name":carrier_name},
        {"caller":"FUN_C","callsite":"0x3000","indirect":False,"target_address":carrier_address,"target_name":carrier_name},
    ]
    summary = module.summarize_records(rows)
    assert summary["call_record_count"] == 3
    assert summary["indirect_edge_count"] == 2
    assert summary["resolved_indirect_target_count"] == 1
    assert summary["unresolved_indirect_target_count"] == 1
    assert summary["resolved_exact_carrier_incoming_count"] == 1
    assert summary["resolved_exact_carrier_incoming"][0]["callsite"] == "0x2000"


def test_zero_resolved_hits_is_not_promoted_to_absence():
    adj = load_evidence()["adjudication"]
    assert adj["p13a_incoming_indirect_index_frontier_captured"] is True
    assert adj["p13a_incoming_indirect_index_has_resolved_target_coverage"] is False
    assert adj["p13a_resolved_exact_carrier_incoming_indirect_found"] is False
    assert adj["p13a_resolved_exact_carrier_incoming_indirect_count"] == 0
    assert adj["p13a_index_can_prove_exact_carrier_incoming_indirect_absence"] is False
    assert adj["incoming_indirect_entry_ruled_out"] is False
    assert adj["runtime_callback_registration_ruled_out"] is False
    assert adj["runtime_generated_or_copied_carrier_pointers_ruled_out"] is False
    assert adj["runtime_generated_selected_wheel_pointer_stores_ruled_out"] is False
    assert adj["stored_or_escaped_aliases_ruled_out"] is False
    assert adj["p13a_slot0_complete"] is False
    assert adj["p13a_slot1_complete"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
