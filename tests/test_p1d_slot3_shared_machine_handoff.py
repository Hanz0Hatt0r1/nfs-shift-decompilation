import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_p1d_slot3_shared_machine_handoff.py"
EVIDENCE = ROOT / "evidence" / "p1d_slot3_shared_machine_handoff.json"
OVERLAP = ROOT / "evidence" / "p1a_p13a_slot01_overlap_store_closure.json"
REP = ROOT / "evidence" / "p1a_p13a_slot01_inline_rep_machine_closure.json"
BARE = ROOT / "evidence" / "p1a_p13a_slot01_bare_string_machine_closure.json"
NAMED = ROOT / "evidence" / "p1a_p13a_slot01_named_memory_frontier.json"
CONSUMER = ROOT / "evidence" / "fun_00755950_absolute_consumed_field_machine_proof.json"


def load_tool():
    spec = importlib.util.spec_from_file_location("p1d_slot3_shared", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_builder_reproduces_checked_handoff():
    module = load_tool()
    generated = module.build(OVERLAP, REP, BARE, NAMED, CONSUMER)
    checked = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert generated == checked


def test_shared_subsets_close_without_promoting_slot3():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1D.P13DSlot3SharedMachineHandoff/1"
    assert data["slot3"]["absolute_byte_range"] == ["HDVehicle+0x28b8", "HDVehicle+0x28bf"]
    closed = data["closed_shared_subsets"]
    assert closed["exact_literal_overlap_stores"] == {
        "store_count": 25,
        "function_count": 13,
        "all_receivers_rejected_for_selected_hdvehicle": True,
        "slot3_writer_found": False,
    }
    assert closed["named_copy_set_depth4"]["named_copy_or_set_within_depth4_any_root"] is False
    assert closed["inline_rep_depth4"]["candidate_count"] == 5
    assert closed["inline_rep_depth4"]["rejected_count"] == 5
    assert closed["bare_string_depth4"]["candidate_count"] == 2
    assert closed["bare_string_depth4"]["rejected_count"] == 2
    adj = data["adjudication"]
    assert adj["slot3_exact_literal_overlap_store_subset_complete"] is True
    assert adj["slot3_shallow_named_copy_set_depth4_surface_empty"] is True
    assert adj["slot3_shallow_inline_rep_depth4_subset_complete"] is True
    assert adj["slot3_shallow_bare_string_depth4_subset_complete"] is True
    assert adj["slot3_computed_address_store_surface_complete"] is False
    assert adj["slot3_escaped_alias_store_surface_complete"] is False
    assert adj["slot3_nonstring_custom_unrolled_copy_init_complete"] is False
    assert adj["slot3_writer_provenance_proven"] is False
    assert adj["p1_3d_complete"] is False
    assert adj["external_provider_count"] == 7


def test_p1a_ownership_is_preserved():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["authority"]["p1a_contracts_consumed_not_reowned"] is True
    assert "SHIFT.P1A.P13ASlot01OverlapStoreClosure/1" in data["upstream_contracts"]
    assert "SHIFT.P1A.P13ASlot01InlineRepMachineClosure/1" in data["upstream_contracts"]
    assert "SHIFT.P1A.P13ASlot01BareStringMachineClosure/1" in data["upstream_contracts"]
    assert "SHIFT.P1A.P13ASlot01NamedMemoryFrontierEvidence/1" in data["upstream_contracts"]
