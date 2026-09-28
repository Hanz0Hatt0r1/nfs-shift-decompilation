"""Deterministic preparation/launch helpers for the retail SDF runtime probe."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

from sdf_runtime_probe_pe_validation import (
    EXPECTED_EXECUTABLE_SHA256,
    validate_probe_executable_file,
)

FORMAT = "SHIFT.SDFRuntimeProbeLauncher/1"


def build_gdb_command_file(
    *,
    probe_script: str | Path,
    output_dir: str | Path,
) -> str:
    script = Path(probe_script).resolve()
    output = Path(output_dir).resolve()
    return (
        "set pagination off\n"
        "set confirm off\n"
        f"source {script}\n"
        f"sdf-probe {output}\n"
        "continue\n"
    )


def prepare_probe_bundle(
    executable: str | Path,
    output_dir: str | Path,
    *,
    probe_script: str | Path,
) -> dict[str, Any]:
    exe = Path(executable).resolve()
    output = Path(output_dir).resolve()
    validation = validate_probe_executable_file(exe)
    output.mkdir(parents=True, exist_ok=True)

    command_file = output / "attach.gdb"
    command_file.write_text(
        build_gdb_command_file(
            probe_script=probe_script,
            output_dir=output,
        ),
        encoding="utf-8",
    )

    manifest = {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if validation["ready"] else "blocked",
        "ready": validation["ready"],
        "executable": {
            "path": str(exe),
            "sha256": validation["sha256"],
            "expected_sha256": EXPECTED_EXECUTABLE_SHA256,
            "validated": validation["ready"],
        },
        "validation": validation,
        "probe": {
            "script": str(Path(probe_script).resolve()),
            "gdb_command_file": str(command_file),
            "output_dir": str(output),
            "expected_captures": [
                "pre_solve_XXXXXX.json",
                "post_solve_XXXXXX.json",
            ],
        },
        "limitations": [
            "A live 32-bit Wine SHIFT.exe process is required for capture.",
            "The launcher never guesses a target process PID.",
            "The launcher never modifies SHIFT.exe.",
        ],
    }
    (output / "probe_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def require_runtime_tools(
    *,
    wine_command: str = "wine",
    gdb_command: str = "gdb",
) -> dict[str, Any]:
    wine = shutil.which(wine_command)
    gdb = shutil.which(gdb_command)
    errors = []
    if wine is None:
        errors.append(f"missing:{wine_command}")
    if gdb is None:
        errors.append(f"missing:{gdb_command}")
    return {
        "format": "SHIFT.SDFRuntimeProbeToolCheck/1",
        "version": 1,
        "ready": not errors,
        "status": "available" if not errors else "unavailable",
        "wine": wine,
        "gdb": gdb,
        "errors": errors,
    }


def launch_retail(
    executable: str | Path,
    *,
    workdir: str | Path | None = None,
    wine_command: str = "wine",
    game_args: Sequence[str] = (),
) -> subprocess.Popen[bytes]:
    tool = shutil.which(wine_command)
    if tool is None:
        raise RuntimeError(f"Wine executable not found: {wine_command}")
    exe = Path(executable).resolve()
    if not exe.is_file():
        raise FileNotFoundError(exe)
    cwd = None if workdir is None else str(Path(workdir).resolve())
    return subprocess.Popen(
        [tool, str(exe), *[str(arg) for arg in game_args]],
        cwd=cwd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def build_attach_command(
    *,
    pid: int,
    gdb_command_file: str | Path,
    gdb_command: str = "gdb",
) -> list[str]:
    if int(pid) <= 0:
        raise ValueError("pid must be positive")
    tool = shutil.which(gdb_command)
    if tool is None:
        raise RuntimeError(f"GDB executable not found: {gdb_command}")
    return [
        tool,
        "-q",
        "-p",
        str(int(pid)),
        "-x",
        str(Path(gdb_command_file).resolve()),
    ]


def describe_sdf_runtime_probe_launcher() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "source-backed",
        "ready": True,
        "modes": {
            "prepare": "validate retail PE and write probe_manifest.json + attach.gdb",
            "launch": "start retail SHIFT.exe under explicit Wine command",
            "attach": "attach GDB to explicit user-supplied PID using attach.gdb",
        },
        "fail_closed": [
            "wrong retail SHA-256",
            "invalid PE/prologue targets",
            "missing Wine",
            "missing GDB",
            "non-positive attach PID",
        ],
        "probe_targets": {
            "builtin_solver": "0x007b0f20",
            "post_solve": "0x007b4110",
        },
    }


__all__ = [
    "FORMAT",
    "build_gdb_command_file",
    "prepare_probe_bundle",
    "require_runtime_tools",
    "launch_retail",
    "build_attach_command",
    "describe_sdf_runtime_probe_launcher",
]
