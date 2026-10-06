from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_outer_vehicle_vhf_root_relation.py"
SPEC = importlib.util.spec_from_file_location("outer_vehicle_vhf_root_relation", TOOL)
assert SPEC is not None and SPEC.loader is not None
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def _identity() -> list[float]:
    return [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    ]


def _bridge() -> dict:
    return {
        "format": mod.BRIDGE_FORMAT,
        "ready": True,
        "retail": {"program": mod.PROGRAM, "md5": mod.PE_MD5},
        "outer_transform": {
            "local_delta_has_concrete_setup_producer": True,
            "local_delta_is_runtime_pose_source": False,
            "render_root_local_delta_offsets": list(mod.DELTA_OFFSETS),
        },
        "snapshot_relation": {
            "translation_formula": "P_snapshot = P_outer + R_outer * delta_local",
        },
        "render_participant_relation": {
            "vehicle_render_model": "participant+0x1340",
            "world_affine_consumed_by": "FUN_004a8c20",
        },
        "handoff": {
            "outer_vehicle_to_render_root_symbolic_affine_ready": True,
            "render_root_translation_delta_producer_bounded": True,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
    }


def _domain() -> dict:
    return {
        "format": mod.DOMAIN_FORMAT,
        "ready": True,
        "retail": {"program": mod.PROGRAM, "md5": mod.PE_MD5},
        "participant_domain": {
            "canonical_bmw_vhf": mod.CANONICAL_VHF,
            "canonical_bmw_vhf_decoded_sha256": mod.DECODED_VHF_SHA256,
            "vehicle_render_model_owner": "participant+0x1340",
            "root_world_affine_layout": (
                "row-major D3D row-vector affine; translation slots 12/13/14"
            ),
        },
        "proof": {
            "vehicle_render_model_root_affine_domain_join_ready": True,
            "participant_root_affine_passed_to_same_render_model_owner": True,
            "render_model_local_points_transformed_by_participant_root_affine": True,
        },
        "handoff": {
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": False,
            "BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
    }


def _root(matrix: list[float] | None = None) -> dict:
    return {
        "format": mod.ROOT_FRAME_FORMAT,
        "ready": True,
        "source": {
            "resolved_path": mod.CANONICAL_VHF,
            "decoded_sha256": mod.DECODED_VHF_SHA256,
        },
        "vehicle_root_frame": {
            "node_path": mod.ROOT_NODE_PATH,
            "matrix_number": "0",
            "matrix_parent_chain_ids": ["0"],
            "world_matrix_row_vector": list(matrix or _identity()),
            "convention": {
                "row_vector_conversion": "exact 4x4 transpose",
            },
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
    }


def _delta_provenance() -> dict:
    return {
        "format": mod.DELTA_PROVENANCE_FORMAT,
        "ready": True,
        "retail": {
            "program": mod.PROGRAM,
            "md5": mod.PE_MD5,
            "function": {
                "address": mod.TARGET_ADDRESS,
                "name": mod.TARGET_FUNCTION,
                "mnemonic_sha256": mod.TARGET_MNEMONIC_SHA256,
            },
        },
        "bridge_provenance": {
            "format": mod.BRIDGE_FORMAT,
            "translation_formula": "P_snapshot = P_outer + R_outer * delta_local",
            "render_root_local_delta_offsets": list(mod.DELTA_OFFSETS),
        },
        "analysis": {
            "candidate_store_count": 3,
            "terminal_root_kinds": ["external-or-memory-varnode"],
        },
        "handoff": {
            "render_root_delta_store_provenance_ready": True,
            "render_root_delta_value_roots_ready": True,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": False,
            "BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "scope": {
            "synthetic_test_values_are_retail_evidence": False,
        },
    }


def _numeric(delta: dict, xyz: list[float]) -> dict:
    return {
        "format": mod.NUMERIC_DELTA_FORMAT,
        "ready": True,
        "source_provenance_format": mod.DELTA_PROVENANCE_FORMAT,
        "source_provenance_sha256": mod._canonical_sha256(delta),
        "target": {
            "function_address": mod.TARGET_ADDRESS,
            "function_name": mod.TARGET_FUNCTION,
            "mnemonic_sha256": mod.TARGET_MNEMONIC_SHA256,
            "field_offsets": list(mod.DELTA_OFFSETS),
        },
        "xyz": list(xyz),
        "proof": {
            "source_backed_terminal_roots_resolved": True,
            "numeric_delta_value_proven": True,
            "runtime_capture_used": False,
            "original_game_executed": False,
            "synthetic_test_values_are_retail_evidence": False,
        },
    }


def test_positive_current_inputs_narrow_remaining_blocker_to_numeric_delta():
    delta = _delta_provenance()
    report = mod.build_outer_vehicle_vhf_root_relation(
        _bridge(),
        delta,
        _domain(),
        _root(),
    )

    assert report["format"] == mod.FORMAT
    assert report["ready"] is False
    assert report["status"] == (
        "blocked-on-source-backed-render-root-delta-numeric-resolution"
    )
    assert report["composition"]["outer_vehicle_root_to_vhf_root"] == (
        "inverse(D_delta) * inverse(M_vhf_root)"
    )
    required = report["required_numeric_delta_contract"]
    assert required["format"] == mod.NUMERIC_DELTA_FORMAT
    assert required["must_bind_source_provenance_sha256"] == mod._canonical_sha256(delta)
    assert required["arbitrary_xyz_allowed"] is False
    assert report["handoff"]["outer_vehicle_vhf_composition_formula_ready"] is True
    assert report["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] is False
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False


def test_noncommuting_root_rotation_locks_row_vector_composition_order():
    # Row-vector +90 degree Z rotation: +X maps to +Y.
    root_matrix = [
        0.0, 1.0, 0.0, 0.0,
        -1.0, 0.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    ]
    delta = _delta_provenance()
    report = mod.build_outer_vehicle_vhf_root_relation(
        _bridge(),
        delta,
        _domain(),
        _root(root_matrix),
        numeric_delta=_numeric(delta, [2.0, 0.0, 0.0]),
    )

    assert report["ready"] is True
    relation = report["relation"]
    assert relation["kind"] == "fixed_affine"
    assert relation["matrix_convention"] == mod.ROW_VECTOR_CONVENTION
    assert relation["row_vector_matrix"] == pytest.approx([
        0.0, -1.0, 0.0, 0.0,
        1.0, 0.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 2.0, 0.0, 1.0,
    ])
    # Reversing the two inverses would leave translation [-2, 0, 0].
    assert relation["row_vector_matrix"][12:15] != pytest.approx([-2.0, 0.0, 0.0])
    assert report["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] is True
    assert report["handoff"]["outer_vehicle_root_to_VHF_fixed_affine_delta_ready"] is True
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False


def test_identity_relation_requires_full_source_backed_composition():
    delta = _delta_provenance()
    report = mod.build_outer_vehicle_vhf_root_relation(
        _bridge(),
        delta,
        _domain(),
        _root(),
        numeric_delta=_numeric(delta, [0.0, 0.0, 0.0]),
    )

    assert report["ready"] is True
    assert report["relation"]["kind"] == "identity"
    assert report["relation"]["row_vector_matrix"] == pytest.approx(_identity())
    assert report["relation"]["identity_semantics_explicitly_proven"] is True
    assert report["relation"]["fixed_affine_delta_ready"] is False
    assert report["limits"]["identity_inferred_from_vhf_root_identity_alone"] is False


def test_identity_vhf_root_does_not_hide_nonzero_outer_delta():
    delta = _delta_provenance()
    report = mod.build_outer_vehicle_vhf_root_relation(
        _bridge(),
        delta,
        _domain(),
        _root(),
        numeric_delta=_numeric(delta, [1.0, 2.0, 3.0]),
    )

    assert report["relation"]["kind"] == "fixed_affine"
    assert report["relation"]["row_vector_matrix"][12:15] == pytest.approx(
        [-1.0, -2.0, -3.0]
    )
    assert report["relation"]["identity_semantics_explicitly_proven"] is False


def test_rejects_numeric_delta_not_bound_to_exact_value_provenance():
    delta = _delta_provenance()
    numeric = _numeric(delta, [1.0, 2.0, 3.0])
    numeric["source_provenance_sha256"] = "0" * 64

    with pytest.raises(ValueError, match="not bound to the exact delta-provenance"):
        mod.build_outer_vehicle_vhf_root_relation(
            _bridge(), delta, _domain(), _root(), numeric_delta=numeric
        )


def test_rejects_numeric_delta_with_synthetic_retail_claim():
    delta = _delta_provenance()
    numeric = _numeric(delta, [1.0, 2.0, 3.0])
    numeric["proof"]["synthetic_test_values_are_retail_evidence"] = True

    with pytest.raises(ValueError, match="Synthetic|synthetic"):
        mod.build_outer_vehicle_vhf_root_relation(
            _bridge(), delta, _domain(), _root(), numeric_delta=numeric
        )


def test_rejects_domain_join_that_preclaims_final_relation():
    domain = copy.deepcopy(_domain())
    domain["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] = True

    with pytest.raises(ValueError, match="domain join unexpectedly preclaims"):
        mod.build_outer_vehicle_vhf_root_relation(
            _bridge(), _delta_provenance(), domain, _root()
        )


def test_rejects_non_affine_root_matrix():
    root = _root()
    root["vehicle_root_frame"]["world_matrix_row_vector"][3] = 1.0

    with pytest.raises(ValueError, match="not D3D row-vector affine"):
        mod.build_outer_vehicle_vhf_root_relation(
            _bridge(), _delta_provenance(), _domain(), root
        )
