from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "bootstrap_runtime_participant_cli",
    ROOT / "tools" / "bootstrap_runtime.py",
)
assert SPEC is not None and SPEC.loader is not None
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)


def _report(*, identity_ready: bool) -> dict:
    return {
        "format": "SHIFT.OfflineRuntimeBootstrap/1",
        "status": "offline-native-build-ready-runtime-gated",
        "offline_build_ready": True,
        "runtime_ready": False,
        "track": "Track",
        "vehicle": "Car",
        "readiness": {
            "vehicle_participant_runtime_identity_ready": identity_ready,
        },
        "blocking_reasons": [],
    }


def test_bootstrap_cli_threads_participant_observation_and_can_require_identity(
    monkeypatch,
    tmp_path,
):
    calls = {}

    def fake_builder(*args, **kwargs):
        calls.update(kwargs)
        return _report(identity_ready=False)

    monkeypatch.setattr(cli, "build_offline_runtime_bootstrap", fake_builder)
    observation = tmp_path / "participant-observation.json"
    rc = cli.main([
        "corpus.zip",
        "-o",
        str(tmp_path / "out"),
        "--track",
        "Track",
        "--vehicle",
        "Car",
        "--participant-observation",
        str(observation),
        "--require-participant-runtime-identity",
    ])

    assert rc == 2
    assert calls["participant_observation_path"] == str(observation)


def test_bootstrap_cli_identity_requirement_succeeds_when_exact_join_is_ready(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        cli,
        "build_offline_runtime_bootstrap",
        lambda *args, **kwargs: _report(identity_ready=True),
    )

    rc = cli.main([
        "corpus.zip",
        "-o",
        str(tmp_path / "out"),
        "--track",
        "Track",
        "--vehicle",
        "Car",
        "--participant-observation",
        str(tmp_path / "participant-observation.json"),
        "--require-participant-runtime-identity",
    ])

    assert rc == 0
