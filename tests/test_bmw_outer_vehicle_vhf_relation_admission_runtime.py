from __future__ import annotations

import copy

import pytest

from src.physics import bmw_outer_vehicle_vhf_relation_admission_runtime as runtime


def _identity() -> list[float]:
    return [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    ]


def _translation(x: float, y: float, z: float) -> list[float]:
    return [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        x, y, z, 1.0,
    ]


def _root_stage() -> dict:
    return {
        "format": runtime.ROOT_STAGE_FORMAT,
        "version": 1,
        "status": "exact-vhf-root-frame-stage-consumed",
        "ready": True,
        "subject": {
            "canonical_vhf": runtime.CANONICAL_VHF,
            "decoded_sha256": "a" * 64,
            "car_name": "BMW_M3_E36",
            "root_node_path": "CAR[BMW_M3_E36]/NODE[HIERARCHY:Root]",
            "matrix_number": "0",
            "matrix_parent_chain_ids": ["0"],
            "local_matrix_row_vector": _identity(),
            "world_matrix_row_vector": _identity(),
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
    }


def _claim(kind: str = "identity") -> dict:
    identity = kind == "identity"
    return {
        "format": runtime.NORMALIZED_CLAIM_FORMAT,
        "version": 1,
        "ready": True,
        "source_contract": "SHIFT.FuturePositiveOuterVehicleVHFRelation/1",
        "semantic_authority": "Process 1",
        "subject": {
            "source_frame": runtime.OUTER_FRAME,
            "target_frame": runtime.VHF_ROOT_FRAME,
            "canonical_vhf": runtime.CANONICAL_VHF,
            "decoded_sha256": "a" * 64,
            "root_node_path": "CAR[BMW_M3_E36]/NODE[HIERARCHY:Root]",
            "matrix_number": "0",
            "matrix_parent_chain_ids": ["0"],
        },
        "relation": {
            "kind": kind,
            "matrix_convention": runtime.ROW_VECTOR_CONVENTION,
            "row_vector_matrix": _identity() if identity else _translation(1.0, 2.0, 3.0),
            "source_backed_relation_proof_ready": True,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": True,
            "relation_matrix_numeric_ready": True,
            "identity_semantics_explicitly_proven": identity,
            "fixed_affine_delta_ready": not identity,
        },
        "downstream": {
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
            "retail_world_transform_admitted": False,
        },
    }


def test_requirements_remain_unbound_until_process1_publishes_exact_format() -> None:
    requirements = runtime.admission_requirements(_root_stage())

    assert requirements["format"] == runtime.FORMAT
    assert requirements["ready"] is False
    assert requirements["status"] == "relation-upstream-format-unbound"
    assert requirements["upstream_relation_contract_bound"] is False
    assert requirements["candidate_or_frontier_admission_allowed"] is False
    assert requirements["identity_from_equal_numeric_matrix_allowed"] is False
    assert requirements["final_BODY0_bind_admission_ready"] is False
    assert requirements["retail_vehicle_world_transform_admission_ready"] is False


def test_positive_explicit_identity_relation_is_consumed_but_not_final_bind() -> None:
    claim = _claim("identity")
    result = runtime.admit_bound_relation_claim(
        _root_stage(),
        claim,
        expected_source_contract=claim["source_contract"],
    )

    assert result["ready"] is True
    assert result["status"] == "positive-outer-vehicle-vhf-relation-consumed"
    assert result["semantic_authority"] == "Process 1"
    assert result["relation"]["kind"] == "identity"
    assert result["relation"]["identity_semantics_explicitly_proven"] is True
    assert result["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_consumed"] is True
    assert result["handoff"]["BODY0_bind_frame_proof_ready"] is False
    assert result["handoff"]["vehicle_world_transform_ready"] is False
    assert result["handoff"]["retail_world_transform_admitted"] is False
    assert result["limits"]["relation_semantics_adjudicated_by_process2"] is False


def test_positive_fixed_affine_relation_is_consumed_without_bind_composition() -> None:
    claim = _claim("fixed_affine")
    result = runtime.admit_bound_relation_claim(
        _root_stage(),
        claim,
        expected_source_contract=claim["source_contract"],
    )

    assert result["relation"]["kind"] == "fixed_affine"
    assert result["relation"]["row_vector_matrix"][12:15] == [1.0, 2.0, 3.0]
    assert result["relation"]["fixed_affine_delta_ready"] is True
    assert result["relation"]["identity_semantics_explicitly_proven"] is False
    assert result["limits"]["BODY0_bind_matrix_composed_without_final_process1_proof"] is False


def test_identity_numeric_matrix_without_explicit_semantics_is_rejected() -> None:
    claim = _claim("identity")
    claim["relation"]["identity_semantics_explicitly_proven"] = False

    with pytest.raises(ValueError, match="explicit semantic proof"):
        runtime.admit_bound_relation_claim(
            _root_stage(), claim, expected_source_contract=claim["source_contract"]
        )


def test_frontier_or_candidate_contract_cannot_be_promoted() -> None:
    claim = _claim("identity")
    claim["source_contract"] = "SHIFT.OuterVehicleVHFRootRelationFrontier/1"

    with pytest.raises(ValueError, match="frontier/candidate"):
        runtime.admit_bound_relation_claim(
            _root_stage(), claim, expected_source_contract=claim["source_contract"]
        )


def test_unbound_future_process1_contract_fails_closed() -> None:
    claim = _claim("identity")

    with pytest.raises(ValueError, match="source contract is not bound"):
        runtime.admit_bound_relation_claim(_root_stage(), claim, expected_source_contract="")


def test_exact_vhf_root_identity_must_match_consumed_root_stage() -> None:
    claim = _claim("fixed_affine")
    claim["subject"]["matrix_number"] = "7"

    with pytest.raises(ValueError, match="MatrixNumber drift"):
        runtime.admit_bound_relation_claim(
            _root_stage(), claim, expected_source_contract=claim["source_contract"]
        )


def test_non_affine_relation_matrix_is_rejected() -> None:
    claim = _claim("fixed_affine")
    claim["relation"]["row_vector_matrix"][3] = 5.0

    with pytest.raises(ValueError, match="not row-vector affine"):
        runtime.admit_bound_relation_claim(
            _root_stage(), claim, expected_source_contract=claim["source_contract"]
        )


def test_relation_stage_cannot_preclaim_final_bind_or_world_transform() -> None:
    for field in (
        "BODY0_bind_frame_proof_ready",
        "vehicle_world_transform_ready",
        "retail_world_transform_admitted",
    ):
        claim = _claim("identity")
        claim["downstream"][field] = True
        with pytest.raises(ValueError):
            runtime.admit_bound_relation_claim(
                _root_stage(), claim, expected_source_contract=claim["source_contract"]
            )


def test_root_stage_preclaim_is_rejected_before_relation_admission() -> None:
    root = _root_stage()
    root["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] = True

    with pytest.raises(ValueError, match="illegally preclaims outer relation"):
        runtime.admission_requirements(root)


def test_contract_refuses_to_invent_future_process1_format() -> None:
    contract = runtime.contract()

    assert contract["future_process1_relation_format"] is None
    assert contract["future_process1_relation_format_must_be_bound_explicitly"] is True
    assert contract["frontier_or_candidate_admission_allowed"] is False
    assert contract["BODY0_bind_frame_proof_ready"] is False
    assert contract["retail_vehicle_world_transform_admitted"] is False
