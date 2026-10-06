"""Strict Process 2 consumer for the positive BMW VHF hierarchy-root frame stage.

This module consumes ``SHIFT.BMWVHFHierarchyRootFrame/1`` without adjudicating
or inventing the still-unresolved outer Vehicle -> VHF root relation.  It is a
narrow staging adaptor for the final BODY0 bind path: exact resource/root
identity, MatrixNumber, parent-chain and row-vector metadata are validated and
projected into a typed Process 2 contract while every downstream semantic
admission gate remains fail-closed.
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

UPSTREAM_FORMAT = "SHIFT.BMWVHFHierarchyRootFrame/1"
FORMAT = "SHIFT.Process2BMWVHFHierarchyRootFrameStage/1"
RESOURCE_JOIN_FORMAT = "SHIFT.BMWVehicleRenderModelResourceJoin/1"
VEHICLE_NAME = "BMW_M3_E36"
CANONICAL_VHF = "vehicles/bmw_m3_e36/bmw_m3_e36.vhf"
ROOT_NODE_NAME = "Root"
ROOT_NODE_PATH = "CAR[BMW_M3_E36]/NODE[HIERARCHY:Root]"
SOURCE_CONVENTION = "VHF row-major column-vector hierarchy"
COMPOSITION_CONVENTION = "world = parent_world * local"
ROW_VECTOR_CONVERSION = "exact 4x4 transpose"

_REQUIRED_PROVENANCE_TRUE = (
    "vehicle_render_hierarchy_resource_owner_join_ready",
    "canonical_BMW_VHF_resource_identity_revalidated",
    "decoded_payload_sha256_matches_resource_join",
    "unique_direct_HIERARCHY_root_ready",
    "exact_root_node_name_ready",
    "exact_root_MatrixNumber_ready",
    "exact_root_MATRIX_record_ready",
    "exact_root_parent_chain_ready",
    "exact_root_affine_matrix_ready",
)

_REQUIRED_HANDOFF_FALSE = (
    "outer_vehicle_root_to_VHF_vehicle_root_ready",
    "outer_vehicle_root_to_VHF_fixed_affine_delta_ready",
    "BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready",
    "BODY0_bind_frame_proof_ready",
    "vehicle_world_transform_ready",
)

_REQUIRED_LIMITS_FALSE = (
    "resource_identity_is_frame_identity",
    "root_identity_matrix_implies_outer_vehicle_identity",
    "equal_numeric_values_are_provenance",
    "callgraph_adjacency_is_ownership",
    "visual_similarity_is_frame_identity",
    "dynamic_outer_vehicle_pose_consumed",
    "BODY0_bind_frame_claimed",
    "runtime_capture_required",
    "original_game_executed",
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    _require(isinstance(value, Mapping), f"{label} is missing")
    return value


def _normalized_path(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip("/").lower()


def _finite_vector(value: Any, count: int, label: str) -> tuple[float, ...]:
    _require(
        isinstance(value, Sequence) and not isinstance(value, (str, bytes)),
        f"{label} must be a numeric sequence",
    )
    _require(len(value) == count, f"{label} must contain exactly {count} scalars")
    out: list[float] = []
    for item in value:
        _require(
            not isinstance(item, bool) and isinstance(item, (int, float)),
            f"{label} contains a non-numeric value",
        )
        number = float(item)
        _require(math.isfinite(number), f"{label} contains a non-finite value")
        out.append(number)
    return tuple(out)


def _matrix(value: Any, label: str) -> tuple[float, ...]:
    return _finite_vector(value, 16, label)


def _transpose4(matrix: Sequence[float]) -> tuple[float, ...]:
    return tuple(float(matrix[column * 4 + row]) for row in range(4) for column in range(4))


def _same_matrix(lhs: Sequence[float], rhs: Sequence[float], tolerance: float = 1.0e-9) -> bool:
    return len(lhs) == len(rhs) and all(
        abs(float(a) - float(b)) <= tolerance for a, b in zip(lhs, rhs)
    )


def _is_identity(matrix: Sequence[float], tolerance: float = 1.0e-9) -> bool:
    identity = (
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    )
    return _same_matrix(matrix, identity, tolerance)


def _validate_column_affine(matrix: Sequence[float], label: str) -> None:
    _require(
        all(abs(float(matrix[index])) <= 1.0e-9 for index in (12, 13, 14)),
        f"{label} is not a VHF column-vector affine matrix",
    )
    _require(abs(float(matrix[15]) - 1.0) <= 1.0e-9, f"{label} homogeneous component drift")


def _validate_row_affine(matrix: Sequence[float], label: str) -> None:
    _require(
        all(abs(float(matrix[index])) <= 1.0e-9 for index in (3, 7, 11)),
        f"{label} is not a D3D row-vector affine matrix",
    )
    _require(abs(float(matrix[15]) - 1.0) <= 1.0e-9, f"{label} homogeneous component drift")


def _validate_sha256(value: Any, label: str) -> str:
    text = str(value or "").lower()
    _require(len(text) == 64 and all(ch in "0123456789abcdef" for ch in text), f"{label} invalid")
    return text


def _validate_parent_chain(frame: Mapping[str, Any], matrix_number: str) -> tuple[str, ...]:
    raw_chain = frame.get("matrix_parent_chain")
    _require(isinstance(raw_chain, list) and bool(raw_chain), "VHF root matrix parent chain is missing")

    ids: list[str] = []
    terminal_local: tuple[float, ...] | None = None
    terminal_offset: tuple[float, ...] | None = None
    terminal_orientation: tuple[float, ...] | None = None
    for index, raw_row in enumerate(raw_chain):
        row = _mapping(raw_row, f"VHF root parent-chain row {index}")
        matrix_id = str(row.get("matrix_id") or "")
        _require(bool(matrix_id), f"VHF root parent-chain row {index} has no matrix_id")
        _require(matrix_id not in ids, "VHF root matrix parent chain contains a cycle/duplicate")
        parent = row.get("parent")
        if index == 0:
            _require(parent is None, "VHF root parent-chain first row must be parentless")
        else:
            _require(str(parent) == ids[-1], "VHF root parent-chain linkage drift")

        offset = _finite_vector(row.get("offset_xyz"), 3, f"MATRIX {matrix_id} offset")
        orientation = _finite_vector(
            row.get("orientation_xyzw"), 4, f"MATRIX {matrix_id} orientation"
        )
        local = _matrix(row.get("local_matrix_column_vector"), f"MATRIX {matrix_id} local matrix")
        _validate_column_affine(local, f"MATRIX {matrix_id} local matrix")
        ids.append(matrix_id)
        terminal_local = local
        terminal_offset = offset
        terminal_orientation = orientation

    _require(ids[-1] == matrix_number, "VHF root MatrixNumber disagrees with parent-chain terminal id")
    raw_ids = frame.get("matrix_parent_chain_ids")
    _require(
        isinstance(raw_ids, list) and [str(value) for value in raw_ids] == ids,
        "VHF root matrix_parent_chain_ids drift",
    )

    local_column = _matrix(frame.get("local_matrix_column_vector"), "VHF root local column matrix")
    _require(terminal_local is not None and _same_matrix(local_column, terminal_local), "VHF root local matrix disagrees with terminal MATRIX record")
    _require(
        terminal_offset is not None
        and _same_matrix(_finite_vector(frame.get("local_offset_xyz"), 3, "VHF root local offset"), terminal_offset),
        "VHF root local offset disagrees with terminal MATRIX record",
    )
    _require(
        terminal_orientation is not None
        and _same_matrix(
            _finite_vector(frame.get("local_orientation_xyzw"), 4, "VHF root local orientation"),
            terminal_orientation,
        ),
        "VHF root local orientation disagrees with terminal MATRIX record",
    )
    return tuple(ids)


def consume_root_frame_stage(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and project one already-positive Process 1 root-frame artifact."""

    _require(value.get("format") == UPSTREAM_FORMAT, f"expected {UPSTREAM_FORMAT}")
    _require(value.get("version") == 1, "BMW VHF root-frame version drift")
    _require(value.get("ready") is True, "BMW VHF root-frame stage is not ready")
    _require(
        value.get("status") == "canonical-bmw-vhf-hierarchy-root-frame-proven",
        "BMW VHF root-frame status is not proven",
    )

    input_contract = _mapping(value.get("INPUT"), "BMW VHF root-frame INPUT")
    _require(input_contract.get("resource_join") == RESOURCE_JOIN_FORMAT, "BMW VHF resource-join contract drift")
    _require(
        _normalized_path(input_contract.get("canonical_vhf")) == _normalized_path(CANONICAL_VHF),
        "canonical BMW VHF INPUT path drift",
    )

    source = _mapping(value.get("source"), "BMW VHF root-frame source")
    _require(source.get("resource_join_format") == RESOURCE_JOIN_FORMAT, "BMW VHF source resource-join drift")
    _require(
        _normalized_path(source.get("resolved_path")) == _normalized_path(CANONICAL_VHF),
        "canonical BMW VHF source path drift",
    )
    decoded_sha256 = _validate_sha256(source.get("decoded_sha256"), "BMW VHF decoded SHA-256")
    _require(isinstance(source.get("entry_index"), int) and source["entry_index"] >= 0, "BMW VHF archive entry index missing")
    _require(isinstance(source.get("decoded_size"), int) and source["decoded_size"] > 0, "BMW VHF decoded size missing")

    frame = _mapping(value.get("vehicle_root_frame"), "BMW VHF vehicle_root_frame")
    _require(frame.get("car_tag") == "CAR", "BMW VHF root CAR tag drift")
    _require(frame.get("car_name") == VEHICLE_NAME, "BMW VHF root CAR identity drift")
    _require(str(frame.get("node_type") or "").upper() == "HIERARCHY", "BMW VHF root node type drift")
    _require(frame.get("node_name") == ROOT_NODE_NAME, "BMW VHF root node name drift")
    _require(frame.get("node_path") == ROOT_NODE_PATH, "BMW VHF root node path drift")
    matrix_number = str(frame.get("matrix_number") or "")
    _require(bool(matrix_number), "BMW VHF root MatrixNumber missing")
    _require(frame.get("matrix_record_present") is True, "BMW VHF root MATRIX record not proven present")
    parent_chain_ids = _validate_parent_chain(frame, matrix_number)

    convention = _mapping(frame.get("convention"), "BMW VHF root matrix convention")
    _require(convention.get("source") == SOURCE_CONVENTION, "BMW VHF source matrix convention drift")
    _require(convention.get("composition") == COMPOSITION_CONVENTION, "BMW VHF matrix composition convention drift")
    _require(convention.get("row_vector_conversion") == ROW_VECTOR_CONVERSION, "BMW VHF row-vector conversion drift")

    local_column = _matrix(frame.get("local_matrix_column_vector"), "BMW VHF root local column matrix")
    local_row = _matrix(frame.get("local_matrix_row_vector"), "BMW VHF root local row matrix")
    world_column = _matrix(frame.get("world_matrix_column_vector"), "BMW VHF root world column matrix")
    world_row = _matrix(frame.get("world_matrix_row_vector"), "BMW VHF root world row matrix")
    _validate_column_affine(local_column, "BMW VHF root local column matrix")
    _validate_column_affine(world_column, "BMW VHF root world column matrix")
    _validate_row_affine(local_row, "BMW VHF root local row matrix")
    _validate_row_affine(world_row, "BMW VHF root world row matrix")
    _require(_same_matrix(local_row, _transpose4(local_column)), "BMW VHF root local row matrix is not the exact transpose")
    _require(_same_matrix(world_row, _transpose4(world_column)), "BMW VHF root world row matrix is not the exact transpose")
    _require(frame.get("local_matrix_is_identity") is _is_identity(local_column), "BMW VHF root local identity flag drift")
    _require(frame.get("world_matrix_is_identity") is _is_identity(world_column), "BMW VHF root world identity flag drift")

    provenance = _mapping(value.get("provenance"), "BMW VHF root-frame provenance")
    for gate in _REQUIRED_PROVENANCE_TRUE:
        _require(provenance.get(gate) is True, f"BMW VHF root-frame provenance gate not ready: {gate}")

    handoff = _mapping(value.get("handoff"), "BMW VHF root-frame handoff")
    _require(handoff.get("canonical_BMW_VHF_hierarchy_root_frame_ready") is True, "BMW VHF hierarchy root-frame gate not ready")
    _require(handoff.get("canonical_BMW_VHF_hierarchy_root_matrix_ready") is True, "BMW VHF hierarchy root-matrix gate not ready")
    for gate in _REQUIRED_HANDOFF_FALSE:
        _require(handoff.get(gate) is False, f"upstream root-frame stage illegally preclaims {gate}")

    limits = _mapping(value.get("limits"), "BMW VHF root-frame limits")
    for gate in _REQUIRED_LIMITS_FALSE:
        _require(limits.get(gate) is False, f"BMW VHF root-frame limit drift: {gate}")

    return {
        "format": FORMAT,
        "version": 1,
        "status": "exact-vhf-root-frame-stage-consumed",
        "ready": True,
        "source_contract": UPSTREAM_FORMAT,
        "resource_contract": RESOURCE_JOIN_FORMAT,
        "subject": {
            "canonical_vhf": CANONICAL_VHF,
            "decoded_sha256": decoded_sha256,
            "car_name": VEHICLE_NAME,
            "root_node_path": ROOT_NODE_PATH,
            "matrix_number": matrix_number,
            "matrix_parent_chain_ids": list(parent_chain_ids),
            "local_matrix_row_vector": list(local_row),
            "world_matrix_row_vector": list(world_row),
            "matrix_convention": "row-major D3D row-vector affine via exact transpose",
        },
        "handoff": {
            "exact_bmw_vhf_resource_identity_consumed": True,
            "exact_bmw_vhf_hierarchy_root_frame_consumed": True,
            "exact_bmw_vhf_hierarchy_root_matrix_consumed": True,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": False,
            "BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
            "retail_world_transform_admitted": False,
        },
        "limits": {
            "outer_vehicle_relation_adjudicated": False,
            "candidate_matrix_promoted": False,
            "identity_root_matrix_used_as_outer_relation": False,
            "final_bind_packet_admitted": False,
            "host_development_cadence_is_retail_evidence": False,
        },
    }


def contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "input": UPSTREAM_FORMAT,
        "retail_subject": CANONICAL_VHF,
        "validation": [
            "exact BMW CAR/HIERARCHY Root identity",
            "MatrixNumber and exact parent-chain continuity",
            "source row-major column-vector hierarchy convention",
            "exact row-vector transpose for local/world matrices",
            "all unresolved outer Vehicle/final bind gates remain false",
        ],
        "outer_vehicle_relation_ready": False,
        "BODY0_bind_frame_proof_ready": False,
        "retail_world_transform_admitted": False,
        "scheduler_authority_contract": "SHIFT.Process2RuntimeSchedulerAuthority/1",
        "host_1_60_is_retail_evidence": False,
    }
