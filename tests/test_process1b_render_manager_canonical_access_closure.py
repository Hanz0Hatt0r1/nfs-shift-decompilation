import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_p1b_render_manager_canonical_access_closure.py"
EVIDENCE = ROOT / "evidence" / "p1b_render_manager_canonical_access_closure.json"

spec = importlib.util.spec_from_file_location("build_p1b_render_manager_canonical_access_closure", TOOL)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_reproduces_committed_evidence():
    assert m.build() == load_evidence()


def test_raw_occurrence_partition_is_complete():
    data = load_evidence()
    part = data["raw_occurrence_partition"]
    assert part["whole_image_little_endian_occurrence_count"] == 115
    assert part["direct_load_count"] == 112
    assert part["direct_store_count"] == 2
    assert part["slot_address_literal_materialization_count"] == 1
    assert part["slot_address_literal_site"] == "0x004fb9af"
    assert part["partition_complete"] is True


def test_simple_reconstruction_has_no_hidden_nonliteral_slot():
    scan = load_evidence()["simple_slot_address_reconstruction"]
    assert scan["mov_r32_imm32_seed_count"] == 38128
    assert scan["same_register_add_sub_lea_transition_count"] == 267
    assert scan["literal_target_production_count"] == 1
    assert scan["nonliteral_target_production_count"] == 0


def test_canonical_surface_closes_without_promoting_unknown_memory():
    data = load_evidence()
    prop = data["origin_and_propagation"]
    assert prop["bounded_direct_target_count"] == 17
    assert prop["bounded_direct_target_remaining_count"] == 0
    assert prop["direct_exact_global_memory_store_count"] == 0
    assert prop["direct_exact_global_push_count"] == 0
    assert prop["known_returned_root_can_persist_or_dispatch"] is False

    adj = data["adjudication"]
    assert adj["canonical_render_manager_slot_access_surface_complete"] is True
    assert adj["canonical_hidden_simple_arithmetic_slot_access_found"] is False
    assert adj["arbitrary_unknown_memory_exact_root_alias_surface_complete"] is False
    assert adj["opaque_helper_created_exact_root_surface_complete"] is False
    assert adj["helper_non_vtable_setter_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
