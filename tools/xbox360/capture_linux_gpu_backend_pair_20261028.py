#!/usr/bin/env python3
"""Run event-aligned Xenos and Native Vulkan captures with frozen inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HOST = Path("/home/pes/work/nfsshift-rex-lwsync-20261027/out/build/linux-amd64-release/nfs_shift")
RUNTIME = Path("/home/pes/work/rexglue-sdk-retail-lwsync-20261027/out/linux-amd64/Release/librexruntime.so")
GAME_DATA = Path("/home/pes/work/process2-retail-isolated-irq-20261023/game-data")
XENOS_PLUGIN = Path("/home/pes/work/rexglue-sdk-retail-lwsync-20261027/out/linux-amd64/librexgpu-xenos.so")
VULKAN_PLUGIN = Path(os.environ.get(
    "SHIFT_P1_NATIVE_PLUGIN",
    "/home/pes/work/.build-process2-p2161-vulkan-plugin-20261027/output/librexgpu-shift-native.so",
))
CAPTURE_RUNNER = ROOT / "tools/xbox360/capture_linux_post_bink_worker_route_v45_ordered_route_20261027.py"
COMPARATOR = ROOT / "tools/xbox360/compare_linux_gpu_backend_runs_20261028.py"

EXPECTED = {
    "host": "ff4278b3df0957d31870c933a001e2d8df4d7ced2149053f773c7fdb39087178",
    "runtime": "693abc4814fe04a8025e41be989ac14faa31565b2786e1397f87ad9544d601cd",
    "xex": "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58",
    "xenos_plugin": "19053b691d7d1f8f17bbe3e90be38ba3acc60439cbe5c1dfcad271e07b47ce43",
    "shift_native_plugin": os.environ.get(
        "SHIFT_P1_NATIVE_PLUGIN_SHA256",
        "22ad3949e35c2d9db11540fc6563e895a8bc2d03f6d1166eb1979222ffb87dac",
    ),
}
P2_SOURCE_COMMIT = os.environ.get(
    "SHIFT_P1_P2_SOURCE_COMMIT", "5465723cb82cccd1f6e9951b126e6dcb2399b4a0"
)
P2_PLUGIN_BUILD_ID = os.environ.get(
    "SHIFT_P1_P2_PLUGIN_BUILD_ID", "baeac82aa4c84011ad3c536bbbde2e3add78d0b1"
)
P2_SDK_PROVIDER_COMMIT = os.environ.get("SHIFT_P1_P2_SDK_PROVIDER_COMMIT", "")
P2_SOURCE_DIFF_SHA256 = os.environ.get("SHIFT_P1_P2_SOURCE_DIFF_SHA256", "")
P2_SOURCE_STATUS_SHA256 = os.environ.get("SHIFT_P1_P2_SOURCE_STATUS_SHA256", "")
P2_SOURCE_DIRTY = os.environ.get("SHIFT_P1_P2_SOURCE_DIRTY", "1") == "1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_head(path: Path) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def git_status_hash(path: Path) -> tuple[bool, str | None]:
    result = subprocess.run(
        ["git", "-C", str(path), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return True, None
    status = result.stdout.encode("utf-8")
    return bool(status), hashlib.sha256(status).hexdigest()


def resource_manifest(root: Path) -> tuple[str, list[dict[str, object]]]:
    records: list[dict[str, object]] = []
    digest = hashlib.sha256()
    files = sorted(path for path in root.rglob("*") if path.is_file())
    for index, path in enumerate(files, 1):
        relative = path.relative_to(root).as_posix()
        stat = path.stat()
        size = stat.st_size
        modified_ns = stat.st_mtime_ns
        records.append({"path": relative, "size": size, "mtime_ns": modified_ns})
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(size).encode("ascii"))
        digest.update(b"\0")
        digest.update(str(modified_ns).encode("ascii"))
        digest.update(b"\n")
        if index % 256 == 0:
            print(f"resource manifest: {index}/{len(files)} files", flush=True)
    return digest.hexdigest(), records


def snapshot(source: Path, target: Path, expected_hash: str) -> str:
    if not source.is_file():
        raise SystemExit(f"missing input artifact: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    actual = sha256(target)
    if actual != expected_hash:
        raise SystemExit(f"artifact hash mismatch for {source}: expected={expected_hash} actual={actual}")
    return actual


def run_capture(
    *, output: Path, backend: str, plugin: Path, plugin_hash: str,
    resource_hash: str, duration: float, p2_commit: str | None,
    native_draw_frame: int, input_trigger: str, input_trigger_delay_seconds: float,
    input_hold_ms: int, input_gap_ms: int, trace_event_write_shd: bool,
) -> None:
    env = os.environ.copy()
    env.update({
        "SHIFT_QUEUE_TRACE_OUT": str(output),
        "SHIFT_QUEUE_TRACE_BINARY": str(HOST),
        "SHIFT_QUEUE_TRACE_RUNTIME": str(RUNTIME),
        "SHIFT_QUEUE_TRACE_PLUGIN": str(plugin),
        "SHIFT_QUEUE_TRACE_GAME_DATA_ROOT": str(GAME_DATA),
        "SHIFT_QUEUE_TRACE_GPU_PLUGIN_NAME": backend,
        "SHIFT_QUEUE_TRACE_EXPECT_PLUGIN_SHA256": plugin_hash,
        "SHIFT_QUEUE_TRACE_RESOURCE_MANIFEST_SHA256": resource_hash,
        "SHIFT_QUEUE_TRACE_INPUT_REPLAY": "1",
        "SHIFT_QUEUE_TRACE_INPUT_TRIGGER": input_trigger,
        "SHIFT_QUEUE_TRACE_INPUT_DELAY_SECONDS": str(input_trigger_delay_seconds),
        "SHIFT_QUEUE_TRACE_INPUT_HOLD_MS": str(input_hold_ms),
        "SHIFT_QUEUE_TRACE_INPUT_GAP_MS": str(input_gap_ms),
        "SHIFT_QUEUE_TRACE_EVENT_WRITE_SHD": "1" if trace_event_write_shd else "0",
        "SHIFT_QUEUE_TRACE_DURATION_SECONDS": str(duration),
        "SHIFT_QUEUE_TRACE_P2_PLUGIN_BUILD_ID": P2_PLUGIN_BUILD_ID if backend == "shift-native" else "",
        "SHIFT_QUEUE_TRACE_P2_SOURCE_COMMIT": p2_commit or "",
        "SHIFT_QUEUE_TRACE_P2_SOURCE_STATE_NOTE": (
            f"frozen plugin artifact; source_dirty={P2_SOURCE_DIRTY}; "
            f"source_diff_sha256={P2_SOURCE_DIFF_SHA256 or 'unavailable'}"
            if backend == "shift-native" else ""
        ),
        "SHIFT_QUEUE_TRACE_P2_SOURCE_DIFF_SHA256": P2_SOURCE_DIFF_SHA256 if backend == "shift-native" else "",
        "SHIFT_QUEUE_TRACE_P2_SOURCE_STATUS_SHA256": P2_SOURCE_STATUS_SHA256 if backend == "shift-native" else "",
        "SHIFT_QUEUE_TRACE_P2_SOURCE_DIRTY": "1" if P2_SOURCE_DIRTY and backend == "shift-native" else "0",
        "SHIFT_NATIVE_VULKAN_TRACE_RING": "1" if backend == "shift-native" else "0",
        "REX_LOG_LEVEL": "info",
    })
    if backend == "shift-native" and native_draw_frame > 0:
        env["SHIFT_NATIVE_VULKAN_DUMP_DRAW_FRAME"] = str(native_draw_frame)
        env["SHIFT_NATIVE_VULKAN_DUMP_GEOMETRY_PREFIX"] = str(output / "native-draw")
        env["SHIFT_NATIVE_VULKAN_DUMP_SHADER_PREFIX"] = str(output / "native-shader")
    result = subprocess.run([sys.executable, str(CAPTURE_RUNNER)], cwd=ROOT, env=env, check=False)
    if result.returncode != 0 and not (output / "events.json").is_file():
        raise SystemExit(f"capture failed: backend={backend} output={output} exit={result.returncode}")
    if result.returncode != 0:
        print(
            f"capture recovered partial trace: backend={backend} output={output} exit={result.returncode}",
            flush=True,
        )


def capture_backends(native_only: bool) -> tuple[str, ...]:
    """Select the run set while keeping follow-up Native checks out of Xenos."""
    return ("shift-native",) if native_only else ("xenos", "shift-native")


def should_compare_capture(backend: str, native_only: bool) -> bool:
    return backend == "shift-native" and not native_only


def metadata_contract(native_only: bool) -> tuple[str, str]:
    if native_only:
        return "capture_metadata.json", "shift.xbox360.linux-gpu-backend-capture.v1"
    return "pair_metadata.json", "shift.xbox360.linux-gpu-backend-pair.v1"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("/tmp/nfs-shift-p1-gpu-backend-pair-20261028"),
    )
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--duration-seconds", type=float, default=135.0)
    parser.add_argument(
        "--native-only", action="store_true",
        help="capture Native Vulkan only (useful for checking a new renderer plugin)",
    )
    parser.add_argument(
        "--native-draw-frame", type=int, default=0,
        help="dump detailed Native draw/scissor/geometry for this submitted Vulkan frame",
    )
    parser.add_argument(
        "--input-trigger", choices=("scene_gate", "bink_complete"), default="scene_gate",
        help="start the same Start/A/Start pulse sequence at the scene gate or after Bink completion",
    )
    parser.add_argument("--input-trigger-delay-seconds", type=float, default=0.5)
    parser.add_argument("--input-hold-ms", type=int, default=3000)
    parser.add_argument("--input-gap-ms", type=int, default=3000)
    parser.add_argument(
        "--trace-event-write-shd", action="store_true",
        help="capture raw EVENT_WRITE_SHD packets targeting the retail software head",
    )
    args = parser.parse_args()
    out = args.output_root.expanduser().resolve()
    if out.exists():
        raise SystemExit(f"refusing to overwrite existing output: {out}")
    if args.repeats < 1:
        raise SystemExit("--repeats must be at least 1")
    if args.duration_seconds <= 0:
        raise SystemExit("--duration-seconds must be positive")
    if args.native_draw_frame < 0:
        raise SystemExit("--native-draw-frame cannot be negative")
    if args.input_trigger_delay_seconds < 0:
        raise SystemExit("--input-trigger-delay-seconds cannot be negative")
    if args.input_hold_ms <= 0:
        raise SystemExit("--input-hold-ms must be positive")
    if args.input_gap_ms < 0:
        raise SystemExit("--input-gap-ms cannot be negative")

    artifacts = out / "artifacts"
    artifacts.mkdir(parents=True)
    host_hash = sha256(HOST)
    runtime_hash = sha256(RUNTIME)
    xex_hash = sha256(GAME_DATA / "default.xex")
    if {"host": host_hash, "runtime": runtime_hash, "xex": xex_hash} != {
        key: EXPECTED[key] for key in ("host", "runtime", "xex")
    }:
        raise SystemExit("host, runtime, or XEX differs from the frozen comparison baseline")

    sdk_root = Path("/home/pes/work/rexglue-sdk-retail-lwsync-20261027")
    p1_commit = git_head(ROOT)
    sdk_commit = git_head(sdk_root)
    p1_dirty, p1_status_sha256 = git_status_hash(ROOT)
    xenos_snapshot = artifacts / "librexgpu-xenos.so"
    vulkan_snapshot = artifacts / "librexgpu-shift-native.so"
    xenos_hash = snapshot(XENOS_PLUGIN, xenos_snapshot, EXPECTED["xenos_plugin"])
    vulkan_hash = snapshot(VULKAN_PLUGIN, vulkan_snapshot, EXPECTED["shift_native_plugin"])

    print("building game-data path/size/mtime manifest", flush=True)
    resource_hash, resource_files = resource_manifest(GAME_DATA)
    (out / "resource_manifest.json").write_text(
        json.dumps({"root": str(GAME_DATA), "kind": "path-size-mtime", "sha256": resource_hash, "files": resource_files}, indent=2) + "\n",
        encoding="utf-8",
    )
    metadata_name, metadata_schema = metadata_contract(args.native_only)
    (out / metadata_name).write_text(json.dumps({
        "schema": metadata_schema,
        "capture_mode": "native-only" if args.native_only else "paired",
        "created_epoch_ms": int(time.time() * 1000),
        "host": {"path": str(HOST), "sha256": host_hash},
        "runtime": {"path": str(RUNTIME), "sha256": runtime_hash},
        "xex": {"path": str(GAME_DATA / "default.xex"), "sha256": xex_hash},
        "game_data": {"root": str(GAME_DATA), "file_count": len(resource_files), "manifest_kind": "path-size-mtime", "manifest_sha256": resource_hash},
        "sdk": {"root": str(sdk_root), "commit": sdk_commit},
        "p2_sdk_provider_source_commit": P2_SDK_PROVIDER_COMMIT or None,
        "p1_repository": {"root": str(ROOT), "commit": p1_commit},
        "p1_source_state": {"dirty": p1_dirty, "status_sha256": p1_status_sha256},
        "capture_runner_sha256": sha256(CAPTURE_RUNNER),
        "trace_script_sha256": sha256(ROOT / "tools/xbox360/trace_linux_post_bink_worker_route_v45_ordered_route_20261027.gdb"),
        "trace_options": {
            "queue_field_alias_probe": os.environ.get("SHIFT_QUEUE_TRACE_QUEUE_FIELD_ALIAS_PROBE", "") or None,
            "event_write_shd_packet_trace": args.trace_event_write_shd,
        },
        "comparator_sha256": sha256(COMPARATOR),
        "plugins": {
            "xenos": {"path": str(XENOS_PLUGIN), "snapshot": str(xenos_snapshot), "sha256": xenos_hash, "build_id": "cfa31cb1ea72cea5f153b76f29e4635536628ff4"},
            "shift-native": {
                "path": str(VULKAN_PLUGIN),
                "snapshot": str(vulkan_snapshot),
                "sha256": vulkan_hash,
                "build_id": P2_PLUGIN_BUILD_ID,
                "source_commit": P2_SOURCE_COMMIT,
                "source_dirty": P2_SOURCE_DIRTY,
                "source_diff_sha256": P2_SOURCE_DIFF_SHA256 or None,
                "source_status_sha256": P2_SOURCE_STATUS_SHA256 or None,
            },
        },
        "repeats": args.repeats,
        "duration_seconds_per_run": args.duration_seconds,
        "native_draw_diagnostic": {
            "selected_submitted_frame": args.native_draw_frame or None,
            "geometry_dump_prefix": "runs/shift-native-rN/native-draw" if args.native_draw_frame else None,
            "shader_dump_prefix": "runs/shift-native-rN/native-shader" if args.native_draw_frame else None,
            "requested": args.native_draw_frame > 0,
        },
        "input_profile": [
            {"button": "Start", "mask": "0x0010", "hold_ms": args.input_hold_ms},
            {"button": "A", "mask": "0x1000", "hold_ms": args.input_hold_ms},
            {"button": "Start", "mask": "0x0010", "hold_ms": args.input_hold_ms},
        ],
        "input_gap_ms": args.input_gap_ms,
        "input_gate": "first scene manager update after Bink clear with state_348=1 and update_count_356>=1",
        "input_trigger": args.input_trigger,
        "input_trigger_delay_seconds": args.input_trigger_delay_seconds if args.input_trigger == "bink_complete" else 0,
        "logging": {
            "rex_log_level": "info",
            "native_vulkan_ring_trace_requested": True,
        },
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    runner_hash = sha256(CAPTURE_RUNNER)
    plugin_by_backend = {
        "xenos": (xenos_snapshot, xenos_hash),
        "shift-native": (vulkan_snapshot, vulkan_hash),
    }
    for repetition in range(1, args.repeats + 1):
        for backend in capture_backends(args.native_only):
            plugin, plugin_hash = plugin_by_backend[backend]
            output = out / "runs" / f"{backend}-r{repetition}"
            output.parent.mkdir(parents=True, exist_ok=True)
            print(f"starting {backend} repetition {repetition}/{args.repeats}", flush=True)
            run_capture(
                output=output,
                backend=backend,
                plugin=plugin,
                plugin_hash=plugin_hash,
                resource_hash=resource_hash,
                duration=args.duration_seconds,
                p2_commit=P2_SOURCE_COMMIT if backend == "shift-native" else None,
                native_draw_frame=args.native_draw_frame if backend == "shift-native" else 0,
                input_trigger=args.input_trigger,
                input_trigger_delay_seconds=args.input_trigger_delay_seconds,
                input_hold_ms=args.input_hold_ms,
                input_gap_ms=args.input_gap_ms,
                trace_event_write_shd=args.trace_event_write_shd,
            )
            metadata_path = output / "run_metadata.json"
            events_path = output / "events.json"
            if not metadata_path.is_file() or not events_path.is_file():
                raise SystemExit(f"capture is missing output files: {output}")
            current_resource_hash, _ = resource_manifest(GAME_DATA)
            if current_resource_hash != resource_hash:
                raise SystemExit(f"game data path/size/mtime manifest changed during capture: {output}")
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            if metadata.get("schema") != "shift.xbox360.linux-gpu-backend-run.v1":
                raise SystemExit(f"unexpected run schema: {metadata.get('schema')}")
            if metadata.get("gpu_backend") != backend or metadata.get("plugin_sha256") != plugin_hash:
                raise SystemExit(f"capture artifact identity mismatch: {output}")
            controller_input = metadata.get("controller_input", {})
            if controller_input.get("trigger_observed") and len(controller_input.get("pulses", [])) != 3:
                raise SystemExit(f"expected all three input pulses after the selected trigger: {output}")
            if not controller_input.get("trigger_observed") and controller_input.get("pulses"):
                raise SystemExit(f"input pulses were sent without the selected trigger: {output}")
            if (args.input_trigger == "scene_gate" and controller_input.get("trigger_observed")
                    and not controller_input.get("gate_observed")):
                raise SystemExit(f"scene-gate input trigger was recorded without the scene gate: {output}")
            metadata["capture_runner_sha256"] = runner_hash
            metadata["resource_manifest_verified_after_capture"] = True
            if backend == "shift-native":
                metadata["p2_sdk_provider_source_commit"] = P2_SDK_PROVIDER_COMMIT or None
                metadata["native_draw_diagnostic"] = {
                    "selected_submitted_frame": args.native_draw_frame or None,
                    "geometry_dump_prefix": str(output / "native-draw") if args.native_draw_frame else None,
                    "shader_dump_prefix": str(output / "native-shader") if args.native_draw_frame else None,
                    "requested": args.native_draw_frame > 0,
                }
            metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")

            if should_compare_capture(backend, args.native_only):
                xenos_run = out / "runs" / f"xenos-r{repetition}"
                vulkan_run = out / "runs" / f"shift-native-r{repetition}"
                compare = subprocess.run(
                    [sys.executable, str(COMPARATOR), "compare", str(xenos_run), str(vulkan_run),
                     "--output", str(out / f"comparison-r{repetition}.json")],
                    cwd=ROOT,
                    check=False,
                )
                if compare.returncode != 0:
                    raise SystemExit(f"comparison failed for repetition {repetition}")

    mode = "Native-only capture" if args.native_only else "paired captures"
    print(f"{mode} complete: {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
