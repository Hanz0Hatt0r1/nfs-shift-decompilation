import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1b_hdvehicle_4330_incoming_direct_calls.py"
EVIDENCE = ROOT / "evidence" / "p1b_hdvehicle_4330_incoming_direct_call_frontier.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1b_4330_incoming", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_checked_evidence_pins_25_to_11_to_7_frontier():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1B.HDVehicle4330IncomingDirectCallFrontier/1"
    assert data["carrier_set"]["count"] == 15
    surface = data["incoming_direct_surface"]
    assert surface["callsite_count"] == 25
    assert surface["exact_carrier_internal_callsite_count"] == 14
    assert surface["external_callsite_count"] == 11
    assert surface["external_caller_count"] == 7
    assert len(surface["external_calls"]) == 11
    assert {row["address"] for row in surface["external_callers"]} == {
        "0x00aa2850", "0x0074da70", "0x00798df0", "0x00491d86",
        "0x00a7063f", "0x00a72322", "0x00795d60",
    }
    assert sum(row["caller"] == "0x00798df0" for row in surface["external_calls"]) == 5


def test_frontier_stays_fail_closed_until_external_receiver_provenance_closes():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    gates = data["adjudication"]
    assert gates["incoming_direct_call_frontier_inventory_complete"] is True
    assert gates["known_internal_carrier_edges_separated"] is True
    assert gates["external_receiver_provenance_complete"] is False
    assert gates["indirect_entry_into_carriers_ruled_out"] is False
    assert gates["global_runtime_derived_4330_alias_surface_complete"] is False
    assert gates["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert gates["last_literal_0x004b86cf_rejected"] is False
    assert gates["p1_3_control_producer_complete"] is False
    assert gates["external_provider_count"] == 7


def test_analyzer_and_evidence_pin_same_external_caller_set():
    module = load_module()
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    evidence = {row["address"]: row["name"] for row in data["incoming_direct_surface"]["external_callers"]}
    assert evidence == module.EXPECTED_EXTERNAL_CALLERS
