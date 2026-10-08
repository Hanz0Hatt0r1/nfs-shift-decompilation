from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "run_final_playable_pipeline_smoke.py"
SPEC = importlib.util.spec_from_file_location(
    "run_final_playable_pipeline_smoke",
    MODULE_PATH,
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _coordination(
    path: Path,
    *,
    control: bool,
    camera: bool,
    camera_feed: bool = True,
) -> Path:
    _write_json(
        path,
        {
            "format": "SHIFT.PlayableSliceThreeProcessExecution/1",
            "status": "active",
            "main_frontier": {
                "vehicle_world_transform_ready": True,
                "retail_outer_cadence_admitted": True,
                "retail_inner_substep_execution_admitted": True,
                "retail_control_chain_complete": control,
                "retail_camera_follow_ready": camera,
                "process_2_camera_feed_ready": camera_feed,
            },
        },
    )
    return path


def _argv(tmp_path: Path, *, interactive: bool = True) -> list[str]:
    args = [
        "input.bff",
        "--output", str(tmp_path / "out"),
        "--track", "Silverstone_Era3_GrandPrix",
        "--vehicle", "BMW_M3_E36",
        "--workspace-root", str(tmp_path),
        "--resource-pipeline", "pipeline",
        "--camera-state", "camera.json",
        "--solver-frame", "solver.sbfr",
        "--generated-body-constraint-frame", "generated.gbcf",
        "--constraint-sample-relation-frame", "relations.csrf",
        "--constraint-relation-reset-frame", "reset.crrf",
        "--post-solve-projection", "post.sbps",
    ]
    if interactive:
        args.append("--interactive")
    else:
        args.extend(["--keyboard", "--frames", "120"])
    return args


def test_current_upstream_control_and_camera_gates_block_final_smoke(tmp_path):
    coordination = _coordination(
        tmp_path / "coordination.json",
        control=False,
        camera=False,
    )
    report, _ = MODULE.build_final_smoke_preflight(
        _argv(tmp_path),
        coordination_path=coordination,
    )
    assert report["ready"] is False
    assert "coordination:retail_control_chain_complete:not-ready" in report["blocking_reasons"]
    assert "coordination:retail_camera_follow_ready:not-ready" in report["blocking_reasons"]
    assert report["boundary"]["missing_upstream_gate_may_be_guessed"] is False


def test_retail_camera_semantics_without_runtime_feed_remain_blocked(tmp_path):
    coordination = _coordination(
        tmp_path / "coordination.json",
        control=True,
        camera=True,
        camera_feed=False,
    )
    report, _ = MODULE.build_final_smoke_preflight(
        _argv(tmp_path),
        coordination_path=coordination,
    )
    assert report["ready"] is False
    assert "coordination:process_2_camera_feed_ready:not-ready" in report["blocking_reasons"]
    assert report["boundary"]["process_2_runtime_camera_feed_required"] is True


def test_exact_ready_frontier_admits_continuous_silverstone_bmw_target(tmp_path):
    coordination = _coordination(
        tmp_path / "coordination.json",
        control=True,
        camera=True,
    )
    report, forwarded = MODULE.build_final_smoke_preflight(
        _argv(tmp_path),
        coordination_path=coordination,
    )
    assert report["ready"] is True
    assert report["track"] == "Silverstone_Era3_GrandPrix"
    assert report["vehicle"] == "BMW_M3_E36"
    assert report["mode"] == "interactive-continuous"
    assert report["coordination_sha256"] == hashlib.sha256(coordination.read_bytes()).hexdigest()
    assert report["boundary"]["coordination_bytes_bound_to_preflight"] is True
    assert report["boundary"]["coordination_must_remain_stable_before_runtime"] is True
    assert report["boundary"]["process_2_runtime_camera_feed_required"] is True
    assert forwarded == _argv(tmp_path)


def test_bounded_keyboard_mode_is_not_final_continuous_smoke(tmp_path):
    coordination = _coordination(
        tmp_path / "coordination.json",
        control=True,
        camera=True,
    )
    report, _ = MODULE.build_final_smoke_preflight(
        _argv(tmp_path, interactive=False),
        coordination_path=coordination,
    )
    assert report["ready"] is False
    assert "runtime:final-smoke-requires-interactive-continuous-mode" in report["blocking_reasons"]
    assert "runtime:final-smoke-must-not-have-frame-limit" in report["blocking_reasons"]
    assert "runtime:bounded-keyboard-mode-not-allowed" in report["blocking_reasons"]


def test_wrong_track_or_vehicle_fails_closed(tmp_path):
    coordination = _coordination(
        tmp_path / "coordination.json",
        control=True,
        camera=True,
    )
    args = _argv(tmp_path)
    args[args.index("Silverstone_Era3_GrandPrix")] = "OtherTrack"
    args[args.index("BMW_M3_E36")] = "OtherCar"
    report, _ = MODULE.build_final_smoke_preflight(
        args,
        coordination_path=coordination,
    )
    assert report["ready"] is False
    assert any(reason.startswith("target:track-must-be-") for reason in report["blocking_reasons"])
    assert any(reason.startswith("target:vehicle-must-be-") for reason in report["blocking_reasons"])


def test_ready_preflight_delegates_to_production_execution_wrapper(tmp_path, monkeypatch):
    coordination = _coordination(
        tmp_path / "coordination.json",
        control=True,
        camera=True,
    )
    captured: dict[str, object] = {}

    def fake_execute(args):
        captured["args"] = list(args)
        return {"ready": True, "status": "completed"}

    monkeypatch.setattr(MODULE.execution, "execute_playable_pipeline_slice", fake_execute)
    report = MODULE.execute_final_smoke(
        _argv(tmp_path),
        coordination_path=coordination,
    )
    assert report["ready"] is True
    assert captured["args"] == _argv(tmp_path)
    assert report["preflight"]["ready"] is True
    assert report["execution"]["status"] == "completed"
    assert report["boundary"]["coordination_stability_checked_before_runtime"] is True
    assert report["boundary"]["coordination_rehash_occurs_immediately_before_runtime_delegation"] is True
    assert report["boundary"]["test_only_core_vehicle_transform_allowed"] is False
    assert report["boundary"]["retail_game_loop_claimed"] is False


def test_coordination_mutation_after_preflight_blocks_runtime(tmp_path, monkeypatch):
    coordination = _coordination(
        tmp_path / "coordination.json",
        control=True,
        camera=True,
    )
    original_build = MODULE.build_final_smoke_preflight

    def mutating_build(*args, **kwargs):
        report, forwarded = original_build(*args, **kwargs)
        _coordination(coordination, control=False, camera=True)
        return report, forwarded

    monkeypatch.setattr(MODULE, "build_final_smoke_preflight", mutating_build)
    monkeypatch.setattr(
        MODULE.execution,
        "execute_playable_pipeline_slice",
        lambda args: pytest.fail("runtime must not be invoked after coordination mutation"),
    )
    with pytest.raises(MODULE.FinalSmokeError, match="coordination changed after final smoke preflight"):
        MODULE.execute_final_smoke(
            _argv(tmp_path),
            coordination_path=coordination,
        )


def test_blocked_preflight_never_invokes_runtime_execution(tmp_path, monkeypatch):
    coordination = _coordination(
        tmp_path / "coordination.json",
        control=False,
        camera=False,
    )
    monkeypatch.setattr(
        MODULE.execution,
        "execute_playable_pipeline_slice",
        lambda args: pytest.fail("execution must not be invoked"),
    )
    with pytest.raises(MODULE.FinalSmokeError, match="preflight blocked"):
        MODULE.execute_final_smoke(
            _argv(tmp_path),
            coordination_path=coordination,
        )
