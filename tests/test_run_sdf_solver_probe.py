import json
from pathlib import Path

import tools.run_sdf_solver_probe as tool


def _manifest():
    return {
        "format": "SHIFT.SDFRuntimeProbeLauncher/1",
        "status": "ready",
        "ready": True,
        "validation": {"errors": []},
    }


def _timeline(*, ready=True):
    return {
        "format": "SHIFT.ConstraintRelationStateMutationTimelineCorrelation/1",
        "ready": ready,
        "mutation_event_count": 2,
        "timeline_anchor_count": 5,
        "summary": {
            "vehicle_setup_mutation_count": 1,
            "runtime_threshold_mutation_count": 1,
            "unclassified_mutation_count": 0,
            "correlated_ready_count": 2 if ready else 1,
        },
        "errors": [] if ready else ["mutation:2:mutation-callsite-not-ready"],
    }


def test_phase638_finalize_helper_persists_phase637_report(
    monkeypatch,
    tmp_path: Path,
):
    monkeypatch.setattr(
        tool,
        "analyze_relation_state_mutation_capture_directory",
        lambda output: _timeline(),
    )

    report = tool.finalize_relation_state_mutation_capture(tmp_path)

    assert report["ready"] is True
    output = tmp_path / tool.TIMELINE_OUTPUT_NAME
    assert output.is_file()
    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["format"] == (
        "SHIFT.ConstraintRelationStateMutationTimelineCorrelation/1"
    )
    assert written["ready"] is True


def test_phase638_full_attach_automatically_finalizes_timeline(
    monkeypatch,
    tmp_path: Path,
    capsys,
):
    monkeypatch.setattr(
        tool,
        "prepare_probe_bundle",
        lambda *args, **kwargs: _manifest(),
    )
    monkeypatch.setattr(
        tool,
        "build_attach_command",
        lambda **kwargs: ["gdb", "-p", "1234"],
    )
    monkeypatch.setattr(tool.subprocess, "call", lambda command: 0)
    monkeypatch.setattr(
        tool,
        "finalize_relation_state_mutation_capture",
        lambda output: _timeline(),
    )

    result = tool.main(
        [
            str(tmp_path / "SHIFT.exe"),
            "--output",
            str(tmp_path / "capture"),
            "--attach-pid",
            "1234",
        ]
    )

    assert result == 0
    output = capsys.readouterr().out
    assert '"automatic_timeline_correlation": true' in output
    assert '"status": "completed"' in output
    assert '"mutation_event_count": 2' in output


def test_phase638_full_attach_blocks_when_timeline_is_not_ready(
    monkeypatch,
    tmp_path: Path,
    capsys,
):
    monkeypatch.setattr(
        tool,
        "prepare_probe_bundle",
        lambda *args, **kwargs: _manifest(),
    )
    monkeypatch.setattr(
        tool,
        "build_attach_command",
        lambda **kwargs: ["gdb", "-p", "1234"],
    )
    monkeypatch.setattr(tool.subprocess, "call", lambda command: 0)
    monkeypatch.setattr(
        tool,
        "finalize_relation_state_mutation_capture",
        lambda output: _timeline(ready=False),
    )

    result = tool.main(
        [
            str(tmp_path / "SHIFT.exe"),
            "--output",
            str(tmp_path / "capture"),
            "--attach-pid",
            "1234",
        ]
    )

    assert result == 2
    output = capsys.readouterr().out
    assert '"status": "blocked"' in output
    assert "mutation-callsite-not-ready" in output


def test_phase638_full_attach_blocks_when_gdb_session_fails_even_if_timeline_ready(
    monkeypatch,
    tmp_path: Path,
):
    monkeypatch.setattr(
        tool,
        "prepare_probe_bundle",
        lambda *args, **kwargs: _manifest(),
    )
    monkeypatch.setattr(
        tool,
        "build_attach_command",
        lambda **kwargs: ["gdb", "-p", "1234"],
    )
    monkeypatch.setattr(tool.subprocess, "call", lambda command: 1)
    monkeypatch.setattr(
        tool,
        "finalize_relation_state_mutation_capture",
        lambda output: _timeline(),
    )

    result = tool.main(
        [
            str(tmp_path / "SHIFT.exe"),
            "--output",
            str(tmp_path / "capture"),
            "--attach-pid",
            "1234",
        ]
    )

    assert result == 2


def test_phase638_provider_only_attach_skips_relation_timeline_finalization(
    monkeypatch,
    tmp_path: Path,
):
    monkeypatch.setattr(
        tool,
        "prepare_probe_bundle",
        lambda *args, **kwargs: _manifest(),
    )
    monkeypatch.setattr(
        tool,
        "build_attach_command",
        lambda **kwargs: ["gdb", "-p", "1234"],
    )
    monkeypatch.setattr(tool.subprocess, "call", lambda command: 0)

    def fail_if_called(output):
        raise AssertionError("provider-only must not run relation timeline finalization")

    monkeypatch.setattr(
        tool,
        "finalize_relation_state_mutation_capture",
        fail_if_called,
    )

    result = tool.main(
        [
            str(tmp_path / "SHIFT.exe"),
            "--output",
            str(tmp_path / "capture"),
            "--attach-pid",
            "1234",
            "--provider-only",
        ]
    )

    assert result == 0
