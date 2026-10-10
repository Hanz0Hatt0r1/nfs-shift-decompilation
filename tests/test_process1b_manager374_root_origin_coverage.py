import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
EVIDENCE = ROOT / "evidence/p1b_manager374_root_origin_coverage.json"
BUILDER = ROOT / "tools/ghidra/build_p1b_manager374_root_origin_coverage.py"


def _load_builder():
    spec = importlib.util.spec_from_file_location("p1b_manager374_root_origin", BUILDER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_committed_evidence_is_reproducible():
    module = _load_builder()
    committed = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert module.build() == committed


def test_static_and_bounded_reconstruction_origins_are_exhausted():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    literal = data["known_literal_origins"]
    assert literal["count"] == 3
    assert literal["independent_runtime_producer_count"] == 0
    assert literal["sites"] == ["0x00489ae3", "0x00489afa", "0x00a9c5a0"]

    static = data["static_and_loader_origins"]
    assert static["whole_file_exact_occurrence_count"] == 3
    assert static["non_text_exact_pointer_occurrence_count"] == 0
    assert static["static_exact_pointer_cell_count"] == 0
    assert static["aligned_static_interior_cell_count"] == 0
    assert static["base_relocation_entries_available"] is False

    recon = data["bounded_reconstruction"]
    assert recon["simple_mov_immediate_seed_count"] == 38128
    assert recon["simple_arithmetic_transition_count"] == 499
    assert recon["constant_multi_register_transition_count"] == 834
    assert recon["non_literal_exact_root_count"] == 0


def test_getter_alias_and_writer_surfaces_are_closed_but_global_origin_stays_fail_closed():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    alias = data["exact_getter_aliases"]
    assert alias["direct_getter_callsite_count"] == 394
    assert alias["object_or_global_store_count"] == 0
    assert alias["stack_save_count"] == 9
    assert alias["immediate_push_eax_count"] == 0
    assert alias["escaped_storage_complete"] is True
    assert alias["stack_argument_aliases_complete"] is True

    writer = data["writer_and_helper_surfaces"]
    assert writer["computed_runtime_remaining_path_count"] == 0
    assert writer["participants_lifecycle_nonzero_writer_found"] is False
    assert writer["participants_lifecycle_helper_or_indirect_setter_surface_complete"] is True
    assert writer["participants_lifecycle_can_place_fixed_hdvehicle_4330_into_manager_374"] is False

    adj = data["adjudication"]
    assert adj["bounded_manager_root_origin_classes_composed"] is True
    assert adj["known_literal_static_loader_constant_reconstruction_origins_complete"] is True
    assert adj["known_bounded_origin_classes_create_unrelated_manager_root"] is False
    assert adj["opaque_helper_or_external_memory_root_origin_surface_complete"] is False
    assert adj["unrecognized_runtime_transform_root_origin_surface_complete"] is False
    assert adj["global_manager_root_origin_surface_complete"] is False
    assert adj["global_helper_non_vtable_indirect_setter_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
