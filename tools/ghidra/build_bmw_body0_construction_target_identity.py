#!/usr/bin/env python3
"""Join construction-time BODY pose writes to the persistent BMW chassis BODY0.

This pass closes the target-identity half of the construction bind proof.  It
combines the existing machine/p-code pose-store discovery with the source-audited
SDF BODY loader/builder semantics, exact retail function fingerprints, the BMW
Phase-404 BODY order, and the already-proven descriptor->persistent-pose
continuity.

It deliberately does not equate the SDF model frame with the VHF vehicle-root
frame and therefore cannot by itself publish SHIFT.BMWBody0BindFrameProof/1 or
a VehicleWorldMatrix.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.BMWBody0ConstructionTargetIdentity/1"
POSE_FORMAT = "SHIFT.BMWBody0ConstructionPoseStores/1"
CONTINUITY_FORMAT = "SHIFT.BMWBody0ConstructionBindContinuity/1"
INTAKE_FORMAT = "SHIFT.BMWM3PhysicsIntakeEvidence/1"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"

BODY_LOADER = "0x007b6900"
BODY_BUILDER = "0x007b3670"
ORI_HELPER = "0x007bbb10"
BODY_STRIDE = 0x170
BODY_COUNT_MEMBER = 0x10
BODY_ARRAY_MEMBER = 0x14
BODY0_INDEX = 0
BODY0_NAME = "body"

TARGETS = {
    BODY_LOADER: "154593816d7647c6cd8a0ee37b96e92c38cd78b318bd16cdbfcefb7bca3aba81",
    BODY_BUILDER: "bcf42f221ca37b7ee8f907b0783fc8da894ecc3528e86506f6d58e448a0953d3",
    ORI_HELPER: "345f993d42c3338af314e48791796449516286b95ccdc40a7d188590fc091238",
}
REQUIRED_EDGES = (
    (BODY_LOADER, "0x007b6e8f", BODY_BUILDER),
    (BODY_BUILDER, "0x007b37c8", ORI_HELPER),
)
EXPECTED_BMW_BODIES = [
    "body",
    "fl_spindle",
    "fr_spindle",
    "fl_wheel",
    "fr_wheel",
    "rl_spindle",
    "rr_spindle",
    "rl_wheel",
    "rr_wheel",
    "fuel_tank",
    "driver_head",
]


def _load_json(path: Path, expected_format: str | None = None) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    if expected_format is not None and value.get("format") != expected_format:
        raise ValueError(f"{path}: expected {expected_format}")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, 1):
            text = raw.strip()
            if not text:
                continue
            value = json.loads(text)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            rows.append(value)
    return rows


def _address(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field}: expected address string")
    token = value.strip().lower()
    if token.startswith("fun_"):
        token = token[4:]
    if token.startswith("0x"):
        token = token[2:]
    try:
        return f"0x{int(token, 16):08x}"
    except ValueError as exc:
        raise ValueError(f"{field}: invalid address {value!r}") from exc


def _validate_retail(root: Path) -> dict[str, Any]:
    binary = _load_json(root / "binary.json")
    if binary.get("program_name") != PROGRAM:
        raise ValueError("unexpected Ghidra program")
    if binary.get("executable_md5") != PE_MD5:
        raise ValueError("unexpected retail executable MD5")

    found: dict[str, Mapping[str, Any]] = {}
    for row in _read_jsonl(root / "functions.jsonl"):
        raw = row.get("address")
        if not isinstance(raw, str):
            continue
        address = _address(raw, "functions.address")
        if address in TARGETS:
            if address in found:
                raise ValueError(f"duplicate function row {address}")
            found[address] = row
    missing = sorted(set(TARGETS) - set(found))
    if missing:
        raise ValueError("missing required retail function(s): " + ", ".join(missing))
    for address, digest in TARGETS.items():
        row = found[address]
        if row.get("external") is True or row.get("thunk") is True:
            raise ValueError(f"{address}: expected concrete retail function")
        if row.get("mnemonic_sha256") != digest:
            raise ValueError(f"{address}: mnemonic fingerprint drift")

    edges: set[tuple[str, str, str]] = set()
    for row in _read_jsonl(root / "callgraph.jsonl"):
        if row.get("indirect") is True:
            continue
        if not all(isinstance(row.get(key), str) for key in ("from_function", "instruction", "to")):
            continue
        edges.add(
            (
                _address(row["from_function"], "callgraph.from_function"),
                _address(row["instruction"], "callgraph.instruction"),
                _address(row["to"], "callgraph.to"),
            )
        )
    missing_edges = [edge for edge in REQUIRED_EDGES if edge not in edges]
    if missing_edges:
        raise ValueError("missing required BODY construction edge(s): " + repr(missing_edges))

    return {
        "program_name": PROGRAM,
        "executable_md5": PE_MD5,
        "functions": [
            {"address": address, "mnemonic_sha256": TARGETS[address]}
            for address in TARGETS
        ],
        "required_direct_edges": [
            {"from": source, "instruction": instruction, "to": target}
            for source, instruction, target in REQUIRED_EDGES
        ],
    }


def _validate_intake(report: Mapping[str, Any]) -> None:
    archive = report.get("archive") or {}
    sdf_entry = report.get("sdf_entry") or {}
    structure = report.get("structure") or {}
    bodies = report.get("bodies")
    if archive.get("filename") != "BMW_M3_E36.bff":
        raise ValueError("BMW archive identity drift")
    if archive.get("sha256") != "c31d34a0a7cab04bcff693fa0cbda3400f50d690a9c8bb2521b2882fc2a68d70":
        raise ValueError("BMW archive SHA-256 drift")
    if sdf_entry.get("path") != "vehicles/physics/suspension/aarm_multilink.sdf":
        raise ValueError("BMW SDF path drift")
    if structure.get("body_count") != len(EXPECTED_BMW_BODIES):
        raise ValueError("BMW BODY count drift")
    if bodies != EXPECTED_BMW_BODIES:
        raise ValueError("BMW BODY order/name drift")


def _validate_pose(report: Mapping[str, Any]) -> None:
    retail = report.get("retail_identity") or {}
    if retail.get("program_name") != PROGRAM or retail.get("executable_md5") != PE_MD5:
        raise ValueError("construction pose-store retail identity drift")
    handoff = report.get("handoff") or {}
    if handoff.get("construction_pose_store_discovery_complete") is not True:
        raise ValueError("construction pose-store discovery is incomplete")
    if handoff.get("construction_pose_store_candidate_found") is not True:
        raise ValueError("construction pose-store candidate is missing")
    analysis = report.get("analysis") or {}
    if analysis.get("structural_blockers"):
        raise ValueError("construction pose-store report retains structural ambiguity")


def _validate_continuity(report: Mapping[str, Any]) -> None:
    if report.get("ready") is not True:
        raise ValueError("construction bind continuity is not ready")
    retail = report.get("retail_identity") or {}
    if retail.get("program_name") != PROGRAM or retail.get("executable_md5") != PE_MD5:
        raise ValueError("construction continuity retail identity drift")
    handoff = report.get("handoff") or {}
    if handoff.get("BODY_descriptor_pos_ori_semantics_ready") is not True:
        raise ValueError("BODY descriptor semantics are not ready")
    if handoff.get("construction_origin_continuity_ready") is not True:
        raise ValueError("construction origin continuity is not ready")
    if handoff.get("construction_basis_continuity_ready") is not True:
        raise ValueError("construction basis continuity is not ready")
    if handoff.get("BODY0_bind_frame_proof_ready") is True:
        raise ValueError("upstream continuity must not preclaim final bind-frame proof")


def build_bmw_body0_construction_target_identity(
    ghidra_export: Path,
    intake_path: Path,
    pose_stores_path: Path,
    continuity_path: Path,
) -> dict[str, Any]:
    retail = _validate_retail(ghidra_export)
    intake = _load_json(intake_path, INTAKE_FORMAT)
    pose = _load_json(pose_stores_path, POSE_FORMAT)
    continuity = _load_json(continuity_path, CONTINUITY_FORMAT)
    _validate_intake(intake)
    _validate_pose(pose)
    _validate_continuity(continuity)

    continuity_handoff = continuity.get("handoff") or {}
    values_ready = continuity_handoff.get("BODY0_local_to_SDF_model_bind_pose_ready") is True

    source_semantics = {
        "evidence_state": "proven-static-under-exact-retail-function-fingerprints",
        "loader": {
            "function": BODY_LOADER,
            "body_count_member": f"+0x{BODY_COUNT_MEMBER:x}",
            "body_array_member": f"+0x{BODY_ARRAY_MEMBER:x}",
            "persistent_body_stride": f"0x{BODY_STRIDE:x}",
            "first_body_ordinal_initialized_to": 0,
            "body_ordinal_reset_occurs_after_persistent_arrays_are_allocated": True,
            "second_parse_pass_calls_builder_once_per_BODY_section": True,
        },
        "builder": {
            "function": BODY_BUILDER,
            "target_expression": "*(loader_this+0x14) + (*body_ordinal * 0x170)",
            "origin_writes_use_target_expression": True,
            "orientation_helper_receiver_uses_same_target_expression": True,
            "body_ordinal_increment_exactly_once_on_success": True,
        },
        "body0_join": {
            "resource_body_index": BODY0_INDEX,
            "resource_body_name": BODY0_NAME,
            "first_persistent_record_expression": "*(loader_this+0x14) + 0*0x170",
            "first_persistent_record_is_resource_BODY0": True,
        },
    }

    return {
        "format": FORMAT,
        "version": 1,
        "status": "construction-target-identity-proven",
        "ready": True,
        "retail_identity": retail,
        "inputs": {
            "intake_format": INTAKE_FORMAT,
            "pose_store_format": POSE_FORMAT,
            "continuity_format": CONTINUITY_FORMAT,
        },
        "source_static_proof": source_semantics,
        "target_identity": {
            "persistent_BODY_array_identity_ready": True,
            "persistent_BODY_record_stride": BODY_STRIDE,
            "first_BODY_ordinal": BODY0_INDEX,
            "first_BODY_name": BODY0_NAME,
            "BODY0_pointer_at_construction_pose_write_ready": True,
            "origin_writer_target_is_BODY0": True,
            "basis_writer_target_is_BODY0": True,
        },
        "handoff": {
            "construction_pose_store_discovery_complete": True,
            "construction_origin_continuity_ready": True,
            "construction_basis_continuity_ready": True,
            "persistent_BODY_target_identity_proven": True,
            "BODY0_pointer_at_construction_pose_write_ready": True,
            "BODY0_bind_origin_basis_values_ready": values_ready,
            "BODY0_local_to_SDF_model_bind_pose_ready": values_ready,
            "SDF_model_to_VHF_vehicle_root_frame_relation_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
            "required_next_join": (
                "prove SDF-model construction frame -> VHF vehicle-root/assembly frame relation; "
                "if exact BODY0 resource values are not yet materialized, feed the existing resource materialization into continuity first"
            ),
        },
        "blockers": [
            {
                "id": "SDF-model-to-VHF-vehicle-root-frame-relation-unproven",
                "status": "unknown",
                "required_evidence": "static frame relation; do not infer identity from common owner names or pointer ancestry",
            }
        ],
        "scope": {
            "original_game_executed": False,
            "new_runtime_capture_required": False,
            "SDF_model_frame_assumed_equal_VHF_vehicle_root": False,
            "final_BODY0_bind_frame_proven": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("intake", type=Path)
    parser.add_argument("pose_stores", type=Path)
    parser.add_argument("continuity", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    report = build_bmw_body0_construction_target_identity(
        args.ghidra_export,
        args.intake,
        args.pose_stores,
        args.continuity,
    )
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
