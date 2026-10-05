from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace


def _load_cli():
    root = Path(__file__).resolve().parents[1]
    path = root / "tools" / "run_playable_from_shift_exe.py"
    spec = importlib.util.spec_from_file_location("run_playable_from_shift_exe_tested", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _install(tmp_path: Path, *, exe_in_bin: bool = False) -> tuple[Path, Path]:
    root = tmp_path / "Need for Speed SHIFT"
    exe_dir = root / "bin" if exe_in_bin else root
    exe_dir.mkdir(parents=True, exist_ok=True)
    shift_exe = exe_dir / "SHIFT.exe"
    shift_exe.write_bytes(b"MZ")

    pakfiles = root / "Pakfiles"
    paths = {
        "Silverstone_Era3_GrandPrix.bff": pakfiles / "Tracks" / "Silverstone_Era3_GrandPrix.bff",
        "Silverstone_Era3_GrandPrix_Physics.bff": pakfiles / "Tracks" / "Silverstone_Era3_GrandPrix_Physics.bff",
        "BMW_M3_E36.bff": pakfiles / "Vehicles" / "BMW_M3_E36.bff",
        "BMW_M3_E36_Cockpit.bff": pakfiles / "Vehicles" / "BMW_M3_E36_Cockpit.bff",
        "RENDER.bff": pakfiles / "Dir" / "RENDER.bff",
    }
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"bff")
    return shift_exe, pakfiles


def test_discovers_pakfiles_next_to_shift_exe(tmp_path):
    cli = _load_cli()
    shift_exe, pakfiles = _install(tmp_path)

    install = cli.discover_shift_install(shift_exe)

    assert install.shift_exe == shift_exe.resolve()
    assert install.game_root == shift_exe.parent.resolve()
    assert install.pakfiles == pakfiles.resolve()
    assert set(install.required_archives) == set(cli.REQUIRED_ARCHIVE_NAMES)


def test_discovers_parent_install_when_shift_exe_is_one_level_lower(tmp_path):
    cli = _load_cli()
    shift_exe, pakfiles = _install(tmp_path, exe_in_bin=True)

    install = cli.discover_shift_install(shift_exe)

    assert install.game_root == pakfiles.parent.resolve()
    assert install.pakfiles == pakfiles.resolve()


def test_missing_required_archive_fails_closed(tmp_path):
    cli = _load_cli()
    shift_exe, pakfiles = _install(tmp_path)
    (pakfiles / "Dir" / "RENDER.bff").unlink()

    try:
        cli.discover_shift_install(shift_exe)
    except cli.InstallDiscoveryError as exc:
        assert "RENDER.bff" in str(exc)
    else:
        raise AssertionError("missing RENDER.bff must fail install discovery")


def test_main_bootstraps_from_pakfiles_and_uses_shift_exe_as_pe_image(
    monkeypatch,
    tmp_path,
):
    cli = _load_cli()
    shift_exe, pakfiles = _install(tmp_path)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    capture = tmp_path / "shift_d3d9_capture.jsonl"
    capture.write_text("{}\n", encoding="utf-8")
    commands: list[tuple[list[str], Path]] = []

    def fake_run(command, *, cwd):
        commands.append((list(command), Path(cwd)))
        if "bootstrap_playable_linux_slice.py" in command[1]:
            out = Path(command[command.index("-o") + 1])
            out.mkdir(parents=True, exist_ok=True)
            (out / "vertical_slice_profile.json").write_text("{}\n", encoding="utf-8")
        return 0

    monkeypatch.setattr(cli, "_run", fake_run)

    rc = cli.main([
        str(shift_exe),
        "--workspace-root",
        str(workspace),
        "--renderer-capture-jsonl",
        str(capture),
    ])

    assert rc == 0
    assert len(commands) == 2
    bootstrap, bootstrap_cwd = commands[0]
    assert bootstrap_cwd == workspace.resolve()
    assert str(pakfiles.resolve()) in bootstrap
    assert "--renderer-pe-image" in bootstrap
    assert bootstrap[bootstrap.index("--renderer-pe-image") + 1] == str(shift_exe.resolve())
    assert "--interactive" in bootstrap
    assert "--validate-launch-plan" in bootstrap
    assert "Vehicles.zip" not in bootstrap
    assert "Silverstone_Era3_.zip" not in bootstrap
    assert "SHIFT_tail.zip" not in bootstrap

    launch, launch_cwd = commands[1]
    assert launch_cwd == workspace.resolve()
    assert "run_native_vertical_slice.py" in launch[1]
    assert str(workspace / "out" / "playable-bootstrap" / "vertical_slice_profile.json") in launch


def test_bootstrap_only_does_not_launch(monkeypatch, tmp_path):
    cli = _load_cli()
    shift_exe, _ = _install(tmp_path)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    capture = tmp_path / "capture.jsonl"
    capture.write_text("{}\n", encoding="utf-8")
    calls = []

    def fake_run(command, *, cwd):
        calls.append(list(command))
        out = Path(command[command.index("-o") + 1])
        out.mkdir(parents=True, exist_ok=True)
        (out / "vertical_slice_profile.json").write_text("{}\n", encoding="utf-8")
        return 0

    monkeypatch.setattr(cli, "_run", fake_run)

    rc = cli.main([
        str(shift_exe),
        "--workspace-root",
        str(workspace),
        "--renderer-capture-jsonl",
        str(capture),
        "--bootstrap-only",
    ])

    assert rc == 0
    assert len(calls) == 1
