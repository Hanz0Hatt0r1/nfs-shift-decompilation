from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1b_manager374_materialized_direct_call_setters.py"


def module():
    spec = importlib.util.spec_from_file_location("p1b_manager374_direct_call_setters", TOOL)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_ecx_forwarded_target_address_finds_direct_callee_write():
    rows = [
        (0x1000, "lea", "eax,[esi+0x374]"),
        (0x1006, "mov", "ecx,eax"),
        (0x1008, "call", "2000 <helper>"),
        (0x100D, "ret", ""),
        (0x2000, "mov", "DWORD PTR [ecx],edx"),
        (0x2002, "ret", ""),
    ]
    data = module().scan_rows(rows)
    surface = data["surface"]
    assert surface["materialized_plus_374_seed_count"] == 1
    assert surface["direct_call_argument_boundary_count"] == 1
    assert surface["indirect_call_argument_boundary_count"] == 0
    assert surface["direct_callee_write_through_candidate_count"] == 1
    row = surface["direct_callee_write_through_candidates"][0]
    assert row["site"] == "0x00002000"
    assert row["callsite"] == "0x00001008"
    assert row["argument_channel"] == "ecx"
    assert row["receiver_register"] == "esi"


def test_stack_argument_survives_standard_ebp_frame_and_spacing_push():
    rows = [
        (0x1100, "lea", "eax,[edi+0x374]"),
        (0x1106, "push", "eax"),
        (0x1107, "push", "0x0"),
        (0x1109, "call", "2100 <helper>"),
        (0x110E, "ret", ""),
        (0x2100, "push", "ebp"),
        (0x2101, "mov", "ebp,esp"),
        (0x2103, "mov", "eax,DWORD PTR [ebp+0xc]"),
        (0x2106, "mov", "DWORD PTR [eax],ecx"),
        (0x2108, "ret", ""),
    ]
    data = module().scan_rows(rows)
    boundary = data["surface"]["direct_call_argument_boundaries"][0]
    assert boundary["stack_argument_channels"] == ["stack+0x8"]
    callee = boundary["callee_scan"]
    assert callee["stack_argument_reload_count"] == 1
    assert callee["stack_argument_reloads"][0]["logical_stack_offset"] == 8
    assert callee["write_count"] == 1
    assert callee["writes"][0]["argument_channel"] == "stack+0x8"


def test_read_only_memory_operand_is_not_counted_as_write():
    rows = [
        (0x1200, "lea", "edx,[ebx+0x374]"),
        (0x1206, "call", "2200"),
        (0x120B, "ret", ""),
        (0x2200, "cmp", "DWORD PTR [edx],0x0"),
        (0x2204, "ret", ""),
    ]
    data = module().scan_rows(rows)
    callee = data["surface"]["direct_call_argument_boundaries"][0]["callee_scan"]
    assert callee["write_count"] == 0
    assert callee["read_count"] == 1


def test_mutated_materialized_address_is_killed_before_call():
    rows = [
        (0x1300, "lea", "eax,[esi+0x374]"),
        (0x1306, "add", "eax,0x4"),
        (0x1309, "mov", "ecx,eax"),
        (0x130B, "call", "2300"),
        (0x2300, "mov", "DWORD PTR [ecx],edx"),
        (0x2302, "ret", ""),
    ]
    data = module().scan_rows(rows)
    assert data["surface"]["direct_call_argument_boundary_count"] == 0
    assert data["surface"]["direct_callee_write_through_candidate_count"] == 0


def test_nested_call_terminates_callee_scan_before_later_write():
    rows = [
        (0x1400, "lea", "ecx,[esi+0x374]"),
        (0x1406, "call", "2400"),
        (0x140B, "ret", ""),
        (0x2400, "call", "2500"),
        (0x2405, "mov", "DWORD PTR [ecx],eax"),
        (0x2407, "ret", ""),
        (0x2500, "ret", ""),
    ]
    data = module().scan_rows(rows)
    callee = data["surface"]["direct_call_argument_boundaries"][0]["callee_scan"]
    assert callee["termination"] == "nested-call"
    assert callee["write_count"] == 0


def test_indirect_call_boundary_is_recorded_but_not_followed():
    rows = [
        (0x1500, "lea", "ecx,[esi+0x374]"),
        (0x1506, "call", "DWORD PTR [eax+0x4]"),
        (0x150A, "ret", ""),
    ]
    data = module().scan_rows(rows)
    surface = data["surface"]
    assert surface["direct_call_argument_boundary_count"] == 0
    assert surface["indirect_call_argument_boundary_count"] == 1
    assert surface["direct_callee_write_through_candidate_count"] == 0


def test_dynamic_esp_adjustment_fails_closed_inside_callee():
    rows = [
        (0x1600, "lea", "eax,[esi+0x374]"),
        (0x1606, "push", "eax"),
        (0x1607, "call", "2600"),
        (0x160C, "ret", ""),
        (0x2600, "sub", "esp,eax"),
        (0x2602, "mov", "eax,DWORD PTR [esp+0x4]"),
        (0x2606, "mov", "DWORD PTR [eax],ecx"),
        (0x2608, "ret", ""),
    ]
    data = module().scan_rows(rows)
    callee = data["surface"]["direct_call_argument_boundaries"][0]["callee_scan"]
    assert callee["termination"] == "unsupported-stack-adjustment"
    assert callee["unsupported_stack_adjustment"] is True
    assert callee["write_count"] == 0


def test_direct_target_parser_handles_objdump_forms():
    mod = module()
    assert mod.parse_direct_target("401000") == 0x401000
    assert mod.parse_direct_target("0x401000") == 0x401000
    assert mod.parse_direct_target("401000 <FUN_00401000>") == 0x401000
    assert mod.parse_direct_target("DWORD PTR [eax]") is None


def test_semantic_gates_remain_fail_closed():
    data = module().scan_rows([])
    adj = data["adjudication"]
    assert adj["materialized_plus_374_direct_call_argument_subset_scanned"] is True
    assert adj["materialized_plus_374_direct_callee_write_through_candidates_classified"] is False
    assert adj["materialized_helper_mediated_setter_surface_complete"] is False
    assert adj["helper_returned_materialized_address_surface_complete"] is False
    assert adj["global_helper_non_vtable_indirect_setter_surface_complete"] is False
    assert adj["external_or_unknown_origin_outer_alias_surface_complete"] is False
    assert adj["global_manager_root_origin_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
