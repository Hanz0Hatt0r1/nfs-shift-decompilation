import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
EVIDENCE = ROOT / "evidence/p1b_render_manager_live_call_boundary_closure.json"
BUILDER = ROOT / "tools/ghidra/build_p1b_render_manager_live_call_boundary_closure.py"


def _load_builder():
    spec = importlib.util.spec_from_file_location("p1b_live_call_boundary", BUILDER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_committed_evidence_is_reproducible():
    module = _load_builder()
    committed = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert module.build() == committed


def test_live_call_boundary_surface_is_bounded_and_classified():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    inv = data["live_call_boundary_inventory"]
    assert inv["call_boundary_observation_count"] == 303
    assert inv["unique_callsite_count"] == 302
    assert inv["caller_saved_exact_alias_unique_callsite_count"] == 95
    assert inv["caller_saved_direct_callsite_count"] == 92
    assert inv["caller_saved_indirect_callsite_count"] == 3

    indirect = data["indirect_exact_root_calls"]
    assert indirect["count"] == 3
    assert indirect["known_vtable_offsets"] == ["+0x1c", "+0x20"]
    assert indirect["non_vtable_indirect_call_count"] == 0
    assert indirect["target_vslot_plus_0x0c_dispatch_count"] == 0
    assert {row["callsite"] for row in indirect["calls"]} == {
        "0x0056bcf2",
        "0x0056bd09",
        "0x0056bd59",
    }


def test_direct_callee_and_global_gates_remain_fail_closed():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    direct = data["direct_exact_root_callees"]
    assert direct["bounded_target_count"] == 17
    assert direct["closed_target_count"] == 17
    assert direct["remaining_target_count"] == 0
    assert direct["can_export_or_recreate_exact_outer_root"] is False

    adj = data["adjudication"]
    assert adj["canonical_lineage_live_call_boundary_surface_complete"] is True
    assert adj["all_live_exact_root_indirect_calls_classified"] is True
    assert adj["canonical_lineage_live_exact_root_non_vtable_indirect_setter_surface_complete"] is True
    assert adj["canonical_lineage_live_exact_root_non_vtable_indirect_setter_found"] is False
    assert adj["helper_non_vtable_setter_surface_complete"] is False
    assert adj["opaque_helper_created_exact_root_surface_complete"] is False
    assert adj["arbitrary_unknown_memory_exact_root_alias_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
