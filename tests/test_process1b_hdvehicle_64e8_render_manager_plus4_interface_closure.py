import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_render_manager_plus4_interface_closure.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_persistent_plus4_producer_and_owner_are_exact():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8RenderManagerPlus4InterfaceClosure/1"
    assert data["ready"] is True
    producer = data["producer"]
    assert producer["root_load"] == "0x0040d834 mov eax,[0x00bc185c]"
    assert producer["derived_materialization"] == "0x0040d83d lea esi,[eax+0x4]"
    assert producer["singleton_root"] == "0x00c24d80"
    assert "+0x574" in producer["persistent_store"]


def test_exact_owner_field_surface_does_not_reconstruct_root():
    surface = load_evidence()["exact_owner_field_surface"]
    assert surface["singleton_getter_direct_call_count"] == 313
    assert surface["exact_owner_plus_0x574_access_count"] == 26
    assert surface["writer_count"] == 1
    assert surface["guard_compare_count"] == 2
    assert surface["loaded_consumer_count"] == 23
    assert surface["root_minus_4_reconstruction_count"] == 0
    assert surface["derived_pointer_return_count"] == 0
    assert surface["derived_pointer_nonstack_store_count"] == 0
    assert surface["derived_pointer_stack_local_store_count"] == 1


def test_secondary_vtable_dispatches_ignore_interface_as_root():
    vt = load_evidence()["secondary_vtable"]
    assert vt["vptr_store"] == "0x0045ef7e [outer+0x4]=0x00ab55f0"
    assert vt["vtable"] == "0x00ab55f0"
    dispatches = vt["reached_dispatches"]
    assert {(d["callsite"], d["slot"], d["target"]) for d in dispatches} == {
        ("0x0050ad2a", "+0x2c", "FUN_0045d870"),
        ("0x0081d328", "+0x1c", "FUN_0045da00"),
        ("0x0082357f", "+0x04", "FUN_0045d900"),
    }
    assert all(d["incoming_ecx_used_as_root"] is False for d in dispatches)
    assert all(d["this_minus_4_reconstruction"] is False for d in dispatches)
    assert all(d["manager_getter_used"] is True for d in dispatches)


def test_stack_local_copy_remains_local_and_frontier_stays_closed():
    data = load_evidence()
    stack = data["stack_local_path"]
    assert stack["store"] == "0x0081d306 [ebp-0x64]=outer+0x4"
    assert stack["dispatch"] == "0x0081d328 vslot+0x1c"
    assert stack["escapes_stack_frame_as_pointer"] is False
    adj = data["adjudication"]
    assert adj["persistent_outer_plus_4_alias_identity_complete"] is True
    assert adj["outer_plus_4_reconstructs_exact_outer_root"] is False
    assert adj["outer_plus_4_interface_surface_closed_negative_for_exact_root_reconstruction"] is True
    assert adj["outer_plus_0x780_derived_alias_surface_complete"] is False
    assert adj["callee_created_or_external_exact_root_alias_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
