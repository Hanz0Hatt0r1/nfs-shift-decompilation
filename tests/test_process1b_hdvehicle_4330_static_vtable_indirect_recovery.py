import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_p1b_hdvehicle_4330_static_vtable_indirect_recovery.py"
EVIDENCE = ROOT / "evidence" / "p1b_hdvehicle_4330_static_vtable_indirect_recovery.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1b_static_vtable_recovery", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_checked_evidence_closes_static_vtable_subset_only():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1B.HDVehicle4330StaticVtableIndirectRecovery/1"
    surface = data["surface"]
    assert surface["p1b_exact_carrier_count"] == 15
    assert surface["static_vtable_candidate_count"] == 2533
    assert surface["static_vtable_slot_count"] == 22416
    assert surface["static_vtable_exact_carrier_target_hit_count"] == 0
    assert surface["incoming_indirect_unresolved_target_count"] == 19500
    gates = data["adjudication"]
    assert gates["static_vtable_indirect_target_subset_complete"] is True
    assert gates["static_vtable_can_target_exact_p1b_carrier"] is False
    assert gates["indirect_entry_into_carriers_ruled_out"] is False
    assert gates["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert gates["last_literal_0x004b86cf_rejected"] is False
    assert gates["p1_3_control_producer_complete"] is False
    assert gates["external_provider_count"] == 7


def test_composer_reproduces_checked_evidence():
    module = load_module()
    assert module.build() == json.loads(EVIDENCE.read_text(encoding="utf-8"))
