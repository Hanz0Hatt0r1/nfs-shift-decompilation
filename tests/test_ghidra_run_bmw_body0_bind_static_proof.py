from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "run_bmw_body0_bind_static_proof.py"


def _module():
    spec = importlib.util.spec_from_file_location("run_bmw_body0_bind_static_proof", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _inputs(tmp_path: Path):
    ghidra = tmp_path / "ghidra"
    ghidra.mkdir()
    callers = tmp_path / "callers.jsonl"
    callers.write_text("{}\n", encoding="utf-8")
    pose = tmp_path / "pose.jsonl"
    pose.write_text("{}\n", encoding="utf-8")
    output = tmp_path / "out"
    return ghidra, callers, pose, output


def _patch_happy(monkeypatch, m, *, stack_required: bool = True, target_ready: bool = True):
    monkeypatch.setattr(
        m._frontier,
        "build_bmw_body0_bind_initialization_frontier",
        lambda root, max_depth=8: {
            "format": "SHIFT.BMWBody0BindInitializationFrontier/1",
            "targeted_proof_worklist": {"function_targets": ["0x007b7840"]},
            "blockers": [],
        },
    )
    monkeypatch.setattr(
        m._registers,
        "analyze_bmw_body0_bind_callsite_register_provenance",
        lambda frontier, instructions: {
            "format": "SHIFT.BMWBody0BindCallsiteRegisterProvenance/1",
            "handoff": {"pose_writer_callsite_register_provenance_ready": True},
            "blockers": [],
        },
    )
    monkeypatch.setattr(
        m._abi,
        "join_bmw_body0_bind_pose_writer_abi",
        lambda root, registers: {
            "format": "SHIFT.BMWBody0BindPoseWriterABI/1",
            "analysis": {
                "stack_value_worklist": (
                    [{"stack_offset": 4, "size": 4}] if stack_required else []
                )
            },
            "handoff": {"pose_writer_parameter_storage_binding_ready": True},
            "blockers": [],
        },
    )
    monkeypatch.setattr(
        m._stack,
        "analyze_bmw_body0_bind_stack_value_provenance",
        lambda abi, instructions: {
            "format": "SHIFT.BMWBody0BindStackValueProvenance/1",
            "handoff": {"pose_writer_stack_argument_values_ready": True},
            "blockers": [],
        },
    )
    monkeypatch.setattr(
        m._target_role,
        "analyze_bmw_body0_bind_pose_writer_target_role",
        lambda abi, instructions: {
            "format": "SHIFT.BMWBody0BindPoseWriterTargetRole/1",
            "handoff": {
                "pose_writer_BODY_target_parameter_ready": target_ready,
            },
            "blockers": (
                []
                if target_ready
                else [
                    {
                        "id": "pose-writer-complete-origin-basis-target-coverage-missing",
                        "evidence_state": "blocked",
                    }
                ]
            ),
        },
    )
    monkeypatch.setattr(
        m._values,
        "analyze_bmw_body0_bind_pose_writer_value_provenance",
        lambda target, instructions: {
            "format": "SHIFT.BMWBody0BindPoseWriterValueProvenance/1",
            "handoff": {
                "pose_writer_pose_store_value_dependency_frontier_ready": True,
                "BODY0_bind_origin_basis_values_ready": False,
                "BODY0_pointer_at_bind_callsite_ready": False,
                "BODY0_bind_frame_proof_ready": False,
            },
            "blockers": [
                {"id": "general-register-source-root-semantics-unresolved"},
                {"id": "BODY0-target-parameter-callsite-value-join-unproven"},
                {"id": "bind-origin-basis-concrete-values-unproven"},
            ],
        },
    )


def test_runs_complete_mechanical_chain_and_preserves_negative_bind_gate(
    tmp_path: Path, monkeypatch
) -> None:
    m = _module()
    _patch_happy(monkeypatch, m, stack_required=True, target_ready=True)
    ghidra, callers, pose, output = _inputs(tmp_path)

    bundle = m.run_bmw_body0_bind_static_proof(
        ghidra, callers, pose, output, max_depth=6
    )

    assert bundle["format"] == m.FORMAT
    assert bundle["completed"] is True
    assert bundle["inputs"]["max_depth"] == 6
    assert bundle["readiness"] == {
        "initialization_frontier_ready": True,
        "callsite_register_provenance_ready": True,
        "pose_writer_parameter_storage_binding_ready": True,
        "pose_writer_stack_argument_values_ready_or_not_required": True,
        "pose_writer_BODY_target_parameter_ready": True,
        "pose_store_value_dependency_frontier_ready": True,
        "BODY0_pointer_at_bind_callsite_ready": False,
        "BODY0_bind_origin_basis_values_ready": False,
        "BODY0_bind_frame_proof_ready": False,
    }
    assert bundle["handoff"]["first_remaining_semantic_join"].startswith(
        "target parameter callsite value -> BMW chassis BODY0"
    )
    assert "BODY0-target-parameter-callsite-value-join-unproven" in bundle["handoff"][
        "first_remaining_blocker_ids"
    ]
    assert bundle["handoff"]["phase704_706_retail_bind_admissible"] is False
    assert bundle["handoff"]["phase649_retail_vulkan_upload_ready"] is False

    expected = [
        "01_bmw_body0_bind_initialization_frontier.json",
        "02_bmw_body0_bind_callsite_register_provenance.json",
        "03_bmw_body0_bind_pose_writer_abi.json",
        "04_bmw_body0_bind_stack_value_provenance.json",
        "05_bmw_body0_bind_pose_writer_target_role.json",
        "06_bmw_body0_bind_pose_writer_value_provenance.json",
        m.BUNDLE_FILE,
    ]
    assert sorted(path.name for path in output.iterdir()) == sorted(expected)
    persisted = json.loads((output / m.BUNDLE_FILE).read_text(encoding="utf-8"))
    assert persisted == bundle


def test_skips_value_stage_when_target_role_is_not_positive(
    tmp_path: Path, monkeypatch
) -> None:
    m = _module()
    _patch_happy(monkeypatch, m, stack_required=False, target_ready=False)
    called = False

    def forbidden_value_stage(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("value stage must not run")

    monkeypatch.setattr(
        m._values,
        "analyze_bmw_body0_bind_pose_writer_value_provenance",
        forbidden_value_stage,
    )
    ghidra, callers, pose, output = _inputs(tmp_path)

    bundle = m.run_bmw_body0_bind_static_proof(ghidra, callers, pose, output)

    assert called is False
    assert bundle["stages"]["stack_value_provenance"]["state"] == "not_required"
    assert bundle["stages"]["pose_writer_value_provenance"]["state"] == "blocked_by_upstream_gate"
    assert bundle["readiness"]["pose_writer_BODY_target_parameter_ready"] is False
    assert bundle["readiness"]["pose_store_value_dependency_frontier_ready"] is False
    assert bundle["handoff"]["first_remaining_semantic_join"] == (
        "FUN_007b7840 persistent BODY target-parameter semantic role"
    )
    assert bundle["handoff"]["first_remaining_blocker_ids"] == [
        "pose-writer-complete-origin-basis-target-coverage-missing"
    ]
    assert not (output / "04_bmw_body0_bind_stack_value_provenance.json").exists()
    assert not (output / "06_bmw_body0_bind_pose_writer_value_provenance.json").exists()


def test_stage_failure_preserves_partial_artifacts_and_failure_bundle(
    tmp_path: Path, monkeypatch
) -> None:
    m = _module()
    _patch_happy(monkeypatch, m)

    def broken_register_stage(*args, **kwargs):
        raise ValueError("synthetic register ambiguity")

    monkeypatch.setattr(
        m._registers,
        "analyze_bmw_body0_bind_callsite_register_provenance",
        broken_register_stage,
    )
    ghidra, callers, pose, output = _inputs(tmp_path)

    with pytest.raises(ValueError, match="synthetic register ambiguity"):
        m.run_bmw_body0_bind_static_proof(ghidra, callers, pose, output)

    assert (output / "01_bmw_body0_bind_initialization_frontier.json").is_file()
    assert not (output / "02_bmw_body0_bind_callsite_register_provenance.json").exists()
    failure = json.loads((output / m.BUNDLE_FILE).read_text(encoding="utf-8"))
    assert failure["format"] == m.FORMAT
    assert failure["completed"] is False
    assert failure["failed_stage"] == "callsite_register_provenance"
    assert "synthetic register ambiguity" in failure["error"]
    assert failure["stages"]["initialization_frontier"]["state"] == "completed"
    assert failure["stages"]["callsite_register_provenance"]["state"] == "failed"
    assert failure["handoff"]["BODY0_bind_frame_proof_ready"] is False


def test_rejects_invalid_depth_before_creating_outputs(tmp_path: Path) -> None:
    m = _module()
    ghidra, callers, pose, output = _inputs(tmp_path)
    with pytest.raises(ValueError, match="max_depth must be >= 1"):
        m.run_bmw_body0_bind_static_proof(
            ghidra, callers, pose, output, max_depth=0
        )
    assert not output.exists()
