#!/usr/bin/env python3
"""Capture the retail WAIT_REG_MEM word writer with queue and GPU context."""

from __future__ import annotations

import os
import hashlib
import json
import re
import shutil
import signal
import subprocess
import time
from datetime import datetime
from pathlib import Path

try:
    from evdev import AbsInfo, UInput, ecodes
except ImportError:  # Input replay is optional for one-backend diagnostic runs.
    AbsInfo = UInput = ecodes = None


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(os.environ.get(
    "SHIFT_QUEUE_TRACE_OUT",
    "/dev/shm/nfs-shift-p1-post-bink-worker-route-v46-wait-word-watch-20261028",
))
HOST = Path(os.environ.get(
    "SHIFT_QUEUE_TRACE_BINARY",
    "/home/pes/work/nfsshift-rex-lwsync-20261027/out/build/linux-amd64-release/nfs_shift",
))
RUNTIME = Path(os.environ.get(
    "SHIFT_QUEUE_TRACE_RUNTIME",
    "/home/pes/work/rexglue-sdk-retail-lwsync-20261027/out/linux-amd64/Release/librexruntime.so",
))
PLUGIN = Path(os.environ.get(
    "SHIFT_QUEUE_TRACE_PLUGIN",
    "/dev/shm/nfs-shift-p1-worker-route-v45-latest-input/librexgpu-shift-native.so",
))
GPU_PLUGIN_NAME = os.environ.get("SHIFT_QUEUE_TRACE_GPU_PLUGIN_NAME", "shift-native")
SCRIPT = ROOT / "tools/xbox360/trace_linux_post_bink_worker_route_v46_wait_word_watch_20261028.gdb"
DATABUNDLE = Path(os.environ.get(
    "SHIFT_QUEUE_TRACE_GAME_DATA_ROOT",
    "/home/pes/work/process2-retail-isolated-irq-20261023/game-data",
))
DURATION = float(os.environ.get("SHIFT_QUEUE_TRACE_DURATION_SECONDS", "135"))
EXPECTED_HASHES = {
    "host": "ff4278b3df0957d31870c933a001e2d8df4d7ced2149053f773c7fdb39087178",
    "runtime": "693abc4814fe04a8025e41be989ac14faa31565b2786e1397f87ad9544d601cd",
    "plugin": "a0026207902f5fd3a0578138d0c0edd8875cecbd98119d33b26a65a4382b5ccf",
    "xex": "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58",
}
EXPECTED_HASHES["plugin"] = os.environ.get(
    "SHIFT_QUEUE_TRACE_EXPECT_PLUGIN_SHA256", EXPECTED_HASHES["plugin"]
)
P2_PLUGIN_BUILD_ID = os.environ.get(
    "SHIFT_QUEUE_TRACE_P2_PLUGIN_BUILD_ID", "e1e9bfa7bf4960893d9ee24f2e06a60af13fcfc0"
)
P2_SOURCE_COMMIT = os.environ.get(
    "SHIFT_QUEUE_TRACE_P2_SOURCE_COMMIT", "903639d023f617c4b15df9fcfb63c2c8dcf3c7ee"
)
P2_SOURCE_STATE_NOTE = os.environ.get(
    "SHIFT_QUEUE_TRACE_P2_SOURCE_STATE_NOTE",
    "P2-reported uncommitted ordered-stream route changes built on this base",
)
P2_SOURCE_DIFF_SHA256 = os.environ.get("SHIFT_QUEUE_TRACE_P2_SOURCE_DIFF_SHA256")
P2_SOURCE_STATUS_SHA256 = os.environ.get("SHIFT_QUEUE_TRACE_P2_SOURCE_STATUS_SHA256")
P2_SOURCE_DIRTY = os.environ.get("SHIFT_QUEUE_TRACE_P2_SOURCE_DIRTY", "0") == "1"
INPUT_REPLAY = os.environ.get("SHIFT_QUEUE_TRACE_INPUT_REPLAY", "0") == "1"
INPUT_GATE_MARKER = "GPU_COMPARE_INPUT_GATE"
BINK_INPUT_TRIGGER = "bink_complete"
INPUT_TRIGGER = os.environ.get("SHIFT_QUEUE_TRACE_INPUT_TRIGGER", "scene_gate")
INPUT_TRIGGER_DELAY_SECONDS = float(os.environ.get("SHIFT_QUEUE_TRACE_INPUT_DELAY_SECONDS", "0.5"))
INPUT_HOLD_MS = int(os.environ.get("SHIFT_QUEUE_TRACE_INPUT_HOLD_MS", "3000"))
INPUT_GAP_MS = int(os.environ.get("SHIFT_QUEUE_TRACE_INPUT_GAP_MS", "3000"))
RING_INTERRUPT_PATTERN = re.compile(
    r"ring trace PM4_INTERRUPT #(\d+) source=(\d+) generation=(\d+) "
    r"batch_rptr=(\d+) batch_wptr=(\d+) ring_guest=([0-9A-Fa-f]+) "
    r"packet=(\d+) packet_source=([0-9A-Fa-f]+)\+(\d+) "
    r"cpu_mask=0x([0-9A-Fa-f]+) dispatched_cpu_mask=0x([0-9A-Fa-f]+) "
    r"callback_dispatches=\[(.*?)\]"
)
RING_CALLBACK_PATTERN = re.compile(
    r"cpu(\d+):callback=0x([0-9A-Fa-f]+),data=0x([0-9A-Fa-f]+),status=([^,\]]+)"
)
RING_TIMESTAMP_PATTERN = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\]")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def xenia_memory_names(shared_dir: Path = Path("/dev/shm")) -> set[str]:
    if not shared_dir.is_dir():
        return set()
    return {
        path.name for path in shared_dir.glob("xenia_memory_*")
        if path.is_file() and re.fullmatch(r"xenia_memory_\d+", path.name)
    }


def cleanup_orphaned_xenia_memory(
    names_before: set[str], *, shared_dir: Path = Path("/dev/shm"),
    proc_root: Path = Path("/proc"),
) -> dict[str, list[str]]:
    """Remove only new Xenia shared-memory backing files with no open process fd."""
    open_targets = set()
    for process in proc_root.glob("[0-9]*"):
        try:
            descriptors = (process / "fd").iterdir()
            for descriptor in descriptors:
                try:
                    target = os.readlink(descriptor).removesuffix(" (deleted)")
                except OSError:
                    continue
                open_targets.add(os.path.abspath(target))
        except OSError:
            continue

    removed = []
    retained_open = []
    for name in sorted(xenia_memory_names(shared_dir) - names_before):
        path = shared_dir / name
        if os.path.abspath(path) in open_targets:
            retained_open.append(name)
            continue
        try:
            path.unlink()
            removed.append(name)
        except OSError:
            retained_open.append(name)
    return {"removed": removed, "retained_open_or_unlink_failed": retained_open}


def bink_complete_elapsed(log_text: str) -> float | None:
    marker = "WORKER_RING_BINK "
    for line in log_text.splitlines():
        position = line.find(marker)
        if position < 0:
            continue
        try:
            value = json.loads(line[position + len(marker):]).get("elapsed_seconds")
        except (json.JSONDecodeError, AttributeError):
            continue
        if isinstance(value, (int, float)):
            return float(value)
    return None


def bink_complete_wall_clock_epoch_ms(log_text: str) -> int | None:
    marker = "WORKER_RING "
    for line in log_text.splitlines():
        position = line.find(marker)
        if position < 0:
            continue
        try:
            event = json.loads(line[position + len(marker):])
        except json.JSONDecodeError:
            continue
        value = event.get("wall_clock_epoch_ms")
        if event.get("kind") == "bink_complete" and isinstance(value, int):
            return value
    return None


def input_trigger_ready(
    log_text: str, trigger: str, elapsed_seconds: float, delay_seconds: float,
    now_wall_clock_epoch_ms: int | None = None,
) -> bool:
    if trigger == "scene_gate":
        return INPUT_GATE_MARKER in log_text
    if trigger == BINK_INPUT_TRIGGER:
        completed_wall_clock = bink_complete_wall_clock_epoch_ms(log_text)
        if completed_wall_clock is not None and now_wall_clock_epoch_ms is not None:
            return now_wall_clock_epoch_ms >= completed_wall_clock + delay_seconds * 1000
        completed = bink_complete_elapsed(log_text)
        return completed is not None and elapsed_seconds >= completed + delay_seconds
    raise ValueError(f"unsupported controller input trigger: {trigger}")


def parse_ring_interrupt_log(path: Path) -> tuple[list[dict], int]:
    if not path.is_file():
        return [], 0
    records = []
    malformed = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        marker = "ring trace PM4_INTERRUPT #"
        if marker not in line:
            continue
        match = RING_INTERRUPT_PATTERN.search(line)
        if not match:
            malformed += 1
            continue
        timestamp_match = RING_TIMESTAMP_PATTERN.search(line)
        if not timestamp_match:
            malformed += 1
            continue
        timestamp_epoch_ms = round(
            datetime.strptime(timestamp_match.group(1), "%Y-%m-%d %H:%M:%S.%f")
            .astimezone()
            .timestamp() * 1000
        )
        (
            ordinal, source, generation, batch_rptr, batch_wptr, ring_guest,
            packet, packet_source, packet_offset, cpu_mask, dispatched_cpu_mask,
            callback_text,
        ) = match.groups()
        callbacks = [
            {
                "cpu": int(cpu),
                "callback": int(callback, 16),
                "data": int(data, 16),
                "status": status,
            }
            for cpu, callback, data, status in RING_CALLBACK_PATTERN.findall(callback_text)
        ]
        records.append({
            "ordinal": int(ordinal),
            "timestamp_epoch_ms": timestamp_epoch_ms,
            "source": int(source),
            "generation": int(generation),
            "batch_rptr": int(batch_rptr),
            "batch_wptr": int(batch_wptr),
            "ring_guest": int(ring_guest, 16),
            "packet_ordinal": int(packet),
            "source_ib": int(packet_source, 16),
            "source_ib_byte_offset": int(packet_offset),
            "cpu_mask": int(cpu_mask, 16),
            "dispatched_cpu_mask": int(dispatched_cpu_mask, 16),
            "callbacks": callbacks,
        })
    return records, malformed


TRACE_EVENT_KEYS = (
    "enqueue_events", "dequeue_events", "completion_events", "producer_events",
    "producer_call_events", "submission_route_events", "source1_callback_events",
    "event_call_events", "counter_write_events", "worker72_write_events",
    "controller_update_events", "controller_return_events", "host_input_events",
    "xam_input_events", "xam_input_return_events", "bink_complete_events",
    "input_gate_events", "scene_function_events", "scene_function_return_events",
    "scene_state_events", "retail_queue_wait_events",
    "retail_queue_wait_return_events", "queue_field_write_events",
    "ke_wait_return_events", "event_write_shd_packet_events",
)


def recover_trace_events_from_log(path: Path, backend: str) -> dict | None:
    """Recover breakpoint events if GDB is interrupted before its JSON finalizer."""
    events = {key: [] for key in TRACE_EVENT_KEYS}
    mapped_hashes = {}
    worker_queues = set()
    stop_diagnostics = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("WORKER_RING_STOP_DIAGNOSTICS "):
            try:
                stop_diagnostics = json.loads(line.split(" ", 1)[1])
            except json.JSONDecodeError:
                pass
            continue
        if line.startswith("WORKER_RING_MAPPED path="):
            match = re.match(r"WORKER_RING_MAPPED path=(.+) sha256=([0-9a-f]{64})$", line)
            if match:
                mapped_hashes[match.group(1)] = match.group(2)
            continue
        if line.startswith("WORKER_RING_WORKER_LOOP queue="):
            match = re.match(r"WORKER_RING_WORKER_LOOP queue=(0x[0-9a-fA-F]+)", line)
            if match:
                worker_queues.add(int(match.group(1), 16))
            continue
        packet_marker = "WORKER_RING_EVENT_WRITE_SHD "
        if line.startswith(packet_marker):
            try:
                events["event_write_shd_packet_events"].append(
                    json.loads(line[len(packet_marker):])
                )
            except json.JSONDecodeError:
                pass
            continue
        marker = "WORKER_RING "
        if marker not in line:
            continue
        try:
            record = json.loads(line.split(marker, 1)[1])
        except json.JSONDecodeError:
            continue
        kind = record.get("kind")
        key = f"{kind}_events" if isinstance(kind, str) else ""
        if key in events:
            events[key].append(record)
    if not any(events.values()):
        return None
    bink = next((row for row in events["bink_complete_events"]), None)
    input_gate = bool(events["input_gate_events"])
    manager = next((row.get("manager") for group in events.values() for row in group
                    if isinstance(row.get("manager"), int)), None)
    xam_calls = max((row.get("call", 0) for row in events["xam_input_events"]), default=0)
    return {
        "schema": "shift.xbox360.linux-gpu-backend-events.v1",
        "gpu_backend": backend,
        "partial_capture": True,
        "capture_finalizer_completed": False,
        "recovery_source": "runner.log WORKER_RING records",
        "bink_target": ({key: value for key, value in bink.items() if key != "kind"} if bink else None),
        "manager": manager,
        "worker_queues": sorted(worker_queues),
        "final_queue_snapshots": [],
        "final_scene_state": None,
        "producer_calls": max((row.get("producer_call", 0) for row in events["producer_call_events"]), default=0),
        "xam_input_calls": xam_calls,
        "controller_update_call_counts": {},
        "input_gate_emitted": input_gate,
        "stop_context": (
            {"partial_log_recovery": True, "diagnostics": stop_diagnostics}
            if stop_diagnostics is not None else {"partial_log_recovery": True}
        ),
        "counts": {key: len(events[key]) for key in TRACE_EVENT_KEYS},
        "event_write_shd_packet_events": events["event_write_shd_packet_events"],
        "mapped_hashes": mapped_hashes,
        "events": events,
    }


def exported_symbol_offset(path: Path, name_fragment: str) -> int:
    result = subprocess.run(
        ["nm", "-D", "--defined-only", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    matches = []
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) >= 3 and name_fragment in fields[-1]:
            try:
                matches.append((int(fields[0], 16), fields[-1]))
            except ValueError:
                continue
    if len(matches) != 1:
        raise SystemExit(f"expected one exported symbol containing {name_fragment!r}, found {matches}")
    return matches[0][0]


def make_virtual_gamepad():
    if UInput is None:
        raise SystemExit("evdev is required when SHIFT_QUEUE_TRACE_INPUT_REPLAY=1")
    axes = {
        ecodes.ABS_X: AbsInfo(0, -32768, 32767, 0, 0, 16),
        ecodes.ABS_Y: AbsInfo(0, -32768, 32767, 0, 0, 16),
        ecodes.ABS_RX: AbsInfo(0, -32768, 32767, 0, 0, 16),
        ecodes.ABS_RY: AbsInfo(0, -32768, 32767, 0, 0, 16),
        ecodes.ABS_Z: AbsInfo(0, 0, 255, 0, 0, 0),
        ecodes.ABS_RZ: AbsInfo(0, 0, 255, 0, 0, 0),
        ecodes.ABS_HAT0X: AbsInfo(0, -1, 1, 0, 0, 0),
        ecodes.ABS_HAT0Y: AbsInfo(0, -1, 1, 0, 0, 0),
    }
    keys = [
        ecodes.BTN_SOUTH, ecodes.BTN_EAST, ecodes.BTN_NORTH, ecodes.BTN_WEST,
        ecodes.BTN_TL, ecodes.BTN_TR, ecodes.BTN_SELECT, ecodes.BTN_START,
        ecodes.BTN_THUMBL, ecodes.BTN_THUMBR,
    ]
    return UInput(
        {ecodes.EV_KEY: keys, ecodes.EV_ABS: [(code, info) for code, info in axes.items()]},
        name="Microsoft X-Box 360 pad",
        bustype=ecodes.BUS_USB,
        vendor=0x045E,
        product=0x028E,
        version=0x0114,
    )


def emit_button(device, code: int, label: str, down: bool, pulse: dict) -> None:
    device.write(ecodes.EV_KEY, code, 1 if down else 0)
    device.syn()
    pulse["down_epoch_ms" if down else "up_epoch_ms"] = int(time.time() * 1000)


def main() -> int:
    if OUT.exists():
        raise SystemExit(f"refusing to overwrite existing capture: {OUT}")
    if not GPU_PLUGIN_NAME.replace("-", "").isalnum():
        raise SystemExit(f"invalid GPU plugin name: {GPU_PLUGIN_NAME!r}")
    if INPUT_TRIGGER not in ("scene_gate", BINK_INPUT_TRIGGER):
        raise SystemExit(f"invalid controller input trigger: {INPUT_TRIGGER!r}")
    if INPUT_HOLD_MS <= 0 or INPUT_GAP_MS < 0:
        raise SystemExit("controller input hold must be positive and gap cannot be negative")
    if not HOST.is_file() or not RUNTIME.is_file() or not PLUGIN.is_file():
        raise SystemExit(f"missing trace input: host={HOST} runtime={RUNTIME} plugin={PLUGIN}")
    xex = DATABUNDLE / "default.xex"
    actual_hashes = {
        "host": sha256(HOST),
        "runtime": sha256(RUNTIME),
        "plugin": sha256(PLUGIN),
        "xex": sha256(xex),
    }
    if actual_hashes != EXPECTED_HASHES:
        raise SystemExit(f"exact capture identity mismatch: {actual_hashes}")
    out_bin = OUT / "bin"
    out_bin.mkdir(parents=True, exist_ok=True)
    staged_host = out_bin / "nfs_shift"
    shutil.copy2(HOST, staged_host)
    plugin_filename = f"librexgpu-{GPU_PLUGIN_NAME}.so"
    for name, source in (("librexruntime.so", RUNTIME), (plugin_filename, PLUGIN)):
        shutil.copy2(source, out_bin / name)

    env = os.environ.copy()
    env["SHIFT_QUEUE_TRACE_OUT"] = str(OUT)
    env["SHIFT_QUEUE_TRACE_GPU_PLUGIN_NAME"] = GPU_PLUGIN_NAME
    env["SHIFT_QUEUE_TRACE_INPUT_REPLAY"] = "1" if INPUT_REPLAY else "0"
    env["SDL_GAMECONTROLLER_IGNORE_DEVICES"] = "0x045e/0x0b12"
    input_symbols = None
    if INPUT_REPLAY:
        input_symbols = {
            "input_system_get_state_offset": exported_symbol_offset(RUNTIME, "InputSystem8GetStateEjP"),
            "xam_input_get_state_offset": exported_symbol_offset(
                RUNTIME, "_ZN3rex6kernel3xam22XamInputGetState_entry"
            ),
        }
        env["SHIFT_QUEUE_TRACE_INPUT_GET_STATE_OFFSET"] = hex(
            input_symbols["input_system_get_state_offset"]
        )
        env["SHIFT_QUEUE_TRACE_XAM_INPUT_OFFSET"] = hex(
            input_symbols["xam_input_get_state_offset"]
        )
    runner_log = OUT / "runner.log"
    controller_input = {
        "enabled": INPUT_REPLAY,
        "trigger": INPUT_TRIGGER,
        "trigger_delay_seconds": INPUT_TRIGGER_DELAY_SECONDS if INPUT_TRIGGER == BINK_INPUT_TRIGGER else 0,
        "hold_ms": INPUT_HOLD_MS,
        "gap_ms": INPUT_GAP_MS,
        "trigger_observed": False,
        "gate": "first scene manager update after Bink clear with state_348=1 and update_count_356>=1",
        "gate_observed": False,
        "pulses": [],
    }
    gamepad = make_virtual_gamepad() if INPUT_REPLAY else None
    xenia_memory_names_before = xenia_memory_names()
    with runner_log.open("w", encoding="utf-8") as output:
        started = time.monotonic()
        started_wall_clock_epoch_ms = int(time.time() * 1000)
        process = subprocess.Popen(
            ["gdb", "-q", "-batch", "-ex", f"file {staged_host}", "-x", str(SCRIPT)],
            stdout=output,
            stderr=subprocess.STDOUT,
            env=env,
        )
        print(f"gdb_pid={process.pid} host={HOST} runtime={RUNTIME} plugin={PLUGIN} duration={DURATION}s", flush=True)
        deadline = started + DURATION
        input_sequence_sent = False
        while process.poll() is None and time.monotonic() < deadline:
            if INPUT_REPLAY and not input_sequence_sent:
                try:
                    current_log = runner_log.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    current_log = ""
                elapsed = time.monotonic() - started
                now_wall_clock_epoch_ms = int(time.time() * 1000)
                if input_trigger_ready(
                    current_log, INPUT_TRIGGER, elapsed, INPUT_TRIGGER_DELAY_SECONDS,
                    now_wall_clock_epoch_ms,
                ):
                    input_sequence_sent = True
                    controller_input["trigger_observed"] = True
                    controller_input["trigger_elapsed_seconds"] = round(elapsed, 3)
                    controller_input["trigger_wall_clock_epoch_ms"] = now_wall_clock_epoch_ms
                    bink_wall_clock_epoch_ms = bink_complete_wall_clock_epoch_ms(current_log)
                    if bink_wall_clock_epoch_ms is not None:
                        controller_input["observed_bink_to_input_delay_seconds"] = round(
                            (now_wall_clock_epoch_ms - bink_wall_clock_epoch_ms) / 1000,
                            3,
                        )
                    controller_input["gate_observed"] = INPUT_GATE_MARKER in current_log
                    if controller_input["gate_observed"]:
                        controller_input["gate_elapsed_seconds"] = round(elapsed, 3)
                    print(
                        f"controller input trigger={INPUT_TRIGGER} gate_observed={controller_input['gate_observed']} "
                        f"after {elapsed:.3f}s",
                        file=output, flush=True,
                    )
                    for index, (code, label, mask) in enumerate((
                        (ecodes.BTN_START, "Start", "0x0010"),
                        (ecodes.BTN_SOUTH, "A", "0x1000"),
                        (ecodes.BTN_START, "Start", "0x0010"),
                    )):
                        pulse = {"index": index, "button": label, "expected_mask": mask}
                        controller_input["pulses"].append(pulse)
                        emit_button(gamepad, code, label, True, pulse)
                        print(f"controller {label} down at {time.monotonic() - started:.3f}s", file=output, flush=True)
                        time.sleep(INPUT_HOLD_MS / 1000)
                        emit_button(gamepad, code, label, False, pulse)
                        print(f"controller {label} up at {time.monotonic() - started:.3f}s", file=output, flush=True)
                        if index != 2:
                            time.sleep(INPUT_GAP_MS / 1000)
            time.sleep(0.25)
        if process.poll() is None:
            process.send_signal(signal.SIGINT)
            print("sent SIGINT to GDB at bounded trace deadline", file=output, flush=True)
        try:
            result = process.wait(timeout=150)
        except subprocess.TimeoutExpired:
            process.kill()
            result = process.wait(timeout=10)
        elapsed = time.monotonic() - started
        ended_wall_clock_epoch_ms = int(time.time() * 1000)
        print(f"gdb_exit={result} elapsed={elapsed:.3f}s", file=output, flush=True)
    if gamepad is not None:
        gamepad.close()
    memory_mapping_cleanup = {"removed": [], "retained_open_or_unlink_failed": []}
    for attempt in range(20):
        memory_mapping_cleanup = cleanup_orphaned_xenia_memory(xenia_memory_names_before)
        if not memory_mapping_cleanup["retained_open_or_unlink_failed"]:
            break
        if attempt < 19:
            time.sleep(0.1)
    if memory_mapping_cleanup["removed"]:
        print(
            "removed orphaned runtime memory mappings: "
            + ", ".join(memory_mapping_cleanup["removed"]),
            flush=True,
        )
    if memory_mapping_cleanup["retained_open_or_unlink_failed"]:
        print(
            "runtime memory mappings still have open holders after cleanup retries: "
            + ", ".join(memory_mapping_cleanup["retained_open_or_unlink_failed"]),
            flush=True,
        )
    ring_trace_requested = (
        GPU_PLUGIN_NAME == "shift-native"
        and os.environ.get("SHIFT_NATIVE_VULKAN_TRACE_RING") == "1"
    )
    ring_records = []
    ring_malformed_records = 0
    ring_seen = set()
    log_paths = [runner_log, OUT / "gdb.log"]
    log_paths.extend(sorted((OUT / "bin" / "logs").rglob("*.log")))
    for log_path in log_paths:
        parsed, malformed = parse_ring_interrupt_log(log_path)
        ring_malformed_records += malformed
        for record in parsed:
            identity = (record["ordinal"], record["source_ib"], record["source_ib_byte_offset"])
            if identity not in ring_seen:
                ring_seen.add(identity)
                ring_records.append(record)
    events_path = OUT / "events.json"
    recovered_trace_events = False
    if not events_path.is_file():
        recovered = recover_trace_events_from_log(runner_log, GPU_PLUGIN_NAME)
        if recovered:
            recovered["gpu_ring_interrupt_events"] = ring_records
            events_path.write_text(json.dumps(recovered, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            recovered_trace_events = True
            print("recovered partial guest trace from runner.log", flush=True)
    if events_path.is_file() and not recovered_trace_events:
        event_data = json.loads(events_path.read_text(encoding="utf-8"))
        event_data["gpu_ring_interrupt_events"] = ring_records
        events_path.write_text(json.dumps(event_data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    generated_root = Path("/home/pes/work/nfsshift-rex-lwsync-20261027/generated/default")
    generated_hashes = {}
    for name in (
        "nfs_shift_recomp.115.cpp",
        "nfs_shift_recomp.127.cpp",
        "nfs_shift_recomp.139.cpp",
        "nfs_shift_recomp.159.cpp",
        "nfs_shift_recomp.190.cpp",
    ):
        source = generated_root / name
        if source.is_file():
            generated_hashes[str(source)] = hashlib.sha256(source.read_bytes()).hexdigest()
    ring_trace_logs = [
        {
            "path": str(path.relative_to(OUT)),
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in sorted((OUT / "bin" / "logs").rglob("*.log"))
    ] if ring_trace_requested else []
    runtime_hash = sha256(RUNTIME)
    plugin_hash = sha256(PLUGIN)
    host_hash = sha256(staged_host)
    metadata = {
        "schema": "shift.xbox360.linux-gpu-backend-run.v1",
        "gpu_backend": GPU_PLUGIN_NAME,
        "controller_input": controller_input,
        "input_probe_symbols": input_symbols,
        "duration_seconds": round(elapsed, 3),
        "orphaned_xenia_memory_cleanup": memory_mapping_cleanup,
        "wall_clock_start_epoch_ms": started_wall_clock_epoch_ms,
        "wall_clock_end_epoch_ms": ended_wall_clock_epoch_ms,
        "gdb_exit": result,
        "event_capture_status": "partial_log_recovery" if recovered_trace_events else "gdb_json_finalizer",
        "guest_memory_modified_by_probe": False,
        "xex_path": str(xex),
        "xex_sha256": sha256(xex),
        "game_data_root": str(DATABUNDLE),
        "resource_manifest_sha256": os.environ.get("SHIFT_QUEUE_TRACE_RESOURCE_MANIFEST_SHA256"),
        "resource_manifest_kind": "path-size-mtime",
        "host_path": str(HOST),
        "host_sha256": host_hash,
        "staged_host_path": str(staged_host),
        "staged_host_sha256": sha256(staged_host),
        "runtime_path": str(RUNTIME),
        "runtime_sha256": runtime_hash,
        "plugin_path": str(PLUGIN),
        "plugin_sha256": plugin_hash,
        "staged_plugin_sha256": sha256(out_bin / plugin_filename),
        "p2_source_commit": P2_SOURCE_COMMIT if GPU_PLUGIN_NAME == "shift-native" else None,
        "p2_source_state_note": P2_SOURCE_STATE_NOTE if GPU_PLUGIN_NAME == "shift-native" else None,
        "p2_source_dirty": P2_SOURCE_DIRTY if GPU_PLUGIN_NAME == "shift-native" else None,
        "p2_source_diff_sha256": P2_SOURCE_DIFF_SHA256 if GPU_PLUGIN_NAME == "shift-native" else None,
        "p2_source_status_sha256": P2_SOURCE_STATUS_SHA256 if GPU_PLUGIN_NAME == "shift-native" else None,
        "p2_plugin_build_id": P2_PLUGIN_BUILD_ID if GPU_PLUGIN_NAME == "shift-native" else None,
        "p2_ring_trace_enabled": ring_trace_requested,
        "p2_ring_trace_record_count": len(ring_records),
        "p2_ring_trace_malformed_record_count": ring_malformed_records,
        "p2_ring_trace_logs": ring_trace_logs,
        "p2_ring_trace_status": (
            "records_captured" if ring_records
            else "requested_no_records" if ring_trace_requested
            else "not_requested"
        ),
        "trace_path": str(SCRIPT.relative_to(ROOT)),
        "trace_sha256": hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
        "runner_path": str(Path(__file__).relative_to(ROOT)),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "generated_source_sha256": generated_hashes,
        "generated_source_root": str(generated_root),
        "events_path": str(OUT / "events.json"),
        "gdb_log_path": str(OUT / "gdb.log"),
    }
    (OUT / "run_metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    print(f"gdb_exit={result} backend={GPU_PLUGIN_NAME} output={OUT} log={OUT / 'gdb.log'} events={OUT / 'events.json'} runner={runner_log}")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
