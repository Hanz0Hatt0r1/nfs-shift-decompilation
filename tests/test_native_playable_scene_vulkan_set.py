from __future__ import annotations

import hashlib
import json
from pathlib import Path

import native_playable_scene_vulkan_set as playable


def _write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _track_set(root: Path) -> Path:
    child = root / "draw_0000"
    _write(
        child / "bundle_manifest.json",
        {"format": "SHIFT.VulkanDrawBundle/1", "ready": True},
    )
    manifest_sha = _sha(child / "bundle_manifest.json")
    _write(
        root / "bundle_set_manifest.json",
        {
            "format": "SHIFT.NativeSceneVulkanSet/1",
            "ready": True,
            "draw_count": 1,
            "ready_draw_count": 1,
            "draws": [
                {
                    "draw_order": 0,
                    "command_index": 2,
                    "submesh_index": 3,
                    "binding_index": 4,
                    "ready": True,
                    "scene_draw_identity_sha256": "a" * 64,
                    "resource": {"path": "track.imb", "sha256": "b" * 64},
                    "bundle": {
                        "manifest_path": "draw_0000/bundle_manifest.json",
                        "manifest_sha256": manifest_sha,
                    },
                }
            ],
            "native_scene_submission": {"ready": True, "blocking_reasons": []},
        },
    )
    _write(
        root / "bundle_set_prepare.json",
        {"format": "SHIFT.NativeSceneVulkanSetPrepare/1", "ready": True},
    )
    (root / "bundle_set.paths").write_text("draw_0000\n", encoding="utf-8")
    return root


def test_composite_preserves_track_then_appends_vehicle_and_keeps_dynamic_pose_blocked(
    monkeypatch, tmp_path
):
    track = _track_set(tmp_path / "track")
    vehicle_source = tmp_path / "vehicle.json"
    _write(vehicle_source, {"format": "SHIFT.BMWMaterialSliceSet/1", "ready": True})

    def fake_vehicle(path, out, **kwargs):
        child = out / "draw_0001"
        _write(
            child / "bundle_manifest.json",
            {"format": "SHIFT.VulkanDrawBundle/1", "ready": True},
        )
        row = {
            "draw_order": 1,
            "command_index": 0,
            "submesh_index": 0,
            "binding_index": None,
            "source_group": "vehicle",
            "status": "ready",
            "ready": True,
            "blocking_reasons": [],
            "scene_draw_identity_sha256": "c" * 64,
            "resource": {
                "kind": "BMW-canonical-body",
                "path": "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb",
                "sha256": "d" * 64,
            },
            "bundle": {
                "format": "SHIFT.VulkanDrawBundle/1",
                "manifest_path": "draw_0001/bundle_manifest.json",
                "manifest_sha256": _sha(child / "bundle_manifest.json"),
            },
        }
        return [row], [], {"mesh_ref": row["resource"]["path"]}

    monkeypatch.setattr(playable, "_vehicle_rows", fake_vehicle)
    monkeypatch.setattr(
        playable,
        "prepare_native_scene_vulkan_set",
        lambda root, **kwargs: {
            "format": "SHIFT.NativeSceneVulkanSetPrepare/1",
            "ready": True,
            "blocking_reasons": [],
        },
    )

    out = tmp_path / "playable"
    report = playable.build_native_playable_scene_vulkan_set(
        track,
        vehicle_source,
        out,
    )

    assert report["ready"] is True
    assert report["track_draw_count"] == 1
    assert report["vehicle_draw_count"] == 1
    assert report["draw_count"] == 2
    manifest = json.loads((out / "bundle_set_manifest.json").read_text())
    assert [row["source_group"] for row in manifest["draws"]] == ["track", "vehicle"]
    assert [row["draw_order"] for row in manifest["draws"]] == [0, 1]
    assert (out / "bundle_set.paths").read_text().splitlines() == [
        "draw_0000",
        "draw_0001",
    ]
    assert manifest["boundary"]["bmw_manifests_relabelled_as_neutral"] is False
    assert manifest["boundary"]["vehicle_children_rebuilt_with_neutral_builder"] is True
    assert manifest["boundary"]["phase698_vehicle_BODY_selection_consumed"] is False
    assert manifest["boundary"]["dynamic_vehicle_world_transform_claimed"] is False
    assert json.loads((out / "draw_0000" / "bundle_manifest.json").read_text())["format"] == "SHIFT.VulkanDrawBundle/1"


def test_track_manifest_hash_tamper_stays_fail_closed(tmp_path):
    track = _track_set(tmp_path / "track")
    manifest = json.loads((track / "bundle_set_manifest.json").read_text())
    manifest["draws"][0]["bundle"]["manifest_sha256"] = "0" * 64
    _write(track / "bundle_set_manifest.json", manifest)

    rows, blockers = playable._track_rows(track, tmp_path / "out")
    assert rows == []
    assert "playable-scene:track-draw-0:manifest-sha256-mismatch" in blockers


def test_vehicle_source_without_world_matrix_is_rejected_before_bundle_build(
    monkeypatch, tmp_path
):
    payload = tmp_path / "vehicle.json"
    _write(payload, {"format": "SHIFT.BMWMaterialSliceSet/1", "ready": True})
    monkeypatch.setattr(
        playable,
        "_find_render_command",
        lambda value: {
            "format": "SHIFT.RenderCommand/1",
            "mesh": {
                "ref": playable.TARGET_MEB,
                "resolved": {"resource_sha256": "e" * 64},
            },
            "submeshes": [{}],
        },
    )
    monkeypatch.setattr(playable, "_find_mesh", lambda payload, command: {"vertices": [], "indices": []})

    rows, blockers, source = playable._vehicle_rows(
        payload,
        tmp_path / "out",
        source_bffs=[],
        environment_cube_dds=None,
        start_order=0,
    )
    assert rows == []
    assert blockers == ["playable-scene:vehicle-world-matrix-source-missing"]
    assert source == {}


def test_neutral_vehicle_builder_requires_static_provenance_gate_not_runtime_provenance(
    monkeypatch, tmp_path
):
    payload = tmp_path / "vehicle.json"
    _write(
        payload,
        {
            "format": "SHIFT.BMWMaterialSliceSet/1",
            "ready": True,
            "texture_sources": [],
        },
    )
    command = {
        "format": "SHIFT.RenderCommand/1",
        "world_matrix": [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
        "mesh": {
            "ref": playable.TARGET_MEB,
            "resolved": {"resource_sha256": "f" * 64},
        },
        "submeshes": [{"textures": [], "external_samplers": []}],
    }
    monkeypatch.setattr(playable, "_find_render_command", lambda value: command)
    monkeypatch.setattr(playable, "_find_mesh", lambda value, cmd: {"vertices": [], "indices": []})
    monkeypatch.setattr(playable, "_normalize_set_submesh_indices", lambda cmd, indices: [0])

    observed = {}

    def fake_build(binding, mesh, child, **kwargs):
        observed.update(kwargs)
        child = Path(child)
        _write(
            child / "bundle_manifest.json",
            {"format": "SHIFT.VulkanDrawBundle/1", "ready": True},
        )
        return {
            "format": "SHIFT.VulkanDrawBundle/1",
            "ready": True,
            "blocking_reasons": [],
            "artifacts": {
                "world_transform": {
                    "format": "SHIFT.VulkanWorldTransformPacket/1",
                    "ready": True,
                    "path": "world_transform.svwt",
                    "sha256": "1" * 64,
                }
            },
        }

    monkeypatch.setattr(playable, "build_vulkan_draw_bundle", fake_build)
    rows, blockers, source = playable._vehicle_rows(
        payload,
        tmp_path / "out",
        source_bffs=[],
        environment_cube_dds=None,
        start_order=0,
    )

    assert blockers == []
    assert len(rows) == 1
    assert rows[0]["source_group"] == "vehicle"
    assert observed["require_runtime_provenance"] is False
    assert source["mesh_ref"] == playable.TARGET_MEB
