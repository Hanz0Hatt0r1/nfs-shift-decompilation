import json
import subprocess
import sys
from pathlib import Path

EVIDENCE = Path("evidence/p1b_manager374_reconstruction_coverage.json")
BUILDER = Path("tools/ghidra/build_p1b_manager374_reconstruction_coverage.py")


def load():
    return json.loads(EVIDENCE.read_text())


def test_builder_reproduces_committed_evidence():
    subprocess.run([sys.executable, str(BUILDER), "--check"], check=True)


def test_bounded_reconstruction_classes_close_negative():
    data = load()
    assert data["format"] == "SHIFT.P1B.Manager374ReconstructionCoverage/1"
    s = data["surface"]
    assert s["static_exact_pointer_cell_count"] == 0
    assert s["simple_mov_immediate_seed_count"] == 38128
    assert s["simple_arithmetic_transition_count"] == 499
    assert s["simple_non_literal_exact_root_count"] == 0
    assert s["constant_multi_register_transition_count"] == 834
    assert s["constant_multi_register_non_literal_exact_root_count"] == 0

    a = data["adjudication"]
    assert a["static_exact_pointer_cells_complete"] is True
    assert a["simple_immediate_arithmetic_reconstruction_complete"] is True
    assert a["constant_only_multi_register_reconstruction_complete"] is True
    assert a["bounded_non_literal_manager_root_reconstruction_count"] == 0
    assert a["bounded_reconstruction_classes_can_create_unrelated_manager_root"] is False
    assert a["memory_load_or_opaque_runtime_reconstruction_complete"] is False
    assert a["helper_or_non_vtable_indirect_setter_surface_complete"] is False
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["last_literal_0x004b86cf_rejected"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
