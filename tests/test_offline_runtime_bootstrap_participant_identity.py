from __future__ import annotations

import json
from pathlib import Path

import offline_runtime_bootstrap as runtime_bootstrap


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_runtime_bootstrap_threads_exact_participant_identity_without_overclaiming_runtime(
    monkeypatch,
    tmp_path,
):
    observed = {}

    def fake_pipeline(inputs, output_dir, *, track, vehicle, decode_limit_per_archive=0):
        out = Path(output_dir)
        sgb = out / "typed_resources" / "Track.bff" / "tracks/test/scene.sgb"
        sgb.parent.mkdir(parents=True, exist_ok=True)
        sgb.write_bytes(b"SGB fixture")
        _write(out / "resource_catalog.json", {"format": "SHIFT.OfflineResourceCatalog/1"})
        _write(out / "dependency_graph.json", {"format": "SHIFT.OfflineResourceDependencyGraph/1"})
        _write(
            out / "scene_vehicle_bootstrap.json",
            {
                "format": "SHIFT.SceneVehicleBootstrap/1",
                "ready": True,
                "track": track,
                "vehicle": vehicle,
                "roots": {"track_visual": {".sgb": "res-sgb"}, "vehicle": {}},
            },
        )
        _write(
            out / "typed_resource_closure.json",
            {
                "format": "SHIFT.TypedResourceClosure/1",
                "ready": True,
                "resources": [
                    {
                        "resource_id": "res-sgb",
                        "archive": "Track.bff",
                        "path": "tracks/test/scene.sgb",
                        "output": str(sgb),
                        "identity_match": True,
                    }
                ],
            },
        )
        _write(
            out / "vehicle_physics_bundle_report.json",
            {"format": "SHIFT.VehiclePhysicsBundleExtractor/1", "ready": True},
        )
        _write(out / "pipeline_run.json", {"fixture": True})
        return {
            "format": "SHIFT.OfflineResourcePipelineRun/1",
            "resource_bootstrap_ready": True,
            "blocking_reasons": [],
        }

    monkeypatch.setattr(runtime_bootstrap, "run_offline_pipeline", fake_pipeline)
    monkeypatch.setattr(
        runtime_bootstrap,
        "build_retail_archive_identity_admission",
        lambda catalog, bootstrap, *, track, vehicle: {
            "format": "SHIFT.RetailArchiveIdentityAdmission/1",
            "status": "ready",
            "ready": True,
            "blocking_reasons": [],
            "roles": {},
        },
    )
    monkeypatch.setattr(
        runtime_bootstrap,
        "load_track",
        lambda catalog, graph, *, track: {
            "format": "SHIFT.OfflineTrackLoad/1",
            "ready": True,
            "status": "ready",
            "blocking_reasons": [],
        },
    )
    monkeypatch.setattr(
        runtime_bootstrap,
        "load_vehicle",
        lambda catalog, graph, *, vehicle: {
            "format": "SHIFT.OfflineVehicleLoad/1",
            "ready": True,
            "status": "ready",
            "blocking_reasons": [],
        },
    )
    monkeypatch.setattr(
        runtime_bootstrap,
        "build_scene_ir",
        lambda inputs, output_dir: {
            "format": "SHIFT.OfflineSceneIRMaterialization/1",
            "ready": True,
            "blocking_reasons": [],
        },
    )
    monkeypatch.setattr(
        runtime_bootstrap,
        "build_native_scene_files",
        lambda *args, **kwargs: {
            "format": "SHIFT.OfflineNativeSceneBuild/1",
            "static_resource_ready": True,
            "native_scene_runtime_ready": False,
            "blocking_reasons": ["runtime:runtime-proven-draw-admission-required"],
        },
    )

    def fake_vehicle(catalog, bootstrap, physics, output_dir, **kwargs):
        observed["participant_observation_path"] = kwargs.get(
            "participant_observation_path"
        )
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        runtime_evidence = out / "native_physics_participant_runtime_evidence.json"
        runtime_evidence.write_text("{}\n", encoding="utf-8")
        return {
            "format": "SHIFT.OfflineNativeVehicleBuild/1",
            "resource_ready": True,
            "participant_structural_ready": True,
            "participant_runtime_identity_evaluated": True,
            "participant_runtime_identity_ready": True,
            "runtime_physics_contract_ready": True,
            "native_vehicle_runtime_ready": False,
            "blocking_reasons": [],
            "runtime_gate_blocking_reasons": [
                "input-binding-runtime-evidence-required",
                "fixed-step-runtime-evidence-required",
            ],
            "artifacts": {
                "participant_runtime_evidence": {
                    "path": str(runtime_evidence),
                    "sha256": "a" * 64,
                }
            },
        }

    monkeypatch.setattr(runtime_bootstrap, "build_native_vehicle_files", fake_vehicle)

    observation = tmp_path / "participant-observation.json"
    observation.write_text("{}\n", encoding="utf-8")
    report = runtime_bootstrap.build_offline_runtime_bootstrap(
        ["corpus.zip"],
        tmp_path / "bootstrap",
        track="Track",
        vehicle="Car",
        participant_observation_path=observation,
    )

    assert observed["participant_observation_path"] == observation
    assert report["offline_build_ready"] is True
    assert report["runtime_ready"] is False
    assert report["readiness"]["retail_archive_identity_ready"] is True
    assert report["readiness"]["vehicle_participant_runtime_identity_evaluated"] is True
    assert report["readiness"]["vehicle_participant_runtime_identity_ready"] is True
    assert "runtime-vehicle:participant-runtime-observation-required" not in report[
        "blocking_reasons"
    ]
    assert "runtime-vehicle:input-binding-runtime-evidence-required" in report[
        "blocking_reasons"
    ]
    assert "runtime-vehicle:fixed-step-runtime-evidence-required" in report[
        "blocking_reasons"
    ]
    assert "participant_runtime_evidence" in report["artifacts"]
    assert report["boundary"]["runtime_execution_claimed"] is False
