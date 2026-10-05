#!/usr/bin/env python3
"""Run the bounded BMW SDF -> vehicle-assembly receiver proof in one command.

The runner opens an already-analyzed retail Ghidra project read-only through the
existing targeted instruction exporter, exports exactly FUN_0076df50 and
FUN_007615c0, then executes
``SHIFT.BMWSDFVehicleAssemblyReceiverProvenance/1``.  It does not execute the
original game, restart auto-analysis, infer coordinate-frame identity from a
receiver pointer, or emit a BODY0 bind matrix.
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

import analyze_bmw_sdf_vehicle_assembly_receiver_provenance as _receiver

FORMAT = "SHIFT.BMWSDFVehicleAssemblyReceiverProofBundle/1"
TARGETS = ("FUN_0076df50", "FUN_007615c0")
INSTRUCTION_FILE = "01_bmw_sdf_vehicle_assembly_instructions.jsonl"
PROOF_FILE = "02_bmw_sdf_vehicle_assembly_receiver_provenance.json"
BUNDLE_FILE = "bmw_sdf_vehicle_assembly_receiver_proof_bundle.json"
RUNNER = _SCRIPT_DIR / "run_shift_function_instructions.sh"


def _write_json(path: Path, value: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _stage(state: str, *, path: Path | None = None, format_name: str | None = None, reason: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"state": state}
    if path is not None:
        result["path"] = str(path)
    if format_name is not None:
        result["format"] = format_name
    if reason is not None:
        result["reason"] = reason
    return result


def _base_bundle(
    project_dir: Path,
    project_name: str,
    ghidra_export: Path,
    program_name: str,
    stages: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "inputs": {
            "project_dir": str(project_dir),
            "project_name": project_name,
            "program_name": program_name,
            "ghidra_export": str(ghidra_export),
        },
        "stages": dict(stages),
        "scope": {
            "targeted_function_count": 2,
            "targeted_functions": list(TARGETS),
            "ghidra_project_opened_read_only": True,
            "ghidra_autoanalysis_requested": False,
            "receiver_pointer_promoted_to_frame_identity": False,
            "BODY0_bind_matrix_emitted": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
    }


def run_bmw_sdf_vehicle_assembly_receiver_proof(
    project_dir: Path,
    project_name: str,
    ghidra_export: Path,
    output_dir: Path,
    *,
    program_name: str = _receiver.PROGRAM,
    ghidra_home: Path | None = None,
    timeout_seconds: int | None = None,
) -> dict[str, Any]:
    if not project_name.strip():
        raise ValueError("project_name must not be empty")
    if program_name != _receiver.PROGRAM:
        raise ValueError(f"program_name must be exact retail {_receiver.PROGRAM}")
    if timeout_seconds is not None and timeout_seconds < 1:
        raise ValueError("timeout_seconds must be >= 1")
    if not RUNNER.is_file():
        raise ValueError(f"targeted instruction runner missing: {RUNNER}")

    output_dir.mkdir(parents=True, exist_ok=True)
    instruction_path = output_dir / INSTRUCTION_FILE
    proof_path = output_dir / PROOF_FILE
    bundle_path = output_dir / BUNDLE_FILE
    stages: dict[str, Any] = {}

    env = os.environ.copy()
    selected_home = ghidra_home or (Path(env["GHIDRA_HOME"]) if env.get("GHIDRA_HOME") else None)
    if selected_home is None:
        raise ValueError("GHIDRA_HOME is required (environment or --ghidra-home)")
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
        *TARGETS,
    ]
    try:
        subprocess.run(command, env=env, check=True)
        stages["instruction_export"] = _stage(
            "completed", path=instruction_path, format_name=_receiver.INSTRUCTION_FORMAT
        )
    except Exception as exc:
        stages["instruction_export"] = _stage(
            "failed", path=instruction_path, reason=f"{type(exc).__name__}: {exc}"
        )
        bundle = _base_bundle(project_dir, project_name, ghidra_export, program_name, stages)
        bundle.update(
            {
                "completed": False,
                "failed_stage": "instruction_export",
                "handoff": {
                    "SDF_loader_owner_receiver_continuity_ready": False,
                    "SDF_model_to_VHF_vehicle_root_frame_relation_ready": False,
                    "BODY0_bind_frame_proof_ready": False,
                    "vehicle_world_transform_ready": False,
                },
            }
        )
        bundle["scope"]["partial_artifacts_preserved"] = True
        _write_json(bundle_path, bundle)
        raise

    try:
        report = _receiver.analyze_bmw_sdf_vehicle_assembly_receiver_provenance(
            ghidra_export, instruction_path
        )
        _write_json(proof_path, report)
        stages["receiver_provenance"] = _stage(
            "completed", path=proof_path, format_name=str(report.get("format") or "")
        )
    except Exception as exc:
        stages["receiver_provenance"] = _stage(
            "failed", path=proof_path, reason=f"{type(exc).__name__}: {exc}"
        )
        bundle = _base_bundle(project_dir, project_name, ghidra_export, program_name, stages)
        bundle.update(
            {
                "completed": False,
                "failed_stage": "receiver_provenance",
                "artifacts": {"instruction_export": str(instruction_path)},
                "handoff": {
                    "SDF_loader_owner_receiver_continuity_ready": False,
                    "SDF_model_to_VHF_vehicle_root_frame_relation_ready": False,
                    "BODY0_bind_frame_proof_ready": False,
                    "vehicle_world_transform_ready": False,
                },
            }
        )
        bundle["scope"]["validated_instruction_export_preserved"] = instruction_path.is_file()
        _write_json(bundle_path, bundle)
        raise

    ready = report.get("ready") is True
    handoff = report.get("handoff") if isinstance(report.get("handoff"), Mapping) else {}
    decision = {
        "class": (
            "high-detail-vehicle-to-sdf-receiver-continuity-ready"
            if ready
            else "receiver-continuity-blocked"
        ),
        "next_action": (
            "prove the source-backed HighDetailVehicle assembly owner frame -> canonical BMW VHF vehicle-root frame relation"
            if ready
            else "resolve only the reported ECX producer ambiguity/nonidentity at the frozen two callsites"
        ),
    }
    bundle = _base_bundle(project_dir, project_name, ghidra_export, program_name, stages)
    bundle.update(
        {
            "completed": True,
            "artifacts": {
                "instruction_export": str(instruction_path),
                "receiver_provenance": str(proof_path),
            },
            "decision": decision,
            "handoff": {
                "SDF_loader_owner_receiver_continuity_ready": (
                    handoff.get("SDF_loader_owner_receiver_continuity_ready") is True
                ),
                "SDF_loader_receiver_equals_HighDetailVehicle_Init_entry_ECX": (
                    handoff.get("SDF_loader_receiver_equals_HighDetailVehicle_Init_entry_ECX") is True
                ),
                "SDF_model_to_VHF_vehicle_root_frame_relation_ready": False,
                "BODY0_bind_frame_proof_ready": False,
                "vehicle_world_transform_ready": False,
            },
        }
    )
    _write_json(bundle_path, bundle)
    return bundle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("project_name")
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--program-name", default=_receiver.PROGRAM)
    parser.add_argument("--ghidra-home", type=Path)
    parser.add_argument("--timeout-seconds", type=int)
    args = parser.parse_args(argv)

    report = run_bmw_sdf_vehicle_assembly_receiver_proof(
        args.project_dir,
        args.project_name,
        args.ghidra_export,
        args.output_dir,
        program_name=args.program_name,
        ghidra_home=args.ghidra_home,
        timeout_seconds=args.timeout_seconds,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
