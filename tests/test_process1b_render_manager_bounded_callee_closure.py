import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "p1b_render_manager_bounded_callee_closure.json"


def load():
    return json.loads(EVIDENCE.read_text())


def test_bounded_direct_receiver_surface_is_fully_closed():
    data = load()
    assert data["format"] == "SHIFT.P1B.RenderManagerBoundedCalleeClosure/1"
    assert data["ready"] is True
    surf = data["bounded_direct_receiver_targets"]
    assert surf["total"] == 17
    assert surf["closed"] == 17
    assert surf["remaining"] == 0
    assert surf["byaddress_local_helper_paths_closed"] == 2


def test_scoped_gate_promotes_without_global_overclaim():
    adj = load()["adjudication"]
    assert adj["bounded_direct_callee_alias_surface_complete"] is True
    assert adj["bounded_direct_callee_can_export_or_recreate_exact_outer_root"] is False
    assert adj["external_or_unknown_origin_alias_surface_complete"] is False
    assert adj["memory_load_or_opaque_runtime_reconstruction_complete"] is False
    assert adj["helper_non_vtable_indirect_setter_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
