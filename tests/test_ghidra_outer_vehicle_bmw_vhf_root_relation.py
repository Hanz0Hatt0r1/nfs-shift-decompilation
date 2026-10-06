from __future__ import annotations
import importlib.util
from pathlib import Path
import pytest

TOOL = Path(__file__).parents[1] / "tools" / "ghidra" / "build_outer_vehicle_bmw_vhf_root_relation.py"
spec = importlib.util.spec_from_file_location("rel", TOOL)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def delta_provenance():
    return {
        "format": mod.DELTA_FORMAT, "version": 1, "status": "delta-store-provenance-ready", "ready": True,
        "retail": {
            "program": "SHIFT.exe", "md5": "705af8b420e5eb1e3834ac43d5533c6b",
            "function": {
                "address": "0x00795d60", "name": "FUN_00795d60", "size": 8797,
                "calling_convention": "__fastcall",
                "mnemonic_sha256": "c587cae5d3d8f99afed40fe0c059c8c60bc9cc45d9ee644f5e90e2e1f5a8eb14",
            },
        },
        "bridge_provenance": {"render_root_local_delta_offsets": ["+0x19c", "+0x1a0", "+0x1a4"]},
        "analysis": {
            "missing_entry_receiver_bytes": [], "structural_blockers": [],
            "store_candidates": [
                {
                    "render_root_delta_fields_touched": [field],
                    "target_is_FUN_00795d60_entry_ECX_on_all_reachable_paths": True,
                    "outer_Vehicle_delta_field_semantics_joined_from_bridge": True,
                    "VHF_frame_semantics_proven": False,
                    "terminal_roots": [{"root_kind": "entry-register", "semantic_join_required": True}],
                }
                for field in ("render_root_delta.x", "render_root_delta.y", "render_root_delta.z")
            ],
        },
        "handoff": {
            "render_root_delta_store_provenance_ready": True,
            "render_root_delta_value_roots_ready": True,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": False,
        },
    }


def bridge():
    return {
        "format": mod.BRIDGE_FORMAT, "ready": True,
        "outer_transform": {
            "render_root_local_delta_offsets": ["+0x19c", "+0x1a0", "+0x1a4"],
            "local_delta_has_concrete_setup_producer": True,
            "local_delta_is_runtime_pose_source": False,
        },
        "snapshot_relation": {
            "translation_formula": "P_snapshot = P_outer + R_outer * delta_local",
            "independent_rotation_source_present": False,
        },
    }


def domain():
    return {
        "format": mod.DOMAIN_FORMAT, "ready": True,
        "proof": {"vehicle_render_model_root_affine_domain_join_ready": True},
        "participant_domain": {
            "canonical_bmw_vhf": mod.CANONICAL_VHF,
            "canonical_bmw_vhf_decoded_sha256": mod.DECODED_VHF_SHA256,
        },
    }


def root(matrix=None):
    if matrix is None:
        matrix = [1,0,0,0, 0,1,0,0, 0,0,1,0, 4,5,6,1]
    return {
        "format": mod.ROOT_FORMAT, "ready": True,
        "source": {"resolved_path": mod.CANONICAL_VHF, "decoded_sha256": mod.DECODED_VHF_SHA256},
        "provenance": {"exact_root_affine_matrix_ready": True},
        "vehicle_root_frame": {
            "node_type": "HIERARCHY", "node_name": "Root", "node_path": mod.ROOT_PATH, "matrix_number": "7",
            "matrix_parent_chain_ids": ["2", "7"],
            "world_matrix_row_vector": matrix,
        },
    }


def test_symbolic_fixed_affine_relation_is_positive_but_not_numeric():
    out = mod.build_relation(delta_provenance(), bridge(), domain(), root())
    assert out["ready"] is True
    assert out["relation"]["kind"] == "fixed_affine"
    assert out["relation"]["outer_to_vhf_root_formula"] == "inverse(M_vhf_root_to_model * T(delta_local))"
    assert out["proof"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] is True
    assert out["proof"]["outer_vehicle_root_to_VHF_fixed_affine_delta_ready"] is True
    assert out["handoff"]["outer_vehicle_root_to_VHF_relation_numeric_matrix_ready"] is False
    assert out["relation"]["identity_semantics_proven"] is False


def test_numeric_algebra_helper_uses_root_then_delta_then_inverse_without_opening_gate():
    root_to_outer, outer_to_root = mod.evaluate_numeric_relation(
        root()["vehicle_root_frame"]["world_matrix_row_vector"], [1, 2, 3]
    )
    # root->model translation (4,5,6), then model->outer translation (1,2,3)
    assert root_to_outer[12:15] == pytest.approx([5,7,9])
    assert outer_to_root[12:15] == pytest.approx([-5,-7,-9])
    out = mod.build_relation(delta_provenance(), bridge(), domain(), root())
    assert out["handoff"]["outer_vehicle_root_to_VHF_relation_numeric_matrix_ready"] is False
    assert out["limits"]["process2_numeric_relation_admission_ready"] is False


def test_identity_valued_numeric_helper_does_not_promote_identity_semantics():
    ident = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]
    _root_to_outer, outer_to_root = mod.evaluate_numeric_relation(ident, [0,0,0])
    assert outer_to_root == pytest.approx(ident)
    out = mod.build_relation(delta_provenance(), bridge(), domain(), root(ident))
    assert out["relation"]["kind"] == "fixed_affine"
    assert out["relation"]["identity_semantics_proven"] is False
    assert out["relation"]["relation_matrix_numeric_ready"] is False


def test_rejects_runtime_pose_delta():
    b = bridge(); b["outer_transform"]["local_delta_is_runtime_pose_source"] = True
    with pytest.raises(ValueError, match="runtime pose"):
        mod.build_relation(delta_provenance(), b, domain(), root())


def test_rejects_domain_drift():
    d = domain(); d["participant_domain"]["canonical_bmw_vhf"] = "vehicles/other.vhf"
    with pytest.raises(ValueError, match="canonical BMW VHF domain drift"):
        mod.build_relation(delta_provenance(), bridge(), d, root())


def test_rejects_root_chain_drift():
    r = root(); r["vehicle_root_frame"]["matrix_parent_chain_ids"] = ["2"]
    with pytest.raises(ValueError, match="parent chain drift"):
        mod.build_relation(delta_provenance(), bridge(), domain(), r)


def test_rejects_delta_value_root_preclaim_or_missing_roots():
    d = delta_provenance()
    d["analysis"]["store_candidates"][0]["terminal_roots"] = []
    with pytest.raises(ValueError, match="terminal value roots missing"):
        mod.build_relation(d, bridge(), domain(), root())


def test_rejects_delta_relation_preclaim():
    d = delta_provenance()
    d["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] = True
    with pytest.raises(ValueError, match="preclaims final outer/VHF relation"):
        mod.build_relation(d, bridge(), domain(), root())
