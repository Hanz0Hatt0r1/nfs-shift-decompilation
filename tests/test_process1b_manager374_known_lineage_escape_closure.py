import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "p1b_manager374_known_lineage_escape_closure.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_shape_and_counts():
    data = load_evidence()
    assert data["format"] == "SHIFT.P1B.Manager374KnownLineageEscapeClosure/1"
    assert data["ready"] is True
    assert data["known_root_lineage"]["exact_getter_callsite_count"] == 394
    assert data["known_root_lineage"]["exact_root_object_or_global_store_count"] == 0
    assert data["known_root_lineage"]["exact_root_immediate_push_count"] == 0
    assert data["known_root_lineage"]["direct_exact_root_callee_count"] == 9
    assert data["known_root_lineage"]["direct_exact_root_callees_all_inside_retail_image"] is True
    assert data["setter_surfaces"]["direct_manager_receiver_call_count"] == 44
    assert data["setter_surfaces"]["manager_vtable_slot_count"] == 18
    assert data["setter_surfaces"]["participants_lifecycle_indirect_call_count"] == 6


def test_known_lineage_is_closed_but_global_origin_remains_fail_closed():
    adj = load_evidence()["adjudication"]
    assert adj["known_manager_root_lineage_escape_surface_complete"] is True
    assert adj["known_manager_root_lineage_persists_into_object_or_global_memory"] is False
    assert adj["known_manager_root_lineage_escapes_as_stack_argument"] is False
    assert adj["known_manager_root_lineage_reaches_external_direct_callee"] is False
    assert adj["known_manager_root_lineage_can_seed_external_memory_alias"] is False
    assert adj["known_manager_root_lineage_helper_or_indirect_setter_surface_complete"] is True
    assert adj["independent_opaque_or_external_runtime_root_synthesis_complete"] is False
    assert adj["global_manager_root_origin_surface_complete"] is False
    assert adj["global_helper_non_vtable_indirect_setter_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
