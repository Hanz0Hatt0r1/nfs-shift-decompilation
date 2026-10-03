from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from offline_runtime_requirements import FORMAT, build_runtime_requirements


def _bootstrap() -> dict:
    return {
        "format": "SHIFT.OfflineRuntimeBootstrap/1",
        "version": 1,
        "status": "offline-native-build-ready-runtime-gated",
        "offline_build_ready": True,
        "runtime_ready": False,
        "track": "Silverstone_Era3_GrandPrix",
        "vehicle": "BMW_M3_E36",
        "blocking_reasons": [
            "runtime-scene:runtime-proven-draw-admission-required",
            "runtime-vehicle:participant-input-binding-required",
        ],
        "readiness": {
            "resource_bootstrap_ready": True,
            "track_load_ready": True,
            "vehicle_load_ready": True,
            "scene_ir_ready": True,
            "static_scene_ready": True,
            "vehicle_resource_ready": True,
            "vehicle_participant_structural_ready": True,
            "vehicle_participant_runtime_identity_evaluated": True,
            "vehicle_participant_runtime_identity_ready": True,
            "vehicle_runtime_physics_contract_ready": True,
            "runtime_scene_ready": False,
            "runtime_vehicle_ready": False,
        },
        "artifacts": {
            "participant_runtime_evidence": "out/native-vehicle/native_physics_participant_runtime_evidence.json",
        },
        "stages": {
            "native_vehicle": {
                "artifacts": {
                    "native_physics_manifest": {
                        "path": "out/native-vehicle/native_physics_manifest.json",
                        "sha256": "a" * 64,
                    },
                    "participant_runtime_evidence": {
                        "path": "out/native-vehicle/native_physics_participant_runtime_evidence.json",
                        "sha256": "b" * 64,
                    },
                }
            }
        },
    }


def _scene_handoff(*, ready: bool = True) -> dict:
    return {
        "format": "SHIFT.RendererNativeSceneHandoff/1",
        "ready": ready,
        "scene_set_ready": ready,
        "artifacts": {
            "scene_set_dir": "out/renderer-native-scene/native-scene-vulkan"
            if ready
            else None,
        },
    }


def test_requirements_reuse_only_proven_bootstrap_runtime_artifacts():
    report = build_runtime_requirements(_bootstrap())

    assert report["format"] == FORMAT
    assert report["ready"] is False
    assert report["summary"]["requirement_count"] == 10
    assert report["summary"]["satisfied"] == [
        "physics_manifest",
        "participant_boundary",
    ]
    assert report["summary"]["missing_count"] == 8
    assert "scene_set" in report["summary"]["missing"]
    assert "camera_state" in report["summary"]["missing"]
    assert "input_binding" in report["summary"]["missing"]

    rows = {row["name"]: row for row in report["requirements"]}
    assert rows["physics_manifest"]["artifact"].endswith(
        "native_physics_manifest.json"
    )
    assert rows["participant_boundary"]["artifact"].endswith(
        "native_physics_participant_runtime_evidence.json"
    )
    assert rows["scene_set"]["satisfied"] is False
    assert rows["scene_set"]["artifact"] is None
    assert report["boundary"]["missing_evidence_synthesized"] is False
    assert report["boundary"]["artifact_substitution_allowed"] is False
    assert report["boundary"]["static_scene_promoted_to_runtime_scene"] is False


def test_requirements_accept_only_ready_renderer_native_scene_handoff():
    report = build_runtime_requirements(
        _bootstrap(),
        runtime_scene_handoff=_scene_handoff(),
    )
    rows = {row["name"]: row for row in report["requirements"]}

    assert rows["scene_set"]["satisfied"] is True
    assert rows["scene_set"]["artifact"] == (
        "out/renderer-native-scene/native-scene-vulkan"
    )
    assert rows["scene_set"]["source"] == (
        "runtime-proven renderer native scene handoff"
    )
    assert "scene_set" not in report["summary"]["missing"]
    assert report["boundary"]["runtime_scene_handoff_accepted"] is True

    blocked = build_runtime_requirements(
        _bootstrap(),
        runtime_scene_handoff=_scene_handoff(ready=False),
    )
    blocked_rows = {row["name"]: row for row in blocked["requirements"]}
    assert blocked_rows["scene_set"]["satisfied"] is False
    assert blocked_rows["scene_set"]["artifact"] is None


def test_requirements_reject_wrong_renderer_scene_handoff_contract():
    with pytest.raises(ValueError, match="RendererNativeSceneHandoff"):
        build_runtime_requirements(
            _bootstrap(),
            runtime_scene_handoff={"format": "wrong"},
        )


def test_requirements_do_not_promote_structural_participant_to_runtime_identity():
    bootstrap = _bootstrap()
    bootstrap["readiness"]["vehicle_participant_runtime_identity_ready"] = False
    bootstrap["artifacts"].pop("participant_runtime_evidence")

    report = build_runtime_requirements(bootstrap)
    rows = {row["name"]: row for row in report["requirements"]}

    assert rows["participant_boundary"]["satisfied"] is False
    assert rows["participant_boundary"]["artifact"] is None
    assert "participant_boundary" in report["summary"]["missing"]


def test_requirements_reject_wrong_bootstrap_contract():
    with pytest.raises(ValueError, match="OfflineRuntimeBootstrap"):
        build_runtime_requirements({"format": "wrong"})


def test_bootstrap_cli_writes_requirements_without_making_them_an_exit_gate(
    monkeypatch,
    tmp_path,
):
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "bootstrap_runtime_requirements_cli",
        root / "tools" / "bootstrap_runtime.py",
    )
    assert spec is not None and spec.loader is not None
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    def fake_bootstrap(*args, **kwargs):
        output = Path(args[1])
        output.mkdir(parents=True, exist_ok=True)
        value = _bootstrap()
        (output / "runtime_bootstrap.json").write_text(
            json.dumps(value),
            encoding="utf-8",
        )
        return value

    monkeypatch.setattr(cli, "build_offline_runtime_bootstrap", fake_bootstrap)

    out = tmp_path / "runtime"
    rc = cli.main([
        "Vehicles.zip",
        "Silverstone_Era3_.zip",
        "-o",
        str(out),
        "--track",
        "Silverstone_Era3_GrandPrix",
        "--vehicle",
        "BMW_M3_E36",
    ])

    assert rc == 0
    written = json.loads((out / "runtime_requirements.json").read_text())
    assert written["format"] == FORMAT
    assert written["ready"] is False
    assert written["summary"]["satisfied"] == [
        "physics_manifest",
        "participant_boundary",
    ]
    assert "scene_set" in written["summary"]["missing"]
