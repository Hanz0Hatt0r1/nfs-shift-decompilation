from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1b_manager374_helper_returned_materialized_targets.py"


def module():
    spec = importlib.util.spec_from_file_location("p1b_helper_returned_target", TOOL)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_ecx_plus_374_helper_return_then_direct_write_is_candidate():
    rows = [
        (0x1000, "call", "2000 <helper>"),
        (0x1005, "mov", "DWORD PTR [eax],edx"),
        (0x1007, "ret", ""),
        (0x2000, "lea", "eax,[ecx+0x374]"),
        (0x2006, "ret", ""),
    ]
    data = module().scan_rows(rows)
    surface = data["surface"]
    assert surface["qualified_helper_return_target_count"] == 1
    helper = surface["qualified_helper_return_targets"][0]
    assert helper["target"] == "0x00002000"
    assert helper["return_argument_channel"] == "ecx"
    assert surface["qualified_helper_callsite_count"] == 1
    assert surface["post_return_write_through_candidate_count"] == 1
    candidate = surface["post_return_write_through_candidates"][0]
    assert candidate["callsite"] == "0x00001000"
    assert candidate["site"] == "0x00001005"
    assert candidate["helper_argument_channel"] == "ecx"


def test_post_return_gpr_copy_preserves_exact_target():
    rows = [
        (0x1100, "call", "2100"),
        (0x1105, "mov", "edi,eax"),
        (0x1107, "mov", "DWORD PTR [edi],ecx"),
        (0x1109, "ret", ""),
        (0x2100, "mov", "eax,edx"),
        (0x2102, "add", "eax,0x374"),
        (0x2107, "ret", ""),
    ]
    data = module().scan_rows(rows)
    assert data["surface"]["post_return_write_through_candidate_count"] == 1
    row = data["surface"]["post_return_write_through_candidates"][0]
    assert row["address_register"] == "edi"
    assert row["copy_depth"] == 1
    assert row["helper_argument_channel"] == "edx"


def test_stack_argument_across_ebp_frame_returns_plus_374():
    rows = [
        (0x1200, "call", "2200"),
        (0x1205, "mov", "DWORD PTR [eax],ecx"),
        (0x1207, "ret", ""),
        (0x2200, "push", "ebp"),
        (0x2201, "mov", "ebp,esp"),
        (0x2203, "mov", "eax,DWORD PTR [ebp+0x8]"),
        (0x2206, "add", "eax,0x374"),
        (0x220B, "leave", ""),
        (0x220C, "ret", ""),
    ]
    data = module().scan_rows(rows)
    helper = data["surface"]["qualified_helper_return_targets"][0]
    assert helper["return_argument_channel"] == "stack+0x4"
    assert helper["stack_argument_loads"][0]["logical_stack_offset"] == 4
    assert data["surface"]["post_return_write_through_candidate_count"] == 1


def test_helper_branch_fails_closed_even_if_later_text_returns_plus_374():
    rows = [
        (0x1300, "call", "2300"),
        (0x1305, "mov", "DWORD PTR [eax],ecx"),
        (0x1307, "ret", ""),
        (0x2300, "test", "ecx,ecx"),
        (0x2302, "je", "2310"),
        (0x2304, "lea", "eax,[ecx+0x374]"),
        (0x230A, "ret", ""),
        (0x2310, "xor", "eax,eax"),
        (0x2312, "ret", ""),
    ]
    data = module().scan_rows(rows)
    assert data["surface"]["qualified_helper_return_target_count"] == 0
    assert data["surface"]["post_return_write_through_candidate_count"] == 0


def test_nested_call_inside_helper_fails_closed():
    rows = [
        (0x1400, "call", "2400"),
        (0x1405, "mov", "DWORD PTR [eax],ecx"),
        (0x1407, "ret", ""),
        (0x2400, "mov", "eax,ecx"),
        (0x2402, "call", "2500"),
        (0x2407, "add", "eax,0x374"),
        (0x240C, "ret", ""),
        (0x2500, "ret", ""),
    ]
    data = module().scan_rows(rows)
    assert data["surface"]["qualified_helper_return_target_count"] == 0


def test_post_return_mutation_kills_target_before_write():
    rows = [
        (0x1500, "call", "2500"),
        (0x1505, "add", "eax,0x4"),
        (0x1508, "mov", "DWORD PTR [eax],ecx"),
        (0x150A, "ret", ""),
        (0x2500, "lea", "eax,[ecx+0x374]"),
        (0x2506, "ret", ""),
    ]
    data = module().scan_rows(rows)
    assert data["surface"]["qualified_helper_return_target_count"] == 1
    assert data["surface"]["post_return_write_through_candidate_count"] == 0


def test_read_only_post_return_dereference_is_separate():
    rows = [
        (0x1600, "call", "2600"),
        (0x1605, "cmp", "DWORD PTR [eax],0x0"),
        (0x1609, "ret", ""),
        (0x2600, "lea", "eax,[edx+0x374]"),
        (0x2606, "ret", ""),
    ]
    data = module().scan_rows(rows)
    call = data["surface"]["qualified_helper_callsites"][0]
    assert call["caller_post_scan"]["read_count"] == 1
    assert call["caller_post_scan"]["write_count"] == 0
    assert data["surface"]["post_return_write_through_candidate_count"] == 0


def test_unrelated_constant_return_does_not_qualify():
    rows = [
        (0x1700, "call", "2700"),
        (0x1705, "mov", "DWORD PTR [eax],ecx"),
        (0x1707, "ret", ""),
        (0x2700, "mov", "eax,0x12340374"),
        (0x2705, "ret", ""),
    ]
    data = module().scan_rows(rows)
    assert data["surface"]["qualified_helper_return_target_count"] == 0


def test_indirect_and_external_calls_do_not_become_helper_candidates():
    rows = [
        (0x1800, "call", "DWORD PTR [eax+0x4]"),
        (0x1804, "call", "900000 <external>"),
        (0x1809, "ret", ""),
    ]
    data = module().scan_rows(rows)
    assert data["surface"]["indirect_call_count"] == 1
    assert data["surface"]["unresolved_direct_target_count"] == 1
    assert data["surface"]["qualified_helper_return_target_count"] == 0


def test_helper_dynamic_stack_adjustment_fails_closed():
    rows = [
        (0x1900, "call", "2900"),
        (0x1905, "mov", "DWORD PTR [eax],ecx"),
        (0x1907, "ret", ""),
        (0x2900, "sub", "esp,eax"),
        (0x2902, "mov", "eax,DWORD PTR [esp+0x4]"),
        (0x2906, "add", "eax,0x374"),
        (0x290B, "ret", ""),
    ]
    data = module().scan_rows(rows)
    assert data["surface"]["qualified_helper_return_target_count"] == 0


def test_partial_register_clobber_kills_helper_return_provenance():
    rows = [
        (0x1A00, "call", "2a00"),
        (0x1A05, "mov", "DWORD PTR [eax],ecx"),
        (0x1A07, "ret", ""),
        (0x2A00, "lea", "eax,[ecx+0x374]"),
        (0x2A06, "mov", "al,0x1"),
        (0x2A08, "ret", ""),
    ]
    data = module().scan_rows(rows)
    assert data["surface"]["qualified_helper_return_target_count"] == 0


def test_direct_target_parser_accepts_objdump_forms():
    mod = module()
    assert mod.parse_direct_target("401000") == 0x401000
    assert mod.parse_direct_target("0x401000") == 0x401000
    assert mod.parse_direct_target("401000 <FUN_00401000>") == 0x401000
    assert mod.parse_direct_target("DWORD PTR [eax]") is None


def test_final_semantic_gates_remain_fail_closed():
    data = module().scan_rows([])
    adj = data["adjudication"]
    assert adj["direct_helper_returned_plus_374_target_subset_scanned"] is True
    assert adj["helper_returned_plus_374_write_candidates_classified"] is False
    assert adj["helper_returned_materialized_address_surface_complete"] is False
    assert adj["global_helper_non_vtable_indirect_setter_surface_complete"] is False
    assert adj["external_or_unknown_origin_outer_alias_surface_complete"] is False
    assert adj["independent_unnamed_opaque_or_external_runtime_root_synthesis_complete"] is False
    assert adj["unrecognized_runtime_transform_root_origin_surface_complete"] is False
    assert adj["global_manager_root_origin_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
