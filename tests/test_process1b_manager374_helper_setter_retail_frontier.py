from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "run_p1b_manager374_helper_setter_retail_frontier.py"


def module():
    spec = importlib.util.spec_from_file_location("p1b_helper_setter_frontier", TOOL)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def synthetic_rows():
    return [
        # Class 1: caller materializes target and passes it to direct helper.
        (0x1000, "lea", "eax,[esi+0x374]"),
        (0x1006, "mov", "ecx,eax"),
        (0x1008, "call", "3000 <setter>"),
        (0x100D, "ret", ""),
        # Class 2: helper returns ECX+0x374, immediate caller writes through EAX.
        (0x1100, "call", "4000 <returner>"),
        (0x1105, "mov", "DWORD PTR [eax],edx"),
        (0x1107, "ret", ""),
        # Class 3: helper returns EDX+0x374, caller spills/reloads before write.
        (0x1200, "call", "5000 <returner_stack>"),
        (0x1205, "mov", "DWORD PTR [ebp-0x8],eax"),
        (0x1208, "mov", "edi,DWORD PTR [ebp-0x8]"),
        (0x120B, "mov", "DWORD PTR [edi],ecx"),
        (0x120D, "ret", ""),
        (0x3000, "mov", "DWORD PTR [ecx],edx"),
        (0x3002, "ret", ""),
        (0x4000, "lea", "eax,[ecx+0x374]"),
        (0x4006, "ret", ""),
        (0x5000, "lea", "eax,[edx+0x374]"),
        (0x5006, "ret", ""),
    ]


def test_single_stream_composes_all_three_bounded_helper_setter_classes():
    data, results = module().run_rows(synthetic_rows())
    assert data["format"] == "SHIFT.P1B.Manager374HelperSetterRetailFrontier/1"
    assert data["authority"]["single_shared_instruction_stream"] is True
    assert data["authority"]["decoded_instruction_count"] == len(synthetic_rows())
    assert set(results) == {
        "direct_call_argument",
        "helper_return_immediate",
        "helper_return_stack",
    }
    surface = data["surface"]
    assert surface["write_candidate_count_by_probe"] == {
        "direct_call_argument": 1,
        "helper_return_immediate": 1,
        "helper_return_stack": 1,
    }
    assert surface["write_candidate_record_count"] == 3
    assert surface["resolved_write_candidate_union_empty"] is False
    assert {row["transport_class"] for row in surface["write_candidate_records"]} == {
        "materialized-target-direct-helper-argument",
        "helper-returned-target-immediate-gpr",
        "helper-returned-target-stack-reload",
    }
    assert surface["helper_return_counts"]["qualified_helper_return_target_count"] == 2
    assert surface["helper_return_counts"]["post_return_stack_scan_count"] == 2


def test_materialized_indirect_call_is_explicit_open_boundary():
    rows = [
        (0x2000, "lea", "ecx,[esi+0x374]"),
        (0x2006, "call", "DWORD PTR [eax+0x4]"),
        (0x200A, "ret", ""),
    ]
    data, _results = module().run_rows(rows)
    surface = data["surface"]
    assert surface["write_candidate_record_count"] == 0
    assert surface["open_boundary_count_by_class"]["materialized_target_indirect_call_argument_boundaries"] == 1
    assert surface["open_boundary_count"] == 1
    assert surface["bounded_frontier_empty"] is False


def test_non_stack_return_persistence_is_open_boundary_not_write_candidate():
    rows = [
        (0x2100, "call", "4100"),
        (0x2105, "mov", "DWORD PTR [edi+0x20],eax"),
        (0x2108, "ret", ""),
        (0x4100, "lea", "eax,[ecx+0x374]"),
        (0x4106, "ret", ""),
    ]
    data, _results = module().run_rows(rows)
    surface = data["surface"]
    assert surface["write_candidate_record_count"] == 0
    assert surface["open_boundary_count_by_class"]["helper_return_non_stack_persistence_escapes"] == 1
    assert surface["bounded_frontier_empty"] is False


def test_empty_synthetic_frontier_does_not_promote_semantic_gates():
    rows = [(0x2200, "ret", "")]
    data, _results = module().run_rows(rows)
    surface = data["surface"]
    assert surface["write_candidate_record_count"] == 0
    assert surface["open_boundary_count"] == 0
    assert surface["bounded_frontier_empty"] is True
    adj = data["adjudication"]
    assert adj["retail_helper_setter_probe_bundle_execution_complete"] is True
    assert adj["retail_helper_setter_candidate_frontier_composed"] is True
    assert adj["helper_setter_write_candidates_classified"] is False
    assert adj["materialized_helper_mediated_setter_surface_complete"] is False
    assert adj["helper_returned_materialized_address_surface_complete"] is False
    assert adj["helper_returned_target_non_stack_persistence_complete"] is False
    assert adj["global_helper_non_vtable_indirect_setter_surface_complete"] is False
    assert adj["global_manager_root_origin_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7


def test_compose_rejects_candidate_count_drift():
    mod = module()
    _data, results = mod.run_rows([(0x2300, "ret", "")])
    results["direct_call_argument"]["surface"]["direct_callee_write_through_candidate_count"] = 1
    with pytest.raises(ValueError, match="candidate count mismatch"):
        mod.compose(results)


def test_probe_registry_pins_expected_contracts():
    mod = module()
    assert mod.PROBES["direct_call_argument"]["format"] == "SHIFT.P1B.Manager374MaterializedDirectCallSetterProbe/1"
    assert mod.PROBES["helper_return_immediate"]["format"] == "SHIFT.P1B.Manager374HelperReturnedMaterializedTargetProbe/1"
    assert mod.PROBES["helper_return_stack"]["format"] == "SHIFT.P1B.Manager374HelperReturnedTargetStackPersistenceProbe/1"
    assert all(cfg["path"].is_file() for cfg in mod.PROBES.values())
