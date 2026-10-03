from __future__ import annotations

import hashlib
import json
from pathlib import Path

from offline_native_resource_handoff import (
    BMW_COMPAT_FORMAT,
    HANDOFF_FORMAT,
    PHYSICS_MANIFEST_FORMAT,
    SCENE_JOIN_FORMAT,
    build_bmw_m3_runtime_compat_manifest,
    build_native_resource_handoff,
    build_native_resource_handoff_files,
    build_scene_catalog_join,
    build_vehicle_physics_resource_manifest,
)


def _catalog():
    vehicle_id = "bff-vehicle"
    track_id = "bff-track"
    resources = [{
        "id": f"{track_id}#7",
        "archive_id": track_id,
        "archive_name": "Silverstone_Era3_GrandPrix.bff",
        "index": 7,
        "path": "tracks/silverstone/objects/bridge.imb",
        "normalized_path": "tracks/silverstone/objects/bridge.imb",
        "extension": ".imb",
        "compression_type": 2,
        "compressed_size": 500,
        "uncompressed_size": 1000,
        "decoded_sha256": "a" * 64,
    }]
    for offset, kind in enumerate(("cdf", "edf", "gdf", "sdf", "tbf", "bbf"), 20):
        resources.append({
            "id": f"{vehicle_id}#{offset}",
            "archive_id": vehicle_id,
            "archive_name": "BMW_M3_E36.bff",
            "index": offset,
            "path": f"vehicles/physics/{kind}/fixture.{kind}",
            "normalized_path": f"vehicles/physics/{kind}/fixture.{kind}",
            "extension": f".{kind}",
            "compression_type": 2,
            "compressed_size": 100 + offset,
            "uncompressed_size": 200 + offset,
        })
    return {
        "format": "SHIFT.OfflineResourceCatalog/1",
        "resources": resources,
    }


def _bootstrap(vehicle="BMW_M3_E36"):
    vehicle_id = "bff-vehicle"
    roots = {
        f".{kind}": f"{vehicle_id}#{offset}"
        for offset, kind in enumerate(("cdf", "edf", "gdf", "sdf", "tbf", "bbf"), 20)
    }
    return {
        "format": "SHIFT.SceneVehicleBootstrap/1",
        "ready": True,
        "track": "Silverstone_Era3_GrandPrix",
        "vehicle": vehicle,
        "selected_archives": {
            "track_visual": {
                "id": "bff-track",
                "archive_name": "Silverstone_Era3_GrandPrix.bff",
            },
            "vehicle": {
                "id": vehicle_id,
                "archive_name": f"{vehicle}.bff",
            },
        },
        "roots": {"vehicle": roots},
    }


def _physics_bundle(vehicle="BMW_M3_E36"):
    entries = {}
    resources = {}
    for offset, kind in enumerate(("cdf", "edf", "gdf", "sdf", "tbf", "bbf"), 20):
        digest = (hex(offset)[2:] * 64)[:64]
        raw_digest = (hex(offset + 32)[2:] * 64)[:64]
        entries[kind] = {
            "archive_path": f"vehicles/physics/{kind}/fixture.{kind}",
            "index": offset,
            "type": 2,
            "compressed_size": 100 + offset,
            "uncompressed_size": 200 + offset,
            "decoded_sha256": digest,
            "raw_sha256": raw_digest,
        }
        if kind in {"cdf", "edf", "gdf", "sdf"}:
            resources[kind] = {"sha256": digest}
    return {
        "format": "SHIFT.VehiclePhysicsBundleExtractor/1",
        "ready": True,
        "source": {"bff": f"/tmp/{vehicle}.bff"},
        "entries": entries,
        "profile": {
            "format": "SHIFT.VehiclePhysicsAssetGraph/1",
            "ready": True,
            "resources": resources,
            "summary": {
                "sdf_bodies": 11,
                "sdf_joint_hinge_count": 4,
                "sdf_bar_count": 20,
            },
        },
    }


def _scene_set(sha="a" * 64):
    return {
        "format": "SHIFT.NativeSceneVulkanSet/1",
        "ready": True,
        "draw_count": 1,
        "ready_draw_count": 1,
        "draws": [{
            "draw_order": 0,
            "binding_index": 42,
            "ready": True,
            "scene_draw_identity_sha256": "b" * 64,
            "resource": {
                "archive": "Silverstone_Era3_GrandPrix.bff",
                "path": "tracks/silverstone/objects/bridge.imb",
                "sha256": sha,
            },
        }],
    }


def _scene_prepare(manifest_sha=None):
    source = {}
    if manifest_sha is not None:
        source["manifest_sha256"] = manifest_sha
    return {
        "format": "SHIFT.NativeSceneVulkanSetPrepare/1",
        "ready": True,
        "source": source,
    }


def test_vehicle_physics_manifest_is_derived_from_exact_catalog_entries():
    manifest = build_vehicle_physics_resource_manifest(
        _catalog(), _bootstrap(), _physics_bundle()
    )
    assert manifest["format"] == PHYSICS_MANIFEST_FORMAT
    assert manifest["ready"] is True
    assert manifest["body_count"] == 11
    assert manifest["joint_hinge_count"] == 4
    assert manifest["bar_count"] == 20
    assert set(manifest["entries"]) == {"cdf", "edf", "gdf", "sdf", "tbf", "bbf"}
    assert manifest["entries"]["sdf"]["resource_id"] == "bff-vehicle#23"

    compat = build_bmw_m3_runtime_compat_manifest(manifest)
    assert compat["format"] == BMW_COMPAT_FORMAT
    assert compat["ready"] is True
    assert len(compat["archive_entry_points"]) == 4
    assert compat["sdf"]["body_count"] == 11


def test_non_bmw_vehicle_does_not_get_bmw_runtime_compatibility():
    catalog = _catalog()
    bootstrap = _bootstrap("Ford_Mustang_2010")
    for row in catalog["resources"]:
        if row["archive_id"] == "bff-vehicle":
            row["archive_name"] = "Ford_Mustang_2010.bff"
    manifest = build_vehicle_physics_resource_manifest(
        catalog, bootstrap, _physics_bundle("Ford_Mustang_2010")
    )
    assert manifest["ready"] is True
    compat = build_bmw_m3_runtime_compat_manifest(manifest)
    assert compat["ready"] is False
    assert "native-runtime-currently-accepts-bmw-m3-e36-only" in compat["blocking_reasons"]


def test_scene_catalog_join_requires_exact_decoded_sha256():
    good = build_scene_catalog_join(
        _catalog(), _bootstrap(), _scene_set(), _scene_prepare()
    )
    assert good["format"] == SCENE_JOIN_FORMAT
    assert good["ready"] is True
    assert good["draws"][0]["catalog_resource_id"] == "bff-track#7"

    bad = build_scene_catalog_join(
        _catalog(), _bootstrap(), _scene_set("c" * 64), _scene_prepare()
    )
    assert bad["ready"] is False
    assert "draw-0:draw:catalog-resource-sha256-mismatch" in bad["blocking_reasons"]


def test_native_resource_handoff_never_claims_runtime_execution():
    report = build_native_resource_handoff(
        _catalog(),
        _bootstrap(),
        _physics_bundle(),
        scene_set=_scene_set(),
        scene_prepare=_scene_prepare(),
    )
    assert report["format"] == HANDOFF_FORMAT
    assert report["ready"] is True
    assert report["resource_inputs_ready"] is True
    assert report["boundary"]["runtime_execution_claimed"] is False
    assert report["boundary"]["provenance_gate_bypass"] is False


def test_file_handoff_rejects_scene_prepare_for_different_manifest(tmp_path: Path):
    catalog = tmp_path / "catalog.json"
    bootstrap = tmp_path / "bootstrap.json"
    physics = tmp_path / "physics.json"
    scene = tmp_path / "scene"
    out = tmp_path / "out"
    scene.mkdir()

    for path, value in (
        (catalog, _catalog()),
        (bootstrap, _bootstrap()),
        (physics, _physics_bundle()),
    ):
        path.write_text(json.dumps(value), encoding="utf-8")
    manifest_path = scene / "bundle_set_manifest.json"
    manifest_path.write_text(json.dumps(_scene_set()), encoding="utf-8")
    wrong_sha = hashlib.sha256(b"other manifest").hexdigest()
    (scene / "bundle_set_prepare.json").write_text(
        json.dumps(_scene_prepare(wrong_sha)), encoding="utf-8"
    )

    report = build_native_resource_handoff_files(
        catalog, bootstrap, physics, out, scene_set_dir=scene
    )
    assert report["ready"] is False
    assert "scene-prepare:source-manifest-sha256-mismatch" in report["blocking_reasons"]
    assert (out / "vehicle_physics_resource_manifest.json").is_file()
    assert (out / "native_physics_manifest.json").is_file()
    assert (out / "scene_catalog_join.json").is_file()
    assert (out / "native_resource_handoff.json").is_file()
