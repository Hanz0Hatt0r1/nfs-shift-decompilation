from __future__ import annotations

import json
from pathlib import Path

import offline_runtime_bootstrap as runtime_bootstrap


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _ready_retail_archive_admission():
    return {
        "format": "SHIFT.RetailArchiveIdentityAdmission/1",
        "status": "ready",
        "ready": True,
        "blocking_reasons": [],
        "roles": {},
    }


def _install_resource_pipeline_fixture(monkeypatch, tmp_path, *, include_sgb=True):
    observed = {}

    def fake_run(inputs, output_dir, *, track, vehicle, decode_limit_per_archive=0):
        observed["inputs"] = list(inputs)
        observed["track"] = track
        observed["vehicle"] = vehicle
        observed["decode_limit"] = decode_limit_per_archive
        out = Path(output_dir)
        raw_sgb = out / "typed_resources" / "Track.bff" / "tracks/test/scene.sgb"
        raw_sgb.parent.mkdir(parents=True, exist_ok=True)
        raw_sgb.write_bytes(b"SGB fixture")
        _write_json(out / "resource_catalog.json", {"format": "SHIFT.OfflineResourceCatalog/1"})
        _write_json(out / "dependency_graph.json", {"format": "SHIFT.OfflineResourceDependencyGraph/1"})
        _write_json(
            out / "scene_vehicle_bootstrap.json",
            {
                "format": "SHIFT.SceneVehicleBootstrap/1",
                "ready": True,
                "track": track,
                "vehicle": vehicle,
                "roots": {
                    "track_visual": {".sgb": "res-sgb"},
                    "vehicle": {},
                },
            },
        )
        resources = []
        if include_sgb:
            resources.append(
                {
                    "resource_id": "res-sgb",
                    "archive": "Track.bff",
                    "path": "tracks/test/scene.sgb",
                    "output": str(raw_sgb),
                    "identity_match": True,
                }
            )
        _write_json(
            out / "typed_resource_closure.json",
            {
                "format": "SHIFT.TypedResourceClosure/1",
                "ready": True,
                "resources": resources,
            },
        )
        _write_json(
            out / "vehicle_physics_bundle_report.json",
            {"format": "SHIFT.VehiclePhysicsBundleExtractor/1", "ready": True},
        )
        _write_json(out / "pipeline_run.json", {"fixture": True})
        return {
            "format": "SHIFT.OfflineResourcePipelineRun/1",
            "resource_bootstrap_ready": True,
            "blocking_reasons": [],
        }

    monkeypatch.setattr(runtime_bootstrap, "run_offline_pipeline", fake_run)
    monkeypatch.setattr(
        runtime_bootstrap,
        "build_retail_archive_identity_admission",
        lambda catalog, bootstrap, *, track, vehicle: _ready_retail_archive_admission(),
    )
    return observed


def _ready_loader(kind):
    return {
        "format": kind,
        "ready": True,
        "status": "ready",
        "blocking_reasons": [],
    }


def _participant_boundary(*, ready=True):
    return {
        "format": "SHIFT.NativePhysicsParticipantBoundary/1",
        "ready": ready,
        "status": "ready" if ready else "blocked",
        "blocking_reasons": [] if ready else ["fixture-blocked"],
        "participant_instance_ready": False,
    }


def test_runtime_bootstrap_composes_existing_stages_without_claiming_runtime(
    monkeypatch,
    tmp_path,
):
    observed = _install_resource_pipeline_fixture(monkeypatch, tmp_path)
    monkeypatch.setattr(
        runtime_bootstrap,
        "load_track",
        lambda catalog, graph, *, track: _ready_loader("SHIFT.OfflineTrackLoad/1"),
    )
    monkeypatch.setattr(
        runtime_bootstrap,
        "load_vehicle",
        lambda catalog, graph, *, vehicle: _ready_loader("SHIFT.OfflineVehicleLoad/1"),
    )

    def fake_scene_ir(inputs, output_dir):
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        report = {
            "format": "SHIFT.OfflineSceneIRMaterialization/1",
            "ready": True,
            "status": "ready",
            "blocking_reasons": [],
        }
        _write_json(out / "scene_ir_materialization.json", report)
        return report

    monkeypatch.setattr(runtime_bootstrap, "build_scene_ir", fake_scene_ir)
    scene_call = {}

    def fake_native_scene(sgb_path, ir_root, output_dir, **kwargs):
        scene_call["sgb"] = Path(sgb_path)
        scene_call["ir"] = Path(ir_root)
        scene_call["kwargs"] = kwargs
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        report = {
            "format": "SHIFT.OfflineNativeSceneBuild/1",
            "static_resource_ready": True,
            "native_scene_runtime_ready": False,
            "blocking_reasons": ["runtime:runtime-proven-draw-admission-required"],
        }
        _write_json(out / "native_scene_build.json", report)
        return report

    monkeypatch.setattr(runtime_bootstrap, "build_native_scene_files", fake_native_scene)
    vehicle_call = {}

    def fake_native_vehicle(catalog, bootstrap, physics, output_dir, **kwargs):
        vehicle_call["kwargs"] = kwargs
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        report = {
            "format": "SHIFT.OfflineNativeVehicleBuild/1",
            "resource_ready": True,
            "participant_structural_ready": True,
            "participant_boundary": _participant_boundary(),
            "runtime_physics_contract_ready": True,
            "native_vehicle_runtime_ready": False,
            "blocking_reasons": [],
        }
        _write_json(out / "native_vehicle_build.json", report)
        return report

    monkeypatch.setattr(runtime_bootstrap, "build_native_vehicle_files", fake_native_vehicle)

    out = tmp_path / "bootstrap"
    report = runtime_bootstrap.build_offline_runtime_bootstrap(
        ["corpus.zip"],
        out,
        track="Track",
        vehicle="Car",
        decode_limit_per_archive=7,
        root_consensus_path="root.json",
        runtime_shader_admission_path="shader.json",
    )

    assert report["offline_build_ready"] is True
    assert report["runtime_ready"] is False
    assert report["status"] == "offline-native-build-ready-runtime-gated"
    assert report["readiness"]["retail_archive_identity_ready"] is True
    assert report["readiness"]["vehicle_participant_structural_ready"] is True
    assert report["readiness"]["vehicle_runtime_physics_contract_ready"] is True
    assert "runtime-scene:runtime-proven-draw-admission-required" in report["blocking_reasons"]
    assert (
        "runtime-vehicle:participant-input-and-fixed-step-runtime-gates-required"
        in report["blocking_reasons"]
    )
    assert scene_call["sgb"].name == "scene.sgb"
    assert scene_call["ir"] == out / "scene-ir"
    assert scene_call["kwargs"]["root_consensus_path"] == "root.json"
    assert scene_call["kwargs"]["runtime_shader_admission_path"] == "shader.json"
    assert Path(vehicle_call["kwargs"]["typed_closure_path"]) == (
        out / "resources" / "typed_resource_closure.json"
    )
    assert observed["decode_limit"] == 7
    persisted = json.loads((out / "runtime_bootstrap.json").read_text(encoding="utf-8"))
    assert persisted["boundary"]["retail_archive_name_alone_is_admission_proof"] is False
    assert persisted["boundary"]["retail_archive_sha256_and_unique_occurrence_required"] is True
    assert persisted["boundary"]["static_scene_promoted_to_runtime_draw_proof"] is False
    assert persisted["boundary"]["vehicle_participant_structural_boundary_required"] is True
    assert persisted["boundary"]["vehicle_resource_manifest_promoted_to_participant_identity"] is False
    assert Path(persisted["artifacts"]["retail_archive_identity_admission"]).is_file()


def test_retail_archive_identity_blocks_native_scene_and_vehicle_admission(
    monkeypatch,
    tmp_path,
):
    _install_resource_pipeline_fixture(monkeypatch, tmp_path)
    monkeypatch.setattr(
        runtime_bootstrap,
        "build_retail_archive_identity_admission",
        lambda *args, **kwargs: {
            "format": "SHIFT.RetailArchiveIdentityAdmission/1",
            "status": "blocked",
            "ready": False,
            "blocking_reasons": ["retail-archive-sha256-mismatch:vehicle_primary"],
        },
    )
    monkeypatch.setattr(
        runtime_bootstrap,
        "load_track",
        lambda catalog, graph, *, track: _ready_loader("SHIFT.OfflineTrackLoad/1"),
    )
    monkeypatch.setattr(
        runtime_bootstrap,
        "load_vehicle",
        lambda catalog, graph, *, vehicle: _ready_loader("SHIFT.OfflineVehicleLoad/1"),
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

    def forbidden(*args, **kwargs):
        raise AssertionError("native admission must not run after retail archive identity failure")

    monkeypatch.setattr(runtime_bootstrap, "build_native_scene_files", forbidden)
    monkeypatch.setattr(runtime_bootstrap, "build_native_vehicle_files", forbidden)

    report = runtime_bootstrap.build_offline_runtime_bootstrap(
        ["corpus.zip"],
        tmp_path / "bootstrap",
        track="Silverstone_Era3_GrandPrix",
        vehicle="BMW_M3_E36",
    )

    assert report["offline_build_ready"] is False
    assert report["status"] == "resource-blocked"
    assert report["readiness"]["retail_archive_identity_ready"] is False
    assert any(
        reason.startswith("retail-archive-identity:retail-archive-sha256-mismatch")
        for reason in report["blocking_reasons"]
    )
    assert report["readiness"]["static_scene_ready"] is False
    assert report["readiness"]["vehicle_resource_ready"] is False


def test_missing_exact_typed_sgb_blocks_scene_without_invoking_builder(
    monkeypatch,
    tmp_path,
):
    _install_resource_pipeline_fixture(monkeypatch, tmp_path, include_sgb=False)
    monkeypatch.setattr(
        runtime_bootstrap,
        "load_track",
        lambda catalog, graph, *, track: _ready_loader("SHIFT.OfflineTrackLoad/1"),
    )
    monkeypatch.setattr(
        runtime_bootstrap,
        "load_vehicle",
        lambda catalog, graph, *, vehicle: _ready_loader("SHIFT.OfflineVehicleLoad/1"),
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

    def should_not_run(*args, **kwargs):
        raise AssertionError("native scene builder must not run without exact typed SGB root")

    monkeypatch.setattr(runtime_bootstrap, "build_native_scene_files", should_not_run)
    monkeypatch.setattr(
        runtime_bootstrap,
        "build_native_vehicle_files",
        lambda *args, **kwargs: {
            "format": "SHIFT.OfflineNativeVehicleBuild/1",
            "resource_ready": True,
            "participant_structural_ready": True,
            "participant_boundary": _participant_boundary(),
            "runtime_physics_contract_ready": False,
            "native_vehicle_runtime_ready": False,
            "blocking_reasons": [],
        },
    )

    report = runtime_bootstrap.build_offline_runtime_bootstrap(
        ["corpus.zip"],
        tmp_path / "bootstrap",
        track="Track",
        vehicle="Car",
    )

    assert report["offline_build_ready"] is False
    assert report["status"] == "offline-native-build-blocked"
    assert any(
        reason.startswith("native-scene:typed-root-missing:res-sgb")
        for reason in report["blocking_reasons"]
    )


def test_participant_structural_boundary_is_an_offline_build_gate(monkeypatch, tmp_path):
    _install_resource_pipeline_fixture(monkeypatch, tmp_path)
    monkeypatch.setattr(
        runtime_bootstrap,
        "load_track",
        lambda catalog, graph, *, track: _ready_loader("SHIFT.OfflineTrackLoad/1"),
    )
    monkeypatch.setattr(
        runtime_bootstrap,
        "load_vehicle",
        lambda catalog, graph, *, vehicle: _ready_loader("SHIFT.OfflineVehicleLoad/1"),
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
            "blocking_reasons": [],
        },
    )
    monkeypatch.setattr(
        runtime_bootstrap,
        "build_native_vehicle_files",
        lambda *args, **kwargs: {
            "format": "SHIFT.OfflineNativeVehicleBuild/1",
            "resource_ready": True,
            "participant_structural_ready": False,
            "participant_boundary": _participant_boundary(ready=False),
            "runtime_physics_contract_ready": True,
            "native_vehicle_runtime_ready": False,
            "blocking_reasons": ["participant-boundary:fixture-blocked"],
        },
    )

    report = runtime_bootstrap.build_offline_runtime_bootstrap(
        ["corpus.zip"],
        tmp_path / "bootstrap",
        track="Track",
        vehicle="Car",
    )

    assert report["offline_build_ready"] is False
    assert report["status"] == "offline-native-build-blocked"
    assert report["readiness"]["vehicle_resource_ready"] is True
    assert report["readiness"]["vehicle_participant_structural_ready"] is False
    assert "participant-boundary:fixture-blocked" in report["blocking_reasons"]


def test_runtime_ready_is_derived_from_future_proven_stage_outputs(monkeypatch, tmp_path):
    _install_resource_pipeline_fixture(monkeypatch, tmp_path)
    monkeypatch.setattr(
        runtime_bootstrap,
        "load_track",
        lambda catalog, graph, *, track: _ready_loader("SHIFT.OfflineTrackLoad/1"),
    )
    monkeypatch.setattr(
        runtime_bootstrap,
        "load_vehicle",
        lambda catalog, graph, *, vehicle: _ready_loader("SHIFT.OfflineVehicleLoad/1"),
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
            "native_scene_runtime_ready": True,
            "blocking_reasons": [],
        },
    )
    monkeypatch.setattr(
        runtime_bootstrap,
        "build_native_vehicle_files",
        lambda *args, **kwargs: {
            "format": "SHIFT.OfflineNativeVehicleBuild/1",
            "resource_ready": True,
            "participant_structural_ready": True,
            "participant_boundary": _participant_boundary(),
            "runtime_physics_contract_ready": True,
            "native_vehicle_runtime_ready": True,
            "blocking_reasons": [],
        },
    )

    report = runtime_bootstrap.build_offline_runtime_bootstrap(
        ["corpus.zip"],
        tmp_path / "bootstrap",
        track="Track",
        vehicle="Car",
    )

    assert report["offline_build_ready"] is True
    assert report["runtime_ready"] is True
    assert report["status"] == "runtime-ready"
    assert not any(reason.startswith("runtime-scene:") for reason in report["blocking_reasons"])
    assert not any(reason.startswith("runtime-vehicle:") for reason in report["blocking_reasons"])
