from pathlib import Path

import pytest

import sdf_runtime_probe_launcher_runtime as runtime


def test_build_gdb_command_file_is_deterministic(tmp_path):
    command = runtime.build_gdb_command_file(
        probe_script=tmp_path / "probe.py",
        output_dir=tmp_path / "capture",
    )
    assert command == (
        f"set pagination off\n"
        f"set confirm off\n"
        f"source {(tmp_path / 'probe.py').resolve()}\n"
        f"sdf-probe {(tmp_path / 'capture').resolve()}\n"
        "continue\n"
    )


def test_build_gdb_command_file_supports_provider_only_mode(tmp_path):
    command = runtime.build_gdb_command_file(
        probe_script=tmp_path / "probe.py",
        output_dir=tmp_path / "capture",
        provider_only=True,
    )
    assert command == (
        f"set pagination off\n"
        f"set confirm off\n"
        f"source {(tmp_path / 'probe.py').resolve()}\n"
        f"sdf-probe {(tmp_path / 'capture').resolve()} --provider-only\n"
        "continue\n"
    )


def test_prepare_probe_bundle_writes_manifest_and_gdb_script(tmp_path, monkeypatch):
    executable = tmp_path / "SHIFT.exe"
    executable.write_bytes(b"retail")
    output = tmp_path / "capture"
    probe = tmp_path / "probe.py"
    probe.write_text("# probe\n", encoding="utf-8")

    monkeypatch.setattr(
        runtime,
        "validate_probe_executable_file",
        lambda path: {
            "ready": True,
            "sha256": "a" * 64,
            "errors": [],
            "format": "SHIFT.SDFRuntimeProbePEValidation/1",
        },
    )

    result = runtime.prepare_probe_bundle(
        executable,
        output,
        probe_script=probe,
    )
    assert result["ready"] is True
    assert (output / "probe_manifest.json").is_file()
    assert (output / "attach.gdb").read_text(encoding="utf-8").endswith("continue\n")
    assert result["probe"]["expected_captures"] == [
        "relation_state_mutation_events.jsonl",
        "pre_solve_XXXXXX.json",
        "post_solve_XXXXXX.json",
        "provider_pre_<provider>_<hit>.json",
        "provider_post_<provider>_<hit>.json",
        "scalar_reset_events.jsonl",
        "provider_reset_effects.jsonl",
    ]
    assert result["probe"]["mode"] == "full"
    assert result["post_capture"] == {
        "automatic_timeline_correlation": True,
        "timeline_output": str(
            output.resolve() / "relation_state_mutation_timeline.json"
        ),
        "timeline_format": (
            "SHIFT.ConstraintRelationStateMutationTimelineCorrelation/1"
        ),
        "automatic_evidence_bundle": True,
        "evidence_bundle_output": str(
            output.resolve() / "sdf_capture_evidence.zip"
        ),
        "evidence_bundle_format": "SHIFT.SDFRuntimeProbeEvidenceBundle/1",
    }
    assert result["probe"]["expected_captures"] == [
        "relation_state_mutation_events.jsonl",
        "pre_solve_XXXXXX.json",
        "post_solve_XXXXXX.json",
        "provider_pre_<provider>_<hit>.json",
        "provider_post_<provider>_<hit>.json",
        "scalar_reset_events.jsonl",
        "provider_reset_effects.jsonl",
    ]


def test_prepare_probe_bundle_blocks_invalid_retail_binary(tmp_path, monkeypatch):
    executable = tmp_path / "SHIFT.exe"
    executable.write_bytes(b"wrong")

    monkeypatch.setattr(
        runtime,
        "validate_probe_executable_file",
        lambda path: {
            "ready": False,
            "sha256": "b" * 64,
            "errors": ["sha256:mismatch"],
            "format": "SHIFT.SDFRuntimeProbePEValidation/1",
        },
    )

    result = runtime.prepare_probe_bundle(
        executable,
        tmp_path / "capture",
        probe_script=tmp_path / "probe.py",
    )
    assert result["ready"] is False
    assert "sha256:mismatch" in result["validation"]["errors"]


def test_require_runtime_tools_fails_closed_when_missing(monkeypatch):
    monkeypatch.setattr(runtime.shutil, "which", lambda name: None)
    result = runtime.require_runtime_tools()
    assert result["ready"] is False
    assert result["status"] == "unavailable"
    assert result["errors"] == ["missing:wine", "missing:gdb"]


def test_require_runtime_tools_reports_available_paths(monkeypatch):
    monkeypatch.setattr(
        runtime.shutil,
        "which",
        lambda name: f"/usr/bin/{name}",
    )
    result = runtime.require_runtime_tools()
    assert result["ready"] is True
    assert result["wine"] == "/usr/bin/wine"
    assert result["gdb"] == "/usr/bin/gdb"


def test_launch_retail_uses_explicit_wine_and_workdir(tmp_path, monkeypatch):
    class DummyProcess:
        pass

    captured = {}
    executable = tmp_path / "SHIFT.exe"
    executable.write_bytes(b"retail")

    monkeypatch.setattr(runtime.shutil, "which", lambda name: "/usr/bin/wine")

    def fake_popen(command, cwd=None, stdout=None, stderr=None):
        captured.update(command=command, cwd=cwd, stdout=stdout, stderr=stderr)
        return DummyProcess()

    monkeypatch.setattr(runtime.subprocess, "Popen", fake_popen)
    process = runtime.launch_retail(
        executable,
        workdir=tmp_path,
        game_args=["-silent"],
    )
    assert isinstance(process, DummyProcess)
    assert captured["command"] == [
        "/usr/bin/wine",
        str(executable.resolve()),
        "-silent",
    ]
    assert captured["cwd"] == str(tmp_path.resolve())


def test_launcher_contract_exposes_explicit_backend_probe():
    result = runtime.describe_sdf_runtime_probe_launcher()
    assert result["probe_targets"]["relation_state_mutation"] == "0x00757d2c"
    assert result["probe_targets"]["builtin_solver"] == "0x007b0f20"
    assert result["probe_targets"]["post_solve"] == "0x007b4110"
    assert "provider-only" in result["modes"]


def test_build_attach_command_requires_positive_pid(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime.shutil, "which", lambda name: "/usr/bin/gdb")
    with pytest.raises(ValueError, match="positive"):
        runtime.build_attach_command(
            pid=0,
            gdb_command_file=tmp_path / "attach.gdb",
        )


def test_build_attach_command_uses_explicit_pid_and_script(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime.shutil, "which", lambda name: "/usr/bin/gdb")
    command = runtime.build_attach_command(
        pid=12345,
        gdb_command_file=tmp_path / "attach.gdb",
    )
    assert command == [
        "/usr/bin/gdb",
        "-q",
        "-p",
        "12345",
        "-x",
        str((tmp_path / "attach.gdb").resolve()),
    ]



def test_resolve_probe_executable_extracts_only_shift_exe(tmp_path):
    import zipfile

    archive = tmp_path / "SHIFT.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("SHIFT.exe", b"retail-exe")
        bundle.writestr("SHIFT.exe.c", b"source")

    result = runtime.resolve_probe_executable(
        archive,
        tmp_path / "bundle",
    )
    assert result.name == "SHIFT.exe"
    assert result.read_bytes() == b"retail-exe"


def test_resolve_probe_executable_rejects_multiple_shift_exe_members(tmp_path):
    import zipfile

    archive = tmp_path / "SHIFT.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("one/SHIFT.exe", b"one")
        bundle.writestr("two/SHIFT.exe", b"two")

    with pytest.raises(ValueError, match="exactly one SHIFT.exe"):
        runtime.resolve_probe_executable(
            archive,
            tmp_path / "bundle",
        )


def test_prepare_probe_bundle_provider_only_expected_captures(tmp_path, monkeypatch):
    executable = tmp_path / "SHIFT.exe"
    executable.write_bytes(b"retail")
    output = tmp_path / "capture"
    probe = tmp_path / "probe.py"
    probe.write_text("# probe\n", encoding="utf-8")

    monkeypatch.setattr(
        runtime,
        "validate_probe_executable_file",
        lambda path: {
            "ready": True,
            "sha256": "a" * 64,
            "errors": [],
            "format": "SHIFT.SDFRuntimeProbePEValidation/1",
        },
    )

    result = runtime.prepare_probe_bundle(
        executable,
        output,
        probe_script=probe,
        provider_only=True,
    )
    assert result["probe"]["mode"] == "provider-only"
    assert result["post_capture"] == {
        "automatic_timeline_correlation": False,
        "timeline_output": None,
        "timeline_format": None,
        "automatic_evidence_bundle": False,
        "evidence_bundle_output": None,
        "evidence_bundle_format": None,
    }
    assert result["probe"]["expected_captures"] == [
        "provider_pre_<provider>_<hit>.json",
        "provider_post_<provider>_<hit>.json",
        "scalar_reset_events.jsonl",
        "provider_reset_effects.jsonl",
    ]



def test_phase642_build_gdb_command_file_bounded_full_mode_detaches(tmp_path):
    command = runtime.build_gdb_command_file(
        probe_script=tmp_path / "probe.py",
        output_dir=tmp_path / "capture",
        capture_frames=3,
    )
    assert command == (
        "set pagination off\n"
        "set confirm off\n"
        f"source {(tmp_path / 'probe.py').resolve()}\n"
        f"sdf-probe {(tmp_path / 'capture').resolve()} --capture-frames 3\n"
        "continue\n"
        "detach\n"
        "quit\n"
    )


@pytest.mark.parametrize("capture_frames", [0, -1])
def test_phase642_build_gdb_command_file_rejects_nonpositive_budget(
    tmp_path,
    capture_frames,
):
    with pytest.raises(ValueError, match="positive"):
        runtime.build_gdb_command_file(
            probe_script=tmp_path / "probe.py",
            output_dir=tmp_path / "capture",
            capture_frames=capture_frames,
        )


def test_phase642_bounded_capture_is_full_mode_only(tmp_path):
    with pytest.raises(ValueError, match="full probe mode"):
        runtime.build_gdb_command_file(
            probe_script=tmp_path / "probe.py",
            output_dir=tmp_path / "capture",
            provider_only=True,
            capture_frames=1,
        )


def test_phase642_prepare_probe_bundle_records_bounded_capture(
    tmp_path,
    monkeypatch,
):
    executable = tmp_path / "SHIFT.exe"
    executable.write_bytes(b"retail")
    probe = tmp_path / "probe.py"
    probe.write_text("# probe\n", encoding="utf-8")
    output = tmp_path / "capture"

    monkeypatch.setattr(
        runtime,
        "validate_probe_executable_file",
        lambda path: {
            "ready": True,
            "sha256": "a" * 64,
            "errors": [],
            "format": "SHIFT.SDFRuntimeProbePEValidation/1",
        },
    )

    result = runtime.prepare_probe_bundle(
        executable,
        output,
        probe_script=probe,
        capture_frames=2,
    )

    assert result["probe"]["capture_frames"] == 2
    assert result["probe"]["auto_detach"] is True
    assert "--capture-frames 2" in (
        output / "attach.gdb"
    ).read_text(encoding="utf-8")
    assert (output / "attach.gdb").read_text(
        encoding="utf-8"
    ).endswith("continue\ndetach\nquit\n")


def test_phase643_gdb_command_file_carries_capture_session_id(tmp_path):
    command = runtime.build_gdb_command_file(
        probe_script=tmp_path / "probe.py",
        output_dir=tmp_path / "capture",
        capture_session_id="ab" * 16,
    )

    assert (
        f"sdf-probe {(tmp_path / 'capture').resolve()} "
        f"--session-id {'ab' * 16}\n"
    ) in command


def test_phase643_prepare_probe_bundle_clears_stale_evidence_and_records_session(
    tmp_path,
    monkeypatch,
):
    executable = tmp_path / "SHIFT.exe"
    executable.write_bytes(b"retail")
    output = tmp_path / "capture"
    output.mkdir()
    probe = tmp_path / "probe.py"
    probe.write_text("# probe\n", encoding="utf-8")

    stale_names = [
        "relation_state_mutation_events.jsonl",
        "frame_entry_000001.json",
        "sdf_capture_evidence.zip",
    ]
    for name in stale_names:
        (output / name).write_text("stale\n", encoding="utf-8")
    (output / "notes.txt").write_text("keep\n", encoding="utf-8")

    monkeypatch.setattr(
        runtime,
        "validate_probe_executable_file",
        lambda path: {
            "ready": True,
            "sha256": "a" * 64,
            "errors": [],
            "format": "SHIFT.SDFRuntimeProbePEValidation/1",
        },
    )
    monkeypatch.setattr(
        runtime,
        "new_capture_session_id",
        lambda: "cd" * 16,
    )

    result = runtime.prepare_probe_bundle(
        executable,
        output,
        probe_script=probe,
    )

    assert result["capture_session"] == {
        "format": "SHIFT.SDFRuntimeProbeCaptureSession/1",
        "version": 1,
        "id": "cd" * 16,
        "single_session_output": True,
        "stale_artifact_count": 3,
        "stale_artifacts_removed": sorted(stale_names),
    }
    assert result["probe"]["capture_session_id"] == "cd" * 16
    for name in stale_names:
        assert not (output / name).exists()
    assert (output / "notes.txt").read_text(encoding="utf-8") == "keep\n"
    assert f"--session-id {'cd' * 16}" in (
        output / "attach.gdb"
    ).read_text(encoding="utf-8")


def test_phase643_blocked_validation_preserves_existing_capture_evidence(
    tmp_path,
    monkeypatch,
):
    executable = tmp_path / "SHIFT.exe"
    executable.write_bytes(b"wrong")
    output = tmp_path / "capture"
    output.mkdir()
    probe = tmp_path / "probe.py"
    probe.write_text("# probe\n", encoding="utf-8")
    stale = output / "relation_state_mutation_events.jsonl"
    stale.write_text("old-evidence\n", encoding="utf-8")

    monkeypatch.setattr(
        runtime,
        "validate_probe_executable_file",
        lambda path: {
            "ready": False,
            "sha256": "b" * 64,
            "errors": ["sha256:mismatch"],
            "format": "SHIFT.SDFRuntimeProbePEValidation/1",
        },
    )

    result = runtime.prepare_probe_bundle(
        executable,
        output,
        probe_script=probe,
    )

    assert result["ready"] is False
    assert result["capture_session"]["stale_artifact_count"] == 0
    assert stale.read_text(encoding="utf-8") == "old-evidence\n"
