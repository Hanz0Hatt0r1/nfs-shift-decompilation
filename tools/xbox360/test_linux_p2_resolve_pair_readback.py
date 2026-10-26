#!/usr/bin/env python3
"""Guard the latest exact-XEX P2 resolve-pair readback record."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_p2_resolve_pair_readback_20261026.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.linux.p2-resolve-pair-readback.v1"
assert evidence["target"]["sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)

binaries = evidence["binaries"]
assert binaries["host_sha256"] == (
    "6a3ac7224c139dced55fe76bd110b3d66a8c1609a1afdfad9514485daf62702b"
)
assert binaries["rexglue_runtime_sha256"] == (
    "d8faeb3973a1a2564dea021f19d0418fa718268dadebd414b0006a94a9062253"
)
assert binaries["gpu_plugin_sha256"] == (
    "0b93aa89499b37bd0d274f42e50f0d1b11ae4ea3224bc6e3a57e5270a0447756"
)
assert binaries["runtime_link_resolution_checked"] is True

run = evidence["run"]
assert run["duration_seconds"] == 58.963
assert run["instrumentation"].startswith("No GDB")
controller = run["controller"]
assert len(controller["pulses"]) == 6
assert controller["same_run_guest_consumption_proven"] is False
assert [pulse["at_seconds"] for pulse in controller["pulses"]] == sorted(
    pulse["at_seconds"] for pulse in controller["pulses"]
)

log = run["renderer_log"]
assert log["ring_wake_events"] == log["ring_snapshot_events"] == log["ring_complete_events"]
assert log["ring_complete_events"] == 1915
assert log["copy_convert_accepts"] == log["draw_submission_batches"] == 1435
assert log["vulkan_frame_refresh_failures"] == log["guest_faults"] == 0
assert log["unresolved_captured_draws"] == 1
assert log["menu_background_xml_open_failures"] == 4

readback = run["readback"]
assert readback["frame"] == 400
assert (readback["width"], readback["height"]) == (1280, 720)
assert readback["bytes"] == readback["width"] * readback["height"] * 4
assert readback["format"] == "VK_FORMAT_A2B10G10R10_UNORM_PACK32"
assert readback["non_black_pixels"] == 0
assert readback["sha256"] == (
    "e94e580f80b4522e921a3c0cf72c929eed0fb7093da4e372c782eaf83827e991"
)

not_proven = evidence["interpretation"]["not_proven"]
assert any("caused the black frame" in item for item in not_proven)
assert any("offline-race entry" in item for item in not_proven)
assert any("renderer regression" in item for item in not_proven)

print("latest P2 resolve-pair readback evidence is internally consistent")

