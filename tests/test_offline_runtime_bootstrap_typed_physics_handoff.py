from __future__ import annotations

import json
from pathlib import Path

import offline_runtime_bootstrap as runtime_bootstrap


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_unified_bootstrap_routes_typed_closure_and_surfaces_exact_sdf(
    monkeypatch,
    tmp_path,
):
    observed = {}
    out = tmp_path / "bootstrap"
    sdf_path = out / "resources" / "typed_resources" / "BMW_M3_E36.bff" / "aarm_multilink.sdf"

    def fake_pipeline(inputs, output_dir, *, track, vehicle, decode_limit_per_archive=0):
        root = Path(output_dir)
        sgb_path = root / "typed_resources" / "Silverstone.bff" / "scene.sgb"
        sgb_path.parent.mkdir(parents=True, exist_ok=True)
        sgb_path.write_bytes(b"sgb")
        sdf_path.parent.mkdir(parents=True, exist_ok=True)
        sdf_path.write_bytes(b"exact sdf")
        _write(root / "resource_catalog.json", {"format": "SHIFT.OfflineResourceCatalog/1"})
        _write(root / "dependency_graph.json", {"format": "SHIFT.OfflineResourceDependencyGraph/1"})
        _write(
            root / "scene_vehicle_bootstrap.json",
            {
                "format": "SHIFT.SceneVehicleBootstrap/1",
                "ready": True,
                "track": track,
                "vehicle": vehicle,
                "roots": {
                    "track_visual": {".sgb": "track-sgb"},
                    "vehicle": {".sdf": "vehicle-sdf"},
                },
            },
        )
        _write(
            root / "typed_resource_closure.json",
            {
                "format": "SHIFT.TypedResourceClosure/1",
                "ready": True,
                "resources": [{
                    "resource_id": "track-sgb",
                    "path": "tracks/silverstone/scene.sgb",
                    "output": str(sgb_path),
                    "identity_match": True,
                }],
            },
        )
        _write(
            root / "vehicle_physics_bundle_report.json",
            {"format": "SHIFT.VehiclePhysicsBundleExtractor/1", "ready": True},
        )
        _write(root / "pipeline_run.json", {"format": "fixture"})
        return {
            "format": "SHIFT.OfflineResourcePipelineRun/1",
            "resource_bootstrap_ready": True,
            "blocking_reasons": [],
        }

    monkeypatch.setattr(runtime_bootstrap, "run_offline_pipeline", fake_pipeline)
    monkeypatch.setattr(
        runtime_bootstrap,
        "build_retail_archive_identity_admission",
        lambda *args, **kwargs: {
            "format": "SHIFT.RetailArchiveIdentityAdmission/1",
            "ready": True,
            "status": "ready",
            "blocking_reasons": [],
        },
    )
    monkeypatch.setattr(
        runtime_bootstrap,
        "load_track",
        lambda *args, **kwargs: {"format": "track", "ready": True, "blocking_reasons": []},
    )
    monkeypatch.setattr(
        runtime_bootstrap,
        "load_vehicle",
        lambda *args, **kwargs: {"format": "vehicle", "ready": True, "blocking_reasons": []},
    )
    monkeypatch.setattr(
        runtime_bootstrap,
        "build_scene_ir",
        lambda *args, **kwargs: {"format": "scene-ir", "ready": True, "blocking_reasons": []},
    )
    monkeypatch.setattr(
        runtime_bootstrap,
        "build_native_scene_files",
        lambda *args, **kwargs: {
            "format": "SHIFT.OfflineNativeSceneBuild/1",
            "static_resource_ready": True,
            "native_scene_runtime_ready": False,
            "blocking_reasons": [],
        },
    )

    def fake_vehicle(catalog, bootstrap, physics, output_dir, **kwargs):
        observed.update(kwargs)
        native_out = Path(output_dir)
        native_out.mkdir(parents=True, exist_ok=True)
        manifest_path = native_out / "vehicle_physics_resource_manifest.json"
        native_manifest_path = native_out / "native_physics_manifest.json"
        _write(manifest_path, {"format": "SHIFT.VehiclePhysicsResourceManifest/1"})
        _write(native_manifest_path, {"format": "SHIFT.BMWM3VehiclePhysicsResourceManifest/1"})
        return {
            "format": "SHIFT.OfflineNativeVehicleBuild/1",
            "resource_ready": True,
            "participant_structural_ready": True,
            "participant_runtime_identity_evaluated": False,
            "participant_runtime_identity_ready": False,
            "runtime_physics_contract_ready": True,
            "native_vehicle_runtime_ready": False,
            "blocking_reasons": [],
            "runtime_gate_blocking_reasons": ["participant-runtime-observation-required"],
            "participant_boundary": {
                "format": "SHIFT.NativePhysicsParticipantBoundary/1",
                "ready": True,
                "blocking_reasons": [],
            },
            "vehicle_physics_manifest": {
                "format": "SHIFT.VehiclePhysicsResourceManifest/1",
                "ready": True,
                "materialized_resources_ready": True,
                "entries": {
                    "sdf": {
                        "resource_id": "vehicle-sdf",
                        "path": "vehicles/physics/suspension/aarm_multilink.sdf",
                        "materialized_path": str(sdf_path),
                    }
                },
            },
            "artifacts": {
                "vehicle_physics_manifest": {"path": str(manifest_path), "sha256": "a" * 64},
                "native_physics_manifest": {"path": str(native_manifest_path), "sha256": "b" * 64},
            },
        }

    monkeypatch.setattr(runtime_bootstrap, "build_native_vehicle_files", fake_vehicle)

    report = runtime_bootstrap.build_offline_runtime_bootstrap(
        ["Vehicles.zip", "Silverstone_Era3_.zip"],
        out,
        track="Silverstone_Era3_GrandPrix",
        vehicle="BMW_M3_E36",
    )

    assert Path(observed["typed_closure_path"]) == out / "resources" / "typed_resource_closure.json"
    assert report["readiness"]["vehicle_physics_materialized_resources_ready"] is True
    assert report["artifacts"]["vehicle_sdf"] == str(sdf_path)
    assert report["artifacts"]["vehicle_physics_manifest"].endswith(
        "native-vehicle/vehicle_physics_resource_manifest.json"
    )
    assert report["artifacts"]["native_physics_manifest"].endswith(
        "native-vehicle/native_physics_manifest.json"
    )
    assert report["boundary"]["vehicle_physics_materialized_paths_require_exact_typed_closure"] is True
    assert report["boundary"]["vehicle_sdf_artifact_claims_body_semantics"] is False
