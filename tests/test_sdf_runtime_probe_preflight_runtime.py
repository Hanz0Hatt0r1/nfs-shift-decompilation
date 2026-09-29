from pathlib import Path

import sdf_runtime_probe_preflight_runtime as runtime


def _artifacts():
    return {
        "ready": True,
        "validation": {"errors": []},
    }


def test_gdb_python_requires_gdb(monkeypatch):
    monkeypatch.setattr(runtime.shutil, "which", lambda name: None)
    result = runtime.check_gdb_python()
    assert result["ready"] is False
    assert result["error"] == "missing:gdb"


def test_gdb_python_probe_accepts_marker(monkeypatch):
    monkeypatch.setattr(runtime.shutil, "which", lambda name: "/usr/bin/gdb")

    class Result:
        returncode = 0
        stdout = "SHIFT_GDB_PYTHON_OK\n"
        stderr = ""

    monkeypatch.setattr(runtime.subprocess, "run", lambda *args, **kwargs: Result())
    result = runtime.check_gdb_python()
    assert result["ready"] is True


def test_gdb_python_probe_rejects_python_disabled(monkeypatch):
    monkeypatch.setattr(runtime.shutil, "which", lambda name: "/usr/bin/gdb")

    class Result:
        returncode = 1
        stdout = ""
        stderr = "Python scripting is not supported"

    monkeypatch.setattr(runtime.subprocess, "run", lambda *args, **kwargs: Result())
    result = runtime.check_gdb_python()
    assert result["ready"] is False
    assert result["error"] == "gdb-python-unavailable"


def test_preflight_combines_artifact_and_tool_errors(monkeypatch, tmp_path: Path):
    executable = tmp_path / "SHIFT.exe"
    executable.write_bytes(b"fixture")
    output = tmp_path / "capture"
    probe = tmp_path / "probe.py"
    probe.write_text("# probe\n", encoding="utf-8")

    monkeypatch.setattr(runtime, "prepare_probe_bundle", lambda *args, **kwargs: _artifacts())
    monkeypatch.setattr(
        runtime,
        "require_runtime_tools",
        lambda **kwargs: {
            "ready": False,
            "wine": None,
            "gdb": None,
            "errors": ["missing:wine", "missing:gdb"],
        },
    )
    monkeypatch.setattr(runtime, "_tool_version", lambda *args: {"ready": False, "path": None, "version": None})
    monkeypatch.setattr(runtime, "check_gdb_python", lambda *args: {"ready": False, "error": "missing:gdb"})
    monkeypatch.setattr(runtime, "validate_probe_script", lambda *args: {"ready": True, "errors": [], "markers": {}})

    result = runtime.preflight_provider_capture(
        executable,
        output,
        probe_script=probe,
    )

    assert result["ready"] is False
    assert result["errors"] == ["missing:wine", "missing:gdb"]
    assert (output / "provider_capture_preflight.json").is_file()


def test_preflight_is_ready_when_all_requirements_pass(monkeypatch, tmp_path: Path):
    executable = tmp_path / "SHIFT.exe"
    executable.write_bytes(b"fixture")
    output = tmp_path / "capture"
    probe = tmp_path / "probe.py"
    probe.write_text("# probe\n", encoding="utf-8")

    monkeypatch.setattr(runtime, "prepare_probe_bundle", lambda *args, **kwargs: _artifacts())
    monkeypatch.setattr(
        runtime,
        "require_runtime_tools",
        lambda **kwargs: {
            "ready": True,
            "wine": "/usr/bin/wine",
            "gdb": "/usr/bin/gdb",
            "errors": [],
        },
    )
    monkeypatch.setattr(runtime, "_tool_version", lambda command, executable: {
        "ready": True,
        "path": executable,
        "version": f"{command}-version",
    })
    monkeypatch.setattr(runtime, "check_gdb_python", lambda *args: {"ready": True})
    monkeypatch.setattr(runtime, "validate_probe_script", lambda *args: {"ready": True, "errors": [], "markers": {}})

    result = runtime.preflight_provider_capture(
        executable,
        output,
        probe_script=probe,
    )

    assert result["ready"] is True
    assert result["runtime_tools"]["wine"] == "/usr/bin/wine"
    assert result["runtime_versions"]["gdb"]["version"] == "gdb-version"


def test_preflight_passes_provider_only_to_bundle(monkeypatch, tmp_path: Path):
    executable = tmp_path / "SHIFT.exe"
    executable.write_bytes(b"fixture")
    output = tmp_path / "capture"
    probe = tmp_path / "probe.py"
    probe.write_text("# probe\n", encoding="utf-8")

    captured = {}

    def fake_prepare(*args, **kwargs):
        captured.update(kwargs)
        return _artifacts()

    monkeypatch.setattr(runtime, "prepare_probe_bundle", fake_prepare)
    monkeypatch.setattr(
        runtime,
        "require_runtime_tools",
        lambda **kwargs: {
            "ready": False,
            "wine": None,
            "gdb": None,
            "errors": ["missing:wine", "missing:gdb"],
        },
    )
    monkeypatch.setattr(runtime, "_tool_version", lambda *args: {"ready": False, "path": None, "version": None})
    monkeypatch.setattr(runtime, "check_gdb_python", lambda *args: {"ready": False, "error": "missing:gdb"})
    monkeypatch.setattr(runtime, "validate_probe_script", lambda *args: {"ready": True, "errors": [], "markers": {}})

    result = runtime.preflight_provider_capture(
        executable,
        output,
        probe_script=probe,
        provider_only=True,
    )

    assert captured["provider_only"] is True
    assert result["capture"]["probe_mode"] == "provider-only"
