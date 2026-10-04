import importlib.util
import json
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "build_bmw_body0_vhf_bind_frame_frontier.py"
    )
    spec = importlib.util.spec_from_file_location("bmw_body0_vhf_bind_frame_frontier", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _translation(x=0.0, y=0.0, z=0.0):
    return [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        float(x), float(y), float(z), 1.0,
    ]


def _global_identity(module, *, ready=False):
    return {
        "format": module.GLOBAL_IDENTITY_FORMAT,
        "identity_join": {
            "global_vehicle_address": "0x00c13700",
            "main_chassis_BODY_selected": True,
            "main_chassis_BODY_name": "body",
            "main_chassis_BODY_index": 0,
        },
        "handoff": {
            "outer_receiver_to_BODY_owner_continuity_proven": ready,
            "vehicle_BODY_selection_ready": ready,
            "selected_BODY_index": 0 if ready else None,
            "phase698_positive_selection_admissible": ready,
            "phase700_runtime_handoff_admissible": ready,
            "phase703_update_child_equality_gate_required": False,
            "phase703_gate_rewrite_ready": ready,
            "vehicle_world_transform_ready": False,
        },
        "scope": {
            "dynamic_BODY_pose_to_VHF_composition_proven": False,
        },
    }


def _vhf(module, *, matrix=None):
    return {
        "format": module.VHF_FORMAT,
        "version": 1,
        "status": "ready",
        "ready": True,
        "world_matrix": _translation(10.0, 0.0, 0.0) if matrix is None else matrix,
        "convention": {
            "source": "VHF row-major column-vector hierarchy",
            "target": "SVWT row-major D3D row-vector",
            "operation": "exact 4x4 transpose",
        },
        "boundary": {
            "canonical_body_meb_identity_proven": True,
            "vhf_object_transform_proven": True,
            "body_physics_pose_consumed": False,
            "body_local_to_meb_object_bind_proven": False,
        },
    }


def _bind(module, *, matrix=None, assumed=False):
    return {
        "format": module.BIND_PROOF_FORMAT,
        "status": "ready",
        "ready": True,
        "evidence_state": "proven-static",
        "body_index": 0,
        "body_name": "body",
        "frame_relation": module.FRAME_RELATION,
        "matrix_convention": module.ROW_CONVENTION,
        "body0_local_to_vhf_vehicle_root_row_matrix": (
            _translation(2.0, 0.0, 0.0) if matrix is None else matrix
        ),
        "provenance": {
            "source_targets": ["FUN_007b6900", "FUN_007b3670", "FUN_007b7840"],
        },
        "scope": {
            "identity_matrix_assumed": assumed,
            "original_game_executed": False,
            "new_runtime_capture_used": False,
        },
    }


def _write(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _inputs(tmp_path, module, *, global_ready=False, bind=False, bind_value=None):
    global_path = _write(tmp_path / "global.json", _global_identity(module, ready=global_ready))
    vhf_path = _write(tmp_path / "vhf.json", _vhf(module))
    bind_path = None
    if bind:
        bind_path = _write(
            tmp_path / "bind.json",
            _bind(module) if bind_value is None else bind_value,
        )
    return global_path, vhf_path, bind_path


def test_current_frontier_is_blocked_but_freezes_exact_formula(tmp_path):
    module = _load_module()
    global_path, vhf_path, _ = _inputs(tmp_path, module)

    report = module.build_bmw_body0_vhf_bind_frame_frontier(global_path, vhf_path)

    assert report["format"] == "SHIFT.BMWBody0VHFBindFrameFrontier/1"
    assert report["composition"]["formula_ready"] is True
    assert report["composition"]["BODY0_bind_frame_proven"] is False
    assert report["composition"]["retail_BODY0_pose_admission_ready"] is False
    assert report["composition"]["dynamic_world_matrix_producer_ready"] is False
    assert report["composition"]["row_vector_equation"] == (
        "M_object_world = M_vhf_bind * inverse(M_BODY0_bind) * M_BODY0_runtime"
    )
    assert {row["id"] for row in report["blockers"]} == {
        "retail-BODY0-pose-admission",
        "body0-bind-frame-provenance-not-proven",
    }
    assert [row["address"] for row in report["next_static_targets"]] == [
        "0x007b6900",
        "0x007b3670",
        "0x007b7840",
    ]
    assert report["scope"]["BODY0_bind_matrix_identity_assumed"] is False
    assert report["scope"]["BODY0_local_equals_MEB_local_assumed"] is False


def test_positive_static_bind_and_owner_identity_prepare_phase646_producer(tmp_path):
    module = _load_module()
    global_path, vhf_path, bind_path = _inputs(
        tmp_path, module, global_ready=True, bind=True
    )
    assert bind_path is not None

    report = module.build_bmw_body0_vhf_bind_frame_frontier(
        global_path, vhf_path, bind_path
    )

    assert report["composition"]["BODY0_bind_frame_proven"] is True
    assert report["composition"]["retail_BODY0_pose_admission_ready"] is True
    assert report["composition"]["dynamic_world_matrix_producer_ready"] is True
    assert report["composition"]["BODY0_bind_matrix"] == _translation(2.0, 0.0, 0.0)
    assert report["blockers"] == []
    assert report["next_static_targets"] == []
    assert report["handoff"]["phase700_BODY0_pose_admission_ready"] is True
    assert report["handoff"]["phase646_world_matrix_producer_ready"] is True
    assert report["handoff"]["vehicle_world_transform_ready"] is True


def test_composition_order_uses_bind_inverse_between_vhf_and_runtime_pose():
    module = _load_module()

    result = module.compose_body0_pose_to_vhf_world_matrix(
        _translation(10.0, 0.0, 0.0),
        _translation(2.0, 0.0, 0.0),
        (5.0, 0.0, 0.0),
        (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0),
    )

    # object->root +10, root->BODY(bind^-1) -2, BODY->world +5 => +13.
    assert result[12:15] == pytest.approx([13.0, 0.0, 0.0])


def test_body_pose_matrix_transposes_source_backed_column_basis():
    module = _load_module()
    # Column-vector +90 degree Z basis in row-major memory order.
    basis = (
        0.0, -1.0, 0.0,
        1.0, 0.0, 0.0,
        0.0, 0.0, 1.0,
    )
    matrix = module.body_pose_row_matrix((3.0, 4.0, 5.0), basis)

    assert matrix == pytest.approx([
        0.0, 1.0, 0.0, 0.0,
        -1.0, 0.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        3.0, 4.0, 5.0, 1.0,
    ])


def test_affine_inverse_handles_rotation_and_translation():
    module = _load_module()
    matrix = [
        0.0, 1.0, 0.0, 0.0,
        -1.0, 0.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        2.0, 3.0, 4.0, 1.0,
    ]
    inverse = module._inverse_affine_row(matrix)
    product = module._mul4(matrix, inverse)
    assert product == pytest.approx(_translation(), abs=1.0e-9)


def test_rejects_bind_proof_that_is_only_identity_assumption(tmp_path):
    module = _load_module()
    bad_bind = _bind(module, matrix=_translation(), assumed=True)
    global_path, vhf_path, bind_path = _inputs(
        tmp_path,
        module,
        global_ready=True,
        bind=True,
        bind_value=bad_bind,
    )
    assert bind_path is not None
    with pytest.raises(ValueError, match="identity assumption"):
        module.build_bmw_body0_vhf_bind_frame_frontier(
            global_path, vhf_path, bind_path
        )


def test_rejects_wrong_body_bind_identity(tmp_path):
    module = _load_module()
    bad_bind = _bind(module)
    bad_bind["body_index"] = 1
    global_path, vhf_path, bind_path = _inputs(
        tmp_path, module, global_ready=True, bind=True, bind_value=bad_bind
    )
    assert bind_path is not None
    with pytest.raises(ValueError, match="index drift"):
        module.build_bmw_body0_vhf_bind_frame_frontier(
            global_path, vhf_path, bind_path
        )


def test_rejects_singular_bind_matrix(tmp_path):
    module = _load_module()
    singular = _translation()
    singular[0] = 0.0
    bad_bind = _bind(module, matrix=singular)
    global_path, vhf_path, bind_path = _inputs(
        tmp_path, module, global_ready=True, bind=True, bind_value=bad_bind
    )
    assert bind_path is not None
    with pytest.raises(ValueError, match="singular"):
        module.build_bmw_body0_vhf_bind_frame_frontier(
            global_path, vhf_path, bind_path
        )


def test_rejects_upstream_dynamic_composition_preclaim(tmp_path):
    module = _load_module()
    global_value = _global_identity(module, ready=False)
    global_value["scope"]["dynamic_BODY_pose_to_VHF_composition_proven"] = True
    global_path = _write(tmp_path / "global.json", global_value)
    vhf_path = _write(tmp_path / "vhf.json", _vhf(module))

    with pytest.raises(ValueError, match="preclaims BODY/VHF composition"):
        module.build_bmw_body0_vhf_bind_frame_frontier(global_path, vhf_path)


def test_rejects_readiness_flag_disagreement(tmp_path):
    module = _load_module()
    global_value = _global_identity(module, ready=False)
    global_value["handoff"]["phase700_runtime_handoff_admissible"] = True
    global_path = _write(tmp_path / "global.json", global_value)
    vhf_path = _write(tmp_path / "vhf.json", _vhf(module))

    with pytest.raises(ValueError, match="readiness flags disagree"):
        module.build_bmw_body0_vhf_bind_frame_frontier(global_path, vhf_path)
