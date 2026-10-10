import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
EVIDENCE = ROOT / "evidence/p1b_manager374_participants_lifecycle_closure.json"
BUILDER = ROOT / "tools/ghidra/build_p1b_manager374_participants_lifecycle_closure.py"


def _load_builder():
    spec = importlib.util.spec_from_file_location("p1b_manager374_participants", BUILDER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_committed_evidence_is_reproducible():
    module = _load_builder()
    committed = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert module.build() == committed


def test_participants_lifecycle_nonzero_writer_surface_is_closed_negative():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    writers = data["lifecycle_writers"]
    assert writers["exact_target_writer_count"] == 2
    assert writers["nonzero_writer_count"] == 0
    assert {(row["function"], row["vtable_slot"], row["written_value"]) for row in writers["writers"]} == {
        ("FUN_004871f0", "+0x08", 0),
        ("FUN_00488970", "+0x14", 0),
    }


def test_active_and_vtable0c_nested_surfaces_are_closed():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    active = data["active_dispatch"]
    assert active["exact_root_forwarder_count"] == 1
    assert active["exact_root_forwarder"] == "FUN_00489b00"
    assert active["exact_root_direct_descendant_count"] == 1
    assert active["root_forwarder_direct_body_reaches_manager_374"] is False
    assert active["exact_root_direct_descendant_reaches_manager_374"] is False
    assert active["descendant_preserves_manager_root_further"] is False

    v0c = data["vtable_0x0c_indirect"]
    assert v0c["indirect_call_count"] == 6
    assert v0c["heap_helper_call_count"] == 3
    assert v0c["manager_derived_call_count"] == 3
    assert v0c["manager_438_parent_recovery_found"] is False
    assert v0c["manager_438_direct_manager_374_store_found"] is False
    assert v0c["surface_reaches_manager_374"] is False


def test_scoped_gate_promotes_without_global_overclaim():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    adj = data["adjudication"]
    assert adj["participants_lifecycle_nested_writer_surface_complete"] is True
    assert adj["participants_lifecycle_nonzero_manager_374_writer_found"] is False
    assert adj["participants_lifecycle_helper_or_indirect_setter_surface_complete"] is True
    assert adj["participants_lifecycle_can_place_fixed_hdvehicle_4330_into_manager_374"] is False
    assert adj["computed_runtime_paths_complete"] is True
    assert adj["exact_getter_alias_storage_and_stack_paths_complete"] is True
    assert adj["unrelated_manager_alias_or_unknown_root_surface_complete"] is False
    assert adj["global_helper_non_vtable_indirect_setter_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
