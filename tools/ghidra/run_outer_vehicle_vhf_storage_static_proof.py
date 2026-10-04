#!/usr/bin/env python3
"""Run the bounded outer-Vehicle -> VHF storage proof in one fail-closed pass.

This composes the existing receiver runner with the transform-storage analyzer:

  Restart/spawn frontier
    -> exact FUN_007927c0 instruction export
    -> sink receiver provenance
    -> dynamically selected direct outer-receiver sinks
    -> exact targeted instruction export for only those sinks
    -> receiver-relative transform storage field spans

The runner never executes the original game, never requests Ghidra auto-analysis,
and never promotes receiver storage to VHF hierarchy identity or a bind matrix.
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

import analyze_outer_vehicle_transform_storage_domain as _storage
import run_outer_vehicle_vhf_receiver_static_proof as _receiver_runner

FORMAT = "SHIFT.OuterVehicleVHFStorageStaticProofBundle/1"
STORAGE_INSTRUCTION_FILE = "04_outer_vehicle_direct_storage_instructions.jsonl"
STORAGE_REPORT_FILE = "05_outer_vehicle_transform_storage_domain.json"
BUNDLE_FILE = "outer_vehicle_vhf_storage_static_proof_bundle.json"
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


def _selected_storage_targets(receiver_path: Path) -> list[str]:
    """Return the exact storage analyzer target set in deterministic order."""
    _report, rows = _storage._validate_receiver_report(receiver_path)
    selected = {
        str(row["callee"])
        for row in _storage._direct_outer_rows(rows)
    }
    return sorted(selected, key=lambda value: int(value, 0))


def _function_token(address: str) -> str:
    return f"FUN_{int(address, 0):08x}"


def _failure_bundle(
    *,
    failed_stage: str,
    inputs: Mapping[str, Any],
    artifacts: Mapping[str, Any],
    stages: Mapping[str, Any],
    selected_targets: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "completed": False,
        "failed_stage": failed_stage,
        "inputs": dict(inputs),
        "artifacts": dict(artifacts),
        "stages": dict(stages),
        "selected_storage_targets": list(selected_targets or []),
        "handoff": {
            "outer_setter_sink_ECX_provenance_ready": False,
            "outer_vehicle_transform_storage_domain_ready": False,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": False,
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


def _blocked_bundle(
    *,
    inputs: Mapping[str, Any],
    artifacts: Mapping[str, Any],
    stages: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "completed": True,
        "status": "blocked-by-receiver-routing",
        "inputs": dict(inputs),
        "artifacts": dict(artifacts),
        "stages": dict(stages),
        "selected_storage_targets": [],
        "decision": {
            "class": "no-direct-outer-receiver-storage-target",
            "next_action": (
                "resolve the receiver provenance until at least one deterministic "
                "__thiscall sink receives the outer setter entry ECX on all reachable paths"
            ),
        },
        "handoff": {
            "outer_setter_sink_ECX_provenance_ready": True,
            "outer_vehicle_transform_storage_domain_ready": False,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "scope": {
            "zero_target_Ghidra_export_attempted": False,
            "receiver_routing_promoted_to_storage_identity": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
    }


def run_outer_vehicle_vhf_storage_static_proof(
    project_dir: Path,
    project_name: str,
    ghidra_export: Path,
    symbolic_relation: Path,
    output_dir: Path,
    *,
    program_name: str = _receiver_runner._frontier.PROGRAM,
    ghidra_home: Path | None = None,
    timeout_seconds: int | None = None,
) -> dict[str, Any]:
    if not project_name.strip():
        raise ValueError("project_name must not be empty")
    if program_name != _receiver_runner._frontier.PROGRAM:
        raise ValueError(
            f"program_name must be exact retail {_receiver_runner._frontier.PROGRAM}"
        )
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
    receiver_bundle_path = output_dir / _receiver_runner.BUNDLE_FILE
    receiver_path = output_dir / _receiver_runner.RECEIVER_FILE
    storage_instruction_path = output_dir / STORAGE_INSTRUCTION_FILE
    storage_report_path = output_dir / STORAGE_REPORT_FILE
    bundle_path = output_dir / BUNDLE_FILE

    inputs = {
        "project_dir": str(project_dir),
        "project_name": project_name,
        "program_name": program_name,
        "ghidra_export": str(ghidra_export),
        "symbolic_relation": str(symbolic_relation),
    }
    artifacts: dict[str, Any] = {}
    stages: dict[str, Any] = {}

    try:
        receiver_bundle = _receiver_runner.run_outer_vehicle_vhf_receiver_static_proof(
            project_dir,
            project_name,
            ghidra_export,
            symbolic_relation,
            output_dir,
            program_name=program_name,
            ghidra_home=selected_home,
            timeout_seconds=timeout_seconds,
        )
        artifacts["receiver_bundle"] = str(receiver_bundle_path)
        artifacts["receiver_provenance"] = str(receiver_path)
        stages["receiver_static_proof"] = _stage(
            "completed",
            path=receiver_bundle_path,
            format_name=_receiver_runner.FORMAT,
        )
        if receiver_bundle.get("completed") is not True:
            raise ValueError("receiver static proof bundle is incomplete")
    except Exception as exc:
        stages["receiver_static_proof"] = _stage(
            "failed",
            path=receiver_bundle_path,
            reason=f"{type(exc).__name__}: {exc}",
        )
        bundle = _failure_bundle(
            failed_stage="receiver_static_proof",
            inputs=inputs,
            artifacts=artifacts,
            stages=stages,
        )
        _write_json(bundle_path, bundle)
        raise

    try:
        selected_targets = _selected_storage_targets(receiver_path)
        stages["storage_target_selection"] = _stage(
            "completed",
            path=receiver_path,
            format_name=_storage.RECEIVER_FORMAT,
        )
    except Exception as exc:
        stages["storage_target_selection"] = _stage(
            "failed",
            path=receiver_path,
            reason=f"{type(exc).__name__}: {exc}",
        )
        bundle = _failure_bundle(
            failed_stage="storage_target_selection",
            inputs=inputs,
            artifacts=artifacts,
            stages=stages,
        )
        _write_json(bundle_path, bundle)
        raise

    if not selected_targets:
        stages["storage_instruction_export"] = _stage(
            "blocked_by_upstream_gate",
            reason="receiver provenance selected zero direct outer-receiver sinks",
        )
        stages["storage_domain"] = _stage(
            "blocked_by_upstream_gate",
            reason="no selected storage instruction targets",
        )
        bundle = _blocked_bundle(
            inputs=inputs,
            artifacts=artifacts,
            stages=stages,
        )
        _write_json(bundle_path, bundle)
        return bundle

    env = os.environ.copy()
    env["GHIDRA_HOME"] = str(selected_home)
    if timeout_seconds is not None:
        env["SHIFT_GHIDRA_HEADLESS_TIMEOUT_SECONDS"] = str(timeout_seconds)
    target_tokens = [_function_token(address) for address in selected_targets]
    command = [
        "bash",
        str(RUNNER),
        str(project_dir),
        project_name,
        program_name,
        str(storage_instruction_path),
        *target_tokens,
    ]
    try:
        subprocess.run(command, env=env, check=True)
        artifacts["storage_instruction_export"] = str(storage_instruction_path)
        stages["storage_instruction_export"] = _stage(
            "completed",
            path=storage_instruction_path,
            format_name=_storage.INSTRUCTION_FORMAT,
        )
    except Exception as exc:
        stages["storage_instruction_export"] = _stage(
            "failed",
            path=storage_instruction_path,
            reason=f"{type(exc).__name__}: {exc}",
        )
        bundle = _failure_bundle(
            failed_stage="storage_instruction_export",
            inputs=inputs,
            artifacts=artifacts,
            stages=stages,
            selected_targets=selected_targets,
        )
        _write_json(bundle_path, bundle)
        raise

    try:
        storage_report = _storage.analyze_outer_vehicle_transform_storage_domain(
            ghidra_export,
            receiver_path,
            storage_instruction_path,
        )
        _write_json(storage_report_path, storage_report)
        artifacts["storage_domain"] = str(storage_report_path)
        stages["storage_domain"] = _stage(
            "completed",
            path=storage_report_path,
            format_name=_storage.FORMAT,
        )
    except Exception as exc:
        stages["storage_domain"] = _stage(
            "failed",
            path=storage_report_path,
            reason=f"{type(exc).__name__}: {exc}",
        )
        bundle = _failure_bundle(
            failed_stage="storage_domain",
            inputs=inputs,
            artifacts=artifacts,
            stages=stages,
            selected_targets=selected_targets,
        )
        _write_json(bundle_path, bundle)
        raise

    storage_handoff = storage_report.get("handoff")
    storage_ready = bool(
        isinstance(storage_handoff, Mapping)
        and storage_handoff.get("outer_vehicle_transform_storage_domain_ready") is True
    )
    field_spans = storage_report.get("exact_outer_receiver_field_spans")
    if not isinstance(field_spans, list):
        field_spans = []

    bundle = {
        "format": FORMAT,
        "version": 1,
        "completed": True,
        "status": "storage-domain-ready" if storage_ready else "storage-domain-frontier",
        "inputs": inputs,
        "artifacts": artifacts,
        "stages": stages,
        "selected_storage_targets": selected_targets,
        "selected_storage_function_tokens": target_tokens,
        "exact_outer_receiver_field_spans": field_spans,
        "decision": {
            "class": (
                "consumer-owner-join"
                if storage_ready
                else "resolve-storage-domain-frontier"
            ),
            "next_action": (
                "trace consumers of the exact outer receiver field spans into a concrete "
                "assembly/hierarchy owner and join that owner to the canonical BMW VHF "
                "vehicle-root loader"
                if storage_ready
                else "resolve storage-domain blockers without inventing a VHF owner"
            ),
        },
        "handoff": {
            "outer_setter_sink_ECX_provenance_ready": True,
            "outer_vehicle_transform_storage_domain_ready": storage_ready,
            "outer_vehicle_transform_field_spans_ready": bool(field_spans),
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": False,
            "BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "scope": {
            "storage_targets_selected_from_receiver_report": True,
            "hardcoded_storage_sink_selected": False,
            "ghidra_project_opened_read_only": True,
            "ghidra_autoanalysis_requested": False,
            "storage_fields_promoted_to_VHF_identity": False,
            "receiver_routing_promoted_to_pointer_equality": False,
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
    parser.add_argument("--program-name", default=_receiver_runner._frontier.PROGRAM)
    parser.add_argument("--ghidra-home", type=Path)
    parser.add_argument("--timeout-seconds", type=int)
    args = parser.parse_args(argv)

    report = run_outer_vehicle_vhf_storage_static_proof(
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
