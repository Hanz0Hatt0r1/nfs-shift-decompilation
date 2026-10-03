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
    runtime_bootstrap.write_text(
        json.dumps({
            "format": "SHIFT.OfflineRuntimeBootstrap/1",
            "offline_build_ready": offline_ready,
        }),
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
        "stages": {},
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


def test_unified_cli_passes_selected_runtime_bootstrap_to_renderer(
    monkeypatch,
    tmp_path,
):
    cli = _load_cli()
    out = tmp_path / "out"
    calls = []
    monkeypatch.setattr(
        cli,
        "build_offline_vertical_slice_bootstrap",
        lambda *args, **kwargs: _base_report(out),
    )

    def renderer(**kwargs):
        calls.append(kwargs)
        return _ready_renderer()

    monkeypatch.setattr(cli, "run_source_bootstrap_production", renderer)
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
    assert len(calls) == 1
    call = calls[0]
    assert call["corpus"] == [
        "Vehicles.zip",
        "Silverstone_Era3_.zip",
        "SHIFT_tail.zip",
    ]
    assert call["runtime_bootstrap"] == str(
        out / "runtime-bootstrap" / "runtime_bootstrap.json"
    )
    assert call["capture_jsonl"] == "shift_d3d9_capture.jsonl"
    assert call["pe_evidence"] == "pe.json"
    assert call["pe_image"] is None

    persisted = json.loads((out / "vertical_slice_bootstrap.json").read_text())
    assert persisted["ready"] is True
    assert persisted["renderer_evidence_requested"] is True
    assert persisted["renderer_evidence_ready"] is True
    assert persisted["renderer_frontier"]["status"] == "continue-offline"
    assert persisted["renderer_frontier"]["capture_blockers"] == []
    assert persisted["artifacts"]["renderer_source_bootstrap"] == str(
        out
        / "renderer-evidence"
        / "silverstone_renderer_source_bootstrap_production_run.json"
    )
    assert (
        persisted["boundary"]["manual_resource_to_renderer_handoff_required"]
        is False
    )
    assert persisted["boundary"]["renderer_bundle_is_selection_authority"] is False


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

    monkeypatch.setattr(cli, "build_launch_plan", forbidden_launcher)
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
    assert persisted["launch_plan_ready"] is False
    assert any(
        "object-candidate-required" in reason
        for reason in persisted["blocking_reasons"]
    )
    assert persisted["boundary"]["launcher_validation_performed"] is False


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
