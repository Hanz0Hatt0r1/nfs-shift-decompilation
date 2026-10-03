from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


def _load_cli():
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "bootstrap_native_vertical_slice_renderer_cli",
        root / "tools" / "bootstrap_native_vertical_slice.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _base_report(out: Path, *, offline_ready: bool = True, profile_ready: bool = True):
    out.mkdir(parents=True, exist_ok=True)
    runtime_bootstrap = out / "runtime-bootstrap" / "runtime_bootstrap.json"
    runtime_bootstrap.parent.mkdir(parents=True, exist_ok=True)
    runtime_bootstrap_value = {
        "format": "SHIFT.OfflineRuntimeBootstrap/1",
        "offline_build_ready": offline_ready,
    }
    runtime_bootstrap.write_text(
        json.dumps(runtime_bootstrap_value),
        encoding="utf-8",
    )
    profile = out / "vertical_slice_profile.json"
    if profile_ready:
        profile.write_text(
            json.dumps({"format": "SHIFT.NativeVerticalSliceProfile/1"}),
            encoding="utf-8",
        )
    if not offline_ready:
        status = "offline-bootstrap-blocked"
        blockers = ["offline-bootstrap:resource-identity-blocked"]
    elif not profile_ready:
        status = "profile-blocked"
        blockers = ["profile:scene-set-missing"]
    else:
        status = "profile-ready"
        blockers = []
    return {
        "format": "SHIFT.OfflineNativeVerticalSliceBootstrap/1",
        "version": 1,
        "status": status,
        "ready": profile_ready and offline_ready,
        "offline_bootstrap_ready": offline_ready,
        "profile_ready": profile_ready and offline_ready,
        "launch_plan_ready": False,
        "track": "Silverstone_Era3_GrandPrix",
        "vehicle": "BMW_M3_E36",
        "blocking_reasons": blockers,
        "stages": {"runtime_bootstrap": runtime_bootstrap_value},
        "artifacts": {
            "runtime_bootstrap": str(runtime_bootstrap),
            "runtime_requirements": str(out / "runtime_requirements.json"),
            "profile_prepare": str(out / "vertical_slice_profile.prepare.json"),
            "profile": str(profile) if profile_ready and offline_ready else None,
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
    ]


def _ready_renderer():
    return {
        "format": "SHIFT.SilverstoneRendererSourceBootstrapProductionRun/1",
        "status": "completed",
        "ready": True,
        "summary": {
            "production_completed": True,
            "object_candidate_join_regeneration_ready": True,
        },
        "self_bootstrap": {
            "production": {
                "status": "completed",
                "renderer_frontier": {
                    "status": "continue-offline",
                    "existing_data_requiring_tooling": [{
                        "requirement_id": "scene_resource_exact_draw_attribution",
                        "status": "ambiguous",
                        "next_step": "use existing spatial evidence",
                    }],
                    "genuinely_absent_capture_observations": [],
                    "capture_blockers": [],
                    "conditional_minimal_capture": [],
                },
            },
        },
        "blocking_reasons": [],
    }


def _ready_scene_handoff(tmp_path: Path) -> dict:
    root = tmp_path / "out" / "renderer-native-scene" / "native-scene-vulkan"
    root.mkdir(parents=True, exist_ok=True)
    return {
        "format": "SHIFT.RendererNativeSceneHandoff/1",
        "status": "ready",
        "ready": True,
        "scene_set_ready": True,
        "blocking_reasons": [],
        "artifacts": {
            "scene_set_dir": str(root),
        },
    }


def test_unified_cli_passes_selected_runtime_bootstrap_to_renderer_and_scene_handoff(
    monkeypatch,
    tmp_path,
):
    cli = _load_cli()
    out = tmp_path / "out"
    renderer_calls = []
    scene_calls = []
    refresh_calls = []
    monkeypatch.setattr(
        cli,
        "build_offline_vertical_slice_bootstrap",
        lambda *args, **kwargs: _base_report(out),
    )

    def renderer(**kwargs):
        renderer_calls.append(kwargs)
        return _ready_renderer()

    def scene_handoff(**kwargs):
        scene_calls.append(kwargs)
        return _ready_scene_handoff(tmp_path)

    def refresh(report, **kwargs):
        refresh_calls.append(kwargs)
        report["profile_ready"] = True
        report["ready"] = True
        report["status"] = "profile-ready"
        return []

    monkeypatch.setattr(cli, "run_source_bootstrap_production", renderer)
    monkeypatch.setattr(cli, "materialize_renderer_native_scene_handoff", scene_handoff)
    monkeypatch.setattr(cli, "_refresh_runtime_profile", refresh)
    rc = cli.main(
        _args(tmp_path)
        + [
            "--renderer-capture-jsonl",
            "shift_d3d9_capture.jsonl",
            "--renderer-pe-evidence",
            "pe.json",
        ]
    )

    assert rc == 0
    assert len(renderer_calls) == 1
    renderer_call = renderer_calls[0]
    assert renderer_call["corpus"] == [
        "Vehicles.zip",
        "Silverstone_Era3_.zip",
        "SHIFT_tail.zip",
    ]
    assert renderer_call["runtime_bootstrap"] == str(
        out / "runtime-bootstrap" / "runtime_bootstrap.json"
    )
    assert renderer_call["capture_jsonl"] == "shift_d3d9_capture.jsonl"
    assert renderer_call["pe_evidence"] == "pe.json"
    assert renderer_call["pe_image"] is None

    assert len(scene_calls) == 1
    scene_call = scene_calls[0]
    assert scene_call["runtime_bootstrap"] == str(
        out / "runtime-bootstrap" / "runtime_bootstrap.json"
    )
    assert scene_call["renderer_source_bootstrap"] == str(
        out
        / "renderer-evidence"
        / "silverstone_renderer_source_bootstrap_production_run.json"
    )
    assert len(refresh_calls) == 1
    assert refresh_calls[0]["runtime_scene_handoff"]["scene_set_ready"] is True

    persisted = json.loads((out / "vertical_slice_bootstrap.json").read_text())
    assert persisted["ready"] is True
    assert persisted["renderer_evidence_requested"] is True
    assert persisted["renderer_evidence_ready"] is True
    assert persisted["renderer_native_scene_requested"] is True
    assert persisted["renderer_native_scene_ready"] is True
    assert persisted["renderer_frontier"]["status"] == "continue-offline"
    assert persisted["renderer_frontier"]["capture_blockers"] == []
    assert persisted["artifacts"]["renderer_source_bootstrap"] == str(
        out
        / "renderer-evidence"
        / "silverstone_renderer_source_bootstrap_production_run.json"
    )
    assert persisted["artifacts"]["renderer_native_scene_handoff"] == str(
        out / "renderer-native-scene" / "renderer_native_scene_handoff.json"
    )
    assert (
        persisted["boundary"]["manual_resource_to_renderer_handoff_required"]
        is False
    )
    assert persisted["boundary"]["renderer_bundle_is_selection_authority"] is False
    assert (
        persisted["boundary"]["renderer_scene_handoff_uses_existing_phase574_to_585_chain"]
        is True
    )


def test_ready_scene_handoff_replaces_old_profile_scene_blocker(
    monkeypatch,
    tmp_path,
):
    cli = _load_cli()
    out = tmp_path / "out"
    monkeypatch.setattr(
        cli,
        "build_offline_vertical_slice_bootstrap",
        lambda *args, **kwargs: _base_report(out, profile_ready=False),
    )
    monkeypatch.setattr(cli, "run_source_bootstrap_production", lambda **kwargs: _ready_renderer())
    monkeypatch.setattr(
        cli,
        "materialize_renderer_native_scene_handoff",
        lambda **kwargs: _ready_scene_handoff(tmp_path),
    )

    def refresh(report, **kwargs):
        assert kwargs["runtime_scene_handoff"]["ready"] is True
        report["profile_ready"] = True
        report["ready"] = True
        report["status"] = "profile-ready"
        return []

    monkeypatch.setattr(cli, "_refresh_runtime_profile", refresh)
    rc = cli.main(
        _args(tmp_path)
        + [
            "--renderer-capture-jsonl",
            "shift_d3d9_capture.jsonl",
            "--renderer-pe-evidence",
            "pe.json",
        ]
    )

    assert rc == 0
    persisted = json.loads((out / "vertical_slice_bootstrap.json").read_text())
    assert persisted["status"] == "profile-ready"
    assert persisted["profile_ready"] is True
    assert persisted["renderer_native_scene_ready"] is True
    assert all(
        not reason.startswith("profile:scene-set")
        for reason in persisted["blocking_reasons"]
    )


def test_explicit_scene_set_skips_renderer_native_scene_materialization(
    monkeypatch,
    tmp_path,
):
    cli = _load_cli()
    out = tmp_path / "out"
    monkeypatch.setattr(
        cli,
        "build_offline_vertical_slice_bootstrap",
        lambda *args, **kwargs: _base_report(out),
    )
    monkeypatch.setattr(cli, "run_source_bootstrap_production", lambda **kwargs: _ready_renderer())

    def forbidden_scene(*args, **kwargs):
        raise AssertionError("explicit scene_set must remain authoritative")

    monkeypatch.setattr(cli, "materialize_renderer_native_scene_handoff", forbidden_scene)
    rc = cli.main(
        _args(tmp_path)
        + [
            "--scene-set",
            str(tmp_path / "existing-scene-set"),
            "--renderer-capture-jsonl",
            "shift_d3d9_capture.jsonl",
            "--renderer-pe-evidence",
            "pe.json",
        ]
    )
    assert rc == 0
    persisted = json.loads((out / "vertical_slice_bootstrap.json").read_text())
    assert persisted["renderer_native_scene_requested"] is False
    assert persisted["renderer_native_scene_ready"] is True


def test_renderer_failure_blocks_unified_readiness_and_launcher_validation(
    monkeypatch,
    tmp_path,
):
    cli = _load_cli()
    out = tmp_path / "out"
    out.mkdir(parents=True)
    stale = out / "launch_plan.json"
    stale.write_text('{"stale":true}\n', encoding="utf-8")
    monkeypatch.setattr(
        cli,
        "build_offline_vertical_slice_bootstrap",
        lambda *args, **kwargs: _base_report(out),
    )
    monkeypatch.setattr(
        cli,
        "run_source_bootstrap_production",
        lambda **kwargs: {
            "format": "SHIFT.SilverstoneRendererSourceBootstrapProductionRun/1",
            "status": "blocked",
            "ready": False,
            "self_bootstrap": None,
            "blocking_reasons": ["production:phase625:object-candidate-required"],
        },
    )

    def forbidden_launcher(*args, **kwargs):
        raise AssertionError("launcher validation must not bypass renderer evidence")

    def forbidden_scene(*args, **kwargs):
        raise AssertionError("scene materialization must not bypass renderer evidence")

    monkeypatch.setattr(cli, "build_launch_plan", forbidden_launcher)
    monkeypatch.setattr(cli, "materialize_renderer_native_scene_handoff", forbidden_scene)
    rc = cli.main(
        _args(tmp_path)
        + [
            "--renderer-capture-jsonl",
            "shift_d3d9_capture.jsonl",
            "--renderer-pe-image",
            "SHIFT.exe",
            "--validate-launch-plan",
        ]
    )

    assert rc == 2
    assert not stale.exists()
    persisted = json.loads((out / "vertical_slice_bootstrap.json").read_text())
    assert persisted["status"] == "renderer-evidence-blocked"
    assert persisted["ready"] is False
    assert persisted["profile_ready"] is True
    assert persisted["renderer_evidence_ready"] is False
    assert persisted["renderer_native_scene_ready"] is False
    assert persisted["launch_plan_ready"] is False
    assert any(
        "object-candidate-required" in reason
        for reason in persisted["blocking_reasons"]
    )
    assert persisted["boundary"]["launcher_validation_performed"] is False


def test_renderer_scene_failure_blocks_profile_gate_without_new_capture_claim(
    monkeypatch,
    tmp_path,
):
    cli = _load_cli()
    out = tmp_path / "out"
    monkeypatch.setattr(
        cli,
        "build_offline_vertical_slice_bootstrap",
        lambda *args, **kwargs: _base_report(out, profile_ready=False),
    )
    monkeypatch.setattr(cli, "run_source_bootstrap_production", lambda **kwargs: _ready_renderer())
    monkeypatch.setattr(
        cli,
        "materialize_renderer_native_scene_handoff",
        lambda **kwargs: {
            "format": "SHIFT.RendererNativeSceneHandoff/1",
            "status": "blocked",
            "ready": False,
            "scene_set_ready": False,
            "blocking_reasons": ["phase580:external-sampler:runtime-resource-unresolved:s3:samplerCube"],
            "artifacts": {"scene_set_dir": None},
        },
    )

    def refresh(report, **kwargs):
        report["profile_ready"] = False
        report["ready"] = False
        report["status"] = "profile-blocked"
        return ["profile:scene_set:explicit-input-required"]

    monkeypatch.setattr(cli, "_refresh_runtime_profile", refresh)
    rc = cli.main(
        _args(tmp_path)
        + [
            "--renderer-capture-jsonl",
            "shift_d3d9_capture.jsonl",
            "--renderer-pe-evidence",
            "pe.json",
        ]
    )
    assert rc == 2
    persisted = json.loads((out / "vertical_slice_bootstrap.json").read_text())
    assert persisted["status"] == "renderer-native-scene-blocked"
    assert persisted["renderer_evidence_ready"] is True
    assert persisted["renderer_native_scene_ready"] is False
    assert any("external-sampler" in item for item in persisted["blocking_reasons"])
    assert all("new-capture" not in item for item in persisted["blocking_reasons"])


def test_renderer_is_not_started_when_selected_offline_bootstrap_is_blocked(
    monkeypatch,
    tmp_path,
):
    cli = _load_cli()
    out = tmp_path / "out"
    monkeypatch.setattr(
        cli,
        "build_offline_vertical_slice_bootstrap",
        lambda *args, **kwargs: _base_report(
            out,
            offline_ready=False,
            profile_ready=False,
        ),
    )

    def forbidden_renderer(*args, **kwargs):
        raise AssertionError("renderer must not bypass blocked resource bootstrap")

    monkeypatch.setattr(cli, "run_source_bootstrap_production", forbidden_renderer)
    rc = cli.main(
        _args(tmp_path)
        + [
            "--renderer-capture-jsonl",
            "shift_d3d9_capture.jsonl",
            "--renderer-pe-evidence",
            "pe.json",
        ]
    )

    assert rc == 2
    persisted = json.loads((out / "vertical_slice_bootstrap.json").read_text())
    assert persisted["status"] == "offline-bootstrap-blocked"
    assert persisted["ready"] is False
    assert persisted["renderer_evidence_ready"] is False
    assert "renderer-evidence:offline-bootstrap-not-ready" in persisted["blocking_reasons"]


def test_renderer_cli_requires_capture_and_exactly_one_pe_source(tmp_path):
    cli = _load_cli()
    with pytest.raises(SystemExit, match="2"):
        cli.main(
            _args(tmp_path)
            + ["--renderer-pe-evidence", "pe.json"]
        )
    with pytest.raises(SystemExit, match="2"):
        cli.main(
            _args(tmp_path)
            + ["--renderer-capture-jsonl", "capture.jsonl"]
        )
