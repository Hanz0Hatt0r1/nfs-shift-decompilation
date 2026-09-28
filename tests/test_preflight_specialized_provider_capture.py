from pathlib import Path

import tools.preflight_specialized_provider_capture as tool


def test_parser_requires_executable_output_and_probe():
    parser = tool.build_parser()
    try:
        parser.parse_args([])
    except SystemExit:
        return
    raise AssertionError("required preflight arguments were not enforced")


def test_cli_delegates_and_prints_machine_readable_summary(monkeypatch, tmp_path: Path, capsys):
    executable = tmp_path / "SHIFT.exe"
    output = tmp_path / "capture"
    probe = tmp_path / "probe.py"
    executable.write_bytes(b"fixture")
    probe.write_text("# probe\n", encoding="utf-8")

    monkeypatch.setattr(
        tool,
        "preflight_provider_capture",
        lambda executable, output_dir, *, probe_script, wine_command="wine", gdb_command="gdb": {
            "format": "SHIFT.SDFRuntimeProbePreflight/1",
            "status": "blocked",
            "ready": False,
            "artifacts": {"ready": True},
            "probe_script": {"exists": True},
            "runtime_tools": {"wine": None, "gdb": None},
            "gdb_python": {"ready": False},
            "errors": ["missing:wine", "missing:gdb"],
        },
    )

    result = tool.main([
        str(executable),
        str(output),
        "--probe-script",
        str(probe),
    ])

    assert result == 2
    text = capsys.readouterr().out
    assert '"ready": false' in text
    assert "missing:wine" in text
