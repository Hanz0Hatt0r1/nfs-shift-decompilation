from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_cli():
    root = Path(__file__).resolve().parents[1]
    path = root / "tools" / "run_playable_from_shift_exe.py"
    spec = importlib.util.spec_from_file_location(
        "run_playable_from_shift_exe_progress_env_tested",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_bootstrap_subprocess_enables_resource_progress_site(monkeypatch, tmp_path):
    cli = _load_cli()
    captured = {}

    class FakeProcess:
        pid = 777

        def wait(self, timeout=None):
            return 0

    def fake_popen(command, *, cwd, env):
        captured["command"] = list(command)
        captured["cwd"] = Path(cwd)
        captured["env"] = dict(env)
        return FakeProcess()

    monkeypatch.setattr(cli.subprocess, "Popen", fake_popen)

    rc = cli._run(
        [
            "python3",
            str(cli.ROOT / "tools" / "bootstrap_playable_linux_slice.py"),
        ],
        cwd=tmp_path,
    )

    assert rc == 0
    env = captured["env"]
    assert env["PYTHONUNBUFFERED"] == "1"
    assert env["SHIFT_RESOURCE_PROGRESS"] == "1"
    assert env["PYTHONPATH"].split(cli.os.pathsep)[0] == str(cli.PROGRESS_SITE_DIR)


def test_native_runtime_strips_inherited_resource_progress_site(monkeypatch, tmp_path):
    cli = _load_cli()
    captured = {}

    class FakeProcess:
        pid = 778

        def wait(self, timeout=None):
            return 0

    def fake_popen(command, *, cwd, env):
        captured["env"] = dict(env)
        return FakeProcess()

    monkeypatch.setattr(cli.subprocess, "Popen", fake_popen)
    monkeypatch.setenv("SHIFT_RESOURCE_PROGRESS", "1")
    relative_progress_site = cli.os.path.relpath(cli.PROGRESS_SITE_DIR, tmp_path)
    monkeypatch.setenv(
        "PYTHONPATH",
        cli.os.pathsep.join([
            "before",
            "",
            relative_progress_site,
            "after",
        ]),
    )

    rc = cli._run(
        [
            "python3",
            str(cli.ROOT / "tools" / "run_native_vertical_slice.py"),
        ],
        cwd=tmp_path,
    )

    assert rc == 0
    env = captured["env"]
    assert env["PYTHONUNBUFFERED"] == "1"
    assert "SHIFT_RESOURCE_PROGRESS" not in env
    assert env["PYTHONPATH"].split(cli.os.pathsep) == ["before", "", "after"]
