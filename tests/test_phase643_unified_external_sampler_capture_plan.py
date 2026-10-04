from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_cli():
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "bootstrap_native_vertical_slice_phase643_tested",
        root / "tools" / "bootstrap_native_vertical_slice.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _base_report(out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    runtime_bootstrap = out / "runtime-bootstrap" / "runtime_bootstrap.json"
    runtime_bootstrap.parent.mkdir(parents=True, exist_ok=True)
    runtime_bootstrap.write_text(
        json.dumps({
            "format": "SHIFT.OfflineRuntimeBootstrap/1",
            "offline_build_ready": True,
        }),
        encoding="utf-8",
    )
    return {
        "format": "SHIFT.OfflineNativeVerticalSliceBootstrap/1",
        "version": 1,
        "status": "profile-blocked",
        "ready": False,
        "offline_bootstrap_ready": True,
        "profile_ready": False,
        "launch_plan_ready": False,
        "track": "Silverstone_Era3_GrandPrix",
        "vehicle": "BMW_M3_E36",
        "blocking_reasons": ["profile:scene-set-missing"],
        "stages": {
            "runtime_bootstrap": {
                "format": "SHIFT.OfflineRuntimeBootstrap/1",
                "offline_build_ready": True,
            },
        },
        "artifacts": {
            "runtime_bootstrap": str(runtime_bootstrap),
            "runtime_requirements": str(out / "runtime_requirements.json"),
            "profile_prepare": str(out / "vertical_slice_profile.prepare.json"),
            "profile": None,
            "launch_plan": None,
        },
        "boundary": {
            "launcher_validation_performed": False,
            "runtime_execution_claimed": False,
        },
    }


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


def _ready_renderer() -> dict:
    return {
        "format": "SHIFT.SilverstoneRendererSourceBootstrapProductionRun/1",
        "status": "completed",
        "ready": True,
        "blocking_reasons": [],
        "self_bootstrap": {
            "production": {
                "renderer_frontier": {
                    "status": "continue-offline",
                },
            },
        },
    }


def _requirement() -> dict:
    return {
        "binding_index": 17,
        "draw_order": 4,
        "register": 7,
        "sampler": "shadowMap",
        "sampler_type": "sampler2D",
        "reason": "snapshot-content-not-captured",
        "expected_d3d9_resource_type": "texture2d",
        "required_snapshot_path_count": 1,
        "requested_texture_stage": 7,
        "capture_frames": [3547],
        "capture_draw_indices": [92],
    }


def _capture_required_handoff(*, declared_count: int = 1) -> dict:
    return {
        "format": "SHIFT.RendererNativeSceneHandoff/1",
        "status": "blocked",
        "ready": False,
        "scene_set_ready": False,
        "blocking_reasons": [
            "phase590:scene-external-capture:binding-17:s7:"
            "snapshot-content-not-captured"
        ],
        "boundary": {
            "capture_observation_required": True,
            "capture_observation_requirement_count": declared_count,
            "new_capture_required": False,
        },
        "existing_capture_completion": {
            "runtime_evidence_required": [_requirement()],
        },
        "artifacts": {"scene_set_dir": None},
    }


def _noncapture_handoff() -> dict:
    return {
        "format": "SHIFT.RendererNativeSceneHandoff/1",
        "status": "blocked",
        "ready": False,
        "scene_set_ready": False,
        "blocking_reasons": [
            "phase591:scene-instance-match:binding-17:"
            "world-matrix-constant-window-not-found"
        ],
        "boundary": {
            "capture_observation_required": False,
            "capture_observation_requirement_count": 0,
            "new_capture_required": False,
        },
        "existing_capture_completion": {
            "runtime_evidence_required": [],
        },
        "artifacts": {"scene_set_dir": None},
    }


def _install_common(monkeypatch, cli, out: Path, scene_handoff: dict) -> None:
    monkeypatch.setattr(
        cli,
        "build_offline_vertical_slice_bootstrap",
        lambda *args, **kwargs: _base_report(out),
    )
    monkeypatch.setattr(
        cli,
        "run_source_bootstrap_production",
        lambda **kwargs: _ready_renderer(),
    )
    monkeypatch.setattr(
        cli,
        "materialize_renderer_native_scene_handoff",
        lambda **kwargs: scene_handoff,
    )

    def refresh(report, **kwargs):
        report["profile_ready"] = False
        report["ready"] = False
        report["status"] = "profile-blocked"
        return ["profile:scene_set:explicit-input-required"]

    monkeypatch.setattr(cli, "_refresh_runtime_profile", refresh)


def test_unified_bootstrap_materializes_exact_phase642_capture_plan(
    monkeypatch,
    tmp_path,
):
    cli = _load_cli()
    out = tmp_path / "out"
    _install_common(monkeypatch, cli, out, _capture_required_handoff())

    rc = cli.main(_args(tmp_path))

    assert rc == 2
    plan_path = (
        out / "renderer-native-scene" / "external_sampler_capture_plan.json"
    )
    assert plan_path.is_file()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert plan["format"] == "SHIFT.Phase641ExternalSamplerCapturePlan/1"
    assert plan["ready"] is True
    assert plan["texture_stage_list"] == [7]
    assert plan["texture_stages"] == "7"

    persisted = json.loads(
        (out / "vertical_slice_bootstrap.json").read_text(encoding="utf-8")
    )
    assert persisted["status"] == "renderer-native-scene-blocked"
    assert persisted["renderer_capture_observation_required"] is True
    assert persisted["renderer_capture_plan_ready"] is True
    assert persisted["artifacts"][
        "renderer_external_sampler_capture_plan"
    ] == str(plan_path)
    assert persisted["stages"][
        "renderer_external_sampler_capture_plan"
    ]["texture_stages"] == "7"
    assert persisted["boundary"]["phase642_capture_plan_required"] is True
    assert persisted["boundary"]["phase642_capture_plan_ready"] is True
    assert persisted["boundary"]["generic_renderer_recapture_inferred"] is False
    assert persisted["boundary"]["renderer_capture_execution_claimed"] is False
    assert all(
        not reason.startswith("renderer-capture-plan:")
        for reason in persisted["blocking_reasons"]
    )


def test_unified_bootstrap_does_not_plan_noncapture_scene_blocker(
    monkeypatch,
    tmp_path,
):
    cli = _load_cli()
    out = tmp_path / "out"
    _install_common(monkeypatch, cli, out, _noncapture_handoff())
    stale = out / "renderer-native-scene" / "external_sampler_capture_plan.json"
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.write_text('{"stale":true}\n', encoding="utf-8")

    def forbidden(*args, **kwargs):
        raise AssertionError("non-capture Phase 641 blocker must not invoke Phase 642")

    monkeypatch.setattr(cli, "build_capture_plan", forbidden)
    rc = cli.main(_args(tmp_path))

    assert rc == 2
    assert not stale.exists()
    persisted = json.loads(
        (out / "vertical_slice_bootstrap.json").read_text(encoding="utf-8")
    )
    assert persisted["renderer_capture_observation_required"] is False
    assert persisted["renderer_capture_plan_ready"] is False
    assert persisted["artifacts"][
        "renderer_external_sampler_capture_plan"
    ] is None
    assert persisted["boundary"]["generic_renderer_recapture_inferred"] is False


def test_unified_bootstrap_rejects_inconsistent_phase641_capture_frontier(
    monkeypatch,
    tmp_path,
):
    cli = _load_cli()
    out = tmp_path / "out"
    _install_common(
        monkeypatch,
        cli,
        out,
        _capture_required_handoff(declared_count=2),
    )

    rc = cli.main(_args(tmp_path))

    assert rc == 2
    plan_path = (
        out / "renderer-native-scene" / "external_sampler_capture_plan.json"
    )
    assert not plan_path.exists()
    persisted = json.loads(
        (out / "vertical_slice_bootstrap.json").read_text(encoding="utf-8")
    )
    assert persisted["renderer_capture_observation_required"] is True
    assert persisted["renderer_capture_plan_ready"] is False
    assert persisted["artifacts"][
        "renderer_external_sampler_capture_plan"
    ] is None
    assert any(
        "capture-observation-count-mismatch" in reason
        for reason in persisted["blocking_reasons"]
    )
