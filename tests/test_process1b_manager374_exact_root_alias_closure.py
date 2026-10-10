import json
import subprocess
import sys
from pathlib import Path

EVIDENCE = Path("evidence/p1b_manager374_exact_root_alias_closure.json")
BUILDER = Path("tools/ghidra/build_p1b_manager374_exact_root_alias_closure.py")


def load():
    return json.loads(EVIDENCE.read_text())


def test_builder_reproduces_committed_evidence():
    subprocess.run([sys.executable, str(BUILDER), "--check"], check=True)


def test_exact_root_alias_surface_is_closed_but_reconstruction_stays_open():
    data = load()
    assert data["format"] == "SHIFT.P1B.Manager374ExactRootAliasClosure/1"
    surface = data["surface"]
    assert surface["whole_image_direct_getter_callsite_count"] == 394
    assert surface["exact_root_stack_save_count"] == 9
    assert surface["exact_root_object_or_global_store_count"] == 0
    assert surface["immediate_push_eax_after_getter_count"] == 0
    assert surface["exact_getter_stack_argument_surface_complete"] is True
    assert surface["exact_getter_stack_persistence_surface_complete"] is True
    assert surface["exact_getter_object_or_global_persistence_surface_complete"] is True
    assert surface["exact_getter_persistence_can_create_manager_plus_0x374_value"] is False

    adj = data["adjudication"]
    assert adj["escaped_storage_paths_complete"] is True
    assert adj["stack_argument_alias_paths_complete"] is True
    assert adj["exact_getter_root_alias_surface_complete"] is True
    assert adj["exact_getter_root_alias_can_establish_manager_374_to_hdvehicle_4330_join"] is False
    assert adj["non_immediate_manager_root_reconstruction_complete"] is False
    assert adj["helper_or_non_vtable_indirect_setter_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
