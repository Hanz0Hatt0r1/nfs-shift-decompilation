import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/ghidra/join_bmw_body0_bind_pose_writer_abi.py"
SPEC = importlib.util.spec_from_file_location("body0_bind_pose_writer_abi", TOOL)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _write_functions(root: Path, parameters, *, address="0x007b7840") -> None:
    root.mkdir(parents=True, exist_ok=True)
    row = {
        "address": address,
        "name": "FUN_007b7840",
        "namespace": "Global",
        "size": 512,
        "thunk": False,
        "external": False,
        "calling_convention": "__thiscall",
        "signature": "undefined FUN_007b7840(...)",
        "parameters": parameters,
        "mnemonic_sha256": "a" * 64,
    }
    (root / "functions.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")


def _physical_report(
    path: Path,
    *,
    ecx_origins=("entry:ECX",),
    edx_origins=("memory:dword ptr [eax + 0x10]",),
    all_analyzed=True,
) -> None:
    def register(origins):
        origins = list(origins)
        unknown = any(
            value.startswith(("unknown:", "ambiguous:", "derived:", "value:"))
            for value in origins
        )
        return {
            "origins": origins,
            "origin_count": len(origins),
            "exact_single_origin": len(origins) == 1,
            "contains_unknown_or_derived": unknown,
            "contains_memory_origin": any(value.startswith("memory:") for value in origins),
            "contains_entry_origin": any(value.startswith("entry:") for value in origins),
        }

    payload = {
        "format": "SHIFT.BMWBody0BindCallsiteRegisterProvenance/1",
        "target": {
            "pose_writer_candidate": "0x007b7840",
            "direct_caller_count": 1,
            "required_caller_functions": ["0x007b4000"],
        },
        "analysis": {
            "analyzed_callsite_count": 1,
            "all_frontier_callsites_analyzed": all_analyzed,
            "tracked_registers": ["EAX", "EBX", "ECX", "EDX", "ESI", "EDI", "EBP", "ESP"],
            "callsites": [
                {
                    "caller": "0x007b4000",
                    "caller_name": "FUN_007b4000",
                    "callsite": "0x007b4050",
                    "target": "0x007b7840",
                    "candidate_class": "BODY-builder-reachable",
                    "registers_before_call": {
                        "ECX": register(ecx_origins),
                        "EDX": register(edx_origins),
                    },
                    "physical_register_provenance_ready": True,
                }
            ],
        },
        "handoff": {
            "pose_writer_callsite_register_provenance_ready": True,
            "pose_writer_ABI_semantics_ready": False,
            "BODY0_pointer_at_bind_callsite_ready": False,
            "BODY0_bind_origin_basis_values_ready": False,
            "BODY0_bind_frame_proof_ready": False,
        },
        "scope": {
            "register_position_used_as_parameter_semantics": False,
            "stack_argument_semantics_inferred": False,
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_storage_join_narrows_exact_stack_worklist_without_semantic_promotion(tmp_path):
    export = tmp_path / "ghidra"
    _write_functions(
        export,
        [
            {"name": "this", "type": "undefined4 *", "storage": "ECX:4 (auto)"},
            {"name": "param_1", "type": "undefined4", "storage": "Stack[0x4]:4"},
            {"name": "param_2", "type": "undefined4", "storage": "Stack[0x8]:4"},
        ],
    )
    physical = tmp_path / "physical.json"
    _physical_report(physical)

    report = MODULE.join_bmw_body0_bind_pose_writer_abi(export, physical)

    assert report["format"] == "SHIFT.BMWBody0BindPoseWriterABI/1"
    assert report["pose_writer"]["calling_convention"] == "__thiscall"
    assert report["pose_writer"]["parameter_count"] == 3
    assert report["pose_writer"]["register_parameter_count"] == 1
    assert report["pose_writer"]["stack_parameter_count"] == 2
    assert [row["storage"] for row in report["analysis"]["stack_value_worklist"]] == [
        "Stack[0x4]:4",
        "Stack[0x8]:4",
    ]
    assert report["handoff"]["pose_writer_parameter_storage_binding_ready"] is True
    assert report["handoff"]["pose_writer_register_argument_provenance_ready"] is True
    assert report["handoff"]["pose_writer_stack_argument_locations_ready"] is True
    assert report["handoff"]["pose_writer_stack_argument_values_ready"] is False
    assert report["handoff"]["pose_writer_ABI_semantic_roles_ready"] is False
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False
    assert report["scope"]["parameter_ordinal_used_as_semantic_role"] is False
    assert report["scope"]["reported_parameter_name_trusted_as_semantics"] is False
    blocker_ids = {row["id"] for row in report["blockers"]}
    assert "pose-writer-stack-argument-value-provenance-unproven" in blocker_ids
    assert "pose-writer-parameter-semantic-roles-unproven" in blocker_ids


def test_register_parameters_attach_all_path_origins_by_physical_storage(tmp_path):
    export = tmp_path / "ghidra"
    _write_functions(
        export,
        [
            {"name": "this", "type": "undefined4 *", "storage": "ECX:4 (auto)"},
            {"name": "param_1", "type": "undefined4", "storage": "EDX:4"},
        ],
    )
    physical = tmp_path / "physical.json"
    _physical_report(physical)

    report = MODULE.join_bmw_body0_bind_pose_writer_abi(export, physical)
    bindings = report["analysis"]["callsites"][0]["parameter_bindings"]

    assert bindings[0]["storage"] == "ECX:4 (auto)"
    assert bindings[0]["tracked_parent_register"] == "ECX"
    assert bindings[0]["origins"] == ["entry:ECX"]
    assert bindings[0]["value_provenance_ready"] is True
    assert bindings[1]["storage"] == "EDX:4"
    assert bindings[1]["origins"] == ["memory:dword ptr [eax + 0x10]"]
    assert bindings[1]["semantic_role"] is None
    assert report["analysis"]["stack_value_worklist"] == []
    assert report["handoff"]["pose_writer_stack_argument_values_ready"] is True
    assert report["handoff"]["pose_writer_ABI_semantic_roles_ready"] is False


def test_ambiguous_register_origin_keeps_register_handoff_blocked(tmp_path):
    export = tmp_path / "ghidra"
    _write_functions(
        export,
        [{"name": "this", "type": "undefined4 *", "storage": "ECX:4 (auto)"}],
    )
    physical = tmp_path / "physical.json"
    _physical_report(physical, ecx_origins=("entry:ECX", "unknown:ECX@0x007b4040:call-clobber"))

    report = MODULE.join_bmw_body0_bind_pose_writer_abi(export, physical)

    assert report["handoff"]["pose_writer_register_argument_provenance_ready"] is False
    assert report["analysis"]["callsites"][0]["parameter_bindings"][0][
        "value_provenance_ready"
    ] is False
    assert "pose-writer-register-argument-value-provenance-ambiguous" in {
        row["id"] for row in report["blockers"]
    }


def test_missing_pose_writer_function_row_fails_closed(tmp_path):
    export = tmp_path / "ghidra"
    _write_functions(
        export,
        [{"name": "this", "type": "undefined4 *", "storage": "ECX:4 (auto)"}],
        address="0x007b7830",
    )
    physical = tmp_path / "physical.json"
    _physical_report(physical)

    with pytest.raises(ValueError, match="exactly one 0x007b7840 row"):
        MODULE.join_bmw_body0_bind_pose_writer_abi(export, physical)


def test_composite_or_unknown_parameter_storage_fails_closed(tmp_path):
    export = tmp_path / "ghidra"
    _write_functions(
        export,
        [{"name": "param_1", "type": "undefined8", "storage": "EAX:4,EDX:4"}],
    )
    physical = tmp_path / "physical.json"
    _physical_report(physical)

    with pytest.raises(ValueError, match="unsupported/composite storage"):
        MODULE.join_bmw_body0_bind_pose_writer_abi(export, physical)


def test_incomplete_physical_frontier_coverage_fails_closed(tmp_path):
    export = tmp_path / "ghidra"
    _write_functions(
        export,
        [{"name": "this", "type": "undefined4 *", "storage": "ECX:4 (auto)"}],
    )
    physical = tmp_path / "physical.json"
    _physical_report(physical, all_analyzed=False)

    with pytest.raises(ValueError, match="does not cover every frontier callsite"):
        MODULE.join_bmw_body0_bind_pose_writer_abi(export, physical)
