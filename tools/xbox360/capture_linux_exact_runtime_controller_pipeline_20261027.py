#!/usr/bin/env python3
"""Trace retail controller fields while emitting bounded A/Start uinput pulses."""

from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path

from evdev import AbsInfo, UInput, ecodes


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(os.environ.get(
    "SHIFT_CONTROLLER_TRACE_OUT",
    "/tmp/nfs-shift-p1-exact-runtime-controller-pipeline-20261027",
))
GDB_SCRIPT = Path(os.environ.get(
    "SHIFT_CONTROLLER_TRACE_GDB",
    ROOT / "tools/xbox360/trace_linux_exact_runtime_controller_pipeline_20261027.gdb",
))
RUNTIME = Path(os.environ.get(
    "SHIFT_CONTROLLER_TRACE_RUNTIME",
    "/tmp/nfs-shift-p1-exact-runtime-20261027-detached/bin/nfs_shift",
))
SOURCE_BIN = RUNTIME.parent
BIN = OUT / "bin"
OUT.mkdir(parents=True, exist_ok=True)
BIN.mkdir(exist_ok=True)
for library in ("librexruntime.so", "librexgpu-shift-native.so"):
    target = BIN / library
    if not target.exists():
        target.symlink_to(SOURCE_BIN / library)

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
    ecodes.BTN_SOUTH,
    ecodes.BTN_EAST,
    ecodes.BTN_NORTH,
    ecodes.BTN_WEST,
    ecodes.BTN_TL,
    ecodes.BTN_TR,
    ecodes.BTN_SELECT,
    ecodes.BTN_START,
    ecodes.BTN_THUMBL,
    ecodes.BTN_THUMBR,
]
device = UInput(
    {ecodes.EV_KEY: keys,
     ecodes.EV_ABS: [(code, info) for code, info in axes.items()]},
    name="Microsoft X-Box 360 pad",
    bustype=ecodes.BUS_USB,
    vendor=0x045E,
    product=0x028E,
    version=0x0114,
)

env = os.environ.copy()
env["SDL_GAMECONTROLLER_IGNORE_DEVICES"] = "0x045e/0x0b12"
console_path = OUT / "runner.log"
with console_path.open("w", encoding="utf-8") as console:
    process = subprocess.Popen(
        ["gdb", "-q", "-batch", "-ex", f"file {RUNTIME}", "-x", str(GDB_SCRIPT)],
        stdout=console,
        stderr=subprocess.STDOUT,
        env=env,
    )
    started = time.monotonic()
    print(f"gdb_pid={process.pid} uinput={device.device.path} output={OUT}", flush=True)
    poll_ready = None
    poll_deadline = started + float(
        os.environ.get("SHIFT_CONTROLLER_TRACE_READY_TIMEOUT_SECONDS", "205"))
    while time.monotonic() < poll_deadline and process.poll() is None:
        try:
            trace_text = console_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            trace_text = ""
        if "CONTROLLER_UPDATE elapsed=" in trace_text and "object=target" in trace_text:
            poll_ready = time.monotonic()
            print(f"retail_controller_update_ready_after={poll_ready - started:.3f}s", file=console, flush=True)
            break
        time.sleep(0.1)
    else:
        print(f"retail_controller_update_not_observed_after={time.monotonic() - started:.3f}s", file=console, flush=True)
    if poll_ready is not None:
        pulse_origin = poll_ready
        wait_marker = os.environ.get("SHIFT_CONTROLLER_TRACE_WAIT_MARKER")
        marker_seen = not wait_marker
        if wait_marker:
            marker_deadline = time.monotonic() + float(
                os.environ.get("SHIFT_CONTROLLER_TRACE_MARKER_TIMEOUT_SECONDS", "90"))
            while time.monotonic() < marker_deadline and process.poll() is None:
                try:
                    trace_text = console_path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    trace_text = ""
                if wait_marker in trace_text:
                    marker_seen = True
                    pulse_origin = time.monotonic()
                    print(f"wait_marker_seen={wait_marker!r} after={pulse_origin - started:.3f}s",
                          file=console, flush=True)
                    break
                time.sleep(0.1)
            if not marker_seen:
                print(f"wait_marker_not_observed={wait_marker!r} after={time.monotonic() - started:.3f}s",
                      file=console, flush=True)
        if marker_seen:
            first_pulse_seconds = float(
                os.environ.get("SHIFT_CONTROLLER_TRACE_FIRST_PULSE_SECONDS", "1"))
            for index, code, label in [
                (0, ecodes.BTN_START, "Start"),
                (1, ecodes.BTN_SOUTH, "A"),
                (2, ecodes.BTN_START, "Start"),
            ]:
                at = pulse_origin + first_pulse_seconds + index * 6.0
                time.sleep(max(0, at - time.monotonic()))
                device.write(ecodes.EV_KEY, code, 1)
                device.syn()
                print(f"input {label} down at {time.monotonic() - started:.3f}s", file=console, flush=True)
                time.sleep(3.0)
                device.write(ecodes.EV_KEY, code, 0)
                device.syn()
                print(f"input {label} up at {time.monotonic() - started:.3f}s", file=console, flush=True)
            hold_seconds = float(os.environ.get("SHIFT_CONTROLLER_TRACE_HOLD_SECONDS", "0"))
            if hold_seconds > 0:
                time.sleep(hold_seconds)
                print(f"post_input_hold_seconds={hold_seconds}", file=console, flush=True)
            if process.poll() is None:
                process.send_signal(signal.SIGINT)
                print("stopped bounded GDB trace after controller pulses", file=console, flush=True)
        elif process.poll() is None:
            process.send_signal(signal.SIGINT)
            print("stopped bounded GDB trace because wait marker was not observed",
                  file=console, flush=True)
    elif process.poll() is None:
        process.send_signal(signal.SIGINT)
        print("stopped bounded GDB trace because controller update was not observed",
              file=console, flush=True)
    try:
        code = process.wait(timeout=155)
    except subprocess.TimeoutExpired:
        process.send_signal(2)
        try:
            code = process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            code = None
    print(f"gdb_exit={code} elapsed={time.monotonic() - started:.3f}s", file=console, flush=True)

device.close()
print(f"gdb_exit={code} trace={OUT / 'gdb.log'} console={console_path}")
