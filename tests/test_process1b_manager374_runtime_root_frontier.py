import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/p1b_manager374_runtime_root_frontier.json"
BUILDER = ROOT / "tools/ghidra/build_p1b_manager374_runtime_root_frontier.py"


def payload():
    return json.loads(EVIDENCE.read_text())


def test_builder_reproduces_committed_evidence():
    out = subprocess.check_output([sys.executable, str(BUILDER)], text=True)
    assert json.loads(out) == payload()


def test_runtime_root_frontier_is_bounded_but_fail_closed():
    p = payload()
    assert p["format"] == "SHIFT.P1B.Manager374RuntimeRootFrontier/1"
    assert p["ready"] is True
    counts = p["observed_counts"]
    assert counts["static_interior_aligned_cells_in_manager_range"] == 0
    assert counts["vslot0c_exact_global_source_read_count"] == 95
    assert counts["vslot0c_exact_global_source_function_count"] == 80
    assert counts["vslot0c_proven_indirect_receiver_transfer_count"] == 3
    assert counts["vslot0c_target_dispatch_count"] == 0
    assert counts["constructor_exact_this_memory_store_count"] == 0
    assert counts["constructor_exact_this_helper_transfer_count"] == 0

    adj = p["adjudication"]
    assert adj["bounded_runtime_root_classes_composed"] is True
    assert adj["known_bounded_runtime_root_paths_can_create_manager_374_to_hdvehicle_4330_join"] is False
    assert adj["runtime_created_or_copied_outer_alias_surface_complete"] is False
    assert adj["memory_load_or_opaque_runtime_reconstruction_complete"] is False
    assert adj["helper_non_vtable_indirect_setter_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
