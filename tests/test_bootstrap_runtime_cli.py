from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "bootstrap_runtime_cli",
    ROOT / "tools" / "bootstrap_runtime.py",
)
assert SPEC is not None and SPEC.loader is not None
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)


def _report(*, offline=True, runtime=False):
    return {
        "format": "SHIFT.OfflineRuntimeBootstrap/1",
        "status": (
            "runtime-ready"
            if runtime
            else "offline-native-build-ready-runtime-gated"
            if offline
            else "offline-native-build-blocked"
        ),
        "offline_build_ready": offline,
        "runtime_ready": runtime,
        "track": "Track",
        "vehicle": "Car",
        "readiness": {},
        "blocking_reasons": [] if runtime else ["runtime-scene:required"],
    }


def test_cli_accepts_ready_offline_build_without_runtime_requirement(monkeypatch, tmp_path):
    monkeypatch.setattr(
        cli,
        "build_offline_runtime_bootstrap",
        lambda *args, **kwargs: _report(offline=True, runtime=False),
    )
    rc = cli.main([
        "corpus.zip",
        "-o",
        str(tmp_path / "out"),
        "--track",
        "Track",
        "--vehicle",
        "Car",
    ])
    assert rc == 0


def test_cli_strict_runtime_gate_returns_nonzero_until_runtime_is_proven(monkeypatch, tmp_path):
    monkeypatch.setattr(
        cli,
        "build_offline_runtime_bootstrap",
        lambda *args, **kwargs: _report(offline=True, runtime=False),
    )
    rc = cli.main([
        "corpus.zip",
        "-o",
        str(tmp_path / "out"),
        "--track",
        "Track",
        "--vehicle",
        "Car",
        "--require-runtime-ready",
    ])
    assert rc == 2


def test_cli_returns_nonzero_when_offline_build_is_blocked(monkeypatch, tmp_path):
    monkeypatch.setattr(
        cli,
        "build_offline_runtime_bootstrap",
        lambda *args, **kwargs: _report(offline=False, runtime=False),
    )
    rc = cli.main([
        "corpus.zip",
        "-o",
        str(tmp_path / "out"),
        "--track",
        "Track",
        "--vehicle",
        "Car",
    ])
    assert rc == 2
