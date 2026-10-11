import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1b_manager374_whole_image_plus374_writers.py"


def module():
    spec = importlib.util.spec_from_file_location("p1b_plus374", TOOL)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_mov_plus374_store_is_candidate():
    data = module().scan_rows([
        (0x401000, "mov", "DWORD PTR [ecx+0x374],eax"),
    ])
    assert data["surface"]["exact_plus_374_write_candidate_count"] == 1
    row = data["surface"]["exact_plus_374_write_candidates"][0]
    assert row["site"] == "0x00401000"
    assert row["registers"] == ["ecx"]


def test_rmw_indexed_plus374_store_is_candidate():
    data = module().scan_rows([
        (0x402000, "add", "DWORD PTR [esi+edx*4+0x374],0x1"),
    ])
    assert data["surface"]["exact_plus_374_write_candidate_count"] == 1
    assert data["surface"]["exact_plus_374_write_candidates"][0]["registers"] == ["edx", "esi"]


def test_read_only_source_operand_is_not_candidate():
    data = module().scan_rows([
        (0x403000, "mov", "eax,DWORD PTR [ecx+0x374]"),
        (0x403004, "cmp", "DWORD PTR [ecx+0x374],0x0"),
    ])
    assert data["surface"]["exact_plus_374_write_candidate_count"] == 0
    assert data["surface"]["exact_plus_374_other_first_memory_operand_count"] == 1
    assert data["surface"]["exact_plus_374_other_first_memory_operands"][0]["mnemonic"] == "cmp"


def test_control_indirect_memory_operand_is_fail_closed_not_writer():
    data = module().scan_rows([
        (0x404000, "call", "DWORD PTR [ecx+0x374]"),
        (0x404004, "jmp", "DWORD PTR [esi+0x374]"),
    ])
    assert data["surface"]["exact_plus_374_write_candidate_count"] == 0
    assert data["surface"]["exact_plus_374_other_first_memory_operand_count"] == 2


def test_neighboring_displacement_is_not_exact_plus374():
    data = module().scan_rows([
        (0x405000, "mov", "DWORD PTR [ecx+0x1374],eax"),
        (0x405004, "mov", "DWORD PTR [ecx-0x374],eax"),
    ])
    assert data["surface"]["exact_plus_374_write_candidate_count"] == 0
    assert data["surface"]["exact_plus_374_other_first_memory_operand_count"] == 0


def test_semantic_gates_remain_fail_closed():
    adjudication = module().scan_rows([])["adjudication"]
    assert adjudication["whole_image_exact_plus_374_write_mnemonic_candidate_inventory_complete"] is True
    assert adjudication["all_plus_374_candidate_receivers_classified"] is False
    assert adjudication["unknown_or_unrelated_manager_root_alias_surface_complete"] is False
    assert adjudication["global_helper_non_vtable_indirect_setter_surface_complete"] is False
    assert adjudication["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adjudication["last_literal_0x004b86cf_rejected"] is False
    assert adjudication["p1_3_control_producer_complete"] is False
    assert adjudication["external_provider_count"] == 7
