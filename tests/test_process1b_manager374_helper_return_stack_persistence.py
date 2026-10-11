from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1b_manager374_helper_return_stack_persistence.py"


def module():
    spec = importlib.util.spec_from_file_location("p1b_helper_return_stack", TOOL)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def helper_rows(target: int, channel: str = "ecx"):
    return [
        (target, "lea", f"eax,[{channel}+0x374]"),
        (target + 6, "ret", ""),
    ]


def test_ebp_spill_reload_then_write_is_new_candidate():
    rows = [
        (0x1000, "call", "2000 <helper>"),
        (0x1005, "mov", "DWORD PTR [ebp-0x10],eax"),
        (0x1008, "mov", "edi,DWORD PTR [ebp-0x10]"),
        (0x100B, "mov", "DWORD PTR [edi],ecx"),
        (0x100D, "ret", ""),
        *helper_rows(0x2000),
    ]
    data = module().scan_rows(rows)
    surface = data["surface"]
    assert surface["qualified_helper_callsite_count"] == 1
    assert surface["stack_reload_derived_write_candidate_count"] == 1
    row = surface["stack_reload_derived_write_candidates"][0]
    assert row["site"] == "0x0000100b"
    assert row["reload_key"] == "ebp-0x10"
    scan = surface["post_return_stack_scans"][0]["post_stack_scan"]
    assert scan["spill_count"] == 1
    assert scan["reload_count"] == 1


def test_esp_normalization_preserves_logical_spill_slot():
    rows = [
        (0x1100, "call", "2100"),
        (0x1105, "sub", "esp,0x20"),
        (0x1108, "mov", "DWORD PTR [esp+0x10],eax"),
        (0x110C, "add", "esp,0x10"),
        (0x110F, "mov", "edi,DWORD PTR [esp]"),
        (0x1112, "mov", "DWORD PTR [edi],ecx"),
        (0x1114, "ret", ""),
        *helper_rows(0x2100),
    ]
    data = module().scan_rows(rows)
    row = data["surface"]["stack_reload_derived_write_candidates"][0]
    assert row["reload_key"] == "esp-0x10"
    assert row["address_register"] == "edi"


def test_push_pop_roundtrip_counts_as_stack_reload():
    rows = [
        (0x1200, "call", "2200"),
        (0x1205, "push", "eax"),
        (0x1206, "pop", "esi"),
        (0x1207, "mov", "DWORD PTR [esi],ecx"),
        (0x1209, "ret", ""),
        *helper_rows(0x2200, "edx"),
    ]
    data = module().scan_rows(rows)
    scan = data["surface"]["post_return_stack_scans"][0]["post_stack_scan"]
    assert scan["spill_count"] == 1
    assert scan["reload_count"] == 1
    assert scan["reloads"][0]["kind"] == "pop"
    assert data["surface"]["stack_reload_derived_write_candidate_count"] == 1


def test_stack_overwrite_invalidates_stale_alias():
    rows = [
        (0x1300, "call", "2300"),
        (0x1305, "mov", "DWORD PTR [ebp-0x8],eax"),
        (0x1308, "mov", "DWORD PTR [ebp-0x8],0x0"),
        (0x130F, "mov", "edi,DWORD PTR [ebp-0x8]"),
        (0x1312, "mov", "DWORD PTR [edi],ecx"),
        (0x1314, "ret", ""),
        *helper_rows(0x2300),
    ]
    data = module().scan_rows(rows)
    scan = data["surface"]["post_return_stack_scans"][0]["post_stack_scan"]
    assert scan["stack_overwrite_invalidation_count"] == 1
    assert scan["reload_count"] == 0
    assert data["surface"]["stack_reload_derived_write_candidate_count"] == 0


def test_direct_post_return_write_is_not_new_reload_candidate():
    rows = [
        (0x1400, "call", "2400"),
        (0x1405, "mov", "DWORD PTR [eax],ecx"),
        (0x1407, "ret", ""),
        *helper_rows(0x2400),
    ]
    data = module().scan_rows(rows)
    scan = data["surface"]["post_return_stack_scans"][0]["post_stack_scan"]
    assert scan["direct_no_reload_write_count"] == 1
    assert data["surface"]["stack_reload_derived_write_candidate_count"] == 0


def test_non_stack_persistence_is_recorded_but_not_followed():
    rows = [
        (0x1500, "call", "2500"),
        (0x1505, "mov", "DWORD PTR [edi+0x20],eax"),
        (0x1508, "ret", ""),
        *helper_rows(0x2500),
    ]
    data = module().scan_rows(rows)
    assert data["surface"]["non_stack_persistence_escape_count"] == 1
    escape = data["surface"]["non_stack_persistence_escapes"][0]
    assert escape["destination"] == "DWORD PTR [edi+0x20]"
    assert data["surface"]["stack_reload_derived_write_candidate_count"] == 0


def test_dynamic_esp_adjustment_stops_before_false_reload():
    rows = [
        (0x1600, "call", "2600"),
        (0x1605, "mov", "DWORD PTR [esp+0x8],eax"),
        (0x1609, "sub", "esp,ecx"),
        (0x160B, "mov", "edi,DWORD PTR [esp+0x8]"),
        (0x160F, "mov", "DWORD PTR [edi],ecx"),
        (0x1611, "ret", ""),
        *helper_rows(0x2600),
    ]
    data = module().scan_rows(rows)
    scan = data["surface"]["post_return_stack_scans"][0]["post_stack_scan"]
    assert scan["termination"] == "unsupported-stack-adjustment"
    assert data["surface"]["stack_reload_derived_write_candidate_count"] == 0


def test_call_boundary_stops_before_later_reload():
    rows = [
        (0x1700, "call", "2700"),
        (0x1705, "mov", "DWORD PTR [ebp-0x10],eax"),
        (0x1708, "call", "2800"),
        (0x170D, "mov", "edi,DWORD PTR [ebp-0x10]"),
        (0x1710, "mov", "DWORD PTR [edi],ecx"),
        (0x1712, "ret", ""),
        *helper_rows(0x2700),
        (0x2800, "ret", ""),
    ]
    data = module().scan_rows(rows)
    scan = data["surface"]["post_return_stack_scans"][0]["post_stack_scan"]
    assert scan["termination"] == "control-boundary"
    assert data["surface"]["stack_reload_derived_write_candidate_count"] == 0


def test_gpr_copy_before_spill_preserves_helper_provenance():
    rows = [
        (0x1800, "call", "2800"),
        (0x1805, "mov", "esi,eax"),
        (0x1807, "mov", "DWORD PTR [ebp-0x4],esi"),
        (0x180A, "mov", "edi,DWORD PTR [ebp-0x4]"),
        (0x180D, "mov", "DWORD PTR [edi],ecx"),
        (0x180F, "ret", ""),
        *helper_rows(0x2800, "edx"),
    ]
    data = module().scan_rows(rows)
    row = data["surface"]["stack_reload_derived_write_candidates"][0]
    assert row["helper_argument_channel"] == "edx"
    assert row["reload_key"] == "ebp-0x4"


def test_semantic_gates_remain_fail_closed():
    data = module().scan_rows([])
    adj = data["adjudication"]
    assert adj["helper_returned_target_stack_persistence_subset_scanned"] is True
    assert adj["helper_returned_target_stack_reload_write_candidates_classified"] is False
    assert adj["helper_returned_target_non_stack_persistence_complete"] is False
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
