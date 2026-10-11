import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_p1b_hdvehicle_4330_direct_absolute_writable_indirect_recovery.py"
EVIDENCE = ROOT / "evidence" / "p1b_hdvehicle_4330_direct_absolute_writable_indirect_recovery.json"


def module():
    spec = importlib.util.spec_from_file_location("p1b_writable_recovery", TOOL)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def data():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_inventory_and_partition_counts():
    d = data()
    assert d["format"] == "SHIFT.P1B.HDVehicle4330DirectAbsoluteWritableIndirectRecovery/1"
    s = d["surface"]
    assert s["unique_writable_slot_count"] == 259
    assert s["direct_absolute_writable_transfer_count"] == 334
    assert s["fixed_bridge_slot_count"] == 2
    assert s["fixed_bridge_transfer_count"] == 2
    assert s["callback_pair_slot_count"] == 2
    assert s["callback_pair_transfer_count"] == 77
    assert s["nvapi_slot_count"] == 255
    assert s["nvapi_transfer_count"] == 255


def test_bounded_internal_static_values_do_not_hit_carriers():
    d = data()
    s = d["surface"]
    assert s["bounded_internal_or_static_candidate_value_count"] == 9
    assert s["bounded_internal_or_static_exact_carrier_hit_count"] == 0
    assert s["callback_pair_exact_carrier_hit_count"] == 0
    assert s["fixed_bridge_exact_carrier_hit_count"] == 0
    assert s["nvapi_initial_exact_carrier_hit_count"] == 0


def test_external_runtime_and_alias_paths_stay_fail_closed():
    a = data()["adjudication"]
    assert a["direct_absolute_writable_indirect_slot_inventory_complete"] is True
    assert a["bounded_internal_static_provider_subset_complete"] is True
    assert a["bounded_internal_static_provider_exact_carrier_hit_found"] is False
    assert a["nvapi_external_runtime_provider_remains_open"] is True
    assert a["callback_pair_alias_or_indirect_writers_remain_open"] is True
    assert a["register_loaded_or_base_indexed_writable_targets_remain_open"] is True
    assert a["indirect_entry_into_carriers_ruled_out"] is False
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["last_literal_0x004b86cf_rejected"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7


def test_builder_reproduces_committed_evidence():
    assert module().build() == data()
