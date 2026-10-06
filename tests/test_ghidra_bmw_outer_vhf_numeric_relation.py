from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "ghidra" / "build_bmw_outer_vhf_numeric_relation.py"
SPEC = importlib.util.spec_from_file_location("bmw_outer_vhf_numeric", TOOL)
assert SPEC is not None and SPEC.loader is not None
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def _relation() -> dict:
    return {
        "format": module.RELATION_FORMAT,
        "ready": True,
        "subject": {
            "vehicle": "BMW_M3_E36",
            "canonical_vhf": module.CANONICAL_VHF,
            "decoded_sha256": module.DECODED_SHA256,
            "root_node_path": module.ROOT_PATH,
        },
        "relation": {
            "kind": "fixed_affine",
            "matrix_convention": module.ROW_CONVENTION,
            "outer_to_vhf_root_formula": "inverse(M_vhf_root_to_model * T(delta_local))",
            "relation_matrix_numeric_ready": False,
        },
        "handoff": {
            "outer_vehicle_root_to_VHF_vehicle_root_ready": True,
            "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": True,
        },
    }


def _delta() -> dict:
    return {
        "format": module.DELTA_FORMAT,
        "ready": True,
        "session_target": "Silverstone+BMW_M3_E36",
        "native_bootstrap_policy": {"first_vehicle_bootstrap": True, "physics_participant_spawn_config_plus_0x10": 0},
        "selected_numeric": {
            "delta_local": [0.0, 0.0, 0.0],
            "scope": "first explicit native primary-player vehicle bootstrap before any origin-update path",
        },
        "handoff": {
            "BMW_primary_player_first_bootstrap_render_root_delta_numeric_ready": True,
            "outer_vehicle_root_to_VHF_relation_numeric_matrix_ready": False,
        },
    }


def _root(matrix: list[float] | None = None) -> dict:
    # Non-identity fixture on purpose: MatrixNumber 0 is not an identity shortcut.
    matrix = matrix or [
        0.0, 1.0, 0.0, 0.0,
        -1.0, 0.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        1.0, 2.0, 3.0, 1.0,
    ]
    return {
        "format": module.ROOT_FORMAT,
        "ready": True,
        "source": {"resolved_path": module.CANONICAL_VHF, "decoded_sha256": module.DECODED_SHA256},
        "vehicle_root_frame": {
            "node_type": "HIERARCHY",
            "node_name": "Root",
            "node_path": module.ROOT_PATH,
            "matrix_number": "0",
            "matrix_parent_chain_ids": ["0"],
            "world_matrix_row_vector": matrix,
        },
        "provenance": {"exact_root_affine_matrix_ready": True},
    }


def test_positive_nonidentity_root_composes_and_inverts():
    report = module.build_numeric_relation(_relation(), _delta(), _root())
    assert report["ready"] is True
    assert report["handoff"]["outer_vehicle_root_to_VHF_relation_numeric_matrix_ready"] is True
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False
    root = report["numeric_relation"]["M_vhf_root_to_outer"]
    inv = report["numeric_relation"]["M_outer_to_vhf_root"]
    product = module._mul(root, inv)
    assert product == pytest.approx([1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1])
    assert report["numeric_relation"]["numeric_matrix_is_identity"] is False
    assert report["numeric_relation"]["identity_semantics_proven"] is False


def test_matrix_number_zero_is_not_identity_shortcut():
    report = module.build_numeric_relation(_relation(), _delta(), _root())
    assert report["subject"]["matrix_number"] == "0"
    assert report["numeric_relation"]["M_vhf_root_to_model"] != [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]


def test_rejects_missing_root_matrix():
    root = _root()
    del root["vehicle_root_frame"]["world_matrix_row_vector"]
    with pytest.raises(ValueError, match="world_matrix_row_vector must be a sequence"):
        module.build_numeric_relation(_relation(), _delta(), root)


def test_rejects_root_sha_drift():
    root = _root()
    root["source"]["decoded_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="decoded SHA drift"):
        module.build_numeric_relation(_relation(), _delta(), root)


def test_rejects_noncanonical_delta():
    delta = _delta()
    delta["selected_numeric"]["delta_local"] = [0.0, 0.0, 1.0]
    with pytest.raises(ValueError, match="delta drift"):
        module.build_numeric_relation(_relation(), delta, _root())


def test_rejects_upstream_numeric_preclaim():
    relation = _relation()
    relation["relation"]["relation_matrix_numeric_ready"] = True
    with pytest.raises(ValueError, match="preclaims numeric matrix"):
        module.build_numeric_relation(relation, _delta(), _root())


def test_rejects_singular_root_matrix():
    singular = [0.0] * 16
    singular[15] = 1.0
    with pytest.raises(ValueError, match="singular"):
        module.build_numeric_relation(_relation(), _delta(), _root(singular))
