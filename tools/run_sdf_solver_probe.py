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
PHYSICS_SRC = ROOT / "src" / "physics"
for path in (ROOT, PHYSICS_SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from sdf_runtime_probe_launcher_runtime import (
    allocate_loopback_port,
    build_attach_command,
    build_remote_gdb_command,
    build_winedbg_launch_command,
    describe_sdf_runtime_probe_launcher,
    finish_winedbg_gdb_proxy,
    launch_winedbg_gdb_proxy,
    prepare_probe_bundle,
)

from relation_state_mutation_timeline_correlation_runtime import (
    analyze_relation_state_mutation_capture_directory,
)

from sdf_runtime_probe_evidence_bundle import (
    build_sdf_runtime_probe_evidence_bundle,
)

from sdf_runtime_probe_evidence_bundle_verify import (
    verify_sdf_runtime_probe_evidence_bundle,
)

from sdf_runtime_probe_evidence_bundle_replay import (
    replay_sdf_runtime_probe_evidence_bundle,
)

TIMELINE_OUTPUT_NAME = "relation_state_mutation_timeline.json"


def finalize_relation_state_mutation_capture(
    output_dir: str | Path,
) -> dict:
    """Build and persist the Phase 637 timeline report after a full capture."""
    output = Path(output_dir).resolve()
    report = analyze_relation_state_mutation_capture_directory(output)
    target = output / TIMELINE_OUTPUT_NAME
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )
    return report


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
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--attach-pid", type=int)
    target.add_argument(
        "--launch-under-winedbg",
        action="store_true",
        help=(
            "create SHIFT.exe under winedbg's GDB proxy and install the "
            "probe before the first debugger continue"
        ),
    )
    parser.add_argument("--gdb", default="gdb")
    parser.add_argument("--winedbg", default="winedbg")
    parser.add_argument(
        "--winedbg-port",
        type=int,
        help="fixed loopback GDB-proxy port; default allocates an ephemeral port",
    )
    parser.add_argument(
        "--gdb-connect-timeout",
        type=int,
        default=30,
        help="seconds GDB retries the WineDbg proxy connection",
    )
    parser.add_argument(
        "--game-arg",
        action="append",
        default=[],
        help="argument passed to SHIFT.exe in --launch-under-winedbg mode",
    )
    parser.add_argument("--provider-only", action="store_true")
    parser.add_argument(
        "--relation-timeline-only",
        action="store_true",
        help=(
            "install only relation mutation, frame-entry and post-solve "
            "breakpoints to reduce debugger overhead"
        ),
    )
    parser.add_argument(
        "--stop-after-relation-mutation",
        action="store_true",
        help=(
            "stop, detach and quit GDB at the first post-solve anchor "
            "after a captured relation-state mutation"
        ),
    )
    parser.add_argument(
        "--capture-frames",
        type=int,
        help=(
            "full or relation-timeline mode: stop on the Nth post-solve hit, "
            "then detach and quit GDB"
        ),
    )
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

    if args.launch_under_winedbg and args.executable.suffix.lower() == ".zip":
        print(json.dumps({
            "format": "SHIFT.SDFRuntimeProbeLauncher/1",
            "status": "blocked",
            "ready": False,
            "error": (
                "--launch-under-winedbg requires a direct retail SHIFT.exe; "
                "ZIP input is prepare/validation-only because the extracted "
                "executable has no game directory"
            ),
        }, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2

    if not args.launch_under_winedbg and (
        args.winedbg_port is not None or args.game_arg
    ):
        print(json.dumps({
            "format": "SHIFT.SDFRuntimeProbeLauncher/1",
            "status": "blocked",
            "ready": False,
            "error": (
                "--winedbg-port and --game-arg require "
                "--launch-under-winedbg"
            ),
        }, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2

    startup_port = None
    if args.launch_under_winedbg:
        try:
            startup_port = (
                int(args.winedbg_port)
                if args.winedbg_port is not None
                else allocate_loopback_port()
            )
        except Exception as exc:
            print(json.dumps({
                "format": "SHIFT.SDFRuntimeProbeLauncher/1",
                "status": "blocked",
                "ready": False,
                "error": f"{type(exc).__name__}: {exc}",
            }, ensure_ascii=False, indent=2), file=sys.stderr)
            return 2

    try:
        manifest = prepare_probe_bundle(
            args.executable,
            args.output,
            probe_script=args.probe_script,
            provider_only=args.provider_only,
            relation_timeline_only=args.relation_timeline_only,
            stop_after_relation_mutation=args.stop_after_relation_mutation,
            capture_frames=args.capture_frames,
            startup_mode=(
                "winedbg-gdb-proxy"
                if args.launch_under_winedbg
                else "external-attach"
            ),
            gdb_proxy_port=startup_port,
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
        "mode": (
            "provider-only"
            if args.provider_only
            else (
                "relation-timeline-only"
                if args.relation_timeline_only
                else "full"
            )
        ),
        "capture_frames": args.capture_frames,
        "stop_after_relation_mutation": args.stop_after_relation_mutation,
        "auto_detach": (
            args.capture_frames is not None
            or args.stop_after_relation_mutation
        ),
        "startup_mode": (
            "winedbg-gdb-proxy"
            if args.launch_under_winedbg
            else "external-attach"
        ),
    }

    if args.attach_pid is not None or args.launch_under_winedbg:
        winedbg_process = None
        winedbg_returncode = None
        if args.launch_under_winedbg:
            winedbg_log = (args.output / "winedbg_gdb_proxy.log").resolve()
            try:
                launch_command = build_winedbg_launch_command(
                    executable=manifest["executable"]["path"],
                    port=startup_port,
                    winedbg_command=args.winedbg,
                    game_args=args.game_arg,
                )
                command = build_remote_gdb_command(
                    port=startup_port,
                    gdb_command_file=args.output / "attach.gdb",
                    gdb_command=args.gdb,
                    connect_timeout=args.gdb_connect_timeout,
                )
                winedbg_process = launch_winedbg_gdb_proxy(
                    launch_command,
                    log_path=winedbg_log,
                    workdir=Path(manifest["executable"]["path"]).parent,
                )
            except Exception as exc:
                print(json.dumps({
                    **result,
                    "status": "blocked",
                    "ready": False,
                    "error": f"{type(exc).__name__}: {exc}",
                }, ensure_ascii=False, indent=2))
                return 2
            result["winedbg_launch_command"] = launch_command
            result["remote_gdb_command"] = command
            result["winedbg_port"] = startup_port
            result["winedbg_log"] = str(winedbg_log)
            result["status"] = "launching-under-winedbg"
        else:
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
        try:
            gdb_returncode = subprocess.call(command)
        finally:
            if winedbg_process is not None:
                winedbg_returncode = finish_winedbg_gdb_proxy(
                    winedbg_process
                )

        if args.provider_only:
            if args.launch_under_winedbg:
                return (
                    0
                    if gdb_returncode == 0 and winedbg_returncode == 0
                    else 2
                )
            return gdb_returncode

        try:
            timeline = finalize_relation_state_mutation_capture(
                args.output
            )
        except Exception as exc:
            final = {
                **result,
                "status": "blocked",
                "ready": False,
                "gdb_returncode": gdb_returncode,
                "post_capture": {
                    "automatic_timeline_correlation": True,
                    "timeline_output": str(
                        (args.output / TIMELINE_OUTPUT_NAME).resolve()
                    ),
                    "ready": False,
                    "error": f"{type(exc).__name__}: {exc}",
                },
            }
            print(json.dumps(final, ensure_ascii=False, indent=2))
            return 2

        try:
            evidence_bundle = build_sdf_runtime_probe_evidence_bundle(
                args.output
            )
        except Exception as exc:
            final = {
                **result,
                "status": "blocked",
                "ready": False,
                "gdb_returncode": gdb_returncode,
                "post_capture": {
                    "automatic_timeline_correlation": True,
                    "timeline_output": str(
                        (args.output / TIMELINE_OUTPUT_NAME).resolve()
                    ),
                    "ready": bool(timeline["ready"]),
                    "mutation_event_count": timeline[
                        "mutation_event_count"
                    ],
                    "timeline_anchor_count": timeline[
                        "timeline_anchor_count"
                    ],
                    "summary": timeline["summary"],
                    "errors": timeline["errors"],
                    "automatic_evidence_bundle": True,
                    "evidence_bundle_ready": False,
                    "evidence_bundle_error": (
                        f"{type(exc).__name__}: {exc}"
                    ),
                },
            }
            print(json.dumps(final, ensure_ascii=False, indent=2))
            return 2

        evidence_bundle_verification = (
            verify_sdf_runtime_probe_evidence_bundle(
                evidence_bundle["archive"]["path"]
            )
        )

        evidence_bundle_replay = (
            replay_sdf_runtime_probe_evidence_bundle(
                evidence_bundle["archive"]["path"]
            )
        )

        final_ready = (
            gdb_returncode == 0
            and winedbg_returncode in (None, 0)
            and bool(timeline["ready"])
            and bool(evidence_bundle["ready"])
            and bool(evidence_bundle_verification["ready"])
            and bool(evidence_bundle_replay["ready"])
        )
        final = {
            **result,
            "status": "completed" if final_ready else "blocked",
            "ready": final_ready,
            "gdb_returncode": gdb_returncode,
            "winedbg_returncode": winedbg_returncode,
            "post_capture": {
                "automatic_timeline_correlation": True,
                "timeline_output": str(
                    (args.output / TIMELINE_OUTPUT_NAME).resolve()
                ),
                "ready": bool(timeline["ready"]),
                "mutation_event_count": timeline[
                    "mutation_event_count"
                ],
                "timeline_anchor_count": timeline[
                    "timeline_anchor_count"
                ],
                "summary": timeline["summary"],
                "errors": timeline["errors"],
                "automatic_evidence_bundle": True,
                "evidence_bundle_ready": bool(
                    evidence_bundle["ready"]
                ),
                "evidence_bundle_capture_ready": bool(
                    evidence_bundle["capture_ready"]
                ),
                "evidence_bundle_file_count": evidence_bundle[
                    "file_count"
                ],
                "evidence_bundle_archive": evidence_bundle["archive"],
                "evidence_bundle_errors": evidence_bundle["errors"],
                "evidence_bundle_verified": True,
                "evidence_bundle_verification_ready": bool(
                    evidence_bundle_verification["ready"]
                ),
                "evidence_bundle_evidence_ready": bool(
                    evidence_bundle_verification["evidence_ready"]
                ),
                "evidence_bundle_verification_errors": (
                    evidence_bundle_verification["errors"]
                ),
                "evidence_bundle_replay_ready": bool(
                    evidence_bundle_replay["ready"]
                ),
                "evidence_bundle_replay_timeline_match": bool(
                    evidence_bundle_replay["timeline_match"]
                ),
                "evidence_bundle_replay_evidence_ready": bool(
                    evidence_bundle_replay["evidence_ready"]
                ),
                "evidence_bundle_replay_errors": (
                    evidence_bundle_replay["errors"]
                ),
                "evidence_bundle_recomputed_timeline_sha256": (
                    evidence_bundle_replay[
                        "recomputed_timeline_sha256"
                    ]
                ),
            },
        }
        print(json.dumps(final, ensure_ascii=False, indent=2))
        return 0 if final_ready else 2

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
