#!/usr/bin/env python3
"""Run the exact retail XEX with P2's matched depth-resolve runtime and bounded input."""

from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import time
from pathlib import Path

from evdev import AbsInfo, UInput, ecodes


OUT = Path("/tmp/nfs-shift-p1-depth-resolve-input-followthrough-20261027")
BIN = OUT / "bin"
GAME_DATA = Path("/home/pes/work/process2-retail-isolated-irq-20261023/game-data")
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "user").mkdir(exist_ok=True)
(OUT / "cache").mkdir(exist_ok=True)

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
pad = UInput(
    {ecodes.EV_KEY: keys, ecodes.EV_ABS: [(code, info) for code, info in axes.items()]},
    name="Microsoft X-Box 360 pad",
    bustype=ecodes.BUS_USB,
    vendor=0x045E,
    product=0x028E,
    version=0x0114,
)

env = os.environ.copy()
env["LD_LIBRARY_PATH"] = str(BIN)
env["SDL_GAMECONTROLLER_IGNORE_DEVICES"] = "0x045e/0x0b12"
runtime_log = OUT / "runner.log"
capture_events = []
input_events = []
captures = [(45, "before-first-post-disclaimer-input"),
            (55, "after-A-1"), (68, "after-Start-1"),
            (80, "after-A-2"), (95, "after-Start-2"),
            (110, "after-A-3")]
pulses = [(52, ecodes.BTN_SOUTH, "A"),
          (65, ecodes.BTN_START, "Start"),
          (78, ecodes.BTN_SOUTH, "A"),
          (90, ecodes.BTN_START, "Start"),
          (102, ecodes.BTN_SOUTH, "A")]


def wait_until(started: float, second: float) -> None:
    time.sleep(max(0.0, started + second - time.monotonic()))


def capture_game_window(pid: int, at_seconds: int, label: str) -> dict:
    clients = json.loads(subprocess.check_output(["hyprctl", "clients", "-j"], text=True))
    client = next((item for item in clients if item.get("pid") == pid), None)
    if client is None:
        return {"at_seconds": at_seconds, "label": label, "error": "target PID window not found"}
    x, y = client["at"]
    width, height = client["size"]
    path = OUT / f"window-{at_seconds:03d}s-{label}.png"
    subprocess.run(["grim", "-g", f"{x},{y} {width}x{height}", str(path)], check=True)
    data = path.read_bytes()
    row = {
        "at_seconds": at_seconds,
        "label": label,
        "path": str(path),
        "sha256": hashlib.sha256(data).hexdigest(),
        "geometry": [x, y, width, height],
    }
    print("WINDOW_CAPTURE", json.dumps(row), flush=True)
    return row


with runtime_log.open("w", encoding="utf-8") as runtime_output:
    process = subprocess.Popen(
        [
            str(BIN / "nfs_shift"),
            f"--game_data_root={GAME_DATA}",
            f"--user_data_root={OUT / 'user'}",
            f"--cache_root={OUT / 'cache'}",
            "--gpu_plugin=shift-native",
            "--no-async_shader_compilation",
            "--fullscreen=false",
        ],
        stdout=runtime_output,
        stderr=subprocess.STDOUT,
        env=env,
    )
started = time.monotonic()
pad_path = pad.device.path if pad.device is not None else "uinput-created-no-readable-event-node"
print(f"pid={process.pid} pad={pad_path} out={OUT}", flush=True)
try:
    events = [(t, "capture", label) for t, label in captures]
    events += [(t, "input", (code, label)) for t, code, label in pulses]
    for at, kind, payload in sorted(events):
        wait_until(started, at)
        if process.poll() is not None:
            print("TITLE_EXITED", process.returncode, flush=True)
            break
        if kind == "capture":
            capture_events.append(capture_game_window(process.pid, at, payload))
            continue
        code, label = payload
        pad.write(ecodes.EV_KEY, code, 1)
        pad.syn()
        input_events.append({"at_seconds": round(time.monotonic() - started, 3), "button": label, "edge": "press"})
        time.sleep(0.5)
        pad.write(ecodes.EV_KEY, code, 0)
        pad.syn()
        input_events.append({"at_seconds": round(time.monotonic() - started, 3), "button": label, "edge": "release"})
        print("INPUT", input_events[-2:], flush=True)
    wait_until(started, 120)
finally:
    if process.poll() is None:
        process.send_signal(signal.SIGINT)
    try:
        return_code = process.wait(timeout=12)
    except subprocess.TimeoutExpired:
        process.kill()
        return_code = process.wait(timeout=5)
    pad.close()

summary = {
    "duration_seconds": round(time.monotonic() - started, 3),
    "exit_code": return_code,
    "input_events": input_events,
    "captures": capture_events,
    "runtime_log": str(runtime_log),
}
summary_path = OUT / "run-summary.json"
summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print("RUN_SUMMARY", json.dumps(summary), flush=True)
