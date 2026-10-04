#!/usr/bin/env python3
"""Run the bounded BMW offset33b static proof from an existing Ghidra project.

This runner removes manual coordination between the targeted instruction export
and ``SHIFT.BMWOffset33bStoreProvenance/1``. It opens the already-analyzed retail
Ghidra project read-only, exports only ``FUN_0076b280``, validates that export via
the existing shell runner, then executes the offset33b store/value-root analyzer.

The original game is never executed. A completed runner does not imply the three
BMW doubles are numerically known: the analyzer may intentionally stop at a
constant/memory/register/helper-return frontier.
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

import analyze_bmw_offset33b_store_provenance as _stores

FORMAT = "SHIFT.BMWOffset33bStaticProofBundle/1"
TARGET = "FUN_0076b280"
INSTRUCTION_FILE = "01_fun_0076b280_instructions.jsonl"
PROVENANCE_FILE = "02_bmw_offset33b_store_provenance.json"
BUNDLE_FILE = "bmw_offset33b_static_proof_bundle.json"
RUNNER = _SCRIPT_DIR / "run_shift_function_instructions.sh"
DEFAULT_RELATION = _stores.DEFAULT_RELATION


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


def _decision(report: Mapping[str, Any]) -> dict[str, Any]:
    analysis = report.get("analysis")
    candidates = analysis.get("store_candidates") if isinstance(analysis, Mapping) else None
    if report.get("ready") is not True or not isinstance(candidates, list):
        return {
            "class": "store-frontier-incomplete",
            "next_action": "resolve offset33b STORE target/coverage blockers before value evaluation",
        }

    kinds = set()
    direct_calls = set()
    for row in candidates:
        if not isinstance(row, Mapping):
            continue
        kinds.update(str(value) for value in row.get("terminal_root_kinds") or [])
        for call in row.get("recent_direct_calls_before_store") or []:
            if not isinstance(call, Mapping):
                continue
            for target in call.get("direct_targets") or []:
                direct_calls.add(str(target))

    if kinds and kinds <= {"constant", "address-space-selector"}:
        return {
            "class": "constant-root-evaluation",
            "next_action": "evaluate the exact supported p-code slices into three IEEE-754 doubles; do not reinterpret raw roots directly",
            "terminal_root_kinds": sorted(kinds),
        }
    if "external-or-memory-varnode" in kinds:
        return {
            "class": "resource-or-init-memory-join",
            "next_action": "join the exact memory roots to resource-driven BMW SDF/init fields and evaluate only that finite producer chain",
            "terminal_root_kinds": sorted(kinds),
        }
    if kinds & {"floating-register", "general-register", "other-register", "unresolved-unique"}:
        return {
            "class": "register-or-helper-return-provenance",
            "next_action": "trace only unresolved register/unique roots and the nearest exact helper return boundaries",
            "terminal_root_kinds": sorted(kinds),
            "nearby_direct_targets": sorted(direct_calls),
        }
    return {
        "class": "finite-value-root-frontier",
        "next_action": "inspect the reported exact value roots; runtime three-double witness remains fallback only",
        "terminal_root_kinds": sorted(kinds),
    }


def run_bmw_offset33b_static_proof(
    project_dir: Path,
    project_name: str,
    ghidra_export: Path,
    output_dir: Path,
    *,
    program_name: str = _stores.PROGRAM,
    relation_path: Path = DEFAULT_RELATION,
    ghidra_home: Path | None = None,
    timeout_seconds: int | None = None,
) -> dict[str, Any]:
    if not project_name.strip():
        raise ValueError("project_name must not be empty")
    if program_name != _stores.PROGRAM:
        raise ValueError(f"program_name must be exact retail {_stores.PROGRAM}")
    if timeout_seconds is not None and timeout_seconds < 1:
        raise ValueError("timeout_seconds must be >= 1")
    if not RUNNER.is_file():
        raise ValueError(f"targeted instruction runner missing: {RUNNER}")

    output_dir.mkdir(parents=True, exist_ok=True)
    instruction_path = output_dir / INSTRUCTION_FILE
    provenance_path = output_dir / PROVENANCE_FILE
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
        TARGET,
    ]
    try:
        subprocess.run(command, env=env, check=True)
        stages["instruction_export"] = _stage(
            "completed",
            path=instruction_path,
            format_name=_stores.INSTRUCTION_FORMAT,
        )
    except Exception as exc:
        stages["instruction_export"] = _stage(
            "failed",
            path=instruction_path,
            reason=f"{type(exc).__name__}: {exc}",
        )
        bundle = {
            "format": FORMAT,
            "version": 1,
            "completed": False,
            "failed_stage": "instruction_export",
            "inputs": {
                "project_dir": str(project_dir),
                "project_name": project_name,
                "program_name": program_name,
                "ghidra_export": str(ghidra_export),
                "relation": str(relation_path),
            },
            "stages": stages,
            "handoff": {
                "offset33b_store_provenance_ready": False,
                "BMW_numeric_offset33b_ready": False,
                "vehicle_world_transform_ready": False,
            },
            "scope": {
                "partial_artifacts_preserved": True,
                "original_game_executed": False,
                "new_runtime_capture_required": False,
            },
        }
        _write_json(bundle_path, bundle)
        raise

    try:
        report = _stores.analyze_bmw_offset33b_store_provenance(
            ghidra_export,
            instruction_path,
            relation_path,
        )
        _write_json(provenance_path, report)
        stages["store_provenance"] = _stage(
            "completed",
            path=provenance_path,
            format_name=str(report.get("format") or ""),
        )
    except Exception as exc:
        stages["store_provenance"] = _stage(
            "failed",
            path=provenance_path,
            reason=f"{type(exc).__name__}: {exc}",
        )
        bundle = {
            "format": FORMAT,
            "version": 1,
            "completed": False,
            "failed_stage": "store_provenance",
            "inputs": {
                "project_dir": str(project_dir),
                "project_name": project_name,
                "program_name": program_name,
                "ghidra_export": str(ghidra_export),
                "relation": str(relation_path),
            },
            "stages": stages,
            "handoff": {
                "offset33b_store_provenance_ready": False,
                "BMW_numeric_offset33b_ready": False,
                "vehicle_world_transform_ready": False,
            },
            "scope": {
                "validated_instruction_export_preserved": instruction_path.is_file(),
                "failed_analysis_promoted_to_numeric_proof": False,
                "original_game_executed": False,
                "new_runtime_capture_required": False,
            },
        }
        _write_json(bundle_path, bundle)
        raise

    decision = _decision(report)
    handoff = report.get("handoff") if isinstance(report.get("handoff"), Mapping) else {}
    bundle = {
        "format": FORMAT,
        "version": 1,
        "completed": True,
        "inputs": {
            "project_dir": str(project_dir),
            "project_name": project_name,
            "program_name": program_name,
            "ghidra_export": str(ghidra_export),
            "relation": str(relation_path),
        },
        "artifacts": {
            "instruction_export": str(instruction_path),
            "store_provenance": str(provenance_path),
        },
        "stages": stages,
        "decision": decision,
        "handoff": {
            "offset33b_store_provenance_ready": handoff.get("offset33b_store_provenance_ready") is True,
            "offset33b_value_root_frontier_ready": handoff.get("offset33b_value_root_frontier_ready") is True,
            "BMW_numeric_offset33b_ready": False,
            "BODY0_to_outer_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "scope": {
            "targeted_function_count": 1,
            "targeted_function": TARGET,
            "ghidra_project_opened_read_only": True,
            "ghidra_autoanalysis_requested": False,
            "store_frontier_promoted_to_numeric_values": False,
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
    parser.add_argument("--program-name", default=_stores.PROGRAM)
    parser.add_argument("--relation", type=Path, default=DEFAULT_RELATION)
    parser.add_argument("--ghidra-home", type=Path)
    parser.add_argument("--timeout-seconds", type=int)
    args = parser.parse_args(argv)

    report = run_bmw_offset33b_static_proof(
        args.project_dir,
        args.project_name,
        args.ghidra_export,
        args.output_dir,
        program_name=args.program_name,
        relation_path=args.relation,
        ghidra_home=args.ghidra_home,
        timeout_seconds=args.timeout_seconds,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
