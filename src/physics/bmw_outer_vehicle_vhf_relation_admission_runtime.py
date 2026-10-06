"""Strict Process 2 seam for a future positive outer Vehicle -> BMW VHF relation.

Process 1 has not yet published the final relation artifact or its concrete
format.  This module therefore does not guess that schema and cannot adapt a
frontier/candidate directly.  Instead it defines a small Process 2 normalized
claim that an exact upstream-format adaptor may populate once Process 1 commits
the semantic proof.

The seam validates the already-consumed canonical VHF root identity, explicit
Process 1 semantic authority, exact row-vector affine metadata and relation-kind
consistency.  It deliberately stops before BODY0 bind-proof/world-transform
admission.
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.Process2BMWOuterVehicleVHFRelationAdmission/1"
NORMALIZED_CLAIM_FORMAT = "SHIFT.Process2BMWOuterVehicleVHFRelationClaim/1"
ROOT_STAGE_FORMAT = "SHIFT.Process2BMWVHFHierarchyRootFrameStage/1"
CANONICAL_VHF = "vehicles/bmw_m3_e36/bmw_m3_e36.vhf"
OUTER_FRAME = "outer_vehicle_root"
VHF_ROOT_FRAME = "canonical_bmw_vhf_hierarchy_root"
ROW_VECTOR_CONVENTION = "row-major D3D row-vector affine"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    _require(isinstance(value, Mapping), f"{label} is missing")
    return value


def _finite_matrix(value: Any, label: str) -> tuple[float, ...]:
    _require(
        isinstance(value, Sequence) and not isinstance(value, (str, bytes)),
        f"{label} must be a numeric sequence",
    )
    _require(len(value) == 16, f"{label} must contain exactly 16 scalars")
    matrix: list[float] = []
    for item in value:
        _require(
            not isinstance(item, bool) and isinstance(item, (int, float)),
            f"{label} contains a non-numeric scalar",
        )
        number = float(item)
        _require(math.isfinite(number), f"{label} contains a non-finite scalar")
        matrix.append(number)
    return tuple(matrix)


def _validate_row_affine(matrix: Sequence[float], label: str) -> None:
    _require(
        all(abs(float(matrix[index])) <= 1.0e-9 for index in (3, 7, 11)),
        f"{label} is not row-vector affine",
    )
    _require(abs(float(matrix[15]) - 1.0) <= 1.0e-9, f"{label} homogeneous component drift")


def _is_identity(matrix: Sequence[float], tolerance: float = 1.0e-9) -> bool:
    expected = (
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    )
    return all(abs(float(a) - b) <= tolerance for a, b in zip(matrix, expected))


def _validate_sha256(value: Any, label: str) -> str:
    text = str(value or "").lower()
    _require(len(text) == 64 and all(ch in "0123456789abcdef" for ch in text), f"{label} invalid")
    return text


def _root_subject(root_stage: Mapping[str, Any]) -> dict[str, Any]:
    _require(root_stage.get("format") == ROOT_STAGE_FORMAT, f"expected {ROOT_STAGE_FORMAT}")
    _require(root_stage.get("version") == 1, "VHF root-stage version drift")
    _require(root_stage.get("ready") is True, "VHF root stage is not ready")
    _require(root_stage.get("status") == "exact-vhf-root-frame-stage-consumed", "VHF root stage not consumed")

    handoff = _mapping(root_stage.get("handoff"), "VHF root-stage handoff")
    _require(handoff.get("exact_bmw_vhf_resource_identity_consumed") is True, "exact BMW VHF resource identity not consumed")
    _require(handoff.get("exact_bmw_vhf_hierarchy_root_frame_consumed") is True, "exact BMW VHF root frame not consumed")
    _require(handoff.get("exact_bmw_vhf_hierarchy_root_matrix_consumed") is True, "exact BMW VHF root matrix not consumed")
    _require(handoff.get("outer_vehicle_root_to_VHF_vehicle_root_ready") is False, "root stage illegally preclaims outer relation")
    _require(handoff.get("BODY0_bind_frame_proof_ready") is False, "root stage illegally preclaims final bind proof")
    _require(handoff.get("vehicle_world_transform_ready") is False, "root stage illegally preclaims world transform")
    _require(handoff.get("retail_world_transform_admitted") is False, "root stage illegally admits retail world transform")

    subject = _mapping(root_stage.get("subject"), "VHF root-stage subject")
    canonical_vhf = str(subject.get("canonical_vhf") or "").replace("\\", "/").strip("/").lower()
    _require(canonical_vhf == CANONICAL_VHF, "canonical BMW VHF subject drift")
    decoded_sha256 = _validate_sha256(subject.get("decoded_sha256"), "BMW VHF decoded SHA-256")
    _require(subject.get("car_name") == "BMW_M3_E36", "BMW VHF CAR identity drift")
    node_path = str(subject.get("root_node_path") or "")
    _require(node_path == "CAR[BMW_M3_E36]/NODE[HIERARCHY:Root]", "BMW VHF root node path drift")
    matrix_number = str(subject.get("matrix_number") or "")
    _require(bool(matrix_number), "BMW VHF root MatrixNumber missing")
    raw_chain = subject.get("matrix_parent_chain_ids")
    _require(isinstance(raw_chain, list) and bool(raw_chain), "BMW VHF root parent-chain ids missing")
    chain = [str(value) for value in raw_chain]
    _require(chain[-1] == matrix_number, "BMW VHF root parent-chain terminal MatrixNumber drift")
    _finite_matrix(subject.get("world_matrix_row_vector"), "BMW VHF root world row matrix")
    _require(
        subject.get("matrix_convention") == "row-major D3D row-vector affine via exact transpose",
        "BMW VHF root-stage matrix convention drift",
    )
    return {
        "canonical_vhf": CANONICAL_VHF,
        "decoded_sha256": decoded_sha256,
        "car_name": "BMW_M3_E36",
        "root_node_path": node_path,
        "matrix_number": matrix_number,
        "matrix_parent_chain_ids": chain,
    }


def admission_requirements(root_stage: Mapping[str, Any]) -> dict[str, Any]:
    """Freeze P2 requirements without inventing the missing Process 1 format."""

    subject = _root_subject(root_stage)
    return {
        "format": FORMAT,
        "version": 1,
        "status": "relation-upstream-format-unbound",
        "ready": False,
        "root_subject": subject,
        "normalized_claim_format": NORMALIZED_CLAIM_FORMAT,
        "required_relation_semantics": {
            "semantic_authority": "Process 1",
            "source_frame": OUTER_FRAME,
            "target_frame": VHF_ROOT_FRAME,
            "relation_kind_domain": ["identity", "fixed_affine"],
            "matrix_convention": ROW_VECTOR_CONVENTION,
            "source_backed_relation_proof_ready": True,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": True,
            "relation_matrix_numeric_ready": True,
        },
        "upstream_relation_contract_bound": False,
        "candidate_or_frontier_admission_allowed": False,
        "identity_from_equal_numeric_matrix_allowed": False,
        "final_BODY0_bind_admission_ready": False,
        "retail_vehicle_world_transform_admission_ready": False,
    }


def admit_bound_relation_claim(
    root_stage: Mapping[str, Any],
    claim: Mapping[str, Any],
    *,
    expected_source_contract: str,
) -> dict[str, Any]:
    """Validate a P2-normalized claim bound to one exact future P1 contract.

    ``expected_source_contract`` must be supplied by the integration commit that
    consumes the future Process 1 artifact.  A frontier/candidate contract is
    explicitly rejected so this helper cannot be used to promote today's
    unresolved evidence.
    """

    subject = _root_subject(root_stage)
    expected_source_contract = str(expected_source_contract or "")
    _require(bool(expected_source_contract), "future Process 1 source contract is not bound")
    lowered = expected_source_contract.lower()
    _require("frontier" not in lowered and "candidate" not in lowered, "frontier/candidate contract cannot satisfy relation admission")
    _require(expected_source_contract.startswith("SHIFT."), "future Process 1 source contract must be explicit")

    _require(claim.get("format") == NORMALIZED_CLAIM_FORMAT, f"expected {NORMALIZED_CLAIM_FORMAT}")
    _require(claim.get("version") == 1, "relation claim version drift")
    _require(claim.get("ready") is True, "relation claim is not ready")
    _require(claim.get("source_contract") == expected_source_contract, "relation source contract mismatch")
    _require(claim.get("semantic_authority") == "Process 1", "relation semantic authority must remain Process 1")

    relation_subject = _mapping(claim.get("subject"), "relation subject")
    _require(relation_subject.get("source_frame") == OUTER_FRAME, "relation source frame drift")
    _require(relation_subject.get("target_frame") == VHF_ROOT_FRAME, "relation target frame drift")
    _require(
        str(relation_subject.get("canonical_vhf") or "").replace("\\", "/").strip("/").lower()
        == subject["canonical_vhf"],
        "relation canonical BMW VHF identity drift",
    )
    _require(
        _validate_sha256(relation_subject.get("decoded_sha256"), "relation BMW VHF decoded SHA-256")
        == subject["decoded_sha256"],
        "relation BMW VHF decoded identity drift",
    )
    _require(relation_subject.get("root_node_path") == subject["root_node_path"], "relation BMW VHF root node drift")
    _require(str(relation_subject.get("matrix_number") or "") == subject["matrix_number"], "relation BMW VHF MatrixNumber drift")
    _require(
        [str(value) for value in relation_subject.get("matrix_parent_chain_ids") or []]
        == subject["matrix_parent_chain_ids"],
        "relation BMW VHF parent-chain drift",
    )

    relation = _mapping(claim.get("relation"), "outer Vehicle/VHF relation")
    kind = str(relation.get("kind") or "")
    _require(kind in {"identity", "fixed_affine"}, "relation kind must be identity or fixed_affine")
    _require(relation.get("matrix_convention") == ROW_VECTOR_CONVENTION, "relation matrix convention drift")
    matrix = _finite_matrix(relation.get("row_vector_matrix"), "outer Vehicle/VHF relation row matrix")
    _validate_row_affine(matrix, "outer Vehicle/VHF relation row matrix")
    _require(relation.get("source_backed_relation_proof_ready") is True, "source-backed relation proof is not ready")
    _require(relation.get("outer_vehicle_root_to_VHF_vehicle_root_ready") is True, "outer Vehicle/VHF relation gate is not ready")
    _require(relation.get("relation_matrix_numeric_ready") is True, "outer Vehicle/VHF numeric relation matrix is not ready")

    if kind == "identity":
        _require(_is_identity(matrix), "identity relation must carry exact identity matrix")
        _require(relation.get("identity_semantics_explicitly_proven") is True, "identity relation lacks explicit semantic proof")
        _require(relation.get("fixed_affine_delta_ready") is False, "identity relation cannot preclaim a non-identity fixed delta")
    else:
        _require(relation.get("fixed_affine_delta_ready") is True, "fixed-affine relation gate is not ready")
        _require(relation.get("identity_semantics_explicitly_proven") is False, "fixed-affine relation cannot also claim identity semantics")

    downstream = _mapping(claim.get("downstream"), "relation downstream gates")
    _require(downstream.get("BODY0_bind_frame_proof_ready") is False, "relation stage must not preclaim final BODY0 bind proof")
    _require(downstream.get("vehicle_world_transform_ready") is False, "relation stage must not preclaim vehicle world transform")
    _require(downstream.get("retail_world_transform_admitted") is False, "relation stage must not admit retail world transform")

    return {
        "format": FORMAT,
        "version": 1,
        "status": "positive-outer-vehicle-vhf-relation-consumed",
        "ready": True,
        "source_contract": expected_source_contract,
        "semantic_authority": "Process 1",
        "subject": subject,
        "relation": {
            "kind": kind,
            "matrix_convention": ROW_VECTOR_CONVENTION,
            "row_vector_matrix": list(matrix),
            "source_backed_relation_proof_ready": True,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": True,
            "fixed_affine_delta_ready": kind == "fixed_affine",
            "identity_semantics_explicitly_proven": kind == "identity",
        },
        "handoff": {
            "outer_vehicle_root_to_VHF_vehicle_root_consumed": True,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
            "retail_world_transform_admitted": False,
        },
        "limits": {
            "relation_semantics_adjudicated_by_process2": False,
            "candidate_or_frontier_promoted": False,
            "equal_numeric_matrix_used_as_identity_proof": False,
            "BODY0_bind_matrix_composed_without_final_process1_proof": False,
        },
    }


def contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "root_stage_contract": ROOT_STAGE_FORMAT,
        "normalized_claim_format": NORMALIZED_CLAIM_FORMAT,
        "future_process1_relation_format": None,
        "future_process1_relation_format_must_be_bound_explicitly": True,
        "frontier_or_candidate_admission_allowed": False,
        "relation_kind_domain": ["identity", "fixed_affine"],
        "matrix_convention": ROW_VECTOR_CONVENTION,
        "BODY0_bind_frame_proof_ready": False,
        "retail_vehicle_world_transform_admitted": False,
    }


__all__ = [
    "FORMAT",
    "NORMALIZED_CLAIM_FORMAT",
    "ROOT_STAGE_FORMAT",
    "CANONICAL_VHF",
    "OUTER_FRAME",
    "VHF_ROOT_FRAME",
    "ROW_VECTOR_CONVENTION",
    "admission_requirements",
    "admit_bound_relation_claim",
    "contract",
]
