#!/usr/bin/env python3
"""Bootstrap and launch the playable Linux slice from one installed SHIFT.exe.

The launcher treats SHIFT.exe as the retail-install anchor, finds the nearest
ancestor containing Pakfiles, verifies the exact archive names required by the
current Silverstone + BMW milestone, then delegates to the existing fail-closed
playable bootstrap. Archive SHA-256 admission and all renderer/runtime evidence
checks remain owned by the downstream bootstrap; this wrapper only removes
manual game-file path enumeration.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import NamedTuple, Sequence

ROOT = Path(__file__).resolve().parents[1]
PROGRESS_SITE_DIR = ROOT / "tools" / "resource_progress_site"

TRACK_DEFAULT = "Silverstone_Era3_GrandPrix"
VEHICLE_DEFAULT = "BMW_M3_E36"
BOOTSTRAP_HEARTBEAT_SECONDS = 10.0
RUNTIME_HEARTBEAT_SECONDS = 60.0
REQUIRED_ARCHIVE_NAMES = (
    "Silverstone_Era3_GrandPrix.bff",
    "Silverstone_Era3_GrandPrix_Physics.bff",
    "BMW_M3_E36.bff",
    "BMW_M3_E36_Cockpit.bff",
    "RENDER.bff",
)


class InstallDiscoveryError(ValueError):
    """Raised when SHIFT.exe cannot be joined to one usable retail Pakfiles tree."""


class ShiftInstall(NamedTuple):
    shift_exe: Path
    game_root: Path
    pakfiles: Path
    required_archives: dict[str, Path]


def _direct_child_casefold(parent: Path, name: str) -> Path | None:
    target = name.casefold()
    try:
        children = list(parent.iterdir())
    except OSError:
        return None
    matches = [child for child in children if child.name.casefold() == target]
    if len(matches) != 1:
        return None
    return matches[0]


def _find_game_root(shift_exe: Path) -> tuple[Path, Path]:
    # Typical retail installs place SHIFT.exe directly beside Pakfiles. Some
    # repacks/wrappers place the executable one directory lower, so walk a small
    # bounded parent chain instead of assuming one fixed layout.
    for root in list(shift_exe.parents)[:6]:
        pakfiles = _direct_child_casefold(root, "Pakfiles")
        if pakfiles is not None and pakfiles.is_dir():
            return root, pakfiles
    raise InstallDiscoveryError(
        f"cannot find a Pakfiles directory in the SHIFT.exe parent chain: {shift_exe}"
    )


def _required_archive_index(pakfiles: Path) -> dict[str, Path]:
    required = {name.casefold(): name for name in REQUIRED_ARCHIVE_NAMES}
    found: dict[str, list[Path]] = {key: [] for key in required}
    for path in pakfiles.rglob("*"):
        if not path.is_file():
            continue
        key = path.name.casefold()
        if key in found:
            found[key].append(path.resolve())

    missing = [required[key] for key, rows in found.items() if not rows]
    ambiguous = {
        required[key]: rows
        for key, rows in found.items()
        if len(rows) > 1
    }
    if missing:
        raise InstallDiscoveryError(
            "required retail archives are missing under Pakfiles: " + ", ".join(missing)
        )
    if ambiguous:
        rendered = "; ".join(
            f"{name} -> {', '.join(str(path) for path in rows)}"
            for name, rows in ambiguous.items()
        )
        raise InstallDiscoveryError(
            "required retail archive basename is ambiguous under Pakfiles: " + rendered
        )

    return {
        required[key]: rows[0]
        for key, rows in found.items()
    }


def discover_shift_install(raw_shift_exe: str | Path) -> ShiftInstall:
    shift_exe = Path(raw_shift_exe).expanduser().resolve()
    if not shift_exe.is_file():
        raise InstallDiscoveryError(f"SHIFT.exe not found: {shift_exe}")
    if shift_exe.name.casefold() != "shift.exe":
        raise InstallDiscoveryError(
            f"expected a file named SHIFT.exe, got: {shift_exe.name}"
        )
    game_root, pakfiles = _find_game_root(shift_exe)
    required_archives = _required_archive_index(pakfiles)
    return ShiftInstall(
        shift_exe=shift_exe,
        game_root=game_root.resolve(),
        pakfiles=pakfiles.resolve(),
        required_archives=required_archives,
    )


def _default_capture_jsonl() -> Path | None:
    candidates = [
        Path.cwd() / "shift_d3d9_capture.jsonl",
        ROOT / "shift_d3d9_capture.jsonl",
    ]
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.is_file():
            return resolved
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("shift_exe", help="path to the installed retail SHIFT.exe")
    parser.add_argument(
        "-o",
        "--output",
        default="out/playable-bootstrap",
        help="bootstrap output directory, workspace-relative unless absolute",
    )
    parser.add_argument(
        "--workspace-root",
        default=str(ROOT),
        help="repository/workspace root used by generated runtime profiles",
    )
    parser.add_argument("--track", default=TRACK_DEFAULT)
    parser.add_argument("--vehicle", default=VEHICLE_DEFAULT)
    capture = parser.add_mutually_exclusive_group()
    capture.add_argument(
        "--renderer-capture-jsonl",
        help="historical D3D9 renderer capture; defaults to shift_d3d9_capture.jsonl in cwd/repo",
    )
    capture.add_argument(
        "--renderer-capture-result",
        help="ready external-sampler capture-result bundle",
    )
    parser.add_argument("--renderer-capture-root")
    parser.add_argument(
        "--runtime",
        default="native_runtime/build/shift_runtime",
        help="native runtime executable, workspace-relative unless absolute",
    )
    parser.add_argument(
        "--validation",
        action="store_true",
        help="enable Vulkan validation in bootstrap validation and final launch",
    )
    parser.add_argument(
        "--bootstrap-only",
        action="store_true",
        help="prepare and validate the playable profile but do not launch it",
    )
    return parser


def _output_path(workspace_root: Path, raw: str | Path) -> Path:
    value = Path(raw).expanduser()
    return value.resolve() if value.is_absolute() else (workspace_root / value).resolve()


def _capture_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> list[str]:
    if args.renderer_capture_result:
        if args.renderer_capture_root:
            parser.error("--renderer-capture-root cannot be combined with --renderer-capture-result")
        return ["--renderer-capture-result", str(Path(args.renderer_capture_result).expanduser().resolve())]

    capture = (
        Path(args.renderer_capture_jsonl).expanduser().resolve()
        if args.renderer_capture_jsonl
        else _default_capture_jsonl()
    )
    if capture is None or not capture.is_file():
        parser.error(
            "renderer capture not found; provide --renderer-capture-jsonl or "
            "--renderer-capture-result (game files are discovered from SHIFT.exe, "
            "but renderer runtime evidence is not part of the retail install)"
        )
    values = ["--renderer-capture-jsonl", str(capture)]
    if args.renderer_capture_root:
        values.extend([
            "--renderer-capture-root",
            str(Path(args.renderer_capture_root).expanduser().resolve()),
        ])
    return values


def _command_stage(command: Sequence[str]) -> tuple[str, float]:
    script = Path(command[1]).name if len(command) > 1 else Path(command[0]).name
    if script == "bootstrap_playable_linux_slice.py":
        return "playable-bootstrap", BOOTSTRAP_HEARTBEAT_SECONDS
    if script == "run_native_vertical_slice.py":
        return "native-runtime", RUNTIME_HEARTBEAT_SECONDS
    return script or "subprocess", BOOTSTRAP_HEARTBEAT_SECONDS


def _strip_resource_progress_env(
    environment: dict[str, str],
    *,
    cwd: Path,
) -> dict[str, str]:
    """Remove bootstrap-only progress hooks from a non-bootstrap child environment."""
    result = dict(environment)
    result.pop("SHIFT_RESOURCE_PROGRESS", None)
    existing_pythonpath = result.get("PYTHONPATH")
    if existing_pythonpath is None:
        return result

    child_cwd = os.path.realpath(os.fspath(cwd))
    progress_site = os.path.normcase(os.path.realpath(os.fspath(PROGRESS_SITE_DIR)))

    def child_location(value: str) -> str:
        expanded = os.path.expanduser(value)
        if not os.path.isabs(expanded):
            expanded = os.path.join(child_cwd, expanded)
        return os.path.normcase(os.path.realpath(expanded))

    result["PYTHONPATH"] = os.pathsep.join(
        value
        for value in existing_pythonpath.split(os.pathsep)
        if not value or child_location(value) != progress_site
    )
    return result


def _run(command: list[str], *, cwd: Path) -> int:
    stage, heartbeat_seconds = _command_stage(command)
    environment = os.environ.copy()
    # Preserve child output as a live diagnostic stream even when stdout is not
    # attached to an interactive terminal.
    environment["PYTHONUNBUFFERED"] = "1"
    if stage == "playable-bootstrap":
        existing_pythonpath = environment.get("PYTHONPATH", "")
        environment["PYTHONPATH"] = os.pathsep.join(
            value
            for value in (str(PROGRESS_SITE_DIR), existing_pythonpath)
            if value
        )
        environment["SHIFT_RESOURCE_PROGRESS"] = "1"
    else:
        environment = _strip_resource_progress_env(environment, cwd=cwd)

    print(f"[shift-launch] stage={stage} event=start cwd={cwd}", flush=True)
    print(f"[shift-launch] stage={stage} command={shlex.join(command)}", flush=True)
    started = time.monotonic()
    process = subprocess.Popen(command, cwd=cwd, env=environment)
    print(
        f"[shift-launch] stage={stage} event=spawn pid={process.pid} "
        f"heartbeat={heartbeat_seconds:.0f}s",
        flush=True,
    )

    try:
        while True:
            try:
                returncode = process.wait(timeout=heartbeat_seconds)
                break
            except subprocess.TimeoutExpired:
                elapsed = time.monotonic() - started
                print(
                    f"[shift-launch] stage={stage} event=heartbeat pid={process.pid} "
                    f"elapsed={elapsed:.1f}s status=running",
                    flush=True,
                )
    except KeyboardInterrupt:
        elapsed = time.monotonic() - started
        print(
            f"[shift-launch] stage={stage} event=interrupt pid={process.pid} "
            f"elapsed={elapsed:.1f}s",
            file=sys.stderr,
            flush=True,
        )
        process.terminate()
        try:
            process.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        return 130

    elapsed = time.monotonic() - started
    print(
        f"[shift-launch] stage={stage} event=exit pid={process.pid} "
        f"elapsed={elapsed:.1f}s returncode={returncode}",
        flush=True,
    )
    return int(returncode)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        install = discover_shift_install(args.shift_exe)
    except (InstallDiscoveryError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    workspace_root = Path(args.workspace_root).expanduser().resolve()
    if not workspace_root.is_dir():
        print(f"error: workspace root not found: {workspace_root}", file=sys.stderr)
        return 2
    output = _output_path(workspace_root, args.output)

    capture_args = _capture_args(args, parser)
    bootstrap = [
        sys.executable,
        str(ROOT / "tools" / "bootstrap_playable_linux_slice.py"),
        str(install.pakfiles),
        "-o",
        str(output),
        "--track",
        args.track,
        "--vehicle",
        args.vehicle,
        "--workspace-root",
        str(workspace_root),
        "--renderer-pe-image",
        str(install.shift_exe),
        "--interactive",
        "--validate-launch-plan",
        "--runtime",
        args.runtime,
        *capture_args,
    ]
    if args.validation:
        bootstrap.append("--validation")

    print(json.dumps({
        "format": "SHIFT.PlayableInstallBootstrapPlan/1",
        "shift_exe": str(install.shift_exe),
        "game_root": str(install.game_root),
        "pakfiles": str(install.pakfiles),
        "required_archives": {
            name: str(path) for name, path in install.required_archives.items()
        },
        "output": str(output),
        "logging": {
            "child_python_unbuffered": True,
            "bootstrap_heartbeat_seconds": BOOTSTRAP_HEARTBEAT_SECONDS,
            "runtime_heartbeat_seconds": RUNTIME_HEARTBEAT_SECONDS,
            "resource_archive_progress": True,
            "resource_entry_progress_interval": 250,
        },
    }, ensure_ascii=False, indent=2, sort_keys=True), flush=True)

    rc = _run(bootstrap, cwd=workspace_root)
    if rc != 0:
        return rc

    profile = output / "vertical_slice_profile.json"
    if not profile.is_file():
        print(
            f"error: bootstrap succeeded without playable profile: {profile}",
            file=sys.stderr,
        )
        return 2
    if args.bootstrap_only:
        print(f"profile: {profile}", flush=True)
        return 0

    launch = [
        sys.executable,
        str(ROOT / "tools" / "run_native_vertical_slice.py"),
        str(profile),
        "--runtime",
        args.runtime,
    ]
    if args.validation:
        launch.append("--validation")
    return _run(launch, cwd=workspace_root)


if __name__ == "__main__":
    raise SystemExit(main())
