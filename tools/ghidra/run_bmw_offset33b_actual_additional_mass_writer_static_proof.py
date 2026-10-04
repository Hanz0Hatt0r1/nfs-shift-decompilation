#!/usr/bin/env python3
"""Run the actual BMW additional-mass writer frontier in one command."""
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

import analyze_bmw_offset33b_actual_additional_mass_writer_frontier as _writer

FORMAT = "SHIFT.BMWOffset33bActualAdditionalMassWriterStaticProofBundle/1"
INSTRUCTION_FILE = "01_actual_additional_mass_constructor_instructions.jsonl"
FRONTIER_FILE = "02_actual_additional_mass_writer_frontier.json"
BUNDLE_FILE = "bmw_offset33b_actual_additional_mass_writer_static_proof_bundle.json"
RUNNER = _SCRIPT_DIR / "run_shift_function_instructions.sh"
TARGET_NAMES = tuple(_writer.FUNCTIONS[address]["name"] for address in _writer.FUNCTIONS)


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _failure(*, failed_stage: str, inputs: Mapping[str, Any], stages: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "completed": False,
        "failed_stage": failed_stage,
        "inputs": dict(inputs),
        "stages": dict(stages),
        "handoff": {
            "actual_additional_mass_writer_frontier_ready": False,
            "actual_additional_mass_numeric_value_ready": False,
            "BMW_numeric_offset33b_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "scope": {
            "partial_artifacts_preserved": True,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
    }


def run_bmw_offset33b_actual_additional_mass_writer_static_proof(
    project_dir: Path,
    project_name: str,
    ghidra_export: Path,
    output_dir: Path,
    *,
    program_name: str = _writer.PROGRAM,
    ghidra_home: Path | None = None,
    timeout_seconds: int | None = None,
) -> dict[str, Any]:
    if not project_name.strip():
        raise ValueError("project_name must not be empty")
    if program_name != _writer.PROGRAM:
        raise ValueError(f"program_name must be exact retail {_writer.PROGRAM}")
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
    instruction_path = output_dir / INSTRUCTION_FILE
    frontier_path = output_dir / FRONTIER_FILE
    bundle_path = output_dir / BUNDLE_FILE
    inputs = {
        "project_dir": str(project_dir),
        "project_name": project_name,
        "program_name": program_name,
        "ghidra_export": str(ghidra_export),
    }
    stages: dict[str, Any] = {}

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
        *TARGET_NAMES,
    ]
    try:
        subprocess.run(command, env=env, check=True)
        stages["instruction_export"] = {
            "state": "completed",
            "path": str(instruction_path),
            "format": _writer.INSTRUCTION_FORMAT,
            "targets": list(TARGET_NAMES),
        }
    except Exception as exc:
        stages["instruction_export"] = {
            "state": "failed",
            "path": str(instruction_path),
            "reason": f"{type(exc).__name__}: {exc}",
        }
        bundle = _failure(failed_stage="instruction_export", inputs=inputs, stages=stages)
        _write_json(bundle_path, bundle)
        raise

    try:
        frontier = _writer.analyze_bmw_offset33b_actual_additional_mass_writer_frontier(
            ghidra_export,
            instruction_path,
        )
        _write_json(frontier_path, frontier)
        stages["writer_frontier"] = {
            "state": "completed",
            "path": str(frontier_path),
            "format": _writer.FORMAT,
        }
    except Exception as exc:
        stages["writer_frontier"] = {
            "state": "failed",
            "path": str(frontier_path),
            "reason": f"{type(exc).__name__}: {exc}",
        }
        bundle = _failure(failed_stage="writer_frontier", inputs=inputs, stages=stages)
        _write_json(bundle_path, bundle)
        raise

    handoff = frontier.get("handoff") if isinstance(frontier.get("handoff"), Mapping) else {}
    analysis = frontier.get("analysis") if isinstance(frontier.get("analysis"), Mapping) else {}
    direct_writers = list(analysis.get("direct_target_writers") or [])
    forward_worklist = list(analysis.get("same_receiver_forward_worklist") or [])
    if direct_writers:
        decision = {
            "class": "evaluate-direct-writer-value",
            "next_action": "evaluate only the reported direct writer dependency slice; do not assume zero",
            "writer_count": len(direct_writers),
        }
    elif frontier.get("ready") is True:
        decision = {
            "class": "export-same-receiver-forward-callees",
            "next_action": "target only the same-receiver forwarded callees emitted by the frontier",
            "candidate_count": len(forward_worklist),
        }
    else:
        decision = {
            "class": "resolve-constructor-receiver-proof",
            "next_action": "resolve the exact affine constructor receiver relation before writer expansion",
        }

    bundle = {
        "format": FORMAT,
        "version": 1,
        "completed": True,
        "status": decision["class"],
        "inputs": inputs,
        "artifacts": {
            "instruction_export": str(instruction_path),
            "writer_frontier": str(frontier_path),
        },
        "stages": stages,
        "decision": decision,
        "direct_target_writers": direct_writers,
        "same_receiver_forward_worklist": forward_worklist,
        "handoff": {
            "actual_additional_mass_writer_frontier_ready": bool(
                handoff.get("actual_additional_mass_writer_frontier_ready") is True
            ),
            "actual_additional_mass_direct_writer_found": bool(
                handoff.get("actual_additional_mass_direct_writer_found") is True
            ),
            "actual_additional_mass_numeric_value_ready": False,
            "BMW_numeric_offset33b_ready": False,
            "BODY0_to_outer_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "scope": {
            "targeted_Ghidra_export_count": 1,
            "targeted_function_count": len(TARGET_NAMES),
            "targeted_functions": list(TARGET_NAMES),
            "ghidra_project_opened_read_only": True,
            "ghidra_autoanalysis_requested": False,
            "manager_record_zero_assumption_reused": False,
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
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--program-name", default=_writer.PROGRAM)
    parser.add_argument("--ghidra-home", type=Path)
    parser.add_argument("--timeout-seconds", type=int)
    args = parser.parse_args(argv)
    report = run_bmw_offset33b_actual_additional_mass_writer_static_proof(
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
