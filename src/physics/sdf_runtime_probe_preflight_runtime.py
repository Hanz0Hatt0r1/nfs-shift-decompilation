"""Preflight the host and artifacts required for authentic SHIFT provider capture.

Phase 504 validates the supplied retail executable, probe script and the local
Wine/GDB runtime needed by ``tools/gdb_sdf_solver_probe.py``. It never launches
the game and never attaches to a process.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Sequence

from sdf_runtime_probe_launcher_runtime import (
    prepare_probe_bundle,
    require_runtime_tools,
)

FORMAT = "SHIFT.SDFRuntimeProbePreflight/1"
_GDB_PYTHON_MARKER = "SHIFT_GDB_PYTHON_OK"


def _tool_version(command: str, executable: str | None) -> dict[str, Any]:
    if executable is None:
        return {
            "path": None,
            "version": None,
            "ready": False,
        }
    try:
        result = subprocess.run(
            [executable, "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "path": executable,
            "version": None,
            "ready": False,
            "error": f"{type(exc).__name__}: {exc}",
        }
    text = (result.stdout or result.stderr or "").splitlines()
    return {
        "path": executable,
        "version": text[0].strip() if text else None,
        "ready": result.returncode == 0,
    }


def check_gdb_python(
    gdb_command: str = "gdb",
) -> dict[str, Any]:
    executable = shutil.which(gdb_command)
    if executable is None:
        return {
            "format": "SHIFT.GDBPythonPreflight/1",
            "version": 1,
            "ready": False,
            "path": None,
            "marker": _GDB_PYTHON_MARKER,
            "error": f"missing:{gdb_command}",
        }
    try:
        result = subprocess.run(
            [
                executable,
                "-q",
                "-nx",
                "-batch",
                "-ex",
                "python print(\"SHIFT_GDB_PYTHON_OK\")",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "format": "SHIFT.GDBPythonPreflight/1",
            "version": 1,
            "ready": False,
            "path": executable,
            "marker": _GDB_PYTHON_MARKER,
            "error": f"{type(exc).__name__}: {exc}",
        }
    output = "\n".join(
        part.strip()
        for part in (result.stdout or "", result.stderr or "")
        if part
    )
    ready = (
        result.returncode == 0
        and _GDB_PYTHON_MARKER in output
    )
    return {
        "format": "SHIFT.GDBPythonPreflight/1",
        "version": 1,
        "ready": ready,
        "path": executable,
        "marker": _GDB_PYTHON_MARKER,
        "output": output[-2000:],
        "error": None if ready else "gdb-python-unavailable",
    }


def preflight_provider_capture(
    executable: str | Path,
    output_dir: str | Path,
    *,
    probe_script: str | Path,
    wine_command: str = "wine",
    gdb_command: str = "gdb",
) -> dict[str, Any]:
    output_dir = Path(output_dir).resolve()
    script = Path(probe_script).resolve()
    artifacts = prepare_probe_bundle(
        executable,
        output_dir,
        probe_script=script,
    )
    tools = require_runtime_tools(
        wine_command=wine_command,
        gdb_command=gdb_command,
    )
    wine_info = _tool_version(wine_command, tools["wine"])
    gdb_info = _tool_version(gdb_command, tools["gdb"])
    gdb_python = check_gdb_python(gdb_command)

    errors = list(artifacts["validation"].get("errors") or [])
    if not script.is_file():
        errors.append(f"missing-probe-script:{script}")
    if not tools["ready"]:
        errors.extend(tools["errors"] or [])
    if tools["wine"] is not None and not wine_info["ready"]:
        errors.append("wine-version-query-failed")
    if tools["gdb"] is not None and not gdb_info["ready"]:
        errors.append("gdb-version-query-failed")
    if not gdb_python["ready"]:
        errors.append(str(gdb_python.get("error") or "gdb-python-unavailable"))

    ready = not errors
    manifest = {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "artifacts": artifacts,
        "probe_script": {
            "path": str(script),
            "exists": script.is_file(),
        },
        "runtime_tools": tools,
        "runtime_versions": {
            "wine": wine_info,
            "gdb": gdb_info,
        },
        "gdb_python": gdb_python,
        "capture": {
            "attach_mode": "explicit-pid-only",
            "launch_mode": "not-performed",
            "expected_provider_pre": "provider_pre_<provider>_<hit>.json",
            "expected_provider_post": "provider_post_<provider>_<hit>.json",
            "expected_reset_events": "scalar_reset_events.jsonl",
        },
        "errors": list(dict.fromkeys(errors)),
        "limitations": [
            "Preflight does not launch SHIFT.exe or attach GDB.",
            "A valid executable and working toolchain do not prove a live game install with all PAKFILES is present.",
            "Runtime provider identity and numeric parity remain capture evidence.",
        ],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "provider_capture_preflight.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Preflight an authentic SHIFT provider capture environment"
    )
    parser.add_argument("executable", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--probe-script",
        type=Path,
        required=True,
    )
    parser.add_argument("--wine", default="wine")
    parser.add_argument("--gdb", default="gdb")
    args = parser.parse_args(argv)
    report = preflight_provider_capture(
        args.executable,
        args.output,
        probe_script=args.probe_script,
        wine_command=args.wine,
        gdb_command=args.gdb,
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "executable_valid": report["artifacts"]["ready"],
        "probe_script_exists": report["probe_script"]["exists"],
        "wine": report["runtime_tools"]["wine"],
        "gdb": report["runtime_tools"]["gdb"],
        "gdb_python_ready": report["gdb_python"]["ready"],
        "errors": report["errors"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


__all__ = ["FORMAT", "check_gdb_python", "preflight_provider_capture"]


if __name__ == "__main__":
    raise SystemExit(main())
