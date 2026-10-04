#!/usr/bin/env python3
"""Run the corrected reduced BMW offset33b static-proof chain in one command.

The chain reuses one targeted ``FUN_0076b280`` Ghidra export and combines only
currently valid first-bootstrap reductions:

  STORE/value-root proof
    -> actual PhysicsParticipant additional-mass +0.0 proof (#1257)
    -> Vehicle reference-Y +0.0 proof (#1259)
    -> exact memory-LOAD/object-field frontier

The historical manager-record zero correction contract is not consumed.  A
completed bundle still keeps the three offset33b doubles non-numeric until the
remaining exact resource/init fields are joined and evaluated.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import analyze_bmw_offset33b_actual_additional_mass_bootstrap_zero as _mass
import analyze_bmw_offset33b_memory_load_provenance as _loads
import analyze_bmw_offset33b_vehicle_reference_y_bootstrap_zero as _reference_y
import run_bmw_offset33b_static_proof as _base

FORMAT = "SHIFT.BMWOffset33bReducedStaticProofBundle/1"
MASS_FILE = "03_bmw_offset33b_actual_additional_mass_bootstrap_zero.json"
REFERENCE_Y_FILE = "04_bmw_offset33b_vehicle_reference_y_bootstrap_zero.json"
LOAD_FILE = "05_bmw_offset33b_memory_load_provenance.json"
BUNDLE_FILE = "bmw_offset33b_reduced_static_proof_bundle.json"


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
    row: dict[str, Any] = {"state": state}
    if path is not None:
        row["path"] = str(path)
    if format_name is not None:
        row["format"] = format_name
    if reason is not None:
        row["reason"] = reason
    return row


def _inputs(
    project_dir: Path,
    project_name: str,
    ghidra_export: Path,
    relation_path: Path,
) -> dict[str, Any]:
    return {
        "project_dir": str(project_dir),
        "project_name": project_name,
        "program_name": _base._stores.PROGRAM,
        "ghidra_export": str(ghidra_export),
        "relation": str(relation_path),
    }


def _failure_bundle(
    *,
    failed_stage: str,
    inputs: Mapping[str, Any],
    artifacts: Mapping[str, Any],
    stages: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "completed": False,
        "failed_stage": failed_stage,
        "inputs": dict(inputs),
        "artifacts": dict(artifacts),
        "stages": dict(stages),
        "handoff": {
            "offset33b_store_provenance_ready": False,
            "offset33b_actual_additional_mass_bootstrap_zero_ready": False,
            "offset33b_vehicle_reference_y_bootstrap_zero_ready": False,
            "offset33b_memory_LOAD_frontier_ready": False,
            "offset33b_exact_memory_field_worklist_ready": False,
            "BMW_numeric_offset33b_ready": False,
            "BODY0_to_outer_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "scope": {
            "partial_artifacts_preserved": True,
            "failed_stage_promoted_to_numeric_proof": False,
            "retracted_manager_record_zero_claim_reused": False,
            "additional_Ghidra_export_requested": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
    }


def _decision(load_report: Mapping[str, Any] | None, store_ready: bool) -> dict[str, Any]:
    if not store_ready:
        return {
            "class": "store-frontier-incomplete",
            "next_action": "resolve exact offset33b STORE/value-root coverage before field joining",
        }
    if load_report is None:
        return {
            "class": "memory-load-stage-not-run",
            "next_action": "repair orchestration before semantic resource joining",
        }
    handoff = load_report.get("handoff")
    if not isinstance(handoff, Mapping):
        return {
            "class": "memory-load-report-invalid",
            "next_action": "repair the memory-LOAD proof artifact before resource semantics",
        }
    if handoff.get("offset33b_exact_memory_field_worklist_ready") is True:
        return {
            "class": "semantic-resource-field-join",
            "next_action": (
                "join each exact (base-origin expression, displacement, width) group to its "
                "HDV/VDF/SDF/tire field, then evaluate only supported arithmetic"
            ),
            "field_worklist": list(
                (load_report.get("analysis") or {}).get("exact_object_field_worklist") or []
            ),
        }
    if handoff.get("offset33b_memory_LOAD_frontier_ready") is True:
        return {
            "class": "resolve-load-base-or-helper-frontier",
            "next_action": (
                "resolve only remaining non-deterministic LOAD bases or non-LOAD/helper roots; "
                "do not broaden to runtime capture yet"
            ),
        }
    return {
        "class": "memory-load-structure-incomplete",
        "next_action": "resolve complex/multi-LOAD structure using the existing FUN_0076b280 export",
    }


def _run_metadata_stage(
    *,
    analyzer,
    path: Path,
    ghidra_export: Path,
    format_name: str,
) -> dict[str, Any]:
    report = analyzer(ghidra_export)
    _write_json(path, report)
    if report.get("format") != format_name or report.get("ready") is not True:
        raise ValueError(f"{format_name} did not produce a positive ready contract")
    return report


def run_bmw_offset33b_reduced_static_proof(
    project_dir: Path,
    project_name: str,
    ghidra_export: Path,
    output_dir: Path,
    *,
    program_name: str = _base._stores.PROGRAM,
    relation_path: Path = _base.DEFAULT_RELATION,
    ghidra_home: Path | None = None,
    timeout_seconds: int | None = None,
) -> dict[str, Any]:
    if not project_name.strip():
        raise ValueError("project_name must not be empty")
    if program_name != _base._stores.PROGRAM:
        raise ValueError(f"program_name must be exact retail {_base._stores.PROGRAM}")
    if timeout_seconds is not None and timeout_seconds < 1:
        raise ValueError("timeout_seconds must be >= 1")

    output_dir.mkdir(parents=True, exist_ok=True)
    base_bundle_path = output_dir / _base.BUNDLE_FILE
    instruction_path = output_dir / _base.INSTRUCTION_FILE
    store_path = output_dir / _base.PROVENANCE_FILE
    mass_path = output_dir / MASS_FILE
    reference_y_path = output_dir / REFERENCE_Y_FILE
    load_path = output_dir / LOAD_FILE
    bundle_path = output_dir / BUNDLE_FILE
    inputs = _inputs(project_dir, project_name, ghidra_export, relation_path)
    artifacts: dict[str, Any] = {}
    stages: dict[str, Any] = {}

    try:
        base_bundle = _base.run_bmw_offset33b_static_proof(
            project_dir,
            project_name,
            ghidra_export,
            output_dir,
            program_name=program_name,
            relation_path=relation_path,
            ghidra_home=ghidra_home,
            timeout_seconds=timeout_seconds,
        )
        artifacts.update(
            {
                "base_bundle": str(base_bundle_path),
                "instruction_export": str(instruction_path),
                "store_provenance": str(store_path),
            }
        )
        stages["base_static_proof"] = _stage(
            "completed", path=base_bundle_path, format_name=_base.FORMAT
        )
        if base_bundle.get("completed") is not True:
            raise ValueError("base offset33b static proof bundle is incomplete")
    except Exception as exc:
        stages["base_static_proof"] = _stage(
            "failed", path=base_bundle_path, reason=f"{type(exc).__name__}: {exc}"
        )
        bundle = _failure_bundle(
            failed_stage="base_static_proof",
            inputs=inputs,
            artifacts=artifacts,
            stages=stages,
        )
        _write_json(bundle_path, bundle)
        raise

    try:
        mass_report = _run_metadata_stage(
            analyzer=_mass.analyze,
            path=mass_path,
            ghidra_export=ghidra_export,
            format_name=_mass.FORMAT,
        )
        artifacts["actual_additional_mass_bootstrap_zero"] = str(mass_path)
        stages["actual_additional_mass_bootstrap_zero"] = _stage(
            "completed", path=mass_path, format_name=_mass.FORMAT
        )
    except Exception as exc:
        stages["actual_additional_mass_bootstrap_zero"] = _stage(
            "failed", path=mass_path, reason=f"{type(exc).__name__}: {exc}"
        )
        bundle = _failure_bundle(
            failed_stage="actual_additional_mass_bootstrap_zero",
            inputs=inputs,
            artifacts=artifacts,
            stages=stages,
        )
        _write_json(bundle_path, bundle)
        raise

    try:
        reference_y_report = _run_metadata_stage(
            analyzer=_reference_y.analyze,
            path=reference_y_path,
            ghidra_export=ghidra_export,
            format_name=_reference_y.FORMAT,
        )
        artifacts["vehicle_reference_y_bootstrap_zero"] = str(reference_y_path)
        stages["vehicle_reference_y_bootstrap_zero"] = _stage(
            "completed", path=reference_y_path, format_name=_reference_y.FORMAT
        )
    except Exception as exc:
        stages["vehicle_reference_y_bootstrap_zero"] = _stage(
            "failed", path=reference_y_path, reason=f"{type(exc).__name__}: {exc}"
        )
        bundle = _failure_bundle(
            failed_stage="vehicle_reference_y_bootstrap_zero",
            inputs=inputs,
            artifacts=artifacts,
            stages=stages,
        )
        _write_json(bundle_path, bundle)
        raise

    base_handoff = base_bundle.get("handoff")
    store_ready = bool(
        isinstance(base_handoff, Mapping)
        and base_handoff.get("offset33b_store_provenance_ready") is True
        and base_handoff.get("offset33b_value_root_frontier_ready") is True
    )

    load_report: dict[str, Any] | None = None
    if store_ready:
        try:
            load_report = _loads.analyze_bmw_offset33b_memory_load_provenance(
                store_path,
                instruction_path,
                mass_path,
            )
            _write_json(load_path, load_report)
            artifacts["memory_load_provenance"] = str(load_path)
            stages["memory_load_provenance"] = _stage(
                "completed", path=load_path, format_name=_loads.FORMAT
            )
        except Exception as exc:
            stages["memory_load_provenance"] = _stage(
                "failed", path=load_path, reason=f"{type(exc).__name__}: {exc}"
            )
            bundle = _failure_bundle(
                failed_stage="memory_load_provenance",
                inputs=inputs,
                artifacts=artifacts,
                stages=stages,
            )
            _write_json(bundle_path, bundle)
            raise
    else:
        stages["memory_load_provenance"] = _stage(
            "blocked_by_upstream_gate",
            reason="base offset33b STORE/value-root frontier is not ready",
        )

    mass_handoff = mass_report.get("handoff")
    mass_ready = bool(
        isinstance(mass_handoff, Mapping)
        and mass_handoff.get("offset33b_actual_additional_mass_bootstrap_zero_ready") is True
    )
    reference_handoff = reference_y_report.get("handoff")
    reference_y_ready = bool(
        isinstance(reference_handoff, Mapping)
        and reference_handoff.get("offset33b_vehicle_reference_y_bootstrap_zero_ready") is True
    )
    load_handoff = (
        load_report.get("handoff")
        if isinstance(load_report, Mapping) and isinstance(load_report.get("handoff"), Mapping)
        else {}
    )
    field_worklist = (
        list((load_report.get("analysis") or {}).get("exact_object_field_worklist") or [])
        if isinstance(load_report, Mapping)
        else []
    )
    decision = _decision(load_report, store_ready)

    bundle = {
        "format": FORMAT,
        "version": 1,
        "completed": True,
        "status": decision["class"],
        "inputs": inputs,
        "artifacts": artifacts,
        "stages": stages,
        "decision": decision,
        "exact_object_field_worklist": field_worklist,
        "known_semantic_reductions": {
            "actual_additional_mass_first_bootstrap_zero": mass_ready,
            "additional_mass_term_elidable_for_first_bootstrap": bool(
                isinstance(mass_handoff, Mapping)
                and mass_handoff.get(
                    "offset33b_additional_mass_term_can_be_elided_for_first_bootstrap"
                )
                is True
            ),
            "vehicle_reference_y_first_bootstrap_zero": reference_y_ready,
            "reference_y_reduced_to_negative_graphical_offset": bool(
                isinstance(reference_handoff, Mapping)
                and reference_handoff.get(
                    "offset33b_reference_y_reduced_to_negative_graphical_offset"
                )
                is True
            ),
            "additional_mass_machine_LOAD_join_ready": bool(
                load_handoff.get("offset33b_additional_mass_machine_LOAD_join_ready") is True
            ),
        },
        "handoff": {
            "offset33b_store_provenance_ready": store_ready,
            "offset33b_actual_additional_mass_bootstrap_zero_ready": mass_ready,
            "offset33b_vehicle_reference_y_bootstrap_zero_ready": reference_y_ready,
            "offset33b_memory_LOAD_frontier_ready": bool(
                load_handoff.get("offset33b_memory_LOAD_frontier_ready") is True
            ),
            "offset33b_exact_memory_field_worklist_ready": bool(
                load_handoff.get("offset33b_exact_memory_field_worklist_ready") is True
            ),
            "BMW_numeric_offset33b_ready": False,
            "BODY0_to_outer_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "scope": {
            "targeted_Ghidra_export_count": 1,
            "targeted_Ghidra_function": _base.TARGET,
            "additional_Ghidra_export_requested": False,
            "retracted_manager_record_zero_claim_reused": False,
            "additional_mass_zero_applied_without_machine_pointer_join": False,
            "memory_field_worklist_promoted_to_resource_semantics": False,
            "numeric_offset33b_claimed": False,
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
    parser.add_argument("--program-name", default=_base._stores.PROGRAM)
    parser.add_argument("--relation", type=Path, default=_base.DEFAULT_RELATION)
    parser.add_argument("--ghidra-home", type=Path)
    parser.add_argument("--timeout-seconds", type=int)
    args = parser.parse_args(argv)

    report = run_bmw_offset33b_reduced_static_proof(
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
