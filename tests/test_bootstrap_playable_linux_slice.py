from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_cli():
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "bootstrap_playable_linux_slice_cli",
        root / "tools" / "bootstrap_playable_linux_slice.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _args(tmp_path: Path) -> list[str]:
    return [
        "Vehicles.zip",
        "Silverstone_Era3_.zip",
        "SHIFT_tail.zip",
        "-o",
        str(tmp_path / "out"),
        "--track",
        "Silverstone_Era3_GrandPrix",
        "--vehicle",
        "BMW_M3_E36",
        "--workspace-root",
        str(tmp_path),
        "--keyboard",
        "--renderer-capture-jsonl",
        "shift_d3d9_capture.jsonl",
        "--renderer-pe-evidence",
        "pe.json",
    ]


def _write_base_report(out: Path) -> None:
    track = out / "renderer-native-scene" / "native-scene-vulkan"
    track.mkdir(parents=True, exist_ok=True)
    stale_profile = out / "vertical_slice_profile.json"
    stale_profile.write_text('{"scene_set":"track-only"}\n', encoding="utf-8")
    runtime_bootstrap = {
        "format": "SHIFT.OfflineRuntimeBootstrap/1",
        "offline_build_ready": True,
        "runtime_ready": False,
        "track": "Silverstone_Era3_GrandPrix",
        "vehicle": "BMW_M3_E36",
        "readiness": {
            "vehicle_runtime_physics_contract_ready": False,
            "vehicle_participant_runtime_identity_ready": False,
            "runtime_scene_ready": False,
        },
        "artifacts": {},
        "stages": {"native_vehicle": {"artifacts": {}}},
    }
    report = {
        "format": "SHIFT.OfflineNativeVerticalSliceBootstrap/1",
        "version": 1,
        "status": "profile-ready",
        "ready": True,
        "offline_bootstrap_ready": True,
        "profile_ready": True,
        "launch_plan_ready": False,
        "renderer_evidence_ready": True,
        "renderer_native_scene_ready": True,
        "blocking_reasons": ["profile:old-track-only-diagnostic"],
        "stages": {
            "runtime_bootstrap": runtime_bootstrap,
            "renderer_native_scene_handoff": {
                "format": "SHIFT.RendererNativeSceneHandoff/1",
                "ready": True,
                "scene_set_ready": True,
                "artifacts": {"scene_set_dir": str(track)},
            },
        },
        "artifacts": {
            "profile": str(stale_profile),
            "runtime_requirements": str(out / "runtime_requirements.json"),
            "profile_prepare": str(out / "vertical_slice_profile.prepare.json"),
            "launch_plan": None,
        },
        "boundary": {"runtime_execution_claimed": False},
    }
    (out / "vertical_slice_bootstrap.json").write_text(
        json.dumps(report),
        encoding="utf-8",
    )


def test_playable_cli_rebuilds_profile_with_generated_composite_scene(
    monkeypatch,
    tmp_path,
):
    cli = _load_cli()
    out = tmp_path / "out"
    base_calls = []
    helper_calls = []
    launch_calls = []

    def base_main(argv):
        base_calls.append(list(argv))
        _write_base_report(out)
        return 0

    composite = out / "playable-scene" / "native-playable-scene"

    def helper(inputs, track_scene_set, output_dir, **kwargs):
        helper_calls.append((list(inputs), str(track_scene_set), Path(output_dir), kwargs))
        composite.mkdir(parents=True, exist_ok=True)
        return {
            "format": "SHIFT.NativePlayableSceneBootstrap/1",
            "ready": True,
            "scene_set_ready": True,
            "status": "ready",
            "blocking_reasons": [],
            "artifacts": {
                "scene_set_dir": str(composite),
                "vehicle_material_admission": str(Path(output_dir) / "vehicle-material-admission" / "admission.json"),
                "vehicle_material_slice_set": str(Path(output_dir) / "vehicle-material-admission" / "material_slice_set.json"),
            },
            "boundary": {},
        }

    def validate(**kwargs):
        scene = str(kwargs["explicit_inputs"]["scene_set"])
        assert scene == str(composite)
        return {
            "scene_set": {
                "format": "SHIFT.OfflineValidatedRuntimeInput/1",
                "name": "scene_set",
                "ready": True,
                "artifact": scene,
                "source": "explicit",
                "blocking_reasons": [],
                "validation": {"ready": True},
            }
        }

    def requirements(runtime_bootstrap, *, validated_runtime_inputs):
        assert runtime_bootstrap["format"] == "SHIFT.OfflineRuntimeBootstrap/1"
        assert validated_runtime_inputs["scene_set"]["artifact"] == str(composite)
        assert validated_runtime_inputs["scene_set"]["source"] == (
            "Phase 644 generated playable scene"
        )
        return {
            "format": "SHIFT.OfflineNativeRuntimeRequirements/1",
            "ready": True,
            "blocking_reasons": [],
        }

    def prepare(requirements, **kwargs):
        assert requirements["ready"] is True
        assert str(kwargs["explicit_inputs"]["scene_set"]) == str(composite)
        return {
            "format": "SHIFT.NativeVerticalSliceProfilePrepare/1",
            "ready": True,
            "blocking_reasons": [],
            "profile": {
                "format": "SHIFT.NativeVerticalSliceProfile/1",
                "scene_set": str(composite),
            },
        }

    def launch(profile_path, **kwargs):
        launch_calls.append((Path(profile_path), kwargs))
        profile = json.loads(Path(profile_path).read_text())
        assert profile["scene_set"] == str(composite)
        return {"format": "SHIFT.NativeVerticalSliceLaunchPlan/1", "ready": True}

    monkeypatch.setattr(cli, "base_main", base_main)
    monkeypatch.setattr(cli, "build_native_playable_scene_bootstrap", helper)
    monkeypatch.setattr(cli, "validate_explicit_runtime_inputs", validate)
    monkeypatch.setattr(cli, "build_runtime_requirements", requirements)
    monkeypatch.setattr(cli, "build_vertical_slice_profile_prepare", prepare)
    monkeypatch.setattr(cli, "build_launch_plan", launch)

    rc = cli.main(_args(tmp_path) + ["--validate-launch-plan"])

    assert rc == 0
    assert len(base_calls) == 1
    assert "--validate-launch-plan" not in base_calls[0]
    assert len(helper_calls) == 1
    assert helper_calls[0][0] == [
        "Vehicles.zip",
        "Silverstone_Era3_.zip",
        "SHIFT_tail.zip",
    ]
    assert helper_calls[0][3]["vehicle"] == "BMW_M3_E36"
    assert len(launch_calls) == 1

    report = json.loads((out / "vertical_slice_bootstrap.json").read_text())
    assert report["status"] == "launch-plan-ready"
    assert report["ready"] is True
    assert report["playable_scene_requested"] is True
    assert report["playable_scene_ready"] is True
    assert report["artifacts"]["playable_scene_set"] == str(composite)
    assert report["boundary"]["manual_vehicle_material_slice_handoff_required"] is False
    assert report["boundary"]["phase643_composite_scene_consumed"] is True
    assert report["boundary"]["phase700_runtime_pose_handoff_consumed"] is False
    assert all("old-track-only" not in reason for reason in report["blocking_reasons"])


def test_playable_cli_drops_track_only_profile_when_composition_blocks(
    monkeypatch,
    tmp_path,
):
    cli = _load_cli()
    out = tmp_path / "out"

    def base_main(argv):
        _write_base_report(out)
        (out / "launch_plan.json").write_text("{}\n", encoding="utf-8")
        return 0

    monkeypatch.setattr(cli, "base_main", base_main)
    monkeypatch.setattr(
        cli,
        "build_native_playable_scene_bootstrap",
        lambda *args, **kwargs: {
            "format": "SHIFT.NativePlayableSceneBootstrap/1",
            "ready": False,
            "scene_set_ready": False,
            "status": "blocked",
            "blocking_reasons": [
                "playable-scene-corpus:archive-missing:RENDER.bff"
            ],
            "artifacts": {
                "scene_set_dir": None,
                "vehicle_material_admission": None,
                "vehicle_material_slice_set": None,
            },
        },
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("blocked composition must not reach profile/launcher refresh")

    monkeypatch.setattr(cli, "validate_explicit_runtime_inputs", forbidden)
    monkeypatch.setattr(cli, "build_launch_plan", forbidden)

    rc = cli.main(_args(tmp_path))

    assert rc == 2
    assert not (out / "vertical_slice_profile.json").exists()
    assert not (out / "launch_plan.json").exists()
    report = json.loads((out / "vertical_slice_bootstrap.json").read_text())
    assert report["status"] == "playable-scene-blocked"
    assert report["ready"] is False
    assert report["profile_ready"] is False
    assert report["playable_scene_ready"] is False
    assert any("RENDER.bff" in reason for reason in report["blocking_reasons"])
