from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _module():
    root = Path(__file__).resolve().parents[1]
    path = root / "tools" / "bootstrap_playable_linux_slice.py"
    spec = importlib.util.spec_from_file_location(
        "bootstrap_playable_linux_slice_phase653_tested",
        path,
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
        "--renderer-capture-result",
        str(tmp_path / "capture" / "external_sampler_capture_result.json"),
        "--renderer-pe-evidence",
        "pe.json",
    ]


def test_phase653_playable_entrypoint_forwards_verified_capture_bundle(
    monkeypatch,
    tmp_path,
):
    cli = _module()
    capture_root = (tmp_path / "capture").resolve()
    capture_jsonl = capture_root / "shift_d3d9_capture.jsonl"
    calls = []

    monkeypatch.setattr(
        cli,
        "resolve_capture_feedback_input",
        lambda path: {
            "format": "SHIFT.Phase652ExternalSamplerCaptureFeedback/1",
            "version": 1,
            "ready": True,
            "capture_result": str(Path(path).resolve()),
            "capture_jsonl": str(capture_jsonl),
            "capture_root": str(capture_root),
            "verified_expectation_count": 1,
            "boundary": {
                "full_renderer_reattribution_required": True,
                "binding_identity_claimed": False,
            },
        },
    )

    class StopAfterBase(Exception):
        pass

    def base_main(argv):
        calls.append(list(argv))
        raise StopAfterBase

    monkeypatch.setattr(cli, "base_main", base_main)

    with pytest.raises(StopAfterBase):
        cli.main(_args(tmp_path))

    assert len(calls) == 1
    forwarded = calls[0]
    assert "--renderer-capture-result" not in forwarded
    assert "--renderer-capture-jsonl" in forwarded
    assert forwarded[forwarded.index("--renderer-capture-jsonl") + 1] == str(
        capture_jsonl
    )
    assert "--renderer-capture-root" in forwarded
    assert forwarded[forwarded.index("--renderer-capture-root") + 1] == str(
        capture_root
    )
    assert "--renderer-pe-evidence" in forwarded


def test_phase653_rejects_manual_capture_jsonl_with_capture_result(
    monkeypatch,
    tmp_path,
):
    cli = _module()
    resolver_called = False

    def resolver(_path):
        nonlocal resolver_called
        resolver_called = True
        return {}

    monkeypatch.setattr(cli, "resolve_capture_feedback_input", resolver)
    monkeypatch.setattr(
        cli,
        "base_main",
        lambda argv: (_ for _ in ()).throw(
            AssertionError("conflicting capture provenance must block before base bootstrap")
        ),
    )

    with pytest.raises(SystemExit) as exc:
        cli.main(
            _args(tmp_path)
            + ["--renderer-capture-jsonl", "other-capture.jsonl"]
        )

    assert exc.value.code == 2
    assert resolver_called is False


def test_phase653_rejects_manual_capture_root_with_capture_result(
    monkeypatch,
    tmp_path,
):
    cli = _module()
    monkeypatch.setattr(
        cli,
        "base_main",
        lambda argv: (_ for _ in ()).throw(
            AssertionError("conflicting capture provenance must block before base bootstrap")
        ),
    )

    with pytest.raises(SystemExit) as exc:
        cli.main(
            _args(tmp_path)
            + ["--renderer-capture-root", str(tmp_path / "other")]
        )

    assert exc.value.code == 2


def test_phase653_rejects_unready_or_tampered_capture_result(
    monkeypatch,
    tmp_path,
):
    cli = _module()

    def resolver(_path):
        raise ValueError("capture-result:not-ready")

    monkeypatch.setattr(cli, "resolve_capture_feedback_input", resolver)
    monkeypatch.setattr(
        cli,
        "base_main",
        lambda argv: (_ for _ in ()).throw(
            AssertionError("invalid Phase 650 result must not reach base bootstrap")
        ),
    )

    with pytest.raises(SystemExit) as exc:
        cli.main(_args(tmp_path))

    assert exc.value.code == 2
