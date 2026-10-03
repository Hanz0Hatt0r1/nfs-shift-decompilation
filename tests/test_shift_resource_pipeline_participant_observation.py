from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "shift_resource_pipeline_participant_observation_cli",
    ROOT / "tools" / "shift_resource_pipeline.py",
)
assert SPEC is not None and SPEC.loader is not None
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def _base_args(
    tmp_path: Path,
    observation: Path,
    *,
    require_identity: bool,
) -> argparse.Namespace:
    return argparse.Namespace(
        inputs=["Vehicles.zip"],
        output=str(tmp_path / "pipeline"),
        track="Silverstone_Era3_GrandPrix",
        vehicle="BMW_M3_E36",
        scene_set="out/runtime-proven-scene",
        participant_runtime_evidence=None,
        participant_observation=str(observation),
        require_participant_runtime_identity=require_identity,
        require_native_resource_handoff=False,
        decode_limit_per_archive=0,
    )


def _install_pipeline_stages(monkeypatch) -> None:
    def fake_run(inputs, output, *, track, vehicle, decode_limit_per_archive):
        out = Path(output)
        out.mkdir(parents=True, exist_ok=True)
        for name in (
            "resource_catalog.json",
            "dependency_graph.json",
            "scene_vehicle_bootstrap.json",
            "vehicle_physics_bundle_report.json",
        ):
            _write(out / name, {})
        return {
            "format": "SHIFT.OfflineResourcePipelineRun/1",
            "resource_bootstrap_ready": True,
            "native_runtime_ready": False,
            "artifacts": {},
            "boundary": {},
        }

    def fake_validation(catalog, graph, output):
        report = {
            "format": "SHIFT.OfflineBootstrapCorpusValidation/1",
            "status": "ready",
            "ready": True,
            "summary": {"targets": 1, "ready": 1, "blocked": 0},
            "blocking_reasons": [],
        }
        _write(Path(output), report)
        return report

    def fake_handoff(catalog, bootstrap, physics, output, *, scene_set_dir=None):
        out = Path(output)
        out.mkdir(parents=True, exist_ok=True)
        report = {
            "format": "SHIFT.OfflineNativeResourceHandoff/1",
            "status": "ready",
            "ready": True,
            "resource_inputs_ready": True,
            "blocking_reasons": [],
            "artifacts": {},
            "boundary": {"runtime_execution_claimed": False},
        }
        _write(out / "native_resource_handoff.json", report)
        return report

    monkeypatch.setattr(cli, "run_offline_pipeline", fake_run)
    monkeypatch.setattr(cli, "build_bootstrap_corpus_validation_files", fake_validation)
    monkeypatch.setattr(cli, "build_native_resource_handoff_files", fake_handoff)


def _runtime_evidence(*, ready: bool) -> dict:
    return {
        "format": "SHIFT.NativePhysicsParticipantRuntimeEvidence/1",
        "ready": ready,
        "registry_selector_identity_join_proven": ready,
        "participant_instance_ready": ready,
    }


def test_all_builds_exact_participant_evidence_from_observation_then_transports_it(
    monkeypatch,
    tmp_path,
):
    _install_pipeline_stages(monkeypatch)
    calls = {}
    observation = tmp_path / "participant-observation.json"
    _write(
        observation,
        {"format": "SHIFT.NativePhysicsParticipantObservation/1", "ready": True},
    )

    def fake_vehicle(catalog, bootstrap, physics, output, **kwargs):
        calls["catalog"] = str(catalog)
        calls["bootstrap"] = str(bootstrap)
        calls["physics"] = str(physics)
        calls["output"] = str(output)
        calls["observation"] = kwargs.get("participant_observation_path")
        out = Path(output)
        out.mkdir(parents=True, exist_ok=True)
        evidence = out / "native_physics_participant_runtime_evidence.json"
        _write(evidence, _runtime_evidence(ready=True))
        build = out / "native_vehicle_build.json"
        _write(build, {"format": "SHIFT.OfflineNativeVehicleBuild/1"})
        return {
            "format": "SHIFT.OfflineNativeVehicleBuild/1",
            "participant_runtime_identity_ready": True,
            "artifacts": {
                "participant_runtime_evidence": {
                    "path": str(evidence),
                    "sha256": "a" * 64,
                }
            },
        }

    monkeypatch.setattr(cli, "build_native_vehicle_files", fake_vehicle)
    args = _base_args(tmp_path, observation, require_identity=True)
    assert cli.cmd_all(args) == 0

    pipeline = Path(args.output)
    copied = (
        pipeline
        / "native-handoff"
        / "native_physics_participant_runtime_evidence.json"
    )
    assert copied.is_file()
    assert calls["observation"] == str(observation)
    assert calls["catalog"].endswith("resource_catalog.json")
    assert calls["bootstrap"].endswith("scene_vehicle_bootstrap.json")
    assert calls["physics"].endswith("vehicle_physics_bundle_report.json")
    assert calls["output"].endswith("native-vehicle")

    run = json.loads((pipeline / "pipeline_run.json").read_text())
    assert run["resource_bootstrap_ready"] is True
    assert run["native_resource_handoff_ready"] is True
    assert run["participant_runtime_observation_join_evaluated"] is True
    assert run["participant_runtime_observation_join_ready"] is True
    assert run["participant_runtime_identity_ready"] is True
    assert run["native_runtime_ready"] is False
    assert run["inputs"]["participant_runtime_observation_source"] == str(
        observation.resolve()
    )
    assert run["inputs"]["participant_runtime_evidence_source"].endswith(
        "native-vehicle/native_physics_participant_runtime_evidence.json"
    )
    assert run["boundary"]["participant_runtime_observation_join_automated"] is True
    assert run["boundary"]["participant_runtime_observation_join_creates_observation"] is False
    assert run["boundary"]["native_resource_handoff_is_runtime_execution"] is False
    assert run["artifacts"]["participant_observation_native_vehicle"].endswith(
        "native-vehicle/native_vehicle_build.json"
    )


def test_blocked_observation_join_remains_runtime_only_unless_strict(monkeypatch, tmp_path):
    _install_pipeline_stages(monkeypatch)
    observation = tmp_path / "participant-observation.json"
    _write(
        observation,
        {"format": "SHIFT.NativePhysicsParticipantObservation/1", "ready": True},
    )

    def blocked_vehicle(catalog, bootstrap, physics, output, **kwargs):
        out = Path(output)
        out.mkdir(parents=True, exist_ok=True)
        evidence = out / "native_physics_participant_runtime_evidence.json"
        _write(evidence, _runtime_evidence(ready=False))
        return {
            "format": "SHIFT.OfflineNativeVehicleBuild/1",
            "participant_runtime_identity_ready": False,
            "artifacts": {
                "participant_runtime_evidence": {
                    "path": str(evidence),
                    "sha256": "b" * 64,
                }
            },
        }

    monkeypatch.setattr(cli, "build_native_vehicle_files", blocked_vehicle)

    optional = _base_args(tmp_path / "optional", observation, require_identity=False)
    assert cli.cmd_all(optional) == 0
    optional_run = json.loads(
        (Path(optional.output) / "pipeline_run.json").read_text()
    )
    assert optional_run["resource_bootstrap_ready"] is True
    assert optional_run["native_resource_handoff_ready"] is True
    assert optional_run["participant_runtime_observation_join_evaluated"] is True
    assert optional_run["participant_runtime_observation_join_ready"] is False
    assert optional_run["participant_runtime_identity_ready"] is False

    required = _base_args(tmp_path / "required", observation, require_identity=True)
    assert cli.cmd_all(required) == 2
    required_run = json.loads(
        (Path(required.output) / "pipeline_run.json").read_text()
    )
    assert required_run["native_resource_handoff_ready"] is True
    assert required_run["participant_runtime_identity_ready"] is False


def test_parser_makes_runtime_evidence_and_observation_mutually_exclusive():
    parser = cli.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([
            "all",
            "Vehicles.zip",
            "-o",
            "out/pipeline",
            "--track",
            "Silverstone",
            "--vehicle",
            "BMW_M3_E36",
            "--participant-runtime-evidence",
            "out/runtime-evidence.json",
            "--participant-observation",
            "out/observation.json",
        ])


def test_native_handoff_accepts_participant_observation_parser_flag():
    parser = cli.build_parser()
    args = parser.parse_args([
        "native-handoff",
        "catalog.json",
        "bootstrap.json",
        "physics.json",
        "-o",
        "out/native-handoff",
        "--participant-observation",
        "out/participant-observation.json",
        "--require-participant-runtime-identity",
    ])
    assert args.participant_runtime_evidence is None
    assert args.participant_observation == "out/participant-observation.json"
    assert args.require_participant_runtime_identity is True
