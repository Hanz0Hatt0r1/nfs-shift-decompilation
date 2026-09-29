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

def test_validate_probe_script_accepts_provider_probe(tmp_path: Path):
    probe = tmp_path / "probe.py"
    probe.write_text(
        "\n".join([
            "import gdb",
            "class Probe(gdb.Breakpoint): pass",
            "class ProviderResetReturnProbe(gdb.FinishBreakpoint): pass",
            "def sdf_probe(): pass",
            "name = 'provider_pre_000000.json'",
            "name2 = 'provider_post_000000.json'",
            "path = 'scalar_reset_events.jsonl'",
            "build_provider_capture_payload = object()",
        ]) + "\n",
        encoding="utf-8",
    )

    report = runtime.validate_probe_script(probe)

    assert report["ready"] is True
    assert report["errors"] == []
    assert all(item["present"] for item in report["markers"].values())


def test_validate_probe_script_blocks_unrelated_python(tmp_path: Path):
    probe = tmp_path / "probe.py"
    probe.write_text("print('hello')\n", encoding="utf-8")

    report = runtime.validate_probe_script(probe)

    assert report["ready"] is False
    assert "probe-script-missing-marker:python-gdb" in report["errors"]
    assert "probe-script-missing-marker:sdf-command" in report["errors"]
    assert "probe-script-missing-marker:provider-pre-capture" in report["errors"]
    assert "probe-script-missing-marker:provider-post-capture" in report["errors"]
    assert "probe-script-missing-marker:scalar-reset-capture" in report["errors"]
    assert "probe-script-missing-marker:provider-snapshot" in report["errors"]
