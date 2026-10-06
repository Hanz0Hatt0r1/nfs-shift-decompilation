from __future__ import annotations

import copy

import pytest

from src.physics import bmw_vhf_hierarchy_root_frame_stage_runtime as runtime


def _column_translation(x: float, y: float, z: float) -> list[float]:
    return [
        1.0, 0.0, 0.0, x,
        0.0, 1.0, 0.0, y,
        0.0, 0.0, 1.0, z,
        0.0, 0.0, 0.0, 1.0,
    ]


def _row_translation(x: float, y: float, z: float) -> list[float]:
    return [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        x, y, z, 1.0,
    ]


def _positive() -> dict:
    return {
        "format": runtime.UPSTREAM_FORMAT,
        "version": 1,
        "status": "canonical-bmw-vhf-hierarchy-root-frame-proven",
        "ready": True,
        "INPUT": {
            "resource_join": runtime.RESOURCE_JOIN_FORMAT,
            "canonical_vhf": runtime.CANONICAL_VHF,
        },
        "source": {
            "resource_join_format": runtime.RESOURCE_JOIN_FORMAT,
            "resolved_path": runtime.CANONICAL_VHF,
            "archive": "BMW_M3_E36.bff",
            "archive_sha256": "b" * 64,
            "entry_index": 1083,
            "decoded_sha256": "a" * 64,
            "decoded_size": 4096,
        },
        "vehicle_root_frame": {
            "car_tag": "CAR",
            "car_name": runtime.VEHICLE_NAME,
            "node_type": "HIERARCHY",
            "node_name": runtime.ROOT_NODE_NAME,
            "node_path": runtime.ROOT_NODE_PATH,
            "matrix_number": "7",
            "matrix_record_present": True,
            "matrix_parent_chain": [
                {
                    "matrix_id": "2",
                    "parent": None,
                    "offset_xyz": [1.0, 2.0, 3.0],
                    "orientation_xyzw": [0.0, 0.0, 0.0, 1.0],
                    "local_matrix_column_vector": _column_translation(1.0, 2.0, 3.0),
                },
                {
                    "matrix_id": "7",
                    "parent": "2",
                    "offset_xyz": [4.0, 5.0, 6.0],
                    "orientation_xyzw": [0.0, 0.0, 0.0, 1.0],
                    "local_matrix_column_vector": _column_translation(4.0, 5.0, 6.0),
                },
            ],
            "matrix_parent_chain_ids": ["2", "7"],
            "local_offset_xyz": [4.0, 5.0, 6.0],
            "local_orientation_xyzw": [0.0, 0.0, 0.0, 1.0],
            "local_matrix_column_vector": _column_translation(4.0, 5.0, 6.0),
            "local_matrix_row_vector": _row_translation(4.0, 5.0, 6.0),
            "world_matrix_column_vector": _column_translation(5.0, 7.0, 9.0),
            "world_matrix_row_vector": _row_translation(5.0, 7.0, 9.0),
            "local_matrix_is_identity": False,
            "world_matrix_is_identity": False,
            "convention": {
                "source": runtime.SOURCE_CONVENTION,
                "composition": runtime.COMPOSITION_CONVENTION,
                "row_vector_conversion": runtime.ROW_VECTOR_CONVERSION,
            },
        },
        "provenance": {
            "vehicle_render_hierarchy_resource_owner_join_ready": True,
            "canonical_BMW_VHF_resource_identity_revalidated": True,
            "decoded_payload_sha256_matches_resource_join": True,
            "unique_direct_HIERARCHY_root_ready": True,
            "exact_root_node_name_ready": True,
            "exact_root_MatrixNumber_ready": True,
            "exact_root_MATRIX_record_ready": True,
            "exact_root_parent_chain_ready": True,
            "exact_root_affine_matrix_ready": True,
        },
        "handoff": {
            "canonical_BMW_VHF_hierarchy_root_frame_ready": True,
            "canonical_BMW_VHF_hierarchy_root_matrix_ready": True,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": False,
            "BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "limits": {
            "resource_identity_is_frame_identity": False,
            "root_identity_matrix_implies_outer_vehicle_identity": False,
            "equal_numeric_values_are_provenance": False,
            "callgraph_adjacency_is_ownership": False,
            "visual_similarity_is_frame_identity": False,
            "dynamic_outer_vehicle_pose_consumed": False,
            "BODY0_bind_frame_claimed": False,
            "runtime_capture_required": False,
            "original_game_executed": False,
        },
    }


def test_positive_stage_consumes_exact_root_metadata_but_not_outer_relation() -> None:
    stage = runtime.consume_root_frame_stage(_positive())

    assert stage["format"] == runtime.FORMAT
    assert stage["ready"] is True
    assert stage["status"] == "exact-vhf-root-frame-stage-consumed"
    assert stage["subject"]["canonical_vhf"] == runtime.CANONICAL_VHF
    assert stage["subject"]["root_node_path"] == runtime.ROOT_NODE_PATH
    assert stage["subject"]["matrix_number"] == "7"
    assert stage["subject"]["matrix_parent_chain_ids"] == ["2", "7"]
    assert stage["subject"]["world_matrix_row_vector"][12:15] == [5.0, 7.0, 9.0]
    assert stage["handoff"]["exact_bmw_vhf_resource_identity_consumed"] is True
    assert stage["handoff"]["exact_bmw_vhf_hierarchy_root_frame_consumed"] is True
    assert stage["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] is False
    assert stage["handoff"]["BODY0_bind_frame_proof_ready"] is False
    assert stage["handoff"]["retail_world_transform_admitted"] is False


def test_matrix_number_must_match_parent_chain_terminal_id() -> None:
    payload = _positive()
    payload["vehicle_root_frame"]["matrix_number"] = "8"

    with pytest.raises(ValueError, match="MatrixNumber disagrees"):
        runtime.consume_root_frame_stage(payload)


def test_parent_chain_must_be_exactly_linked() -> None:
    payload = _positive()
    payload["vehicle_root_frame"]["matrix_parent_chain"][1]["parent"] = "99"

    with pytest.raises(ValueError, match="parent-chain linkage drift"):
        runtime.consume_root_frame_stage(payload)


def test_row_vector_matrix_must_be_exact_transpose() -> None:
    payload = _positive()
    payload["vehicle_root_frame"]["world_matrix_row_vector"][12] = 6.0

    with pytest.raises(ValueError, match="not the exact transpose"):
        runtime.consume_root_frame_stage(payload)


def test_resource_identity_drift_fails_closed() -> None:
    payload = _positive()
    payload["source"]["resolved_path"] = "vehicles/bmw_m3_e36/bmw_m3_e36_cockpit.vhf"

    with pytest.raises(ValueError, match="source path drift"):
        runtime.consume_root_frame_stage(payload)


def test_upstream_outer_relation_preclaim_is_rejected() -> None:
    payload = _positive()
    payload["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] = True

    with pytest.raises(ValueError, match="illegally preclaims"):
        runtime.consume_root_frame_stage(payload)


def test_identity_root_frame_does_not_promote_outer_relation() -> None:
    payload = _positive()
    identity = _column_translation(0.0, 0.0, 0.0)
    payload["vehicle_root_frame"].update(
        {
            "matrix_number": "0",
            "matrix_parent_chain": [
                {
                    "matrix_id": "0",
                    "parent": None,
                    "offset_xyz": [0.0, 0.0, 0.0],
                    "orientation_xyzw": [0.0, 0.0, 0.0, 1.0],
                    "local_matrix_column_vector": identity,
                }
            ],
            "matrix_parent_chain_ids": ["0"],
            "local_offset_xyz": [0.0, 0.0, 0.0],
            "local_orientation_xyzw": [0.0, 0.0, 0.0, 1.0],
            "local_matrix_column_vector": identity,
            "local_matrix_row_vector": identity,
            "world_matrix_column_vector": identity,
            "world_matrix_row_vector": identity,
            "local_matrix_is_identity": True,
            "world_matrix_is_identity": True,
        }
    )

    stage = runtime.consume_root_frame_stage(payload)
    assert stage["subject"]["matrix_number"] == "0"
    assert stage["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] is False
    assert stage["limits"]["identity_root_matrix_used_as_outer_relation"] is False


def test_contract_keeps_scheduler_authority_and_final_admission_explicit() -> None:
    contract = runtime.contract()

    assert contract["scheduler_authority_contract"] == "SHIFT.Process2RuntimeSchedulerAuthority/1"
    assert contract["host_1_60_is_retail_evidence"] is False
    assert contract["outer_vehicle_relation_ready"] is False
    assert contract["BODY0_bind_frame_proof_ready"] is False
    assert contract["retail_world_transform_admitted"] is False
