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
        "pre_solve_XXXXXX.json",
        "post_solve_XXXXXX.json",
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
    assert result["probe_targets"]["builtin_solver"] == "0x007b0f20"
    assert result["probe_targets"]["post_solve"] == "0x007b4110"


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
