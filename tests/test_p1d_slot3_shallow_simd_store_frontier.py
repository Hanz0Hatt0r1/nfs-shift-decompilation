import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1d_slot3_shallow_simd_store_frontier.py"
EVIDENCE = ROOT / "evidence" / "p1d_slot3_shallow_simd_store_frontier.json"


def load_tool():
    spec = importlib.util.spec_from_file_location("p1d_simd", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_store_class_and_stack_classifier_are_explicit():
    module = load_tool()
    for mnemonic in ("movaps", "movups", "movdqa", "movdqu", "movss", "movsd", "movq", "movlpd"):
        assert mnemonic in module.STORE_MNEMONICS
    assert module.IMPLICIT_STORE_MNEMONICS == {"maskmovq", "maskmovdqu"}
    assert module.is_stack("esp+0x4") is True
    assert module.is_stack("ebp-0x20") is True
    assert module.is_stack("esi+0x538") is False
    assert module.destination_memory("qword ptr [esp+0x10]") == "esp+0x10"


def test_authoritative_frontier_is_exact_and_stack_only():
    data = load_evidence()
    assert data["format"] == "SHIFT.P1D.P13DSlot3ShallowSIMDStoreFrontier/1"
    assert data["ready"] is True
    scan = data["scan"]
    assert scan["max_direct_call_depth"] == 4
    assert scan["reachable_unique_node_count"] == 377
    assert scan["reachable_sized_function_count"] == 377
    assert scan["simd_instruction_count"] == 497
    assert scan["simd_instruction_function_count"] == 8
    assert scan["explicit_simd_store_count"] == 14
    assert scan["explicit_simd_store_function_count"] == 4
    assert scan["stack_explicit_simd_store_count"] == 14
    assert scan["non_stack_explicit_simd_store_count"] == 0
    assert scan["implicit_mask_store_count"] == 0
    assert scan["store_functions"] == ["FUN_009011e0", "FUN_00909e0e", "FUN_0090a37e", "FUN_00911e19"]


def test_all_pinned_store_groups_are_stack_domains():
    data = load_evidence()
    groups = data["store_groups"]
    assert len(groups) == 4
    assert sum(len(row["stores"]) for row in groups) == 14
    assert all(row["destination_domain"] == "stack" for row in groups)
    assert all(row["selected_slot3_candidate"] is False for row in groups)
    assert all("[esp+" in store for row in groups for store in row["stores"])


def test_semantic_gates_remain_fail_closed():
    a = load_evidence()["adjudication"]
    assert a["shallow_mapped_canonical_simd_store_surface_complete"] is True
    assert a["all_explicit_simd_stores_are_stack_local"] is True
    assert a["shallow_non_stack_simd_store_candidate_count"] == 0
    assert a["selected_slot3_simd_writer_found"] is False
    assert a["slot3_shallow_sse_vector_copy_zero_init_subset_complete"] is True
    assert a["deeper_direct_aliases_complete"] is False
    assert a["indirect_callback_aliases_complete"] is False
    assert a["slot3_writer_provenance_proven"] is False
    assert a["p1_3d_complete"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
