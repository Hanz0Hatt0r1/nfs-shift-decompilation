"""Deterministic preparation/launch helpers for the retail SDF runtime probe."""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import zipfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from sdf_runtime_probe_capture_session import (
    clear_capture_artifacts,
    describe_capture_session,
    new_capture_session_id,
    validate_capture_session_id,
)
from sdf_runtime_probe_pe_validation import (
    EXPECTED_EXECUTABLE_SHA256,
    validate_probe_executable_file,
)

FORMAT = "SHIFT.SDFRuntimeProbeLauncher/1"


def resolve_probe_executable(
    input_path: str | Path,
    output_dir: str | Path,
) -> Path:
    """Resolve SHIFT.exe directly or extract the single retail executable from SHIFT.zip."""
    source = Path(input_path).resolve()
    output = Path(output_dir).resolve()
    if source.suffix.lower() != ".zip":
        if not source.is_file():
            raise FileNotFoundError(source)
        return source

    output.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source) as archive:
        candidates = [
            info for info in archive.infolist()
            if not info.is_dir() and Path(info.filename).name.lower() == "shift.exe"
        ]
        if len(candidates) != 1:
            raise ValueError(
                f"expected exactly one SHIFT.exe in archive, found {len(candidates)}"
            )
        info = candidates[0]
        target = output / "SHIFT.exe"
        target.write_bytes(archive.read(info))
        return target


def build_gdb_command_file(
    *,
    probe_script: str | Path,
    output_dir: str | Path,
    provider_only: bool = False,
    relation_timeline_only: bool = False,
    stop_after_relation_mutation: bool = False,
    capture_frames: int | None = None,
    capture_session_id: str | None = None,
) -> str:
    script = Path(probe_script).resolve()
    output = Path(output_dir).resolve()
    if provider_only and relation_timeline_only:
        raise ValueError(
            "provider_only and relation_timeline_only are mutually exclusive"
        )
    if provider_only and stop_after_relation_mutation:
        raise ValueError(
            "stop_after_relation_mutation is not supported in provider-only mode"
        )
    if capture_frames is not None:
        capture_frames = int(capture_frames)
        if capture_frames <= 0:
            raise ValueError("capture_frames must be positive")
        if provider_only:
            raise ValueError(
                "capture_frames is not supported in provider-only mode"
            )

    probe_args = f"{output}"
    if capture_session_id is not None:
        probe_args += (
            f" --session-id {validate_capture_session_id(capture_session_id)}"
        )
    if provider_only:
        probe_args += " --provider-only"
    if relation_timeline_only:
        probe_args += " --relation-timeline-only"
    if stop_after_relation_mutation:
        probe_args += " --stop-after-relation-mutation"
    if capture_frames is not None:
        probe_args += f" --capture-frames {capture_frames}"

    commands = (
        "set pagination off\n"
        "set confirm off\n"
        "handle SIGUSR1 nostop noprint pass\n"
        f"source {script}\n"
        f"sdf-probe {probe_args}\n"
        "continue\n"
    )
    if capture_frames is not None or stop_after_relation_mutation:
        commands += "detach\nquit\n"
    return commands


def prepare_probe_bundle(
    executable: str | Path,
    output_dir: str | Path,
    *,
    probe_script: str | Path,
    provider_only: bool = False,
    relation_timeline_only: bool = False,
    stop_after_relation_mutation: bool = False,
    capture_frames: int | None = None,
    startup_mode: str = "external-attach",
    gdb_proxy_port: int | None = None,
) -> dict[str, Any]:
    output = Path(output_dir).resolve()
    if provider_only and relation_timeline_only:
        raise ValueError(
            "provider_only and relation_timeline_only are mutually exclusive"
        )
    if provider_only and stop_after_relation_mutation:
        raise ValueError(
            "stop_after_relation_mutation is not supported in provider-only mode"
        )
    if startup_mode not in {"external-attach", "winedbg-gdb-proxy"}:
        raise ValueError(f"unsupported startup_mode: {startup_mode}")
    if startup_mode == "winedbg-gdb-proxy":
        if gdb_proxy_port is None:
            raise ValueError("winedbg-gdb-proxy startup requires gdb_proxy_port")
        if not 1 <= int(gdb_proxy_port) <= 65535:
            raise ValueError("gdb_proxy_port must be in range 1..65535")
        gdb_proxy_port = int(gdb_proxy_port)
    elif gdb_proxy_port is not None:
        raise ValueError(
            "gdb_proxy_port is only valid with winedbg-gdb-proxy startup"
        )
    exe = resolve_probe_executable(executable, output)
    validation = validate_probe_executable_file(exe)
    output.mkdir(parents=True, exist_ok=True)
    stale_artifacts_removed = (
        clear_capture_artifacts(output)
        if validation["ready"]
        else []
    )
    capture_session_id = new_capture_session_id()
    capture_session = describe_capture_session(
        capture_session_id,
        stale_artifacts_removed=stale_artifacts_removed,
    )

    if provider_only:
        expected_captures = [
            "provider_pre_<provider>_<hit>.json",
            "provider_post_<provider>_<hit>.json",
            "scalar_reset_events.jsonl",
            "provider_reset_effects.jsonl",
        ]
    elif relation_timeline_only:
        expected_captures = [
            "relation_state_mutation_events.jsonl",
            "frame_entry_XXXXXX.json",
            "post_solve_XXXXXX.json",
        ]
    else:
        expected_captures = [
            "relation_state_mutation_events.jsonl",
            "frame_entry_XXXXXX.json",
            "pre_solve_XXXXXX.json",
            "post_solve_XXXXXX.json",
            "provider_pre_<provider>_<hit>.json",
            "provider_post_<provider>_<hit>.json",
            "scalar_reset_events.jsonl",
            "provider_reset_effects.jsonl",
        ]

    command_file = output / "attach.gdb"
    command_file.write_text(
        build_gdb_command_file(
            probe_script=probe_script,
            output_dir=output,
            provider_only=provider_only,
            relation_timeline_only=relation_timeline_only,
            stop_after_relation_mutation=stop_after_relation_mutation,
            capture_frames=capture_frames,
            capture_session_id=capture_session_id,
        ),
        encoding="utf-8",
    )

    manifest = {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if validation["ready"] else "blocked",
        "ready": validation["ready"],
        "input": {
            "path": str(Path(executable).resolve()),
            "kind": "zip" if Path(executable).suffix.lower() == ".zip" else "executable",
        },
        "executable": {
            "path": str(exe),
            "sha256": validation["sha256"],
            "expected_sha256": EXPECTED_EXECUTABLE_SHA256,
            "validated": validation["ready"],
        },
        "validation": validation,
        "capture_session": capture_session,
        "probe": {
            "script": str(Path(probe_script).resolve()),
            "gdb_command_file": str(command_file),
            "output_dir": str(output),
            "mode": (
                "provider-only"
                if provider_only
                else (
                    "relation-timeline-only"
                    if relation_timeline_only
                    else "full"
                )
            ),
            "capture_session_id": capture_session_id,
            "capture_frames": capture_frames,
            "stop_after_relation_mutation": stop_after_relation_mutation,
            "startup_mode": startup_mode,
            "gdb_proxy_port": gdb_proxy_port,
            "startup_ordering": (
                "debuggee-created-under-winedbg-and-held-before-first-continue"
                if startup_mode == "winedbg-gdb-proxy"
                else "external-process-already-running-before-attach"
            ),
            "auto_detach": (
                capture_frames is not None
                or stop_after_relation_mutation
            ),
            "expected_captures": expected_captures,
        },
        "post_capture": {
            "automatic_timeline_correlation": not provider_only,
            "timeline_output": (
                None
                if provider_only
                else str(output / "relation_state_mutation_timeline.json")
            ),
            "timeline_format": (
                None
                if provider_only
                else "SHIFT.ConstraintRelationStateMutationTimelineCorrelation/1"
            ),
            "automatic_evidence_bundle": not provider_only,
            "evidence_bundle_output": (
                None
                if provider_only
                else str(output / "sdf_capture_evidence.zip")
            ),
            "evidence_bundle_format": (
                None
                if provider_only
                else "SHIFT.SDFRuntimeProbeEvidenceBundle/1"
            ),
        },
        "limitations": [
            "A live 32-bit Wine SHIFT.exe process is required for capture.",
            (
                "External attach mode never guesses a target process PID."
                if startup_mode == "external-attach"
                else (
                    "winedbg early-launch creates the validated process under "
                    "the debugger before GDB sends the first continue."
                )
            ),
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
        "-iex",
        "set pagination off",
        "-iex",
        "set confirm off",
        "-iex",
        "set debuginfod enabled off",
        "-iex",
        "handle SIGUSR1 nostop noprint pass",
        "-p",
        str(int(pid)),
        "-x",
        str(Path(gdb_command_file).resolve()),
    ]


def allocate_loopback_port() -> int:
    """Reserve an ephemeral loopback TCP port for a short-lived winedbg proxy."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def build_winedbg_launch_command(
    *,
    executable: str | Path,
    port: int,
    winedbg_command: str = "winedbg",
    game_args: Sequence[str] = (),
) -> list[str]:
    """Build a winedbg GDB-proxy launch that holds the Win32 target at startup."""
    if not 1 <= int(port) <= 65535:
        raise ValueError("port must be in range 1..65535")
    tool = shutil.which(winedbg_command)
    if tool is None:
        raise RuntimeError(f"WineDbg executable not found: {winedbg_command}")
    exe = Path(executable).resolve()
    if not exe.is_file():
        raise FileNotFoundError(exe)
    return [
        tool,
        "--gdb",
        "--no-start",
        "--port",
        str(int(port)),
        str(exe),
        *[str(arg) for arg in game_args],
    ]


def build_remote_gdb_command(
    *,
    port: int,
    gdb_command_file: str | Path,
    gdb_command: str = "gdb",
    connect_timeout: int = 30,
) -> list[str]:
    """Build GDB frontend invocation for a winedbg remote proxy."""
    if not 1 <= int(port) <= 65535:
        raise ValueError("port must be in range 1..65535")
    if int(connect_timeout) <= 0:
        raise ValueError("connect_timeout must be positive")
    tool = shutil.which(gdb_command)
    if tool is None:
        raise RuntimeError(f"GDB executable not found: {gdb_command}")
    return [
        tool,
        "-q",
        "-iex",
        "set pagination off",
        "-iex",
        "set confirm off",
        "-iex",
        "set debuginfod enabled off",
        "-iex",
        "set tcp auto-retry on",
        "-iex",
        f"set tcp connect-timeout {int(connect_timeout)}",
        "-ex",
        f"target remote 127.0.0.1:{int(port)}",
        "-x",
        str(Path(gdb_command_file).resolve()),
    ]


def launch_winedbg_gdb_proxy(
    command: Sequence[str],
    *,
    log_path: str | Path,
    workdir: str | Path | None = None,
) -> subprocess.Popen[bytes]:
    """Start winedbg with output redirected to a deterministic diagnostic log."""
    target = Path(log_path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    cwd = None if workdir is None else str(Path(workdir).resolve())
    with target.open("wb") as stream:
        return subprocess.Popen(
            [str(item) for item in command],
            cwd=cwd,
            stdout=stream,
            stderr=subprocess.STDOUT,
        )


def finish_winedbg_gdb_proxy(
    process: subprocess.Popen[bytes],
    *,
    timeout: float = 5.0,
) -> int:
    """Require the proxy to exit after the GDB frontend disconnects."""
    try:
        return int(process.wait(timeout=timeout))
    except subprocess.TimeoutExpired:
        process.terminate()
        try:
            return int(process.wait(timeout=2.0))
        except subprocess.TimeoutExpired:
            process.kill()
            return int(process.wait(timeout=2.0))


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
            "winedbg-early-launch": (
                "create retail SHIFT.exe under the Wine GDB proxy and install "
                "the probe before the first debugger continue"
            ),
            "provider-only": "omit per-frame and builtin-solver breakpoints; keep provider solve/reset and scalar-reset hooks",
            "bounded-full": "stop on the requested post-solve hit, then detach and quit GDB",
            "relation-timeline-only": "capture only relation mutation, frame entry and post-solve anchors",
            "stop-after-relation-mutation": "stop, detach and quit on the first post-solve anchor after a captured relation mutation",
            "capture-session": "isolate one output directory to one fresh evidence session",
        },
        "fail_closed": [
            "wrong retail SHA-256",
            "invalid PE/prologue targets",
            "missing Wine",
            "missing GDB",
            "missing WineDbg for early-launch mode",
            "invalid WineDbg GDB-proxy port",
            "non-positive attach PID",
            "non-positive bounded capture frame count",
            "bounded capture requested in provider-only mode",
            "provider-only combined with relation-timeline-only",
            "stop-after-relation-mutation requested in provider-only mode",
            "invalid capture-session identifier",
        ],
        "probe_targets": {
            "relation_state_mutation": "0x00757d2c",
            "builtin_solver": "0x007b0f20",
            "post_solve": "0x007b4110",
        },
    }


__all__ = [
    "FORMAT",
    "build_gdb_command_file",
    "resolve_probe_executable",
    "prepare_probe_bundle",
    "require_runtime_tools",
    "launch_retail",
    "build_attach_command",
    "allocate_loopback_port",
    "build_winedbg_launch_command",
    "build_remote_gdb_command",
    "launch_winedbg_gdb_proxy",
    "finish_winedbg_gdb_proxy",
    "describe_sdf_runtime_probe_launcher",
]
