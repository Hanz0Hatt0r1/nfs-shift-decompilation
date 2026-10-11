import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_p1b_hdvehicle_4330_indirect_entry_coverage_v9.py"
EVIDENCE = ROOT / "evidence" / "p1b_hdvehicle_4330_indirect_entry_coverage_v9.json"


def module():
    spec = importlib.util.spec_from_file_location("p1b_4330_indirect_v9", TOOL)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def data():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_v9_adds_writable_data_class_without_carrier_hits():
    d = data()
    assert d["format"] == "SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/9"
    s = d["surface"]
    assert s["previous_bounded_coverage_class_count"] == 12
    assert s["composed_coverage_class_count"] == 13
    assert s["direct_absolute_writable_transfer_count"] == 334
    assert s["direct_absolute_writable_unique_slot_count"] == 259
    assert s["direct_absolute_writable_bounded_candidate_value_count"] == 9
    assert s["direct_absolute_writable_exact_carrier_hit_count"] == 0
    assert s["bounded_exact_carrier_hit_count"] == 0


def test_navigation_frontier_is_not_falsely_decremented():
    s = data()["surface"]
    assert s["incoming_indirect_navigation_edge_count"] == 19500
    assert s["incoming_indirect_unresolved_target_count"] == 19500


def test_global_gates_remain_fail_closed():
    a = data()["adjudication"]
    assert a["direct_absolute_writable_internal_static_target_subset_included"] is True
    assert a["external_runtime_writable_target_providers_remain_open"] is True
    assert a["register_loaded_or_base_indexed_writable_targets_remain_open"] is True
    assert a["indirect_entry_into_carriers_ruled_out"] is False
    assert a["runtime_generated_or_copied_function_pointers_ruled_out"] is False
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["last_literal_0x004b86cf_rejected"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7


def test_builder_reproduces_committed_evidence():
    assert module().build() == data()
