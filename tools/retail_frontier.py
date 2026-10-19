#!/usr/bin/env python3
"""Run and analyze bounded SHIFT retail entrypoint probes.

A failed retail startup is an OBSERVATION, not a successful game boot.
The current first failure and regression comparison are persisted as JSON.
No copyrighted PE, P-code ELF, or capture payload is copied to the repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile

RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
FORMAT = "SHIFT.RetailStartupFrontier/1"
FAILURE = re.compile(
    r"failed after (?P<dispatches>[0-9]+) P-code function dispatches "
    r"across (?P<unique>[0-9]+) unique functions: (?P<reason>[^\n;]+)"
)
ADDRESS = re.compile(r"\breturn_address=(0x[0-9a-fA-F]+)")
CALLER = re.compile(r"\bcalled from (0x[0-9a-fA-F]+)")


def _json_objects(log: str):
    decoder = json.JSONDecoder()
    for match in re.finditer(r"(?m)^\s*\{", log):
        try:
            obj, _ = decoder.raw_decode(log[match.start():].lstrip())
        except ValueError:
            continue
        if isinstance(obj, dict) and str(obj.get("format", "")).startswith("SHIFT."):
            yield obj


def inspect_log(log: str, exit_code: int | None = None) -> dict:
    """Extract the last observed retail frontier, without guessing success."""
    frame = None
    for obj in _json_objects(log):
        if obj.get("format") == "SHIFT.NativeRuntimeFrameLoop/1":
            frame = obj
    failures = list(FAILURE.finditer(log))
    last = failures[-1] if failures else None
    status = "unknown"
    if exit_code == 124:
        status = "timeout"
    elif last:
        status = "blocked"
    elif frame is not None:
        status = "host-frame-loop"
    dispatches = int(last["dispatches"]) if last else (
        frame.get("recompiled_pcode_functions_dispatched") if frame else None
    )
    unique = int(last["unique"]) if last else (
        frame.get("recompiled_pcode_unique_functions_dispatched") if frame else None
    )
    reason = last["reason"].strip() if last else None
    text_after = log[last.start():last.start() + 2200] if last else ""
    addr = ADDRESS.search(text_after)
    caller = CALLER.search(text_after)
    validation = frame.get("validation_errors") if frame else None
    scheduler = frame.get("recompiled_guest_scheduler_state", {}) if frame else {}
    return {
        "format": FORMAT,
        "status": status,
        "exit_code": exit_code,
        "dispatches": dispatches,
        "unique_functions": unique,
        "blocker": reason,
        "caller": caller.group(1).lower() if caller else None,
        "return_address": addr.group(1).lower() if addr else None,
        "frames_rendered": frame.get("frames_rendered") if frame else None,
        "validation_errors": validation,
        "d3d9_vulkan_bridge": (
            frame.get("d3d9_vulkan_bridge", scheduler.get("d3d9_vulkan_bridge"))
            if frame else None
        ),
        "d3d9_clear_request": (
            frame.get("d3d9_clear_request", scheduler.get("d3d9_clear_request"))
            if frame else None
        ),
        "guest_main_thread_function": scheduler.get("main_thread_current_function"),
        "worker_waiting_count": scheduler.get("worker_waiting_count"),
        "pe_image_loaded": frame.get("recompiled_pe_image_loaded") if frame else (
            "Loaded PE32 image" in log
        ),
        "retail_rendering_proven": False,
    }


def compare(current: dict, baseline: dict) -> dict:
    """Regressions are objective counter/validation changes, not assumptions."""
    previous_count = baseline.get("dispatches")
    count = current.get("dispatches")
    previous_unique = baseline.get("unique_functions")
    unique = current.get("unique_functions")
    if current["status"] in ("unknown", "timeout"):
        return {"result": "unverified", "reason": "probe did not yield a usable frontier"}
    if current.get("validation_errors") not in (None, 0):
        return {"result": "regressed", "reason": "Vulkan validation errors"}
    if not isinstance(count, int) or not isinstance(previous_count, int):
        return {"result": "unverified", "reason": "missing dispatch counts"}
    if count < previous_count or (
        isinstance(unique, int) and isinstance(previous_unique, int)
        and unique < previous_unique
    ):
        return {"result": "regressed", "reason": "fewer dispatches or unique functions"}
    if count > previous_count or (
        isinstance(unique, int) and isinstance(previous_unique, int)
        and unique > previous_unique
    ):
        return {"result": "advanced", "reason": "more retail code executed"}
    if (current.get("blocker"), current.get("status")) == (
        baseline.get("blocker"), baseline.get("status")
    ):
        return {"result": "unchanged", "reason": "same frontier and stop"}
    return {"result": "changed", "reason": "same counts but a different stop; review required"}


def load_frontier(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() == ".json":
        obj = json.loads(text)
        if obj.get("format") != FORMAT:
            raise ValueError("baseline must be a SHIFT.RetailStartupFrontier/1 report or raw log")
        return obj
    return inspect_log(text)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ensure_probe_mesh(env: dict[str, str]) -> tempfile.TemporaryDirectory | None:
    """Use a tiny synthetic MGEO when a retail probe mesh was not supplied."""
    if env.get("SHIFT_ENTRYPOINT_PROBE_MESH"):
        return None
    temporary = tempfile.TemporaryDirectory(prefix="shift-retail-probe-")
    mesh = Path(temporary.name) / "startup-probe.mgeo"
    mesh.write_bytes(
        b"MGEO"
        + struct.pack("<HHIIIIII", 1, 0, 3, 3, 1, 0, 0, 2)
        + struct.pack("<9f", 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0)
        + struct.pack("<3I", 0, 1, 2)
        + b"{}"
    )
    env["SHIFT_ENTRYPOINT_PROBE_MESH"] = str(mesh)
    return temporary


def write_report(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(path)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    inspect = sub.add_parser("inspect", help="analyze an existing local or committed probe log")
    inspect.add_argument("--log", type=Path, required=True)
    inspect.add_argument("--exit-code", type=int)
    run = sub.add_parser("run", help="run existing bounded retail probe and inspect its stop")
    run.add_argument("--runtime", type=Path, required=True)
    run.add_argument("--artifacts", type=Path, required=True)
    run.add_argument("--build-dir", type=Path, required=True)
    run.add_argument("--pe", type=Path, required=True)
    run.add_argument("--game-data", type=Path, required=True)
    run.add_argument("--log", type=Path, required=True)
    run.add_argument("--frames", type=int, default=120)
    run.add_argument("--timeout", type=int, default=180)
    run.add_argument("--validation", action="store_true")
    run.add_argument("--build-runtime", action="store_true")
    for command in (inspect, run):
        command.add_argument("--baseline", type=Path)
        command.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    if args.operation == "inspect":
        result = inspect_log(args.log.read_text(encoding="utf-8", errors="replace"),
                             args.exit_code)
        result["probe_log_sha256"] = sha256(args.log)
    else:
        if args.frames < 1 or args.timeout < 1:
            parser.error("--frames and --timeout must be positive")
        if not args.pe.is_file() or sha256(args.pe) != RETAIL_SHA256:
            parser.error("PE is absent or SHA-256 is not the pinned PC retail 1.02 executable")
        if not args.runtime.is_file() and not args.build_runtime:
            parser.error("runtime not found; use --build-runtime or provide a compiled runtime")
        root = Path(__file__).resolve().parents[1]
        if args.build_runtime:
            build = subprocess.run([
                "bash", str(root / "tools/build_shift_runtime_cached.sh"),
                "--build-dir", str(args.build_dir),
            ], check=False)
            if build.returncode:
                print("native runtime build failed", file=sys.stderr)
                return 2
        args.log.parent.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env.update({
            "SHIFT_ENTRYPOINT_PROBE_FRAMES": str(args.frames),
            "SHIFT_ENTRYPOINT_TIMEOUT_SECONDS": str(args.timeout),
            "SHIFT_ENTRYPOINT_PROBE_VALIDATION": "1" if args.validation else "0",
        })
        command = [
            "bash", str(root / "tools/run_shift_recompiled_entrypoint_probe.sh"),
            str(args.runtime.resolve()), str(args.artifacts.resolve()),
            str(args.build_dir.resolve()), str(args.pe.resolve()),
            str(args.game_data.resolve()), str(args.log.resolve()),
        ]
        temporary_mesh = _ensure_probe_mesh(env)
        try:
            completed = subprocess.run(command, env=env, check=False)
        finally:
            if temporary_mesh is not None:
                temporary_mesh.cleanup()
        if not args.log.exists():
            print("probe did not create a log", file=sys.stderr)
            return 2
        result = inspect_log(args.log.read_text(encoding="utf-8", errors="replace"),
                             completed.returncode)
        result["pe_sha256"] = RETAIL_SHA256
        result["probe_log_sha256"] = sha256(args.log)

    if args.baseline:
        result["comparison"] = compare(result, load_frontier(args.baseline))
    write_report(args.output, result)
    print(json.dumps(result, sort_keys=True))
    if result["status"] in ("unknown", "timeout"):
        return 2
    if result.get("comparison", {}).get("result") in ("regressed", "unverified", "changed"):
        return 1
    if result.get("validation_errors") not in (None, 0):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
