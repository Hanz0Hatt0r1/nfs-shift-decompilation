#!/usr/bin/env python3
"""Freeze the BODY0 -> VHF bind-frame equation without inventing the bind matrix.

The current repository already has three independent pieces:

* a persistent BODY0 pose ABI (origin + 3x3 basis),
* a source-backed VHF body-MEB bind transform in D3D row-vector convention,
* a native per-step vehicle world-transform transport.

What is still missing is one static affine witness: BODY0-local -> VHF vehicle-root
at bind/assembly time.  This report makes that single unknown explicit and freezes
the exact composition that becomes legal once the witness is proven.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.BMWBody0VHFBindFrameFrontier/1"
GLOBAL_IDENTITY_FORMAT = "SHIFT.GlobalVehicleBodyOwnerIdentity/1"
VHF_FORMAT = "SHIFT.BMWVHFBodyWorldTransform/1"
BIND_PROOF_FORMAT = "SHIFT.BMWBody0BindFrameProof/1"

BODY_INDEX = 0
BODY_NAME = "body"
GLOBAL_VEHICLE_ADDRESS = 0x00C13700
ROW_CONVENTION = "row-major D3D row-vector affine"
FRAME_RELATION = "BODY0-local-to-VHF-vehicle-root"

STATIC_TARGETS = [
    {
        "function": "FUN_007b6900",
        "address": "0x007b6900",
        "evidence_state": "verified-loader-anchor",
        "request": "trace exact BODY[0] pos/ori descriptor production without assigning unproved runtime semantics",
    },
    {
        "function": "FUN_007b3670",
        "address": "0x007b3670",
        "evidence_state": "verified-body-builder-anchor",
        "request": "trace BODY[0] descriptor vectors into the 0x170-byte persistent BODY record",
    },
    {
        "function": "FUN_007b7840",
        "address": "0x007b7840",
        "evidence_state": "verified-pose-writer-candidate",
        "request": "recover callers and exact origin/basis inputs on the vehicle initialization path; do not assume this writer owns bind initialization",
    },
]


def _load(path: Path, expected: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}")
    return value


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _int(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError(f"invalid integer: {value!r}")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value, 0)
    raise ValueError(f"invalid integer: {value!r}")


def _finite_vector(value: Any, count: int, label: str) -> list[float]:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes))
        or len(value) != count
    ):
        raise ValueError(f"{label} must contain exactly {count} scalars")
    result: list[float] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise ValueError(f"{label} contains non-numeric value")
        number = float(item)
        if not math.isfinite(number):
            raise ValueError(f"{label} contains non-finite value")
        result.append(number)
    return result


def _det3(matrix: Sequence[float]) -> float:
    a, b, c = matrix[0], matrix[1], matrix[2]
    d, e, f = matrix[4], matrix[5], matrix[6]
    g, h, i = matrix[8], matrix[9], matrix[10]
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


def _row_affine(value: Any, label: str) -> list[float]:
    matrix = _finite_vector(value, 16, label)
    if any(abs(matrix[index]) > 1.0e-6 for index in (3, 7, 11)):
        raise ValueError(f"{label} is not D3D row-vector affine")
    if abs(matrix[15] - 1.0) > 1.0e-6:
        raise ValueError(f"{label} homogeneous component is not one")
    determinant = _det3(matrix)
    if not math.isfinite(determinant) or abs(determinant) <= 1.0e-12:
        raise ValueError(f"{label} linear block is singular")
    return matrix


def _mul4(lhs: Sequence[float], rhs: Sequence[float]) -> list[float]:
    return [
        sum(float(lhs[row * 4 + k]) * float(rhs[k * 4 + column]) for k in range(4))
        for row in range(4)
        for column in range(4)
    ]


def _inverse_affine_row(value: Any, label: str = "bind matrix") -> list[float]:
    m = _row_affine(value, label)
    a, b, c = m[0], m[1], m[2]
    d, e, f = m[4], m[5], m[6]
    g, h, i = m[8], m[9], m[10]
    det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    inv_det = 1.0 / det
    inv = [
        (e * i - f * h) * inv_det,
        (c * h - b * i) * inv_det,
        (b * f - c * e) * inv_det,
        0.0,
        (f * g - d * i) * inv_det,
        (a * i - c * g) * inv_det,
        (c * d - a * f) * inv_det,
        0.0,
        (d * h - e * g) * inv_det,
        (b * g - a * h) * inv_det,
        (a * e - b * d) * inv_det,
        0.0,
        0.0,
        0.0,
        0.0,
        1.0,
    ]
    tx, ty, tz = m[12], m[13], m[14]
    inv[12] = -(tx * inv[0] + ty * inv[4] + tz * inv[8])
    inv[13] = -(tx * inv[1] + ty * inv[5] + tz * inv[9])
    inv[14] = -(tx * inv[2] + ty * inv[6] + tz * inv[10])
    return _row_affine(inv, f"inverse({label})")


def body_pose_row_matrix(origin: Sequence[float], basis: Sequence[float]) -> list[float]:
    """Convert the proven BODY column-vector basis/origin into SVWT row form.

    BODY basis memory order is the source-backed 3x3 B used by
    world_offset_column = B * local_column.  A D3D row-vector representation is
    therefore the exact transpose of the homogeneous column-vector pose.
    """
    o = _finite_vector(origin, 3, "BODY origin")
    b = _finite_vector(basis, 9, "BODY basis")
    matrix = [
        b[0], b[3], b[6], 0.0,
        b[1], b[4], b[7], 0.0,
        b[2], b[5], b[8], 0.0,
        o[0], o[1], o[2], 1.0,
    ]
    return _row_affine(matrix, "BODY pose row matrix")


def compose_body0_pose_to_vhf_world_matrix(
    vhf_bind_row: Sequence[float],
    body0_bind_row: Sequence[float],
    origin: Sequence[float],
    basis: Sequence[float],
) -> list[float]:
    """Compose object->root, inverse(BODY0->root), BODY0->world in row order."""
    vhf = _row_affine(vhf_bind_row, "VHF body bind matrix")
    body_bind_inverse = _inverse_affine_row(body0_bind_row, "BODY0 bind matrix")
    body_world = body_pose_row_matrix(origin, basis)
    result = _mul4(_mul4(vhf, body_bind_inverse), body_world)
    return _row_affine(result, "dynamic BMW world matrix")


def _validate_global_identity(report: Mapping[str, Any]) -> bool:
    identity = report.get("identity_join") or {}
    handoff = report.get("handoff") or {}
    scope = report.get("scope") or {}
    _require(identity.get("main_chassis_BODY_selected") is True, "BMW chassis BODY is not selected")
    _require(identity.get("main_chassis_BODY_name") == BODY_NAME, "BMW chassis BODY name drift")
    _require(_int(identity.get("main_chassis_BODY_index")) == BODY_INDEX, "BMW chassis BODY index drift")
    _require(_int(identity.get("global_vehicle_address")) == GLOBAL_VEHICLE_ADDRESS, "global vehicle address drift")
    _require(handoff.get("phase703_update_child_equality_gate_required") is False, "obsolete update-child gate was reintroduced")
    _require(handoff.get("vehicle_world_transform_ready") is False, "upstream identity preclaims vehicle world transform")
    _require(scope.get("dynamic_BODY_pose_to_VHF_composition_proven") is False, "upstream identity preclaims BODY/VHF composition")

    flags = [
        handoff.get("outer_receiver_to_BODY_owner_continuity_proven"),
        handoff.get("vehicle_BODY_selection_ready"),
        handoff.get("phase698_positive_selection_admissible"),
        handoff.get("phase700_runtime_handoff_admissible"),
        handoff.get("phase703_gate_rewrite_ready"),
    ]
    if any(not isinstance(value, bool) for value in flags):
        raise ValueError("global BODY-owner readiness flags are missing")
    _require(len(set(flags)) == 1, "global BODY-owner readiness flags disagree")
    ready = bool(flags[0])
    selected = handoff.get("selected_BODY_index")
    if ready:
        _require(_int(selected) == BODY_INDEX, "positive BODY-owner identity did not select BODY 0")
    else:
        _require(selected is None, "blocked BODY-owner identity preclaims a BODY index")
    return ready


def _validate_vhf(report: Mapping[str, Any]) -> list[float]:
    _require(report.get("ready") is True and report.get("status") == "ready", "VHF transform is not ready")
    boundary = report.get("boundary") or {}
    _require(boundary.get("canonical_body_meb_identity_proven") is True, "canonical BMW body MEB identity is not proven")
    _require(boundary.get("vhf_object_transform_proven") is True, "VHF body object transform is not proven")
    _require(boundary.get("body_physics_pose_consumed") is False, "VHF input already claims physics pose consumption")
    _require(boundary.get("body_local_to_meb_object_bind_proven") is False, "VHF input preclaims BODY/MEB bind proof")
    convention = report.get("convention") or {}
    _require(convention.get("target") == "SVWT row-major D3D row-vector", "VHF target convention drift")
    _require(convention.get("operation") == "exact 4x4 transpose", "VHF conversion operation drift")
    return _row_affine(report.get("world_matrix"), "Phase 645 VHF world matrix")


def _validate_bind_proof(report: Mapping[str, Any]) -> list[float]:
    _require(report.get("ready") is True and report.get("status") == "ready", "BODY0 bind proof is not ready")
    _require(report.get("evidence_state") == "proven-static", "BODY0 bind proof is not proven-static")
    _require(_int(report.get("body_index")) == BODY_INDEX, "BODY0 bind proof index drift")
    _require(report.get("body_name") == BODY_NAME, "BODY0 bind proof name drift")
    _require(report.get("frame_relation") == FRAME_RELATION, "BODY0 bind frame relation drift")
    _require(report.get("matrix_convention") == ROW_CONVENTION, "BODY0 bind matrix convention drift")
    provenance = report.get("provenance") or {}
    targets = provenance.get("source_targets")
    _require(isinstance(targets, list) and targets and all(isinstance(x, str) and x for x in targets), "BODY0 bind proof has no static source targets")
    scope = report.get("scope") or {}
    _require(scope.get("identity_matrix_assumed") is False, "BODY0 bind proof was produced by identity assumption")
    _require(scope.get("original_game_executed") is False, "BODY0 bind proof requires original game execution")
    _require(scope.get("new_runtime_capture_used") is False, "BODY0 bind proof uses new runtime capture")
    return _row_affine(report.get("body0_local_to_vhf_vehicle_root_row_matrix"), "BODY0 bind matrix")


def build_bmw_body0_vhf_bind_frame_frontier(
    global_identity_path: Path,
    vhf_transform_path: Path,
    bind_proof_path: Path | None = None,
) -> dict[str, Any]:
    global_identity = _load(global_identity_path, GLOBAL_IDENTITY_FORMAT)
    vhf = _load(vhf_transform_path, VHF_FORMAT)
    body_owner_ready = _validate_global_identity(global_identity)
    vhf_matrix = _validate_vhf(vhf)

    bind_matrix: list[float] | None = None
    bind_ready = False
    if bind_proof_path is not None:
        bind = _load(bind_proof_path, BIND_PROOF_FORMAT)
        bind_matrix = _validate_bind_proof(bind)
        bind_ready = True

    producer_ready = body_owner_ready and bind_ready
    blockers: list[dict[str, Any]] = []
    if not body_owner_ready:
        blockers.append({
            "id": "retail-BODY0-pose-admission",
            "evidence_state": "blocked",
            "required_contract": GLOBAL_IDENTITY_FORMAT,
            "required_result": "phase700_runtime_handoff_admissible=true",
        })
    if not bind_ready:
        blockers.append({
            "id": "body0-bind-frame-provenance-not-proven",
            "evidence_state": "unknown",
            "required_contract": BIND_PROOF_FORMAT,
            "required_relation": FRAME_RELATION,
            "required_evidence": "static/source-backed initialization writer provenance into persistent BODY0 origin+basis",
        })

    return {
        "format": FORMAT,
        "inputs": {
            "global_vehicle_BODY_owner_identity": str(global_identity_path),
            "phase645_VHF_body_world_transform": str(vhf_transform_path),
            "BODY0_bind_frame_proof": None if bind_proof_path is None else str(bind_proof_path),
        },
        "proven_conventions": {
            "BODY_basis_memory_order": "+0xd4..+0xf4 row-major B",
            "BODY_column_equation": "world_offset_column = B * local_column",
            "BODY_origin_offsets": ["+0x00", "+0x08", "+0x10"],
            "BODY_pose_to_D3D_row_operation": "exact homogeneous transpose",
            "VHF_bind_matrix_convention": ROW_CONVENTION,
            "phase646_transport_matrix_convention": ROW_CONVENTION,
        },
        "composition": {
            "row_vector_equation": "M_object_world = M_vhf_bind * inverse(M_BODY0_bind) * M_BODY0_runtime",
            "column_vector_equation": "M_object_world_col = M_BODY0_runtime_col * inverse(M_BODY0_bind_col) * M_vhf_bind_col",
            "formula_ready": True,
            "BODY0_bind_frame_proven": bind_ready,
            "BODY0_bind_matrix": bind_matrix,
            "phase645_VHF_bind_matrix": vhf_matrix,
            "retail_BODY0_pose_admission_ready": body_owner_ready,
            "dynamic_world_matrix_producer_ready": producer_ready,
            "evidence_state": "proven-composition-contract" if producer_ready else "blocked",
        },
        "next_static_targets": [] if bind_ready else list(STATIC_TARGETS),
        "blockers": blockers,
        "handoff": {
            "BODY0_pose_to_VHF_world_matrix_formula_ready": True,
            "BODY0_bind_frame_proven": bind_ready,
            "phase700_BODY0_pose_admission_ready": body_owner_ready,
            "phase646_world_matrix_producer_ready": producer_ready,
            "vehicle_world_transform_ready": producer_ready,
            "camera_follow_target_ready": producer_ready,
            "critical_next_join": (
                "camera follows proven dynamic vehicle world transform"
                if producer_ready
                else "BODY0 local bind frame -> Phase 645 VHF vehicle-root frame"
                if body_owner_ready
                else "positive retail FUN_00765470 BODY-owner receiver proof and BODY0 bind-frame proof"
            ),
        },
        "scope": {
            "BODY0_bind_matrix_identity_assumed": False,
            "BODY0_local_equals_MEB_local_assumed": False,
            "axis_remap_assumed": False,
            "matching_offsets_used_as_frame_identity": False,
            "synthetic_positive_bind_is_retail_proof": False,
            "native_renderer_transport_reimplemented": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("global_vehicle_BODY_owner_identity", type=Path)
    parser.add_argument("phase645_VHF_body_world_transform", type=Path)
    parser.add_argument("--bind-proof", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = build_bmw_body0_vhf_bind_frame_frontier(
        args.global_vehicle_BODY_owner_identity,
        args.phase645_VHF_body_world_transform,
        args.bind_proof,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
