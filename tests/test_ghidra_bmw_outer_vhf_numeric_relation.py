from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "evaluate_bmw_outer_vhf_numeric_relation.py"
SPEC = importlib.util.spec_from_file_location("bmw_outer_vhf_numeric", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _semantic() -> dict:
    return {
        "format": MODULE.SEMANTIC_FORMAT,
        "ready": True,
        "subject": {
            "vehicle": MODULE.VEHICLE,
            "canonical_vhf": MODULE.CANONICAL_VHF,
            "decoded_sha256": MODULE.DECODED_SHA256,
            "root_node_path": MODULE.ROOT_PATH,
            "matrix_number": "0",
        },
        "relation": {
            "kind": "fixed_affine",
            "matrix_convention": MODULE.ROW_CONVENTION,
            "outer_to_vhf_root_formula": "inverse(M_vhf_root_to_model * T(delta_local))",
            "relation_matrix_numeric_ready": False,
        },
        "handoff": {
            "outer_vehicle_root_to_VHF_vehicle_root_ready": True,
            "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": True,
            "outer_vehicle_root_to_VHF_relation_numeric_matrix_ready": False,
        },
    }


def _delta() -> dict:
    return {
        "format": MODULE.DELTA_FORMAT,
        "ready": True,
        "status": "bmw-primary-player-first-bootstrap-render-root-delta-proven",
        "vehicle": MODULE.VEHICLE,
        "session_target": MODULE.SESSION,
        "selected_numeric": {
            "delta_local": [0.0, 0.0, 0.0],
            "producer": "FUN_00795d60",
        },
        "handoff": {
            "BMW_primary_player_first_bootstrap_render_root_delta_numeric_ready": True,
            "outer_vehicle_root_to_VHF_relation_numeric_matrix_ready": False,
        },
    }


def _root(matrix: list[float] | None = None) -> dict:
    if matrix is None:
        matrix = [
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            2.0, 3.0, 4.0, 1.0,
        ]
    return {
        "format": MODULE.ROOT_FORMAT,
        "version": 1,
        "ready": True,
        "status": "canonical-bmw-vhf-hierarchy-root-frame-proven",
        "source": {
            "resolved_path": MODULE.CANONICAL_VHF,
            "decoded_sha256": MODULE.DECODED_SHA256,
        },
        "vehicle_root_frame": {
            "car_name": MODULE.VEHICLE,
            "node_path": MODULE.ROOT_PATH,
            "matrix_number": "0",
            "matrix_parent_chain_ids": ["0"],
            "world_matrix_row_vector": matrix,
        },
        "handoff": {
            "canonical_BMW_VHF_hierarchy_root_frame_ready": True,
            "canonical_BMW_VHF_hierarchy_root_matrix_ready": True,
        },
    }


def test_zero_delta_inverts_exact_root_matrix_and_only_closes_s2() -> None:
    result = MODULE.evaluate(_semantic(), _delta(), _root())

    assert result["ready"] is True
    assert result["numeric"]["M_vhf_root_to_outer"][12:15] == [2.0, 3.0, 4.0]
    assert result["numeric"]["M_outer_to_vhf_root"][12:15] == pytest.approx([-2.0, -3.0, -4.0])
    assert result["handoff"]["outer_vehicle_root_to_VHF_relation_numeric_matrix_ready"] is True
    assert result["handoff"]["BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready"] is False
    assert result["handoff"]["BODY0_bind_frame_proof_ready"] is False
    assert result["handoff"]["vehicle_world_transform_ready"] is False


def test_nonzero_first_bootstrap_delta_is_rejected() -> None:
    delta = _delta()
    delta["selected_numeric"]["delta_local"] = [0.0, 1.0, 0.0]
    with pytest.raises(ValueError, match="requires exact first-bootstrap"):
        MODULE.evaluate(_semantic(), delta, _root())


def test_root_hash_mismatch_is_rejected() -> None:
    root = _root()
    root["source"]["decoded_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="decoded SHA-256 drift"):
        MODULE.evaluate(_semantic(), _delta(), root)


def test_matrix_number_mismatch_is_rejected() -> None:
    root = _root()
    root["vehicle_root_frame"]["matrix_number"] = "1"
    root["vehicle_root_frame"]["matrix_parent_chain_ids"] = ["1"]
    with pytest.raises(ValueError, match="MatrixNumber disagrees"):
        MODULE.evaluate(_semantic(), _delta(), root)


def test_singular_root_matrix_is_rejected() -> None:
    root = _root([
        0.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    ])
    with pytest.raises(ValueError, match="singular"):
        MODULE.evaluate(_semantic(), _delta(), root)
