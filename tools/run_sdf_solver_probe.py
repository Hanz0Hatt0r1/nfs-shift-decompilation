#!/usr/bin/env python3
"""Prepare or attach the retail SDF solver probe."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sdf_runtime_probe_launcher_runtime import (
    build_attach_command,
    describe_sdf_runtime_probe_launcher,
    prepare_probe_bundle,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path, help="validated retail SHIFT.exe")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("out/sdf-solver-capture"),
        help="capture output/bundle directory",
    )
    parser.add_argument(
        "--probe-script",
        type=Path,
        default=ROOT / "tools" / "gdb_sdf_solver_probe.py",
    )
    parser.add_argument("--attach-pid", type=int)
    parser.add_argument("--gdb", default="gdb")
    parser.add_argument("--print-contract", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.print_contract:
        print(json.dumps(
            describe_sdf_runtime_probe_launcher(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ))
        return 0

    try:
        manifest = prepare_probe_bundle(
            args.executable,
            args.output,
            probe_script=args.probe_script,
        )
    except Exception as exc:
        print(json.dumps({
            "format": "SHIFT.SDFRuntimeProbeLauncher/1",
            "status": "blocked",
            "ready": False,
            "error": str(exc),
        }, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2

    if not manifest["ready"]:
        print(json.dumps({
            "format": manifest["format"],
            "status": manifest["status"],
            "ready": False,
            "manifest": str(args.output / "probe_manifest.json"),
            "validation_errors": manifest["validation"]["errors"],
        }, ensure_ascii=False, indent=2))
        return 2

    result = {
        "format": manifest["format"],
        "status": "ready",
        "ready": True,
        "manifest": str(args.output / "probe_manifest.json"),
        "gdb_command_file": str(args.output / "attach.gdb"),
    }

    if args.attach_pid is not None:
        try:
            command = build_attach_command(
                pid=args.attach_pid,
                gdb_command_file=args.output / "attach.gdb",
                gdb_command=args.gdb,
            )
        except Exception as exc:
            print(json.dumps({
                **result,
                "status": "blocked",
                "ready": False,
                "error": str(exc),
            }, ensure_ascii=False, indent=2))
            return 2
        result["attach_command"] = command
        result["status"] = "attaching"
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return subprocess.call(command)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
