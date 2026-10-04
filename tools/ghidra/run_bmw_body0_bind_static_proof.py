#!/usr/bin/env python3
"""Run the current BMW BODY0 bind static-proof chain in one fail-closed pass.

The runner composes only already-audited Process 1 stages:

  initialization frontier
    -> callsite register provenance
    -> physical pose-writer ABI
    -> stack value provenance (when required)
    -> BODY pose target-parameter role
    -> pose STORE value-dependency frontier (only after target role is positive)

It never manufactures a positive SHIFT.BMWBody0BindFrameProof/1.  The bundle is
coordination infrastructure: it preserves every intermediate JSON report and
states the first remaining semantic join for the playable Linux slice.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import analyze_bmw_body0_bind_callsite_register_provenance as _registers
import analyze_bmw_body0_bind_pose_writer_target_role as _target_role
import analyze_bmw_body0_bind_pose_writer_value_provenance as _values
import analyze_bmw_body0_bind_stack_value_provenance as _stack
import build_bmw_body0_bind_initialization_frontier as _frontier
import join_bmw_body0_bind_pose_writer_abi as _abi

FORMAT = "SHIFT.BMWBody0BindStaticProofBundle/1"

_STAGE_FILES = {
    "initialization_frontier": "01_bmw_body0_bind_initialization_frontier.json",
    "callsite_register_provenance": "02_bmw_body0_bind_callsite_register_provenance.json",
    "pose_writer_abi": "03_bmw_body0_bind_pose_writer_abi.json",
    "stack_value_provenance": "04_bmw_body0_bind_stack_value_provenance.json",
    "pose_writer_target_role": "05_bmw_body0_bind_pose_writer_target_role.json",
    "pose_writer_value_provenance": "06_bmw_body0_bind_pose_writer_value_provenance.json",
}
BUNDLE_FILE = "bmw_body0_bind_static_proof_bundle.json"


def _write_json(path: Path, value: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _stage_record(
    *,
    state: str,
    path: Path | None = None,
    report: dict[str, Any] | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {"state": state}
    if path is not None:
        result["path"] = str(path)
    if report is not None:
        result["format"] = report.get("format")
    if reason is not None:
        result["reason"] = reason
    return result


def _blocker_ids(report: dict[str, Any]) -> list[str]:
    blockers = report.get("blockers")
    if not isinstance(blockers, list):
        return []
    result: list[str] = []
    for row in blockers:
        if not isinstance(row, dict):
            continue
        identifier = row.get("id")
        if isinstance(identifier, str) and identifier not in result:
            result.append(identifier)
    return result


def _failure_bundle(
    *,
    ghidra_export: Path,
    caller_instruction_export: Path,
    pose_writer_instruction_export: Path,
    output_dir: Path,
    stages: dict[str, Any],
    failed_stage: str,
    error: Exception,
) -> dict[str, Any]:
    return {
        "format": FORMAT,
        "completed": False,
        "failed_stage": failed_stage,
        "error": f"{type(error).__name__}: {error}",
        "inputs": {
            "ghidra_export": str(ghidra_export),
            "caller_instruction_export": str(caller_instruction_export),
            "pose_writer_instruction_export": str(pose_writer_instruction_export),
        },
        "output_dir": str(output_dir),
        "stages": stages,
        "handoff": {
            "BODY0_bind_frame_proof_ready": False,
            "retail_vehicle_world_transform_ready": False,
        },
        "scope": {
            "partial_success_artifacts_preserved": True,
            "failed_stage_promoted_to_semantic_proof": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
    }


def run_bmw_body0_bind_static_proof(
    ghidra_export: Path,
    caller_instruction_export: Path,
    pose_writer_instruction_export: Path,
    output_dir: Path,
    *,
    max_depth: int = 8,
) -> dict[str, Any]:
    if max_depth < 1:
        raise ValueError("max_depth must be >= 1")
    output_dir.mkdir(parents=True, exist_ok=True)
    stages: dict[str, Any] = {}
    reports: dict[str, dict[str, Any]] = {}

    def execute(
        name: str,
        callback: Callable[[], dict[str, Any]],
    ) -> tuple[dict[str, Any], Path]:
        path = output_dir / _STAGE_FILES[name]
        try:
            report = callback()
            if not isinstance(report, dict) or not isinstance(report.get("format"), str):
                raise ValueError(f"{name}: stage returned malformed report")
            _write_json(path, report)
            reports[name] = report
            stages[name] = _stage_record(state="completed", path=path, report=report)
            return report, path
        except Exception as exc:
            stages[name] = _stage_record(
                state="failed",
                path=path,
                reason=f"{type(exc).__name__}: {exc}",
            )
            bundle = _failure_bundle(
                ghidra_export=ghidra_export,
                caller_instruction_export=caller_instruction_export,
                pose_writer_instruction_export=pose_writer_instruction_export,
                output_dir=output_dir,
                stages=stages,
                failed_stage=name,
                error=exc,
            )
            _write_json(output_dir / BUNDLE_FILE, bundle)
            raise

    frontier, frontier_path = execute(
        "initialization_frontier",
        lambda: _frontier.build_bmw_body0_bind_initialization_frontier(
            ghidra_export,
            max_depth=max_depth,
        ),
    )

    register_report, register_path = execute(
        "callsite_register_provenance",
        lambda: _registers.analyze_bmw_body0_bind_callsite_register_provenance(
            frontier_path,
            caller_instruction_export,
        ),
    )

    abi_report, abi_path = execute(
        "pose_writer_abi",
        lambda: _abi.join_bmw_body0_bind_pose_writer_abi(
            ghidra_export,
            register_path,
        ),
    )

    abi_analysis = abi_report.get("analysis")
    if not isinstance(abi_analysis, dict):
        raise ValueError("pose_writer_abi: analysis missing after completed stage")
    stack_worklist = abi_analysis.get("stack_value_worklist")
    if not isinstance(stack_worklist, list):
        raise ValueError("pose_writer_abi: stack_value_worklist missing")

    stack_report: dict[str, Any] | None = None
    stack_path: Path | None = None
    if stack_worklist:
        stack_report, stack_path = execute(
            "stack_value_provenance",
            lambda: _stack.analyze_bmw_body0_bind_stack_value_provenance(
                abi_path,
                caller_instruction_export,
            ),
        )
    else:
        stages["stack_value_provenance"] = _stage_record(
            state="not_required",
            reason="pose-writer ABI contains no stack value worklist",
        )

    target_report, target_path = execute(
        "pose_writer_target_role",
        lambda: _target_role.analyze_bmw_body0_bind_pose_writer_target_role(
            abi_path,
            pose_writer_instruction_export,
        ),
    )

    target_handoff = target_report.get("handoff")
    if not isinstance(target_handoff, dict):
        raise ValueError("pose_writer_target_role: handoff missing after completed stage")
    target_ready = target_handoff.get("pose_writer_BODY_target_parameter_ready") is True

    value_report: dict[str, Any] | None = None
    value_path: Path | None = None
    if target_ready:
        value_report, value_path = execute(
            "pose_writer_value_provenance",
            lambda: _values.analyze_bmw_body0_bind_pose_writer_value_provenance(
                target_path,
                pose_writer_instruction_export,
            ),
        )
    else:
        stages["pose_writer_value_provenance"] = _stage_record(
            state="blocked_by_upstream_gate",
            reason="pose_writer_BODY_target_parameter_ready is false",
        )

    value_frontier_ready = False
    if value_report is not None:
        handoff = value_report.get("handoff")
        if isinstance(handoff, dict):
            value_frontier_ready = (
                handoff.get("pose_writer_pose_store_value_dependency_frontier_ready") is True
            )

    stack_values_ready = True
    if stack_report is not None:
        stack_handoff = stack_report.get("handoff")
        stack_values_ready = bool(
            isinstance(stack_handoff, dict)
            and stack_handoff.get("pose_writer_stack_argument_values_ready") is True
        )

    if not target_ready:
        first_join = "FUN_007b7840 persistent BODY target-parameter semantic role"
        first_blockers = _blocker_ids(target_report)
    elif not value_frontier_ready:
        first_join = "FUN_007b7840 origin/basis STORE value extraction"
        first_blockers = _blocker_ids(value_report or {})
    else:
        first_join = (
            "target parameter callsite value -> BMW chassis BODY0 AND pose STORE terminal roots -> concrete bind values"
        )
        first_blockers = _blocker_ids(value_report or {})

    bundle = {
        "format": FORMAT,
        "completed": True,
        "inputs": {
            "ghidra_export": str(ghidra_export),
            "caller_instruction_export": str(caller_instruction_export),
            "pose_writer_instruction_export": str(pose_writer_instruction_export),
            "max_depth": max_depth,
        },
        "output_dir": str(output_dir),
        "stages": stages,
        "stage_formats": {
            name: report.get("format")
            for name, report in reports.items()
        },
        "readiness": {
            "initialization_frontier_ready": bool(
                frontier.get("targeted_proof_worklist", {}).get("function_targets")
            ),
            "callsite_register_provenance_ready": bool(
                register_report.get("handoff", {}).get(
                    "pose_writer_callsite_register_provenance_ready"
                )
            ),
            "pose_writer_parameter_storage_binding_ready": bool(
                abi_report.get("handoff", {}).get(
                    "pose_writer_parameter_storage_binding_ready"
                )
            ),
            "pose_writer_stack_argument_values_ready_or_not_required": stack_values_ready,
            "pose_writer_BODY_target_parameter_ready": target_ready,
            "pose_store_value_dependency_frontier_ready": value_frontier_ready,
            "BODY0_pointer_at_bind_callsite_ready": False,
            "BODY0_bind_origin_basis_values_ready": False,
            "BODY0_bind_frame_proof_ready": False,
        },
        "handoff": {
            "first_remaining_semantic_join": first_join,
            "first_remaining_blocker_ids": first_blockers,
            "BODY0_bind_frame_proof_ready": False,
            "phase704_706_retail_bind_admissible": False,
            "retail_vehicle_world_transform_ready": False,
            "phase649_retail_vulkan_upload_ready": False,
        },
        "scope": {
            "intermediate_reports_preserved": True,
            "stack_stage_skipped_only_when_not_required_by_ABI": True,
            "value_stage_requires_positive_target_role": True,
            "dependency_frontier_promoted_to_concrete_values": False,
            "pose_writer_candidate_promoted_to_bind_initializer": False,
            "BODY0_pointer_identity_proven": False,
            "BODY0_bind_matrix_proven": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
    }
    _write_json(output_dir / BUNDLE_FILE, bundle)
    return bundle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("caller_instruction_export", type=Path)
    parser.add_argument("pose_writer_instruction_export", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--max-depth", type=int, default=8)
    args = parser.parse_args()

    bundle = run_bmw_body0_bind_static_proof(
        args.ghidra_export,
        args.caller_instruction_export,
        args.pose_writer_instruction_export,
        args.output_dir,
        max_depth=args.max_depth,
    )
    print(f"format: {bundle['format']}")
    print(f"completed: {str(bundle['completed']).lower()}")
    print(
        "target parameter ready: "
        f"{str(bundle['readiness']['pose_writer_BODY_target_parameter_ready']).lower()}"
    )
    print(
        "value dependency frontier ready: "
        f"{str(bundle['readiness']['pose_store_value_dependency_frontier_ready']).lower()}"
    )
    print(f"next join: {bundle['handoff']['first_remaining_semantic_join']}")
    print(f"bundle: {args.output_dir / BUNDLE_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
