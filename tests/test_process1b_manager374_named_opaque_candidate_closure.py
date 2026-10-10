import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "p1b_manager374_named_opaque_candidate_closure.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_named_candidate_inventory_is_closed_negative():
    data = load_evidence()
    assert data["format"] == "SHIFT.P1B.Manager374NamedOpaqueCandidateClosure/1"
    assert data["ready"] is True
    assert data["summary"]["named_candidate_count"] == 2
    assert data["summary"]["named_candidate_exportable_count"] == 0
    assert data["summary"]["vslot24_observed_dispatch_preserves_root"] is False
    assert data["summary"]["vslot0c_exact_lineage_dispatch_count"] == 0
    ids = {row["id"] for row in data["named_opaque_candidates"]}
    assert ids == {"render-child-vslot24-eax-residue", "render-manager-vslot0c"}


def test_global_root_origin_remains_fail_closed():
    adj = load_evidence()["adjudication"]
    assert adj["named_opaque_manager_root_candidate_surface_complete"] is True
    assert adj["named_opaque_manager_root_candidate_count"] == 2
    assert adj["named_opaque_manager_root_exportable_candidate_count"] == 0
    assert adj["known_named_opaque_helpers_can_create_independent_manager_root_alias"] is False
    assert adj["independent_unnamed_opaque_or_external_runtime_root_synthesis_complete"] is False
    assert adj["global_manager_root_origin_surface_complete"] is False
    assert adj["global_helper_non_vtable_indirect_setter_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
