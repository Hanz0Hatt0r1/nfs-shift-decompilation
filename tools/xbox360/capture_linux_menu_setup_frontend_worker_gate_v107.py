#!/usr/bin/env python3
"""Capture the original menu dispatch caller around Start/A input."""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE_RUNNER = ROOT / "tools/xbox360/capture_linux_menu_setup_state2_input_v46_20261029.py"
TRACE = ROOT / "tools/xbox360/trace_linux_menu_setup_frontend_worker_gate_v107.gdb"
PLUGINS = {
    "xenos": (
        Path("/home/pes/work/nfs-shift-p1-v99-xenos-same-script-20261029/bin/librexgpu-xenos.so"),
        "8b5abe7a0c59a8a41af5aa166df23de46fed191bfc863e183c98d6023c54e4de",
    ),
    "shift-native": (
        Path("/home/pes/work/nfs-shift-p1-service-ready-after-clean-pr2161-v126-native-20261029/bin/librexgpu-shift-native.so"),
        "fd615adad5febc2adcf9a46fa0b74a67c9cf28f013bc74ca8715ac9abad9c490",
    ),
}


def main() -> int:
    spec = importlib.util.spec_from_file_location("menu_setup_state2_input_base", BASE_RUNNER)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load input capture runner: {BASE_RUNNER}")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    runner.PLUGINS = PLUGINS
    runner.SCRIPT = TRACE
    runner.__file__ = str(Path(__file__).resolve())
    return runner.main()


if __name__ == "__main__":
    raise SystemExit(main())
