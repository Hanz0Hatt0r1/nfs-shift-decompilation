#!/usr/bin/env python3
"""Compose the exact outer Vehicle -> canonical BMW VHF HIERARCHY-root relation.

All frame/domain semantics consumed here are already independently proven:

* ``SHIFT.OuterVehicleRenderSnapshotAffineBridge/1`` proves
  ``P_model = P_outer + R_outer * delta_local`` and binds ``delta_local`` to
  outer Vehicle +0x19c/+0x1a0/+0x1a4 produced by FUN_00795d60;
* ``SHIFT.VehicleRenderModelRootAffineDomainJoin/1`` proves that the resulting
  participant affine is local->world for the same materialized Vehicle Render
  Model domain selected as the canonical BMW VHF;
* ``SHIFT.BMWVHFHierarchyRootFrame/1`` proves the exact canonical VHF HIERARCHY
  Root local->model-domain affine in the established D3D row-vector convention;
* ``SHIFT.OuterVehicleRenderRootDeltaProvenance/1`` proves exact entry-ECX store
  and value-root provenance for the three delta fields.

The only still-missing value input is a separate source-backed numeric resolution
of those exact terminal roots.  This composer therefore refuses arbitrary XYZ
arguments.  It accepts only ``SHIFT.OuterVehicleRenderRootDeltaNumeric/1`` bound
by canonical JSON SHA-256 to the exact delta-provenance artifact.

For D3D row vectors, let:

    O = outer Vehicle root local -> world
    D = translation(delta_local)
    H = VHF HIERARCHY Root local -> Vehicle Render Model domain

The proven bridge/domain relation is model_domain->world = D * O, therefore
VHF_root->world = H * D * O and the coordinate transform from outer Vehicle root
to VHF root is exactly:

    M_outer_to_vhf = inverse(D) * inverse(H)

No identity relation is inferred from an identity-valued VHF matrix.  ``identity``
is emitted only if the complete source-backed composition above evaluates to the
identity matrix; otherwise the positive relation kind is ``fixed_affine``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.OuterVehicleVHFRootRelation/1"
BRIDGE_FORMAT = "SHIFT.OuterVehicleRenderSnapshotAffineBridge/1"
DELTA_PROVENANCE_FORMAT = "SHIFT.OuterVehicleRenderRootDeltaProvenance/1"
NUMERIC_DELTA_FORMAT = "SHIFT.OuterVehicleRenderRootDeltaNumeric/1"
DOMAIN_FORMAT = "SHIFT.VehicleRenderModelRootAffineDomainJoin/1"
ROOT_FRAME_FORMAT = "SHIFT.BMWVHFHierarchyRootFrame/1"

PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
CANONICAL_VHF = "vehicles/bmw_m3_e36/bmw_m3_e36.vhf"
DECODED_VHF_SHA256 = "e08887d17d9e34e703a385260f41017fc19acbebc3405614b375e81766b4bd51"
TARGET_FUNCTION = "FUN_00795d60"
TARGET_ADDRESS = "0x00795d60"
TARGET_MNEMONIC_SHA256 = "c587cae5d3d8f99afed40fe0c059c8c60bc9cc45d9ee644f5e90e2e1f5a8eb14"
DELTA_OFFSETS = ["+0x19c", "+0x1a0", "+0x1a4"]
ROW_VECTOR_CONVENTION = "row-major D3D row-vector affine"
ROOT_NODE_PATH = "CAR[BMW_M3_E36]/NODE[HIERARCHY:Root]"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _load(value: str | Path | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return json.loads(json.dumps(dict(value)))
    path = Path(value)
    payload = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(payload, dict), f"{path}: expected JSON object")
    return payload


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            dict(value),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _finite_matrix16(value: Any, label: str) -> list[float]:
    _require(
        isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)),
        f"{label} must be a numeric sequence",
    )
    _require(len(value) == 16, f"{label} must contain exactly 16 scalars")
    result: list[float] = []
    for index, item in enumerate(value):
        _require(
            not isinstance(item, bool) and isinstance(item, (int, float)),
            f"{label}[{index}] is not numeric",
        )
        scalar = float(item)
        _require(math.isfinite(scalar), f"{label}[{index}] is not finite")
        result.append(scalar)
    return result


def _finite_xyz(value: Any, label: str) -> list[float]:
    _require(
        isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)),
        f"{label} must be a numeric sequence",
    )
    _require(len(value) == 3, f"{label} must contain exactly three scalars")
    result: list[float] = []
    for index, item in enumerate(value):
        _require(
            not isinstance(item, bool) and isinstance(item, (int, float)),
            f"{label}[{index}] is not numeric",
        )
        scalar = float(item)
        _require(math.isfinite(scalar), f"{label}[{index}] is not finite")
        result.append(scalar)
    return result


def _require_row_affine(matrix: Sequence[float], label: str) -> None:
    tolerance = 1.0e-9
    _require(
        all(abs(float(matrix[index])) <= tolerance for index in (3, 7, 11)),
        f"{label} is not D3D row-vector affine",
    )
    _require(
        abs(float(matrix[15]) - 1.0) <= tolerance,
        f"{label} homogeneous component drift",
    )


def _mat_mul(a: Sequence[float], b: Sequence[float]) -> list[float]:
    _require(len(a) == 16 and len(b) == 16, "matrix multiply requires 4x4 matrices")
    return [
        sum(float(a[row * 4 + k]) * float(b[k * 4 + col]) for k in range(4))
        for row in range(4)
        for col in range(4)
    ]


def _inverse3(matrix: Sequence[float], label: str) -> list[float]:
    a, b, c, d, e, f, g, h, i = (float(value) for value in matrix)
    det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    _require(math.isfinite(det) and abs(det) > 1.0e-12, f"{label} is singular")
    inv_det = 1.0 / det
    return [
        (e * i - f * h) * inv_det,
        (c * h - b * i) * inv_det,
        (b * f - c * e) * inv_det,
        (f * g - d * i) * inv_det,
        (a * i - c * g) * inv_det,
        (c * d - a * f) * inv_det,
        (d * h - e * g) * inv_det,
        (b * g - a * h) * inv_det,
        (a * e - b * d) * inv_det,
    ]


def _invert_row_affine(matrix: Sequence[float], label: str) -> list[float]:
    values = _finite_matrix16(matrix, label)
    _require_row_affine(values, label)
    linear = [
        values[0], values[1], values[2],
        values[4], values[5], values[6],
        values[8], values[9], values[10],
    ]
    inverse_linear = _inverse3(linear, label)
    tx, ty, tz = values[12], values[13], values[14]
    inverse_translation = [
        -(tx * inverse_linear[0] + ty * inverse_linear[3] + tz * inverse_linear[6]),
        -(tx * inverse_linear[1] + ty * inverse_linear[4] + tz * inverse_linear[7]),
        -(tx * inverse_linear[2] + ty * inverse_linear[5] + tz * inverse_linear[8]),
    ]
    return [
        inverse_linear[0], inverse_linear[1], inverse_linear[2], 0.0,
        inverse_linear[3], inverse_linear[4], inverse_linear[5], 0.0,
        inverse_linear[6], inverse_linear[7], inverse_linear[8], 0.0,
        inverse_translation[0], inverse_translation[1], inverse_translation[2], 1.0,
    ]


def _translation_matrix(xyz: Sequence[float]) -> list[float]:
    x, y, z = (float(value) for value in xyz)
    return [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        x, y, z, 1.0,
    ]


def _is_identity(matrix: Sequence[float], tolerance: float = 1.0e-9) -> bool:
    expected = [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    ]
    return all(abs(float(a) - b) <= tolerance for a, b in zip(matrix, expected))


def _validate_bridge(value: Mapping[str, Any]) -> dict[str, Any]:
    _require(value.get("format") == BRIDGE_FORMAT and value.get("ready") is True, f"expected ready {BRIDGE_FORMAT}")
    retail = value.get("retail") or {}
    _require(retail.get("program") == PROGRAM and retail.get("md5") == PE_MD5, "bridge retail identity drift")
    outer = value.get("outer_transform") or {}
    _require(outer.get("local_delta_has_concrete_setup_producer") is True, "bridge lacks concrete delta producer")
    _require(outer.get("local_delta_is_runtime_pose_source") is False, "static setup delta misclassified as runtime pose")
    _require(outer.get("render_root_local_delta_offsets") == DELTA_OFFSETS, "bridge delta field layout drift")
    relation = value.get("snapshot_relation") or {}
    _require(relation.get("translation_formula") == "P_snapshot = P_outer + R_outer * delta_local", "bridge affine formula drift")
    participant = value.get("render_participant_relation") or {}
    _require(participant.get("vehicle_render_model") == "participant+0x1340", "bridge render-model owner drift")
    _require(participant.get("world_affine_consumed_by") == "FUN_004a8c20", "bridge root-affine consumer drift")
    handoff = value.get("handoff") or {}
    _require(handoff.get("outer_vehicle_to_render_root_symbolic_affine_ready") is True, "bridge symbolic affine not ready")
    _require(handoff.get("render_root_translation_delta_producer_bounded") is True, "bridge delta producer not bounded")
    for gate in (
        "outer_vehicle_root_to_VHF_vehicle_root_ready",
        "outer_vehicle_root_to_VHF_fixed_affine_delta_ready",
        "BODY0_bind_frame_proof_ready",
        "vehicle_world_transform_ready",
    ):
        _require(handoff.get(gate) is False, f"bridge unexpectedly preclaims {gate}")
    return {
        "format": BRIDGE_FORMAT,
        "translation_formula": relation.get("translation_formula"),
        "delta_offsets": list(DELTA_OFFSETS),
        "participant_render_model": participant.get("vehicle_render_model"),
    }


def _validate_domain(value: Mapping[str, Any]) -> dict[str, Any]:
    _require(value.get("format") == DOMAIN_FORMAT and value.get("ready") is True, f"expected ready {DOMAIN_FORMAT}")
    retail = value.get("retail") or {}
    _require(retail.get("program") == PROGRAM and retail.get("md5") == PE_MD5, "domain join retail identity drift")
    domain = value.get("participant_domain") or {}
    _require(domain.get("canonical_bmw_vhf") == CANONICAL_VHF, "domain join canonical VHF drift")
    _require(domain.get("canonical_bmw_vhf_decoded_sha256") == DECODED_VHF_SHA256, "domain join decoded VHF SHA drift")
    _require(domain.get("vehicle_render_model_owner") == "participant+0x1340", "domain join render-model owner drift")
    _require(domain.get("root_world_affine_layout") == "row-major D3D row-vector affine; translation slots 12/13/14", "domain join affine layout drift")
    proof = value.get("proof") or {}
    _require(proof.get("vehicle_render_model_root_affine_domain_join_ready") is True, "vehicle render-model root affine domain is not ready")
    _require(proof.get("participant_root_affine_passed_to_same_render_model_owner") is True, "same render-model owner continuity not proven")
    _require(proof.get("render_model_local_points_transformed_by_participant_root_affine") is True, "model-domain affine consumption not proven")
    handoff = value.get("handoff") or {}
    for gate in (
        "outer_vehicle_root_to_VHF_vehicle_root_ready",
        "outer_vehicle_root_to_VHF_fixed_affine_delta_ready",
        "BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready",
        "BODY0_bind_frame_proof_ready",
        "vehicle_world_transform_ready",
    ):
        _require(handoff.get(gate) is False, f"domain join unexpectedly preclaims {gate}")
    return {
        "format": DOMAIN_FORMAT,
        "canonical_vhf": CANONICAL_VHF,
        "decoded_sha256": DECODED_VHF_SHA256,
        "render_model_owner": "participant+0x1340",
    }


def _validate_root_frame(value: Mapping[str, Any]) -> dict[str, Any]:
    _require(value.get("format") == ROOT_FRAME_FORMAT and value.get("ready") is True, f"expected ready {ROOT_FRAME_FORMAT}")
    source = value.get("source") or {}
    _require(str(source.get("resolved_path") or "").replace("\\", "/").lower() == CANONICAL_VHF, "root-frame canonical VHF drift")
    _require(str(source.get("decoded_sha256") or "").lower() == DECODED_VHF_SHA256, "root-frame decoded VHF SHA drift")
    frame = value.get("vehicle_root_frame") or {}
    _require(frame.get("node_path") == ROOT_NODE_PATH, "root-frame node path drift")
    matrix_number = str(frame.get("matrix_number") or "")
    _require(bool(matrix_number), "root-frame MatrixNumber missing")
    chain = frame.get("matrix_parent_chain_ids")
    _require(isinstance(chain, list) and bool(chain), "root-frame parent chain missing")
    normalized_chain = [str(item) for item in chain]
    _require(normalized_chain[-1] == matrix_number, "root-frame parent chain terminal drift")
    root_matrix = _finite_matrix16(frame.get("world_matrix_row_vector"), "VHF root world row matrix")
    _require_row_affine(root_matrix, "VHF root world row matrix")
    convention = frame.get("convention") or {}
    _require(convention.get("row_vector_conversion") == "exact 4x4 transpose", "root-frame row-vector convention drift")
    handoff = value.get("handoff") or {}
    _require(handoff.get("canonical_BMW_VHF_hierarchy_root_frame_ready") is True, "VHF hierarchy root frame not ready")
    _require(handoff.get("canonical_BMW_VHF_hierarchy_root_matrix_ready") is True, "VHF hierarchy root matrix not ready")
    for gate in (
        "outer_vehicle_root_to_VHF_vehicle_root_ready",
        "outer_vehicle_root_to_VHF_fixed_affine_delta_ready",
        "BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready",
        "BODY0_bind_frame_proof_ready",
        "vehicle_world_transform_ready",
    ):
        _require(handoff.get(gate) is False, f"root-frame artifact unexpectedly preclaims {gate}")
    return {
        "format": ROOT_FRAME_FORMAT,
        "canonical_vhf": CANONICAL_VHF,
        "decoded_sha256": DECODED_VHF_SHA256,
        "root_node_path": ROOT_NODE_PATH,
        "matrix_number": matrix_number,
        "matrix_parent_chain_ids": normalized_chain,
        "world_matrix_row_vector": root_matrix,
    }


def _validate_delta_provenance(value: Mapping[str, Any]) -> dict[str, Any]:
    _require(value.get("format") == DELTA_PROVENANCE_FORMAT and value.get("ready") is True, f"expected ready {DELTA_PROVENANCE_FORMAT}")
    retail = value.get("retail") or {}
    _require(retail.get("program") == PROGRAM and retail.get("md5") == PE_MD5, "delta provenance retail identity drift")
    function = retail.get("function") or {}
    _require(str(function.get("address") or "").lower() == TARGET_ADDRESS, "delta provenance target address drift")
    _require(function.get("name") == TARGET_FUNCTION, "delta provenance target function drift")
    _require(function.get("mnemonic_sha256") == TARGET_MNEMONIC_SHA256, "delta provenance function fingerprint drift")
    bridge = value.get("bridge_provenance") or {}
    _require(bridge.get("format") == BRIDGE_FORMAT, "delta provenance bridge contract drift")
    _require(bridge.get("translation_formula") == "P_snapshot = P_outer + R_outer * delta_local", "delta provenance affine formula drift")
    _require(bridge.get("render_root_local_delta_offsets") == DELTA_OFFSETS, "delta provenance field layout drift")
    handoff = value.get("handoff") or {}
    _require(handoff.get("render_root_delta_store_provenance_ready") is True, "delta STORE provenance not ready")
    _require(handoff.get("render_root_delta_value_roots_ready") is True, "delta value roots not ready")
    for gate in (
        "outer_vehicle_root_to_VHF_vehicle_root_ready",
        "outer_vehicle_root_to_VHF_fixed_affine_delta_ready",
        "BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready",
        "BODY0_bind_frame_proof_ready",
        "vehicle_world_transform_ready",
    ):
        _require(handoff.get(gate) is False, f"delta provenance unexpectedly preclaims {gate}")
    return {
        "format": DELTA_PROVENANCE_FORMAT,
        "canonical_sha256": _canonical_sha256(value),
        "target_function": TARGET_FUNCTION,
        "target_address": TARGET_ADDRESS,
        "field_offsets": list(DELTA_OFFSETS),
    }


def _validate_numeric_delta(
    value: Mapping[str, Any],
    delta_provenance: Mapping[str, Any],
) -> dict[str, Any]:
    _require(value.get("format") == NUMERIC_DELTA_FORMAT and value.get("ready") is True, f"expected ready {NUMERIC_DELTA_FORMAT}")
    _require(value.get("source_provenance_format") == DELTA_PROVENANCE_FORMAT, "numeric delta source format drift")
    expected_sha = _canonical_sha256(delta_provenance)
    _require(value.get("source_provenance_sha256") == expected_sha, "numeric delta is not bound to the exact delta-provenance artifact")
    target = value.get("target") or {}
    _require(str(target.get("function_address") or "").lower() == TARGET_ADDRESS, "numeric delta target address drift")
    _require(target.get("function_name") == TARGET_FUNCTION, "numeric delta target function drift")
    _require(target.get("mnemonic_sha256") == TARGET_MNEMONIC_SHA256, "numeric delta target function fingerprint drift")
    _require(target.get("field_offsets") == DELTA_OFFSETS, "numeric delta field layout drift")
    xyz = _finite_xyz(value.get("xyz"), "render-root delta xyz")
    proof = value.get("proof") or {}
    _require(proof.get("source_backed_terminal_roots_resolved") is True, "numeric delta terminal roots are not source-backed resolved")
    _require(proof.get("numeric_delta_value_proven") is True, "numeric delta value is not proven")
    _require(proof.get("runtime_capture_used") is False, "numeric delta may not depend on a new runtime capture")
    _require(proof.get("original_game_executed") is False, "numeric delta may not depend on original-game execution")
    _require(proof.get("synthetic_test_values_are_retail_evidence") is False, "synthetic values cannot be retail delta evidence")
    return {
        "format": NUMERIC_DELTA_FORMAT,
        "source_provenance_sha256": expected_sha,
        "xyz": xyz,
        "source_backed_terminal_roots_resolved": True,
        "numeric_delta_value_proven": True,
    }


def build_outer_vehicle_vhf_root_relation(
    bridge: str | Path | Mapping[str, Any],
    delta_provenance: str | Path | Mapping[str, Any],
    domain_join: str | Path | Mapping[str, Any],
    root_frame: str | Path | Mapping[str, Any],
    *,
    numeric_delta: str | Path | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the exact P1 relation when the final numeric delta proof is present."""

    bridge_value = _load(bridge)
    delta_value = _load(delta_provenance)
    domain_value = _load(domain_join)
    root_value = _load(root_frame)

    bridge_summary = _validate_bridge(bridge_value)
    delta_summary = _validate_delta_provenance(delta_value)
    domain_summary = _validate_domain(domain_value)
    root_summary = _validate_root_frame(root_value)

    base = {
        "format": FORMAT,
        "version": 1,
        "semantic_authority": "Process 1",
        "subject": {
            "source_frame": "outer_vehicle_root",
            "target_frame": "canonical_bmw_vhf_hierarchy_root",
            "canonical_vhf": CANONICAL_VHF,
            "decoded_sha256": DECODED_VHF_SHA256,
            "root_node_path": ROOT_NODE_PATH,
            "matrix_number": root_summary["matrix_number"],
            "matrix_parent_chain_ids": root_summary["matrix_parent_chain_ids"],
        },
        "inputs": {
            "affine_bridge": bridge_summary,
            "delta_provenance": delta_summary,
            "render_model_domain": domain_summary,
            "vhf_root_frame": root_summary,
        },
        "composition": {
            "row_vector_convention": ROW_VECTOR_CONVENTION,
            "model_domain_to_world": "D_delta * M_outer_world",
            "vhf_root_to_world": "M_vhf_root * D_delta * M_outer_world",
            "outer_vehicle_root_to_vhf_root": "inverse(D_delta) * inverse(M_vhf_root)",
            "multiplication_order_proven": True,
        },
        "limits": {
            "identity_inferred_from_vhf_root_identity_alone": False,
            "equal_numeric_values_used_as_semantic_proof": False,
            "visual_similarity_used_as_proof": False,
            "resource_identity_used_as_frame_identity": False,
            "runtime_capture_required": False,
            "original_game_execution_required": False,
            "static_vhf_frame_is_dynamic_vehicle_pose": False,
        },
    }

    if numeric_delta is None:
        return {
            **base,
            "status": "blocked-on-source-backed-render-root-delta-numeric-resolution",
            "ready": False,
            "blocking_reasons": [
                "outer-vhf-relation:SHIFT.OuterVehicleRenderRootDeltaNumeric/1-not-supplied"
            ],
            "required_numeric_delta_contract": {
                "format": NUMERIC_DELTA_FORMAT,
                "must_bind_source_provenance_sha256": delta_summary["canonical_sha256"],
                "must_resolve_exact_terminal_roots": True,
                "arbitrary_xyz_allowed": False,
            },
            "relation": None,
            "handoff": {
                "outer_vehicle_vhf_composition_formula_ready": True,
                "outer_vehicle_render_root_delta_numeric_ready": False,
                "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
                "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": False,
                "relation_matrix_numeric_ready": False,
                "BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready": False,
                "BODY0_bind_frame_proof_ready": False,
                "vehicle_world_transform_ready": False,
            },
        }

    numeric_value = _load(numeric_delta)
    numeric_summary = _validate_numeric_delta(numeric_value, delta_value)
    delta_matrix = _translation_matrix(numeric_summary["xyz"])
    inverse_delta = _invert_row_affine(delta_matrix, "render-root delta translation")
    inverse_root = _invert_row_affine(
        root_summary["world_matrix_row_vector"],
        "VHF root world row matrix",
    )
    relation_matrix = _mat_mul(inverse_delta, inverse_root)
    _require_row_affine(relation_matrix, "outer Vehicle -> VHF root relation")
    kind = "identity" if _is_identity(relation_matrix) else "fixed_affine"

    return {
        **base,
        "status": "outer-vehicle-to-canonical-bmw-vhf-root-relation-proven",
        "ready": True,
        "blocking_reasons": [],
        "numeric_delta": numeric_summary,
        "relation": {
            "kind": kind,
            "matrix_convention": ROW_VECTOR_CONVENTION,
            "row_vector_matrix": relation_matrix,
            "source_backed_relation_proof_ready": True,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": True,
            "relation_matrix_numeric_ready": True,
            "fixed_affine_delta_ready": kind == "fixed_affine",
            "identity_semantics_explicitly_proven": kind == "identity",
            "proof_equation": "inverse(T(delta_local)) * inverse(M_vhf_hierarchy_root)",
        },
        "handoff": {
            "outer_vehicle_vhf_composition_formula_ready": True,
            "outer_vehicle_render_root_delta_numeric_ready": True,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": True,
            "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": kind == "fixed_affine",
            "relation_matrix_numeric_ready": True,
            "BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
            "next_frontier": "compose target-session BODY0-local -> outer Vehicle-root numeric relation with this exact outer Vehicle-root -> VHF-root matrix and publish SHIFT.BMWBody0BindFrameProof/1",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bridge", type=Path)
    parser.add_argument("delta_provenance", type=Path)
    parser.add_argument("domain_join", type=Path)
    parser.add_argument("root_frame", type=Path)
    parser.add_argument("--numeric-delta", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)

    report = build_outer_vehicle_vhf_root_relation(
        args.bridge,
        args.delta_provenance,
        args.domain_join,
        args.root_frame,
        numeric_delta=args.numeric_delta,
    )
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
