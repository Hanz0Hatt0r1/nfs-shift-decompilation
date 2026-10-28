#!/usr/bin/env python3
"""Regression test for Native Vulkan draw and shader dump capture flags."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).with_name("capture_linux_gpu_backend_pair_20261028.py")
SPEC = importlib.util.spec_from_file_location("gpu_backend_pair_capture", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
RUNNER_SCRIPT = SCRIPT.with_name("capture_linux_post_bink_worker_route_v45_ordered_route_20261027.py")
RUNNER_SPEC = importlib.util.spec_from_file_location("post_bink_capture_runner", RUNNER_SCRIPT)
assert RUNNER_SPEC and RUNNER_SPEC.loader


def main() -> None:
    assert MODULE.capture_backends(native_only=False) == ("xenos", "shift-native")
    assert MODULE.capture_backends(native_only=True) == ("shift-native",)
    assert not MODULE.should_compare_capture("shift-native", native_only=True)
    assert MODULE.should_compare_capture("shift-native", native_only=False)
    assert not MODULE.should_compare_capture("xenos", native_only=False)
    assert MODULE.metadata_contract(native_only=True) == (
        "capture_metadata.json", "shift.xbox360.linux-gpu-backend-capture.v1"
    )
    assert MODULE.metadata_contract(native_only=False) == (
        "pair_metadata.json", "shift.xbox360.linux-gpu-backend-pair.v1"
    )
    with patch.dict(os.environ, {
        "SHIFT_QUEUE_TRACE_INPUT_HOLD_MS": "1000",
        "SHIFT_QUEUE_TRACE_INPUT_GAP_MS": "100",
    }):
        runner = importlib.util.module_from_spec(RUNNER_SPEC)
        RUNNER_SPEC.loader.exec_module(runner)
    assert runner.INPUT_HOLD_MS == 1000
    assert runner.INPUT_GAP_MS == 100
    for option, value, expected in (
        ("--input-hold-ms", "0", "--input-hold-ms must be positive"),
        ("--input-gap-ms", "-1", "--input-gap-ms cannot be negative"),
    ):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(sys, "argv", [str(SCRIPT), "--output-root", str(Path(temporary) / "out"), option, value]):
                try:
                    MODULE.main()
                except SystemExit as exc:
                    assert str(exc) == expected
                else:
                    raise AssertionError(f"invalid {option} was accepted")
    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary) / "shift-native"
        output.mkdir()
        calls = []

        def fake_run(command, *, cwd, env, check):
            calls.append((command, cwd, env, check))
            return subprocess.CompletedProcess(command, 0)

        with patch.object(MODULE.subprocess, "run", side_effect=fake_run), patch.dict(
            MODULE.os.environ,
            {"SHIFT_QUEUE_TRACE_QUEUE_FIELD_ALIAS_PROBE": "physical_head_counter"},
        ):
            MODULE.run_capture(
                output=output,
                backend="shift-native",
                plugin=Path("plugin.so"),
                plugin_hash="a" * 64,
                resource_hash="b" * 64,
                duration=75,
                p2_commit="commit",
                native_draw_frame=322,
                input_trigger="bink_complete",
                input_trigger_delay_seconds=0.5,
                input_hold_ms=1000,
                input_gap_ms=100,
                trace_event_write_shd=True,
            )

        assert len(calls) == 1
        env = calls[0][2]
        assert env["SHIFT_NATIVE_VULKAN_DUMP_DRAW_FRAME"] == "322"
        assert env["SHIFT_NATIVE_VULKAN_DUMP_GEOMETRY_PREFIX"] == str(output / "native-draw")
        assert env["SHIFT_NATIVE_VULKAN_DUMP_SHADER_PREFIX"] == str(output / "native-shader")
        assert env["SHIFT_QUEUE_TRACE_INPUT_TRIGGER"] == "bink_complete"
        assert env["SHIFT_QUEUE_TRACE_INPUT_DELAY_SECONDS"] == "0.5"
        assert env["SHIFT_QUEUE_TRACE_INPUT_HOLD_MS"] == "1000"
        assert env["SHIFT_QUEUE_TRACE_INPUT_GAP_MS"] == "100"
        assert env["SHIFT_QUEUE_TRACE_EVENT_WRITE_SHD"] == "1"
        assert env["SHIFT_QUEUE_TRACE_QUEUE_FIELD_ALIAS_PROBE"] == "physical_head_counter"

    print("Native-only selection skips Xenos; selected Native draw frame enables geometry and shader dump prefixes")


if __name__ == "__main__":
    main()
