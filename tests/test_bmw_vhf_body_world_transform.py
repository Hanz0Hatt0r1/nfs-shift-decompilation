from __future__ import annotations

import copy

import pytest

import bmw_vhf_body_world_transform as mod


MEB = "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb"
SHA = "9" * 64


def _golden():
    return {
        "format": "SHIFT.BMWGoldenAssetManifest/1",
        "golden": {"resource": MEB, "resource_sha256": SHA},
    }


def _scene(matrix=None, *, sha=SHA, resource=MEB, name=mod.DEFAULT_BODY_NODE):
    if matrix is None:
        # VHF column-vector matrix: rotate XY + translate (4,5,6).
        matrix = [
            0.0, -1.0, 0.0, 4.0,
            1.0, 0.0, 0.0, 5.0,
            0.0, 0.0, 1.0, 6.0,
            0.0, 0.0, 0.0, 1.0,
        ]
    return {
        "format": "SHIFT.VHFScene/1",
        "parts": [{
            "name": name,
            "resource": resource,
            "resource_sha256": sha,
            "matrix_number": "17",
            "world_matrix": matrix,
        }],
    }


def _material_set(world=None):
    return {
        "format": "SHIFT.BMWMaterialSliceSet/1",
        "ready": True,
        "identity_sha256": "a" * 64,
        "mesh_identity": {
            "resource": MEB,
            "resource_sha256": SHA,
        },
        "render_command": {
            "format": "SHIFT.RenderCommand/1",
            "ready": True,
            "blocking_reasons": [],
            "mesh": {"ref": MEB},
            "world_matrix": world,
            "submeshes": [],
            "resource_plan": {},
        },
    }


def test_vhf_body_transform_requires_exact_body_identity_and_transposes_to_svwt(monkeypatch):
    monkeypatch.setattr(mod, "build_vhf_scene", lambda *args, **kwargs: _scene())

    report = mod.build_bmw_vhf_body_world_transform("BMW_M3_E36.bff", _golden())

    assert report["format"] == mod.FORMAT
    assert report["ready"] is True
    assert report["source"]["node_name"] == mod.DEFAULT_BODY_NODE
    assert report["source"]["mesh_resource"] == MEB
    assert report["source"]["mesh_sha256"] == SHA
    assert report["world_matrix"] == [
        0.0, 1.0, 0.0, 0.0,
        -1.0, 0.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        4.0, 5.0, 6.0, 1.0,
    ]
    assert report["translation_xyz"] == [4.0, 5.0, 6.0]
    assert report["convention"]["operation"] == "exact 4x4 transpose"
    assert report["boundary"]["phase700_runtime_pose_handoff_consumed"] is False
    assert report["boundary"]["dynamic_vehicle_world_transform_claimed"] is False


def test_vhf_body_transform_rejects_path_or_sha_mismatch(monkeypatch):
    monkeypatch.setattr(
        mod,
        "build_vhf_scene",
        lambda *args, **kwargs: _scene(sha="8" * 64),
    )
    with pytest.raises(ValueError, match="found 0"):
        mod.build_bmw_vhf_body_world_transform("BMW_M3_E36.bff", _golden())


def test_vhf_body_transform_rejects_non_affine_source_matrix(monkeypatch):
    matrix = _scene()["parts"][0]["world_matrix"][:]
    matrix[12] = 0.25
    monkeypatch.setattr(
        mod,
        "build_vhf_scene",
        lambda *args, **kwargs: _scene(matrix=matrix),
    )
    with pytest.raises(ValueError, match="column-vector affine"):
        mod.build_bmw_vhf_body_world_transform("BMW_M3_E36.bff", _golden())


def test_apply_vhf_transform_preserves_material_set_abi(monkeypatch):
    monkeypatch.setattr(mod, "build_vhf_scene", lambda *args, **kwargs: _scene())
    monkeypatch.setattr(
        mod,
        "validate_render_command",
        lambda command: {"valid": True, "blocking_reasons": []},
    )
    transform = mod.build_bmw_vhf_body_world_transform("BMW_M3_E36.bff", _golden())
    source = _material_set()
    source_copy = copy.deepcopy(source)

    result = mod.apply_bmw_vhf_body_world_transform(source, transform)

    assert source == source_copy
    assert result["format"] == "SHIFT.BMWMaterialSliceSet/1"
    assert result["render_command"]["world_matrix"] == transform["world_matrix"]
    assert result["vhf_body_world_transform"]["format"] == mod.FORMAT
    assert result["boundary"]["material_slice_set_abi_preserved"] is True
    assert result["boundary"]["dynamic_vehicle_world_transform_claimed"] is False


def test_apply_vhf_transform_rejects_existing_conflicting_matrix(monkeypatch):
    monkeypatch.setattr(mod, "build_vhf_scene", lambda *args, **kwargs: _scene())
    transform = mod.build_bmw_vhf_body_world_transform("BMW_M3_E36.bff", _golden())
    existing = [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    ]
    with pytest.raises(ValueError, match="conflicts"):
        mod.apply_bmw_vhf_body_world_transform(_material_set(existing), transform)


def test_apply_vhf_transform_rejects_mesh_sha_disagreement(monkeypatch):
    monkeypatch.setattr(mod, "build_vhf_scene", lambda *args, **kwargs: _scene())
    transform = mod.build_bmw_vhf_body_world_transform("BMW_M3_E36.bff", _golden())
    source = _material_set()
    source["mesh_identity"]["resource_sha256"] = "7" * 64
    with pytest.raises(ValueError, match="SHA-256 disagrees"):
        mod.apply_bmw_vhf_body_world_transform(source, transform)
