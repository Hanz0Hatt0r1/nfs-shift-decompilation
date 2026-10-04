#!/usr/bin/env python3
"""Run the bounded outer-Vehicle -> VHF receiver proof from existing static data.

The runner composes three already fail-closed stages:

1. build ``SHIFT.OuterVehicleVHFRootRelationFrontier/1`` from the saved retail
   Ghidra evidence and symbolic BODY0 -> outer Vehicle relation;
2. open the existing Ghidra project read-only/noanalysis and export exactly
   ``FUN_007927c0`` as ``SHIFT.GhidraFunctionInstructions/2``;
3. build ``SHIFT.OuterVehicleTransformSinkReceiverProvenance/1`` and partition
   the remaining deterministic owner domains.

It never executes the original game and never equates an origin-expression group
with a VHF hierarchy owner.  Its purpose is to turn the current bind blocker into
a one-command finite owner worklist.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import analyze_outer_vehicle_transform_sink_receiver_provenance as _receivers
import build_outer_vehicle_vhf_root_relation_frontier as _frontier

FORMAT = "SHIFT.OuterVehicleVHFReceiverStaticProofBundle/1"
TARGET = "FUN_007927c0"
FRONTIER_FILE = "01_outer_vehicle_vhf_root_relation_frontier.json"
INSTRUCTION_FILE = "02_outer_vehicle_setter_instructions.jsonl"
RECEIVER_FILE = "03_outer_vehicle_sink_receiver_provenance.json"
BUNDLE_FILE = "outer_vehicle_vhf_receiver_static_proof_bundle.json"
RUNNER = _SCRIPT_DIR / "run_shift_function_instructions.sh"


def _write_json(path: Path, value: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _stage(
    state: str,
    *,
    path: Path | None = None,
    format_name: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {"state": state}
    if path is not None:
        result["path"] = str(path)
    if format_name is not None:
        result["format"] = format_name
    if reason is not None:
        result["reason"] = reason
    return result


def _decision(receiver_report: Mapping[str, Any]) -> dict[str, Any]:
    handoff = receiver_report.get("handoff")
    if not isinstance(handoff, Mapping):
        return {
            "class": "receiver-report-invalid",
            "next_action": "repair receiver proof artifact before owner analysis",
        }
    candidates = receiver_report.get("next_owner_candidates")
    if not isinstance(candidates, list):
        candidates = []
    normalized: list[dict[str, Any]] = []
    for row in candidates:
        if not isinstance(row, Mapping):
            continue
        normalized.append(
            {
                "callsite": row.get("callsite"),
                "callee": row.get("callee"),
                "callee_name": row.get("callee_name"),
                "ECX_origins_before_call": list(row.get("ECX_origins_before_call") or []),
                "ECX_origin_deterministic": row.get("ECX_origin_deterministic") is True,
                "same_ECX_origin_expression_set_as_HDVehicle_sink": (
                    row.get("same_ECX_origin_expression_set_as_HDVehicle_sink") is True
                ),
            }
        )

    ambiguous = [row for row in normalized if not row["ECX_origin_deterministic"]]
    if handoff.get("outer_setter_sink_ECX_provenance_unambiguous") is not True or ambiguous:
        return {
            "class": "resolve-receiver-ambiguity",
            "ambiguous_candidates": ambiguous,
            "next_action": (
                "resolve every reachable ECX producer at the listed callsites before "
                "callee owner or stack-transform analysis"
            ),
        }

    shared = [
        row for row in normalized
        if row["same_ECX_origin_expression_set_as_HDVehicle_sink"]
    ]
    distinct = [
        row for row in normalized
        if not row["same_ECX_origin_expression_set_as_HDVehicle_sink"]
    ]
    return {
        "class": "deterministic-owner-domain-partition",
        "shared_HDVehicle_origin_expression_candidates": shared,
        "distinct_origin_expression_candidates": distinct,
        "next_action": (
            "for each deterministic thiscall receiver domain, prove concrete callee "
            "writes/forwards and its owner-producing edge; join only a source-backed "
            "owner to the canonical BMW VHF hierarchy loader before tracing stack transforms"
        ),
    }


def _failure_bundle(
    *,
    failed_stage: str,
    inputs: Mapping[str, Any],
    stages: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "completed": False,
        "failed_stage": failed_stage,
        "inputs": dict(inputs),
        "stages": dict(stages),
        "handoff": {
            "outer_vehicle_VHF_frontier_ready": False,
            "outer_setter_sink_ECX_provenance_ready": False,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "scope": {
            "partial_artifacts_preserved": True,
            "failed_stage_promoted_to_frame_identity": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
    }


def run_outer_vehicle_vhf_receiver_static_proof(
    project_dir: Path,
    project_name: str,
    ghidra_export: Path,
    symbolic_relation: Path,
    output_dir: Path,
    *,
    program_name: str = _frontier.PROGRAM,
    ghidra_home: Path | None = None,
    timeout_seconds: int | None = None,
) -> dict[str, Any]:
    if not project_name.strip():
        raise ValueError("project_name must not be empty")
    if program_name != _frontier.PROGRAM:
        raise ValueError(f"program_name must be exact retail {_frontier.PROGRAM}")
    if timeout_seconds is not None and timeout_seconds < 1:
        raise ValueError("timeout_seconds must be >= 1")
    if not RUNNER.is_file():
        raise ValueError(f"targeted instruction runner missing: {RUNNER}")

    selected_home = ghidra_home
    if selected_home is None and os.environ.get("GHIDRA_HOME"):
        selected_home = Path(os.environ["GHIDRA_HOME"])
    if selected_home is None:
        raise ValueError("GHIDRA_HOME is required (environment or --ghidra-home)")

    output_dir.mkdir(parents=True, exist_ok=True)
    frontier_path = output_dir / FRONTIER_FILE
    instruction_path = output_dir / INSTRUCTION_FILE
    receiver_path = output_dir / RECEIVER_FILE
    bundle_path = output_dir / BUNDLE_FILE
    inputs = {
        "project_dir": str(project_dir),
        "project_name": project_name,
        "program_name": program_name,
        "ghidra_export": str(ghidra_export),
        "symbolic_relation": str(symbolic_relation),
    }
    stages: dict[str, Any] = {}

    try:
        frontier = _frontier.build_outer_vehicle_vhf_root_relation_frontier(
            ghidra_export,
            symbolic_relation,
        )
        _write_json(frontier_path, frontier)
        stages["frontier"] = _stage(
            "completed", path=frontier_path, format_name=_frontier.FORMAT
        )
    except Exception as exc:
        stages["frontier"] = _stage(
            "failed", path=frontier_path, reason=f"{type(exc).__name__}: {exc}"
        )
        bundle = _failure_bundle(
            failed_stage="frontier", inputs=inputs, stages=stages
        )
        _write_json(bundle_path, bundle)
        raise

    env = os.environ.copy()
    env["GHIDRA_HOME"] = str(selected_home)
    if timeout_seconds is not None:
        env["SHIFT_GHIDRA_HEADLESS_TIMEOUT_SECONDS"] = str(timeout_seconds)
    command = [
        "bash",
        str(RUNNER),
        str(project_dir),
        project_name,
        program_name,
        str(instruction_path),
        TARGET,
    ]
    try:
        subprocess.run(command, env=env, check=True)
        stages["instruction_export"] = _stage(
            "completed",
            path=instruction_path,
            format_name=_receivers.INSTRUCTION_FORMAT,
        )
    except Exception as exc:
        stages["instruction_export"] = _stage(
            "failed", path=instruction_path, reason=f"{type(exc).__name__}: {exc}"
        )
        bundle = _failure_bundle(
            failed_stage="instruction_export", inputs=inputs, stages=stages
        )
        _write_json(bundle_path, bundle)
        raise

    try:
        receiver_report = _receivers.analyze_outer_vehicle_transform_sink_receiver_provenance(
            frontier_path,
            instruction_path,
        )
        _write_json(receiver_path, receiver_report)
        stages["receiver_provenance"] = _stage(
            "completed", path=receiver_path, format_name=_receivers.FORMAT
        )
    except Exception as exc:
        stages["receiver_provenance"] = _stage(
            "failed", path=receiver_path, reason=f"{type(exc).__name__}: {exc}"
        )
        bundle = _failure_bundle(
            failed_stage="receiver_provenance", inputs=inputs, stages=stages
        )
        _write_json(bundle_path, bundle)
        raise

    decision = _decision(receiver_report)
    receiver_handoff = receiver_report.get("handoff")
    bundle = {
        "format": FORMAT,
        "version": 1,
        "completed": True,
        "inputs": inputs,
        "artifacts": {
            "frontier": str(frontier_path),
            "instruction_export": str(instruction_path),
            "receiver_provenance": str(receiver_path),
        },
        "stages": stages,
        "decision": decision,
        "handoff": {
            "outer_vehicle_VHF_frontier_ready": frontier.get("ready") is True,
            "outer_setter_sink_ECX_provenance_ready": (
                isinstance(receiver_handoff, Mapping)
                and receiver_handoff.get("outer_setter_sink_ECX_provenance_evaluated") is True
            ),
            "outer_setter_sink_ECX_provenance_unambiguous": (
                isinstance(receiver_handoff, Mapping)
                and receiver_handoff.get("outer_setter_sink_ECX_provenance_unambiguous") is True
            ),
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": False,
            "BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "scope": {
            "targeted_function_count": 1,
            "targeted_function": TARGET,
            "ghidra_project_opened_read_only": True,
            "ghidra_autoanalysis_requested": False,
            "receiver_partition_promoted_to_pointer_equality": False,
            "receiver_partition_promoted_to_frame_identity": False,
            "stack_transform_values_evaluated": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
    }
    _write_json(bundle_path, bundle)
    return bundle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("project_name")
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("symbolic_relation", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--program-name", default=_frontier.PROGRAM)
    parser.add_argument("--ghidra-home", type=Path)
    parser.add_argument("--timeout-seconds", type=int)
    args = parser.parse_args(argv)

    report = run_outer_vehicle_vhf_receiver_static_proof(
        args.project_dir,
        args.project_name,
        args.ghidra_export,
        args.symbolic_relation,
        args.output_dir,
        program_name=args.program_name,
        ghidra_home=args.ghidra_home,
        timeout_seconds=args.timeout_seconds,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
