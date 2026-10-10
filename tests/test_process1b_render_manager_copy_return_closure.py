import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/p1b_render_manager_copy_return_closure.json"
BUILDER = ROOT / "tools/ghidra/build_p1b_render_manager_copy_return_closure.py"


def payload():
    return json.loads(EVIDENCE.read_text())


def test_builder_reproduces_evidence():
    out = subprocess.check_output([sys.executable, str(BUILDER)], text=True)
    assert json.loads(out) == payload()


def test_copy_return_surface_closes_only_bounded_classes():
    p = payload()
    assert p["format"] == "SHIFT.P1B.RenderManagerCopyReturnClosure/1"
    assert p["ready"] is True

    cfg = p["machine_cfg"]
    assert cfg["exact_global_seed_count"] == 112
    assert cfg["exact_root_memory_store_count"] == 0
    assert cfg["exact_root_push_count"] == 0
    assert cfg["unmodelled_exact_alias_transfer_count"] == 0
    assert cfg["derived_subobject_transition_count"] == 3

    ret = p["returned_root"]
    assert ret["conditional_exact_eax_return_function_count"] == 7
    assert ret["direct_return_callsite_count"] == 6
    assert ret["direct_return_consumers_persist_or_dispatch_exact_root"] is False
    assert ret["table_return_consumer_surface_complete"] is True
    assert ret["table_return_consumers_persist_or_dispatch_exact_root"] is False

    adj = p["adjudication"]
    assert adj["direct_exact_global_postconstruction_copy_surface_complete"] is True
    assert adj["direct_exact_global_postconstruction_copy_surface_closed_negative"] is True
    assert adj["known_returned_root_consumer_surface_complete"] is True
    assert adj["known_returned_root_can_persist_or_dispatch_exact_root"] is False
    assert adj["derived_subobject_alias_surface_complete"] is False
    assert adj["callee_created_or_external_exact_root_alias_surface_complete"] is False
    assert adj["memory_load_or_opaque_runtime_reconstruction_complete"] is False
    assert adj["helper_non_vtable_indirect_setter_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
