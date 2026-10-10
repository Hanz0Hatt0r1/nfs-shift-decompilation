import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/p1b_manager374_writer_coverage.json"
BUILDER = ROOT / "tools/ghidra/build_p1b_manager374_writer_coverage.py"


def load_builder():
    spec = importlib.util.spec_from_file_location("builder", BUILDER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_committed_evidence_matches_builder():
    committed = json.loads(EVIDENCE.read_text())
    assert load_builder().build() == committed


def test_writer_coverage_is_bounded_and_fail_closed():
    data = json.loads(EVIDENCE.read_text())
    assert data["format"] == "SHIFT.P1B.Manager374WriterCoverage/1"
    s = data["surface"]
    assert s["exact_root_direct_callee_count"] == 9
    assert s["exact_root_direct_manager_374_writer_count"] == 1
    assert s["only_direct_nonzero_writer"] == "FUN_00d60660"
    assert s["computed_runtime_original_path_count"] == 18
    assert s["computed_runtime_remaining_path_count"] == 0
    assert s["direct_bulk_copy_literal_writer_surface_complete"] is True
    assert s["manager_374_literal_writer_surface_complete"] is True

    a = data["adjudication"]
    assert a["bounded_manager_374_writer_classes_complete"] is True
    assert a["bounded_writer_classes_place_fixed_hdvehicle_4330_into_manager_374"] is False
    assert a["escaped_storage_paths_complete"] is False
    assert a["stack_argument_alias_paths_complete"] is False
    assert a["helper_alias_or_non_vtable_indirect_setter_still_possible"] is True
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["last_literal_0x004b86cf_rejected"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
