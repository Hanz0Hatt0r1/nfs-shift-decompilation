from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import struct

import pytest

import bmw_vhf_root_frame_scene_consumer as mod
import native_playable_scene_bootstrap as bootstrap


VHF = "vehicles/bmw_m3_e36/bmw_m3_e36.vhf"
MEB = "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb"
BODY = "BMW_M3_E36_KIT00_BODY_LODA"


def _transpose(matrix):
    return [matrix[col * 4 + row] for row in range(4) for col in range(4)]


def _decoded(*, body_parent="1", include_body_matrix=True):
    body_matrix = (
        f'<MATRIX id="2" parent="{body_parent}" Offset="4 5 6" Orientation="0 0 0 1" />'
        if include_body_matrix
        else ""
    )
    return (
        '<CAR Name="BMW_M3_E36">'
        '<NODE type="HIERARCHY" Name="Root" MatrixNumber="1" />'
        '<MATRIX id="1" Offset="1 2 3" Orientation="0 0 0 1" />'
        f'{body_matrix}'
        f'<NODE type="OBJECT" Name="{BODY}" MatrixNumber="2">'
        f'<RESOURCE Filename="{MEB}" />'
        '</NODE>'
        '</CAR>'
    ).encode("utf-8")


class _Entry:
    index = 1083
    path = VHF


class _FakeBFF:
    decoded = _decoded()

    def __init__(self, path):
        self.entries = [_Entry()]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def extract_entry(self, entry, *, type2):
        assert type2 == "lzx"
        return self.decoded


def _source(archive: Path, decoded: bytes):
    return {
        "archive": archive.name,
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "entry_index": 1083,
        "resolved_path": VHF,
        "path": VHF,
        "decoded_sha256": hashlib.sha256(decoded).hexdigest(),
        "decoded_size": len(decoded),
    }


def _root_handoff(archive: Path, decoded: bytes):
    source = _source(archive, decoded)
    root_column = [
        1.0, 0.0, 0.0, 1.0,
        0.0, 1.0, 0.0, 2.0,
        0.0, 0.0, 1.0, 3.0,
        0.0, 0.0, 0.0, 1.0,
    ]
    return {
        "format": "SHIFT.BMWVHFHierarchyRootFrame/1",
        "ready": True,
        "source": source,
        "vehicle_root_frame": {
            "node_type": "HIERARCHY",
            "node_name": "Root",
            "matrix_number": "1",
            "matrix_parent_chain_ids": ["1"],
            "world_matrix_column_vector": root_column,
            "world_matrix_row_vector": _transpose(root_column),
        },
        "handoff": {
            "canonical_BMW_VHF_hierarchy_root_frame_ready": True,
            "canonical_BMW_VHF_hierarchy_root_matrix_ready": True,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
    }


def _vhf_transform(archive: Path, decoded: bytes):
    source = _source(archive, decoded)
    body_column = [
        1.0, 0.0, 0.0, 5.0,
        0.0, 1.0, 0.0, 7.0,
        0.0, 0.0, 1.0, 9.0,
        0.0, 0.0, 0.0, 1.0,
    ]
    return {
        "format": "SHIFT.BMWVHFBodyWorldTransform/1",
        "ready": True,
        "source": {
            "archive": archive.name,
            "vhf_resource": VHF,
            "vhf_entry": {
                "archive": source["archive"],
                "archive_sha256": source["archive_sha256"],
                "entry_index": source["entry_index"],
                "path": VHF,
                "decoded_sha256": source["decoded_sha256"],
                "decoded_size": source["decoded_size"],
            },
            "node_name": BODY,
            "mesh_resource": MEB,
        },
        "vhf_world_matrix": body_column,
        "world_matrix": _transpose(body_column),
    }


def _build(monkeypatch, tmp_path, decoded=None):
    decoded = _decoded() if decoded is None else decoded
    archive = tmp_path / "BMW_M3_E36.bff"
    archive.write_bytes(b"retail-archive-identity")
    _FakeBFF.decoded = decoded
    monkeypatch.setattr(mod, "BFF", _FakeBFF)
    consumer = mod.build_bmw_vhf_root_frame_scene_consumer(
        archive,
        _root_handoff(archive, decoded),
        _vhf_transform(archive, decoded),
    )
    return archive, consumer


def test_positive_root_frame_is_preserved_into_body_object_frame(monkeypatch, tmp_path):
    _, consumer = _build(monkeypatch, tmp_path)

    assert consumer["parser_bootstrap_ready"] is True
    assert consumer["ready"] is False
    assert consumer["root_frame"]["matrix_number"] == "1"
    assert consumer["body_object_frame"]["matrix_parent_chain_ids"] == ["1", "2"]
    assert consumer["body_object_frame"]["root_matrix_number_is_ancestor"] is True
    assert consumer["body_object_frame"]["world_matrix_row_vector"][12:15] == [5.0, 7.0, 9.0]
    assert consumer["boundary"]["missing_MATRIX_identity_fallback_allowed"] is False
    assert consumer["boundary"]["static_vhf_frame_is_dynamic_vehicle_pose"] is False


def test_missing_body_matrix_fails_closed_instead_of_preview_identity_fallback(monkeypatch, tmp_path):
    decoded = _decoded(include_body_matrix=False)
    archive = tmp_path / "BMW_M3_E36.bff"
    archive.write_bytes(b"retail-archive-identity")
    _FakeBFF.decoded = decoded
    monkeypatch.setattr(mod, "BFF", _FakeBFF)

    with pytest.raises(ValueError, match="missing VHF MATRIX id '2'"):
        mod.build_bmw_vhf_root_frame_scene_consumer(
            archive,
            _root_handoff(archive, decoded),
            _vhf_transform(archive, decoded),
        )


def test_body_object_must_descend_from_positive_root_matrix(monkeypatch, tmp_path):
    decoded = (
        '<CAR Name="BMW_M3_E36">'
        '<NODE type="HIERARCHY" Name="Root" MatrixNumber="1" />'
        '<MATRIX id="1" Offset="1 2 3" Orientation="0 0 0 1" />'
        '<MATRIX id="9" Offset="0 0 0" Orientation="0 0 0 1" />'
        '<MATRIX id="2" parent="9" Offset="4 5 6" Orientation="0 0 0 1" />'
        f'<NODE type="OBJECT" Name="{BODY}" MatrixNumber="2">'
        f'<RESOURCE Filename="{MEB}" />'
        '</NODE>'
        '</CAR>'
    ).encode("utf-8")
    archive = tmp_path / "BMW_M3_E36.bff"
    archive.write_bytes(b"retail-archive-identity")
    _FakeBFF.decoded = decoded
    monkeypatch.setattr(mod, "BFF", _FakeBFF)

    with pytest.raises(ValueError, match="does not descend from HIERARCHY Root"):
        mod.build_bmw_vhf_root_frame_scene_consumer(
            archive,
            _root_handoff(archive, decoded),
            _vhf_transform(archive, decoded),
        )


def _write_scene_set(scene_root: Path, consumer, *, tamper=False):
    child = scene_root / "draw_0001"
    child.mkdir(parents=True)
    matrix = list(consumer["body_object_frame"]["world_matrix_row_vector"])
    if tamper:
        matrix[12] += 1.0
    packet = (
        mod.SVWT_HEADER.pack(b"SVWT", 1, 1, mod.SVWT_MATRIX.size)
        + mod.SVWT_MATRIX.pack(*matrix)
    )
    packet_path = child / "world_transform.svwt"
    packet_path.write_bytes(packet)
    packet_sha = hashlib.sha256(packet).hexdigest()
    child_manifest = {
        "format": "SHIFT.VulkanDrawBundle/1",
        "ready": True,
        "artifacts": {
            "world_transform": {
                "format": "SHIFT.VulkanWorldTransformPacket/1",
                "ready": True,
                "path": "world_transform.svwt",
                "sha256": packet_sha,
            }
        },
    }
    child_manifest_path = child / "bundle_manifest.json"
    child_manifest_path.write_text(json.dumps(child_manifest), encoding="utf-8")
    child_sha = hashlib.sha256(child_manifest_path.read_bytes()).hexdigest()
    scene_manifest = {
        "format": "SHIFT.NativeSceneVulkanSet/1",
        "ready": True,
        "draws": [{
            "draw_order": 1,
            "submesh_index": 0,
            "source_group": "vehicle",
            "bundle": {
                "manifest_path": "draw_0001/bundle_manifest.json",
                "manifest_sha256": child_sha,
            },
        }],
    }
    (scene_root / "bundle_set_manifest.json").write_text(
        json.dumps(scene_manifest), encoding="utf-8"
    )


def test_final_consumer_proves_every_vehicle_svwt_matches_static_object_frame(monkeypatch, tmp_path):
    _, consumer = _build(monkeypatch, tmp_path)
    scene_root = tmp_path / "scene"
    _write_scene_set(scene_root, consumer)

    final = mod.finalize_bmw_vhf_root_frame_scene_consumer(consumer, scene_root)

    assert final["ready"] is True
    assert final["vulkan_object_frame_ready"] is True
    assert final["vulkan_object_frame"]["vehicle_draw_count"] == 1
    assert final["handoff"]["canonical_BMW_VHF_root_frame_scene_consumer_ready"] is True
    assert final["handoff"]["vehicle_world_transform_ready"] is False
    assert final["boundary"]["process2_freshness_gated_live_transform_still_required"] is True
    assert final["limits"]["does_not_hide_missing_physics_motion_with_render_animation"] is True


def test_final_consumer_rejects_tampered_vehicle_svwt(monkeypatch, tmp_path):
    _, consumer = _build(monkeypatch, tmp_path)
    scene_root = tmp_path / "scene"
    _write_scene_set(scene_root, consumer, tamper=True)

    with pytest.raises(ValueError, match="SVWT matrix disagrees"):
        mod.finalize_bmw_vhf_root_frame_scene_consumer(consumer, scene_root)


def test_production_resource_join_requires_root_frame_handoff(monkeypatch, tmp_path):
    monkeypatch.delenv(bootstrap.ROOT_FRAME_ENV, raising=False)
    monkeypatch.setattr(
        bootstrap,
        "load_bmw_vehicle_render_model_resource_join",
        lambda value: {"format": "SHIFT.BMWVehicleRenderModelResourceJoin/1", "ready": True},
    )

    report = bootstrap.build_native_playable_scene_bootstrap(
        ["unused.zip"],
        tmp_path / "track",
        tmp_path / "out",
        vehicle="BMW_M3_E36",
        vehicle_render_model_join={"ready": True},
    )

    assert report["ready"] is False
    assert report["boundary"]["bmw_vhf_hierarchy_root_frame_required"] is True
    assert report["boundary"]["bmw_vhf_hierarchy_root_frame_consumed"] is False
    assert any("bmw-vhf-hierarchy-root-frame-handoff-missing" in reason for reason in report["blocking_reasons"])
