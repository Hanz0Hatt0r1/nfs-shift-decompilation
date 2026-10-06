from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_outer_vehicle_vhf_root_relation_composition.py"
SPEC = importlib.util.spec_from_file_location("outer_vhf_relation_composition", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _domain():
    return {
        "format": MODULE.DOMAIN_FORMAT,
        "ready": True,
        "proof": {"vehicle_render_model_root_affine_domain_join_ready": True},
        "participant_domain": {
            "canonical_bmw_vhf": MODULE.CANONICAL_VHF,
            "canonical_bmw_vhf_decoded_sha256": MODULE.DECODED_SHA256,
        },
        "handoff": {
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "BODY0_bind_frame_proof_ready": False,
        },
    }


def _bridge():
    return {
        "format": MODULE.BRIDGE_FORMAT,
        "ready": True,
        "outer_transform": {
            "render_root_local_delta_offsets": MODULE.DELTA_OFFSETS,
            "local_delta_has_concrete_setup_producer": True,
            "local_delta_is_runtime_pose_source": False,
        },
        "snapshot_relation": {
            "translation_formula": "P_snapshot = P_outer + R_outer * delta_local",
            "independent_rotation_source_present": False,
        },
        "handoff": {
            "outer_vehicle_to_render_root_symbolic_affine_ready": True,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
        },
    }


def _root(matrix=None):
    matrix = matrix or [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        4.0, 5.0, 6.0, 1.0,
    ]
    return {
        "format": MODULE.ROOT_FORMAT,
        "ready": True,
        "source": {
            "resolved_path": MODULE.CANONICAL_VHF,
            "decoded_sha256": MODULE.DECODED_SHA256,
        },
        "vehicle_root_frame": {
            "node_type": "HIERARCHY",
            "node_name": "Root",
            "matrix_number": "7",
            "matrix_parent_chain_ids": ["2", "7"],
            "world_matrix_row_vector": matrix,
        },
        "handoff": {
            "canonical_BMW_VHF_hierarchy_root_frame_ready": True,
            "canonical_BMW_VHF_hierarchy_root_matrix_ready": True,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
        },
    }


def _delta():
    rows = []
    for label, displacement in zip(MODULE.DELTA_FIELD_LABELS, (0x19C, 0x1A0, 0x1A4)):
        rows.append(
            {
                "target_is_FUN_00795d60_entry_ECX_on_all_reachable_paths": True,
                "render_root_delta_fields_touched": [label],
                "displacement": displacement,
                "numeric_delta_value_proven": False,
            }
        )
    return {
        "format": MODULE.DELTA_FORMAT,
        "ready": True,
        "retail": {"function": {"address": "0x00795d60"}},
        "bridge_provenance": {
            "translation_formula": "P_snapshot = P_outer + R_outer * delta_local"
        },
        "analysis": {"missing_entry_receiver_bytes": [], "store_candidates": rows},
    }


def test_positive_composition_proves_formula_only():
    report = MODULE.build(_domain(), _bridge(), _root(), _delta())

    assert report["ready"] is True
    assert report["composition"]["formula_ready"] is True
    assert report["composition"]["outer_local_to_vhf_root_local"] == (
        "M_outer_to_vhf = T_row(-delta_local) * inverse(M_vhf_root_model)"
    )
    assert report["composition"]["inverse_root_model_row_matrix"][12:15] == pytest.approx(
        [-4.0, -5.0, -6.0]
    )
    assert report["handoff"]["outer_vehicle_to_VHF_root_fixed_affine_formula_ready"] is True
    assert report["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] is False
    assert report["handoff"]["outer_vehicle_root_to_VHF_fixed_affine_delta_ready"] is False
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False


def test_identity_root_does_not_promote_relation():
    identity = [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    ]
    report = MODULE.build(_domain(), _bridge(), _root(identity), _delta())

    assert report["composition"]["root_model_matrix_is_identity"] is True
    assert report["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] is False
    assert report["limits"]["identity_root_matrix_used_as_outer_vhf_identity"] is False


def test_rejects_upstream_relation_preclaim():
    domain = _domain()
    domain["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] = True
    with pytest.raises(ValueError, match="preclaims outer/VHF"):
        MODULE.build(domain, _bridge(), _root(), _delta())


def test_rejects_incomplete_delta_store_coverage():
    delta = _delta()
    delta["analysis"]["store_candidates"].pop()
    with pytest.raises(ValueError, match="delta field semantic coverage drift"):
        MODULE.build(_domain(), _bridge(), _root(), delta)


def test_rejects_non_affine_root_matrix():
    root = _root()
    root["vehicle_root_frame"]["world_matrix_row_vector"][3] = 1.0
    with pytest.raises(ValueError, match="not D3D row-vector affine"):
        MODULE.build(_domain(), _bridge(), root, _delta())


def test_rejects_numeric_promotion_inside_delta_frontier():
    delta = _delta()
    for row in delta["analysis"]["store_candidates"]:
        row["numeric_delta_value_proven"] = True
    with pytest.raises(ValueError, match="bind an explicit numeric producer contract"):
        MODULE.build(_domain(), _bridge(), _root(), delta)
