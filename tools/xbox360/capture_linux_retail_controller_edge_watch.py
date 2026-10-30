#!/usr/bin/env python3
"""Run the exact retail XEX with bounded input and read-only edge-byte watchpoints."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from evdev import AbsInfo, UInput, ecodes


ROOT = Path(__file__).resolve().parents[2]
OUT = Path("/tmp/nfs-shift-p1-controller-edge-watch-20261026")
GDB_SCRIPT = ROOT / "tools/xbox360/trace_linux_retail_controller_edge_watch.gdb"
RUNTIME = Path("/tmp/nfs-shift-p1-p2-scratch-linux-20261026/bin/nfs_shift")
OUT.mkdir(parents=True, exist_ok=True)

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
    {ecodes.EV_KEY: keys, ecodes.EV_ABS: [(code, info) for code, info in axes.items()]},
    name="Microsoft X-Box 360 pad",
    bustype=ecodes.BUS_USB,
    vendor=0x045E,
    product=0x028E,
    version=0x0114,
)

env = os.environ.copy()
env["SDL_GAMECONTROLLER_IGNORE_DEVICES"] = "0x045e/0x0b12"
runner_log = OUT / "runner.log"
with runner_log.open("w", encoding="utf-8") as log:
    process = subprocess.Popen(
        ["gdb", "-q", "-batch", "-ex", f"file {RUNTIME}", "-x", str(GDB_SCRIPT)],
        stdout=log,
        stderr=subprocess.STDOUT,
        env=env,
    )
    started = time.monotonic()
    print(f"gdb_pid={process.pid} uinput={device.device.path} output={OUT}", flush=True)
    for at, code, label in [
        (16, ecodes.BTN_START, "Start"),
        (24, ecodes.BTN_SOUTH, "A"),
        (32, ecodes.BTN_START, "Start"),
        (40, ecodes.BTN_SOUTH, "A"),
        (48, ecodes.BTN_START, "Start"),
    ]:
        time.sleep(max(0, started + at - time.monotonic()))
        device.write(ecodes.EV_KEY, code, 1)
        device.syn()
        print(f"input {label} down at {time.monotonic() - started:.3f}s", file=log, flush=True)
        time.sleep(0.65)
        device.write(ecodes.EV_KEY, code, 0)
        device.syn()
        print(f"input {label} up at {time.monotonic() - started:.3f}s", file=log, flush=True)
    try:
        exit_code = process.wait(timeout=25)
    except subprocess.TimeoutExpired:
        process.send_signal(2)
        try:
            exit_code = process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            exit_code = None
    print(f"gdb_exit={exit_code} elapsed={time.monotonic() - started:.3f}s", file=log, flush=True)

device.close()
print(f"gdb_exit={exit_code} trace={OUT / 'gdb.log'} runner={runner_log}")
