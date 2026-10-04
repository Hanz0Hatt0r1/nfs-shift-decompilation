#!/usr/bin/env python3
"""Join exact BMW BODY0 resource values to the static construction continuity proof.

This pass consumes only machine-readable evidence.  It never requires the raw
retail BFF/SDF to be committed.  A positive zero-orientation resource witness
promotes BODY0-local -> SDF-model to the exact row-vector affine pose already
licensed by SHIFT.BMWBody0ConstructionBindContinuity/1.  The outer/VHF frame
relation deliberately remains fail-closed.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

CONTINUITY_FORMAT = "SHIFT.BMWBody0ConstructionBindContinuity/1"
RESOURCE_FORMAT = "SHIFT.BMWBody0BindResourceMaterialization/1"
ARCHIVE_SHA256 = "c31d34a0a7cab04bcff693fa0cbda3400f50d690a9c8bb2521b2882fc2a68d70"
SDF_PATH = "vehicles/physics/suspension/aarm_multilink.sdf"
SDF_SHA256 = "fe0b18e95e81f87d67076b70890965a0a1384a925bfd836aaf5aa705fc4781ed"
BODY_INDEX = 0
BODY_NAME = "body"
BODY_COUNT = 11


def _load(path: Path, expected_format: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    if value.get("format") != expected_format:
        raise ValueError(f"{path}: expected {expected_format}")
    return value


def _finite3(value: Any, label: str) -> list[float]:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes))
        or len(value) != 3
    ):
        raise ValueError(f"{label}: expected exactly three scalars")
    result: list[float] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise ValueError(f"{label}: non-numeric scalar")
        number = float(item)
        if not math.isfinite(number):
            raise ValueError(f"{label}: non-finite scalar")
        result.append(number)
    return result


def _identity_pose_row(pos: Sequence[float]) -> list[float]:
    return [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        float(pos[0]), float(pos[1]), float(pos[2]), 1.0,
    ]


def _validate_continuity(report: Mapping[str, Any]) -> None:
    if report.get("ready") is not True:
        raise ValueError("construction continuity evidence is not ready")
    handoff = report.get("handoff") or {}
    for field in (
        "BODY_descriptor_pos_ori_semantics_ready",
        "construction_origin_continuity_ready",
        "construction_basis_continuity_ready",
    ):
        if handoff.get(field) is not True:
            raise ValueError(f"construction continuity prerequisite not ready: {field}")
    intake = report.get("bmw_intake") or {}
    archive = intake.get("archive") or {}
    sdf = intake.get("sdf_entry") or {}
    if archive.get("filename") != "BMW_M3_E36.bff" or archive.get("sha256") != ARCHIVE_SHA256:
        raise ValueError("construction continuity BMW archive identity drift")
    if sdf.get("path") != SDF_PATH or sdf.get("decoded_sha256") != SDF_SHA256:
        raise ValueError("construction continuity BMW SDF identity drift")
    if int(intake.get("body_count", -1)) != BODY_COUNT:
        raise ValueError("construction continuity BODY count drift")
    if int(intake.get("body_index", -1)) != BODY_INDEX or intake.get("body_name") != BODY_NAME:
        raise ValueError("construction continuity BODY0 identity drift")


def _validate_resource(report: Mapping[str, Any]) -> tuple[list[float], list[float]]:
    if report.get("ready") is not True or report.get("status") != "materialized":
        raise ValueError("BODY0 resource materialization is not ready")
    archive = report.get("retail_archive") or {}
    resource = report.get("resource") or {}
    body0 = report.get("body0") or {}
    handoff = report.get("handoff") or {}
    if archive.get("canonical_filename") != "BMW_M3_E36.bff" or archive.get("sha256") != ARCHIVE_SHA256:
        raise ValueError("BODY0 resource BMW archive identity drift")
    if resource.get("path") != SDF_PATH or resource.get("decoded_sha256") != SDF_SHA256:
        raise ValueError("BODY0 resource SDF identity drift")
    if int(resource.get("entry_index", -1)) != 1091:
        raise ValueError("BODY0 resource SDF entry index drift")
    if int(resource.get("compression_type", -1)) != 2:
        raise ValueError("BODY0 resource compression type drift")
    if int(resource.get("compressed_size", -1)) != 1110 or int(resource.get("uncompressed_size", -1)) != 5056:
        raise ValueError("BODY0 resource SDF size drift")
    if int(body0.get("body_count", -1)) != BODY_COUNT:
        raise ValueError("BODY0 resource BODY count drift")
    if int(body0.get("body_index", -1)) != BODY_INDEX or body0.get("body_name") != BODY_NAME:
        raise ValueError("BODY0 resource identity drift")
    if handoff.get("BODY0_resource_pos_ori_values_ready") is not True:
        raise ValueError("BODY0 resource values are not admitted")
    pos = _finite3(body0.get("pos"), "BODY0 pos")
    ori = _finite3(body0.get("ori"), "BODY0 ori")
    exact_zero = all(value == 0.0 for value in ori)
    if bool(body0.get("ori_is_exact_zero")) != exact_zero:
        raise ValueError("BODY0 exact-zero orientation flag drift")
    if bool(body0.get("zero_orientation_identity_shortcut_eligible")) != exact_zero:
        raise ValueError("BODY0 identity-shortcut flag drift")
    return pos, ori


def promote(
    continuity_path: Path,
    resource_path: Path,
) -> dict[str, Any]:
    continuity = _load(continuity_path, CONTINUITY_FORMAT)
    resource_evidence = _load(resource_path, RESOURCE_FORMAT)
    _validate_continuity(continuity)
    pos, ori = _validate_resource(resource_evidence)

    report = copy.deepcopy(continuity)
    exact_zero = all(value == 0.0 for value in ori)
    resource_body0: dict[str, Any] = {
        "available": True,
        "path": SDF_PATH,
        "sha256": SDF_SHA256,
        "body_index": BODY_INDEX,
        "body_name": BODY_NAME,
        "pos": pos,
        "ori": ori,
        "ori_is_exact_zero": exact_zero,
        "basis_ready": exact_zero,
        "basis": (
            [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
            if exact_zero else None
        ),
        "body0_local_to_sdf_model_row_matrix_ready": exact_zero,
        "body0_local_to_sdf_model_row_matrix": _identity_pose_row(pos) if exact_zero else None,
    }
    report["resource_BODY0"] = resource_body0
    report["resource_materialization_evidence"] = {
        "format": RESOURCE_FORMAT,
        "path": str(resource_path),
        "archive_sha256": ARCHIVE_SHA256,
        "decoded_sdf_sha256": SDF_SHA256,
    }

    blockers = [
        row
        for row in (report.get("blockers") or [])
        if isinstance(row, dict)
        and row.get("id") not in {
            "exact-BMW-BODY0-pos-ori-values-unavailable",
            "nonzero-BODY0-ori-retail-basis-evaluation-not-materialized",
        }
    ]
    if not exact_zero:
        blockers.insert(
            0,
            {
                "id": "nonzero-BODY0-ori-retail-basis-evaluation-not-materialized",
                "status": "blocked",
                "required_evidence": (
                    "materialize the exact FUN_007b00a0 basis result for the observed nonzero BODY0 ori"
                ),
            },
        )
    report["blockers"] = blockers

    handoff = report.setdefault("handoff", {})
    handoff["BODY0_resource_pos_ori_values_ready"] = True
    handoff["BODY0_local_to_SDF_model_bind_pose_ready"] = exact_zero
    handoff["SDF_model_to_VHF_vehicle_root_frame_relation_ready"] = False
    handoff["BODY0_bind_frame_proof_ready"] = False
    handoff["vehicle_world_transform_ready"] = False

    scope = report.setdefault("scope", {})
    scope["resource_materialization_evidence_consumed"] = True
    scope["raw_retail_archive_committed"] = False
    scope["raw_decoded_sdf_committed"] = False
    scope["SDF_model_frame_assumed_equal_VHF_vehicle_root"] = False
    scope["final_BODY0_to_VHF_bind_relation_proven"] = False
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("continuity", type=Path)
    parser.add_argument("resource_materialization", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    report = promote(args.continuity, args.resource_materialization)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out is None:
        print(text, end="")
    else:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
