from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "shift_resource_pipeline_participant_handoff_cli",
    ROOT / "tools" / "shift_resource_pipeline.py",
)
assert SPEC is not None and SPEC.loader is not None
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _participant(*, ready: bool = True) -> dict:
    return {
        "format": "SHIFT.NativePhysicsParticipantRuntimeEvidence/1",
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": [] if ready else ["fixture-blocked"],
        "registry_selector_identity_join_proven": ready,
        "participant_instance_ready": ready,
        "participant_pointer_token": "0x12345678",
    }


def _args(
    tmp_path: Path,
    participant: Path,
    *,
    require_identity: bool,
) -> argparse.Namespace:
    return argparse.Namespace(
        inputs=["Vehicles.zip", "Silverstone_Era3_.zip"],
        output=str(tmp_path / "pipeline"),
        track="Silverstone_Era3_GrandPrix",
        vehicle="BMW_M3_E36",
        scene_set="out/runtime-proven-scene",
        participant_runtime_evidence=str(participant),
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
            "version": 1,
            "status": "ready",
            "ready": True,
            "resource_inputs_ready": True,
            "blocking_reasons": [],
            "artifacts": {},
            "boundary": {
                "runtime_execution_claimed": False,
                "participant_runtime_identity_evaluated": False,
            },
        }
        _write(out / "native_resource_handoff.json", report)
        return report

    monkeypatch.setattr(cli, "run_offline_pipeline", fake_run)
    monkeypatch.setattr(cli, "build_bootstrap_corpus_validation_files", fake_validation)
    monkeypatch.setattr(cli, "build_native_resource_handoff_files", fake_handoff)


def test_all_transports_ready_participant_evidence_without_claiming_runtime(
    monkeypatch,
    tmp_path,
):
    _install_pipeline_stages(monkeypatch)
    participant = tmp_path / "participant-runtime.json"
    _write(participant, _participant())
    source_bytes = participant.read_bytes()

    args = _args(tmp_path, participant, require_identity=True)
    assert cli.cmd_all(args) == 0

    pipeline = Path(args.output)
    copied = (
        pipeline
        / "native-handoff"
        / "native_physics_participant_runtime_evidence.json"
    )
    assert copied.read_bytes() == source_bytes

    handoff = json.loads(
        (pipeline / "native-handoff" / "native_resource_handoff.json").read_text(
            encoding="utf-8"
        )
    )
    assert handoff["ready"] is True
    assert handoff["resource_inputs_ready"] is True
    assert handoff["participant_runtime_identity_ready"] is True
    assert handoff["boundary"]["runtime_execution_claimed"] is False
    assert "participant_runtime_evidence" in handoff["artifacts"]

    run = json.loads(
        (pipeline / "pipeline_run.json").read_text(encoding="utf-8")
    )
    assert run["participant_runtime_identity_evaluated"] is True
    assert run["participant_runtime_identity_ready"] is True
    assert run["native_runtime_ready"] is False
    assert run["inputs"]["participant_runtime_evidence_source"] == str(
        participant.resolve()
    )
    assert run["boundary"]["participant_runtime_evidence_transport_automated"] is True
    assert (
        run["boundary"]["participant_runtime_evidence_transport_is_runtime_execution"]
        is False
    )
    assert run["artifacts"]["native_handoff_participant_runtime_evidence"] == str(
        copied
    )


def test_invalid_participant_evidence_is_optional_unless_strictly_required(
    monkeypatch,
    tmp_path,
):
    _install_pipeline_stages(monkeypatch)
    participant = tmp_path / "participant-runtime.json"
    _write(participant, _participant(ready=False))

    optional = _args(tmp_path / "optional", participant, require_identity=False)
    assert cli.cmd_all(optional) == 0
    optional_run = json.loads(
        (Path(optional.output) / "pipeline_run.json").read_text(encoding="utf-8")
    )
    assert optional_run["native_resource_handoff_ready"] is True
    assert optional_run["participant_runtime_identity_ready"] is False
    assert "participant-runtime-evidence:not-ready" in optional_run[
        "participant_runtime_identity_blocking_reasons"
    ]

    required = _args(tmp_path / "required", participant, require_identity=True)
    assert cli.cmd_all(required) == 2
    required_run = json.loads(
        (Path(required.output) / "pipeline_run.json").read_text(encoding="utf-8")
    )
    assert required_run["native_resource_handoff_ready"] is True
    assert required_run["participant_runtime_identity_ready"] is False


def test_parser_exposes_participant_transport_for_all_and_native_handoff():
    parser = cli.build_parser()
    all_args = parser.parse_args([
        "all",
        "Vehicles.zip",
        "-o",
        "out/pipeline",
        "--track",
        "Silverstone",
        "--vehicle",
        "BMW_M3_E36",
        "--participant-runtime-evidence",
        "out/participant.json",
        "--require-participant-runtime-identity",
    ])
    assert all_args.participant_runtime_evidence == "out/participant.json"
    assert all_args.require_participant_runtime_identity is True

    handoff_args = parser.parse_args([
        "native-handoff",
        "catalog.json",
        "bootstrap.json",
        "physics.json",
        "-o",
        "out/native-handoff",
        "--participant-runtime-evidence",
        "out/participant.json",
        "--require-participant-runtime-identity",
    ])
    assert handoff_args.participant_runtime_evidence == "out/participant.json"
    assert handoff_args.require_participant_runtime_identity is True
