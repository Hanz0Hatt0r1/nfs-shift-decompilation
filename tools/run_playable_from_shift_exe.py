#!/usr/bin/env python3
"""Bootstrap and launch the playable Linux slice from one installed SHIFT.exe.

The launcher treats SHIFT.exe as the retail-install anchor, finds the nearest
ancestor containing Pakfiles, verifies the exact archive names required by the
current Silverstone + BMW milestone, then delegates to the existing fail-closed
playable bootstrap.  Archive SHA-256 admission and all renderer/runtime evidence
checks remain owned by the downstream bootstrap; this wrapper only removes
manual game-file path enumeration.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]

TRACK_DEFAULT = "Silverstone_Era3_GrandPrix"
VEHICLE_DEFAULT = "BMW_M3_E36"
REQUIRED_ARCHIVE_NAMES = (
    "Silverstone_Era3_GrandPrix.bff",
    "Silverstone_Era3_GrandPrix_Physics.bff",
    "BMW_M3_E36.bff",
    "BMW_M3_E36_Cockpit.bff",
    "RENDER.bff",
)


class InstallDiscoveryError(ValueError):
    """Raised when SHIFT.exe cannot be joined to one usable retail Pakfiles tree."""


@dataclass(frozen=True)
class ShiftInstall:
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
    # Typical retail installs place SHIFT.exe directly beside Pakfiles.  Some
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


def _run(command: list[str], *, cwd: Path) -> int:
    completed = subprocess.run(command, cwd=cwd, check=False)
    return int(completed.returncode)


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
    }, ensure_ascii=False, indent=2, sort_keys=True))

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
        print(f"profile: {profile}")
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
