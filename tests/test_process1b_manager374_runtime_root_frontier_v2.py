import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools/ghidra/build_p1b_manager374_runtime_root_frontier_v2.py"
EVIDENCE = ROOT / "evidence/p1b_manager374_runtime_root_frontier_v2.json"


def module():
    spec = importlib.util.spec_from_file_location("p1b_runtime_root_frontier_v2", BUILDER)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_builder_reproduces_committed_evidence():
    assert module().build() == evidence()


def test_program_internal_exact_root_alias_surface_is_closed_negative():
    data = evidence()
    surface = data["program_internal_exact_root_surface"]
    assert surface["pre_global_exact_this_memory_store_count"] == 0
    assert surface["pre_global_exact_this_helper_transfer_count"] == 0
    assert surface["canonical_direct_load_count"] == 112
    assert surface["postconstruction_exact_root_memory_store_count"] == 0
    assert surface["postconstruction_exact_root_push_count"] == 0
    assert surface["postconstruction_unmodelled_exact_alias_transfer_count"] == 0
    assert surface["derived_subobject_transition_count"] == 3
    assert surface["derived_subobject_reconstructs_exact_outer_root"] is False
    assert surface["conditional_exact_eax_return_function_count"] == 7
    assert surface["direct_return_callsite_count"] == 6
    assert surface["returned_root_consumer_can_persist_or_dispatch"] is False
    assert surface["bounded_direct_callee_target_count"] == 17
    assert surface["bounded_direct_callee_remaining_count"] == 0
    assert surface["live_call_boundary_observation_count"] == 303
    assert surface["live_call_boundary_unique_callsite_count"] == 302
    assert surface["indirect_exact_root_call_count"] == 3
    assert surface["non_vtable_indirect_exact_root_call_count"] == 0


def test_named_opaque_candidates_are_closed_but_unnamed_class_remains_open():
    data = evidence()
    assert data["named_opaque_surface"] == {
        "candidate_count": 2,
        "exportable_candidate_count": 0,
    }
    adj = data["adjudication"]
    assert adj["named_opaque_manager_root_candidate_surface_complete"] is True
    assert adj["known_named_opaque_manager_root_exportable_candidate_count"] == 0
    assert adj["independent_unnamed_opaque_or_external_runtime_root_synthesis_complete"] is False


def test_only_internal_runtime_alias_gate_promotes():
    adj = evidence()["adjudication"]
    assert adj["program_internal_canonical_lineage_runtime_alias_surface_complete"] is True
    assert adj["program_internal_canonical_lineage_runtime_alias_found"] is False
    assert adj["canonical_lineage_pre_global_escape_surface_complete"] is True
    assert adj["canonical_lineage_postconstruction_copy_surface_complete"] is True
    assert adj["canonical_lineage_returned_root_consumer_surface_complete"] is True
    assert adj["canonical_lineage_derived_subobject_surface_complete"] is True
    assert adj["canonical_lineage_live_call_boundary_surface_complete"] is True

    assert adj["external_or_unknown_origin_outer_alias_surface_complete"] is False
    assert adj["unrecognized_runtime_transform_root_origin_surface_complete"] is False
    assert adj["memory_load_or_opaque_runtime_reconstruction_complete"] is False
    assert adj["global_manager_root_origin_surface_complete"] is False
    assert adj["global_helper_non_vtable_indirect_setter_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7


def test_surviving_frontier_is_only_external_or_unrecognized_origin_classes():
    frontier = evidence()["surviving_frontier"]
    assert len(frontier) == 3
    assert all("canonical" not in item.lower() or "without a canonical" in item.lower() for item in frontier)
    assert any("unknown-origin" in item for item in frontier)
    assert any("opaque helper" in item for item in frontier)
    assert any("unrecognized runtime transform" in item for item in frontier)
