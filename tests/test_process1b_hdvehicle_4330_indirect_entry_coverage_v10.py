import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_p1b_hdvehicle_4330_indirect_entry_coverage_v10.py"
EVIDENCE = ROOT / "evidence" / "p1b_hdvehicle_4330_indirect_entry_coverage_v10.json"


def module():
    spec = importlib.util.spec_from_file_location("p1b_4330_indirect_v10", TOOL)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def data():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_v10_adds_base_indexed_writable_near_transfer_subset():
    d = data()
    assert d["format"] == "SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/10"
    s = d["surface"]
    assert s["previous_bounded_coverage_class_count"] == 13
    assert s["composed_coverage_class_count"] == 14
    assert s["base_indexed_writable_data_load_count"] == 63
    assert s["base_indexed_unique_effective_address_count"] == 51
    assert s["base_indexed_same_register_indirect_transfer_count"] == 0
    assert s["base_indexed_exact_carrier_hit_count"] == 0
    assert s["bounded_exact_carrier_hit_count"] == 0


def test_navigation_frontier_remains_capability_metric():
    s = data()["surface"]
    assert s["incoming_indirect_navigation_edge_count"] == 19500
    assert s["incoming_indirect_unresolved_target_count"] == 19500


def test_followup_propagation_and_global_gates_stay_open():
    a = data()["adjudication"]
    assert a["base_indexed_writable_same_register_near_transfer_subset_included"] is True
    assert a["base_indexed_copy_transform_spill_interblock_remain_open"] is True
    assert a["indirect_entry_into_carriers_ruled_out"] is False
    assert a["runtime_generated_or_copied_function_pointers_ruled_out"] is False
    assert a["generic_function_pointer_stores_copies_ruled_out"] is False
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["last_literal_0x004b86cf_rejected"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7


def test_builder_reproduces_committed_evidence():
    assert module().build() == data()
