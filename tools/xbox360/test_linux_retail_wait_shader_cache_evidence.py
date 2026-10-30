#!/usr/bin/env python3
"""Guard the current exact-XEX retail wait snapshot and its claim boundaries."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_retail_wait_shader_cache_20261026.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-retail-wait-shader-cache.v1"
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
assert evidence["binaries"]["host_sha256"] == (
    "6a3ac7224c139dced55fe76bd110b3d66a8c1609a1afdfad9514485daf62702b"
)
assert evidence["binaries"]["rexglue_runtime"]["mapping_verified"] is True
assert evidence["binaries"]["gpu_plugin"]["sha256"] == (
    "f1d6394bfa01dd65b2472d50eda64b1dd5ceade8993a43771b0e73b84090f95c"
)
assert evidence["probe"]["controller_events_sent"] is False
assert "read only" in evidence["probe"]["instrumentation"]

queue = evidence["retail_queue"]
assert queue["head"] == 4967
assert queue["tail"] == 4977
assert queue["head"] <= queue["wait_target_decimal"] < queue["tail"]
assert queue["wait_return_site"] == "0x823B3560"
assert queue["predicate_return_r3"] == 1
assert queue["predicate"] == "0x04"
assert int(queue["predicate"], 16) & int(queue["tested_completion_mask"], 16) == 0
assert queue["global_831B3820"] == "0x00000000"

stack = evidence["stacks"]
assert stack["guest_main_thread"]["thread_name"] == "Core 0/0: Main"
assert "pthread_cond_wait" in stack["host_graphics_worker"]["state"]
assert evidence["runtime_activity"]["vulkan_frame_refresh_failures"] == 0
assert evidence["runtime_activity"]["guest_faults"] == 0

not_proven = evidence["interpretation"]["not_proven"]
assert any("caused the wait" in item for item in not_proven)
assert any("offline race" in item for item in not_proven)

print("current exact-XEX retail wait evidence is internally consistent")
