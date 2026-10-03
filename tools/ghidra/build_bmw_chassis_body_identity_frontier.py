#!/usr/bin/env python3
"""Prove the retail BMW main suspension/chassis BODY from retained topology evidence.

This proof does not promote the SDF name ``body`` by plausibility.  It joins the
Phase 404 exact BODY order to the Phase 405 source-backed real-asset solver
signature and retained constraint topology.  The selected BODY is the unique
endpoint incident to all 20 suspension BAR records across all four spindle
families.  Update-child -> vehicle solver-base continuity remains a separate
fail-closed boundary.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.BMWChassisBodyIdentityFrontier/1"
PHASE404_FORMAT = "SHIFT.BMWM3PhysicsIntakeEvidence/1"
PHASE405_FORMAT = "SHIFT.BMWM3SolverDomainEvidence/1"
TOPOLOGY_FORMAT = "SHIFT.BMWM3ChassisBodyTopologyEvidence/1"
BMW_ARCHIVE = "BMW_M3_E36.bff"
BMW_ARCHIVE_SHA256 = "c31d34a0a7cab04bcff693fa0cbda3400f50d690a9c8bb2521b2882fc2a68d70"
BMW_SDF_PATH = "vehicles/physics/suspension/aarm_multilink.sdf"
BMW_SDF_SHA256 = "fe0b18e95e81f87d67076b70890965a0a1384a925bfd836aaf5aa705fc4781ed"
PHASE405_COMMIT = "17c4adebc3e0c42fdfa929be0cb5d25716d3d2e7"
DEFAULT_PHASE404 = "evidence/bmw_m3_e36_physics_intake_phase404.json"
DEFAULT_PHASE405 = "evidence/bmw_m3_e36_solver_domain_phase405.json"
DEFAULT_TOPOLOGY = "evidence/bmw_m3_e36_chassis_body_topology_process1.json"
UPSTREAM_BATCH = "0x00713050"
FIRST_UPDATE_CALLER = "0x00794a30"
VEHICLE_SOLVER_SETUP = "0x007615c0"


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load(path: Path, expected: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}")
    return value


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _source_hashes(value: dict[str, Any]) -> tuple[str, str, str, str]:
    source = value.get("source") or {}
    return (
        str(source.get("archive") or ""),
        str(source.get("archive_sha256") or "").lower(),
        str(source.get("sdf_path") or ""),
        str(source.get("sdf_sha256") or "").lower(),
    )


def build_bmw_chassis_body_identity_frontier(
    phase404_path: Path | None = None,
    phase405_path: Path | None = None,
    topology_path: Path | None = None,
) -> dict[str, Any]:
    root = _root()
    phase404_path = phase404_path or root / DEFAULT_PHASE404
    phase405_path = phase405_path or root / DEFAULT_PHASE405
    topology_path = topology_path or root / DEFAULT_TOPOLOGY
    phase404 = _load(phase404_path, PHASE404_FORMAT)
    phase405 = _load(phase405_path, PHASE405_FORMAT)
    topology = _load(topology_path, TOPOLOGY_FORMAT)

    archive = phase404.get("archive") or {}
    sdf_entry = phase404.get("sdf_entry") or {}
    structure = phase404.get("structure") or {}
    bodies = phase404.get("bodies")
    _require(phase404.get("status") == "decoded-from-user-supplied-bff", "Phase 404 provenance drift")
    _require(archive.get("filename") == BMW_ARCHIVE, "Phase 404 archive drift")
    _require(str(archive.get("sha256") or "").lower() == BMW_ARCHIVE_SHA256, "Phase 404 archive SHA-256 drift")
    _require(sdf_entry.get("path") == BMW_SDF_PATH, "Phase 404 SDF path drift")
    _require(str(sdf_entry.get("decoded_sha256") or "").lower() == BMW_SDF_SHA256, "Phase 404 SDF SHA-256 drift")
    _require(isinstance(bodies, list) and len(bodies) == 11, "Phase 404 BODY order missing")
    _require(int(structure.get("body_count", -1)) == 11, "Phase 404 BODY count drift")
    body_names = [str(value) for value in bodies]
    _require(len(set(body_names)) == len(body_names), "Phase 404 duplicate BODY name")

    phase405_source = _source_hashes(phase405)
    expected_source = (BMW_ARCHIVE, BMW_ARCHIVE_SHA256, BMW_SDF_PATH, BMW_SDF_SHA256)
    _require(phase405_source == expected_source, "Phase 405 source identity drift")
    _require(phase405.get("status") == "source-backed-real-asset-topology", "Phase 405 provenance drift")
    runtime = phase405.get("runtime_topology") or {}
    _require(int(runtime.get("body_count", -1)) == 11, "Phase 405 BODY count drift")
    _require(int(runtime.get("joint_hinge_source_records", -1)) == 4, "Phase 405 JOINT&Hinge count drift")
    _require(int(runtime.get("runtime_bar_records", -1)) == 20, "Phase 405 BAR count drift")
    _require(int(runtime.get("solver_scalar_count", -1)) == 40, "Phase 405 scalar count drift")

    topology_source = _source_hashes(topology)
    _require(topology_source == expected_source, "retained topology source identity drift")
    source = topology.get("source") or {}
    _require(source.get("retained_reconstruction_commit") == PHASE405_COMMIT, "retained Phase 405 commit drift")
    _require(topology.get("status") == "retained-source-backed-real-asset-topology", "retained topology provenance drift")

    expected_ordering = topology.get("phase405_ordering_signature") or {}
    phase405_ordering = phase405.get("ordering") or {}
    for key in ("function", "initial_cost", "final_cost", "improvement_count", "pass_count", "final_order_tail"):
        _require(phase405_ordering.get(key) == expected_ordering.get(key), f"Phase 405 ordering signature drift: {key}")

    joints = topology.get("joint_hinge_pairs")
    _require(isinstance(joints, list) and len(joints) == 4, "retained JOINT&Hinge topology drift")
    joint_axes = phase404.get("joint_axes")
    _require(isinstance(joint_axes, list) and len(joint_axes) == 4, "Phase 404 joint axes missing")
    for index, row in enumerate(joints):
        _require(isinstance(row, dict), f"invalid joint row {index}")
        _require(row.get("posbody") in body_names and row.get("negbody") in body_names, f"joint BODY identity drift at {index}")
        _require(row.get("axis") == joint_axes[index], f"joint axis drift at {index}")

    bars = topology.get("bar_topology") or {}
    bar_count = int(bars.get("bar_count", -1))
    common_body = str(bars.get("common_body") or "")
    target_counts = bars.get("target_counts")
    _require(bar_count == 20, "retained BAR count drift")
    _require(common_body in body_names, "retained common BAR BODY missing from Phase 404")
    _require(isinstance(target_counts, dict) and len(target_counts) == 4, "retained BAR target families drift")
    normalized_targets = {str(name): int(count) for name, count in target_counts.items()}
    _require(sum(normalized_targets.values()) == bar_count, "retained BAR target count sum drift")
    _require(set(normalized_targets) == {"fl_spindle", "fr_spindle", "rl_spindle", "rr_spindle"}, "retained BAR spindle target set drift")
    _require(all(count == 5 for count in normalized_targets.values()), "retained BAR spindle degree drift")
    _require(common_body not in normalized_targets, "common BAR BODY cannot be a spindle target")

    degrees = {name: 0 for name in body_names}
    degrees[common_body] += bar_count
    for name, count in normalized_targets.items():
        _require(name in degrees, f"retained BAR target BODY missing: {name}")
        degrees[name] += count
    all_bar_endpoints = [name for name, degree in degrees.items() if degree == bar_count]
    _require(all_bar_endpoints == [common_body], "central suspension BODY is not unique")

    selection = topology.get("semantic_selection") or {}
    selected_name = str(selection.get("body_name") or "")
    selected_index = int(selection.get("body_index", -1))
    _require(selected_name == common_body, "semantic selection/common BAR BODY mismatch")
    _require(selected_name in body_names, "selected BODY name missing")
    _require(body_names.index(selected_name) == selected_index, "selected BODY index/order mismatch")
    _require(selected_index == 0, "retail main suspension BODY index drift")

    return {
        "format": FORMAT,
        "inputs": {
            "phase404_archive_evidence": str(phase404_path),
            "phase405_solver_domain_evidence": str(phase405_path),
            "retained_constraint_topology_evidence": str(topology_path),
        },
        "retail_identity": {
            "archive": BMW_ARCHIVE,
            "archive_sha256": BMW_ARCHIVE_SHA256,
            "sdf_path": BMW_SDF_PATH,
            "sdf_sha256": BMW_SDF_SHA256,
        },
        "topology_proof": {
            "source_state": "retained-phase405-source-backed-real-asset-topology",
            "bar_count": bar_count,
            "common_bar_BODY": common_body,
            "bar_endpoint_degrees": degrees,
            "unique_BODY_incident_to_all_BARs": common_body,
            "spindle_target_counts": normalized_targets,
            "phase405_ordering_signature_verified": True,
            "body_name_plausibility_used_as_proof": False,
        },
        "selection": {
            "role": "main-suspension/chassis BODY",
            "selected_BODY_name": selected_name,
            "selected_BODY_index": selected_index,
            "evidence_state": "proven-by-retail-constraint-topology",
            "main_chassis_BODY_selected": True,
        },
        "handoff": {
            "main_chassis_BODY_selected": True,
            "main_chassis_BODY_index": selected_index,
            "main_chassis_BODY_name": selected_name,
            "rear_axle_BODY_index_required_for_chassis_selection": False,
            "update_child_to_vehicle_solver_base_continuity_proven": False,
            "vehicle_BODY_selection_ready": False,
            "phase698_positive_selection_admissible": False,
            "critical_next_join": "*record+0x340 update child -> FUN_007615c0 vehicle solver base",
        },
        "blockers": [
            {
                "id": "update-child-to-vehicle-solver-base-continuity",
                "evidence_state": "unknown",
                "targets": [UPSTREAM_BATCH, FIRST_UPDATE_CALLER, VEHICLE_SOLVER_SETUP],
                "required_evidence": "join *record+0x340 update child to the FUN_007615c0 vehicle base before emitting SHIFT.VehicleBodyIdentityFrontier/1",
            }
        ],
        "residual_noncritical_unknowns": [
            {
                "id": "rear-axle-field-role-to-SDF-index",
                "vehicle_offset": "0x2e00",
                "blocks_main_chassis_pose_selection": False,
            }
        ],
        "scope": {
            "body_name_alone_proves_chassis_semantics": False,
            "constraint_topology_proves_main_suspension_BODY": True,
            "update_child_identity_inferred_from_BODY_index": False,
            "vehicle_world_transform_ready": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase404", type=Path)
    parser.add_argument("--phase405", type=Path)
    parser.add_argument("--topology-evidence", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    report = build_bmw_chassis_body_identity_frontier(args.phase404, args.phase405, args.topology_evidence)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"main chassis BODY: {report['selection']['selected_BODY_index']} ({report['selection']['selected_BODY_name']})")
    print(f"vehicle BODY selection ready: {report['handoff']['vehicle_BODY_selection_ready']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
